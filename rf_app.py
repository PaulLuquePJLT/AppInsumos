from __future__ import annotations

from datetime import date
import time
from typing import Any

import streamlit.components.v1 as components

import pandas as pd
import streamlit as st

from src.auth import authenticate_user, request_password_reset, reset_password_with_code

try:
    from src.db import reset_engine_pool
except Exception:  # compatibilidad si src.db no tiene esta función
    def reset_engine_pool() -> None:
        return None
from src.rf_movimientos import (
    confirmar_ingreso_rf,
    confirmar_tarea_picking_rf,
    confirmar_transferencia_rf,
)
from src.rf_queries import (
    rf_clear_master_cache,
    rf_find_product_by_code,
    rf_get_auditoria_picking,
    rf_get_pickings_pendientes,
    rf_get_proveedores,
    rf_get_stage_recepcion,
    rf_get_stock_consulta,
    rf_get_stock_por_ubicacion,
    rf_get_tareas_picking,
    rf_get_ubicaciones_activas,
)
from src.rf_theme import apply_rf_theme, load_rf_icon, logo_img, render_rf_logo_sidebar, render_rf_product_card
from src.session import (
    clear_auth_session,
    current_user,
    current_user_id,
)


st.set_page_config(
    page_title="RF WMS Block B",
    page_icon=load_rf_icon(),
    layout="centered",
    initial_sidebar_state="collapsed",
)


ALLOWED_ROLES = {"operario", "administrador", "admin"}
RF_IDLE_TIMEOUT_SECONDS = 180


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
    st.session_state.rf_authenticated = True
    st.session_state.rf_auth_user = user
    st.session_state.authenticated = True
    st.session_state.auth_user = user
    st.session_state.rf_last_activity_ts = time.time()


