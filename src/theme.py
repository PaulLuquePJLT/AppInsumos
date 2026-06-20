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
        _asset_path("logo.jpg"),
        _asset_path("logo.jpeg"),
        _asset_path("logo.webp"),
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
    """Devuelve el logo local para usarlo como favicon de Streamlit."""
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
          <stop offset='.55' stop-color='#f7fbfb'/>
          <stop offset='1' stop-color='#eef7f6'/>
        </linearGradient>
        <linearGradient id='rack' x1='0' y1='0' x2='0' y2='1'>
          <stop offset='0' stop-color='#0e5663' stop-opacity='.22'/>
          <stop offset='1' stop-color='#142534' stop-opacity='.08'/>
        </linearGradient>
      </defs>
      <rect width='1600' height='900' fill='url(#bg)'/>
      <circle cx='1320' cy='130' r='260' fill='#18A999' opacity='.09'/>
      <circle cx='260' cy='720' r='280' fill='#F2C94C' opacity='.10'/>
      <g opacity='.72'>
        <path d='M90 600 L520 410 L520 760 L90 860 Z' fill='url(#rack)'/>
        <path d='M1080 360 L1510 205 L1510 650 L1080 775 Z' fill='url(#rack)'/>
        <path d='M145 615 L500 465' stroke='#0E5663' stroke-opacity='.16' stroke-width='10'/>
        <path d='M145 690 L500 540' stroke='#0E5663' stroke-opacity='.13' stroke-width='8'/>
        <path d='M145 765 L500 615' stroke='#0E5663' stroke-opacity='.10' stroke-width='8'/>
        <path d='M1130 395 L1480 265' stroke='#0E5663' stroke-opacity='.16' stroke-width='10'/>
        <path d='M1130 480 L1480 350' stroke='#0E5663' stroke-opacity='.13' stroke-width='8'/>
        <path d='M1130 565 L1480 435' stroke='#0E5663' stroke-opacity='.10' stroke-width='8'/>
      </g>
      <g opacity='.32'>
        <rect x='103' y='618' width='55' height='42' rx='4' fill='#F2C94C'/>
        <rect x='175' y='588' width='52' height='39' rx='4' fill='#18A999'/>
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

        .block-container {{
            padding-top: 2.0rem;
            padding-bottom: 3rem;
            max-width: 1540px;
        }}

        header[data-testid="stHeader"] {{
            background: rgba(255,255,255,.70) !important;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(220,231,234,.65);
        }}

        h1, h2, h3 {{
            color: var(--wms-navy) !important;
            letter-spacing: -0.035em;
        }}

        h1 {{ font-weight: 850 !important; }}
        .stMarkdown p, label, .stCaptionContainer {{ color: #334155; }}

        section[data-testid="stSidebar"] {{
            background:
                radial-gradient(circle at 25% 12%, rgba(24,169,153,.22), transparent 24%),
                linear-gradient(180deg, #0E313C 0%, #123D49 46%, #1B5861 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding-top: 1.35rem;
        }}

        section[data-testid="stSidebar"] * {{ color: rgba(255,255,255,.88) !important; }}
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color: rgba(255,255,255,.88) !important; }}
        section[data-testid="stSidebar"] [data-testid="stHeader"] {{ background: transparent !important; }}

        section[data-testid="stSidebar"] a {{
            border-radius: 13px !important;
            padding-top: .48rem !important;
            padding-bottom: .48rem !important;
            margin: .05rem 0 !important;
            color: rgba(255,255,255,.84) !important;
            transition: all .15s ease-in-out;
        }}

        section[data-testid="stSidebar"] a:hover {{
            background: rgba(255,255,255,.08) !important;
            transform: translateX(2px);
        }}

        section[data-testid="stSidebar"] a[aria-current="page"] {{
            background: rgba(24,169,153,.22) !important;
            border-left: 4px solid var(--wms-gold);
            font-weight: 760;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] a span, section[data-testid="stSidebar"] a svg {{
            color: rgba(221,247,243,.92) !important;
            fill: rgba(221,247,243,.92) !important;
        }}

        .wms-sidebar-brand {{
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 20px;
            padding: .85rem .85rem;
            margin: .2rem .05rem 1rem .05rem;
            display: flex;
            gap: .75rem;
            align-items: center;
            box-shadow: 0 14px 32px rgba(0,0,0,.12);
        }}

        .wms-sidebar-brand-logo {{
            width: 54px;
            height: 54px;
            border-radius: 16px;
            background: rgba(255,255,255,.88);
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:hidden;
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
            .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
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
        }}

        [data-testid="stAppViewContainer"] {{
            background:
                linear-gradient(90deg, rgba(14,49,60,.92) 0%, rgba(14,49,60,.88) 16%, rgba(14,49,60,0) 16.2%),
                url("{logo_bg}") center center / cover no-repeat !important;
        }}

        .block-container {{
            max-width: 460px !important;
            padding-top: 7.5vh !important;
            padding-bottom: 3rem !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}

        .wms-login-wrapper {{
            background: rgba(255,255,255,.88);
            border: 1px solid rgba(220,231,234,.90);
            border-radius: 30px;
            box-shadow: 0 32px 78px rgba(20,37,52,.18);
            padding: 1.75rem 1.8rem 1.25rem 1.8rem;
            backdrop-filter: blur(14px);
        }}

        .wms-login-logo-card {{
            width: 118px;
            height: 118px;
            border-radius: 24px;
            background: linear-gradient(145deg, rgba(255,255,255,.96), rgba(221,247,243,.78));
            border: 1px solid rgba(220,231,234,.9);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1.05rem auto;
            box-shadow: 0 18px 40px rgba(14,86,99,.12);
            overflow: hidden;
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
            margin: 0 auto 1.45rem auto;
            max-width: 320px;
            line-height: 1.55;
        }}

        .wms-login-wrapper .stButton > button,
        .wms-login-wrapper .stFormSubmitButton > button {{
            width: 100%;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    logo = logo_img_html(width=46)
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
    for group_name, items in groups:
        if not items:
            continue
        st.markdown(f'<div class="wms-nav-section">{group_name}</div>', unsafe_allow_html=True)
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
