import streamlit as st

from src.queries import get_movimientos


st.title("📜 Movimientos")

movimientos = get_movimientos()

if movimientos.empty:
    st.info("No hay movimientos registrados.")
    st.stop()

col1, col2, col3 = st.columns(3)

with col1:
    tipo = st.selectbox(
        "Tipo de movimiento",
        [""] + sorted(
            movimientos["tipo_movimiento"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
    )

with col2:
    sku = st.text_input("SKU o producto")

with col3:
    cuenta = st.text_input("Cuenta logística")

filtered = movimientos.copy()

if tipo:
    filtered = filtered[filtered["tipo_movimiento"].astype(str) == tipo]

if sku.strip():
    sku_filter = sku.strip().lower()
    filtered = filtered[
        filtered["sku"].astype(str).str.lower().str.contains(sku_filter, na=False)
        | filtered["nombre_producto"]
        .astype(str)
        .str.lower()
        .str.contains(sku_filter, na=False)
    ]

if cuenta.strip():
    cuenta_filter = cuenta.strip().lower()
    filtered = filtered[
        filtered["codigo_cuenta"]
        .astype(str)
        .str.lower()
        .str.contains(cuenta_filter, na=False)
        | filtered["nombre_cuenta"]
        .astype(str)
        .str.lower()
        .str.contains(cuenta_filter, na=False)
    ]

st.metric("Movimientos visibles", len(filtered))

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Descargar movimientos filtrados",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name="movimientos_wms.csv",
    mime="text/csv",
)
