import streamlit as st

from src.queries import get_stock_por_cuenta

st.title("Stock por cuenta logística")
st.caption("La consulta se ejecuta en Azure SQL con los filtros indicados.")

if "stock_cta_cuenta" not in st.session_state:
    st.session_state.stock_cta_cuenta = ""
if "stock_cta_producto" not in st.session_state:
    st.session_state.stock_cta_producto = ""

with st.form("form_stock_cuentas"):
    col1, col2, col3 = st.columns([1.2, 1.2, .7])
    with col1:
        cuenta = st.text_input("Buscar cuenta", value=st.session_state.stock_cta_cuenta)
    with col2:
        producto = st.text_input("Buscar SKU o producto", value=st.session_state.stock_cta_producto)
    with col3:
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")

if consultar:
    st.session_state.stock_cta_cuenta = cuenta.strip()
    st.session_state.stock_cta_producto = producto.strip()

try:
    stock_cuenta = get_stock_por_cuenta(
        cuenta=st.session_state.stock_cta_cuenta,
        sku=st.session_state.stock_cta_producto,
    )
except Exception as exc:
    st.error(
        "No se pudo cargar el stock por cuenta. "
        "Revisa que dbo.vw_stock_por_cuenta exista y esté actualizada en Azure SQL."
    )
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

if stock_cuenta.empty:
    st.info("No hay stock de cuenta para los filtros seleccionados.")
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Registros", len(stock_cuenta))
m2.metric("Total entregado", f"{stock_cuenta['cantidad_entregada'].sum():,.2f}")
m3.metric("Stock neto cuentas", f"{stock_cuenta['cantidad_neta'].sum():,.2f}")

st.dataframe(stock_cuenta, use_container_width=True, hide_index=True)
