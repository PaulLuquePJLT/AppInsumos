import pandas as pd
import streamlit as st

from src.bulk_utils import (
    add_error,
    build_excel_template,
    clean_text,
    clean_upper,
    read_excel_upload,
    show_validation_errors,
    to_float,
    validate_required_columns,
    normalize_columns,
)
from src.queries import (
    bulk_insert_ubicaciones,
    bulk_insert_zonas,
    delete_ubicacion,
    delete_zona,
    get_ubicaciones_todas,
    get_zonas,
    get_zonas_todas,
    insert_ubicacion,
    insert_zona,
    update_ubicacion,
    update_zona,
)

st.title("📍 Zonas y ubicaciones")

if "msg_ubicacion" in st.session_state:
    st.success(st.session_state.pop("msg_ubicacion"))

zonas = get_zonas()
zonas_todas = get_zonas_todas()
ubicaciones = get_ubicaciones_todas()


def _zona_id(codigo_zona: str) -> int:
    return int(
        zonas.loc[
            zonas["codigo_zona"] == codigo_zona,
            "id_zona",
        ].iloc[0]
    )


def validar_zonas_excel(df: pd.DataFrame):
    required = [
        "codigo_zona",
        "nombre_zona",
        "descripcion",
    ]

    errors = validate_required_columns(df, required)

    if errors:
        return None, [
            {
                "fila_excel": "encabezado",
                "campo": "columnas",
                "error": err,
            }
            for err in errors
        ]

    existing_codes = set(zonas_todas["codigo_zona"].astype(str).str.upper()) if not zonas_todas.empty else set()
    file_codes = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        codigo_zona = clean_upper(row["codigo_zona"])
        nombre_zona = clean_text(row["nombre_zona"])
        descripcion = clean_text(row["descripcion"])

        if not codigo_zona:
            add_error(row_errors, excel_row, "codigo_zona", "El código de zona es obligatorio.")
            has_error = True
        elif codigo_zona in existing_codes:
            add_error(row_errors, excel_row, "codigo_zona", "El código de zona ya existe.")
            has_error = True
        elif codigo_zona in file_codes:
            add_error(row_errors, excel_row, "codigo_zona", "El código de zona está duplicado en el archivo.")
            has_error = True
        else:
            file_codes.add(codigo_zona)

        if not nombre_zona:
            add_error(row_errors, excel_row, "nombre_zona", "El nombre de zona es obligatorio.")
            has_error = True

        if not has_error:
            row_dict = {
                "codigo_zona": codigo_zona,
                "nombre_zona": nombre_zona,
                "descripcion": descripcion,
            }
            rows.append(row_dict)
            preview_rows.append(row_dict)

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


def validar_ubicaciones_excel(df: pd.DataFrame):
    required = [
        "codigo_ubicacion",
        "codigo_zona",
        "tipo_ubicacion",
        "pasillo",
        "rack",
        "nivel",
        "posicion",
        "capacidad_maxima",
    ]

    errors = validate_required_columns(df, required)

    if errors:
        return None, [
            {
                "fila_excel": "encabezado",
                "campo": "columnas",
                "error": err,
            }
            for err in errors
        ]

    valid_zones = set(zonas["codigo_zona"].astype(str).str.upper()) if not zonas.empty else set()
    existing_codes = set(ubicaciones["codigo_ubicacion"].astype(str).str.upper()) if not ubicaciones.empty else set()

    file_codes = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        codigo_ubicacion = clean_upper(row["codigo_ubicacion"])
        codigo_zona = clean_upper(row["codigo_zona"])
        tipo_ubicacion = clean_text(row["tipo_ubicacion"])

        if not codigo_ubicacion:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código de ubicación es obligatorio.")
            has_error = True
        elif codigo_ubicacion in existing_codes:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código de ubicación ya existe.")
            has_error = True
        elif codigo_ubicacion in file_codes:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código de ubicación está duplicado en el archivo.")
            has_error = True
        else:
            file_codes.add(codigo_ubicacion)

        if codigo_zona not in valid_zones:
            add_error(row_errors, excel_row, "codigo_zona", "La zona no existe o está inactiva.")
            has_error = True

        if not tipo_ubicacion:
            add_error(row_errors, excel_row, "tipo_ubicacion", "El tipo de ubicación es obligatorio.")
            has_error = True

        try:
            capacidad_maxima = to_float(row["capacidad_maxima"], 0.0)
        except Exception:
            add_error(row_errors, excel_row, "capacidad_maxima", "La capacidad máxima debe ser numérica.")
            capacidad_maxima = 0.0
            has_error = True

        if capacidad_maxima < 0:
            add_error(row_errors, excel_row, "capacidad_maxima", "La capacidad no puede ser negativa.")
            has_error = True

        if not has_error:
            row_insert = {
                "codigo_ubicacion": codigo_ubicacion,
                "id_zona": _zona_id(codigo_zona),
                "tipo_ubicacion": tipo_ubicacion,
                "pasillo": clean_text(row["pasillo"]),
                "rack": clean_text(row["rack"]),
                "nivel": clean_text(row["nivel"]),
                "posicion": clean_text(row["posicion"]),
                "capacidad_maxima": capacidad_maxima,
            }

            rows.append(row_insert)
            preview_rows.append({
                **row_insert,
                "codigo_zona": codigo_zona,
            })

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


