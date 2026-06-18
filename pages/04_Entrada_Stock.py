import streamlit as st
from src.session import current_user_id
from src.queries import get_productos_activos, get_ubicaciones
from src.movimientos import registrar_entrada

st.title("➕ Entrada de stock")

productos = get_productos_activos()
ubicaciones = get_ubicaciones()

if productos.empty:
    st.warning("Primero registra al menos un producto activo.")
    st.stop()

if ubicaciones.empty:
    st.warning("Primero registra al menos una ubicación activa.")
    st.stop()

with st.form("form_entrada"):
    producto_label = st.selectbox("Producto", productos["nombre_producto"].tolist())
    ubicacion_label = st.selectbox("Ubicación destino", ubicaciones["codigo_ubicacion"].tolist())
    cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0)
    lote = st.text_input("Lote", value="").strip()
    referencia = st.text_input("Referencia").strip()
    observacion = st.text_area("Observación").strip()
    submitted = st.form_submit_button("Registrar entrada")

if submitted:
    id_producto = int(
        productos.loc[
            productos["nombre_producto"] == producto_label,
            "id_producto",
        ].iloc[0]
    )
    id_ubicacion = int(
        ubicaciones.loc[
            ubicaciones["codigo_ubicacion"] == ubicacion_label,
            "id_ubicacion",
        ].iloc[0]
    )

    try:
        registrar_entrada(
            id_producto=id_producto,
            id_ubicacion_destino=id_ubicacion,
            cantidad=cantidad,
            id_usuario=current_user_id(),
            referencia=referencia,
            observacion=observacion,
            lote=lote or None,
        )
        st.success("Entrada registrada correctamente.")
    except Exception as exc:
        st.error("No se pudo registrar la entrada.")
        st.exception(exc)
