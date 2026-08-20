import streamlit as st
import pandas as pd
import json
import io
import re
import os
from typing import List, Dict, Any
import plotly.graph_objects as go
import plotly.express as px

from triagem_rsl import (
    executar_triagem,
    carregar_base_artigos,
    gerar_excel_multi_abas,
    DEFAULT_RULES,
    COLS_SAIDA
)

# ── CONFIGURAÇÃO DA PÁGINA ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Triador RSL Parsifal - Screening Inteligente",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── ESTILIZAÇÃO CSS AVANÇADA COM SUPORTE A TEMA CLARO/ESCURO ───────────────────
st.markdown("""
<style>
    /* Tipografia e Títulos */
    .main-header {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(120deg, #1d4ed8, #0ea5e9, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    /* Cards de Estatísticas & Regras */
    .metric-card {
        border-radius: 10px;
        padding: 1rem 1.25rem;
        border: 1px solid rgba(226, 232, 240, 0.8);
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 0.75rem;
    }
    
    .badge-approved {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-block;
    }
    .badge-rejected {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-block;
    }
    
    /* Suporte a Tema Escuro */
    @media (prefers-color-scheme: dark) {
        .metric-card {
            background: #1e293b;
            border-color: #334155;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }
        .sub-header {
            color: #94a3b8;
        }
        .badge-approved {
            background-color: #064e3b;
            color: #6ee7b7;
        }
        .badge-rejected {
            background-color: #7f1d1d;
            color: #fca5a5;
        }
    }
</style>
""", unsafe_allow_html=True)


