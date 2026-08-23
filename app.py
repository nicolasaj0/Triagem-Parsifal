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
    page_title="Triador RSL — Mesa de Revisão Científica",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ── DESIGN SYSTEM CENTRALIZADO: MESA DE REVISÃO CIENTÍFICA ───────────────────
def inject_custom_css():
    st.markdown("""
    <style>
        /* ── IMPORTAÇÃO DA FAMÍLIA IBM PLEX COMPLETA ── */
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap');

        /* ── TOKENS DO DESIGN SYSTEM (MESA DE REVISÃO) ── */
        :root {
            --desk-bg: #171310;
            --paper-surface: #211C16;
            --paper-surface-hover: #2B241C;
            --card-border: #38301F;
            --card-border-subtle: #2C251B;
            --card-border-focus: #8FB0D1;

            --text-primary: #EDE7DB;
            --text-muted: #A89C8A;
            --text-dim: #7A6F5F;

            --ink-approved-strong: #2F5A42;
            --ink-approved-text: #8FBF9E;
            --ink-approved-bg: rgba(47, 90, 66, 0.28);
            --ink-approved-border: rgba(143, 191, 158, 0.45);

            --ink-rejected-strong: #7A2E28;
            --ink-rejected-text: #DF978B;
            --ink-rejected-bg: rgba(122, 46, 40, 0.28);
            --ink-rejected-border: rgba(223, 151, 139, 0.45);

            --ink-accent-strong: #2E4A6B;
            --ink-accent-text: #8FB0D1;
            --ink-accent-bg: rgba(46, 74, 107, 0.32);
            --ink-accent-border: rgba(143, 176, 209, 0.45);

            --sp-1: 4px;
            --sp-2: 8px;
            --sp-3: 12px;
            --sp-4: 16px;
            --sp-5: 24px;
            --sp-6: 32px;

            --radius-sm: 2px;
            --radius-md: 4px;
        }

        /* ── RESET TIPOGRÁFICO & BASE ── */
        html, body, [class*="css"], .stMarkdown, .stText, p, span, label, li {
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: var(--text-primary);
        }

        code, pre, kbd, samp {
            font-family: 'IBM Plex Mono', monospace !important;
        }

        /* ── ACESSIBILIDADE: ESTADO DE FOCO VISÍVEL VIA TECLADO ── */
        button:focus-visible,
        input:focus-visible,
        select:focus-visible,
        textarea:focus-visible,
        [tabindex="0"]:focus-visible,
        [data-baseweb="tab"]:focus-visible,
        [data-baseweb="select"]:focus-visible {
            outline: 2px solid var(--ink-accent-text) !important;
            outline-offset: 2px !important;
        }

        /* ── CABEÇALHO INSTITUCIONAL ── */
        .brand-container {
            display: flex;
            align-items: flex-start;
            gap: var(--sp-4);
            padding: var(--sp-3) 0 var(--sp-4) 0;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: var(--sp-5);
        }

        .brand-icon-box {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
            background: var(--paper-surface);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            color: var(--ink-accent-text);
            flex-shrink: 0;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }

        .brand-title {
            font-family: 'IBM Plex Serif', Georgia, serif !important;
            font-size: 1.85rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin: 0;
        }

        .brand-subtitle {
            font-size: 0.92rem;
            color: var(--text-muted);
            margin-top: var(--sp-1);
            line-height: 1.4;
        }

        .brand-badge {
            display: inline-flex;
            align-items: center;
            gap: var(--sp-1);
            background: var(--ink-accent-bg);
            border: 1px solid var(--ink-accent-border);
            color: var(--ink-accent-text);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            margin-left: var(--sp-2);
            vertical-align: middle;
        }

        /* ── SIDEBAR: TRILHA DE PROGRESSO VERTICAL ── */
        section[data-testid="stSidebar"] {
            background-color: var(--desk-bg) !important;
            border-right: 1px solid var(--card-border) !important;
        }

        .sidebar-header {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: var(--sp-2);
            padding-bottom: var(--sp-3);
            border-bottom: 1px solid var(--card-border);
            margin-bottom: var(--sp-4);
        }

        .trail-step-header {
            display: flex;
            align-items: center;
            gap: var(--sp-3);
            margin-top: var(--sp-3);
            margin-bottom: var(--sp-2);
        }

        .trail-step-badge {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: var(--paper-surface);
            border: 1.5px solid var(--card-border);
            color: var(--text-muted);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.75rem;
            font-weight: 700;
            flex-shrink: 0;
        }

        .trail-step-badge.active {
            border-color: var(--ink-accent-text);
            color: var(--ink-accent-text);
            background: var(--ink-accent-bg);
        }

        .trail-step-badge.done {
            border-color: var(--ink-approved-text);
            color: var(--ink-approved-text);
            background: var(--ink-approved-bg);
        }

        .trail-step-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }

        .trail-divider {
            height: 1px;
            background: var(--card-border);
            margin: var(--sp-4) 0;
        }

        /* ── ABAS EM FORMATO DE PASTAS DE DOSSIÊ SUSPENSAS ── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px !important;
            background-color: transparent !important;
            border-bottom: 1px solid var(--card-border) !important;
            padding-bottom: 0px !important;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: var(--desk-bg) !important;
            border: 1px solid var(--card-border) !important;
            border-bottom: 1px solid var(--card-border) !important;
            border-radius: 4px 4px 0 0 !important;
            padding: 8px 18px !important;
            color: var(--text-muted) !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            transition: all 0.15s ease-in-out !important;
            margin-bottom: -1px !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: var(--text-primary) !important;
            background-color: var(--paper-surface-hover) !important;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: var(--paper-surface) !important;
            color: var(--text-primary) !important;
            border-top: 2px solid var(--ink-accent-text) !important;
            border-bottom: 1px solid var(--paper-surface) !important;
            font-weight: 600 !important;
        }

        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        .stTabs [data-baseweb="tab-panel"] {
            padding-top: var(--sp-4) !important;
        }

        /* ── CARDS DE INDICADORES DE MÉTRICAS (PAINEL DE SCREENING) ── */
        .metric-grid-card {
            background: var(--paper-surface);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: var(--sp-3) var(--sp-4);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .metric-card-secondary {
            border-left: 3px solid var(--card-border);
        }

        .metric-card-approved {
            border: 1px solid var(--ink-approved-border);
            border-left: 4px solid var(--ink-approved-text);
            background: linear-gradient(180deg, var(--ink-approved-bg) 0%, var(--paper-surface) 100%);
        }

        .metric-card-rejected {
            border: 1px solid var(--ink-rejected-border);
            border-left: 4px solid var(--ink-rejected-text);
            background: linear-gradient(180deg, var(--ink-rejected-bg) 0%, var(--paper-surface) 100%);
        }

        .metric-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: var(--sp-1);
        }

        .metric-value-mono {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.1;
            font-variant-numeric: tabular-nums;
        }

        .metric-delta-tag {
            display: inline-flex;
            align-items: center;
            gap: var(--sp-1);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: var(--sp-2);
            padding: 1px 6px;
            border-radius: var(--radius-sm);
            width: fit-content;
        }

        .metric-delta-approved {
            background: var(--ink-approved-bg);
            color: var(--ink-approved-text);
            border: 1px solid var(--ink-approved-border);
        }

        .metric-delta-rejected {
            background: var(--ink-rejected-bg);
            color: var(--ink-rejected-text);
            border: 1px solid var(--ink-rejected-border);
        }

        /* ── CARIMBO DE DECISÃO EDITORIAL (ELEMENTO DE ASSINATURA) ── */
        .audit-stamp {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'IBM Plex Sans', sans-serif;
            text-transform: uppercase;
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            padding: 5px 12px;
            border-radius: var(--radius-sm);
            user-select: none;
            line-height: 1;
        }

        .audit-stamp-approved {
            color: var(--ink-approved-text);
            background: var(--ink-approved-bg);
            border: 1.5px solid var(--ink-approved-text);
            box-shadow: inset 0 0 0 1px var(--ink-approved-bg), 0 1px 3px rgba(0, 0, 0, 0.4);
            transform: rotate(-1.5deg);
        }

        .audit-stamp-rejected {
            color: var(--ink-rejected-text);
            background: var(--ink-rejected-bg);
            border: 1.5px solid var(--ink-rejected-text);
            box-shadow: inset 0 0 0 1px var(--ink-rejected-bg), 0 1px 3px rgba(0, 0, 0, 0.4);
            transform: rotate(1.5deg);
        }

        /* ── FICHA CATALOGRÁFICA (INSPETOR DE ARTIGO) ── */
        .catalog-card {
            background: var(--paper-surface);
            border: 1px solid var(--card-border);
            border-left: 4px solid var(--ink-accent-text);
            border-radius: var(--radius-md);
            padding: var(--sp-4) var(--sp-5);
            margin-top: var(--sp-3);
            margin-bottom: var(--sp-4);
        }

        .catalog-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: var(--sp-3);
            margin-bottom: var(--sp-3);
        }

        .catalog-article-title {
            font-family: 'IBM Plex Serif', Georgia, serif;
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.35;
            margin: 0;
        }

        .catalog-meta-strip {
            display: flex;
            flex-wrap: wrap;
            gap: var(--sp-4);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            padding: var(--sp-2) 0;
            border-top: 1px solid var(--card-border-subtle);
            border-bottom: 1px solid var(--card-border-subtle);
            margin: var(--sp-3) 0;
        }

        .catalog-meta-item strong {
            color: var(--text-primary);
            font-weight: 600;
        }

        /* ── CHECKLIST COMPACTO DE AUDITORIA ── */
        .audit-checklist {
            display: flex;
            flex-direction: column;
            gap: var(--sp-2);
            margin: var(--sp-3) 0;
        }

        .audit-check-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sp-2) var(--sp-3);
            background: var(--desk-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-sm);
            font-size: 0.88rem;
        }

        .audit-check-left {
            display: flex;
            align-items: center;
            gap: var(--sp-2);
        }

        .audit-rule-code {
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 700;
            font-size: 0.78rem;
            padding: 1px 6px;
            border-radius: var(--radius-sm);
        }

        .audit-rule-code.inclusion {
            background: var(--ink-approved-bg);
            color: var(--ink-approved-text);
            border: 1px solid var(--ink-approved-border);
        }

        .audit-rule-code.exclusion {
            background: var(--ink-rejected-bg);
            color: var(--ink-rejected-text);
            border: 1px solid var(--ink-rejected-border);
        }

        .audit-status-tag {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .audit-status-tag.pass {
            background: var(--ink-approved-bg);
            color: var(--ink-approved-text);
            border: 1px solid var(--ink-approved-border);
        }

        .audit-status-tag.violated {
            background: var(--ink-rejected-bg);
            color: var(--ink-rejected-text);
            border: 1px solid var(--ink-rejected-border);
        }

        /* ── DOSSIÊ PRISMA 2020: DOCUMENT CARD ── */
        .prisma-dossier-card {
            background: var(--paper-surface);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            overflow: hidden;
            margin: var(--sp-3) 0;
        }

        .prisma-dossier-header {
            background: var(--desk-bg);
            border-bottom: 1px solid var(--card-border);
            padding: var(--sp-3) var(--sp-4);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .prisma-dossier-title {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-primary);
        }

        /* ── CONTAINER DE TEXTO COM RECUO EDITORIAL (ABSTRACT) ── */
        .editorial-text-box {
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 0.94rem;
            line-height: 1.68;
            color: var(--text-primary);
            text-align: justify;
            background: var(--desk-bg);
            border: 1px solid var(--card-border-subtle);
            border-left: 3px solid var(--ink-accent-text);
            padding: var(--sp-3) var(--sp-4);
            border-radius: var(--radius-sm);
            margin-top: var(--sp-2);
        }

        /* ── ESTILOS NATIVOS DO STREAMLIT HARMONIZADOS ── */
        div[data-testid="stExpander"] {
            background-color: var(--paper-surface) !important;
            border: 1px solid var(--card-border) !important;
            border-radius: var(--radius-md) !important;
            margin-bottom: var(--sp-3) !important;
        }

        div[data-testid="stExpander"] summary {
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-weight: 600 !important;
            color: var(--text-primary) !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--card-border) !important;
            border-radius: var(--radius-md) !important;
            background-color: var(--paper-surface) !important;
        }

        .stButton>button {
            border-radius: var(--radius-md) !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-weight: 600 !important;
            transition: all 0.15s ease-in-out !important;
        }

        .stDownloadButton>button {
            border-radius: var(--radius-md) !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-weight: 600 !important;
        }

        div[data-testid="stFileUploader"] {
            background-color: var(--desk-bg) !important;
            border: 1px dashed var(--card-border) !important;
            border-radius: var(--radius-md) !important;
            padding: var(--sp-2) !important;
        }
    </style>
    """, unsafe_allow_html=True)


