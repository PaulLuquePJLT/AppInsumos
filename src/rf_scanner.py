from __future__ import annotations

from io import BytesIO

import streamlit as st


def _decode_barcode(uploaded_file) -> str | None:
    """Intenta decodificar código de barras desde una foto.

    Usa zxing-cpp si está disponible. Si no está instalado, devuelve None y
    se mantiene el flujo de escaneo por lector físico/teclado.
    """
    if uploaded_file is None:
        return None

    try:
        import zxingcpp  # type: ignore
        from PIL import Image
    except Exception:
        return None

    try:
        image = Image.open(BytesIO(uploaded_file.getvalue())).convert("RGB")
        results = zxingcpp.read_barcodes(image)
        if results:
            return str(results[0].text or "").strip()
    except Exception:
        return None

    return None


def scanner_text_input(
    label: str,
    key: str,
    placeholder: str = "",
    *,
    help_text: str | None = None,
    uppercase: bool = False,
) -> str:
    """Input RF con botón de cámara al costado.

    El botón abre un popover con cámara. En equipos Zebra se recomienda usar el
    lector físico como teclado; la cámara es un fallback para celulares.
    """
    col_input, col_scan = st.columns([0.78, 0.22], vertical_alignment="bottom")
    with col_input:
        value = st.text_input(label, key=key, placeholder=placeholder, help=help_text)

    with col_scan:
        popover = getattr(st, "popover", None)
        if popover:
            with st.popover("📷", use_container_width=True):
                st.caption("Escanea con cámara. Usa buena luz y enfoca el código.")
                photo = st.camera_input(
                    "Cámara",
                    key=f"{key}_camera",
                    label_visibility="collapsed",
                )
                if photo is not None:
                    decoded = _decode_barcode(photo)
                    if decoded:
                        st.session_state[key] = decoded.upper() if uppercase else decoded
                        st.success(f"Código detectado: {st.session_state[key]}")
                        st.rerun()
                    else:
                        st.warning("No se pudo leer el código. Usa el lector físico o escribe el valor.")
        else:
            st.caption("📷")

    value = str(st.session_state.get(key, value) or "").strip()
    return value.upper() if uppercase else value
