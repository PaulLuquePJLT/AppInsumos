import os

import streamlit as st

from src.auth import ensure_default_admin
from src.auth_views import render_login_page


st.set_page_config(
    page_title="Mini WMS Insumos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        button { width: 100%; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None


# Opcional: configura DEFAULT_ADMIN_PASSWORD en Streamlit Secrets
# para fijar/crear el admin inicial.
try:
    default_admin_password = st.secrets.get(
        "DEFAULT_ADMIN_PASSWORD",
        os.getenv("DEFAULT_ADMIN_PASSWORD"),
    )
except Exception:
    default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")

try:
    force_admin_reset = str(
        st.secrets.get("DEFAULT_ADMIN_FORCE_RESET", "false")
    ).lower() in {"1", "true", "yes", "si", "sí"}
except Exception:
    force_admin_reset = str(
        os.getenv("DEFAULT_ADMIN_FORCE_RESET", "false")
    ).lower() in {"1", "true", "yes", "si", "sí"}

if default_admin_password:
    ensure_default_admin(
        default_admin_password,
        force_password_reset=force_admin_reset,
    )


login_page = st.Page(
    render_login_page,
    title="Login",
    icon="🔐",
)

if not st.session_state.authenticated:
    pg = st.navigation([login_page], position="hidden")
    pg.run()
    st.stop()


user = st.session_state.auth_user or {}
is_admin = bool(user.get("is_admin"))


def logout_page():
    st.title("Cerrar sesión")
    st.write("¿Deseas cerrar tu sesión actual?")

    if st.button("Cerrar sesión", type="primary"):
        for key in [
            "authenticated",
            "auth_user",
            "auth_mode",
            "reset_identifier",
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()


pages = {}

if is_admin:
    pages["Maestros"] = [
        st.Page("pages/02_Productos.py", title="Productos", icon="🧾"),
        st.Page("pages/03_Ubicaciones.py", title="Ubicaciones", icon="📍"),
        st.Page("pages/10_Areas_Logisticas.py", title="Áreas Logísticas", icon="🏢"),
        st.Page(
            "pages/11_Categorias_Unidades.py",
            title="Categorías y Unidades",
            icon="🗂️",
        ),
        st.Page("pages/12_Usuarios.py", title="Usuarios", icon="👤"),
    ]

pages["Ingresos"] = [
    st.Page("pages/04_Entrada_Stock.py", title="Entrada Stock", icon="➕"),
]

pages["Salidas"] = [
    st.Page("pages/05_Salida_Cuenta.py", title="Salida Cuenta", icon="➖"),
]

pages["Consultas"] = [
    st.Page("pages/06_Transferencias.py", title="Transferencias", icon="🔁"),
    st.Page("pages/07_Stock.py", title="Stock", icon="📦"),
    st.Page("pages/08_Movimientos.py", title="Movimientos", icon="📜"),
    st.Page("pages/09_Stock_Cuentas.py", title="Stock Cuentas", icon="💼"),
]

pages["Reportes"] = [
    st.Page("pages/01_Dashboard.py", title="Dashboard", icon="📊", default=True),
]

pages["Sesión"] = [
    st.Page(logout_page, title="Cerrar sesión", icon="🚪"),
]

with st.sidebar:
    st.divider()
    st.caption("Sesión activa")

    full_name = f"{user.get('nombres', '')} {user.get('apellidos', '')}".strip()

    st.write(f"**{full_name or user.get('usuario_login', '')}**")
    st.caption(f"Rol: {user.get('rol', '')}")

pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
