import streamlit as st
from src.queries import get_stock_por_cuenta

st.title('💼 Stock por cuenta logística')
stock_cuenta = get_stock_por_cuenta()
st.dataframe(stock_cuenta)