def _clear_rf_session_state() -> None:
    """Limpia la sesión RF sin forzar rerun.

    Se usa tanto para cierre manual como para cierre automático por inactividad.
    """
    for key in [
        "rf_authenticated",
        "rf_auth_user",
        "rf_auth_mode",
        "rf_reset_identifier",
        "rf_page",
        "rf_ingreso_detalles",
        "rf_scan_codigo",
        "rf_lote",
        "rf_cantidad",
        "rf_texto_item",
        "rf_confirm_ingreso",
        "rf_header_id_proveedor",
        "rf_header_proveedor",
        "rf_header_fecha",
        "rf_header_documento",
        "rf_header_texto",
        "rf_picking_id",
        "rf_picking_nro",
        "rf_picking_mode",
        "rf_picking_total",
        "rf_picking_done_session",
        "rf_cancel_picking_process",
        "rf_transfer_confirm",
        "rf_transfer_origen",
        "rf_transfer_producto_label",
        "rf_transfer_lote",
        "rf_transfer_destino",
        "rf_transfer_destino_id",
        "rf_transfer_cantidad",
        "rf_stock_query",
        "rf_stock_ubicacion",
        "rf_last_activity_ts",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    clear_auth_session()
    try:
        reset_engine_pool()
    except Exception:
        pass


def _logout() -> None:
    _clear_rf_session_state()
    st.rerun()


def _handle_timeout_query_param() -> None:
    """Cierra la sesión RF cuando el watchdog del navegador agrega ?wms_timeout=1."""
    try:
        if st.query_params.get("wms_timeout") or st.query_params.get("rf_timeout"):
            _clear_rf_session_state()
            st.session_state["rf_timeout_message"] = "Tu sesión RF se cerró automáticamente por 3 minutos de inactividad."
            st.query_params.clear()
            st.rerun()
    except Exception:
        pass


def _enforce_rf_idle_timeout() -> bool:
    """Valida inactividad en backend durante cada rerun de Streamlit."""
    if not st.session_state.get("rf_authenticated"):
        return False

    now = time.time()
    last_activity = float(st.session_state.get("rf_last_activity_ts") or now)

    if now - last_activity > RF_IDLE_TIMEOUT_SECONDS:
        _clear_rf_session_state()
        st.session_state["rf_timeout_message"] = "Tu sesión RF se cerró automáticamente por 3 minutos de inactividad."
        return True

    st.session_state.rf_last_activity_ts = now
    return False


def _render_rf_idle_timeout_script(timeout_seconds: int = RF_IDLE_TIMEOUT_SECONDS) -> None:
    """Watchdog en navegador para cerrar sesión incluso si el equipo queda en segundo plano."""
    timeout_ms = int(timeout_seconds * 1000)
    html = """
    <script>
    (function() {
        const timeoutMs = __TIMEOUT_MS__;
        const storageKey = "rf_wms_last_activity";
        let timer = null;

        function parentWindow() {
            return window.parent || window;
        }

        function markActivity() {
            try {
                parentWindow().localStorage.setItem(storageKey, String(Date.now()));
            } catch (e) {}
            scheduleCheck();
        }

        function elapsedMs() {
            try {
                const last = Number(parentWindow().localStorage.getItem(storageKey) || Date.now());
                return Date.now() - last;
            } catch (e) {
                return 0;
            }
        }

        function triggerTimeout() {
            try {
                const url = new URL(parentWindow().location.href);
                url.searchParams.set("rf_timeout", "1");
                parentWindow().location.href = url.toString();
            } catch (e) {
                parentWindow().location.href = parentWindow().location.href.split("?")[0] + "?rf_timeout=1";
            }
        }

        function checkTimeout() {
            if (elapsedMs() >= timeoutMs) {
                triggerTimeout();
                return;
            }
            scheduleCheck();
        }

        function scheduleCheck() {
            if (timer) clearTimeout(timer);
            const remaining = Math.max(1000, timeoutMs - elapsedMs());
            timer = setTimeout(checkTimeout, remaining);
        }

        const events = ["click", "keydown", "mousemove", "touchstart", "scroll", "wheel"];
        events.forEach(function(evt) {
            try {
                parentWindow().document.addEventListener(evt, markActivity, {passive: true});
            } catch (e) {}
        });

        try {
            parentWindow().document.addEventListener("visibilitychange", function() {
                if (!parentWindow().document.hidden && elapsedMs() >= timeoutMs) {
                    triggerTimeout();
                }
            });
        } catch (e) {}

        markActivity();
    })();
    </script>
    """.replace("__TIMEOUT_MS__", str(timeout_ms))
    components.html(html, height=0, width=0)


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

    timeout_message = st.session_state.pop("rf_timeout_message", None) or st.session_state.pop("timeout_message", None)
    if timeout_message:
        st.warning(timeout_message)

    if st.session_state.rf_auth_mode == "login":
        with st.container(border=True):
            _login_brand()
            usuario = st.text_input("Usuario o correo", key="rf_login_identifier")
            password = st.text_input("Contraseña", type="password", key="rf_login_password")
            ingresar = st.button("Ingresar", use_container_width=True, type="primary", key="rf_login_btn")
            forgot = st.button("¿Olvidaste tu contraseña?", use_container_width=True, key="rf_login_forgot_btn")

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
                    st.session_state.rf_last_activity_ts = time.time()
                    st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        if forgot:
            st.session_state.rf_auth_mode = "forgot_request"
            st.rerun()

    elif st.session_state.rf_auth_mode == "forgot_request":
        with st.container(border=True):
            _login_brand()
            st.write("Ingresa tu usuario o correo registrado para recibir un código de recuperación.")
            identifier = st.text_input("Usuario o correo", key="rf_forgot_identifier")
            enviar = st.button("Enviar código", use_container_width=True, type="primary", key="rf_forgot_send")
            volver = st.button("Volver al login", use_container_width=True, key="rf_forgot_back")

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
        with st.container(border=True):
            _login_brand()
            identifier = st.text_input("Usuario o correo", value=st.session_state.rf_reset_identifier, key="rf_verify_identifier")
            code = st.text_input("Código recibido", key="rf_verify_code")
            new_password = st.text_input("Nueva contraseña", type="password", key="rf_verify_new_password")
            confirm_password = st.text_input("Confirmar nueva contraseña", type="password", key="rf_verify_confirm_password")
            cambiar = st.button("Restablecer contraseña", use_container_width=True, type="primary", key="rf_verify_change")
            volver = st.button("Volver al login", use_container_width=True, key="rf_verify_back")

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

def _set_page(page_name: str) -> None:
    st.session_state.rf_page = page_name
    st.session_state.rf_collapse_sidebar = True


def _toggle_group(group_key: str) -> None:
    st.session_state[group_key] = not bool(st.session_state.get(group_key, False))


def _render_auto_collapse_sidebar() -> None:
    """Cierra el sidebar en móvil después de elegir una función."""
    if not st.session_state.pop("rf_collapse_sidebar", False):
        return

    html = """
    <script>
    (function() {
        function closeSidebarAttempt() {
            const doc = window.parent.document;
            const candidates = [];
            const selectors = [
                '[data-testid="stSidebarCollapseButton"] button',
                '[data-testid="stSidebarCollapseButton"]',
                'button[title="Close sidebar"]',
                'button[aria-label="Close sidebar"]',
                'button[aria-label="Collapse sidebar"]',
                'button[title="Collapse sidebar"]'
            ];
            selectors.forEach(function(selector) {
                doc.querySelectorAll(selector).forEach(function(el) { candidates.push(el); });
            });
            Array.from(doc.querySelectorAll('button')).forEach(function(btn) {
                const label = (btn.getAttribute('aria-label') || btn.getAttribute('title') || btn.innerText || '').toLowerCase();
                const text = (btn.innerText || '').trim();
                if (
                    label.includes('close sidebar') ||
                    label.includes('collapse') ||
                    label.includes('ocultar') ||
                    label.includes('cerrar') ||
                    text.includes('«') ||
                    text.includes('‹') ||
                    text.includes('<<')
                ) {
                    candidates.push(btn);
                }
            });
            for (const el of candidates) {
                try {
                    if (el && el.offsetParent !== null) {
                        el.click();
                        return true;
                    }
                } catch (e) {}
            }
            return false;
        }
        let attempts = 0;
        const timer = setInterval(function() {
            attempts += 1;
            if (closeSidebarAttempt() || attempts >= 18) {
                clearInterval(timer);
            }
        }, 120);
    })();
    </script>
    """
    components.html(html, height=0, width=0)

def render_sidebar() -> None:
    render_rf_logo_sidebar()

    with st.sidebar.expander("▣ MOVIMIENTOS", expanded=False):
        if st.button("↧ Ingresos", use_container_width=True, type="primary" if st.session_state.rf_page == "Ingresos" else "secondary", key="rf_nav_ingresos"):
            _set_page("Ingresos")
            st.rerun()
        if st.button("▥ Picking", use_container_width=True, type="primary" if st.session_state.rf_page == "Picking" else "secondary", key="rf_nav_picking"):
            _set_page("Picking")
            st.rerun()
        if st.button("⇄ Transferencia", use_container_width=True, type="primary" if st.session_state.rf_page == "Transferencia" else "secondary", key="rf_nav_transferencia"):
            _set_page("Transferencia")
            st.rerun()

    with st.sidebar.expander("⌕ CONSULTAS", expanded=False):
        if st.button("⌕ Stock", use_container_width=True, type="primary" if st.session_state.rf_page == "Stock" else "secondary", key="rf_nav_stock"):
            _set_page("Stock")
            st.rerun()

    user = current_user()
    display_name = f"{user.get('nombres','')} {user.get('apellidos','')}".strip() or user.get("usuario_login", "")
    st.sidebar.markdown(
        f"""
        <div class="rf-session-simple">
            <div class="rf-session-label">Sesión activa</div>
            <div class="rf-session-user">{display_name}</div>
            <div class="rf-session-role">Rol: {user.get('rol','')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Cerrar sesión", use_container_width=True, key="rf_logout"):
        _logout()

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


# ---------------------------------------------------------------------------
# Ingresos RF
# ---------------------------------------------------------------------------


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


def render_ingresos() -> None:
    _init_ingreso_state()
    st.title("Ingresos RF")
    st.caption("Recepción móvil por SKU o EAN")

    tab_header, tab_add, tab_detail = st.tabs(["Datos Cabecera", "Agregar Detalle", "Detalle"])

    with tab_header:
        _, id_proveedor = _provider_selectbox()
        st.date_input("Fecha de ingreso", value=date.today(), key="rf_header_fecha")
        st.text_input("Documento de referencia", key="rf_header_documento", placeholder="Guía, factura, OC, etc.")
        st.text_area("Texto de cabecera", key="rf_header_texto", placeholder="Opcional")
        st.session_state.rf_header_id_proveedor = id_proveedor

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


# ---------------------------------------------------------------------------
# Picking RF
# ---------------------------------------------------------------------------


def _start_picking(id_picking: int, nro_picking: str, total_tareas: int) -> None:
    st.session_state.rf_picking_id = int(id_picking)
    st.session_state.rf_picking_nro = nro_picking
    st.session_state.rf_picking_mode = "tareas"
    st.session_state.rf_picking_total = int(total_tareas or 0)
    st.session_state.rf_picking_done_session = 0
    rf_clear_master_cache()
    st.rerun()


def _back_to_picking_list() -> None:
    for key in ["rf_picking_id", "rf_picking_nro", "rf_picking_mode", "rf_picking_total", "rf_picking_done_session", "rf_cancel_picking_process"]:
        if key in st.session_state:
            del st.session_state[key]
    rf_clear_master_cache()
    st.rerun()


def render_picking() -> None:
    st.title("Picking RF")
    st.caption("Atención secuencial de tareas liberadas")

    mode = st.session_state.get("rf_picking_mode", "lista")
    if mode == "tareas" and st.session_state.get("rf_picking_id"):
        _render_picking_tareas()
    elif mode == "auditoria" and st.session_state.get("rf_picking_id"):
        _render_picking_auditoria()
    else:
        _render_picking_lista()


def _render_picking_lista() -> None:
    data = rf_get_pickings_pendientes()
    if data.empty:
        st.info("No hay pickings pendientes de atención.")
        return

    st.markdown('<div class="rf-kicker">Pickings pendientes</div>', unsafe_allow_html=True)
    for _, row in data.iterrows():
        st.markdown(
            f"""
            <div class="rf-picking-card">
                <div class="rf-picking-title">▥ {row['nro_picking']}</div>
                <div class="rf-picking-sub"><b>Solicitante:</b> {row.get('solicitante') or '-'}</div>
                <div class="rf-picking-sub"><b>Cuenta:</b> {row.get('cuenta_logistica') or '-'}</div>
                <div class="rf-pill-row">
                    <div class="rf-pill">Qty: {float(row.get('cantidad_total') or 0):,.2f}</div>
                    <div class="rf-pill">Códigos: {int(row.get('codigos') or 0)}</div>
                    <div class="rf-pill">Ubicaciones: {int(row.get('ubicaciones') or 0)}</div>
                    <div class="rf-pill">Tareas: {int(row.get('tareas_pendientes') or 0)}</div>
                    <div class="rf-pill">{row.get('estado') or ''}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Atender {row['nro_picking']}", key=f"rf_start_pk_{row['id_picking']}", use_container_width=True, type="primary"):
            _start_picking(int(row["id_picking"]), str(row["nro_picking"]), int(row.get("tareas_pendientes") or 0))


def _render_picking_tareas() -> None:
    id_picking = int(st.session_state.rf_picking_id)
    tareas = rf_get_tareas_picking(id_picking)
    total = int(st.session_state.get("rf_picking_total") or len(tareas))
    done = int(st.session_state.get("rf_picking_done_session") or 0)

    if tareas.empty:
        st.session_state.rf_picking_mode = "auditoria"
        st.rerun()

    tarea = tareas.iloc[0].to_dict()
    current = min(done + 1, total if total > 0 else 1)

    st.markdown(
        f"""
        <div class="rf-task-main rf-task-compact">
            <div class="rf-task-header">
                <div class="rf-task-pk">{st.session_state.get('rf_picking_nro', '')}</div>
                <div class="rf-task-counter">Tarea {current}/{total}</div>
            </div>
            <div class="rf-task-row">
                <div>
                    <div class="rf-task-big-label">Ubicación</div>
                    <div class="rf-task-big-value rf-location-value">{tarea.get('codigo_ubicacion')}</div>
                </div>
                <div>
                    <div class="rf-task-big-label">Cantidad</div>
                    <div class="rf-task-big-value rf-qty-value">{float(tarea.get('cantidad_picking') or 0):,.2f} {tarea.get('codigo_unidad')}</div>
                </div>
            </div>
            <div class="rf-task-big-label">Artículo</div>
            <div class="rf-task-product">{tarea.get('sku')} · {tarea.get('nombre_producto')}</div>
            <div class="rf-grid rf-grid-compact">
                <div class="rf-field"><div class="rf-label">Zona</div><div class="rf-value">{tarea.get('codigo_zona')} - {tarea.get('nombre_zona')}</div></div>
                <div class="rf-field"><div class="rf-label">Cuenta</div><div class="rf-value">{tarea.get('codigo_cuenta')}</div></div>
                <div class="rf-field"><div class="rf-label">Solicitante</div><div class="rf-value">{tarea.get('solicitante') or '-'}</div></div>
                <div class="rf-field"><div class="rf-label">Lote</div><div class="rf-value">{tarea.get('lote') or '-'}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    if col1.button("Confirmar", type="primary", use_container_width=True):
        try:
            confirmar_tarea_picking_rf(int(tarea["id_picking_detalle"]), current_user_id())
            st.session_state.rf_picking_done_session = done + 1
            rf_clear_master_cache()
            st.rerun()
        except Exception as exc:
            st.error("No se pudo confirmar la tarea.")
            with st.expander("Detalle técnico"):
                st.code(str(exc))

    if col2.button("Cancelar", use_container_width=True):
        st.session_state.rf_cancel_picking_process = True

    if st.session_state.get("rf_cancel_picking_process"):
        _render_cancel_picking_dialog()


def _render_cancel_picking_dialog() -> None:
    if hasattr(st, "dialog"):
        @st.dialog("Desea cancelar el proceso")
        def _dialog():
            st.write("Volverás a la lista de pickings. Las tareas ya confirmadas se mantienen completadas; la tarea actual y las siguientes quedarán pendientes.")
            col_yes, col_no = st.columns(2)
            if col_yes.button("Sí", use_container_width=True, type="primary"):
                _back_to_picking_list()
            if col_no.button("No", use_container_width=True):
                st.session_state.rf_cancel_picking_process = False
                st.rerun()

        _dialog()
    else:
        st.warning("¿Desea cancelar el proceso?")
        col_yes, col_no = st.columns(2)
        if col_yes.button("Sí", use_container_width=True, type="primary"):
            _back_to_picking_list()
        if col_no.button("No", use_container_width=True):
            st.session_state.rf_cancel_picking_process = False
            st.rerun()


def _render_picking_auditoria() -> None:
    id_picking = int(st.session_state.rf_picking_id)
    nro = st.session_state.get("rf_picking_nro", "")
    st.subheader(f"Auditoría {nro}")
    auditoria = rf_get_auditoria_picking(id_picking)
    if auditoria.empty:
        st.warning("No hay tareas completadas para auditar.")
    else:
        st.dataframe(auditoria, use_container_width=True, hide_index=True)

    if st.button("Confirmar auditoría", type="primary", use_container_width=True):
        _back_to_picking_list()


# ---------------------------------------------------------------------------
# Transferencia RF
# ---------------------------------------------------------------------------


def _clear_transfer_state() -> None:
    for key in [
        "rf_transfer_origen",
        "rf_transfer_producto_label",
        "rf_transfer_lote",
        "rf_transfer_destino",
        "rf_transfer_destino_id",
        "rf_transfer_cantidad",
        "rf_transfer_confirm",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    rf_clear_master_cache()
    st.rerun()


def render_transferencia() -> None:
    st.title("Transferencia RF")
    st.caption("Movimiento interno por ubicación y código")

    ubicaciones = rf_get_ubicaciones_activas()
    if ubicaciones.empty:
        st.error("No hay ubicaciones activas.")
        return

    ubicacion_options = [""] + ubicaciones["codigo_ubicacion"].astype(str).tolist()
    origen = st.selectbox("Ubicación de origen", ubicacion_options, key="rf_transfer_origen")
    if not origen:
        st.info("Selecciona una ubicación origen para ver códigos disponibles.")
        return

    stock_origen = rf_get_stock_por_ubicacion(origen)
    if stock_origen.empty:
        st.warning("La ubicación seleccionada no tiene stock disponible.")
        return

    productos = (
        stock_origen.groupby(["id_producto", "sku", "nombre_producto", "codigo_unidad"], as_index=False)
        .agg(cantidad_disponible=("cantidad_disponible", "sum"), lotes=("lote", "nunique"))
        .sort_values(["sku", "nombre_producto"])
    )
    product_labels = productos.apply(lambda r: f"{r['sku']} | {r['nombre_producto']} | Disp: {float(r['cantidad_disponible']):,.2f} {r['codigo_unidad']}", axis=1).tolist()
    producto_label = st.selectbox("Código", product_labels, key="rf_transfer_producto_label")
    prod = productos.iloc[product_labels.index(producto_label)]
    product_rows = stock_origen[stock_origen["id_producto"] == prod["id_producto"]].copy()

    # Si existen varios lotes para el producto en la ubicación, el disponible
    # debe mostrarse por lote seleccionado, no por total del código.
    lotes_disponibles = (
        product_rows.assign(lote_key=product_rows["lote"].fillna("").astype(str))
        .groupby("lote_key", as_index=False)
        .agg(cantidad_disponible=("cantidad_disponible", "sum"))
        .sort_values("lote_key")
    )

    if len(lotes_disponibles) > 1:
        lote_labels = [l if l else "Sin lote" for l in lotes_disponibles["lote_key"].tolist()]
        lote_label = st.selectbox("Lote", lote_labels, key="rf_transfer_lote")
        lote = "" if lote_label == "Sin lote" else lote_label
        stock_lote = product_rows[product_rows["lote"].fillna("").astype(str) == lote].iloc[0].copy()
        disponible_lote = float(lotes_disponibles.loc[lotes_disponibles["lote_key"] == lote, "cantidad_disponible"].iloc[0])
        stock_lote["cantidad_disponible"] = disponible_lote
    else:
        stock_lote = product_rows.iloc[0].copy()
        lote = str(stock_lote.get("lote") or "")
        disponible_lote = float(stock_lote.get("cantidad_disponible") or 0)
        if lote:
            st.info(f"Lote: {lote}")

    st.markdown(
        f"""
        <div class="rf-card rf-card-compact">
            <div class="rf-kicker">Stock en ubicación</div>
            <div class="rf-product-title">{prod['sku']} - {prod['nombre_producto']}</div>
            <div class="rf-grid rf-grid-compact">
                <div class="rf-field"><div class="rf-label">Ubicación</div><div class="rf-value">{origen}</div></div>
                <div class="rf-field"><div class="rf-label">Lote</div><div class="rf-value">{lote if lote else '-'}</div></div>
                <div class="rf-field"><div class="rf-label">Disponible lote</div><div class="rf-value">{disponible_lote:,.2f} {prod['codigo_unidad']}</div></div>
                <div class="rf-field"><div class="rf-label">Disponible total código</div><div class="rf-value">{float(prod['cantidad_disponible']):,.2f} {prod['codigo_unidad']}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    destino = st.text_input(
        "Ubicación destino",
        key="rf_transfer_destino",
        placeholder="Escanea o escribe ubicación destino",
    ).strip().upper()
    cantidad = st.text_input("Cantidad", key="rf_transfer_cantidad", placeholder="Cantidad parcial o total")

    col1, col2 = st.columns(2)
    if col1.button("Confirmar Movimiento", type="primary", use_container_width=True):
        try:
            qty = _parse_qty(cantidad)
            disponible = float(stock_lote["cantidad_disponible"] or 0)
            if not destino:
                raise ValueError("Ingresa ubicación destino.")
            destino_row = ubicaciones[ubicaciones["codigo_ubicacion"].astype(str).str.upper() == destino]
            if destino_row.empty:
                raise ValueError("La ubicación destino no existe o está inactiva.")
            if destino == str(origen).upper():
                raise ValueError("La ubicación origen y destino no pueden ser iguales.")
            if qty > disponible:
                raise ValueError("La cantidad supera el stock disponible del lote/ubicación.")
            st.session_state.rf_transfer_confirm = True
            st.session_state.rf_transfer_destino_id = int(destino_row.iloc[0]["id_ubicacion"])
        except Exception as exc:
            st.error(str(exc))

    if col2.button("Cancelar", use_container_width=True):
        _clear_transfer_state()

    if st.session_state.get("rf_transfer_confirm"):
        _render_confirm_transfer_dialog(stock_lote, destino, cantidad, st.session_state.get("rf_transfer_destino_id"))


def _render_confirm_transfer_dialog(stock_lote: pd.Series, destino: str, cantidad: str, id_destino: int | None) -> None:
    def _do_confirm():
        if not id_destino:
            raise ValueError("No se pudo identificar la ubicación destino.")
        id_mov = confirmar_transferencia_rf(
            id_producto=int(stock_lote["id_producto"]),
            id_ubicacion_origen=int(stock_lote["id_ubicacion"]),
            id_ubicacion_destino=int(id_destino),
            cantidad=_parse_qty(cantidad),
            id_usuario=current_user_id(),
            lote=stock_lote.get("lote") or None,
        )
        st.success(f"Transferencia confirmada. Movimiento: {id_mov}")
        _clear_transfer_state()

    if hasattr(st, "dialog"):
        @st.dialog("Desea confirmar movimiento")
        def _dialog():
            st.write("Se actualizará el stock de origen y destino.")
            col_yes, col_no = st.columns(2)
            if col_yes.button("Sí", type="primary", use_container_width=True):
                _do_confirm()
            if col_no.button("No", use_container_width=True):
                st.session_state.rf_transfer_confirm = False
                st.rerun()

        _dialog()
    else:
        st.warning("¿Desea confirmar movimiento?")
        col_yes, col_no = st.columns(2)
        if col_yes.button("Sí", type="primary", use_container_width=True):
            _do_confirm()
        if col_no.button("No", use_container_width=True):
            st.session_state.rf_transfer_confirm = False
            st.rerun()


# ---------------------------------------------------------------------------
# Stock RF
# ---------------------------------------------------------------------------


def render_stock() -> None:
    st.title("Stock RF")
    st.caption("Consulta rápida por SKU, EAN, descripción o ubicación")
    code = st.text_input("Escanear o buscar", placeholder="SKU / EAN / descripción")
    ubicacion = st.text_input("Ubicación", placeholder="Código de ubicación opcional")
    if st.button("Consultar", type="primary", use_container_width=True):
        st.session_state.rf_stock_query = code.strip()
        st.session_state.rf_stock_ubicacion = ubicacion.strip()

    query = st.session_state.get("rf_stock_query", "")
    query_ubicacion = st.session_state.get("rf_stock_ubicacion", "")
    if not query and not query_ubicacion:
        st.info("Ingresa o escanea un código, o consulta por ubicación.")
        return

    data = rf_get_stock_consulta(query, query_ubicacion)
    if data.empty:
        st.warning("No se encontró stock para la búsqueda.")
    else:
        st.dataframe(data, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Router RF
# ---------------------------------------------------------------------------


def _rf_main() -> None:
    _init_auth_state()
    _handle_timeout_query_param()

    if not st.session_state.rf_authenticated:
        render_login()
        return

    st.session_state.authenticated = True
    st.session_state.auth_user = st.session_state.rf_auth_user

    if _enforce_rf_idle_timeout():
        st.rerun()

    _render_rf_idle_timeout_script(RF_IDLE_TIMEOUT_SECONDS)

    apply_rf_theme(login=False)
    st.session_state.setdefault("rf_page", "Inicio")
    render_sidebar()
    _render_auto_collapse_sidebar()

    page = st.session_state.rf_page
    if page == "Inicio":
        render_home()
    elif page == "Ingresos":
        render_ingresos()
    elif page == "Picking":
        render_picking()
    elif page == "Transferencia":
        render_transferencia()
    elif page == "Stock":
        render_stock()
    else:
        render_home()


_rf_page = st.Page(_rf_main, title="RF WMS Block B")
_rf_nav = st.navigation([_rf_page], position="hidden")
_rf_nav.run()
