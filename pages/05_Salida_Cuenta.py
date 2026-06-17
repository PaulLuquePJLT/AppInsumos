import streamlit as st
from src.queries import get_productos_activos, get_ubicaciones, get_cuentas
from src.movimientos import registrar_salida_cuenta

st.title('➖ Salida a cuenta logística')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()
cuentas = get_cuentas()

if productos.empty or ubicaciones.empty or cuentas.empty:
    st.warning('Asegúrese de tener productos, ubicaciones y cuentas cargadas antes de registrar salidas.')

with st.form('form_salida'):
    producto_label = st.selectbox('Producto', productos['nombre_producto'].tolist())
    ubicacion_label = st.selectbox('Ubicación origen', ubicaciones['codigo_ubicacion'].tolist())
    cuenta_label = st.selectbox('Cuenta logística', cuentas['nombre_cuenta'].tolist())
    cantidad = st.number_input('Cantidad', min_value=0.01, step=1.0)
    lote = st.text_input('Lote', value='')
    referencia = st.text_input('Referencia')
    observacion = st.text_area('Observación')
    submitted = st.form_submit_button('Registrar salida')

    if submitted:
        id_producto = int(productos.loc[productos['nombre_producto'] == producto_label, 'id_producto'].iloc[0])
        id_ubicacion_origen = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == ubicacion_label, 'id_ubicacion'].iloc[0])
        id_cuenta = int(cuentas.loc[cuentas['nombre_cuenta'] == cuenta_label, 'id_cuenta'].iloc[0])
        try:
            registrar_salida_cuenta(id_producto, id_ubicacion_origen, id_cuenta, cantidad, 1, referencia, observacion, lote or None)
            st.success('Salida registrada correctamente.')
        except Exception as exc:
            st.error(str(exc))
