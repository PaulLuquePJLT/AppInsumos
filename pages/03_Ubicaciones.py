import streamlit as st
from src.queries import get_zonas, get_ubicaciones, insert_zona, insert_ubicacion

st.title('📍 Ubicaciones')

zonas = get_zonas()

with st.expander('Agregar zona de almacén'):
    with st.form('form_zona'):
        codigo_zona = st.text_input('Código de zona')
        nombre_zona = st.text_input('Nombre de zona')
        descripcion = st.text_area('Descripción')
        submitted_zona = st.form_submit_button('Guardar zona')
        if submitted_zona:
            if not codigo_zona or not nombre_zona:
                st.error('Complete código y nombre de zona.')
            else:
                insert_zona(codigo_zona, nombre_zona, descripcion)
                st.success('Zona agregada correctamente.')

with st.expander('Agregar ubicación'):
    with st.form('form_ubicacion'):
        codigo_ubicacion = st.text_input('Código de ubicación')
        zona = st.selectbox('Zona', zonas['codigo_zona'].tolist() if not zonas.empty else [])
        tipo_ubicacion = st.selectbox('Tipo de ubicación', ['Armario', 'Rack', 'Estante', 'Otro'])
        pasillo = st.text_input('Pasillo')
        rack = st.text_input('Rack')
        nivel = st.text_input('Nivel')
        posicion = st.text_input('Posición')
        capacidad_maxima = st.number_input('Capacidad máxima', min_value=0.0, step=1.0)
        submitted_ubicacion = st.form_submit_button('Guardar ubicación')
        if submitted_ubicacion:
            if not codigo_ubicacion or zonas.empty:
                st.error('Complete el código y seleccione una zona.')
            else:
                id_zona = int(zonas.loc[zonas['codigo_zona'] == zona, 'id_zona'].iloc[0])
                insert_ubicacion(codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima)
                st.success('Ubicación agregada correctamente.')

st.subheader('Zonas de almacén')
st.dataframe(zonas)

st.subheader('Ubicaciones activas')
ubicaciones = get_ubicaciones()
st.dataframe(ubicaciones)
