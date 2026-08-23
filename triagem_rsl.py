"""
Triagem Automática para Revisão Sistemática da Literatura (RSL)
Módulo central de processamento, deduplicação, filtragem por critérios
(inclusão/exclusão) e geração de relatórios de conformidade (PRISMA 2020).
"""

from typing import Any, Dict, List, Optional, Union
import io
import os
import re
import pandas as pd

INPUT_FILE = "articles.xlsx"
OUT_APROV = "aprovados.xlsx"
OUT_REJ = "rejeitados.xlsx"

COLS_SAIDA = [
    "bibtex_key", "title", "author", "journal", "year", "source",
    "abstract", "document_type", "doi", "url",
    "author_keywords", "keywords", "publisher", "language",
]

# Configurações de Regras Padrão
DEFAULT_RULES = [
    {
        "id": "EX1",
        "name": "Estudos de Revisão (Exclusão)",
        "type": "exclusion",
        "pattern": r"review|survey|meta-analysis|revisão",
        "fields": ["title", "abstract"]
    },
    {
        "id": "IN1",
        "name": "Geração Procedural (Inclusão)",
        "type": "inclusion",
        "pattern": r"procedural|pcg|geração procedural",
        "fields": ["title", "abstract", "keywords"]
    }
]


def _ler_csv_com_auto_separador(source: Union[str, io.BytesIO, Any], encoding: str = "utf-8") -> pd.DataFrame:
    try:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source, sep=None, engine="python", encoding=encoding)
    except Exception:
        if hasattr(source, "seek"):
            source.seek(0)
        return pd.read_csv(source, sep=",", encoding=encoding)


def carregar_base_artigos(source: Union[str, io.BytesIO, Any]) -> pd.DataFrame:
    """
    Carrega a planilha ou arquivo de artigos suportando formatos .xlsx, .xls e .csv.
    Detecta automaticamente o separador do CSV (, ou ;) e a codificação (utf-8/latin1).
    Normaliza os nomes de colunas removendo espaços residuais.
    """
    if isinstance(source, str):
        ext = os.path.splitext(source)[1].lower()
        if ext == ".csv":
            try:
                df = _ler_csv_com_auto_separador(source, encoding="utf-8")
            except UnicodeDecodeError:
                df = _ler_csv_com_auto_separador(source, encoding="latin1")
        else:
            df = pd.read_excel(source)
    else:
        # Objeto buffer (ex: UploadedFile do Streamlit ou BytesIO)
        file_name = getattr(source, "name", "").lower()
        if file_name.endswith(".csv"):
            try:
                df = _ler_csv_com_auto_separador(source, encoding="utf-8")
            except (UnicodeDecodeError, Exception):
                df = _ler_csv_com_auto_separador(source, encoding="latin1")
        else:
            df = pd.read_excel(source)

    # Limpeza de nomes de colunas
    df.columns = [str(c).strip() for c in df.columns]
    return df


def executar_triagem(
    df: pd.DataFrame,
    rules: List[Dict[str, Any]],
    remover_duplicatas: bool = True,
    coluna_dedup: str = "title",
    estrategia_doi: str = "remove"  # "remove", "flag", "ignore"
) -> Dict[str, Any]:
    """
    Executa a triagem dos artigos com base nos parâmetros e regras fornecidas.
    Retorna um dicionário estruturado com:
      - 'aprovados': pd.DataFrame
      - 'rejeitados': pd.DataFrame
      - 'stats': dict (estatísticas detalhadas do processamento e funil PRISMA)
    """
    df_clean = df.copy()
    total_inicial = len(df_clean)

    # ── 1. Limpeza de Duplicatas ──────────────────────────────────────────────
    duplicatas = 0
    if remover_duplicatas and coluna_dedup in df_clean.columns:
        norm_col = f"_{coluna_dedup}_norm"
        df_clean[norm_col] = df_clean[coluna_dedup].astype(str).str.strip().str.lower()
        df_clean = df_clean.drop_duplicates(subset=norm_col)
        duplicatas = total_inicial - len(df_clean)
        df_clean = df_clean.drop(columns=[norm_col])

    # ── 2. Limpeza / Sinalização de DOI ───────────────────────────────────────
    sem_doi = 0
    sem_doi_count = 0
    if "doi" in df_clean.columns:
        sem_doi_mask = df_clean["doi"].isna() | (df_clean["doi"].astype(str).str.strip() == "")
        sem_doi_count = int(sem_doi_mask.sum())

        if estrategia_doi == "remove":
            total_antes_doi = len(df_clean)
            df_clean = df_clean[~sem_doi_mask].copy()
            sem_doi = total_antes_doi - len(df_clean)
        elif estrategia_doi == "flag":
            df_clean["sem_doi_alerta"] = sem_doi_mask

    # ── 3. Consolidação Otimizada de Texto e Execução de Regex ─────────────────
    # Cacheia textos consolidados por combinação de colunas para evitar repetição
    consolidated_cache: Dict[tuple, pd.Series] = {}

    for rule in rules:
        fields = rule.get("fields", ["title", "abstract", "author_keywords", "keywords"])
        # Preserva a ordem original dos campos especificados na regra (ex: title antes de abstract)
        existing_fields = tuple([f for f in fields if f in df_clean.columns])

        if existing_fields not in consolidated_cache:
            if existing_fields:
                # Garante que NaNs virem string vazia sem gerar literais 'nan' ou 'None'
                consolidated_cache[existing_fields] = (
                    df_clean[list(existing_fields)].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
                )
            else:
                consolidated_cache[existing_fields] = pd.Series("", index=df_clean.index)

        consolidated_text = consolidated_cache[existing_fields]
        rule_id = rule["id"]
        pattern_str = str(rule.get("pattern", "")).strip()
        is_excl = str(rule.get("type", "")).strip().lower() in ["exclusion", "exclusao", "exclusão", "ex"]

        if pattern_str:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                matches = consolidated_text.str.contains(pattern, regex=True, na=False)
            except Exception:
                # Se regex for inválida, exclusão não descarta e inclusão não penaliza
                matches = pd.Series(False if is_excl else True, index=df_clean.index)
        else:
            matches = pd.Series(False if is_excl else True, index=df_clean.index)

        df_clean[f"_match_{rule_id}"] = matches

    # ── 4. Classificação Rápida dos Artigos ────────────────────────────────────
    # Constrói motivos de rejeição vetorizados por linha
    rejeicoes_por_linha: List[List[str]] = [[] for _ in range(len(df_clean))]

    for rule in rules:
        rule_id = rule["id"]
        rule_name = rule["name"]
        is_excl = str(rule.get("type", "")).strip().lower() in ["exclusion", "exclusao", "exclusão", "ex"]
        matches_series = df_clean[f"_match_{rule_id}"].values

        if is_excl:
            for i, matched in enumerate(matches_series):
                if matched:
                    rejeicoes_por_linha[i].append(f"{rule_id} ({rule_name})")
        else:  # inclusion
            for i, matched in enumerate(matches_series):
                if not matched:
                    rejeicoes_por_linha[i].append(f"Falta {rule_id} ({rule_name})")

    decisoes = [", ".join(motivos) if motivos else "APROVADO" for motivos in rejeicoes_por_linha]
    df_clean["_decisao"] = decisoes

    # ── 5. Separação de Aprovados e Rejeitados ─────────────────────────────────
    match_cols = [f"_match_{rule['id']}" for rule in rules]
    internal_cols = ["_decisao"] + match_cols

    aprovados = df_clean[df_clean["_decisao"] == "APROVADO"].copy()
    rejeitados = df_clean[df_clean["_decisao"] != "APROVADO"].copy()

    rejeitados["motivo_rejeicao"] = rejeitados["_decisao"]

    # Limpeza de colunas temporárias internas
    aprovados_export = aprovados.drop(columns=[col for col in internal_cols if col in aprovados.columns])
    rejeitados_export = rejeitados.drop(columns=[col for col in internal_cols if col in rejeitados.columns])

    # Filtrar apenas as colunas de saída que existem, mais alertas se houverem
    cols_aprov = [c for c in COLS_SAIDA if c in aprovados_export.columns]
    if "sem_doi_alerta" in aprovados_export.columns:
        cols_aprov.append("sem_doi_alerta")
    # Manter demais colunas úteis presentes no dataset original
    extra_aprov = [c for c in aprovados_export.columns if c not in cols_aprov]
    aprovados_export = aprovados_export[cols_aprov + extra_aprov]

    cols_rej = [c for c in COLS_SAIDA if c in rejeitados_export.columns]
    if "sem_doi_alerta" in rejeitados_export.columns:
        cols_rej.append("sem_doi_alerta")
    cols_rej.append("motivo_rejeicao")
    extra_rej = [c for c in rejeitados_export.columns if c not in cols_rej]
    rejeitados_export = rejeitados_export[cols_rej + extra_rej]

    # Estatísticas de Regras
    regra_stats = {}
    for rule in rules:
        rule_id = rule["id"]
        is_excl = str(rule.get("type", "")).strip().lower() in ["exclusion", "exclusao", "exclusão", "ex"]
        matches = df_clean[f"_match_{rule_id}"]
        if is_excl:
            regra_stats[rule_id] = int(matches.sum())
        else:
            regra_stats[rule_id] = int((~matches).sum())

    stats = {
        "total_inicial": total_inicial,
        "duplicatas_removidas": duplicatas,
        "sem_doi": sem_doi,
        "sem_doi_flagged": int(sem_doi_count),
        "pos_limpeza": len(df_clean),
        "aprovados": len(aprovados),
        "rejeitados": len(rejeitados),
        "taxa_aprovacao_pct": round((len(aprovados) / len(df_clean) * 100) if len(df_clean) > 0 else 0.0, 2),
        "taxa_rejeicao_pct": round((len(rejeitados) / len(df_clean) * 100) if len(df_clean) > 0 else 0.0, 2),
        "regra_stats": regra_stats
    }

    return {
        "aprovados": aprovados_export,
        "rejeitados": rejeitados_export,
        "stats": stats
    }


