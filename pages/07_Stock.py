import pandas as pd
import streamlit as st

from src.queries import get_stock_general, get_stock_por_ubicacion, get_stock_por_cuenta

st.title("Stock")
st.caption("Las consultas se ejecutan en Azure SQL con los filtros indicados. Usa filtros para evitar cargar tablas muy grandes.")


def _show_db_error(nombre_consulta: str, exc: Exception):
    st.error(
        f"No se pudo cargar {nombre_consulta}. "
        "Revisa que las vistas SQL estén creadas y actualizadas en Azure SQL."
    )
    with st.expander("Detalle técnico"):
        st.code(str(exc))


def _render_result(df: pd.DataFrame, label: str):
    if df.empty:
        st.info("No hay registros para mostrar con los filtros seleccionados.")
        return
    st.metric("Registros visibles", len(df))
    st.dataframe(df, use_container_width=True, hide_index=True)


vista = st.radio(
    "Vista",
    ["Stock general", "Por ubicación", "Por cuenta", "Stock bajo mínimo"],
    horizontal=True,
)

if vista == "Stock general":
    if "stock_general_sku" not in st.session_state:
        st.session_state.stock_general_sku = ""
    with st.form("form_stock_general"):
        sku = st.text_input("SKU o producto", value=st.session_state.stock_general_sku)
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")
    if consultar:
        st.session_state.stock_general_sku = sku.strip()
    try:
        df = get_stock_general(sku=st.session_state.stock_general_sku)
        _render_result(df, "stock_general")
    except Exception as exc:
        _show_db_error("stock general", exc)

elif vista == "Por ubicación":
    for key in ["stock_ubi_sku", "stock_ubi_ubicacion", "stock_ubi_zona"]:
        if key not in st.session_state:
            st.session_state[key] = ""
    with st.form("form_stock_ubicacion"):
        col1, col2, col3 = st.columns(3)
        with col1:
            sku = st.text_input("SKU o producto", value=st.session_state.stock_ubi_sku)
        with col2:
            ubicacion = st.text_input("Ubicación", value=st.session_state.stock_ubi_ubicacion)
        with col3:
            zona = st.text_input("Zona", value=st.session_state.stock_ubi_zona)
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")
    if consultar:
        st.session_state.stock_ubi_sku = sku.strip()
        st.session_state.stock_ubi_ubicacion = ubicacion.strip()
        st.session_state.stock_ubi_zona = zona.strip()
    try:
        df = get_stock_por_ubicacion(
            sku=st.session_state.stock_ubi_sku,
            ubicacion=st.session_state.stock_ubi_ubicacion,
            zona=st.session_state.stock_ubi_zona,
        )
        _render_result(df, "stock_ubicacion")
    except Exception as exc:
        _show_db_error("stock por ubicación", exc)

elif vista == "Por cuenta":
    for key in ["stock_cuenta_cuenta", "stock_cuenta_sku"]:
        if key not in st.session_state:
            st.session_state[key] = ""
    with st.form("form_stock_cuenta"):
        col1, col2 = st.columns(2)
        with col1:
            cuenta = st.text_input("Cuenta logística", value=st.session_state.stock_cuenta_cuenta)
        with col2:
            sku = st.text_input("SKU o producto", value=st.session_state.stock_cuenta_sku)
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")
    if consultar:
        st.session_state.stock_cuenta_cuenta = cuenta.strip()
        st.session_state.stock_cuenta_sku = sku.strip()
    try:
        df = get_stock_por_cuenta(
            cuenta=st.session_state.stock_cuenta_cuenta,
            sku=st.session_state.stock_cuenta_sku,
        )
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Registros", len(df))
            m2.metric("Total entregado", f"{df['cantidad_entregada'].sum():,.2f}" if "cantidad_entregada" in df.columns else "0.00")
            m3.metric("Stock neto cuentas", f"{df['cantidad_neta'].sum():,.2f}" if "cantidad_neta" in df.columns else "0.00")
        _render_result(df, "stock_cuenta")
    except Exception as exc:
        _show_db_error("stock por cuenta", exc)

else:
    if "stock_bajo_sku" not in st.session_state:
        st.session_state.stock_bajo_sku = ""
    with st.form("form_stock_bajo"):
        sku = st.text_input("SKU o producto", value=st.session_state.stock_bajo_sku)
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")
    if consultar:
        st.session_state.stock_bajo_sku = sku.strip()
    try:
        df = get_stock_general(sku=st.session_state.stock_bajo_sku)
        if df.empty:
            st.info("No hay productos para evaluar.")
        else:
            low_stock = df[
                df["cantidad_disponible"].fillna(df["cantidad_total"]).fillna(0)
                <= df["stock_minimo"].fillna(0)
            ]
            if low_stock.empty:
                st.success("No hay productos bajo mínimo.")
            else:
                cols = ["sku", "nombre_producto", "cantidad_total", "cantidad_en_picking", "cantidad_en_ingreso", "cantidad_disponible", "stock_minimo"]
                st.dataframe(low_stock[[c for c in cols if c in low_stock.columns]].reset_index(drop=True), use_container_width=True, hide_index=True)
    except Exception as exc:
        _show_db_error("stock bajo mínimo", exc)
