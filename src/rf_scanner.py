from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT_DIR = Path(__file__).resolve().parents[1] / "components" / "rf_barcode_scanner"
_rf_barcode_scanner = components.declare_component(
    "rf_barcode_scanner",
    path=str(_COMPONENT_DIR),
)


def consume_scanned_value() -> None:
    """Compatibilidad con versiones previas.

    La versión anterior del scanner enviaba el código por query params. La nueva
    versión usa un componente bidireccional de Streamlit y aplica el valor dentro
    de scan_text_input(). Esta función queda como no-op para no romper imports.
    """
    return None


def _apply_pending_scan(key: str, uppercase: bool) -> None:
    pending_key = f"{key}_pending_scan"
    if pending_key not in st.session_state:
        return

    value = str(st.session_state.pop(pending_key) or "").strip()
    if uppercase:
        value = value.upper()

    # Importante: aplicar antes de crear el widget con key=key.
    st.session_state[key] = value
    st.session_state[f"{key}_scanner_open"] = False
    st.session_state["rf_last_scanned_value"] = value
    st.session_state["rf_last_scanned_target"] = key


def scan_text_input(
    label: str,
    key: str,
    placeholder: str = "",
    *,
    button_label: str = "Escanear",
    help: str | None = None,
    max_chars: int | None = None,
    uppercase: bool = False,
) -> str:
    """Input RF con botón de cámara.

    Usa un componente bidireccional real para que, apenas se detecte el código,
    el valor se escriba en st.session_state[key] y aparezca en el input.
    """
    _apply_pending_scan(key, uppercase)

    # Mobile/RF: el input y el botón de cámara deben caber en la misma fila.
    # Se agrega una tercera columna invisible de seguridad para que Streamlit no
    # empuje el botón fuera del viewport en pantallas angostas.
    col_input, col_scan, _col_pad = st.columns([0.70, 0.09, 0.13], gap=None)
    with col_input:
        value = st.text_input(
            label,
            key=key,
            placeholder=placeholder,
            help=help,
            max_chars=max_chars,
        )
    with col_scan:
        st.markdown('<div class="rf-scan-button-spacer"></div>', unsafe_allow_html=True)
        if st.button("📷", key=f"{key}_scanner_btn", help=button_label, use_container_width=False):
            st.session_state[f"{key}_scanner_open"] = True

    if st.session_state.get(f"{key}_scanner_open"):
        _render_scanner_panel(target_key=key, title=button_label, uppercase=uppercase)

    return str(value or "").upper() if uppercase else str(value or "")


def _render_scanner_panel(target_key: str, title: str = "Escanear código", uppercase: bool = False) -> None:
    with st.container(border=True):
        c1, c2 = st.columns([0.72, 0.28])
        with c1:
            st.markdown(f"**{title}**")
            st.caption("Apunta al código. Se intentará usar la cámara posterior.")
        with c2:
            if st.button("Cerrar", key=f"{target_key}_scanner_close", use_container_width=True):
                st.session_state[f"{target_key}_scanner_open"] = False
                st.rerun()

        result = _rf_barcode_scanner(
            target_key=target_key,
            preferred_camera="environment",
            default=None,
            key=f"rf_barcode_component_{target_key}",
        )

        code = _extract_code(result)
        if code:
            if uppercase:
                code = code.upper()
            st.session_state[f"{target_key}_pending_scan"] = code
            st.session_state[f"{target_key}_scanner_open"] = False
            st.rerun()


def _extract_code(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        return str(result.get("code") or result.get("value") or "").strip()
    return ""