def gerar_excel_multi_abas(
    aprovados: pd.DataFrame,
    rejeitados: pd.DataFrame,
    stats: Dict[str, Any],
    rules: List[Dict[str, Any]]
) -> bytes:
    """
    Gera um único arquivo Excel (.xlsx) contendo 3 planilhas:
    1. 'Artigos_Aprovados'
    2. 'Artigos_Rejeitados'
    3. 'Resumo_PRISMA' (Relatório com métricas de triagem e regras)
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Aba 1: Aprovados
        aprovados.to_excel(writer, sheet_name="Artigos_Aprovados", index=False)

        # Aba 2: Rejeitados
        rejeitados.to_excel(writer, sheet_name="Artigos_Rejeitados", index=False)

        # Aba 3: Resumo PRISMA
        linhas_resumo = [
            {"Métrica PRISMA": "1. Identificação - Total Inicial de Artigos", "Valor": stats.get("total_inicial", 0)},
            {"Métrica PRISMA": "2. Triagem - Duplicatas Removidas", "Valor": stats.get("duplicatas_removidas", 0)},
            {"Métrica PRISMA": "3. Triagem - Artigos Excluídos Sem DOI", "Valor": stats.get("sem_doi", 0)},
            {"Métrica PRISMA": "4. Triagem - Artigos Sinalizados Sem DOI", "Valor": stats.get("sem_doi_flagged", 0)},
            {"Métrica PRISMA": "5. Elegibilidade - Artigos Avaliados por Critérios", "Valor": stats.get("pos_limpeza", 0)},
            {"Métrica PRISMA": "6. Inclusão - Artigos Aprovados", "Valor": stats.get("aprovados", 0)},
            {"Métrica PRISMA": "7. Exclusão - Artigos Rejeitados", "Valor": stats.get("rejeitados", 0)},
            {"Métrica PRISMA": "8. Taxa de Aprovação (%)", "Valor": f"{stats.get('taxa_aprovacao_pct', 0.0)}%"},
            {"Métrica PRISMA": "9. Taxa de Rejeição (%)", "Valor": f"{stats.get('taxa_rejeicao_pct', 0.0)}%"}
        ]
        df_resumo_prisma = pd.DataFrame(linhas_resumo)
        df_resumo_prisma.to_excel(writer, sheet_name="Resumo_PRISMA", index=False, startrow=0)

        # Detalhamento de Regras no Resumo
        linhas_regras = []
        for r in rules:
            r_id = r["id"]
            r_name = r["name"]
            r_type = "Exclusão" if r["type"] == "exclusion" else "Inclusão"
            count = stats.get("regra_stats", {}).get(r_id, 0)
            linhas_regras.append({
                "ID Regra": r_id,
                "Nome": r_name,
                "Tipo": r_type,
                "Expressão Regular": r.get("pattern", ""),
                "Artigos Afetados": count
            })

        df_regras_resumo = pd.DataFrame(linhas_regras)
        start_row_rules = len(df_resumo_prisma) + 3
        df_regras_resumo.to_excel(writer, sheet_name="Resumo_PRISMA", index=False, startrow=start_row_rules)

    return output.getvalue()


def main() -> None:
    input_file = INPUT_FILE
    if not os.path.exists(input_file):
        for alt in ["articles.xls", "articles.csv"]:
            if os.path.exists(alt):
                input_file = alt
                break
        else:
            print(f"Erro: O arquivo de entrada '{input_file}' não foi encontrado.")
            return

    df = carregar_base_artigos(input_file)

    # Executa a triagem com as regras padrão
    resultado = executar_triagem(
        df=df,
        rules=DEFAULT_RULES,
        remover_duplicatas=True,
        coluna_dedup="title",
        estrategia_doi="remove"
    )

    aprovados = resultado["aprovados"]
    rejeitados = resultado["rejeitados"]
    stats = resultado["stats"]

    # Salva os resultados individuais e consolidados
    aprovados.to_excel(OUT_APROV, index=False)
    rejeitados.to_excel(OUT_REJ, index=False)

    multi_excel_bytes = gerar_excel_multi_abas(aprovados, rejeitados, stats, DEFAULT_RULES)
    with open("triagem_consolidada_prisma.xlsx", "wb") as f:
        f.write(multi_excel_bytes)

    # Imprime o Relatório
    print("=" * 60)
    print("RELATÓRIO DE TRIAGEM – RSL (CLI)")
    print("=" * 60)
    print(f"  Total inicial            : {stats['total_inicial']}")
    print(f"  Duplicatas removidas     : {stats['duplicatas_removidas']}")
    print(f"  Removidos sem DOI        : {stats['sem_doi']}")
    print(f"  Pós-limpeza (triagem)    : {stats['pos_limpeza']}")
    print("-" * 60)

    # Imprime estatísticas das regras
    for rule in DEFAULT_RULES:
        rule_id = rule["id"]
        rule_name = rule["name"]
        rule_type = rule["type"]
        count = stats["regra_stats"][rule_id]

        prefix = "  Com" if rule_type == "exclusion" else "  Sem"
        label = f"{prefix} {rule_id} ({rule_name})"
        print(f"{label:<45}: {count}")

    print("=" * 60)
    print(f"  TOTAL APROVADOS          : {stats['aprovados']} ({stats['taxa_aprovacao_pct']}%)")
    print(f"  TOTAL REJEITADOS         : {stats['rejeitados']} ({stats['taxa_rejeicao_pct']}%)")
    print("=" * 60)
    print("Planilhas salvas com sucesso (incluindo 'triagem_consolidada_prisma.xlsx')!")


if __name__ == "__main__":
    main()
