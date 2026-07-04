import streamlit as st

from src.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    UNKNOWN_LOGIN_MAX_ATTEMPTS,
    authenticate_user,
    request_password_reset,
    reset_password_with_code,
)
from src.theme import apply_login_theme, logo_img_html


def _init_auth_state():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    if "reset_identifier" not in st.session_state:
        st.session_state.reset_identifier = ""


def _login_brand(title: str = "App WMS Block B", subtitle: str = "Gestión de insumos, stock y operaciones logísticas"):
    logo = logo_img_html(width=94)
    st.markdown(
        f"""
        <div class="wms-login-brand">
            <div class="wms-login-logo">{logo}</div>
            <div class="login-title">{title}</div>
            <div class="login-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page():
    _init_auth_state()
    apply_login_theme()

    timeout_message = st.session_state.pop("timeout_message", None)
    if timeout_message:
        st.info(timeout_message)

    db_warning = st.session_state.pop("db_startup_warning", None)
    if db_warning:
        st.warning(db_warning)

    if st.session_state.auth_mode == "login":
        with st.form("login_form"):
            _login_brand()
            usuario = st.text_input("Usuario o correo")
            password = st.text_input("Contraseña", type="password")
            ingresar = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
            forgot = st.form_submit_button("¿Olvidaste tu contraseña?", use_container_width=True)

        if forgot:
            st.session_state.auth_mode = "forgot_request"
            st.rerun()

        if ingresar:
            login_exception = False
            handled_auth_failure = False
            try:
                user = authenticate_user(usuario, password)
            except AccountLockedError:
                handled_auth_failure = True
                st.session_state.reset_identifier = str(usuario or "").strip()
                st.error(
                    "La cuenta fue bloqueada por intentos fallidos. "
                    "Para desbloquearla, usa la opción ¿Olvidaste tu contraseña? y restablece tu clave."
                )
                user = None
            except InvalidCredentialsError as exc:
                handled_auth_failure = True
                user = None
                if exc.remaining_attempts > 0:
                    st.error(
                        "Usuario o contraseña incorrectos. "
                        f"Intentos restantes antes del bloqueo: {exc.remaining_attempts}."
                    )
                else:
                    st.error(
                        "La cuenta fue bloqueada por intentos fallidos. "
                        "Restablece tu contraseña para desbloquearla."
                    )
            except Exception as exc:
                login_exception = True
                st.warning(
                    "No se pudo validar el usuario en este momento. "
                    "Si Azure SQL estaba pausado, espera unos segundos e intenta nuevamente."
                )
                with st.expander("Detalle técnico"):
                    st.code(str(exc))
                user = None

            if user:
                st.session_state.auth_failed_unknown_count = 0
                st.session_state.authenticated = True
                st.session_state.auth_user = user
                st.session_state["last_activity_ts"] = __import__("time").time()
                st.rerun()
            elif not login_exception and not handled_auth_failure:
                if not str(usuario or "").strip() or not str(password or ""):
                    st.error("Ingresa usuario/correo y contraseña.")
                else:
                    st.session_state.auth_failed_unknown_count = int(st.session_state.get("auth_failed_unknown_count", 0)) + 1
                    if st.session_state.auth_failed_unknown_count >= UNKNOWN_LOGIN_MAX_ATTEMPTS:
                        st.error(
                            "Se alcanzó el máximo de intentos de ingreso en esta sesión. "
                            "Usa la recuperación de contraseña o vuelve a intentarlo más tarde."
                        )
                    else:
                        st.error("Usuario o contraseña incorrectos.")

    elif st.session_state.auth_mode == "forgot_request":
        with st.form("forgot_request_form"):
            _login_brand(
                title="Recuperar contraseña",
                subtitle="Ingresa tu usuario o correo registrado. Te enviaremos un código de recuperación.",
            )
            identifier = st.text_input("Usuario o correo")
            enviar = st.form_submit_button("Enviar código", use_container_width=True, type="primary")
            volver = st.form_submit_button("Volver al login", use_container_width=True)

        if volver:
            st.session_state.auth_mode = "login"
            st.rerun()

        if enviar:
            if not identifier.strip():
                st.error("Ingresa tu usuario o correo.")
            else:
                try:
                    request_password_reset(identifier)
                    st.session_state.reset_identifier = identifier.strip()
                    st.session_state.auth_mode = "forgot_verify"
                    st.success(
                        "Si el usuario existe y tiene correo configurado, "
                        "se envió un código de recuperación."
                    )
                    st.rerun()
                except Exception as exc:
                    error_text = str(exc)
                    if "Username and Password not accepted" in error_text or "535" in error_text:
                        st.error(
                            "El servidor SMTP rechazó las credenciales. "
                            "Si usas Gmail, utiliza una contraseña de aplicación."
                        )
                    else:
                        st.error(
                            "No se pudo enviar el correo. "
                            "Revisa la configuración SMTP en Streamlit Secrets."
                        )
                    with st.expander("Detalle técnico"):
                        st.code(error_text)

    elif st.session_state.auth_mode == "forgot_verify":
        with st.form("forgot_verify_form"):
            _login_brand(
                title="Restablecer contraseña",
                subtitle="Ingresa el código recibido por correo y define una nueva contraseña.",
            )
            identifier = st.text_input(
                "Usuario o correo",
                value=st.session_state.reset_identifier,
            )
            code = st.text_input("Código recibido")
            new_password = st.text_input("Nueva contraseña", type="password")
            confirm_password = st.text_input("Confirmar nueva contraseña", type="password")
            cambiar = st.form_submit_button(
                "Restablecer contraseña",
                use_container_width=True,
                type="primary",
            )
            enviar_otro = st.form_submit_button("Enviar otro código", use_container_width=True)
            volver = st.form_submit_button("Volver al login", use_container_width=True)

        if volver:
            st.session_state.auth_mode = "login"
            st.rerun()

        if enviar_otro:
            st.session_state.auth_mode = "forgot_request"
            st.rerun()

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
                    st.session_state.auth_mode = "login"
                else:
                    st.error(message)
