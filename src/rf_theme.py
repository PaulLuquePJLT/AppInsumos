from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


RF_COLORS = {
    "navy": "#142534",
    "navy_2": "#103541",
    "teal_dark": "#0E5663",
    "teal": "#18A999",
    "teal_soft": "#DDF7F3",
    "gold": "#F2C94C",
    "bg": "#F4FAFA",
    "surface": "#FFFFFF",
    "muted": "#6B7A86",
    "border": "#DCE7EA",
    "danger": "#D64545",
}


def _logo_path() -> Path | None:
    for file_name in ["logo.png", "logo.webp", "logo.jpg", "logo.jpeg"]:
        candidate = Path("assets") / file_name
        if candidate.exists():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def logo_base64() -> str:
    path = _logo_path()
    if not path:
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def load_rf_icon():
    path = _logo_path()
    if not path:
        return "📦"
    try:
        from PIL import Image

        return Image.open(path)
    except Exception:
        return str(path)


def logo_img(width: int = 72) -> str:
    encoded = logo_base64()
    if not encoded:
        return ""
    return f'<img src="data:image/png;base64,{encoded}" style="width:{width}px;height:auto;display:block;" />'


def rf_background_uri() -> str:
    svg = """
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 1600'>
      <defs>
        <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0' stop-color='#eaf8f6'/>
          <stop offset='.55' stop-color='#f8fcfc'/>
          <stop offset='1' stop-color='#eef7f6'/>
        </linearGradient>
        <linearGradient id='rack' x1='0' y1='0' x2='0' y2='1'>
          <stop offset='0' stop-color='#0e5663' stop-opacity='.22'/>
          <stop offset='1' stop-color='#142534' stop-opacity='.06'/>
        </linearGradient>
      </defs>
      <rect width='900' height='1600' fill='url(#bg)'/>
      <circle cx='780' cy='180' r='210' fill='#18A999' opacity='.10'/>
      <circle cx='110' cy='1380' r='260' fill='#F2C94C' opacity='.09'/>
      <g opacity='.65'>
        <path d='M70 980 L430 830 L430 1250 L70 1370 Z' fill='url(#rack)'/>
        <path d='M510 360 L850 240 L850 760 L510 860 Z' fill='url(#rack)'/>
        <path d='M115 1010 L400 890' stroke='#0E5663' stroke-opacity='.15' stroke-width='9'/>
        <path d='M115 1090 L400 970' stroke='#0E5663' stroke-opacity='.12' stroke-width='8'/>
        <path d='M115 1170 L400 1050' stroke='#0E5663' stroke-opacity='.09' stroke-width='8'/>
        <path d='M560 400 L825 300' stroke='#0E5663' stroke-opacity='.15' stroke-width='9'/>
        <path d='M560 490 L825 390' stroke='#0E5663' stroke-opacity='.12' stroke-width='8'/>
        <path d='M560 580 L825 480' stroke='#0E5663' stroke-opacity='.09' stroke-width='8'/>
      </g>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def apply_rf_theme(login: bool = False) -> None:
    bg = rf_background_uri()
    sidebar_css = "" if not login else """
        section[data-testid="stSidebar"],
        div[data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display:none !important;
            visibility:hidden !important;
            width:0 !important;
            min-width:0 !important;
        }
    """
    st.markdown(
        f"""
        <style>
        :root {{
            --rf-navy: {RF_COLORS['navy']};
            --rf-navy-2: {RF_COLORS['navy_2']};
            --rf-teal-dark: {RF_COLORS['teal_dark']};
            --rf-teal: {RF_COLORS['teal']};
            --rf-teal-soft: {RF_COLORS['teal_soft']};
            --rf-gold: {RF_COLORS['gold']};
            --rf-bg: {RF_COLORS['bg']};
            --rf-surface: {RF_COLORS['surface']};
            --rf-muted: {RF_COLORS['muted']};
            --rf-border: {RF_COLORS['border']};
            --rf-danger: {RF_COLORS['danger']};
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: url("{bg}") center center / cover no-repeat fixed !important;
            color: var(--rf-navy);
        }}

        header[data-testid="stHeader"] {{
            background: rgba(255,255,255,.78) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(220,231,234,.78);
            min-height: 3.45rem;
        }}

        .block-container {{
            padding-top: 4.65rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 720px !important;
        }}

        h1, h2, h3 {{
            color: var(--rf-navy) !important;
            letter-spacing: -0.035em;
        }}

        .rf-login-card {{
            background: rgba(255,255,255,.92);
            border: 1px solid rgba(220,231,234,.95);
            border-radius: 28px;
            box-shadow: 0 28px 72px rgba(20,37,52,.18);
            padding: 1.65rem 1.35rem 1.45rem 1.35rem;
            backdrop-filter: blur(16px);
            margin: 0 auto;
        }}

        .rf-login-brand {{
            display:flex;
            flex-direction: column;
            align-items:center;
            margin-bottom: 1rem;
            text-align:center;
        }}

        .rf-login-title {{
            color: var(--rf-navy);
            font-size: 1.85rem;
            line-height: 1.05;
            font-weight: 900;
            margin-top: .65rem;
        }}

        .rf-login-subtitle {{
            color: var(--rf-muted);
            font-size: .92rem;
            line-height: 1.35;
            margin-top: .45rem;
        }}

        div[data-testid="stForm"] {{
            border: 0 !important;
            background: transparent !important;
        }}

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] > div {{
            border-radius: 14px !important;
            border: 1px solid rgba(220,231,234,.95) !important;
            background: rgba(248,251,252,.98) !important;
            min-height: 2.85rem;
        }}

        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {{
            border-radius: 14px !important;
            font-weight: 820 !important;
            min-height: 3rem;
            border: 1px solid rgba(14,86,99,.18) !important;
        }}

        button[kind="primary"], .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--rf-teal-dark), var(--rf-teal)) !important;
            color: white !important;
        }}

        .rf-card {{
            background: rgba(255,255,255,.93);
            border: 1px solid rgba(220,231,234,.92);
            border-radius: 22px;
            padding: 1rem;
            box-shadow: 0 18px 38px rgba(15,74,85,.10);
            margin-bottom: 1rem;
        }}

        .rf-product-ok {{
            border-left: 6px solid var(--rf-teal);
        }}

        .rf-product-error {{
            border-left: 6px solid var(--rf-danger);
        }}

        .rf-kicker {{
            color: var(--rf-teal-dark);
            font-weight: 850;
            letter-spacing: .06em;
            text-transform: uppercase;
            font-size: .76rem;
        }}

        .rf-product-title {{
            color: var(--rf-navy);
            font-weight: 900;
            font-size: 1.08rem;
            line-height: 1.18;
            margin: .25rem 0 .55rem 0;
        }}

        .rf-grid {{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap: .65rem;
        }}

        .rf-field {{
            background: rgba(221,247,243,.55);
            border-radius: 14px;
            padding: .58rem .65rem;
        }}

        .rf-label {{
            color: var(--rf-muted);
            font-size: .72rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .05em;
        }}

        .rf-value {{
            color: var(--rf-navy);
            font-size: .95rem;
            font-weight: 850;
            margin-top: .12rem;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0D3140 0%, #123F4B 45%, #1C6570 100%) !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: rgba(255,255,255,.92) !important;
        }}

        .rf-sidebar-logo {{
            display:flex;
            align-items:center;
            justify-content:center;
            padding: 1rem .25rem 1.2rem .25rem;
            margin-bottom: .3rem;
        }}

        .rf-sidebar-section {{
            font-size: .78rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: rgba(221,247,243,.78) !important;
            margin-top: .85rem;
            margin-bottom: .4rem;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            background: rgba(255,255,255,.08) !important;
            color: rgba(255,255,255,.96) !important;
            border: 1px solid rgba(255,255,255,.11) !important;
            box-shadow: none !important;
        }}

        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(24,169,153,.26) !important;
        }}

        [data-testid="stDataFrame"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--rf-border);
            background:white;
        }}

        {sidebar_css}

        @media (max-width: 640px) {{
            .block-container {{
                max-width: 100vw !important;
                padding-top: 4.25rem !important;
            }}
            .rf-login-card {{
                padding: 1.35rem 1rem 1.2rem 1rem;
                border-radius: 24px;
            }}
            .rf-grid {{ grid-template-columns: 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_rf_logo_sidebar() -> None:
    st.sidebar.markdown(
        f"""
        <div class="rf-sidebar-logo">
            {logo_img(86)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rf_product_card(product: dict | None, searched_code: str) -> None:
    if not searched_code:
        return

    if not product:
        st.markdown(
            f"""
            <div class="rf-card rf-product-error">
                <div class="rf-kicker">Código no encontrado</div>
                <div class="rf-product-title">❌ {searched_code}</div>
                <div style="color:var(--rf-muted);font-weight:650;">
                    El SKU/EAN escaneado no existe o está inactivo.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    ean = product.get("ean_serie") or "-"
    flag_lote = "SI" if bool(product.get("requiere_lote")) else "NO"
    st.markdown(
        f"""
        <div class="rf-card rf-product-ok">
            <div class="rf-kicker">Código reconocido ✅</div>
            <div class="rf-product-title">{product.get('nombre_producto','')}</div>
            <div class="rf-grid">
                <div class="rf-field"><div class="rf-label">SKU</div><div class="rf-value">{product.get('sku','')}</div></div>
                <div class="rf-field"><div class="rf-label">EAN</div><div class="rf-value">{ean}</div></div>
                <div class="rf-field"><div class="rf-label">Unidad</div><div class="rf-value">{product.get('codigo_unidad','')}</div></div>
                <div class="rf-field"><div class="rf-label">Categoría</div><div class="rf-value">{product.get('nombre_categoria','')}</div></div>
                <div class="rf-field"><div class="rf-label">Aplica lote</div><div class="rf-value">{flag_lote}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