tabs = st.tabs([
    "Agregar zona",
    "Modificar / eliminar zona",
    "Carga masiva zonas",
    "Agregar ubicación",
    "Modificar / eliminar ubicación",
    "Carga masiva ubicaciones",
    "Listado",
])


with tabs[0]:
    with st.form("form_zona"):
        codigo_zona = st.text_input("Código de zona").strip().upper()
        nombre_zona = st.text_input("Nombre de zona").strip()
        descripcion = st.text_area("Descripción").strip()
        submitted_zona = st.form_submit_button("Guardar zona")

    if submitted_zona:
        if not codigo_zona or not nombre_zona:
            st.error("Completa código y nombre de zona.")
        else:
            try:
                insert_zona(codigo_zona, nombre_zona, descripcion)
                st.session_state["msg_ubicacion"] = "Zona agregada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la zona. Revisa si el código ya existe.")
                st.exception(exc)


with tabs[1]:
    if zonas_todas.empty:
        st.info("No hay zonas registradas.")
    else:
        labels = zonas_todas.apply(
            lambda r: f"{r['codigo_zona']} | {r['nombre_zona']} | {'Activa' if r['activo'] else 'Inactiva'}",
            axis=1,
        ).tolist()

        zona_label = st.selectbox("Selecciona zona", labels)
        selected = zonas_todas.iloc[labels.index(zona_label)]

        with st.form("form_editar_zona"):
            codigo_edit = st.text_input("Código de zona", value=str(selected["codigo_zona"]))
            nombre_edit = st.text_input("Nombre de zona", value=str(selected["nombre_zona"]))
            descripcion_edit = st.text_area("Descripción", value=clean_text(selected["descripcion"]))
            activo_edit = st.checkbox("Activa", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_zona(
                    int(selected["id_zona"]),
                    codigo_edit,
                    nombre_edit,
                    descripcion_edit,
                    int(activo_edit),
                )
                st.session_state["msg_ubicacion"] = "Zona actualizada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la zona.")
                st.exception(exc)

        if eliminar:
            try:
                delete_zona(int(selected["id_zona"]))
                st.session_state["msg_ubicacion"] = "Zona desactivada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la zona.")
                st.exception(exc)


