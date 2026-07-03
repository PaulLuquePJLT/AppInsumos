from datetime import date
from src.time_utils import local_today

import streamlit as st

from src.queries import get_movimientos

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

with st.form("form_filtros_movimientos"):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=st.session_state.mov_fecha_inicio)
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=st.session_state.mov_fecha_fin)
    with col3:
        tipo = st.selectbox(
            "Tipo de movimiento",
            ["", "ENTRADA", "SALIDA_CUENTA", "TRANSFERENCIA"],
            index=["", "ENTRADA", "SALIDA_CUENTA", "TRANSFERENCIA"].index(st.session_state.mov_tipo)
            if st.session_state.mov_tipo in ["", "ENTRADA", "SALIDA_CUENTA", "TRANSFERENCIA"] else 0,
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

m1, m2, m3 = st.columns(3)
m1.metric("Movimientos", movimientos["id_movimiento"].nunique() if "id_movimiento" in movimientos.columns else len(movimientos))
m2.metric("Cantidad", f"{movimientos['cantidad'].sum():,.2f}" if "cantidad" in movimientos.columns else "0.00")
m3.metric("Monto S/.", f"S/ {movimientos['importe_soles'].sum():,.2f}" if "importe_soles" in movimientos.columns else "S/ 0.00")

st.dataframe(movimientos, use_container_width=True, hide_index=True)
