import streamlit as st
from src.queries import get_stock_general, get_productos_activos, get_ubicaciones, get_cuentas

st.title('📊 Dashboard')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()
cuentas = get_cuentas()
stock_general = get_stock_general()

col1, col2, col3, col4 = st.columns(4)
col1.metric('Productos', len(productos))
col2.metric('Ubicaciones', len(ubicaciones))
col3.metric('Cuentas logísticas', len(cuentas))
col4.metric('Productos en stock', len(stock_general[stock_general['cantidad_total'] > 0]))

low_stock = stock_general[stock_general['cantidad_total'] <= stock_general['stock_minimo']]
if not low_stock.empty:
    st.warning(f'Se encontraron {len(low_stock)} productos con stock igual o inferior al mínimo.')
    st.dataframe(low_stock[['sku', 'nombre_producto', 'cantidad_total', 'stock_minimo']].reset_index(drop=True))
else:
    st.success('No hay productos en stock bajo mínimo.')
