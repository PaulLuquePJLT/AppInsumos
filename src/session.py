import time

import streamlit as st
import streamlit.components.v1 as components

SESSION_TIMEOUT_SECONDS = 300


def current_user() -> dict:
    return st.session_state.get("auth_user") or {}


def current_user_id(default: int = 1) -> int:
    user = current_user()
    return int(user.get("id_usuario") or default)


def is_admin() -> bool:
    return bool(current_user().get("is_admin"))


def clear_auth_session() -> None:
    """Limpia los datos de sesión del usuario autenticado."""
    for key in [
        "authenticated",
        "auth_user",
        "auth_mode",
        "reset_identifier",
        "last_activity_ts",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def enforce_session_timeout(timeout_seconds: int = SESSION_TIMEOUT_SECONDS) -> bool:
    """Cierra sesión si transcurrió el tiempo máximo sin interacción.

    Retorna True si la sesión fue cerrada.
    """
    now = time.time()
    last_activity = st.session_state.get("last_activity_ts")

    if st.session_state.get("authenticated") and last_activity:
        if now - float(last_activity) > timeout_seconds:
            clear_auth_session()
            st.session_state["timeout_message"] = (
                "Tu sesión se cerró automáticamente por 5 minutos de inactividad."
            )
            return True

    st.session_state["last_activity_ts"] = now
    return False


def render_idle_timeout_script(timeout_seconds: int = SESSION_TIMEOUT_SECONDS) -> None:
    """Inyecta un watchdog de inactividad en el navegador.

    El cierre real se ejecuta en Python cuando la URL vuelve con ?wms_timeout=1.
    """
    timeout_ms = int(timeout_seconds * 1000)
    components.html(
        f"""
        <script>
        (function() {{
            const timeoutMs = {timeout_ms};
            let timer = null;

            function triggerTimeout() {{
                try {{
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set('wms_timeout', '1');
                    window.parent.location.href = url.toString();
                }} catch (e) {{
                    window.location.search = '?wms_timeout=1';
                }}
            }}

            function resetTimer() {{
                if (timer) {{ clearTimeout(timer); }}
                timer = setTimeout(triggerTimeout, timeoutMs);
            }}

            try {{
                const events = ['click','keydown','mousemove','wheel','scroll','touchstart'];
                events.forEach(function(evt) {{
                    window.parent.document.addEventListener(evt, resetTimer, true);
                }});
                window.parent.document.addEventListener('visibilitychange', resetTimer, true);
                resetTimer();
            }} catch (e) {{
                resetTimer();
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )
