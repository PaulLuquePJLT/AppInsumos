from __future__ import annotations

from datetime import date
import time
from typing import Any

import pandas as pd
import streamlit as st

from src.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    UNKNOWN_LOGIN_MAX_ATTEMPTS,
    authenticate_user,
    request_password_reset,
    reset_password_with_code,
)

try:
    from src.db import reset_engine_pool
except Exception:  # compatibilidad si src.db no tiene esta función
    def reset_engine_pool() -> None:
        return None
from src.rf_scanner import consume_scanned_value, scan_text_input
from src.rf_voice import (
    build_audit_prompt,
    build_voice_instruction,
    consume_voice_event,
    handle_help_text,
    log_voice_event,
    mark_task_voice_confirmation,
    register_voice_short_incident,
    render_voice_assistant,
    reset_voice_autoplay,
)
from src.rf_movimientos import (
    confirmar_ingreso_rf,
    confirmar_tarea_picking_rf,
    confirmar_transferencia_rf,
)
from src.movimientos import atender_tarea_picking_con_corto_parcial
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
RF_IDLE_TIMEOUT_SECONDS = 300


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
        "_rf_idle_watchdog_loaded",
        "rf_voice_enabled",
        "rf_voice_auto_listen",
        "rf_voice_task_key",
        "rf_voice_short_pending",
        "rf_voice_short_task_id",
        "rf_voice_short_qty",
        "rf_voice_short_transcript",
        "rf_voice_processed_event",
        "rf_voice_step",
        "rf_voice_cancel_confirm",
        "rf_voice_waiting_presence",
        "rf_voice_presence_resume",
        "rf_voice_greeting_done",
        "rf_voice_last_zone_code",
        "rf_voice_last_location_code",
        "rf_voice_same_location_intro",
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
            st.session_state["rf_timeout_message"] = "Tu sesión RF se cerró automáticamente por 5 minutos de inactividad."
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
        st.session_state["rf_timeout_message"] = "Tu sesión RF se cerró automáticamente por 5 minutos de inactividad."
        return True

    st.session_state.rf_last_activity_ts = now
    return False


def _render_rf_idle_timeout_script(timeout_seconds: int = RF_IDLE_TIMEOUT_SECONDS) -> None:
    """Deshabilitado para máxima respuesta al touch.

    Se mantiene el timeout de servidor en cada rerun, pero no se agregan
    listeners JavaScript sobre touch/click/scroll.
    """
    return None


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
            handled_auth_failure = False
            login_exception = False
            try:
                user = authenticate_user(usuario, password)
            except AccountLockedError:
                handled_auth_failure = True
                st.session_state.rf_reset_identifier = str(usuario or "").strip()
                st.error(
                    "Cuenta bloqueada por intentos fallidos. "
                    "Usa ¿Olvidaste tu contraseña? para desbloquearla."
                )
                user = None
            except InvalidCredentialsError as exc:
                handled_auth_failure = True
                user = None
                if exc.remaining_attempts > 0:
                    st.error(f"Credenciales incorrectas. Intentos restantes: {exc.remaining_attempts}.")
                else:
                    st.error("Cuenta bloqueada. Restablece tu contraseña para desbloquearla.")
            except Exception as exc:
                login_exception = True
                st.error("No se pudo validar el usuario. Si Azure SQL estaba pausado, espera unos segundos e intenta nuevamente.")
                with st.expander("Detalle técnico"):
                    st.code(str(exc))
                user = None

            if user:
                st.session_state.rf_failed_unknown_count = 0
                role = _normalize_role(user.get("rol"))
                if role not in ALLOWED_ROLES:
                    st.error("Este usuario no tiene rol Operario para usar la app RF.")
                else:
                    _set_auth_user(user)
                    st.session_state.rf_last_activity_ts = time.time()
                    st.rerun()
            elif not login_exception and not handled_auth_failure:
                if not str(usuario or "").strip() or not str(password or ""):
                    st.error("Ingresa usuario/correo y contraseña.")
                else:
                    st.session_state.rf_failed_unknown_count = int(st.session_state.get("rf_failed_unknown_count", 0)) + 1
                    if st.session_state.rf_failed_unknown_count >= UNKNOWN_LOGIN_MAX_ATTEMPTS:
                        st.error("Se alcanzó el máximo de intentos en esta sesión. Usa recuperación de contraseña.")
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
    """Callback mínimo para navegación RF.

    Solo actualiza el nombre de página. No dispara st.rerun(), no ejecuta
    JavaScript y no intenta cerrar el sidebar, para que el touch responda lo
    más rápido posible.
    """
    st.session_state.rf_page = page_name


