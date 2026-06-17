import streamlit as st
from src.queries import get_stock_general, get_stock_por_ubicacion, get_stock_por_cuenta

st.title('📦 Stock')

stock_general = get_stock_general()
stock_ubicacion = get_stock_por_ubicacion()
stock_cuenta = get_stock_por_cuenta()

tabs = st.tabs(['Stock general', 'Por ubicación', 'Por cuenta', 'Stock bajo mínimo'])

with tabs[0]:
    st.dataframe(stock_general)

with tabs[1]:
    st.dataframe(stock_ubicacion)

with tabs[2]:
    st.dataframe(stock_cuenta)

with tabs[3]:
    low_stock = stock_general[stock_general['cantidad_total'] <= stock_general['stock_minimo']]
    if low_stock.empty:
        st.success('No hay productos en stock bajo mínimo.')
    else:
        st.dataframe(low_stock[['sku', 'nombre_producto', 'cantidad_total', 'stock_minimo']].reset_index(drop=True))
