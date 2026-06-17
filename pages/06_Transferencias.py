import streamlit as st
from src.queries import get_productos_activos, get_ubicaciones
from src.movimientos import registrar_transferencia

st.title('🔁 Transferencias')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()

if productos.empty or ubicaciones.empty:
    st.warning('Asegúrese de tener productos y ubicaciones para registrar transferencias.')

with st.form('form_transferencia'):
    producto_label = st.selectbox('Producto', productos['nombre_producto'].tolist())
    origen_label = st.selectbox('Ubicación origen', ubicaciones['codigo_ubicacion'].tolist())
    destino_label = st.selectbox('Ubicación destino', ubicaciones['codigo_ubicacion'].tolist())
    cantidad = st.number_input('Cantidad', min_value=0.01, step=1.0)
    lote = st.text_input('Lote', value='')
    referencia = st.text_input('Referencia')
    observacion = st.text_area('Observación')
    submitted = st.form_submit_button('Registrar transferencia')

    if submitted:
        if origen_label == destino_label:
            st.error('La ubicación origen y destino no pueden ser iguales.')
        else:
            id_producto = int(productos.loc[productos['nombre_producto'] == producto_label, 'id_producto'].iloc[0])
            id_ubicacion_origen = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == origen_label, 'id_ubicacion'].iloc[0])
            id_ubicacion_destino = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == destino_label, 'id_ubicacion'].iloc[0])
            try:
                registrar_transferencia(id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, 1, referencia, observacion, lote or None)
                st.success('Transferencia registrada correctamente.')
            except Exception as exc:
                st.error(str(exc))
