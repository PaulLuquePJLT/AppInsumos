from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.auth import authenticate_user, request_password_reset, reset_password_with_code
from src.rf_movimientos import confirmar_ingreso_rf
from src.rf_queries import (
    rf_clear_master_cache,
    rf_find_product_by_code,
    rf_get_proveedores,
    rf_get_stage_recepcion,
    rf_get_stock_consulta,
)
from src.rf_theme import apply_rf_theme, load_rf_icon, logo_img, render_rf_logo_sidebar, render_rf_product_card
from src.session import clear_auth_session, current_user, current_user_id


st.set_page_config(
    page_title="RF WMS Block B",
    page_icon=load_rf_icon(),
    layout="centered",
    initial_sidebar_state="collapsed",
)


ALLOWED_ROLES = {"operario", "administrador", "admin"}


def _normalize_role(value: str | None) -> str:
    return str(value or "").strip().lower()


def _parse_qty(value: Any) -> float:
    text = str(value or "").strip().replace(",", ".")
    if text == "":
        raise ValueError("La cantidad es obligatoria.")
    qty = float(text)
    if qty <= 0:
        raise ValueError("La cantidad debe ser mayor a cero.")
    return qty


def _init_auth_state() -> None:
    st.session_state.setdefault("rf_authenticated", False)
    st.session_state.setdefault("rf_auth_user", None)
    st.session_state.setdefault("rf_auth_mode", "login")
    st.session_state.setdefault("rf_reset_identifier", "")


def _set_auth_user(user: dict) -> None:
    # También llenamos las claves usadas por src.session para reutilizar current_user_id().
    st.session_state.rf_authenticated = True
    st.session_state.rf_auth_user = user
    st.session_state.authenticated = True
    st.session_state.auth_user = user


