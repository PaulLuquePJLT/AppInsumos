import streamlit as st

from src.auth import authenticate_user, request_password_reset, reset_password_with_code


def _login_css():
    st.markdown(
        """
        <style>
        div[data-testid="stSidebar"] {display: none;}

        .block-container {
            max-width: 520px;
            padding-top: 10vh;
        }

        .login-title {
            text-align: center;
            font-size: 2.1rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .login-subtitle {
            text-align: center;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_auth_state():
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    if "reset_identifier" not in st.session_state:
        st.session_state.reset_identifier = ""


def render_login_page():
    _init_auth_state()
    _login_css()

    st.markdown('<div class="login-title">📦 App WMS Block B</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-subtitle">Acceso al sistema de insumos</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.auth_mode == "login":
        with st.form("login_form"):
            usuario = st.text_input("Usuario o correo")
            password = st.text_input("Contraseña", type="password")
            ingresar = st.form_submit_button("Ingresar", use_container_width=True)

        if ingresar:
            user = authenticate_user(usuario, password)

            if user:
                st.session_state.authenticated = True
                st.session_state.auth_user = user
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        if st.button("¿Olvidaste tu contraseña?", use_container_width=True):
            st.session_state.auth_mode = "forgot_request"
            st.rerun()

    elif st.session_state.auth_mode == "forgot_request":
        st.subheader("Recuperar contraseña")
        st.write(
            "Ingresa tu usuario o correo registrado. "
            "El sistema enviará un código de recuperación."
        )

        with st.form("forgot_request_form"):
            identifier = st.text_input("Usuario o correo")
            enviar = st.form_submit_button("Enviar código", use_container_width=True)

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
                    st.error(
                        "No se pudo enviar el correo. "
                        "Revisa la configuración SMTP en Streamlit Secrets."
                    )
                    st.exception(exc)

        if st.button("Volver al login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()

    elif st.session_state.auth_mode == "forgot_verify":
        st.subheader("Restablecer contraseña")

        with st.form("forgot_verify_form"):
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
            )

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

        col1, col2 = st.columns(2)

        if col1.button("Enviar otro código", use_container_width=True):
            st.session_state.auth_mode = "forgot_request"
            st.rerun()

        if col2.button("Volver al login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()