with tabs[2]:
    columns = [
        "codigo_zona",
        "nombre_zona",
        "descripcion",
    ]

    example = [{
        "codigo_zona": "RACK-A",
        "nombre_zona": "Rack Selectivo A",
        "descripcion": "Zona de racks selectivos",
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_zonas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de zonas", type=["xlsx"], key="upload_zonas")

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_zonas_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_zonas_masivo"):
                    bulk_insert_zonas(rows)
                    st.session_state["msg_ubicacion"] = f"Se registraron {len(rows)} zonas correctamente."
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo.")
            st.exception(exc)


with tabs[3]:
    if zonas.empty:
        st.warning("Primero registra al menos una zona activa.")
    else:
        with st.form("form_ubicacion"):
            codigo_ubicacion = st.text_input("Código de ubicación").strip().upper()
            zona = st.selectbox("Zona", zonas["codigo_zona"].tolist())
            tipo_ubicacion = st.selectbox("Tipo de ubicación", ["Armario", "Rack", "Estante", "Piso", "Otro"])
            pasillo = st.text_input("Pasillo").strip()
            rack = st.text_input("Rack / Armario").strip()
            nivel = st.text_input("Nivel / Repisa").strip()
            posicion = st.text_input("Posición").strip()
            capacidad_maxima = st.number_input("Capacidad máxima", min_value=0.0, step=1.0)
            submitted_ubicacion = st.form_submit_button("Guardar ubicación")

        if submitted_ubicacion:
            if not codigo_ubicacion:
                st.error("Completa el código de ubicación.")
            else:
                try:
                    insert_ubicacion(
                        codigo_ubicacion,
                        _zona_id(zona),
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
                    st.error("No se pudo guardar la ubicación. Revisa si el código ya existe.")
                    st.exception(exc)


with tabs[4]:
    if ubicaciones.empty:
        st.info("No hay ubicaciones registradas.")
    elif zonas.empty:
        st.warning("No hay zonas activas para editar ubicaciones.")
    else:
        labels = ubicaciones.apply(
            lambda r: f"{r['codigo_ubicacion']} | {r['codigo_zona']} | {'Activa' if r['activo'] else 'Inactiva'}",
            axis=1,
        ).tolist()

        ubicacion_label = st.selectbox("Selecciona ubicación", labels)
        selected = ubicaciones.iloc[labels.index(ubicacion_label)]

        zona_options = zonas["codigo_zona"].tolist()

        with st.form("form_editar_ubicacion"):
            codigo_edit = st.text_input("Código de ubicación", value=str(selected["codigo_ubicacion"]))

            zona_edit = st.selectbox(
                "Zona",
                zona_options,
                index=zona_options.index(selected["codigo_zona"]) if selected["codigo_zona"] in zona_options else 0,
            )

            tipo_edit = st.text_input("Tipo de ubicación", value=str(selected["tipo_ubicacion"]))
            pasillo_edit = st.text_input("Pasillo", value=clean_text(selected["pasillo"]))
            rack_edit = st.text_input("Rack / Armario", value=clean_text(selected["rack"]))
            nivel_edit = st.text_input("Nivel / Repisa", value=clean_text(selected["nivel"]))
            posicion_edit = st.text_input("Posición", value=clean_text(selected["posicion"]))

            capacidad_value = 0.0 if pd.isna(selected["capacidad_maxima"]) else float(selected["capacidad_maxima"])

            capacidad_edit = st.number_input(
                "Capacidad máxima",
                min_value=0.0,
                step=1.0,
                value=capacidad_value,
            )

            activo_edit = st.checkbox("Activa", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_ubicacion(
                    int(selected["id_ubicacion"]),
                    codigo_edit,
                    _zona_id(zona_edit),
                    tipo_edit,
                    pasillo_edit,
                    rack_edit,
                    nivel_edit,
                    posicion_edit,
                    capacidad_edit,
                    int(activo_edit),
                )
                st.session_state["msg_ubicacion"] = "Ubicación actualizada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la ubicación.")
                st.exception(exc)

        if eliminar:
            try:
                delete_ubicacion(int(selected["id_ubicacion"]))
                st.session_state["msg_ubicacion"] = "Ubicación desactivada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la ubicación.")
                st.exception(exc)


with tabs[5]:
    columns = [
        "codigo_ubicacion",
        "codigo_zona",
        "tipo_ubicacion",
        "pasillo",
        "rack",
        "nivel",
        "posicion",
        "capacidad_maxima",
    ]

    example = [{
        "codigo_ubicacion": "RCK-A-01-N01-P01",
        "codigo_zona": zonas["codigo_zona"].iloc[0] if not zonas.empty else "RACK-A",
        "tipo_ubicacion": "Rack",
        "pasillo": "A",
        "rack": "01",
        "nivel": "N01",
        "posicion": "P01",
        "capacidad_maxima": 100,
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_ubicaciones.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de ubicaciones", type=["xlsx"], key="upload_ubicaciones")

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_ubicaciones_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_ubicaciones_masivo"):
                    bulk_insert_ubicaciones(rows)
                    st.session_state["msg_ubicacion"] = f"Se registraron {len(rows)} ubicaciones correctamente."
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo.")
            st.exception(exc)


with tabs[6]:
    st.subheader("Zonas")
    st.dataframe(zonas_todas, use_container_width=True, hide_index=True)

    st.subheader("Ubicaciones")
    st.dataframe(ubicaciones, use_container_width=True, hide_index=True)
