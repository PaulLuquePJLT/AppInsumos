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
    login_form_css = """
        /* Login RF: tarjeta única, compacta y centrada horizontalmente. */
        .block-container {
            width: min(92vw, 400px) !important;
            max-width: 400px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: .75rem !important;
            padding-right: .75rem !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            width: min(88vw, 380px) !important;
            max-width: 380px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            background: rgba(255,255,255,.92) !important;
            border: 1px solid rgba(220,231,234,.95) !important;
            border-radius: 28px !important;
            box-shadow: 0 28px 72px rgba(20,37,52,.18) !important;
            padding: 1.35rem 1.15rem 1.18rem 1.15rem !important;
            backdrop-filter: blur(16px) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background: transparent !important;
            border: 0 !important;
            padding: 0 !important;
        }

        div[data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
    """ if login else """
        div[data-testid="stForm"] {
            border: 0 !important;
            background: transparent !important;
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

        {login_form_css}

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

        .rf-product-ok {{ border-left: 6px solid var(--rf-teal); }}
        .rf-product-error {{ border-left: 6px solid var(--rf-danger); }}

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

        .rf-task-counter {{
            text-align:right;
            color: var(--rf-teal-dark);
            font-weight:900;
            letter-spacing:.02em;
            margin-top:-.5rem;
            margin-bottom:.5rem;
        }}

        .rf-task-main {{
            background: rgba(255,255,255,.94);
            border-radius: 24px;
            border: 1px solid rgba(220,231,234,.95);
            box-shadow: 0 20px 44px rgba(15,74,85,.12);
            padding: 1.05rem;
            margin-bottom: 1rem;
        }}

        .rf-task-big-label {{
            color: var(--rf-muted);
            text-transform: uppercase;
            font-size: .70rem;
            font-weight: 850;
            letter-spacing: .06em;
        }}

        .rf-task-big-value {{
            color: var(--rf-navy);
            font-size: 1.65rem;
            font-weight: 950;
            line-height: 1.05;
            margin-bottom: .65rem;
        }}

        .rf-picking-card {{
            background: rgba(255,255,255,.92);
            border: 1px solid rgba(220,231,234,.92);
            border-left: 6px solid var(--rf-teal);
            border-radius: 22px;
            padding: .95rem;
            box-shadow: 0 16px 36px rgba(15,74,85,.10);
            margin-bottom: .85rem;
        }}

        .rf-picking-title {{
            color: var(--rf-navy);
            font-size: 1.25rem;
            font-weight: 950;
            margin-bottom: .2rem;
        }}

        .rf-picking-sub {{
            color: var(--rf-muted);
            font-size: .84rem;
            font-weight: 650;
            line-height: 1.35;
        }}

        .rf-pill-row {{
            display:flex;
            flex-wrap:wrap;
            gap:.35rem;
            margin-top:.75rem;
        }}

        .rf-pill {{
            background: rgba(24,169,153,.12);
            color: var(--rf-teal-dark);
            border: 1px solid rgba(24,169,153,.16);
            border-radius: 999px;
            padding: .30rem .55rem;
            font-size: .75rem;
            font-weight: 850;
        }}

        section[data-testid="stSidebar"] {{
            width: min(58vw, 310px) !important;
            min-width: min(58vw, 310px) !important;
            max-width: min(58vw, 310px) !important;
            background: linear-gradient(180deg, #0D3140 0%, #123F4B 45%, #1C6570 100%) !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: rgba(255,255,255,.92) !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding: .75rem .65rem .85rem .65rem !important;
        }}

        .rf-sidebar-logo {{
            display:flex;
            align-items:center;
            justify-content:center;
            padding: .45rem .15rem .70rem .15rem !important;
            margin-bottom: .10rem !important;
        }}

        section[data-testid="stSidebar"] details,
        section[data-testid="stSidebar"] details[open] {{
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            margin: .12rem 0 .20rem 0 !important;
            padding: 0 !important;
            box-shadow: none !important;
        }}

        section[data-testid="stSidebar"] details summary {{
            padding: .12rem .05rem .10rem .05rem !important;
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            color: rgba(221,247,243,.90) !important;
            font-size: .72rem !important;
            font-weight: 900 !important;
            letter-spacing: .075em !important;
            text-transform: uppercase !important;
        }}

        section[data-testid="stSidebar"] details summary:hover {{
            background: transparent !important;
            color: #FFFFFF !important;
        }}

        section[data-testid="stSidebar"] details summary * {{
            color: rgba(221,247,243,.90) !important;
        }}

        section[data-testid="stSidebar"] .stButton {{ margin: 0 !important; }}

        section[data-testid="stSidebar"] .stButton > button {{
            justify-content: flex-start !important;
            text-align: left !important;
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            padding: .12rem .35rem .12rem .95rem !important;
            margin: .01rem 0 !important;
            border-radius: 6px !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            color: rgba(255,255,255,.90) !important;
            font-size: .86rem !important;
            font-weight: 690 !important;
        }}

        section[data-testid="stSidebar"] .stButton > button div,
        section[data-testid="stSidebar"] .stButton > button p {{
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}

        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255,255,255,.08) !important;
            color: #FFFFFF !important;
            transform: none !important;
        }}

        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] button[kind="primary"] {{
            background: rgba(24,169,153,.20) !important;
            border-left: 3px solid var(--rf-gold) !important;
            color: #FFFFFF !important;
            font-weight: 820 !important;
        }}

        .rf-session-simple {{
            margin: .85rem .15rem 0 .15rem !important;
            padding-top: .50rem !important;
            border-top: 1px solid rgba(255,255,255,.12) !important;
        }}

        .rf-session-label {{
            color: rgba(221,247,243,.62) !important;
            font-size: .65rem !important;
            font-weight: 850 !important;
            text-transform: uppercase !important;
            letter-spacing: .075em !important;
        }}

        .rf-session-user {{
            color: rgba(255,255,255,.94) !important;
            font-size: .86rem !important;
            font-weight: 780 !important;
            line-height: 1.18 !important;
            margin-top: .18rem !important;
        }}

        .rf-session-role {{
            color: rgba(221,247,243,.68) !important;
            font-size: .72rem !important;
            margin-top: .10rem !important;
        }}

        [data-testid="stDataFrame"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--rf-border);
            background:white;
        }}

        .rf-home-hero {{
            min-height: calc(100vh - 7rem);
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            text-align:center;
            padding: 1.25rem;
            border-radius: 30px;
            background:
                radial-gradient(circle at 50% 20%, rgba(255,255,255,.92), rgba(255,255,255,.62) 42%, rgba(221,247,243,.38) 100%);
            border: 1px solid rgba(220,231,234,.55);
            box-shadow: 0 28px 72px rgba(20,37,52,.12);
            backdrop-filter: blur(10px);
        }}

        .rf-home-logo {{
            width: 150px;
            height: 150px;
            display:flex;
            align-items:center;
            justify-content:center;
            margin-bottom: 1rem;
            filter: drop-shadow(0 22px 30px rgba(14,86,99,.20));
        }}

        .rf-home-title {{
            color: var(--rf-navy);
            font-size: clamp(2rem, 8vw, 3rem);
            line-height: 1.02;
            font-weight: 950;
            letter-spacing: -.06em;
        }}

        .rf-home-subtitle {{
            color: var(--rf-muted);
            font-size: 1rem;
            font-weight: 700;
            margin-top: .55rem;
            margin-bottom: 1.2rem;
        }}

        .rf-home-grid {{
            display:flex;
            flex-wrap:wrap;
            justify-content:center;
            gap:.55rem;
            margin: .35rem auto 1.05rem auto;
            max-width: 420px;
        }}

        .rf-home-chip {{
            background: rgba(24,169,153,.12);
            border: 1px solid rgba(24,169,153,.18);
            color: var(--rf-teal-dark);
            font-weight: 850;
            border-radius: 999px;
            padding: .48rem .8rem;
            font-size: .86rem;
        }}

        .rf-home-help {{
            color: var(--rf-muted);
            font-weight: 650;
            max-width: 360px;
            line-height: 1.45;
        }}


        /* RF compact mode: compact widgets and align menu. */

        h1 {{
            font-size: clamp(2.05rem, 8vw, 2.65rem) !important;
            line-height: .98 !important;
            margin-bottom: .25rem !important;
        }}

        .block-container {{
            padding-top: 4.0rem !important;
            padding-left: .85rem !important;
            padding-right: .85rem !important;
            padding-bottom: 1.25rem !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: .25rem !important;
        }}

        .stTabs button {{
            font-size: .86rem !important;
            padding: .25rem .35rem !important;
        }}

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stDateInput label,
        .stNumberInput label {{
            font-size: .82rem !important;
            font-weight: 700 !important;
            margin-bottom: .10rem !important;
        }}

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] > div,
        .stDateInput input {{
            min-height: 2.28rem !important;
            height: 2.28rem !important;
            font-size: .88rem !important;
            border-radius: 12px !important;
        }}

        .stTextArea textarea {{
            min-height: 4.6rem !important;
            height: 4.6rem !important;
        }}

        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {{
            min-height: 2.38rem !important;
            height: 2.38rem !important;
            border-radius: 12px !important;
            font-size: .88rem !important;
            padding-top: .18rem !important;
            padding-bottom: .18rem !important;
        }}

        .rf-card,
        .rf-picking-card,
        .rf-task-main {{
            padding: .72rem !important;
            border-radius: 18px !important;
            margin-bottom: .62rem !important;
        }}

        .rf-card-compact {{
            padding: .58rem !important;
        }}

        .rf-kicker {{
            font-size: .64rem !important;
            letter-spacing: .05em !important;
        }}

        .rf-product-title {{
            font-size: .92rem !important;
            margin: .18rem 0 .35rem 0 !important;
        }}

        .rf-grid {{
            gap: .35rem !important;
        }}

        .rf-grid-compact {{
            grid-template-columns: 1fr 1fr !important;
            gap: .28rem !important;
        }}

        .rf-field {{
            padding: .34rem .42rem !important;
            border-radius: 11px !important;
        }}

        .rf-label {{
            font-size: .58rem !important;
        }}

        .rf-value {{
            font-size: .74rem !important;
            line-height: 1.15 !important;
        }}

        .rf-task-header {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:.5rem;
            margin-bottom:.38rem;
        }}

        .rf-task-pk {{
            color: var(--rf-muted);
            font-size: .70rem;
            font-weight: 850;
        }}

        .rf-task-counter {{
            margin:0 !important;
            text-align:right;
            color: var(--rf-teal-dark);
            font-size:.78rem;
            font-weight:950;
            background: rgba(24,169,153,.12);
            border: 1px solid rgba(24,169,153,.15);
            padding:.18rem .45rem;
            border-radius:999px;
        }}

        .rf-task-row {{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap:.55rem;
            align-items:start;
        }}

        .rf-task-big-label {{
            font-size: .58rem !important;
            letter-spacing: .045em !important;
        }}

        .rf-task-big-value {{
            font-size: 1.18rem !important;
            margin-bottom: .35rem !important;
        }}

        .rf-location-value {{
            font-size: 1.35rem !important;
        }}

        .rf-qty-value {{
            font-size: 1.05rem !important;
        }}

        .rf-task-product {{
            color: var(--rf-navy);
            font-size:.86rem;
            font-weight:850;
            line-height:1.15;
            margin: .08rem 0 .42rem 0;
        }}

        section[data-testid="stSidebar"] {{
            width: min(58vw, 305px) !important;
            min-width: min(58vw, 305px) !important;
            max-width: min(58vw, 305px) !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            justify-content: flex-start !important;
            text-align: left !important;
            min-height: 1.95rem !important;
            height: 1.95rem !important;
            padding: .10rem .30rem .10rem .58rem !important;
            margin: .005rem 0 !important;
            border-radius: 7px !important;
            font-size: .78rem !important;
            line-height:1.0 !important;
        }}

        section[data-testid="stSidebar"] .stButton > button div,
        section[data-testid="stSidebar"] .stButton > button p {{
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}

        #MainMenu {{ visibility: hidden; }}

        /* Ajustes finales RF: expander nativo compacto con flecha visible y funciones sangradas. */
        section[data-testid="stSidebar"] details {{
            margin: .14rem 0 .42rem 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
        }}

        section[data-testid="stSidebar"] details summary {{
            padding: .18rem .05rem .16rem .05rem !important;
            background: transparent !important;
            border: 0 !important;
            font-size: .74rem !important;
            font-weight: 900 !important;
            letter-spacing: .075em !important;
            text-transform: uppercase !important;
        }}

        section[data-testid="stSidebar"] details summary svg,
        section[data-testid="stSidebar"] details summary * {{
            color: rgba(221,247,243,.92) !important;
            fill: rgba(221,247,243,.92) !important;
        }}

        section[data-testid="stSidebar"] details .stButton > button {{
            padding-left: 1.15rem !important;
            justify-content: flex-start !important;
            text-align: left !important;
        }}

        section[data-testid="stSidebar"] details .stButton > button p,
        section[data-testid="stSidebar"] details .stButton > button div {{
            text-align: left !important;
            justify-content: flex-start !important;
        }}

        {sidebar_css}

        @media (max-width: 640px) {{
            .block-container {{
                max-width: 100vw !important;
                padding-top: 4.25rem !important;
            }}
            div[data-testid="stForm"] {{
                padding: 1.35rem 1rem 1.2rem 1rem !important;
                border-radius: 24px !important;
            }}
            .rf-grid {{ grid-template-columns: 1fr; }}
        }}


        /* Ajustes RF finales: compactar home, menú y picking. */

        section[data-testid="stSidebar"] {{
            width: min(58vw, 300px) !important;
            min-width: min(58vw, 300px) !important;
            max-width: min(58vw, 300px) !important;
        }}

        section[data-testid="stSidebar"] details,
        section[data-testid="stSidebar"] details[open] {{
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            margin: .05rem 0 .25rem 0 !important;
            padding: 0 !important;
        }}

        section[data-testid="stSidebar"] details summary {{
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            padding: .15rem .05rem .12rem .05rem !important;
            color: rgba(221,247,243,.92) !important;
            font-size: .72rem !important;
            font-weight: 920 !important;
            letter-spacing: .075em !important;
            text-transform: uppercase !important;
        }}

        section[data-testid="stSidebar"] details summary:hover {{
            background: transparent !important;
            color: #FFFFFF !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            justify-content: flex-start !important;
            text-align: left !important;
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            padding: .12rem .35rem .12rem 1.15rem !important;
            margin: .01rem 0 !important;
            border-radius: 6px !important;
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            color: rgba(255,255,255,.90) !important;
            font-size: .86rem !important;
            font-weight: 700 !important;
        }}

        section[data-testid="stSidebar"] .stButton > button div,
        section[data-testid="stSidebar"] .stButton > button p {{
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}

        section[data-testid="stSidebar"] .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] button[kind="primary"] {{
            background: rgba(24,169,153,.20) !important;
            border-left: 3px solid var(--rf-gold) !important;
            color: #FFFFFF !important;
            font-weight: 830 !important;
        }}

        .rf-home-hero {{
            min-height: auto !important;
            padding: .85rem !important;
            border-radius: 22px !important;
            margin-top: .25rem !important;
        }}

        .rf-home-logo {{
            width: 88px !important;
            height: 88px !important;
            margin-bottom: .55rem !important;
        }}

        .rf-home-title {{
            font-size: clamp(1.45rem, 6.3vw, 2rem) !important;
            letter-spacing: -.045em !important;
        }}

        .rf-home-subtitle {{
            font-size: .78rem !important;
            margin-top: .25rem !important;
            margin-bottom: .55rem !important;
        }}

        .rf-home-grid {{
            gap: .25rem !important;
            margin: .15rem auto .55rem auto !important;
        }}

        .rf-home-chip {{
            padding: .25rem .45rem !important;
            font-size: .70rem !important;
        }}

        .rf-home-help {{
            font-size: .76rem !important;
            line-height: 1.25 !important;
        }}

        .rf-task-main {{
            padding: .62rem !important;
            border-radius: 16px !important;
            margin-bottom: .48rem !important;
        }}

        .rf-task-header {{
            display:flex !important;
            align-items:center !important;
            justify-content:space-between !important;
            gap:.35rem !important;
            margin-bottom:.35rem !important;
        }}

        .rf-task-counter {{
            margin:0 !important;
            text-align:right !important;
            font-size:.78rem !important;
            color: var(--rf-teal-dark) !important;
            font-weight:900 !important;
        }}

        .rf-task-pk {{
            font-size:.78rem !important;
            font-weight:900 !important;
            color: var(--rf-navy) !important;
        }}

        .rf-task-big-label {{ font-size:.60rem !important; }}
        .rf-task-big-value {{ font-size:1.25rem !important; margin-bottom:.35rem !important; }}
        .rf-task-product {{ font-size:.86rem !important; line-height:1.2 !important; margin-bottom:.35rem !important; font-weight:800 !important; }}
        .rf-field {{ padding:.38rem .44rem !important; border-radius:10px !important; }}
        .rf-label {{ font-size:.58rem !important; }}
        .rf-value {{ font-size:.72rem !important; line-height:1.15 !important; }}


        /* ==========================================================
           Zebra MC3300X / RF safe compact layout
           No oculta contenedores de Streamlit; solo reduce tamaños.
           ========================================================== */
        @media (max-width: 900px) {{
            header[data-testid="stHeader"] {{
                min-height: 2.45rem !important;
                height: 2.45rem !important;
            }}

            .block-container {{
                max-width: 100vw !important;
                padding-top: 2.95rem !important;
                padding-left: .42rem !important;
                padding-right: .42rem !important;
                padding-bottom: .60rem !important;
            }}

            h1 {{
                font-size: 1.12rem !important;
                line-height: 1.02 !important;
                margin: .04rem 0 .18rem 0 !important;
            }}
            h2 {{ font-size: 1.00rem !important; margin: .08rem 0 .12rem 0 !important; }}
            h3 {{ font-size: .90rem !important; margin: .06rem 0 .10rem 0 !important; }}

            .stCaptionContainer,
            [data-testid="stCaptionContainer"],
            .stMarkdown p {{
                font-size: .70rem !important;
                line-height: 1.16 !important;
                margin-bottom: .10rem !important;
            }}

            .stTabs [data-baseweb="tab-list"] {{
                gap: .10rem !important;
                margin-bottom: .20rem !important;
            }}
            .stTabs button {{
                font-size: .70rem !important;
                min-height: 1.42rem !important;
                padding: .12rem .16rem !important;
            }}
            .stTabs button p {{ font-size: .70rem !important; }}

            .stTextInput label,
            .stTextArea label,
            .stSelectbox label,
            .stDateInput label,
            .stNumberInput label {{
                font-size: .66rem !important;
                line-height: 1.0 !important;
                margin-bottom: .03rem !important;
            }}

            .stTextInput input,
            .stNumberInput input,
            .stDateInput input,
            .stTextArea textarea,
            .stSelectbox [data-baseweb="select"] > div {{
                min-height: 1.78rem !important;
                height: 1.78rem !important;
                font-size: .72rem !important;
                border-radius: 9px !important;
                padding-top: .06rem !important;
                padding-bottom: .06rem !important;
            }}
            .stSelectbox [data-baseweb="select"] span,
            .stSelectbox [data-baseweb="select"] div {{
                font-size: .72rem !important;
                line-height: 1.0 !important;
            }}
            .stTextArea textarea {{
                min-height: 2.35rem !important;
                height: 2.35rem !important;
            }}

            .stButton > button,
            .stFormSubmitButton > button,
            .stDownloadButton > button {{
                min-height: 1.86rem !important;
                height: 1.86rem !important;
                border-radius: 9px !important;
                font-size: .72rem !important;
                line-height: 1.0 !important;
                padding: .08rem .24rem !important;
                margin-top: .02rem !important;
                margin-bottom: .02rem !important;
            }}

            .rf-card,
            .rf-picking-card,
            .rf-task-main {{
                padding: .48rem !important;
                border-radius: 13px !important;
                margin-bottom: .32rem !important;
                box-shadow: 0 8px 18px rgba(15,74,85,.08) !important;
            }}
            .rf-card-compact {{ padding: .40rem !important; }}
            .rf-kicker {{ font-size: .54rem !important; letter-spacing: .04em !important; }}
            .rf-product-title {{ font-size: .76rem !important; line-height: 1.08 !important; margin: .08rem 0 .18rem 0 !important; }}
            .rf-grid,
            .rf-grid-compact {{ grid-template-columns: 1fr 1fr !important; gap: .18rem !important; }}
            .rf-field {{ padding: .22rem .26rem !important; border-radius: 8px !important; }}
            .rf-label {{ font-size: .50rem !important; line-height: .98 !important; }}
            .rf-value {{ font-size: .62rem !important; line-height: 1.08 !important; margin-top: .05rem !important; }}

            .rf-task-header {{ margin-bottom: .18rem !important; gap: .20rem !important; }}
            .rf-task-pk {{ font-size: .58rem !important; line-height: 1.0 !important; }}
            .rf-task-counter {{ font-size: .58rem !important; padding: .08rem .28rem !important; }}
            .rf-task-row {{ grid-template-columns: 1fr 1fr !important; gap: .22rem !important; }}
            .rf-task-big-label {{ font-size: .50rem !important; line-height: 1.0 !important; }}
            .rf-task-big-value {{ font-size: .92rem !important; line-height: 1.0 !important; margin-bottom: .16rem !important; }}
            .rf-location-value {{ font-size: 1.08rem !important; }}
            .rf-qty-value {{ font-size: .88rem !important; }}
            .rf-task-product {{ font-size: .66rem !important; line-height: 1.08 !important; margin: .02rem 0 .18rem 0 !important; }}

            .rf-picking-card {{ border-left-width: 4px !important; }}
            .rf-picking-title {{ font-size: .88rem !important; margin-bottom: .05rem !important; }}
            .rf-picking-sub {{ font-size: .62rem !important; line-height: 1.10 !important; }}
            .rf-pill-row {{ gap:.14rem !important; margin-top:.30rem !important; }}
            .rf-pill {{ font-size: .54rem !important; padding: .14rem .28rem !important; }}

            .rf-home-hero {{
                min-height: auto !important;
                padding: .58rem !important;
                border-radius: 16px !important;
                margin-top: .15rem !important;
            }}
            .rf-home-logo {{ width: 64px !important; height: 64px !important; margin-bottom: .32rem !important; }}
            .rf-home-logo img {{ width: 64px !important; }}
            .rf-home-title {{ font-size: 1.22rem !important; line-height: 1.0 !important; }}
            .rf-home-subtitle {{ font-size: .62rem !important; margin-top: .14rem !important; margin-bottom: .35rem !important; }}
            .rf-home-grid {{ gap: .14rem !important; margin: .12rem auto .32rem auto !important; max-width: 280px !important; }}
            .rf-home-chip {{ font-size: .54rem !important; padding: .13rem .28rem !important; }}
            .rf-home-help {{ font-size: .58rem !important; line-height: 1.15 !important; max-width: 270px !important; }}

            .rf-login-brand {{ margin-bottom: .44rem !important; }}
            .rf-login-brand img {{ width: 66px !important; }}
            .rf-login-title {{ font-size: 1.16rem !important; line-height: 1.0 !important; margin-top: .24rem !important; }}
            .rf-login-subtitle {{ font-size: .60rem !important; line-height: 1.12 !important; margin-top: .14rem !important; }}
            div[data-testid="stVerticalBlockBorderWrapper"] {{
                width: min(86vw, 320px) !important;
                max-width: 320px !important;
                padding: .62rem .62rem .56rem .62rem !important;
                border-radius: 16px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }}

            section[data-testid="stSidebar"] {{
                width: min(58vw, 250px) !important;
                min-width: min(58vw, 250px) !important;
                max-width: min(58vw, 250px) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
                padding: .48rem .42rem .58rem .42rem !important;
            }}
            .rf-sidebar-logo {{ padding: .20rem .05rem .28rem .05rem !important; margin-bottom: .02rem !important; }}
            .rf-sidebar-logo img {{ width: 52px !important; }}
            section[data-testid="stSidebar"] details {{ margin: .05rem 0 .10rem 0 !important; }}
            section[data-testid="stSidebar"] details summary {{
                padding: .06rem .02rem .05rem .02rem !important;
                font-size: .58rem !important;
                line-height: 1.0 !important;
                letter-spacing: .055em !important;
            }}
            section[data-testid="stSidebar"] .stButton > button {{
                min-height: 1.50rem !important;
                height: 1.50rem !important;
                padding: .05rem .22rem .05rem .75rem !important;
                font-size: .64rem !important;
                border-radius: 5px !important;
            }}
            .rf-session-simple {{ margin: .38rem .08rem 0 .08rem !important; padding-top: .30rem !important; }}
            .rf-session-label {{ font-size: .50rem !important; }}
            .rf-session-user {{ font-size: .64rem !important; line-height: 1.06 !important; }}
            .rf-session-role {{ font-size: .54rem !important; }}

            [data-testid="stDataFrame"] {{ border-radius: 10px !important; font-size: .60rem !important; }}
            .stAlert {{ padding: .28rem .38rem !important; font-size: .62rem !important; }}
        }}

        @media (max-height: 560px) {{
            .block-container {{ padding-top: 2.50rem !important; padding-bottom: .30rem !important; }}
            h1 {{ font-size: 1.02rem !important; }}
            .rf-card, .rf-picking-card, .rf-task-main {{ margin-bottom: .22rem !important; }}
            .stTextArea textarea {{ min-height: 1.95rem !important; height: 1.95rem !important; }}
            .rf-task-big-value {{ font-size: .84rem !important; }}
            .rf-location-value {{ font-size: .98rem !important; }}
            .rf-qty-value {{ font-size: .80rem !important; }}
        }}


        /* ==========================================================
           FIX RF: compactar fondo gris de inputs y evitar corte del texto
           ========================================================== */
        div[data-testid="stTextInput"],
        div[data-testid="stNumberInput"],
        div[data-testid="stDateInput"],
        div[data-testid="stTextArea"],
        div[data-testid="stSelectbox"] {{
            margin-bottom: .18rem !important;
        }}

        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stNumberInput"] div[data-baseweb="input"],
        div[data-testid="stDateInput"] div[data-baseweb="input"],
        div[data-baseweb="input"] {{
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            border-radius: 10px !important;
            background: rgba(248,251,252,.98) !important;
            border: 1px solid rgba(220,231,234,.95) !important;
            box-shadow: 0 4px 10px rgba(20,37,52,.04) !important;
            overflow: hidden !important;
        }}

        div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
        div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
        div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
        div[data-baseweb="input"] > div {{
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            background: transparent !important;
        }}

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-baseweb="input"] input {{
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            font-size: .78rem !important;
            line-height: 1 !important;
            padding: .08rem .42rem !important;
            background: transparent !important;
        }}

        div[data-testid="stTextArea"] div[data-baseweb="textarea"],
        div[data-baseweb="textarea"] {{
            min-height: 3.05rem !important;
            height: 3.05rem !important;
            border-radius: 10px !important;
            background: rgba(248,251,252,.98) !important;
            border: 1px solid rgba(220,231,234,.95) !important;
            box-shadow: 0 4px 10px rgba(20,37,52,.04) !important;
            overflow: hidden !important;
        }}

        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="textarea"] textarea {{
            min-height: 3.05rem !important;
            height: 3.05rem !important;
            font-size: .78rem !important;
            line-height: 1.1 !important;
            padding: .34rem .42rem !important;
            background: transparent !important;
        }}

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div {{
            min-height: 2.05rem !important;
            height: 2.05rem !important;
            font-size: .78rem !important;
            border-radius: 10px !important;
            background: rgba(248,251,252,.98) !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            font-size: .70rem !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            min-height: 1.70rem !important;
            height: 1.70rem !important;
            padding-left: .70rem !important;
            padding-right: .18rem !important;
        }}

        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button div,
        section[data-testid="stSidebar"] .stButton > button span {{
            font-size: .70rem !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }}

        @media (max-width: 900px) {{
            div[data-testid="stTextInput"] div[data-baseweb="input"],
            div[data-testid="stNumberInput"] div[data-baseweb="input"],
            div[data-testid="stDateInput"] div[data-baseweb="input"],
            div[data-baseweb="input"] {{
                min-height: 1.48rem !important;
                height: 1.48rem !important;
                border-radius: 8px !important;
            }}

            div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
            div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
            div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
            div[data-baseweb="input"] > div {{
                min-height: 1.48rem !important;
                height: 1.48rem !important;
            }}

            div[data-testid="stTextInput"] input,
            div[data-testid="stNumberInput"] input,
            div[data-testid="stDateInput"] input,
            div[data-baseweb="input"] input {{
                min-height: 1.48rem !important;
                height: 1.48rem !important;
                font-size: .64rem !important;
                padding: .04rem .30rem !important;
            }}

            div[data-testid="stTextArea"] div[data-baseweb="textarea"],
            div[data-baseweb="textarea"] {{
                min-height: 2.05rem !important;
                height: 2.05rem !important;
                border-radius: 8px !important;
            }}

            div[data-testid="stTextArea"] textarea,
            div[data-baseweb="textarea"] textarea {{
                min-height: 2.05rem !important;
                height: 2.05rem !important;
                font-size: .64rem !important;
                padding: .25rem .30rem !important;
            }}

            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
            div[data-baseweb="select"] > div {{
                min-height: 1.48rem !important;
                height: 1.48rem !important;
                font-size: .64rem !important;
                border-radius: 8px !important;
            }}

            div[data-baseweb="select"] span,
            div[data-baseweb="select"] div {{
                font-size: .64rem !important;
                line-height: 1 !important;
            }}

            section[data-testid="stSidebar"] .stButton > button {{
                font-size: .54rem !important;
                min-height: 1.34rem !important;
                height: 1.34rem !important;
                padding-left: .48rem !important;
                padding-right: .12rem !important;
                letter-spacing: -.01em !important;
                white-space: nowrap !important;
            }}

            section[data-testid="stSidebar"] .stButton > button p,
            section[data-testid="stSidebar"] .stButton > button div,
            section[data-testid="stSidebar"] .stButton > button span {{
                font-size: .54rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: visible !important;
                text-overflow: clip !important;
            }}

            section[data-testid="stSidebar"] details summary {{
                font-size: .54rem !important;
                letter-spacing: .045em !important;
            }}
        }}


        /* ==========================================================
           RF final readability: restore input heights and compact menu
           ========================================================== */
        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stNumberInput"] div[data-baseweb="input"],
        div[data-testid="stDateInput"] div[data-baseweb="input"],
        div[data-baseweb="input"] {{
            min-height: 2.48rem !important;
            height: 2.48rem !important;
            border-radius: 11px !important;
            background: rgba(248,251,252,.98) !important;
            overflow: visible !important;
        }}

        div[data-testid="stTextInput"] div[data-baseweb="input"] > div,
        div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
        div[data-testid="stDateInput"] div[data-baseweb="input"] > div,
        div[data-baseweb="input"] > div {{
            min-height: 2.48rem !important;
            height: 2.48rem !important;
            align-items: center !important;
        }}

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-baseweb="input"] input {{
            min-height: 2.48rem !important;
            height: 2.48rem !important;
            font-size: .80rem !important;
            line-height: 1.2 !important;
            padding: .22rem .48rem !important;
            overflow: visible !important;
        }}

        div[data-testid="stTextArea"] div[data-baseweb="textarea"],
        div[data-baseweb="textarea"] {{
            min-height: 4.35rem !important;
            height: 4.35rem !important;
            border-radius: 11px !important;
            background: rgba(248,251,252,.98) !important;
            overflow: visible !important;
        }}

        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="textarea"] textarea {{
            min-height: 4.35rem !important;
            height: 4.35rem !important;
            font-size: .80rem !important;
            line-height: 1.2 !important;
            padding: .38rem .48rem !important;
            overflow: auto !important;
        }}

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-baseweb="select"] > div {{
            min-height: 2.48rem !important;
            height: 2.48rem !important;
            font-size: .80rem !important;
            border-radius: 11px !important;
            align-items: center !important;
        }}

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {{
            font-size: .80rem !important;
            line-height: 1.15 !important;
        }}

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stDateInput label,
        .stNumberInput label {{
            font-size: .78rem !important;
            line-height: 1.1 !important;
            margin-bottom: .08rem !important;
        }}

        section[data-testid="stSidebar"] {{
            width: min(60vw, 300px) !important;
            min-width: min(60vw, 300px) !important;
            max-width: min(60vw, 300px) !important;
        }}

        section[data-testid="stSidebar"] details,
        section[data-testid="stSidebar"] details[open] {{
            margin: .02rem 0 .08rem 0 !important;
        }}

        section[data-testid="stSidebar"] details summary {{
            font-size: .56rem !important;
            letter-spacing: .035em !important;
            padding: .06rem .04rem .06rem .04rem !important;
            line-height: 1.05 !important;
        }}

        section[data-testid="stSidebar"] .stButton {{
            margin: 0 !important;
            padding: 0 !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            font-size: .66rem !important;
            line-height: 1.05 !important;
            white-space: nowrap !important;
            min-height: 1.42rem !important;
            height: 1.42rem !important;
            padding: .05rem .16rem .05rem .72rem !important;
            margin: 0 !important;
            border-radius: 6px !important;
        }}

        section[data-testid="stSidebar"] .stButton > button p,
        section[data-testid="stSidebar"] .stButton > button div,
        section[data-testid="stSidebar"] .stButton > button span {{
            font-size: .80rem !important;
            line-height: 1.05 !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }}

        .rf-sidebar-logo {{
            padding: .32rem .12rem .42rem .12rem !important;
            margin-bottom: .02rem !important;
        }}

        .rf-session-simple {{
            margin-top: .42rem !important;
            padding-top: .38rem !important;
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

