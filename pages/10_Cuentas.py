import streamlit as st

from src.queries import get_cuentas, insert_cuenta

st.title("🏢 Cuentas logísticas")

if "msg_cuenta" in st.session_state:
    st.success(st.session_state.pop("msg_cuenta"))

with st.expander("Agregar cuenta logística", expanded=True):
    with st.form("form_cuenta"):
        codigo_cuenta = st.text_input("Código de cuenta").strip().upper()
        nombre_cuenta = st.text_input("Nombre de cuenta").strip()
        responsable = st.text_input("Responsable").strip()
        centro_costo = st.text_input("Centro de costo").strip()
        submitted = st.form_submit_button("Guardar cuenta")

    if submitted:
        if not codigo_cuenta or not nombre_cuenta:
            st.error("Completa código y nombre de la cuenta.")
        else:
            try:
                insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo)
                st.session_state["msg_cuenta"] = "Cuenta logística agregada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la cuenta logística.")
                st.exception(exc)

st.subheader("Cuentas activas")
cuentas = get_cuentas()
st.dataframe(cuentas, use_container_width=True, hide_index=True)
