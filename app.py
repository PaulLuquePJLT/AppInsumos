import streamlit as st

st.set_page_config(
    page_title="Mini WMS Insumos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@media (max-width: 768px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    button { width: 100%; }
}
</style>
""", unsafe_allow_html=True)

st.title("📦 Mini WMS de Insumos")
st.write("Gestión de bodega, ubicaciones, stock y entregas a cuentas logísticas.")
st.info("Usa el menú lateral para navegar por los módulos del sistema.")
