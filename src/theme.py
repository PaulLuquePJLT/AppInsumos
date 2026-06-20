from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


PALETTE = {
    "navy": "#142534",
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


def _find_logo_path() -> Path | None:
    candidates = [
        Path("assets/logo.png"),
        Path("assets/logo.jpg"),
        Path("assets/logo.jpeg"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def get_logo_base64() -> str:
    logo_path = _find_logo_path()
    if not logo_path:
        return ""
    return base64.b64encode(logo_path.read_bytes()).decode("utf-8")


def logo_img_html(width: int = 72, extra_style: str = "") -> str:
    encoded = get_logo_base64()
    if not encoded:
        return ""
    return (
        f'<img src="data:image/png;base64,{encoded}" '
        f'style="width:{width}px;height:auto;display:block;{extra_style}" />'
    )


def apply_global_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --wms-navy: {PALETTE['navy']};
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
                radial-gradient(circle at top left, rgba(24,169,153,.14), transparent 30%),
                linear-gradient(135deg, #F7FCFC 0%, #F2FAF9 42%, #F8FBFC 100%) !important;
            color: var(--wms-navy);
        }}

        .block-container {{
            padding-top: 2.1rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}

        h1, h2, h3 {{
            color: var(--wms-navy) !important;
            letter-spacing: -0.035em;
        }}

        h1 {{
            font-weight: 850 !important;
        }}

        .stMarkdown p, label, .stCaptionContainer {{
            color: #334155;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #102F3B 0%, #173F4A 52%, #122E38 100%) !important;
            border-right: 1px solid rgba(255,255,255,.08);
        }}

        section[data-testid="stSidebar"] * {{
            color: rgba(255,255,255,.88) !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: rgba(255,255,255,.88) !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        section[data-testid="stSidebar"] a,
        section[data-testid="stSidebar"] button {{
            border-radius: 12px !important;
        }}

        section[data-testid="stSidebar"] a[aria-current="page"] {{
            background: rgba(24,169,153,.23) !important;
            border-left: 4px solid var(--wms-gold);
            font-weight: 700;
        }}

        section[data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,.16) !important;
        }}

        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(245,251,251,.96));
            border: 1px solid var(--wms-border);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 14px 32px rgba(15, 74, 85, .08);
        }}

        div[data-testid="stMetric"] label {{
            color: var(--wms-muted) !important;
            font-weight: 650;
        }}

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: var(--wms-teal-dark) !important;
            font-weight: 850;
        }}

        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--wms-teal-dark) !important;
            border-bottom-color: var(--wms-teal) !important;
            font-weight: 750;
        }}

        div[data-testid="stTabs"] button {{
            color: #51616D !important;
        }}

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

        .stDownloadButton > button {{
            background: white !important;
            color: var(--wms-teal-dark) !important;
        }}

        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--wms-border);
            box-shadow: 0 14px 32px rgba(15, 74, 85, .07);
            background: white;
        }}

        .wms-card {{
            background: rgba(255,255,255,.88);
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

        .wms-sidebar-brand {{
            display: flex;
            gap: .7rem;
            align-items: center;
            padding: .8rem .15rem 1rem .15rem;
            margin-bottom: .35rem;
        }}

        .wms-sidebar-title {{
            color: white;
            font-size: 1.05rem;
            font-weight: 850;
            line-height: 1.1;
        }}

        .wms-sidebar-subtitle {{
            color: rgba(255,255,255,.62);
            font-size: .78rem;
            margin-top: .15rem;
        }}

        .wms-login-wrapper {{
            background: rgba(255,255,255,.83);
            border: 1px solid rgba(220,231,234,.8);
            border-radius: 28px;
            box-shadow: 0 28px 60px rgba(20,37,52,.12);
            padding: 2rem 2rem 1.4rem 2rem;
            backdrop-filter: blur(8px);
        }}

        .wms-login-logo {{
            display: flex;
            justify-content: center;
            margin-bottom: .7rem;
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


def render_sidebar_brand() -> None:
    logo = logo_img_html(width=42)
    st.markdown(
        f"""
        <div class="wms-sidebar-brand">
            <div>{logo}</div>
            <div>
                <div class="wms-sidebar-title">AppInsumos</div>
                <div class="wms-sidebar-subtitle">Mini WMS</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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
