from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterable

import streamlit as st


PALETTE = {
    "navy": "#142534",
    "navy_2": "#103541",
    "teal_dark": "#0E5663",
    "teal": "#18A999",
    "teal_soft": "#DDF7F3",
    "gold": "#F2C94C",
    "gold_soft": "#FFF4C7",
    "bg": "#F4FAFA",
    "surface": "#FFFFFF",
    "surface_2": "#F8FBFC",
    "border": "#DCE7EA",
    "muted": "#6B7A86",
    "danger": "#D64545",
}


def _asset_path(*parts: str) -> Path:
    return Path("assets", *parts)


def _find_logo_path() -> Path | None:
    candidates = [
        _asset_path("logo.png"),
        _asset_path("logo.webp"),
        _asset_path("logo.jpg"),
        _asset_path("logo.jpeg"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def get_asset_base64(path: str) -> str:
    asset = Path(path)
    if not asset.exists():
        return ""
    return base64.b64encode(asset.read_bytes()).decode("utf-8")


@st.cache_data(show_spinner=False)
def get_logo_base64() -> str:
    logo_path = _find_logo_path()
    if not logo_path:
        return ""
    return base64.b64encode(logo_path.read_bytes()).decode("utf-8")


def load_page_icon():
    """Logo local para favicon de Streamlit."""
    logo_path = _find_logo_path()
    if not logo_path:
        return "📦"
    try:
        from PIL import Image

        return Image.open(logo_path)
    except Exception:
        return str(logo_path)


def logo_img_html(width: int = 72, extra_style: str = "") -> str:
    encoded = get_logo_base64()
    if not encoded:
        return ""
    return (
        f'<img src="data:image/png;base64,{encoded}" '
        f'style="width:{width}px;height:auto;display:block;{extra_style}" />'
    )


def login_background_data_uri() -> str:
    """Fondo SVG liviano de almacén/racks, embebido como data URI."""
    svg = """
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 900'>
      <defs>
        <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0' stop-color='#eaf8f6'/>
          <stop offset='.52' stop-color='#f8fcfc'/>
          <stop offset='1' stop-color='#eef7f6'/>
        </linearGradient>
        <linearGradient id='rack' x1='0' y1='0' x2='0' y2='1'>
          <stop offset='0' stop-color='#0e5663' stop-opacity='.22'/>
          <stop offset='1' stop-color='#142534' stop-opacity='.06'/>
        </linearGradient>
      </defs>
      <rect width='1600' height='900' fill='url(#bg)'/>
      <circle cx='1320' cy='125' r='260' fill='#18A999' opacity='.10'/>
      <circle cx='250' cy='735' r='280' fill='#F2C94C' opacity='.09'/>
      <g opacity='.72'>
        <path d='M85 600 L515 410 L515 760 L85 860 Z' fill='url(#rack)'/>
        <path d='M1085 360 L1515 205 L1515 650 L1085 775 Z' fill='url(#rack)'/>
        <path d='M145 615 L495 465' stroke='#0E5663' stroke-opacity='.15' stroke-width='10'/>
        <path d='M145 690 L495 540' stroke='#0E5663' stroke-opacity='.12' stroke-width='8'/>
        <path d='M145 765 L495 615' stroke='#0E5663' stroke-opacity='.09' stroke-width='8'/>
        <path d='M1135 395 L1480 265' stroke='#0E5663' stroke-opacity='.15' stroke-width='10'/>
        <path d='M1135 480 L1480 350' stroke='#0E5663' stroke-opacity='.12' stroke-width='8'/>
        <path d='M1135 565 L1480 435' stroke='#0E5663' stroke-opacity='.09' stroke-width='8'/>
      </g>
      <g opacity='.30'>
        <rect x='105' y='618' width='55' height='42' rx='4' fill='#F2C94C'/>
        <rect x='178' y='588' width='52' height='39' rx='4' fill='#18A999'/>
        <rect x='252' y='554' width='58' height='43' rx='4' fill='#142534'/>
        <rect x='1165' y='397' width='58' height='43' rx='4' fill='#18A999'/>
        <rect x='1245' y='365' width='52' height='39' rx='4' fill='#F2C94C'/>
        <rect x='1320' y='336' width='58' height='43' rx='4' fill='#142534'/>
      </g>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def apply_global_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --wms-navy: {PALETTE['navy']};
            --wms-navy-2: {PALETTE['navy_2']};
            --wms-teal-dark: {PALETTE['teal_dark']};
            --wms-teal: {PALETTE['teal']};
            --wms-teal-soft: {PALETTE['teal_soft']};
            --wms-gold: {PALETTE['gold']};
            --wms-gold-soft: {PALETTE['gold_soft']};
            --wms-bg: {PALETTE['bg']};
            --wms-surface: {PALETTE['surface']};
            --wms-border: {PALETTE['border']};
            --wms-muted: {PALETTE['muted']};
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at top left, rgba(24,169,153,.12), transparent 32%),
                linear-gradient(135deg, #F7FCFC 0%, #F2FAF9 48%, #F8FBFC 100%) !important;
            color: var(--wms-navy);
        }}

        header[data-testid="stHeader"] {{
            background: rgba(255,255,255,.78) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(220,231,234,.78);
            min-height: 3.65rem;
            z-index: 999999;
        }}

        .block-container {{
            padding-top: 4.35rem !important;
            padding-bottom: 3rem;
            max-width: 1540px;
        }}

        h1, h2, h3 {{
            color: var(--wms-navy) !important;
            letter-spacing: -0.035em;
        }}

        h1 {{ font-weight: 850 !important; }}
        .stMarkdown p, label, .stCaptionContainer {{ color: #334155; }}

        section[data-testid="stSidebar"] {{
            background:
                radial-gradient(circle at 18% 8%, rgba(221,247,243,.16), transparent 26%),
                linear-gradient(180deg, #0D3140 0%, #123F4B 42%, #1C6570 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding-top: 1.2rem;
        }}

        section[data-testid="stSidebar"] * {{ color: rgba(255,255,255,.88) !important; }}
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: rgba(255,255,255,.88) !important; }}
        section[data-testid="stSidebar"] [data-testid="stHeader"] {{ background: transparent !important; }}

        section[data-testid="stSidebar"] details {{
            background: rgba(255,255,255,.055) !important;
            border: 1px solid rgba(255,255,255,.075) !important;
            border-radius: 16px !important;
            margin: .42rem 0 .68rem 0 !important;
            overflow: hidden;
        }}

        section[data-testid="stSidebar"] details summary {{
            padding: .55rem .65rem !important;
            font-weight: 820 !important;
            letter-spacing: .04em;
            text-transform: uppercase;
            font-size: .78rem !important;
            color: rgba(221,247,243,.92) !important;
        }}

        section[data-testid="stSidebar"] details summary:hover {{
            background: rgba(255,255,255,.055) !important;
        }}

        section[data-testid="stSidebar"] a {{
            border-radius: 12px !important;
            padding-top: .45rem !important;
            padding-bottom: .45rem !important;
            margin: .04rem .25rem !important;
            color: rgba(255,255,255,.84) !important;
            transition: all .15s ease-in-out;
        }}

        section[data-testid="stSidebar"] a:hover {{
            background: rgba(255,255,255,.08) !important;
            transform: translateX(2px);
        }}

        section[data-testid="stSidebar"] a[aria-current="page"] {{
            background: rgba(24,169,153,.24) !important;
            border-left: 4px solid var(--wms-gold);
            font-weight: 760;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] a span, section[data-testid="stSidebar"] a svg {{
            color: rgba(221,247,243,.92) !important;
            fill: rgba(221,247,243,.92) !important;
        }}

        .wms-sidebar-brand {{
            background: rgba(255,255,255,.07);
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 20px;
            padding: .9rem .85rem;
            margin: .15rem .05rem 1rem .05rem;
            display: flex;
            gap: .75rem;
            align-items: center;
            box-shadow: 0 14px 32px rgba(0,0,0,.12);
        }}

        .wms-sidebar-brand-logo {{
            width: 56px;
            height: 56px;
            border-radius: 16px;
            background: transparent;
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:visible;
            filter: drop-shadow(0 10px 16px rgba(0,0,0,.20));
        }}

        .wms-sidebar-title {{
            color: white;
            font-size: 1.05rem;
            font-weight: 850;
            line-height: 1.1;
        }}

        .wms-sidebar-subtitle {{
            color: rgba(255,255,255,.68) !important;
            font-size: .78rem;
            margin-top: .15rem;
        }}

        .wms-nav-section {{
            color: rgba(255,255,255,.58) !important;
            font-size: .74rem;
            font-weight: 800;
            letter-spacing: .085em;
            text-transform: uppercase;
            margin: 1rem .15rem .35rem .15rem;
        }}

        section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.15) !important; }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(245,251,251,.96));
            border: 1px solid var(--wms-border);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 14px 32px rgba(15, 74, 85, .08);
        }}

        div[data-testid="stMetric"] label {{ color: var(--wms-muted) !important; font-weight: 650; }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: var(--wms-teal-dark) !important; font-weight: 850; }}

        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--wms-teal-dark) !important;
            border-bottom-color: var(--wms-teal) !important;
            font-weight: 750;
        }}
        div[data-testid="stTabs"] button {{ color: #51616D !important; }}

        .stButton > button,
        .stDownloadButton > button,
        button[kind="primary"] {{
            border-radius: 12px !important;
            border: 1px solid rgba(14,86,99,.18) !important;
            font-weight: 760 !important;
            box-shadow: 0 10px 22px rgba(14,86,99,.11);
        }}
        .stButton > button[kind="primary"], button[kind="primary"] {{
            background: linear-gradient(135deg, var(--wms-teal-dark), var(--wms-teal)) !important;
            color: white !important;
        }}
        .stDownloadButton > button {{ background: white !important; color: var(--wms-teal-dark) !important; }}

        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--wms-border);
            box-shadow: 0 14px 32px rgba(15, 74, 85, .07);
            background: white;
        }}

        .wms-card {{
            background: rgba(255,255,255,.90);
            border: 1px solid var(--wms-border);
            border-radius: 20px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 18px 38px rgba(15,74,85,.08);
            backdrop-filter: blur(6px);
            margin-bottom: 1rem;
        }}

        .wms-card-title {{
            font-size: 1.06rem;
            font-weight: 820;
            color: var(--wms-navy);
            margin-bottom: .65rem;
            display: flex;
            gap: .5rem;
            align-items: center;
        }}

        .wms-soft-banner {{
            background: linear-gradient(135deg, rgba(24,169,153,.13), rgba(242,201,76,.13));
            border: 1px solid rgba(24,169,153,.16);
            border-radius: 20px;
            padding: 1rem 1.15rem;
            color: var(--wms-navy);
            margin-bottom: 1rem;
        }}

        .wms-page-kicker {{
            color: var(--wms-teal-dark);
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-size: .78rem;
        }}

        @media (max-width: 768px) {{
            .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 4rem !important; }}
            .wms-card {{ padding: 1rem; }}
            button {{ width: 100%; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_login_theme() -> None:
    logo_bg = login_background_data_uri()
    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"],
        div[data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
            transform: translateX(-100%) !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: url("{logo_bg}") center center / cover no-repeat fixed !important;
            margin-left: 0 !important;
        }}

        [data-testid="stAppViewContainer"] .main,
        section.main {{
            margin-left: 0 !important;
        }}

        header[data-testid="stHeader"] {{
            background: rgba(255,255,255,.72) !important;
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(220,231,234,.72);
            min-height: 3.65rem;
            z-index: 999999;
        }}

        .block-container {{
            max-width: 430px !important;
            padding-top: 6.25rem !important;
            padding-bottom: 3rem !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}

        div[data-testid="stForm"] {{
            background: rgba(255,255,255,.90) !important;
            border: 1px solid rgba(220,231,234,.92) !important;
            border-radius: 30px !important;
            box-shadow: 0 32px 78px rgba(20,37,52,.18) !important;
            padding: 1.85rem 1.85rem 1.4rem 1.85rem !important;
            backdrop-filter: blur(16px) !important;
        }}

        div[data-testid="stForm"] .stTextInput input {{
            background: rgba(246,250,251,.98) !important;
            border: 1px solid rgba(220,231,234,.95) !important;
            border-radius: 13px !important;
        }}

        div[data-testid="stForm"] .stFormSubmitButton > button {{
            width: 100% !important;
            border-radius: 13px !important;
            font-weight: 760 !important;
            min-height: 2.6rem;
        }}

        div[data-testid="stForm"] .stFormSubmitButton:first-of-type > button {{
            background: linear-gradient(135deg, var(--wms-teal-dark), var(--wms-teal)) !important;
            color: white !important;
            border: 1px solid rgba(14,86,99,.18) !important;
        }}

        .wms-login-brand {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 1.25rem;
        }}

        .wms-login-logo {{
            width: 112px;
            height: 112px;
            display:flex;
            align-items:center;
            justify-content:center;
            margin: 0 auto .95rem auto;
            background: transparent;
            filter: drop-shadow(0 18px 28px rgba(14,86,99,.18));
        }}

        .login-title {{
            text-align: center;
            font-size: 2.0rem;
            font-weight: 880;
            margin-bottom: .25rem;
            color: var(--wms-navy);
            letter-spacing: -0.05em;
        }}

        .login-subtitle {{
            text-align: center;
            color: var(--wms-muted);
            margin: 0 auto .6rem auto;
            max-width: 320px;
            line-height: 1.55;
        }}

        @media (max-width: 768px) {{
            .block-container {{
                max-width: 92vw !important;
                padding-top: 5rem !important;
            }}
            div[data-testid="stForm"] {{ padding: 1.35rem 1.2rem 1.15rem 1.2rem !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    logo = logo_img_html(width=54)
    st.markdown(
        f"""
        <div class="wms-sidebar-brand">
            <div class="wms-sidebar-brand-logo">{logo}</div>
            <div>
                <div class="wms-sidebar-title">App WMS Block B</div>
                <div class="wms-sidebar-subtitle">Insumos • Stock • Operaciones</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_nav(groups: Iterable[tuple[str, list[dict]]]) -> None:
    """Renderiza grupos del menú como desplegables contraídos por defecto."""
    for group_name, items in groups:
        if not items:
            continue
        with st.expander(group_name, expanded=False):
            for item in items:
                st.page_link(
                    item["path"],
                    label=item["title"],
                    icon=item.get("icon"),
                )


def card(title: str, body_html: str = "") -> None:
    st.markdown(
        f"""
        <div class="wms-card">
            <div class="wms-card-title">{title}</div>
            {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