# ── TEMPLATE GLOBAL COORDENADO PARA GRÁFICOS PLOTLY ──────────────────────────
def aplicar_tema_plotly(fig: go.Figure) -> go.Figure:
    """Aplica o design system analítico da Mesa de Revisão nos gráficos Plotly."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="IBM Plex Sans, sans-serif",
            color="#EDE7DB",
            size=12
        ),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(
            font=dict(family="IBM Plex Sans, sans-serif", color="#EDE7DB", size=11),
            bgcolor="rgba(33, 28, 22, 0.8)",
            bordercolor="#38301F",
            borderwidth=1
        )
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#2C251B",
        zerolinecolor="#38301F",
        tickfont=dict(family="IBM Plex Mono, monospace", color="#A89C8A", size=11),
        title_font=dict(family="IBM Plex Sans, sans-serif", color="#EDE7DB", size=12)
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#2C251B",
        zerolinecolor="#38301F",
        tickfont=dict(family="IBM Plex Mono, monospace", color="#A89C8A", size=11),
        title_font=dict(family="IBM Plex Sans, sans-serif", color="#EDE7DB", size=12)
    )
    return fig


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
    Destaca ocorrências de critérios no texto com estilo de marca-texto fluido,
    utilizando box-decoration-break e sobrescrito discreto sem quebrar a linha.
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
                is_excl = (r.get("type") == "exclusion")
                bg_color = "rgba(122, 46, 40, 0.40)" if is_excl else "rgba(47, 90, 66, 0.40)"
                text_color = "#DF978B" if is_excl else "#8FBF9E"
                border_color = "#DF978B" if is_excl else "#8FBF9E"
                label = r.get("id", "")
                spans.append((start, end, bg_color, text_color, border_color, label))
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
            last_start, last_end, last_bg, last_tc, last_bc, last_label = merged_spans[-1]
            curr_start, curr_end, curr_bg, curr_tc, curr_bc, curr_label = current
            if curr_start < last_end:
                new_end = max(last_end, curr_end)
                is_excl = ("122, 46, 40" in last_bg or "122, 46, 40" in curr_bg)
                new_bg = "rgba(122, 46, 40, 0.40)" if is_excl else "rgba(47, 90, 66, 0.40)"
                new_tc = "#DF978B" if is_excl else "#8FBF9E"
                new_bc = "#DF978B" if is_excl else "#8FBF9E"
                new_label = f"{last_label}+{curr_label}"
                merged_spans[-1] = (last_start, new_end, new_bg, new_tc, new_bc, new_label)
            else:
                merged_spans.append(current)

    result = []
    last_idx = 0
    for start, end, bg_color, text_color, border_color, label in merged_spans:
        result.append(text[last_idx:start])
        matched_text = text[start:end]
        result.append(
            f'<mark style="background-color: {bg_color}; color: {text_color}; '
            f'border-bottom: 1.5px solid {border_color}; border-radius: 2px; padding: 1px 4px; '
            f'box-decoration-break: clone; -webkit-box-decoration-break: clone; font-weight: 500;" '
            f'title="Critério: {label}">'
            f'{matched_text}'
            f'<sup style="font-family: \'IBM Plex Mono\', monospace; font-size: 0.68em; '
            f'margin-left: 2px; font-weight: 700; opacity: 0.9; vertical-align: super;">{label}</sup>'
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

# Injetar regras de estilo centralizadas
inject_custom_css()


# ── CABEÇALHO PRINCIPAL DA APLICAÇÃO ─────────────────────────────────────────
st.markdown("""
<div class="brand-container">
    <div class="brand-icon-box">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
    </div>
    <div>
        <div style="display: flex; align-items: center; flex-wrap: wrap;">
            <h1 class="brand-title">Triador RSL — Mesa de Revisão</h1>
            <span class="brand-badge">PRISMA 2020</span>
        </div>
        <div class="brand-subtitle">
            Auditoria bibliográfica automatizada por Expressões Regulares para Revisões Sistemáticas de Literatura.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── PAINEL LATERAL (SIDEBAR): TRILHA SEQUENCIAL DE SETUP ─────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="4" y1="21" x2="4" y2="14"></line>
            <line x1="4" y1="10" x2="4" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12" y2="3"></line>
            <line x1="20" y1="21" x2="20" y2="16"></line>
            <line x1="20" y1="12" x2="20" y2="3"></line>
            <line x1="1" y1="14" x2="7" y2="14"></line>
            <line x1="9" y1="8" x2="15" y2="8"></line>
            <line x1="17" y1="16" x2="23" y2="16"></line>
        </svg>
        Painel de Setup & Protocolo
    </div>
    """, unsafe_allow_html=True)

    # 1. Base de Artigos
    uploaded_file = st.file_uploader(
        "Importar Base de Artigos (.xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv"],
        help="Planilha exportada do Parsifal, Scopus, IEEE Xplore, PubMed ou repositório similar."
    )

    columns_list = []
    df_uploaded = None
    step1_class = "active"
    step1_num = "1"

    if uploaded_file is not None:
        try:
            df_uploaded = carregar_base_artigos(uploaded_file)
            columns_list = df_uploaded.columns.tolist()
            step1_class = "done"
            step1_num = "✓"
            st.markdown(
                f'<div style="font-family: \'IBM Plex Mono\', monospace; font-size: 0.78rem; color: var(--ink-approved-text); '
                f'background: var(--ink-approved-bg); border: 1px solid var(--ink-approved-border); padding: 4px 8px; '
                f'border-radius: 2px; margin-top: 4px;">'
                f'● Base Carregada: <strong>{len(df_uploaded)} artigos</strong> ({len(columns_list)} colunas)'
                f'</div>',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.markdown(f"""
    <div class="trail-step-header">
        <div class="trail-step-badge {step1_class}">{step1_num}</div>
        <div class="trail-step-title">Base de Artigos</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

    # 2. Configurações de Limpeza
    st.markdown("""
    <div class="trail-step-header">
        <div class="trail-step-badge active">2</div>
        <div class="trail-step-title">Estratégias de Limpeza</div>
    </div>
    """, unsafe_allow_html=True)

    remover_duplicatas = st.checkbox(
        "Remover Artigos Duplicados",
        value=True,
        help="Normaliza o texto do título para consolidar entradas idênticas."
    )

    coluna_dedup = "title"
    if remover_duplicatas:
        default_idx = columns_list.index("title") if "title" in columns_list else 0
        coluna_dedup = st.selectbox(
            "Coluna para Deduplicação",
            options=columns_list if columns_list else ["title"],
            index=default_idx
        )

    estrategia_doi = st.selectbox(
        "Política de Registros Sem DOI",
        options=["remove", "flag", "ignore"],
        format_func=lambda x: {
            "remove": "Descartar artigos sem DOI",
            "flag": "Sinalizar no relatório",
            "ignore": "Ignorar verificação de DOI"
        }.get(x, x),
        index=0,
        help="Define a tratativa para publicações sem código identificador DOI."
    )

    st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

    # 3. Perfis de Regras
    st.markdown("""
    <div class="trail-step-header">
        <div class="trail-step-badge active">3</div>
        <div class="trail-step-title">Perfis de Regras</div>
    </div>
    """, unsafe_allow_html=True)

    rules_json_str = json.dumps(st.session_state.rules, indent=2, ensure_ascii=False)
    st.download_button(
        label="Exportar Perfil (JSON)",
        data=rules_json_str,
        file_name="perfil_regras_rsl.json",
        mime="application/json",
        use_container_width=True
    )

    uploaded_rules = st.file_uploader(
        "Carregar Perfil Salvo (JSON)",
        type=["json"],
        help="Importa um conjunto de critérios de inclusão e exclusão salvo em JSON."
    )
    if uploaded_rules is not None:
        try:
            rules_data = json.load(uploaded_rules)
            if isinstance(rules_data, list) and all(isinstance(r, dict) and "id" in r and "pattern" in r for r in rules_data):
                st.session_state.rules = rules_data
                st.success("Perfil de regras importado com sucesso.")
                st.rerun()
            else:
                st.error("Estrutura JSON de regras incompatível.")
        except Exception as e:
            st.error(f"Erro ao processar arquivo JSON: {e}")

    if st.button("Restaurar Regras Padrão", use_container_width=True):
        st.session_state.rules = json.loads(json.dumps(DEFAULT_RULES))
        st.success("Regras redefinidas para a configuração original.")
        st.rerun()


