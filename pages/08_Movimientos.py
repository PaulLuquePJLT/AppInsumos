import streamlit as st
from src.queries import get_movimientos

st.title('📜 Movimientos')
movimientos = get_movimientos()
st.dataframe(movimientos)
