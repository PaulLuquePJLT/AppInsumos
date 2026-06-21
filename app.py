import os

import streamlit as st

from src.auth import ensure_default_admin
from src.auth_views import render_login_page
from src.session import clear_auth_session, enforce_session_timeout, render_idle_timeout_script
from src.theme import (
    apply_global_theme,
    enable_auto_csv_downloads,
    load_page_icon,
    render_sidebar_brand,
    render_sidebar_nav,
)


st.set_page_config(
    page_title="App WMS Block B",
    page_icon=load_page_icon(),
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_theme()
enable_auto_csv_downloads()

# Si el watchdog del navegador detectó 5 minutos de inactividad,
# vuelve a esta URL con ?wms_timeout=1 y cerramos sesión.
try:
    if st.query_params.get("wms_timeout"):
        clear_auth_session()
        st.session_state["timeout_message"] = "Tu sesión se cerró automáticamente por 5 minutos de inactividad."
        st.query_params.clear()
        st.rerun()
except Exception:
    pass

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
    try:
        ensure_default_admin(
            default_admin_password,
            force_password_reset=force_admin_reset,
        )
    except Exception:
        # Si Azure SQL Serverless está despertando, no bloqueamos toda la app.
        # El siguiente acceso a BD reintentará con un pool limpio.
        st.session_state["db_startup_warning"] = (
            "La base de datos está despertando o rechazó la primera conexión. "
            "Intenta iniciar sesión nuevamente en unos segundos."
        )


login_page = st.Page(
    render_login_page,
    title="Login",
    icon=":material/login:",
)

if not st.session_state.authenticated:
    pg = st.navigation([login_page], position="hidden")
    pg.run()
    st.stop()

if enforce_session_timeout(300):
    st.rerun()

render_idle_timeout_script(300)


user = st.session_state.auth_user or {}
is_admin = bool(user.get("is_admin"))


MENU_GROUPS: list[tuple[str, list[dict]]] = []

if is_admin:
    MENU_GROUPS.append((
        "Maestros",
        [
            {"path": "pages/02_Productos.py", "title": "Productos", "icon": ":material/inventory_2:"},
            {"path": "pages/03_Ubicaciones.py", "title": "Ubicaciones", "icon": ":material/location_on:"},
            {"path": "pages/13_Proveedores.py", "title": "Proveedores", "icon": ":material/local_shipping:"},
            {"path": "pages/10_Areas_Logisticas.py", "title": "Áreas Logísticas", "icon": ":material/apartment:"},
            {"path": "pages/11_Categorias_Unidades.py", "title": "Categorías y Unidades", "icon": ":material/category:"},
            {"path": "pages/12_Usuarios.py", "title": "Usuarios", "icon": ":material/manage_accounts:"},
        ],
    ))

MENU_GROUPS.extend([
    (
        "Ingresos",
        [
            {"path": "pages/04_Entrada_Stock.py", "title": "Entrada Stock", "icon": ":material/move_to_inbox:"},
        ],
    ),
    (
        "Salidas",
        [
            {"path": "pages/14_Pedidos.py", "title": "Pedidos", "icon": ":material/request_quote:"},
            {"path": "pages/15_Picking.py", "title": "Picking", "icon": ":material/assignment:"},
            {"path": "pages/16_Atencion_Picking.py", "title": "Atención de Picking", "icon": ":material/task_alt:"},
            {"path": "pages/05_Salida_Cuenta.py", "title": "Salida Cuenta", "icon": ":material/output:"},
        ],
    ),
    (
        "Consultas",
        [
            {"path": "pages/06_Transferencias.py", "title": "Transferencias", "icon": ":material/swap_horiz:"},
            {"path": "pages/07_Stock.py", "title": "Stock", "icon": ":material/package_2:"},
            {"path": "pages/08_Movimientos.py", "title": "Movimientos", "icon": ":material/receipt_long:"},
            {"path": "pages/09_Stock_Cuentas.py", "title": "Stock Cuentas", "icon": ":material/business_center:"},
        ],
    ),
    (
        "Reportes",
        [
            {"path": "pages/01_Dashboard.py", "title": "Dashboard", "icon": ":material/monitoring:", "default": True},
        ],
    ),
])


def _page_objects_from_menu(groups: list[tuple[str, list[dict]]]) -> dict:
    pages: dict[str, list] = {}
    for group_name, items in groups:
        pages[group_name] = [
            st.Page(
                item["path"],
                title=item["title"],
                icon=item.get("icon"),
                default=bool(item.get("default", False)),
            )
            for item in items
        ]
    return pages


def _logout() -> None:
    clear_auth_session()
    st.rerun()


# La navegación se registra en modo oculto para poder controlar totalmente
# el orden, branding e iconografía del sidebar.
pg = st.navigation(_page_objects_from_menu(MENU_GROUPS), position="hidden")

with st.sidebar:
    render_sidebar_brand()
    render_sidebar_nav(MENU_GROUPS)

    full_name = f"{user.get('nombres', '')} {user.get('apellidos', '')}".strip()
    display_name = full_name or user.get("usuario_login", "")
    role_name = user.get("rol", "")

    st.markdown(
        f"""
        <div class="wms-sidebar-spacer"></div>
        <div class="wms-session-block">
            <div class="wms-session-label">Sesión activa</div>
            <div class="wms-session-name">{display_name}</div>
            <div class="wms-session-role">Rol: {role_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Cerrar sesión", use_container_width=True, type="secondary"):
        _logout()

pg.run()
