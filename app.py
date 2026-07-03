import streamlit as st
import pandas as pd
import json
import io
import re
import os
from triagem_rsl import executar_triagem, DEFAULT_RULES, COLS_SAIDA

# Configurações da página
st.set_page_config(
    page_title="Triador RSL Parsifal",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de CSS customizado para polimento visual
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1f4068, #162447);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    .rule-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        background-color: #fafafa;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    /* Suporte a Tema Escuro do Streamlit */
    @media (prefers-color-scheme: dark) {
        .rule-card {
            background-color: #1e222b;
            border-color: #2e3440;
        }
    }
</style>
""", unsafe_allow_html=True)

# Inicializa as regras na sessão se não existirem
if "rules" not in st.session_state:
    # Cópia profunda simples para evitar referenciar o DEFAULT_RULES original
    st.session_state.rules = json.loads(json.dumps(DEFAULT_RULES))

if "resultados" not in st.session_state:
    st.session_state.resultados = None

# Interface do App
st.markdown('<div class="main-header">🔍 Triador Automático de RSL</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Customize regras, filtre duplicatas/DOI e gere relatórios de triagem para o Parsifal de forma interativa.</div>', unsafe_allow_html=True)

# ── PAINEL LATERAL ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações Gerais")
    
    # 1. Upload da Planilha do Parsifal
    st.subheader("1. Base de Artigos")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel do Parsifal (.xlsx)",
        type=["xlsx"],
        help="Planilha contendo os artigos exportados do Parsifal."
    )
    
    # Ler colunas do arquivo se carregado
    columns_list = []
    df_uploaded = None
    if uploaded_file is not None:
        try:
            # Carrega apenas o cabeçalho para ser rápido
            df_header = pd.read_excel(uploaded_file, nrows=0)
            columns_list = df_header.columns.tolist()
            # Carrega todo o dataframe
            uploaded_file.seek(0)
            df_uploaded = pd.read_excel(uploaded_file)
            st.success(f"Arquivo carregado! ({len(df_uploaded)} artigos)")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
            
    # 2. Configurações de Limpeza
    st.subheader("2. Opções de Limpeza")
    remover_duplicatas = st.checkbox("Remover Duplicatas", value=True)
    
    coluna_dedup = "title"
    if remover_duplicatas:
        default_idx = columns_list.index("title") if "title" in columns_list else 0
        coluna_dedup = st.selectbox(
            "Coluna para Deduplicação",
            options=columns_list if columns_list else ["title"],
            index=default_idx
        )
        
    estrategia_doi = st.selectbox(
        "Filtro de DOI",
        options=["remove", "flag", "ignore"],
        format_func=lambda x: {
            "remove": "❌ Remover artigos sem DOI",
            "flag": "⚠️ Apenas sinalizar/marcar sem DOI",
            "ignore": "⚙️ Ignorar filtro de DOI"
        }.get(x, x),
        index=0,
        help="Define se artigos sem DOI serão excluídos ou apenas sinalizados no relatório final."
    )
    
    # 3. Exportar/Importar Configuração de Regras
    st.subheader("3. Perfil de Regras")
    
    # Download das regras atuais
    rules_json_str = json.dumps(st.session_state.rules, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Exportar Regras (JSON)",
        data=rules_json_str,
        file_name="regras_triagem_rsl.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Upload para sobrescrever regras atuais
    uploaded_rules = st.file_uploader(
        "Importar Regras (JSON)",
        type=["json"],
        help="Substitui as regras ativas na interface por uma configuração salva previamente."
    )
    if uploaded_rules is not None:
        try:
            rules_data = json.load(uploaded_rules)
            # Validação simples
            if isinstance(rules_data, list) and all(isinstance(r, dict) and "id" in r and "pattern" in r for r in rules_data):
                st.session_state.rules = rules_data
                st.success("Regras carregadas com sucesso!")
                st.rerun()
            else:
                st.error("Formato do JSON de regras inválido.")
        except Exception as e:
            st.error(f"Erro ao ler regras: {e}")

    # Resetar regras
    if st.button("🔄 Resetar para Regras Padrão", use_container_width=True):
        st.session_state.rules = json.loads(json.dumps(DEFAULT_RULES))
        st.success("Regras resetadas!")
        st.rerun()

# ── PAINEL PRINCIPAL (TABS) ──────────────────────────────────────────────────
tab_regras, tab_execucao, tab_estatisticas = st.tabs([
    "🛠️ Configuração de Filtros", 
    "⚡ Execução & Resultados", 
    "📊 Estatísticas & Relatório"
])

# ── TAB 1: CONFIGURAÇÃO DE REGRAS ──────────────────────────────────────────
with tab_regras:
    st.subheader("Gerenciar Critérios de Inclusão e Exclusão")
    st.write("Abaixo você pode editar as expressões regulares (regex) de cada regra, seu tipo e em quais colunas realizar a busca.")
    
    # Formato do editor de regras
    rules_to_delete = []
    
    for i, rule in enumerate(st.session_state.rules):
        rule_id = rule["id"]
        rule_name = rule["name"]
        rule_type = rule["type"]
        rule_pattern = rule["pattern"]
        rule_fields = rule.get("fields", ["title", "abstract", "author_keywords", "keywords"])
        
        with st.expander(f"📝 {rule_id}: {rule_name} ({'Inclusão' if rule_type == 'inclusion' else 'Exclusão'})", expanded=False):
            # Usando colunas para organizar o formulário da regra
            c1, c2 = st.columns([1, 3])
            
            with c1:
                new_id = st.text_input(f"ID da Regra", value=rule_id, key=f"id_{i}")
                new_type = st.selectbox(
                    f"Tipo da Regra",
                    options=["exclusion", "inclusion"],
                    format_func=lambda x: "❌ Exclusão (Se achar, rejeita)" if x == "exclusion" else "✅ Inclusão (Se não achar, rejeita)",
                    index=0 if rule_type == "exclusion" else 1,
                    key=f"type_{i}"
                )
            
            with c2:
                new_name = st.text_input(f"Nome da Regra", value=rule_name, key=f"name_{i}")
                new_pattern = st.text_area(f"Expressão Regular (Regex)", value=rule_pattern, key=f"pattern_{i}", height=68)
                
            # Seleção de campos
            available_fields = ["title", "abstract", "author_keywords", "keywords"]
            # Adiciona colunas do upload se disponíveis
            for col in columns_list:
                if col not in available_fields:
                    available_fields.append(col)
                    
            new_fields = st.multiselect(
                f"Pesquisar nos Campos",
                options=available_fields,
                default=[f for f in rule_fields if f in available_fields],
                key=f"fields_{i}"
            )
            
            # Botão para deletar a regra
            if st.button(f"🗑️ Excluir Regra {rule_id}", key=f"del_{i}", type="secondary"):
                rules_to_delete.append(i)
                
            # Atualiza o estado da sessão imediatamente
            st.session_state.rules[i]["id"] = new_id
            st.session_state.rules[i]["name"] = new_name
            st.session_state.rules[i]["type"] = new_type
            st.session_state.rules[i]["pattern"] = new_pattern
            st.session_state.rules[i]["fields"] = new_fields
            
    # Processa deleções
    if rules_to_delete:
        for idx in sorted(rules_to_delete, reverse=True):
            st.session_state.rules.pop(idx)
        st.rerun()
        
    st.markdown("---")
    
    # Adicionar Nova Regra
    st.subheader("➕ Adicionar Novo Critério")
    with st.form("add_rule_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            add_id = st.text_input("ID da Regra", placeholder="Ex: EC5")
        with c2:
            add_name = st.text_input("Nome Descritivo", placeholder="Ex: Foco em Outras Plataformas")
        with c3:
            add_type = st.selectbox(
                "Tipo de Critério", 
                options=["exclusion", "inclusion"],
                format_func=lambda x: "❌ Exclusão" if x == "exclusion" else "✅ Inclusão"
            )
            
        add_pattern = st.text_area("Expressão Regular (Regex)", placeholder="Ex: mobile|android|ios|webgl")
        
        # Campos de busca padrão
        available_fields = ["title", "abstract", "author_keywords", "keywords"]
        for col in columns_list:
            if col not in available_fields:
                available_fields.append(col)
        add_fields = st.multiselect("Campos de Busca", options=available_fields, default=["title", "abstract"])
        
        submitted = st.form_submit_button("Adicionar Regra")
        if submitted:
            if not add_id or not add_name or not add_pattern:
                st.error("Por favor, preencha o ID, Nome e Regex para adicionar uma nova regra.")
            else:
                new_rule = {
                    "id": add_id,
                    "name": add_name,
                    "type": add_type,
                    "pattern": add_pattern,
                    "fields": add_fields
                }
                st.session_state.rules.append(new_rule)
                st.success(f"Regra {add_id} adicionada com sucesso!")
                st.rerun()

# ── TAB 2: EXECUÇÃO & RESULTADOS ──────────────────────────────────────────
with tab_execucao:
    st.subheader("Processar Artigos")
    
    if df_uploaded is None:
        st.info("💡 Por favor, faça o upload de uma planilha Excel na barra lateral para iniciar.")
    else:
        if st.button("⚡ Executar Triagem Automática", type="primary", use_container_width=True):
            with st.spinner("Processando triagem..."):
                try:
                    resultado = executar_triagem(
                        df=df_uploaded,
                        rules=st.session_state.rules,
                        remover_duplicatas=remover_duplicatas,
                        coluna_dedup=coluna_dedup,
                        estrategia_doi=estrategia_doi
                    )
                    st.session_state.resultados = resultado
                    st.success("Triagem concluída com sucesso!")
                except Exception as e:
                    st.error(f"Erro durante o processamento da triagem: {e}")
                    
        # Exibe resultados se já houver processamento
        if st.session_state.resultados is not None:
            res = st.session_state.resultados
            stats = res["stats"]
            aprovados = res["aprovados"]
            rejeitados = res["rejeitados"]
            
            # ── Indicadores Métricos ──
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            col_m1.metric("Total Inicial", stats["total_inicial"])
            col_m2.metric("Duplicatas Removidas", stats["duplicatas_removidas"])
            
            if estrategia_doi == "remove":
                col_m3.metric("Removidos sem DOI", stats["sem_doi"])
            else:
                col_m3.metric("Sinalizados sem DOI", stats["sem_doi_flagged"])
                
            col_m4.metric("Aprovados", stats["aprovados"], delta=f"{stats['aprovados'] - stats['total_inicial']}", delta_color="inverse")
            col_m5.metric("Rejeitados", stats["rejeitados"])
            
            st.markdown("---")
            
            # ── Botões de Download ──
            st.subheader("📥 Baixar Resultados")
            col_d1, col_d2 = st.columns(2)
            
            # Gerar Excel em memória para os Aprovados
            towrite_ap = io.BytesIO()
            aprovados.to_excel(towrite_ap, index=False)
            towrite_ap.seek(0)
            
            col_d1.download_button(
                label="🟢 Baixar Artigos APROVADOS (Excel)",
                data=towrite_ap,
                file_name="aprovados_triagem.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Gerar Excel em memória para os Rejeitados
            towrite_rej = io.BytesIO()
            rejeitados.to_excel(towrite_rej, index=False)
            towrite_rej.seek(0)
            
            col_d2.download_button(
                label="🔴 Baixar Artigos REJEITADOS (Excel)",
                data=towrite_rej,
                file_name="rejeitados_triagem.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # ── Visualização das Tabelas ──
            st.subheader("📋 Artigos Aprovados")
            if not aprovados.empty:
                st.dataframe(aprovados, use_container_width=True)
            else:
                st.write("Nenhum artigo aprovado.")
                
            st.subheader("📋 Artigos Rejeitados")
            if not rejeitados.empty:
                st.dataframe(rejeitados, use_container_width=True)
            else:
                st.write("Nenhum artigo rejeitado.")

# ── TAB 3: ESTATÍSTICAS & RELATÓRIO ───────────────────────────────────────
with tab_estatisticas:
    st.subheader("Relatório Analítico")
    
    if st.session_state.resultados is None:
        st.info("💡 Execute a triagem na aba 'Execução & Resultados' para visualizar estatísticas de exclusão.")
    else:
        res = st.session_state.resultados
        stats = res["stats"]
        
        c1, c2 = st.columns([2, 3])
        
        with c1:
            st.subheader("📊 Distribuição de Artigos")
            
            df_pizza = pd.DataFrame({
                "Aprovados": [stats["aprovados"]],
                "Rejeitados": [stats["rejeitados"]]
            }, index=["Quantidade"])
            
            # Gráfico de barras simples usando Streamlit nativo
            st.bar_chart(df_pizza, color=["#4CAF50", "#F44336"])
            
        with c2:
            st.subheader("📊 Motivos de Exclusão")
            st.write("Contagem de artigos afetados por cada critério (inclusão ausente ou exclusão correspondida):")
            
            # Montar DataFrame dos motivos
            motivos_lista = []
            for rule in st.session_state.rules:
                rule_id = rule["id"]
                rule_name = rule["name"]
                count = stats["regra_stats"].get(rule_id, 0)
                motivos_lista.append({
                    "Critério": f"{rule_id} - {rule_name}",
                    "Artigos Afetados": count
                })
                
            df_motivos = pd.DataFrame(motivos_lista)
            st.dataframe(df_motivos, hide_index=True, use_container_width=True)
            
            # Gráfico de barras horizontais
            if not df_motivos.empty and df_motivos["Artigos Afetados"].sum() > 0:
                st.bar_chart(df_motivos.set_index("Critério"), y="Artigos Afetados")
                
        # Relatório em formato de texto para copiar
        st.markdown("---")
        st.subheader("📋 Relatório Textual para Copiar")
        
        # Montar string do relatório
        linhas_relatorio = []
        linhas_relatorio.append("============================================================")
        linhas_relatorio.append("RELATÓRIO DE TRIAGEM AUTOMÁTICA – RSL")
        linhas_relatorio.append("============================================================")
        linhas_relatorio.append(f"  Total inicial            : {stats['total_inicial']}")
        linhas_relatorio.append(f"  Duplicatas removidas     : {stats['duplicatas_removidas']}")
        
        if estrategia_doi == "remove":
            linhas_relatorio.append(f"  Removidos sem DOI        : {stats['sem_doi']}")
        else:
            linhas_relatorio.append(f"  Sinalizados sem DOI      : {stats['sem_doi_flagged']}")
            
        linhas_relatorio.append(f"  Pós-limpeza (triagem)    : {stats['pos_limpeza']}")
        linhas_relatorio.append("-" * 60)
        
        for rule in st.session_state.rules:
            rule_id = rule["id"]
            rule_name = rule["name"]
            rule_type = rule["type"]
            count = stats["regra_stats"].get(rule_id, 0)
            prefix = "  Com" if rule_type == "exclusion" else "  Sem"
            linhas_relatorio.append(f"{prefix:<27} ({rule_id}): {count}")
            
        linhas_relatorio.append("============================================================")
        linhas_relatorio.append(f"  TOTAL APROVADOS          : {stats['aprovados']}")
        linhas_relatorio.append(f"  TOTAL REJEITADOS         : {stats['rejeitados']}")
        linhas_relatorio.append("============================================================")
        
        relatorio_texto = "\n".join(linhas_relatorio)
        
        st.text_area(
            "Selecione e copie as estatísticas abaixo:",
            value=relatorio_texto,
            height=320,
            disabled=True
        )
