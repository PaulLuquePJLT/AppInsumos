import streamlit as st

from src.queries import get_stock_por_cuenta

st.title("💼 Stock por cuenta logística")

try:
    stock_cuenta = get_stock_por_cuenta()
except Exception as exc:
    st.error(
        "No se pudo cargar el stock por cuenta. "
        "Revisa que dbo.vw_stock_por_cuenta exista y esté actualizada en Azure SQL."
    )
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

if stock_cuenta.empty:
    st.info("Todavía no hay stock entregado a cuentas logísticas.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    cuenta = st.text_input("Buscar cuenta")
with col2:
    producto = st.text_input("Buscar SKU o producto")

filtered = stock_cuenta.copy()

if cuenta.strip():
    value = cuenta.strip().lower()
    filtered = filtered[
        filtered["codigo_cuenta"].astype(str).str.lower().str.contains(value, na=False)
        | filtered["nombre_cuenta"].astype(str).str.lower().str.contains(value, na=False)
    ]

if producto.strip():
    value = producto.strip().lower()
    filtered = filtered[
        filtered["sku"].astype(str).str.lower().str.contains(value, na=False)
        | filtered["nombre_producto"].astype(str).str.lower().str.contains(value, na=False)
    ]

m1, m2, m3 = st.columns(3)
m1.metric("Registros", len(filtered))
m2.metric("Total entregado", f"{filtered['cantidad_entregada'].sum():,.2f}")
m3.metric("Stock neto cuentas", f"{filtered['cantidad_neta'].sum():,.2f}")

st.dataframe(filtered, use_container_width=True, hide_index=True)

st.download_button(
    "Descargar CSV",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name="stock_por_cuenta.csv",
    mime="text/csv",
)
