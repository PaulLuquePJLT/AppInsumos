import streamlit as st

from src.queries import get_zonas, get_ubicaciones, insert_zona, insert_ubicacion

st.title("📍 Ubicaciones")

if "msg_ubicacion" in st.session_state:
    st.success(st.session_state.pop("msg_ubicacion"))

zonas = get_zonas()

with st.expander("Agregar zona de almacén"):
    with st.form("form_zona"):
        codigo_zona = st.text_input("Código de zona").strip().upper()
        nombre_zona = st.text_input("Nombre de zona").strip()
        descripcion = st.text_area("Descripción").strip()
        submitted_zona = st.form_submit_button("Guardar zona")

    if submitted_zona:
        if not codigo_zona or not nombre_zona:
            st.error("Complete código y nombre de zona.")
        else:
            try:
                insert_zona(codigo_zona, nombre_zona, descripcion)
                st.session_state["msg_ubicacion"] = "Zona agregada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la zona.")
                st.exception(exc)

with st.expander("Agregar ubicación"):
    if zonas.empty:
        st.warning("Primero registra al menos una zona de almacén.")
    else:
        with st.form("form_ubicacion"):
            codigo_ubicacion = st.text_input("Código de ubicación").strip().upper()
            zona = st.selectbox("Zona", zonas["codigo_zona"].tolist())
            tipo_ubicacion = st.selectbox(
                "Tipo de ubicación",
                ["Armario", "Rack", "Estante", "Piso", "Otro"],
            )
            pasillo = st.text_input("Pasillo").strip()
            rack = st.text_input("Rack / Armario").strip()
            nivel = st.text_input("Nivel / Repisa").strip()
            posicion = st.text_input("Posición").strip()
            capacidad_maxima = st.number_input(
                "Capacidad máxima referencial",
                min_value=0.0,
                step=1.0,
            )
            submitted_ubicacion = st.form_submit_button("Guardar ubicación")

        if submitted_ubicacion:
            if not codigo_ubicacion:
                st.error("Complete el código de ubicación.")
            else:
                id_zona = int(
                    zonas.loc[zonas["codigo_zona"] == zona, "id_zona"].iloc[0]
                )
                try:
                    insert_ubicacion(
                        codigo_ubicacion,
                        id_zona,
                        tipo_ubicacion,
                        pasillo,
                        rack,
                        nivel,
                        posicion,
                        capacidad_maxima,
                    )
                    st.session_state["msg_ubicacion"] = "Ubicación agregada correctamente."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo guardar la ubicación.")
                    st.exception(exc)

st.subheader("Zonas de almacén")
st.dataframe(zonas, use_container_width=True, hide_index=True)

st.subheader("Ubicaciones activas")
ubicaciones = get_ubicaciones()
st.dataframe(ubicaciones, use_container_width=True, hide_index=True)