def _logout() -> None:
    for key in [
        "rf_authenticated",
        "rf_auth_user",
        "rf_auth_mode",
        "rf_reset_identifier",
        "rf_page",
        "rf_ingreso_detalles",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    clear_auth_session()
    st.rerun()


def _login_brand() -> None:
    st.markdown(
        f"""
        <div class="rf-login-brand">
            <div>{logo_img(96)}</div>
            <div class="rf-login-title">RF WMS Block B</div>
            <div class="rf-login-subtitle">Recepción, picking y movimientos operativos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    apply_rf_theme(login=True)
    _init_auth_state()

    st.markdown('<div class="rf-login-card">', unsafe_allow_html=True)

    if st.session_state.rf_auth_mode == "login":
        with st.form("rf_login_form"):
            _login_brand()
            usuario = st.text_input("Usuario o correo")
            password = st.text_input("Contraseña", type="password")
            ingresar = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
            forgot = st.form_submit_button("¿Olvidaste tu contraseña?", use_container_width=True)

        if ingresar:
            try:
                user = authenticate_user(usuario, password)
            except Exception as exc:
                st.error("No se pudo validar el usuario. Si Azure SQL estaba pausado, espera unos segundos e intenta nuevamente.")
                with st.expander("Detalle técnico"):
                    st.code(str(exc))
                user = None

            if user:
                role = _normalize_role(user.get("rol"))
                if role not in ALLOWED_ROLES:
                    st.error("Este usuario no tiene rol Operario para usar la app RF.")
                else:
                    _set_auth_user(user)
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        if forgot:
            st.session_state.rf_auth_mode = "forgot_request"
            st.rerun()

    elif st.session_state.rf_auth_mode == "forgot_request":
        with st.form("rf_forgot_request_form"):
            _login_brand()
            st.write("Ingresa tu usuario o correo registrado para recibir un código de recuperación.")
            identifier = st.text_input("Usuario o correo")
            enviar = st.form_submit_button("Enviar código", use_container_width=True, type="primary")
            volver = st.form_submit_button("Volver al login", use_container_width=True)

        if enviar:
            if not identifier.strip():
                st.error("Ingresa tu usuario o correo.")
            else:
                try:
                    request_password_reset(identifier)
                    st.session_state.rf_reset_identifier = identifier.strip()
                    st.session_state.rf_auth_mode = "forgot_verify"
                    st.success("Si el usuario existe y tiene correo configurado, se envió un código.")
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo enviar el correo de recuperación.")
                    with st.expander("Detalle técnico"):
                        st.code(str(exc))

        if volver:
            st.session_state.rf_auth_mode = "login"
            st.rerun()

    elif st.session_state.rf_auth_mode == "forgot_verify":
        with st.form("rf_forgot_verify_form"):
            _login_brand()
            identifier = st.text_input("Usuario o correo", value=st.session_state.rf_reset_identifier)
            code = st.text_input("Código recibido")
            new_password = st.text_input("Nueva contraseña", type="password")
            confirm_password = st.text_input("Confirmar nueva contraseña", type="password")
            cambiar = st.form_submit_button("Restablecer contraseña", use_container_width=True, type="primary")
            volver = st.form_submit_button("Volver al login", use_container_width=True)

        if cambiar:
            if not identifier.strip() or not code.strip():
                st.error("Ingresa usuario/correo y código.")
            elif len(new_password) < 8:
                st.error("La nueva contraseña debe tener al menos 8 caracteres.")
            elif new_password != confirm_password:
                st.error("Las contraseñas no coinciden.")
            else:
                ok, message = reset_password_with_code(identifier, code, new_password)
                if ok:
                    st.success(message)
                    st.session_state.rf_auth_mode = "login"
                else:
                    st.error(message)

        if volver:
            st.session_state.rf_auth_mode = "login"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _set_page(page_name: str) -> None:
    st.session_state.rf_page = page_name


def render_sidebar() -> None:
    render_rf_logo_sidebar()

    with st.sidebar.expander("▣ Movimientos", expanded=True):
        if st.button("Ingresos", use_container_width=True, type="primary" if st.session_state.rf_page == "Ingresos" else "secondary"):
            _set_page("Ingresos")
            st.rerun()
        if st.button("Picking", use_container_width=True, type="primary" if st.session_state.rf_page == "Picking" else "secondary"):
            _set_page("Picking")
            st.rerun()
        if st.button("Transferencia", use_container_width=True, type="primary" if st.session_state.rf_page == "Transferencia" else "secondary"):
            _set_page("Transferencia")
            st.rerun()

    with st.sidebar.expander("⌕ Consultas", expanded=True):
        if st.button("Stock", use_container_width=True, type="primary" if st.session_state.rf_page == "Stock" else "secondary"):
            _set_page("Stock")
            st.rerun()

    st.sidebar.divider()
    user = current_user()
    display_name = f"{user.get('nombres','')} {user.get('apellidos','')}".strip() or user.get("usuario_login", "")
    st.sidebar.caption("Sesión activa")
    st.sidebar.write(f"**{display_name}**")
    st.sidebar.caption(f"Rol: {user.get('rol','')}")
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        _logout()

def _init_ingreso_state() -> None:
    st.session_state.setdefault("rf_ingreso_detalles", [])
    st.session_state.setdefault("rf_scan_codigo", "")
    st.session_state.setdefault("rf_lote", "")
    st.session_state.setdefault("rf_cantidad", "")
    st.session_state.setdefault("rf_texto_item", "")

    if st.session_state.pop("rf_clear_detail_inputs", False):
        st.session_state.rf_scan_codigo = ""
        st.session_state.rf_lote = ""
        st.session_state.rf_cantidad = ""
        st.session_state.rf_texto_item = ""


def _provider_selectbox() -> tuple[pd.DataFrame, int | None]:
    proveedores = rf_get_proveedores()
    if proveedores.empty:
        st.error("No hay proveedores activos. Registra proveedores desde la app de escritorio.")
        return proveedores, None

    labels = proveedores.apply(lambda r: f"{r['ruc']} | {r['razon_social']}", axis=1).tolist()
    selected_label = st.selectbox("Proveedor", labels, key="rf_header_proveedor")
    selected = proveedores.iloc[labels.index(selected_label)]
    return proveedores, int(selected["id_proveedor"])


def render_home() -> None:
    st.markdown(
        f"""
        <div class="rf-home-hero">
            <div class="rf-home-logo">{logo_img(128)}</div>
            <div class="rf-home-title">RF WMS Block B</div>
            <div class="rf-home-subtitle">Operación móvil de almacén</div>
            <div class="rf-home-grid">
                <div class="rf-home-chip">Movimientos</div>
                <div class="rf-home-chip">Ingresos</div>
                <div class="rf-home-chip">Picking</div>
                <div class="rf-home-chip">Transferencia</div>
                <div class="rf-home-chip">Stock</div>
            </div>
            <div class="rf-home-help">Abre el menú lateral y selecciona una función para iniciar.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ingresos() -> None:
    _init_ingreso_state()
    st.title("Ingresos RF")
    st.caption("Recepción móvil por SKU o EAN")

    tab_header, tab_add, tab_detail = st.tabs(["Datos Cabecera", "Agregar Detalle", "Detalle"])

    with tab_header:
        st.markdown('<div class="rf-card">', unsafe_allow_html=True)
        _, id_proveedor = _provider_selectbox()
        st.date_input("Fecha de ingreso", value=date.today(), key="rf_header_fecha")
        st.text_input("Documento de referencia", key="rf_header_documento", placeholder="Guía, factura, OC, etc.")
        st.text_area("Texto de cabecera", key="rf_header_texto", placeholder="Opcional")
        st.session_state.rf_header_id_proveedor = id_proveedor
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_add:
        stage = rf_get_stage_recepcion()
        if not stage:
            st.error("No existe la ubicación stage B1.RE.01 activa. Ejecuta la migración RF o crea la ubicación.")
            st.stop()

        scanned_code = st.text_input(
            "Escanear SKU o EAN",
            key="rf_scan_codigo",
            placeholder="Escanea o ingresa SKU/EAN",
        ).strip()

        product = rf_find_product_by_code(scanned_code) if scanned_code else None
        render_rf_product_card(product, scanned_code)

        if product:
            requires_lot = bool(product.get("requiere_lote"))
            if requires_lot:
                st.text_input("Lote", key="rf_lote", placeholder="Obligatorio")
            else:
                st.text_input("Lote", key="rf_lote", placeholder="No aplica", disabled=True)

            st.text_input("Cantidad a ingresar", key="rf_cantidad", placeholder="Ejemplo: 1, 10, 2.5")
            st.text_area("Texto de posición", key="rf_texto_item", placeholder="Opcional")
            st.info(f"Ubicación destino por defecto: {stage['codigo_ubicacion']}")

            if st.button("Agregar Detalle", type="primary", use_container_width=True):
                try:
                    qty = _parse_qty(st.session_state.rf_cantidad)
                    lote = str(st.session_state.rf_lote or "").strip()
                    if requires_lot and not lote:
                        raise ValueError("El producto requiere lote.")

                    detail = {
                        "id_producto": int(product["id_producto"]),
                        "sku": str(product["sku"]),
                        "ean_serie": product.get("ean_serie") or "",
                        "nombre_producto": str(product["nombre_producto"]),
                        "codigo_unidad": str(product["codigo_unidad"]),
                        "nombre_categoria": str(product.get("nombre_categoria") or ""),
                        "requiere_lote": bool(product.get("requiere_lote")),
                        "lote": lote or None,
                        "cantidad": qty,
                        "codigo_ubicacion_destino": stage["codigo_ubicacion"],
                        "id_ubicacion_destino": int(stage["id_ubicacion"]),
                        "texto_item": str(st.session_state.rf_texto_item or "").strip(),
                    }
                    st.session_state.rf_ingreso_detalles.append(detail)
                    st.session_state.rf_clear_detail_inputs = True
                    st.success("Detalle agregado correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        elif scanned_code:
            st.warning("Escanea un SKU/EAN válido para habilitar los datos de cantidad.")

    with tab_detail:
        details = st.session_state.rf_ingreso_detalles
        if not details:
            st.info("Aún no has agregado detalles.")
            return

        df = pd.DataFrame(details)
        visible_cols = [
            "sku",
            "ean_serie",
            "nombre_producto",
            "codigo_unidad",
            "cantidad",
            "lote",
            "codigo_ubicacion_destino",
            "texto_item",
        ]
        st.dataframe(df[visible_cols], use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        if col1.button("Limpiar detalles", use_container_width=True):
            st.session_state.rf_ingreso_detalles = []
            st.rerun()

        if col2.button("Confirmar Ingreso", type="primary", use_container_width=True):
            st.session_state.rf_confirm_ingreso = True

        if st.session_state.get("rf_confirm_ingreso"):
            _render_confirm_ingreso_dialog()


def _confirm_ingreso() -> None:
    id_proveedor = st.session_state.get("rf_header_id_proveedor")
    if not id_proveedor:
        st.error("Selecciona proveedor en Datos Cabecera.")
        return
    if not st.session_state.get("rf_ingreso_detalles"):
        st.error("No hay detalles para confirmar.")
        return

    try:
        id_movimiento = confirmar_ingreso_rf(
            id_proveedor=int(id_proveedor),
            fecha_ingreso=st.session_state.get("rf_header_fecha", date.today()),
            documento_referencia=str(st.session_state.get("rf_header_documento", "")).strip(),
            texto_cabecera=str(st.session_state.get("rf_header_texto", "")).strip(),
            id_usuario=current_user_id(),
            detalles=st.session_state.rf_ingreso_detalles,
        )
        st.session_state.rf_ingreso_detalles = []
        st.session_state.rf_confirm_ingreso = False
        rf_clear_master_cache()
        st.success(f"Ingreso confirmado correctamente. Movimiento: {id_movimiento}")
    except Exception as exc:
        st.error("No se pudo confirmar el ingreso.")
        with st.expander("Detalle técnico"):
            st.code(str(exc))


def _render_confirm_ingreso_dialog() -> None:
    if hasattr(st, "dialog"):
        @st.dialog("Desea confirmar Movimiento")
        def _dialog():
            st.write("Se contabilizarán todos los detalles agregados en stock y movimientos.")
            col_yes, col_no = st.columns(2)
            if col_yes.button("Sí", type="primary", use_container_width=True):
                _confirm_ingreso()
                st.rerun()
            if col_no.button("No", use_container_width=True):
                st.session_state.rf_confirm_ingreso = False
                st.rerun()

        _dialog()
    else:
        with st.container(border=True):
            st.warning("¿Desea confirmar Movimiento?")
            col_yes, col_no = st.columns(2)
            if col_yes.button("Sí", type="primary", use_container_width=True):
                _confirm_ingreso()
            if col_no.button("No", use_container_width=True):
                st.session_state.rf_confirm_ingreso = False
                st.rerun()


def render_placeholder(title: str, message: str) -> None:
    st.title(title)
    st.markdown(
        f"""
        <div class="rf-card">
            <div class="rf-product-title">{message}</div>
            <div style="color:var(--rf-muted);font-weight:650;">
                Esta vista queda reservada para el siguiente desarrollo RF.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stock() -> None:
    st.title("Stock RF")
    st.caption("Consulta rápida por SKU, EAN o descripción")
    code = st.text_input("Escanear o buscar", placeholder="SKU / EAN / descripción")
    if st.button("Consultar", type="primary", use_container_width=True):
        st.session_state.rf_stock_query = code.strip()

    query = st.session_state.get("rf_stock_query", "")
    if not query:
        st.info("Ingresa o escanea un código para consultar stock.")
        return

    data = rf_get_stock_consulta(query)
    if data.empty:
        st.warning("No se encontró stock para la búsqueda.")
    else:
        st.dataframe(data, use_container_width=True, hide_index=True)


def _rf_main() -> None:
    _init_auth_state()
    if not st.session_state.rf_authenticated:
        render_login()
        return

    # Sincroniza la sesión RF con helpers compartidos.
    st.session_state.authenticated = True
    st.session_state.auth_user = st.session_state.rf_auth_user

    apply_rf_theme(login=False)
    st.session_state.setdefault("rf_page", "Inicio")
    render_sidebar()

    page = st.session_state.rf_page
    if page == "Inicio":
        render_home()
    elif page == "Ingresos":
        render_ingresos()
    elif page == "Picking":
        render_placeholder("Picking RF", "Ejecución de tareas de picking por RF")
    elif page == "Transferencia":
        render_placeholder("Transferencia RF", "Movimientos internos por escaneo")
    elif page == "Stock":
        render_stock()
    else:
        render_home()


# Importante: st.navigation en modo hidden desactiva la navegación automática
# de la carpeta pages/ para esta app RF. Así no aparecen páginas de escritorio
# como Productos, Ubicaciones, Dashboard, etc.
_rf_page = st.Page(_rf_main, title="RF WMS Block B")
_rf_nav = st.navigation([_rf_page], position="hidden")
_rf_nav.run()
