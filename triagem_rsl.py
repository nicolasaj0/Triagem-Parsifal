"""
Triagem Automática para Revisão Sistemática da Literatura (RSL)
Tema: Análise de Desempenho Computacional de Algoritmos Clássicos
       na Geração Procedural de Níveis
---------------------------------------------------------------
Entrada : articles.xlsx
Saída   : aprovados.xlsx | rejeitados.xlsx
"""

import pandas as pd
import re
import os

INPUT_FILE  = "articles.xlsx"
OUT_APROV   = "aprovados.xlsx"
OUT_REJ     = "rejeitados.xlsx"

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


def executar_triagem(
    df: pd.DataFrame,
    rules: list,
    remover_duplicatas: bool = True,
    coluna_dedup: str = "title",
    estrategia_doi: str = "remove"  # "remove", "flag", "ignore"
) -> dict:
    """
    Executa a triagem dos artigos com base nos parâmetros e regras fornecidas.
    Retorna um dicionário com:
      - 'aprovados': pd.DataFrame
      - 'rejeitados': pd.DataFrame
      - 'stats': dict (estatísticas do processamento)
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
        sem_doi_count = sem_doi_mask.sum()
        
        if estrategia_doi == "remove":
            total_antes_doi = len(df_clean)
            df_clean = df_clean[~sem_doi_mask].copy()
            sem_doi = total_antes_doi - len(df_clean)
        elif estrategia_doi == "flag":
            df_clean["sem_doi_alerta"] = sem_doi_mask
            
    # ── 3. Aplicar padrões de busca das regras ────────────────────────────────
    for rule in rules:
        rule_id = rule["id"]
        fields = rule.get("fields", ["title", "abstract", "author_keywords", "keywords"])
        
        # Filtra apenas os campos que existem no dataframe
        existing_fields = [f for f in fields if f in df_clean.columns]
        if existing_fields:
            consolidated_text = df_clean[existing_fields].fillna("").agg(" ".join, axis=1).str.lower()
        else:
            consolidated_text = pd.Series("", index=df_clean.index)
            
        pattern_str = rule["pattern"]
        try:
            pattern = re.compile(pattern_str)
            matches = consolidated_text.str.contains(pattern, regex=True, na=False)
        except Exception:
            # Caso a regex seja inválida, consideramos que não encontrou correspondência
            matches = pd.Series(False, index=df_clean.index)
            
        df_clean[f"_match_{rule_id}"] = matches

    # ── 4. Classificar os Artigos ─────────────────────────────────────────────
    def classificar_linha(row: pd.Series) -> str:
        motivos = []
        for rule in rules:
            rule_id = rule["id"]
            rule_name = rule["name"]
            rule_type = rule["type"]
            matched = row[f"_match_{rule_id}"]
            
            if rule_type == "exclusion" and matched:
                motivos.append(f"{rule_id} ({rule_name})")
            elif rule_type == "inclusion" and not matched:
                motivos.append(f"Falta {rule_id} ({rule_name})")
                
        return ", ".join(motivos) if motivos else "APROVADO"
        
    df_clean["_decisao"] = df_clean.apply(classificar_linha, axis=1)
    
    # ── 5. Separar Aprovados e Rejeitados ─────────────────────────────────────
    match_cols = [f"_match_{rule['id']}" for rule in rules]
    
    aprovados = df_clean[df_clean["_decisao"] == "APROVADO"].copy()
    rejeitados = df_clean[df_clean["_decisao"] != "APROVADO"].copy()
    
    rejeitados["motivo_rejeicao"] = rejeitados["_decisao"]
    
    # Limpeza de colunas temporárias internas
    internal_cols = ["_decisao"] + match_cols
    aprovados_export = aprovados.drop(columns=[col for col in internal_cols if col in aprovados.columns])
    rejeitados_export = rejeitados.drop(columns=[col for col in internal_cols if col in rejeitados.columns])
    
    # Filtrar apenas as colunas de saída que existem, mais alertas se houverem
    cols_aprov = [c for c in COLS_SAIDA if c in aprovados_export.columns]
    if "sem_doi_alerta" in aprovados_export.columns:
        cols_aprov.append("sem_doi_alerta")
    aprovados_export = aprovados_export[cols_aprov]
    
    cols_rej = [c for c in COLS_SAIDA if c in rejeitados_export.columns]
    if "sem_doi_alerta" in rejeitados_export.columns:
        cols_rej.append("sem_doi_alerta")
    cols_rej.append("motivo_rejeicao")
    rejeitados_export = rejeitados_export[cols_rej]
    
    # Estatísticas de Regras
    regra_stats = {}
    for rule in rules:
        rule_id = rule["id"]
        rule_type = rule["type"]
        matches = df_clean[f"_match_{rule_id}"]
        if rule_type == "exclusion":
            regra_stats[rule_id] = int(matches.sum())
        else:
            regra_stats[rule_id] = int((~matches).sum())
            
    stats = {
        "total_inicial": total_inicial,
        "duplicatas_removidas": duplicatas,
        "sem_doi": sem_doi,
        "pos_limpeza": len(df_clean),
        "aprovados": len(aprovados),
        "rejeitados": len(rejeitados),
        "regra_stats": regra_stats
    }
    
    if "sem_doi_alerta" in df_clean.columns:
        stats["sem_doi_flagged"] = int(sem_doi_count)
    else:
        stats["sem_doi_flagged"] = int(sem_doi_count)
        
    return {
        "aprovados": aprovados_export,
        "rejeitados": rejeitados_export,
        "stats": stats
    }


def main() -> None:
    if not os.path.exists(INPUT_FILE):
        print(f"Erro: O arquivo de entrada '{INPUT_FILE}' não foi encontrado.")
        return

    df = pd.read_excel(INPUT_FILE)
    
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
    
    # Salva os resultados
    aprovados.to_excel(OUT_APROV, index=False)
    rejeitados.to_excel(OUT_REJ, index=False)
    
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
    print(f"  TOTAL APROVADOS          : {stats['aprovados']}")
    print(f"  TOTAL REJEITADOS         : {stats['rejeitados']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