# ── ABAS PRINCIPAIS: PASTAS DE DOSSIÊ SUSPENSAS ──────────────────────────────
tab_regras, tab_execucao, tab_estatisticas = st.tabs([
    "1. Critérios & Validação Regex",
    "2. Execução & Dossiê de Screening",
    "3. Fluxo PRISMA 2020 & Estatísticas"
])


# ── ABA 1: CONFIGURAÇÃO DE REGRAS & PLAYGROUND REGEX ──────────────────────────
with tab_regras:
    st.markdown("""
    <div style="margin-bottom: var(--sp-4);">
        <h3 style="font-family: 'IBM Plex Serif', serif; font-size: 1.25rem; font-weight: 600; margin: 0 0 var(--sp-1) 0;">
            Critérios de Inclusão e Exclusão
        </h3>
        <div style="font-size: 0.9rem; color: var(--text-muted);">
            Defina e teste expressões regulares para classificar cada artigo automaticamente conforme o protocolo da RSL.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Resumo dos Critérios Ativos em Tabela
    if st.session_state.rules:
        summary_data = []
        for r in st.session_state.rules:
            tipo_label = "Exclusão" if r["type"] == "exclusion" else "Inclusão"
            summary_data.append({
                "ID": r["id"],
                "Nome do Critério": r["name"],
                "Ação": tipo_label,
                "Campos Inspecionados": ", ".join(r.get("fields", [])),
                "Expressão Regular (Regex)": r.get("pattern", "")
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum critério ativo cadastrado.")

    # ── SANDBOX INTERATIVO DE REGEX EM TEMPO REAL ──
    with st.expander("Validador & Testador de Regex em Tempo Real", expanded=False):
        st.markdown(
            '<div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: var(--sp-3);">'
            'Simule a captura da expressão regular contra um trecho de título ou resumo de amostra.'
            '</div>',
            unsafe_allow_html=True
        )

        c_sand1, c_sand2 = st.columns([1, 1])
        with c_sand1:
            teste_regex = st.text_input("Expressão Regular para Teste", value="procedural|pcg|survey")
            teste_tipo = st.radio("Simular Comportamento", ["Inclusão (Retenção)", "Exclusão (Descarte)"], horizontal=True)
        with c_sand2:
            texto_exemplo_padrao = "We present a survey on procedural content generation (PCG) in digital games."
            teste_texto = st.text_area("Texto de Amostra para Avaliação", value=texto_exemplo_padrao, height=85)

        if teste_regex:
            try:
                comp_pattern = re.compile(teste_regex, re.IGNORECASE | re.MULTILINE)
                ocorrencias = list(comp_pattern.finditer(teste_texto))

                st.markdown(
                    f'<div style="font-family: \'IBM Plex Mono\', monospace; font-size: 0.82rem; color: var(--ink-approved-text); '
                    f'background: var(--ink-approved-bg); border: 1px solid var(--ink-approved-border); padding: 6px 12px; '
                    f'border-radius: 2px; margin: var(--sp-2) 0;">'
                    f'Sintaxe Regex Válida • Correspondências encontradas: <strong>{len(ocorrencias)}</strong>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                regra_fake = [{
                    "id": "TESTE",
                    "pattern": teste_regex,
                    "type": "exclusion" if "Exclusão" in teste_tipo else "inclusion",
                    "fields": ["mock"]
                }]
                texto_destacado = highlight_text(teste_texto, regra_fake, "mock")
                st.markdown(f'<div class="editorial-text-box">{texto_destacado}</div>', unsafe_allow_html=True)

            except re.error as err:
                st.markdown(
                    f'<div style="font-family: \'IBM Plex Mono\', monospace; font-size: 0.82rem; color: var(--ink-rejected-text); '
                    f'background: var(--ink-rejected-bg); border: 1px solid var(--ink-rejected-border); padding: 6px 12px; '
                    f'border-radius: 2px; margin: var(--sp-2) 0;">'
                    f'Erro de Sintaxe Regex: {err}'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

    # ── EDIÇÃO DOS CRITÉRIOS EXISTENTES ──
    st.markdown("""
    <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-bottom: var(--sp-3);">
        Editar Critérios Ativos
    </h4>
    """, unsafe_allow_html=True)

    rules_to_delete = []

    for i, rule in enumerate(st.session_state.rules):
        rule_id = rule["id"]
        rule_name = rule["name"]
        rule_type = rule["type"]
        rule_pattern = rule.get("pattern", "")
        rule_fields = rule.get("fields", ["title", "abstract", "author_keywords", "keywords"])

        tipo_badge = "Exclusão" if rule_type == "exclusion" else "Inclusão"
        with st.expander(f"[{rule_id}] {rule_name} — {tipo_badge}", expanded=False):
            c1, c2 = st.columns([1, 2])
            with c1:
                new_id = st.text_input("Identificador (ID)", value=rule_id, key=f"id_{i}")
                new_type = st.selectbox(
                    "Tipo de Ação",
                    options=["exclusion", "inclusion"],
                    format_func=lambda x: "Exclusão (Se encontrar no texto, descarta)" if x == "exclusion" else "Inclusão (Se não encontrar, descarta)",
                    index=0 if rule_type == "exclusion" else 1,
                    key=f"type_{i}"
                )
            with c2:
                new_name = st.text_input("Nome Descritivo", value=rule_name, key=f"name_{i}")
                new_pattern = st.text_area("Expressão Regular (Regex)", value=rule_pattern, key=f"pattern_{i}", height=68)

            available_fields = ["title", "abstract", "author_keywords", "keywords"]
            for col in columns_list:
                if col not in available_fields:
                    available_fields.append(col)

            new_fields = st.multiselect(
                "Campos Inspecionados",
                options=available_fields,
                default=[f for f in rule_fields if f in available_fields],
                key=f"fields_{i}"
            )

            if st.button(f"Excluir Critério {rule_id}", key=f"del_{i}", type="secondary"):
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

    st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

    # ── ADICIONAR NOVO CRITÉRIO ──
    st.markdown("""
    <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-bottom: var(--sp-3);">
        Adicionar Novo Critério
    </h4>
    """, unsafe_allow_html=True)

    with st.form("add_rule_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            add_id = st.text_input("ID do Critério", placeholder="Ex: EX2 ou IN2")
        with c2:
            add_name = st.text_input("Nome", placeholder="Ex: Publicações de Workshop / Resumos Curtos")
        with c3:
            add_type = st.selectbox(
                "Tipo de Critério",
                options=["exclusion", "inclusion"],
                format_func=lambda x: "Exclusão (Descarte)" if x == "exclusion" else "Inclusão (Obrigatório)"
            )

        add_pattern = st.text_area("Expressão Regular (Regex)", placeholder="Ex: short paper|extended abstract|poster|workshop")

        available_fields = ["title", "abstract", "author_keywords", "keywords"]
        for col in columns_list:
            if col not in available_fields:
                available_fields.append(col)
        add_fields = st.multiselect("Campos Inspecionados", options=available_fields, default=["title", "abstract"])

        submitted = st.form_submit_button("Cadastrar Critério", use_container_width=True)
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
                st.success(f"Critério '{add_id}' cadastrado com sucesso.")
                st.rerun()


# ── ABA 2: EXECUÇÃO & DOSSIÊ DE SCREENING ─────────────────────────────────────
with tab_execucao:
    st.markdown("""
    <div style="margin-bottom: var(--sp-4);">
        <h3 style="font-family: 'IBM Plex Serif', serif; font-size: 1.25rem; font-weight: 600; margin: 0 0 var(--sp-1) 0;">
            Processamento & Auditoria de Triagem
        </h3>
        <div style="font-size: 0.9rem; color: var(--text-muted);">
            Execute a classificação em lote dos artigos e audite as decisões critério por critério.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_uploaded is None:
        st.markdown("""
        <div style="background: var(--paper-surface); border: 1px dashed var(--card-border); padding: var(--sp-5); border-radius: var(--radius-md); text-align: center;">
            <div style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: var(--sp-2);">
                Nenhuma base carregada.
            </div>
            <div style="color: var(--text-dim); font-size: 0.84rem;">
                Importe uma planilha (.xlsx, .xls ou .csv) no Painel de Setup à esquerda para iniciar o screening.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.button("Executar Triagem Automática", type="primary", use_container_width=True):
            with st.spinner("Classificando publicações e consolidando decisões..."):
                try:
                    resultado = executar_triagem(
                        df=df_uploaded,
                        rules=st.session_state.rules,
                        remover_duplicatas=remover_duplicatas,
                        coluna_dedup=coluna_dedup,
                        estrategia_doi=estrategia_doi
                    )
                    st.session_state.resultados = resultado
                    st.success("Triagem concluída com sucesso.")
                except Exception as e:
                    st.error(f"Erro no processamento da triagem: {e}")

        # ── EXIBIÇÃO DE RESULTADOS ──
        if st.session_state.resultados is not None:
            res = st.session_state.resultados
            stats = res["stats"]
            aprovados = res["aprovados"]
            rejeitados = res["rejeitados"]

            st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

            # ── PAINEL DE INDICADORES DE MÉTRICAS (HIERARQUIA VISUAL EM 2 NÍVEIS) ──
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

            with col_m1:
                st.markdown(f"""
                <div class="metric-grid-card metric-card-secondary">
                    <div class="metric-label">Total Inicial</div>
                    <div class="metric-value-mono">{stats['total_inicial']}</div>
                    <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: var(--sp-1);">Registros brutos</div>
                </div>
                """, unsafe_allow_html=True)

            with col_m2:
                st.markdown(f"""
                <div class="metric-grid-card metric-card-secondary">
                    <div class="metric-label">Duplicatas</div>
                    <div class="metric-value-mono">{stats['duplicatas_removidas']}</div>
                    <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: var(--sp-1);">Excluídas na limpeza</div>
                </div>
                """, unsafe_allow_html=True)

            with col_m3:
                doi_val = stats["sem_doi"] if estrategia_doi == "remove" else stats["sem_doi_flagged"]
                doi_lbl = "Sem DOI (Excluídos)" if estrategia_doi == "remove" else "Sem DOI (Marcados)"
                st.markdown(f"""
                <div class="metric-grid-card metric-card-secondary">
                    <div class="metric-label">{doi_lbl}</div>
                    <div class="metric-value-mono">{doi_val}</div>
                    <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: var(--sp-1);">Política: {estrategia_doi}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_m4:
                tx_ap = stats.get("taxa_aprovacao_pct", 0)
                st.markdown(f"""
                <div class="metric-grid-card metric-card-approved">
                    <div class="metric-label" style="color: var(--ink-approved-text);">Artigos Aprovados</div>
                    <div class="metric-value-mono" style="color: var(--ink-approved-text);">{stats['aprovados']}</div>
                    <div class="metric-delta-tag metric-delta-approved">
                        {tx_ap}% de retenção
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_m5:
                tx_rej = stats.get("taxa_rejeicao_pct", 0)
                st.markdown(f"""
                <div class="metric-grid-card metric-card-rejected">
                    <div class="metric-label" style="color: var(--ink-rejected-text);">Artigos Rejeitados</div>
                    <div class="metric-value-mono" style="color: var(--ink-rejected-text);">{stats['rejeitados']}</div>
                    <div class="metric-delta-tag metric-delta-rejected">
                        {tx_rej}% de descarte
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

            # ── BOTÕES DE EXPORTAÇÃO ──
            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-bottom: var(--sp-3);">
                Exportação de Resultados
            </h4>
            """, unsafe_allow_html=True)

            multi_excel_data = gerar_pacote_completo_excel(aprovados, rejeitados, stats, st.session_state.rules)
            st.download_button(
                label="Baixar Pacote Consolidado Multi-Abas (Excel .xlsx)",
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
                    label="Baixar Apenas Artigos Aprovados (Excel)",
                    data=excel_ap,
                    file_name="artigos_aprovados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with c_d2:
                excel_rej = converter_df_para_excel(rejeitados)
                st.download_button(
                    label="Baixar Apenas Artigos Rejeitados (Excel)",
                    data=excel_rej,
                    file_name="artigos_rejeitados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

            # ── TABELAS DE ARTIGOS ──
            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-bottom: var(--sp-2);">
                Artigos Aprovados (Retidos)
            </h4>
            """, unsafe_allow_html=True)

            if not aprovados.empty:
                st.dataframe(aprovados, use_container_width=True)
            else:
                st.info("Nenhum artigo aprovado com a parametrização atual.")

            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-top: var(--sp-4); margin-bottom: var(--sp-2);">
                Artigos Rejeitados (Descartados)
            </h4>
            """, unsafe_allow_html=True)

            if not rejeitados.empty:
                motivos_unicos = ["(Todos os Critérios)"]
                for r in st.session_state.rules:
                    motivos_unicos.append(r["id"])

                filtro_motivo = st.selectbox("Filtrar Tabela por Critério Violado:", options=motivos_unicos)
                if filtro_motivo != "(Todos os Critérios)":
                    df_rej_view = rejeitados[rejeitados["motivo_rejeicao"].str.contains(filtro_motivo, na=False)]
                else:
                    df_rej_view = rejeitados

                st.dataframe(df_rej_view, use_container_width=True)
            else:
                st.info("Nenhum artigo rejeitado.")

            st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

            # ── INSPETOR & DIAGNÓSTICO INDIVIDUAL (FICHA CATALOGRÁFICA) ──
            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.15rem; font-weight: 600; margin-bottom: var(--sp-1);">
                Inspetor & Diagnóstico Individual de Artigo
            </h4>
            <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: var(--sp-3);">
                Audite a ativação de cada critério e examine o texto original com grifo de marca-texto analítico.
            </div>
            """, unsafe_allow_html=True)

            ap_temp = aprovados.copy()
            ap_temp["status"] = "APROVADO"
            ap_temp["motivo_rejeicao"] = ""

            rej_temp = rejeitados.copy()
            rej_temp["status"] = "REJEITADO"

            df_total = pd.concat([ap_temp, rej_temp], ignore_index=True)

            if not df_total.empty:
                options_list = df_total.index.tolist()
                def formatar_opcao_artigo(idx):
                    row_item = df_total.loc[idx]
                    status = row_item["status"]
                    title = str(row_item.get("title", "Sem Título"))
                    short_title = title[:90] + "..." if len(title) > 90 else title
                    return f"[{status}] {short_title}"

                artigo_selecionado = st.selectbox(
                    "Selecione o artigo para inspeção detalhada:",
                    options=options_list,
                    format_func=formatar_opcao_artigo
                )

                if artigo_selecionado is not None:
                    row = df_total.loc[artigo_selecionado]
                    status_val = row["status"]
                    is_approved = (status_val == "APROVADO")
                    stamp_class = "audit-stamp-approved" if is_approved else "audit-stamp-rejected"

                    st.markdown(f"""
                    <div class="catalog-card">
                        <div class="catalog-card-header">
                            <div>
                                <h3 class="catalog-article-title">{row.get('title', 'Sem Título')}</h3>
                            </div>
                            <div>
                                <span class="audit-stamp {stamp_class}">
                                    {status_val}
                                </span>
                            </div>
                        </div>
                        <div class="catalog-meta-strip">
                            <div class="catalog-meta-item">Autor(es): <strong>{row.get('author', 'N/A')}</strong></div>
                            <div class="catalog-meta-item">Ano: <strong>{row.get('year', 'N/A')}</strong></div>
                            <div class="catalog-meta-item">DOI: <strong>{row.get('doi', 'N/A')}</strong></div>
                            <div class="catalog-meta-item">Periódico/Veículo: <strong>{row.get('journal', 'N/A')}</strong></div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Checklist de Auditoria Compacto
                    st.markdown("""
                    <div style="font-size: 0.84rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-top: var(--sp-3); margin-bottom: var(--sp-2);">
                        Auditoria Critério a Critério
                    </div>
                    <div class="audit-checklist">
                    """, unsafe_allow_html=True)

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
                            violado = matched
                            tag_text = "VIOLADO" if violado else "PASSOU"
                            tag_class = "violated" if violado else "pass"
                            desc_text = "Termos de exclusão detectados" if violado else "Nenhum termo indesejado"
                        else:
                            violado = not matched
                            tag_text = "PASSOU" if not violado else "VIOLADO"
                            tag_class = "pass" if not violado else "violated"
                            desc_text = "Termos obrigatórios encontrados" if not violado else "Termos obrigatórios ausentes"

                        type_class = "exclusion" if r_type == "exclusion" else "inclusion"

                        st.markdown(f"""
                        <div class="audit-check-row">
                            <div class="audit-check-left">
                                <span class="audit-rule-code {type_class}">{r_id}</span>
                                <span><strong>{r_name}</strong> <span style="color: var(--text-muted); font-size: 0.82rem;">({desc_text})</span></span>
                            </div>
                            <span class="audit-status-tag {tag_class}">{tag_text}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Destaque nos Campos de Texto
                    st.markdown("""
                    <div style="font-size: 0.84rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-top: var(--sp-4); margin-bottom: var(--sp-2);">
                        Grifos Analíticos nos Campos de Texto
                    </div>
                    """, unsafe_allow_html=True)

                    h_title = highlight_text(str(row.get("title", "")), st.session_state.rules, "title")
                    st.markdown(f"<div style='font-size: 0.9rem; margin-bottom: var(--sp-2);'><strong>Título:</strong> {h_title}</div>", unsafe_allow_html=True)

                    if "abstract" in row.index and pd.notna(row["abstract"]):
                        h_abstract = highlight_text(str(row["abstract"]), st.session_state.rules, "abstract")
                        st.markdown(f"<strong>Resumo (Abstract):</strong><div class='editorial-text-box'>{h_abstract}</div>", unsafe_allow_html=True)

                    if "keywords" in row.index and pd.notna(row["keywords"]):
                        h_kw = highlight_text(str(row["keywords"]), st.session_state.rules, "keywords")
                        st.markdown(f"<div style='font-size: 0.88rem; margin-top: var(--sp-2);'><strong>Palavras-chave:</strong> {h_kw}</div>", unsafe_allow_html=True)

                    if "author_keywords" in row.index and pd.notna(row["author_keywords"]):
                        h_akw = highlight_text(str(row["author_keywords"]), st.session_state.rules, "author_keywords")
                        st.markdown(f"<div style='font-size: 0.88rem; margin-top: var(--sp-1);'><strong>Palavras-chave do Autor:</strong> {h_akw}</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)


# ── ABA 3: ESTATÍSTICAS & FLUXO PRISMA 2020 ──────────────────────────────────
with tab_estatisticas:
    st.markdown("""
    <div style="margin-bottom: var(--sp-4);">
        <h3 style="font-family: 'IBM Plex Serif', serif; font-size: 1.25rem; font-weight: 600; margin: 0 0 var(--sp-1) 0;">
            Diagrama de Fluxo & Dossiê PRISMA 2020
        </h3>
        <div style="font-size: 0.9rem; color: var(--text-muted);">
            Indicadores quantitativos e sumário estruturado para citação direta em manuscritos científicos.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.resultados is None:
        st.info("Execute a triagem na aba 'Execução & Dossiê de Screening' para gerar as estatísticas e o fluxo PRISMA.")
    else:
        res = st.session_state.resultados
        stats = res["stats"]

        # ── GRÁFICO INTERATIVO DE FLUXO PRISMA (FUNIL DE RETENÇÃO ANALÍTICA) ──
        st.markdown("""
        <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.1rem; font-weight: 600; margin-bottom: var(--sp-2);">
            Funil de Seleção PRISMA 2020
        </h4>
        """, unsafe_allow_html=True)

        funnel_labels = [
            f"1. Identificação Inicial ({stats['total_inicial']})",
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

        # Gradiente monotônico analítico de retenção até a tinta de aprovação final
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_labels,
            x=funnel_values,
            textinfo="value+percent initial",
            marker={
                "color": ["#2E4A6B", "#243B55", "#1B2C3F", "#2F5A42"],
                "line": {"color": "#211C16", "width": 1.5}
            },
            textfont=dict(family="IBM Plex Mono, monospace", size=11, color="#EDE7DB")
        ))
        fig_funnel = aplicar_tema_plotly(fig_funnel)
        fig_funnel.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_funnel, use_container_width=True)

        st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)

        c_g1, c_g2 = st.columns([1, 1])

        with c_g1:
            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.05rem; font-weight: 600; margin-bottom: var(--sp-2);">
                Distribuição Final
            </h4>
            """, unsafe_allow_html=True)
            fig_pie = px.pie(
                values=[stats["aprovados"], stats["rejeitados"]],
                names=["Aprovados", "Rejeitados"],
                color=["Aprovados", "Rejeitados"],
                color_discrete_map={"Aprovados": "#2F5A42", "Rejeitados": "#7A2E28"},
                hole=0.48
            )
            fig_pie.update_traces(
                marker=dict(line=dict(color="#211C16", width=2)),
                textfont=dict(family="IBM Plex Mono, monospace", size=12, color="#EDE7DB")
            )
            fig_pie = aplicar_tema_plotly(fig_pie)
            fig_pie.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_g2:
            st.markdown("""
            <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.05rem; font-weight: 600; margin-bottom: var(--sp-2);">
                Impacto por Critério de Descarte
            </h4>
            """, unsafe_allow_html=True)
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
                    color_continuous_scale=[
                        [0.0, "#4A1D1A"],
                        [0.5, "#7A2E28"],
                        [1.0, "#9E3B33"]
                    ]
                )
                fig_bar.update_traces(
                    marker=dict(line=dict(color="#38301F", width=1))
                )
                fig_bar = aplicar_tema_plotly(fig_bar)
                fig_bar.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Nenhum descarte por critério registrado.")

        # ── DOSSIÊ PRISMA 2020: DOCUMENTO ESTRUTURADO PARA CÓPIA DIRETA ──
        st.markdown('<div class="trail-divider"></div>', unsafe_allow_html=True)
        st.markdown("""
        <h4 style="font-family: 'IBM Plex Serif', serif; font-size: 1.15rem; font-weight: 600; margin-bottom: var(--sp-1);">
            Dossiê PRISMA 2020 (Extrato de Auditoria)
        </h4>
        <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: var(--sp-3);">
            Extrato padronizado para inclusão direta em tabelas e seções de metodologia de publicações científicas.
        </div>
        """, unsafe_allow_html=True)

        linhas_relatorio = [
            "DOSSIÊ DE SCREENING BIBLIOGRÁFICO – FLUXO PRISMA 2020",
            "────────────────────────────────────────────────────────────",
            f"1. Identificação Inicial     : {stats['total_inicial']:>6} artigos",
            f"2. Duplicatas Removidas      : {stats['duplicatas_removidas']:>6} artigos",
            f"3. Excluídos Sem DOI         : {stats['sem_doi']:>6} artigos",
            f"4. Sinalizados Sem DOI       : {stats['sem_doi_flagged']:>6} artigos",
            f"5. Elegibilidade Avaliada    : {stats['pos_limpeza']:>6} artigos",
            "────────────────────────────────────────────────────────────",
            "CRITÉRIOS DE DESCARTE:"
        ]

        for rule in st.session_state.rules:
            r_id = rule["id"]
            r_name = rule["name"]
            r_type = rule["type"]
            count = stats["regra_stats"].get(r_id, 0)
            prefix = "Com Exclusão" if r_type == "exclusion" else "Sem Inclusão"
            linhas_relatorio.append(f"  • {r_id:<6} ({prefix:<12} - {r_name}): {count:>5} artigos")

        linhas_relatorio.extend([
            "────────────────────────────────────────────────────────────",
            f"TOTAL APROVADOS (INCLUÍDOS)  : {stats['aprovados']:>6} ({stats.get('taxa_aprovacao_pct', 0):>5.1f}%)",
            f"TOTAL REJEITADOS (EXCLUÍDOS) : {stats['rejeitados']:>6} ({stats.get('taxa_rejeicao_pct', 0):>5.1f}%)",
            "────────────────────────────────────────────────────────────"
        ])

        texto_dossie = "\n".join(linhas_relatorio)

        st.text_area(
            "Copie o extrato abaixo para colar no manuscrito ou protocolo de RSL:",
            value=texto_dossie,
            height=280
        )
