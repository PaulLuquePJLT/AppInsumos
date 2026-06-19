import pandas as pd
import streamlit as st

from src.queries import get_stock_general, get_stock_por_ubicacion, get_stock_por_cuenta

st.title("📦 Stock")


def _show_db_error(nombre_consulta: str, exc: Exception):
    st.error(
        f"No se pudo cargar {nombre_consulta}. "
        "Revisa que las vistas SQL estén creadas y actualizadas en Azure SQL."
    )
    with st.expander("Detalle técnico"):
        st.code(str(exc))


def _render_table(df: pd.DataFrame, key_prefix: str):
    if df.empty:
        st.info("No hay registros para mostrar.")
        return

    col1, col2 = st.columns(2)
    with col1:
        filtro_producto = st.text_input("Buscar SKU o producto", key=f"{key_prefix}_producto")
    with col2:
        filtro_extra = st.text_input("Buscar ubicación/cuenta/zona", key=f"{key_prefix}_extra")

    filtered = df.copy()

    if filtro_producto.strip():
        value = filtro_producto.strip().lower()
        mask = False
        if "sku" in filtered.columns:
            mask = filtered["sku"].astype(str).str.lower().str.contains(value, na=False)
        if "nombre_producto" in filtered.columns:
            mask = mask | filtered["nombre_producto"].astype(str).str.lower().str.contains(value, na=False)
        filtered = filtered[mask]

    if filtro_extra.strip():
        value = filtro_extra.strip().lower()
        candidate_cols = [
            "codigo_ubicacion",
            "codigo_zona",
            "nombre_zona",
            "codigo_cuenta",
            "nombre_cuenta",
        ]
        mask = False
        has_col = False
        for col in candidate_cols:
            if col in filtered.columns:
                has_col = True
                mask = mask | filtered[col].astype(str).str.lower().str.contains(value, na=False)
        if has_col:
            filtered = filtered[mask]

    st.metric("Registros visibles", len(filtered))
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.download_button(
        "Descargar CSV",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{key_prefix}.csv",
        mime="text/csv",
        key=f"{key_prefix}_download",
    )


tabs = st.tabs(["Stock general", "Por ubicación", "Por cuenta", "Stock bajo mínimo"])

with tabs[0]:
    try:
        stock_general = get_stock_general()
        _render_table(stock_general, "stock_general")
    except Exception as exc:
        _show_db_error("stock general", exc)

with tabs[1]:
    try:
        stock_ubicacion = get_stock_por_ubicacion()
        _render_table(stock_ubicacion, "stock_ubicacion")
    except Exception as exc:
        _show_db_error("stock por ubicación", exc)

with tabs[2]:
    try:
        stock_cuenta = get_stock_por_cuenta()
        _render_table(stock_cuenta, "stock_cuenta")
    except Exception as exc:
        _show_db_error("stock por cuenta", exc)

with tabs[3]:
    try:
        stock_general = get_stock_general()
        if stock_general.empty:
            st.info("No hay productos para evaluar.")
        else:
            low_stock = stock_general[
                stock_general["cantidad_disponible"].fillna(stock_general["cantidad_total"]).fillna(0)
                <= stock_general["stock_minimo"].fillna(0)
            ]
            if low_stock.empty:
                st.success("No hay productos en stock bajo mínimo.")
            else:
                st.dataframe(
                    low_stock[["sku", "nombre_producto", "cantidad_total", "cantidad_en_picking", "cantidad_disponible", "stock_minimo"]]
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )
    except Exception as exc:
        _show_db_error("stock bajo mínimo", exc)
