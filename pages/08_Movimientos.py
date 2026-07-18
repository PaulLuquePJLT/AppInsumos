from src.time_utils import local_today

import pandas as pd
import streamlit as st

from src.queries import get_movimientos
from src.theme import download_report_xlsx_button

st.title("Movimientos")
st.caption("Por defecto se muestran solo los movimientos del día. Usa los filtros y presiona Consultar.")

if "mov_fecha_inicio" not in st.session_state:
    st.session_state.mov_fecha_inicio = local_today()
if "mov_fecha_fin" not in st.session_state:
    st.session_state.mov_fecha_fin = local_today()
if "mov_tipo" not in st.session_state:
    st.session_state.mov_tipo = ""
if "mov_cuenta" not in st.session_state:
    st.session_state.mov_cuenta = ""
if "mov_sku" not in st.session_state:
    st.session_state.mov_sku = ""

TIPOS = ["", "ENTRADA", "SALIDA_CUENTA", "SALIDA_AJUSTE", "TRANSFERENCIA"]

with st.form("form_filtros_movimientos"):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=st.session_state.mov_fecha_inicio)
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=st.session_state.mov_fecha_fin)
    with col3:
        tipo = st.selectbox(
            "Tipo de movimiento",
            TIPOS,
            index=TIPOS.index(st.session_state.mov_tipo) if st.session_state.mov_tipo in TIPOS else 0,
            format_func=lambda x: "Todos" if x == "" else x,
        )

    col4, col5, col6 = st.columns([1, 1, .7])
    with col4:
        cuenta = st.text_input("Cuenta logística", value=st.session_state.mov_cuenta)
    with col5:
        sku = st.text_input("SKU o producto", value=st.session_state.mov_sku)
    with col6:
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")

if consultar:
    if fecha_fin < fecha_inicio:
        st.error("La fecha fin no puede ser menor que la fecha inicio.")
        st.stop()
    st.session_state.mov_fecha_inicio = fecha_inicio
    st.session_state.mov_fecha_fin = fecha_fin
    st.session_state.mov_tipo = tipo
    st.session_state.mov_cuenta = cuenta.strip()
    st.session_state.mov_sku = sku.strip()

try:
    movimientos = get_movimientos(
        fecha_inicio=st.session_state.mov_fecha_inicio,
        fecha_fin=st.session_state.mov_fecha_fin,
        tipo_movimiento=st.session_state.mov_tipo,
        cuenta=st.session_state.mov_cuenta,
        sku=st.session_state.mov_sku,
    )
except Exception as exc:
    st.error("No se pudo consultar movimientos.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

if movimientos.empty:
    st.info("No hay movimientos para los filtros seleccionados.")
    st.stop()

movimientos = movimientos.copy()
movimientos["cantidad"] = pd.to_numeric(movimientos.get("cantidad", 0), errors="coerce").fillna(0.0)
movimientos["importe_soles"] = pd.to_numeric(movimientos.get("importe_soles", 0), errors="coerce").fillna(0.0)
movimientos["tipo_movimiento"] = movimientos["tipo_movimiento"].astype(str).str.upper()

# Mostrar las salidas como cantidades negativas. Las transferencias se mantienen
# positivas y se resaltan en amarillo para distinguirlas de ingresos/salidas.
salida_mask = movimientos["tipo_movimiento"].str.startswith("SALIDA")
movimientos.loc[salida_mask, "cantidad"] = -movimientos.loc[salida_mask, "cantidad"].abs()
movimientos.loc[salida_mask, "importe_soles"] = -movimientos.loc[salida_mask, "importe_soles"].abs()

# Redondeo operativo solicitado: una cifra decimal en cantidad.
movimientos["cantidad"] = movimientos["cantidad"].round(1)

m1, m2, m3 = st.columns(3)
m1.metric("Movimientos", movimientos["id_movimiento"].nunique() if "id_movimiento" in movimientos.columns else len(movimientos))
m2.metric("Cantidad neta", f"{movimientos['cantidad'].sum():,.1f}")
m3.metric("Monto neto S/.", f"S/ {movimientos['importe_soles'].sum():,.2f}")

# Botón explícito para evitar que el exportador automático no detecte Styler.
download_report_xlsx_button(
    movimientos,
    table_name="Movimientos",
    label="Descargar XLSX",
    key="download_movimientos_xlsx",
)


def _color_cantidad(row):
    styles = ["" for _ in row]
    if "cantidad" not in row.index:
        return styles
    idx = list(row.index).index("cantidad")
    tipo = str(row.get("tipo_movimiento", "")).upper()
    if tipo.startswith("SALIDA"):
        styles[idx] = "background-color: #FADADA; color: #7F1D1D; font-weight: 700;"
    elif tipo == "ENTRADA":
        styles[idx] = "background-color: #DDF7E8; color: #14532D; font-weight: 700;"
    elif tipo == "TRANSFERENCIA":
        styles[idx] = "background-color: #FFF4C7; color: #713F12; font-weight: 700;"
    return styles

styled = movimientos.style.apply(_color_cantidad, axis=1).format({
    "cantidad": "{:.1f}",
    "importe_soles": "{:,.2f}",
})
st.dataframe(styled, use_container_width=True, hide_index=True)