# ── FUNÇÕES AUXILIARES COM CACHE ──────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def converter_df_para_excel(df: pd.DataFrame) -> bytes:
    """Serializa um DataFrame para Excel em memória com cache."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def gerar_pacote_completo_excel(
    aprovados: pd.DataFrame,
    rejeitados: pd.DataFrame,
    stats: Dict[str, Any],
    rules: List[Dict[str, Any]]
) -> bytes:
    """Gera o arquivo unificado com múltiplas abas em cache."""
    return gerar_excel_multi_abas(aprovados, rejeitados, stats, rules)


def highlight_text(text: str, rules: list, field_name: str) -> str:
    """
    Destaca ocorrências de critérios ativos no texto com formatação visual.
    Mescla trechos sobrepostos com segurança.
    """
    if not isinstance(text, str) or not text:
        return ""

    spans = []
    for r in rules:
        fields = r.get("fields", [])
        if field_name not in fields:
            continue

        pattern_str = r.get("pattern", "")
        if not pattern_str or not pattern_str.strip():
            continue

        try:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            for match in pattern.finditer(text):
                start, end = match.span()
                color = "#fecaca" if r["type"] == "exclusion" else "#bbf7d0"
                text_color = "#991b1b" if r["type"] == "exclusion" else "#166534"
                label = r["id"]
                spans.append((start, end, color, text_color, label))
        except Exception:
            pass

    if not spans:
        return text

    spans.sort(key=lambda x: (x[0], -x[1]))

    merged_spans = []
    for current in spans:
        if not merged_spans:
            merged_spans.append(current)
        else:
            last_start, last_end, last_color, last_text_color, last_label = merged_spans[-1]
            curr_start, curr_end, curr_color, curr_text_color, curr_label = current
            if curr_start < last_end:
                new_end = max(last_end, curr_end)
                is_excl = (last_color == "#fecaca" or curr_color == "#fecaca")
                new_color = "#fecaca" if is_excl else "#bbf7d0"
                new_text_color = "#991b1b" if is_excl else "#166534"
                new_label = f"{last_label}+{curr_label}"
                merged_spans[-1] = (last_start, new_end, new_color, new_text_color, new_label)
            else:
                merged_spans.append(current)

    result = []
    last_idx = 0
    for start, end, color, text_color, label in merged_spans:
        result.append(text[last_idx:start])
        matched_text = text[start:end]
        result.append(
            f'<mark style="background-color: {color}; color: {text_color}; border-radius: 4px; padding: 2px 5px; font-weight: 600;" title="Regra: {label}">'
            f'{matched_text}'
            f'<sub style="font-size: 0.72em; margin-left: 3px; font-weight: 800;">{label}</sub>'
            f'</mark>'
        )
        last_idx = end
    result.append(text[last_idx:])
    return "".join(result)


# ── INICIALIZAÇÃO DE ESTADO DA SESSÃO ─────────────────────────────────────────
if "rules" not in st.session_state:
    st.session_state.rules = json.loads(json.dumps(DEFAULT_RULES))

if "resultados" not in st.session_state:
    st.session_state.resultados = None


# ── CABEÇALHO PRINCIPAL ───────────────────────────────────────────────────────
st.markdown('<div class="main-header">🔍 Triador Automático de RSL - Parsifal</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Filtre artigos, valide critérios de inclusão/exclusão por Expressões Regulares e gere relatórios no padrão PRISMA 2020.</div>',
    unsafe_allow_html=True
)

# ── PAINEL LATERAL (SIDEBAR) ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Painel de Controle")

    # 1. Base de Artigos
    st.subheader("1. Importar Artigos")
    uploaded_file = st.file_uploader(
        "Arquivo do Parsifal (.xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv"],
        help="Planilha de artigos exportada do Parsifal, Scopus, IEEE ou base similar."
    )

    columns_list = []
    df_uploaded = None
    if uploaded_file is not None:
        try:
            df_uploaded = carregar_base_artigos(uploaded_file)
            columns_list = df_uploaded.columns.tolist()
            st.success(f"✅ Base carregada: **{len(df_uploaded)} artigos** ({len(columns_list)} colunas)")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.markdown("---")

    # 2. Configurações de Limpeza
    st.subheader("2. Estratégias de Limpeza")
    remover_duplicatas = st.checkbox("Remover Artigos Duplicados", value=True, help="Normaliza o texto da coluna de título para remover repetições.")

    coluna_dedup = "title"
    if remover_duplicatas:
        default_idx = columns_list.index("title") if "title" in columns_list else 0
        coluna_dedup = st.selectbox(
            "Coluna para Deduplicação",
            options=columns_list if columns_list else ["title"],
            index=default_idx
        )

    estrategia_doi = st.selectbox(
        "Filtro de Artigos Sem DOI",
        options=["remove", "flag", "ignore"],
        format_func=lambda x: {
            "remove": "❌ Remover artigos sem DOI",
            "flag": "⚠️ Apenas sinalizar no relatório",
            "ignore": "⚙️ Ignorar verificação de DOI"
        }.get(x, x),
        index=0,
        help="Define a política para registros sem código identificador DOI."
    )

    st.markdown("---")

    # 3. Perfil de Regras
    st.subheader("3. Perfis de Regras")
    rules_json_str = json.dumps(st.session_state.rules, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Exportar Regras (JSON)",
        data=rules_json_str,
        file_name="perfil_regras_rsl.json",
        mime="application/json",
        use_container_width=True
    )

    uploaded_rules = st.file_uploader(
        "Importar Regras (JSON)",
        type=["json"],
        help="Carrega um conjunto de regras previamente salvo."
    )
    if uploaded_rules is not None:
        try:
            rules_data = json.load(uploaded_rules)
            if isinstance(rules_data, list) and all(isinstance(r, dict) and "id" in r and "pattern" in r for r in rules_data):
                st.session_state.rules = rules_data
                st.success("Regras importadas com sucesso!")
                st.rerun()
            else:
                st.error("Formato JSON de regras incompatível.")
        except Exception as e:
            st.error(f"Erro ao processar JSON: {e}")

    if st.button("🔄 Restaurar Regras Padrão", use_container_width=True):
        st.session_state.rules = json.loads(json.dumps(DEFAULT_RULES))
        st.success("Regras redefinidas para o padrão!")
        st.rerun()


# ── ABAS PRINCIPAIS ──────────────────────────────────────────────────────────
tab_regras, tab_execucao, tab_estatisticas = st.tabs([
    "🛠️ Configuração de Filtros & Regex",
    "⚡ Execução & Resultados",
    "📊 Estatísticas & PRISMA 2020"
])

# ── ABA 1: CONFIGURAÇÃO DE REGRAS & SANDBOX REGEX ─────────────────────────────
with tab_regras:
    st.subheader("Critérios de Inclusão e Exclusão")
    st.caption("Adicione, edite e teste expressões regulares para classificar seus artigos de forma automatizada.")

    # Resumo Geral das Regras Ativas
    if st.session_state.rules:
        summary_data = []
        for r in st.session_state.rules:
            summary_data.append({
                "ID": r["id"],
                "Nome": r["name"],
                "Tipo": "❌ Exclusão" if r["type"] == "exclusion" else "✅ Inclusão",
                "Campos de Busca": ", ".join(r.get("fields", [])),
                "Expressão Regular (Regex)": r.get("pattern", "")
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Nenhuma regra ativa configurada.")

    # 🧪 TESTADOR / PLAYGROUND DE REGEX EM TEMPO REAL
    with st.expander("🧪 Testador & Validador de Regex em Tempo Real", expanded=False):
        st.write("Teste como suas expressões regulares se comportam contra textos reais de títulos ou resumos.")
        
        c_sand1, c_sand2 = st.columns([1, 1])
        with c_sand1:
            teste_regex = st.text_input("Expressão Regular para Teste", value="procedural|pcg|survey")
            teste_tipo = st.radio("Tipo Simulado", ["Inclusão (Verde)", "Exclusão (Vermelho)"], horizontal=True)
        with c_sand2:
            texto_exemplo_padrao = "We present a survey on procedural content generation (PCG) in digital games."
            teste_texto = st.text_area("Texto de Amostra para Avaliação", value=texto_exemplo_padrao, height=85)

        if teste_regex:
            try:
                comp_pattern = re.compile(teste_regex, re.IGNORECASE | re.MULTILINE)
                ocorrencias = list(comp_pattern.finditer(teste_texto))
                
                st.success(f"✅ **Sintaxe Regex Válida!** Correspondências encontradas: **{len(ocorrencias)}**")
                
                # Destaca no texto do teste
                regra_fake = [{
                    "id": "TESTE",
                    "pattern": teste_regex,
                    "type": "exclusion" if "Exclusão" in teste_tipo else "inclusion",
                    "fields": ["mock"]
                }]
                texto_destacado = highlight_text(teste_texto, regra_fake, "mock")
                st.markdown(f"**Visualização com Destaque:**  \n{texto_destacado}", unsafe_allow_html=True)
                
            except re.error as err:
                st.error(f"❌ **Erro de Sintaxe na Regex:** `{err}`")

    st.markdown("---")

    # Editor de Regras Existentes
    st.markdown("#### 📝 Editar Critérios Ativos")
    rules_to_delete = []

    for i, rule in enumerate(st.session_state.rules):
        rule_id = rule["id"]
        rule_name = rule["name"]
        rule_type = rule["type"]
        rule_pattern = rule.get("pattern", "")
        rule_fields = rule.get("fields", ["title", "abstract", "author_keywords", "keywords"])

        tipo_icone = "❌ Exclusão" if rule_type == "exclusion" else "✅ Inclusão"
        with st.expander(f"📌 {rule_id}: {rule_name} ({tipo_icone})", expanded=False):
            c1, c2 = st.columns([1, 2])
            with c1:
                new_id = st.text_input("ID do Critério", value=rule_id, key=f"id_{i}")
                new_type = st.selectbox(
                    "Tipo de Ação",
                    options=["exclusion", "inclusion"],
                    format_func=lambda x: "❌ Exclusão (Se encontrar, descarta)" if x == "exclusion" else "✅ Inclusão (Se não encontrar, descarta)",
                    index=0 if rule_type == "exclusion" else 1,
                    key=f"type_{i}"
                )
            with c2:
                new_name = st.text_input("Nome Descritivo", value=rule_name, key=f"name_{i}")
                new_pattern = st.text_area("Expressão Regular (Regex)", value=rule_pattern, key=f"pattern_{i}", height=68)

            # Seleção de campos
            available_fields = ["title", "abstract", "author_keywords", "keywords"]
            for col in columns_list:
                if col not in available_fields:
                    available_fields.append(col)

            new_fields = st.multiselect(
                "Pesquisar nos Campos",
                options=available_fields,
                default=[f for f in rule_fields if f in available_fields],
                key=f"fields_{i}"
            )

            if st.button(f"🗑️ Excluir Critério {rule_id}", key=f"del_{i}", type="secondary"):
                rules_to_delete.append(i)

            st.session_state.rules[i]["id"] = new_id
            st.session_state.rules[i]["name"] = new_name
            st.session_state.rules[i]["type"] = new_type
            st.session_state.rules[i]["pattern"] = new_pattern
            st.session_state.rules[i]["fields"] = new_fields

    if rules_to_delete:
        for idx in sorted(rules_to_delete, reverse=True):
            st.session_state.rules.pop(idx)
        st.rerun()

    st.markdown("---")

    # Adicionar Novo Critério
    st.markdown("#### ➕ Criar Novo Critério")
    with st.form("add_rule_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            add_id = st.text_input("ID do Critério", placeholder="Ex: EX2 ou IN2")
        with c2:
            add_name = st.text_input("Nome", placeholder="Ex: Artigos Fora do Escopo Temporal")
        with c3:
            add_type = st.selectbox(
                "Tipo de Critério",
                options=["exclusion", "inclusion"],
                format_func=lambda x: "❌ Exclusão" if x == "exclusion" else "✅ Inclusão"
            )

        add_pattern = st.text_area("Expressão Regular (Regex)", placeholder="Ex: short paper|extended abstract|poster|workshop")

        available_fields = ["title", "abstract", "author_keywords", "keywords"]
        for col in columns_list:
            if col not in available_fields:
                available_fields.append(col)
        add_fields = st.multiselect("Campos de Busca", options=available_fields, default=["title", "abstract"])

        submitted = st.form_submit_button("➕ Salvar Novo Critério", use_container_width=True)
        if submitted:
            if not add_id.strip() or not add_name.strip() or not add_pattern.strip():
                st.error("Preencha o ID, Nome e Regex para cadastrar o critério.")
            else:
                new_rule = {
                    "id": add_id.strip(),
                    "name": add_name.strip(),
                    "type": add_type,
                    "pattern": add_pattern.strip(),
                    "fields": add_fields
                }
                st.session_state.rules.append(new_rule)
                st.success(f"Critério '{add_id}' cadastrado com sucesso!")
                st.rerun()


# ── ABA 2: EXECUÇÃO & RESULTADOS ─────────────────────────────────────────────
with tab_execucao:
    st.subheader("Processamento da Triagem")

    if df_uploaded is None:
        st.info("💡 Carregue uma planilha Excel ou CSV no painel lateral à esquerda para iniciar.")
    else:
        if st.button("⚡ Executar Triagem Automática", type="primary", use_container_width=True):
            with st.spinner("Processando e classificando artigos..."):
                try:
                    resultado = executar_triagem(
                        df=df_uploaded,
                        rules=st.session_state.rules,
                        remover_duplicatas=remover_duplicatas,
                        coluna_dedup=coluna_dedup,
                        estrategia_doi=estrategia_doi
                    )
                    st.session_state.resultados = resultado
                    st.success("✅ Triagem concluída com sucesso!")
                except Exception as e:
                    st.error(f"Erro no processamento da triagem: {e}")

        # Exibição dos Resultados
        if st.session_state.resultados is not None:
            res = st.session_state.resultados
            stats = res["stats"]
            aprovados = res["aprovados"]
            rejeitados = res["rejeitados"]

            st.markdown("---")

            # ── Indicadores Métricos com Porcentagens ──
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            col_m1.metric("Total Inicial", stats["total_inicial"])
            col_m2.metric("Duplicatas", stats["duplicatas_removidas"])

            if estrategia_doi == "remove":
                col_m3.metric("Sem DOI (Excluídos)", stats["sem_doi"])
            else:
                col_m3.metric("Sem DOI (Marcados)", stats["sem_doi_flagged"])

            col_m4.metric(
                "Aprovados",
                stats["aprovados"],
                delta=f"{stats.get('taxa_aprovacao_pct', 0)}% do total",
                delta_color="normal"
            )
            col_m5.metric(
                "Rejeitados",
                stats["rejeitados"],
                delta=f"{stats.get('taxa_rejeicao_pct', 0)}% do total",
                delta_color="inverse"
            )

            st.markdown("---")

            # ── Botões de Exportação ──
            st.subheader("📥 Exportar Relatórios")
            
            # Botão de Destaque: Pacote Completo Multi-Abas
            multi_excel_data = gerar_pacote_completo_excel(aprovados, rejeitados, stats, st.session_state.rules)
            st.download_button(
                label="📦 Baixar Relatório Completo Multi-Abas (Excel .xlsx)",
                data=multi_excel_data,
                file_name="triagem_rsl_consolidada_prisma.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                excel_ap = converter_df_para_excel(aprovados)
                st.download_button(
                    label="🟢 Baixar Apenas APROVADOS (Excel)",
                    data=excel_ap,
                    file_name="artigos_aprovados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with c_d2:
                excel_rej = converter_df_para_excel(rejeitados)
                st.download_button(
                    label="🔴 Baixar Apenas REJEITADOS (Excel)",
                    data=excel_rej,
                    file_name="artigos_rejeitados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("---")

            # ── Tabelas de Visualização ──
            st.subheader("📋 Artigos Aprovados")
            if not aprovados.empty:
                st.dataframe(aprovados, use_container_width=True)
            else:
                st.info("Nenhum artigo aprovado com as regras atuais.")

            st.subheader("📋 Artigos Rejeitados")
            if not rejeitados.empty:
                # Filtro dinâmico por motivo de rejeição
                motivos_unicos = ["(Todos os Motivos)"]
                for r in st.session_state.rules:
                    motivos_unicos.append(r["id"])
                    
                filtro_motivo = st.selectbox("Filtrar Tabela por Critério Violado:", options=motivos_unicos)
                if filtro_motivo != "(Todos os Motivos)":
                    df_rej_view = rejeitados[rejeitados["motivo_rejeicao"].str.contains(filtro_motivo, na=False)]
                else:
                    df_rej_view = rejeitados
                    
                st.dataframe(df_rej_view, use_container_width=True)
            else:
                st.info("Nenhum artigo rejeitado.")

            st.markdown("---")

            # ── Inspetor Detalhado de Artigos ──
            st.subheader("🔍 Inspetor & Diagnóstico Individual de Artigo")
            st.caption("Selecione um artigo para auditar a ativação de cada critério e visualizar as correspondências no texto.")

            ap_temp = aprovados.copy()
            ap_temp["status"] = "APROVADO"
            ap_temp["motivo_rejeicao"] = ""

            rej_temp = rejeitados.copy()
            rej_temp["status"] = "REJEITADO"

            df_total = pd.concat([ap_temp, rej_temp], ignore_index=True)

            if not df_total.empty:
                options_list = df_total.index.tolist()
                def obter_label(idx):
                    row_item = df_total.loc[idx]
                    status = row_item["status"]
                    title = str(row_item.get("title", "Sem Título"))
                    short_title = title[:95] + "..." if len(title) > 95 else title
                    icon = "🟢" if status == "APROVADO" else "🔴"
                    return f"{icon} [{status}] {short_title}"

                artigo_selecionado = st.selectbox(
                    "Selecione o artigo para inspeção:",
                    options=options_list,
                    format_func=obter_label
                )

                if artigo_selecionado is not None:
                    row = df_total.loc[artigo_selecionado]
                    status_val = row["status"]

                    with st.container(border=True):
                        c_stat, c_info = st.columns([1, 4])
                        with c_stat:
                            if status_val == "APROVADO":
                                st.markdown('<div class="badge-approved">🟢 APROVADO</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="badge-rejected">🔴 REJEITADO</div>', unsafe_allow_html=True)

                        st.markdown(f"### {row.get('title', 'Sem Título')}")

                        # Metadados
                        c_auth, c_year, c_doi = st.columns(3)
                        c_auth.write(f"**Autor(es):** {row.get('author', 'N/A')}")
                        c_year.write(f"**Ano:** {row.get('year', 'N/A')}")
                        c_doi.write(f"**DOI:** {row.get('doi', 'N/A')}")

                        st.markdown("---")
                        st.markdown("#### 📋 Auditoria das Regras")

                        for r in st.session_state.rules:
                            r_id = r["id"]
                            r_name = r["name"]
                            r_type = r["type"]
                            r_fields = r.get("fields", ["title", "abstract", "author_keywords", "keywords"])

                            existing_fields = [f for f in r_fields if f in row.index]
                            consolidated = " ".join([str(row[f]) for f in existing_fields if pd.notna(row[f])])

                            pattern_str = r.get("pattern", "")
                            matched = False
                            if pattern_str.strip():
                                try:
                                    pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
                                    matched = bool(pattern.search(consolidated))
                                except Exception:
                                    pass

                            if r_type == "exclusion":
                                if matched:
                                    st.error(f"❌ **{r_id} - {r_name}** (Exclusão): **VIOLADO** (Termos de descarte detectados)")
                                else:
                                    st.success(f"✅ **{r_id} - {r_name}** (Exclusão): **PASSOU** (Nenhum termo indesejado)")
                            else:
                                if matched:
                                    st.success(f"✅ **{r_id} - {r_name}** (Inclusão): **PASSOU** (Termos obrigatórios encontrados)")
                                else:
                                    st.error(f"❌ **{r_id} - {r_name}** (Inclusão): **VIOLADO** (Termos obrigatórios ausentes)")

                        st.markdown("---")
                        st.markdown("#### 📄 Destaque Visual nos Campos de Texto")

                        h_title = highlight_text(str(row.get("title", "")), st.session_state.rules, "title")
                        st.markdown(f"**Título:**  \n{h_title}", unsafe_allow_html=True)
                        st.write("")

                        if "abstract" in row.index and pd.notna(row["abstract"]):
                            h_abstract = highlight_text(str(row["abstract"]), st.session_state.rules, "abstract")
                            st.markdown(f"**Resumo (Abstract):**  \n<div style='text-align: justify; border-left: 3px solid #3b82f6; padding-left: 12px; margin-top: 4px;'>{h_abstract}</div>", unsafe_allow_html=True)
                            st.write("")

                        if "keywords" in row.index and pd.notna(row["keywords"]):
                            h_kw = highlight_text(str(row["keywords"]), st.session_state.rules, "keywords")
                            st.markdown(f"**Palavras-chave:** {h_kw}", unsafe_allow_html=True)

                        if "author_keywords" in row.index and pd.notna(row["author_keywords"]):
                            h_akw = highlight_text(str(row["author_keywords"]), st.session_state.rules, "author_keywords")
                            st.markdown(f"**Palavras-chave do Autor:** {h_akw}", unsafe_allow_html=True)


# ── ABA 3: ESTATÍSTICAS & FLUXO PRISMA 2020 ──────────────────────────────────
with tab_estatisticas:
    st.subheader("Relatório e Diagrama de Fluxo PRISMA 2020")
    st.caption("Visão analítica da retenção e descarte de artigos para inclusão direta em sua publicação científica.")

    if st.session_state.resultados is None:
        st.info("💡 Execute a triagem na aba 'Execução & Resultados' para carregar as métricas e o fluxo PRISMA.")
    else:
        res = st.session_state.resultados
        stats = res["stats"]

        # ── GRÁFICO INTERATIVO DE FLUXO PRISMA (FUNIL) ──
        st.markdown("### 📊 Funil de Seleção PRISMA")
        
        funnel_labels = [
            f"1. Total Bruto ({stats['total_inicial']})",
            f"2. Pós-Deduplicação ({stats['total_inicial'] - stats['duplicatas_removidas']})",
            f"3. Elegibilidade ({stats['pos_limpeza']})",
            f"4. Aprovados ({stats['aprovados']})"
        ]
        funnel_values = [
            stats["total_inicial"],
            stats["total_inicial"] - stats["duplicatas_removidas"],
            stats["pos_limpeza"],
            stats["aprovados"]
        ]

        fig_funnel = go.Figure(go.Funnel(
            y=funnel_labels,
            x=funnel_values,
            textinfo="value+percent initial",
            marker={
                "color": ["#3b82f6", "#6366f1", "#8b5cf6", "#10b981"]
            }
        ))
        fig_funnel.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

        st.markdown("---")

        c_g1, c_g2 = st.columns([1, 1])

        with c_g1:
            st.markdown("#### 🎯 Distribuição Final")
            fig_pie = px.pie(
                values=[stats["aprovados"], stats["rejeitados"]],
                names=["Aprovados", "Rejeitados"],
                color=["Aprovados", "Rejeitados"],
                color_discrete_map={"Aprovados": "#10b981", "Rejeitados": "#ef4444"},
                hole=0.45
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_g2:
            st.markdown("#### 🚫 Impacto por Critério")
            motivos_lista = []
            for rule in st.session_state.rules:
                r_id = rule["id"]
                r_name = rule["name"]
                count = stats["regra_stats"].get(r_id, 0)
                motivos_lista.append({
                    "Critério": f"{r_id}",
                    "Nome": r_name,
                    "Descartes": count
                })
            df_motivos = pd.DataFrame(motivos_lista)
            if not df_motivos.empty and df_motivos["Descartes"].sum() > 0:
                fig_bar = px.bar(
                    df_motivos,
                    x="Critério",
                    y="Descartes",
                    hover_data=["Nome"],
                    color="Descartes",
                    color_continuous_scale="Reds"
                )
                fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Nenhum descarte por critério registrado.")

        # Relatório Textual Formatado
        st.markdown("---")
        st.markdown("#### 📋 Relatório PRISMA 2020 Formatado para Cópia")

        linhas_relatorio = [
            "============================================================",
            "RELATÓRIO DE TRIAGEM AUTOMÁTICA – FLUXO PRISMA 2020",
            "============================================================",
            f"1. Identificação Inicial   : {stats['total_inicial']} artigos",
            f"2. Duplicatas Removidas    : {stats['duplicatas_removidas']} artigos",
            f"3. Excluídos Sem DOI       : {stats['sem_doi']} artigos",
            f"4. Sinalizados Sem DOI     : {stats['sem_doi_flagged']} artigos",
            f"5. Elegibilidade Avaliada  : {stats['pos_limpeza']} artigos",
            "------------------------------------------------------------",
            "CRITÉRIOS DE DESCARTE:"
        ]

        for rule in st.session_state.rules:
            r_id = rule["id"]
            r_name = rule["name"]
            r_type = rule["type"]
            count = stats["regra_stats"].get(r_id, 0)
            prefix = "Com Exclusão" if r_type == "exclusion" else "Sem Inclusão"
            linhas_relatorio.append(f"  - {prefix} {r_id} ({r_name}): {count} artigos")

        linhas_relatorio.extend([
            "============================================================",
            f"TOTAL INCLUÍDOS / APROVADOS: {stats['aprovados']} ({stats.get('taxa_aprovacao_pct', 0)}%)",
            f"TOTAL EXCLUÍDOS / REJEITADOS: {stats['rejeitados']} ({stats.get('taxa_rejeicao_pct', 0)}%)",
            "============================================================"
        ])

        st.text_area(
            "Copie o sumário abaixo para o protocolo ou relatório da RSL:",
            value="\n".join(linhas_relatorio),
            height=300
        )