def _toggle_group(group_key: str) -> None:
    st.session_state[group_key] = not bool(st.session_state.get(group_key, False))

def render_sidebar() -> None:
    render_rf_logo_sidebar()

    current_page = st.session_state.get("rf_page", "Inicio")

    with st.sidebar.expander("▣ MOVIMIENTOS", expanded=False):
        st.button(
            "↧ Ingresos",
            use_container_width=True,
            type="primary" if current_page == "Ingresos" else "secondary",
            key="rf_nav_ingresos",
            on_click=_set_page,
            args=("Ingresos",),
        )
        st.button(
            "▥ Picking",
            use_container_width=True,
            type="primary" if current_page == "Picking" else "secondary",
            key="rf_nav_picking",
            on_click=_set_page,
            args=("Picking",),
        )
        st.button(
            "◎ Voice Picking",
            use_container_width=True,
            type="primary" if current_page == "Voice Picking" else "secondary",
            key="rf_nav_voice_picking",
            on_click=_set_page,
            args=("Voice Picking",),
        )
        st.button(
            "⇄ Transferencia",
            use_container_width=True,
            type="primary" if current_page == "Transferencia" else "secondary",
            key="rf_nav_transferencia",
            on_click=_set_page,
            args=("Transferencia",),
        )

    with st.sidebar.expander("⌕ CONSULTAS", expanded=False):
        st.button(
            "⌕ Stock",
            use_container_width=True,
            type="primary" if current_page == "Stock" else "secondary",
            key="rf_nav_stock",
            on_click=_set_page,
            args=("Stock",),
        )

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

        scanned_code = scan_text_input(
            "Escanear SKU o EAN",
            key="rf_scan_codigo",
            placeholder="Escanea o ingresa SKU/EAN",
            button_label="Abrir cámara",
            uppercase=True,
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
# Picking RF manual y Voice Picking
# ---------------------------------------------------------------------------


def _start_picking(id_picking: int, nro_picking: str, total_tareas: int, *, voice: bool = False) -> None:
    st.session_state.rf_picking_id = int(id_picking)
    st.session_state.rf_picking_nro = nro_picking
    st.session_state.rf_picking_mode = "voice_tareas" if voice else "tareas"
    st.session_state.rf_picking_total = int(total_tareas or 0)
    st.session_state.rf_picking_done_session = 0
    _reset_voice_state(clear_last_zone=True)
    rf_clear_master_cache()
    st.rerun()


def _reset_voice_state(clear_last_zone: bool = False) -> None:
    """Limpia estado temporal de la tarea de voz.

    Importante: no se elimina rf_voice_greeting_done en cada tarea, para que
    el saludo se reproduzca solo al iniciar la atención del picking y no en
    cada posición. Solo se limpia cuando volvemos a la lista o iniciamos otro
    picking completo.
    """
    for key in [
        "rf_voice_task_key",
        "rf_voice_step",
        "rf_voice_short_pending",
        "rf_voice_short_task_id",
        "rf_voice_short_qty",
        "rf_voice_short_transcript",
        "rf_voice_processed_event",
        "rf_voice_cancel_confirm",
        "rf_voice_presence_resume",
        "rf_voice_waiting_presence",
        "rf_voice_unrecognized",
    ]:
        st.session_state.pop(key, None)
    if clear_last_zone:
        st.session_state.pop("rf_voice_last_zone_code", None)
        st.session_state.pop("rf_voice_last_location_code", None)
        st.session_state.pop("rf_voice_same_location_intro", None)
        st.session_state.pop("rf_voice_greeting_done", None)
        st.session_state.pop("rf_voice_farewell_played", None)


def _back_to_picking_list(farewell: str | None = None) -> None:
    if farewell:
        st.session_state.rf_voice_farewell_text = farewell
    for key in [
        "rf_picking_id",
        "rf_picking_nro",
        "rf_picking_mode",
        "rf_picking_total",
        "rf_picking_done_session",
        "rf_cancel_picking_process",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    _reset_voice_state(clear_last_zone=True)
    rf_clear_master_cache()
    st.rerun()


def render_picking() -> None:
    """Picking manual: mantiene la versión sin voice picking."""
    mode = st.session_state.get("rf_picking_mode", "lista")
    if mode == "tareas" and st.session_state.get("rf_picking_id"):
        _render_picking_tareas_manual()
    elif mode == "auditoria" and st.session_state.get("rf_picking_id"):
        _render_picking_auditoria(voice=False)
    else:
        _render_picking_lista(voice=False)


def render_voice_picking() -> None:
    """Voice Picking conversacional."""
    mode = st.session_state.get("rf_picking_mode", "voice_lista")
    if mode == "voice_tareas" and st.session_state.get("rf_picking_id"):
        _render_voice_picking_tareas()
    elif mode == "voice_auditoria" and st.session_state.get("rf_picking_id"):
        _render_picking_auditoria(voice=True)
    else:
        _render_picking_lista(voice=True)


def _render_picking_lista(*, voice: bool = False) -> None:
    if voice and st.session_state.get("rf_voice_farewell_text"):
        farewell_text = str(st.session_state.get("rf_voice_farewell_text") or "Picking finalizado. Buen trabajo.")
        st.markdown('<div class="rf-voice-note"><b>Picking finalizado</b><br>El proceso de voz quedó cerrado correctamente.</div>', unsafe_allow_html=True)
        render_voice_assistant(
            farewell_text,
            key="rf_voice_farewell",
            auto_play=True,
            auto_listen=False,
            keepalive=False,
            height=54,
        )
        # Mantener el mensaje solo durante el primer render posterior al cierre.
        st.session_state.pop("rf_voice_farewell_text", None)

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
        button_label = f"Voice Picking {row['nro_picking']}" if voice else f"Atender {row['nro_picking']}"
        if st.button(button_label, key=f"rf_start_{'voice' if voice else 'manual'}_pk_{row['id_picking']}", use_container_width=True, type="primary"):
            _start_picking(int(row["id_picking"]), str(row["nro_picking"]), int(row.get("tareas_pendientes") or 0), voice=voice)


def _confirm_current_picking_task(tarea: dict, current: int, done: int, *, voice_event: dict | None = None) -> None:
    try:
        st.session_state.rf_voice_last_location_code = str(tarea.get("codigo_ubicacion") or "")
        st.session_state.rf_voice_last_zone_code = str(tarea.get("codigo_zona") or "")
        confirmar_tarea_picking_rf(int(tarea["id_picking_detalle"]), current_user_id())
        if voice_event:
            mark_task_voice_confirmation(
                id_picking_detalle=int(tarea["id_picking_detalle"]),
                transcript=voice_event.get("transcript"),
                confidence=voice_event.get("confidence"),
            )
            log_voice_event(
                id_usuario=current_user_id(),
                id_picking=int(tarea["id_picking"]),
                id_picking_detalle=int(tarea["id_picking_detalle"]),
                evento="TAREA_CONFIRMADA_VOZ",
                texto_reconocido=voice_event.get("transcript"),
                comando_normalizado=voice_event.get("command"),
                confianza=voice_event.get("confidence"),
            )
        st.session_state.rf_picking_done_session = done + 1
        _reset_voice_state(clear_last_zone=False)
        rf_clear_master_cache()
        st.rerun()
    except Exception as exc:
        st.error("No se pudo confirmar la tarea.")
        with st.expander("Detalle técnico"):
            st.code(str(exc))



def _render_html_card(html: str) -> None:
    """Renderiza HTML operativo sin que Streamlit lo escape como texto."""
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def _confirm_short_current_picking_task(tarea: dict, cantidad_encontrada: float) -> None:
    try:
        result = atender_tarea_picking_con_corto_parcial(
            id_picking_detalle=int(tarea["id_picking_detalle"]),
            cantidad_encontrada=float(cantidad_encontrada),
            id_usuario=current_user_id(),
            observacion="Corto RF manual",
            requiere_aprobacion_admin=True,
            origen_atencion="RF",
            transcript=f"Corto manual. Cantidad encontrada {cantidad_encontrada}",
            confidence=None,
        )
        st.session_state.rf_picking_done_session = int(st.session_state.get("rf_picking_done_session") or 0) + (1 if float(cantidad_encontrada or 0) > 0 else 0)
        st.session_state.pop("rf_manual_short_open", None)
        st.session_state.pop("rf_manual_short_qty", None)
        rf_clear_master_cache()
        st.success(f"Corto registrado. Atendido: {float(result.get('qty_atendida', 0)):,.2f}; corto: {float(result.get('qty_corto', 0)):,.2f}.")
        st.rerun()
    except Exception as exc:
        st.error("No se pudo registrar el corto.")
        with st.expander("Detalle técnico"):
            st.code(str(exc))

def _task_card_html(tarea: dict, current: int, total: int, step_label: str = "") -> str:
    step_badge = f'<div class="rf-pill">PASO: {step_label}</div>' if step_label else ""
    return f"""
    <div class="rf-task-main rf-task-compact">
        <div class="rf-task-header">
            <div class="rf-task-pk">{st.session_state.get('rf_picking_nro', '')}</div>
            <div class="rf-task-counter">Tarea {current}/{total}</div>
        </div>
        {step_badge}
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
            <div class="rf-field"><div class="rf-label">Unidad</div><div class="rf-value">{tarea.get('nombre_unidad') or tarea.get('codigo_unidad')}</div></div>
            <div class="rf-field"><div class="rf-label">Lote</div><div class="rf-value">{tarea.get('lote') or '-'}</div></div>
        </div>
    </div>
    """


def _render_picking_tareas_manual() -> None:
    id_picking = int(st.session_state.rf_picking_id)
    tareas = rf_get_tareas_picking(id_picking)
    total = int(st.session_state.get("rf_picking_total") or len(tareas))
    done = int(st.session_state.get("rf_picking_done_session") or 0)

    if tareas.empty:
        st.session_state.rf_picking_mode = "auditoria"
        st.rerun()

    tarea = tareas.iloc[0].to_dict()
    current = min(done + 1, total if total > 0 else 1)
    _render_html_card(_task_card_html(tarea, current, total))

    col1, col2, col3 = st.columns([1, 1, 1])
    if col1.button("Confirmar", type="primary", use_container_width=True):
        _confirm_current_picking_task(tarea, current, done)

    if col2.button("Registrar corto", use_container_width=True):
        st.session_state.rf_manual_short_open = True
        st.session_state.rf_manual_short_qty = float(tarea.get("cantidad_picking") or 0)

    if col3.button("Cancelar", use_container_width=True):
        st.session_state.rf_cancel_picking_process = True

    if st.session_state.get("rf_manual_short_open"):
        with st.container(border=True):
            st.markdown("**Registrar corto**")
            st.caption("Indica la cantidad realmente encontrada. El sistema atenderá esa cantidad y generará un corto por la diferencia.")
            qty_asignada = float(tarea.get("cantidad_picking") or 0)
            qty_encontrada = st.number_input(
                "Cantidad encontrada",
                min_value=0.0,
                max_value=qty_asignada,
                step=0.001,
                format="%.3f",
                value=float(st.session_state.get("rf_manual_short_qty") or 0),
                key="rf_manual_short_qty_input",
            )
            c_ok, c_cancel = st.columns(2)
            if c_ok.button("Confirmar corto", type="primary", use_container_width=True):
                _confirm_short_current_picking_task(tarea, qty_encontrada)
            if c_cancel.button("Cerrar", use_container_width=True):
                st.session_state.pop("rf_manual_short_open", None)
                st.rerun()

    if st.session_state.get("rf_cancel_picking_process"):
        _render_cancel_picking_dialog()


def _voice_step_label(step: str) -> str:
    return {
        "ubicacion": "UBICACIÓN",
        "material": "MATERIAL",
        "cantidad": "CANTIDAD",
    }.get(step, step.upper())


def _voice_help(step: str, short_pending: bool = False, short_qty: float | None = None, cancel_confirm: bool = False) -> str:
    if cancel_confirm:
        return "Puedes decir: cancelar para confirmar la cancelación, o continuar para seguir."
    if short_pending and short_qty is None:
        return "Indica la cantidad encontrada. Ejemplo: cinco, diez, veinte."
    if short_pending and short_qty is not None:
        return "Puedes decir: confirmar corto, o indicar otra cantidad."
    if step == "ubicacion":
        return "Puedes decir: estoy aquí, repítelo, repite ubicación o cancelar picking."
    if step == "material":
        return "Puedes decir: ok, correcto, conforme, repite código o cancelar picking."
    if step == "cantidad":
        return "Puedes decir: ok, correcto, conforme, repite cantidad, tengo corto o cancelar picking."
    return handle_help_text(step)


def _current_voice_key(tarea: dict, step: str) -> str:
    suffix = ""
    if st.session_state.get("rf_voice_cancel_confirm"):
        suffix += "_cancel"
    if st.session_state.get("rf_voice_short_pending"):
        suffix += f"_short_{st.session_state.get('rf_voice_short_qty')}"
    if st.session_state.get("rf_voice_presence_resume"):
        suffix += "_resume"
    if st.session_state.get("rf_voice_unrecognized"):
        suffix += "_unrecognized"
    return f"rf_voice_task_{int(tarea['id_picking_detalle'])}_{step}{suffix}"


def _handle_voice_command(event: dict, tarea: dict, current: int, total: int, done: int, prompt: str, voice_key: str) -> None:
    command = str(event.get("command") or "").upper()
    transcript = str(event.get("transcript") or "")
    confidence = event.get("confidence")
    step = str(st.session_state.get("rf_voice_step") or "ubicacion")

    log_voice_event(
        id_usuario=current_user_id(),
        id_picking=int(tarea["id_picking"]),
        id_picking_detalle=int(tarea["id_picking_detalle"]),
        evento="COMANDO_RECONOCIDO" if command not in {"NO_RECONOCIDO", "NO_INPUT"} else "COMANDO_NO_RECONOCIDO",
        texto_emitido=prompt,
        texto_reconocido=transcript,
        comando_normalizado=command,
        confianza=confidence,
    )

    if command == "NO_RECONOCIDO":
        st.session_state.rf_voice_unrecognized = True
        reset_voice_autoplay(voice_key)
        st.rerun()

    # Si ya hubo un comando válido, limpiar mensaje anterior de no reconocido.
    st.session_state.rf_voice_unrecognized = False

    if command == "NO_INPUT":
        # El componente se encargará de preguntar "¿Estás ahí?" cada 10 segundos.
        st.session_state.rf_voice_waiting_presence = True
        return

    if command == "PRESENCIA":
        st.session_state.rf_voice_waiting_presence = False
        st.session_state.rf_voice_presence_resume = True
        st.session_state.rf_voice_unrecognized = False
        reset_voice_autoplay(voice_key)
        st.rerun()

    if command == "CANCELAR_PICKING":
        if st.session_state.get("rf_voice_cancel_confirm"):
            _back_to_picking_list()
        else:
            st.session_state.rf_voice_cancel_confirm = True
            reset_voice_autoplay(voice_key)
            st.rerun()

    if command in {"NO", "CONTINUAR"} and st.session_state.get("rf_voice_cancel_confirm"):
        st.session_state.rf_voice_cancel_confirm = False
        reset_voice_autoplay(voice_key)
        st.rerun()

    if command == "REPETIR":
        reset_voice_autoplay(voice_key)
        st.rerun()
    if command == "REPETIR_UBICACION":
        st.session_state.rf_voice_step = "ubicacion"
        reset_voice_autoplay(voice_key)
        st.rerun()
    if command == "REPETIR_CODIGO":
        st.session_state.rf_voice_step = "material"
        reset_voice_autoplay(voice_key)
        st.rerun()
    if command == "REPETIR_CANTIDAD":
        st.session_state.rf_voice_step = "cantidad"
        reset_voice_autoplay(voice_key)
        st.rerun()

    if command == "AYUDA":
        st.info(handle_help_text(step))
        reset_voice_autoplay(voice_key)
        st.rerun()

    if st.session_state.get("rf_voice_short_pending"):
        if command == "CANTIDAD":
            st.session_state.rf_voice_short_qty = event.get("quantity")
            st.session_state.rf_voice_short_transcript = transcript
            reset_voice_autoplay(voice_key)
            st.rerun()
        if command == "CONFIRMAR_CORTO":
            qty = st.session_state.get("rf_voice_short_qty")
            if qty is None:
                # Todavía no hay cantidad encontrada; volver a pedirla.
                st.session_state.rf_voice_short_pending = True
                reset_voice_autoplay(voice_key)
                st.rerun()
            register_voice_short_incident(
                id_usuario=current_user_id(),
                id_picking=int(tarea["id_picking"]),
                id_picking_detalle=int(tarea["id_picking_detalle"]),
                cantidad_reportada=float(qty),
                transcript=st.session_state.get("rf_voice_short_transcript") or transcript,
                confidence=confidence,
            )
            st.session_state.rf_voice_last_location_code = str(tarea.get("codigo_ubicacion") or "")
            st.session_state.rf_voice_last_zone_code = str(tarea.get("codigo_zona") or "")
            _reset_voice_state(clear_last_zone=False)
            # Si encontró algo, se considera una tarea procesada. Si encontró cero,
            # la tarea queda como corto y la lista avanza al siguiente pendiente.
            st.session_state.rf_picking_done_session = done + 1
            rf_clear_master_cache()
            st.rerun()
        # Si dijo otra cantidad de forma natural, el componente suele enviarla como CANTIDAD.
        reset_voice_autoplay(voice_key)
        st.rerun()

    if step == "ubicacion" and command in {"ESTOY_AQUI", "OK"}:
        st.session_state.rf_voice_last_zone_code = str(tarea.get("codigo_zona") or "")
        st.session_state.rf_voice_step = "material"
        st.session_state.rf_voice_cancel_confirm = False
        reset_voice_autoplay(voice_key)
        st.rerun()

    if step == "material" and command == "OK":
        st.session_state.rf_voice_same_location_intro = False
        st.session_state.rf_voice_step = "cantidad"
        st.session_state.rf_voice_cancel_confirm = False
        reset_voice_autoplay(voice_key)
        st.rerun()

    if step == "cantidad" and command == "OK":
        _confirm_current_picking_task(tarea, current, done, voice_event=event)

    if step == "cantidad" and command == "TENGO_CORTO":
        st.session_state.rf_voice_short_pending = True
        st.session_state.rf_voice_short_task_id = int(tarea["id_picking_detalle"])
        st.session_state.rf_voice_short_qty = None
        st.session_state.rf_voice_short_transcript = transcript
        reset_voice_autoplay(voice_key)
        st.rerun()

    st.session_state.rf_voice_presence_resume = False
    st.warning("Comando no reconocido. Intenta nuevamente o di repítelo.")
    reset_voice_autoplay(voice_key)
    st.rerun()


def _render_voice_picking_tareas() -> None:
    id_picking = int(st.session_state.rf_picking_id)
    tareas = rf_get_tareas_picking(id_picking)
    total = int(st.session_state.get("rf_picking_total") or len(tareas))
    done = int(st.session_state.get("rf_picking_done_session") or 0)

    if tareas.empty:
        st.session_state.rf_picking_mode = "voice_auditoria"
        st.rerun()

    tarea = tareas.iloc[0].to_dict()
    current = min(done + 1, total if total > 0 else 1)

    if st.session_state.get("rf_voice_task_key") != str(tarea["id_picking_detalle"]):
        st.session_state.rf_voice_task_key = str(tarea["id_picking_detalle"])
        previous_location = str(st.session_state.get("rf_voice_last_location_code") or "")
        current_location = str(tarea.get("codigo_ubicacion") or "")
        same_location = bool(previous_location and current_location and previous_location == current_location)
        st.session_state.rf_voice_same_location_intro = same_location
        # Si la tarea nueva está en la misma ubicación que la anterior, no volver a pedir
        # confirmación de ubicación: se informa "en esta misma ubicación" y se pasa
        # directamente al paso de material.
        st.session_state.rf_voice_step = "material" if same_location else "ubicacion"
        st.session_state.rf_voice_short_pending = False
        st.session_state.rf_voice_short_qty = None
        st.session_state.rf_voice_short_transcript = ""
        st.session_state.rf_voice_cancel_confirm = False
        st.session_state.rf_voice_presence_resume = False
        st.session_state.rf_voice_greeting_done = bool(st.session_state.get("rf_voice_greeting_done", False))

    step = str(st.session_state.get("rf_voice_step") or "ubicacion")
    last_zone = str(st.session_state.get("rf_voice_last_zone_code") or "")
    current_zone = str(tarea.get("codigo_zona") or "")
    include_zone = step == "ubicacion" and current_zone != last_zone
    greeting = not bool(st.session_state.get("rf_voice_greeting_done"))
    cancel_confirm = bool(st.session_state.get("rf_voice_cancel_confirm"))
    short_pending = bool(st.session_state.get("rf_voice_short_pending"))
    short_qty = st.session_state.get("rf_voice_short_qty")
    resume = bool(st.session_state.pop("rf_voice_presence_resume", False))
    unrecognized = bool(st.session_state.get("rf_voice_unrecognized"))
    same_location_intro = bool(st.session_state.get("rf_voice_same_location_intro"))

    if unrecognized:
        prompt = "Disculpa, no entendí."
        greeting = False
    else:
        prompt = build_voice_instruction(
            tarea,
            current,
            total,
            step=step,
            include_zone=include_zone,
            greeting=greeting,
            resume=resume,
            cancel_confirm=cancel_confirm,
            short_pending=short_pending,
            short_qty=short_qty,
            same_location=same_location_intro and step == "material",
        )
    if greeting:
        st.session_state.rf_voice_greeting_done = True

    _render_html_card(_task_card_html(tarea, current, total, _voice_step_label(step)))
    st.markdown(
        f"""
        <div class="rf-voice-note">
            <b>Comandos disponibles</b><br>{_voice_help(step, short_pending=short_pending, short_qty=short_qty, cancel_confirm=cancel_confirm)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    voice_key = _current_voice_key(tarea, step)
    event = render_voice_assistant(
        prompt,
        key=voice_key,
        auto_play=True,
        auto_listen=True,
        keepalive=True,
        keepalive_ms=10000,
        presence_mode=bool(st.session_state.get("rf_voice_waiting_presence")),
        height=92,
    )
    event = consume_voice_event(event, f"rf_voice_processed_{voice_key}")
    if event:
        _handle_voice_command(event, tarea, current, total, done, prompt, voice_key)


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


def _render_picking_auditoria(*, voice: bool = False) -> None:
    id_picking = int(st.session_state.rf_picking_id)
    nro = st.session_state.get("rf_picking_nro", "")
    st.subheader(f"Auditoría {nro}")
    auditoria = rf_get_auditoria_picking(id_picking)
    if auditoria.empty:
        st.warning("No hay tareas completadas para auditar.")
        rows = []
    else:
        st.dataframe(auditoria, use_container_width=True, hide_index=True)
        rows = auditoria.to_dict("records")

    if voice:
        audit_key = f"rf_voice_audit_{id_picking}"
        audit_prompt = build_audit_prompt(rows)
        voice_event = render_voice_assistant(
            audit_prompt,
            key=audit_key,
            auto_play=True,
            auto_listen=True,
            keepalive=True,
            keepalive_ms=10000,
            height=92,
        )
        voice_event = consume_voice_event(voice_event, f"rf_voice_processed_{audit_key}")
        if voice_event:
            command = str(voice_event.get("command") or "").upper()
            log_voice_event(
                id_usuario=current_user_id(),
                id_picking=id_picking,
                evento="AUDITORIA_COMANDO_VOZ",
                texto_emitido=audit_prompt,
                texto_reconocido=voice_event.get("transcript"),
                comando_normalizado=command,
                confianza=voice_event.get("confidence"),
            )
            if command == "CONFIRMAR_AUDITORIA":
                _back_to_picking_list(farewell=f"Picking {nro} finalizado. Buen trabajo.")
            elif command == "REPETIR":
                reset_voice_autoplay(audit_key)
                st.rerun()
    else:
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
    ubicaciones = rf_get_ubicaciones_activas()
    if ubicaciones.empty:
        st.error("No hay ubicaciones activas.")
        return

    origen = scan_text_input(
        "Ubicación de origen",
        key="rf_transfer_origen",
        placeholder="Escanea o escribe ubicación origen",
        button_label="Escanear ubicación origen",
        uppercase=True,
    ).strip().upper()
    
    if not origen:
        st.info("Escanea o ingresa una ubicación origen para ver códigos disponibles.")
        return
    
    origen_row = ubicaciones[
        ubicaciones["codigo_ubicacion"].astype(str).str.upper() == origen
    ]
    
    if origen_row.empty:
        st.error("La ubicación origen no existe o está inactiva.")
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

    destino = scan_text_input(
        "Ubicación destino",
        key="rf_transfer_destino",
        placeholder="Escanea o escribe ubicación destino",
        button_label="Abrir cámara",
        uppercase=True,
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
    code = scan_text_input(
        "Escanear o buscar",
        key="rf_stock_input_code",
        placeholder="SKU / EAN / descripción",
        button_label="Abrir cámara",
        uppercase=True,
    )
    ubicacion = scan_text_input(
        "Ubicación",
        key="rf_stock_input_ubicacion",
        placeholder="Código de ubicación opcional",
        button_label="Abrir cámara",
        uppercase=True,
    )
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

    consume_scanned_value()

    # Sin watchdog JS: evita listeners extra en cada touch.

    apply_rf_theme(login=False)
    st.session_state.setdefault("rf_page", "Inicio")
    render_sidebar()

    page = st.session_state.rf_page
    if page == "Inicio":
        render_home()
    elif page == "Ingresos":
        render_ingresos()
    elif page == "Picking":
        render_picking()
    elif page == "Voice Picking":
        render_voice_picking()
    elif page == "Transferencia":
        render_transferencia()
    elif page == "Stock":
        render_stock()
    else:
        render_home()


_rf_page = st.Page(_rf_main, title="RF WMS Block B")
_rf_nav = st.navigation([_rf_page], position="hidden")
_rf_nav.run()
