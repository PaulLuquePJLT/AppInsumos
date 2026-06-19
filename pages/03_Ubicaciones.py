import pandas as pd
import streamlit as st

from src.bulk_utils import (
    add_error,
    build_excel_template,
    clean_text,
    clean_upper,
    normalize_columns,
    read_excel_upload,
    show_validation_errors,
    to_bool_int,
    to_float,
    validate_required_columns,
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
st.caption("Ahora las ubicaciones tienen secuencia de recorrido, flag stage y flag surtible para picking.")

if "msg_ubicacion" in st.session_state:
    st.success(st.session_state.pop("msg_ubicacion"))

zonas = get_zonas()
zonas_todas = get_zonas_todas()
ubicaciones = get_ubicaciones_todas()


def _zona_id(codigo_zona: str) -> int:
    return int(zonas.loc[zonas["codigo_zona"] == codigo_zona, "id_zona"].iloc[0])


def validar_zonas_excel(df: pd.DataFrame):
    required = ["codigo_zona", "nombre_zona", "descripcion"]
    errors = validate_required_columns(df, required)
    if errors:
        return None, [{"fila_excel": "encabezado", "campo": "columnas", "error": err} for err in errors]

    existing = set(zonas_todas["codigo_zona"].astype(str).str.upper()) if not zonas_todas.empty else set()
    seen = set()
    rows, preview, row_errors = [], [], []
    for idx, row in df.iterrows():
        excel_row = idx + 2
        codigo = clean_upper(row["codigo_zona"])
        nombre = clean_text(row["nombre_zona"])
        descripcion = clean_text(row["descripcion"])
        has_error = False
        if not codigo:
            add_error(row_errors, excel_row, "codigo_zona", "El código de zona es obligatorio."); has_error = True
        elif codigo in existing:
            add_error(row_errors, excel_row, "codigo_zona", "El código de zona ya existe."); has_error = True
        elif codigo in seen:
            add_error(row_errors, excel_row, "codigo_zona", "El código está duplicado en el archivo."); has_error = True
        else:
            seen.add(codigo)
        if not nombre:
            add_error(row_errors, excel_row, "nombre_zona", "El nombre de zona es obligatorio."); has_error = True
        if not has_error:
            item = {"codigo_zona": codigo, "nombre_zona": nombre, "descripcion": descripcion}
            rows.append(item); preview.append(item)
    if row_errors:
        return None, row_errors
    return pd.DataFrame(preview), rows


def validar_ubicaciones_excel(df: pd.DataFrame):
    required = [
        "codigo_ubicacion", "codigo_zona", "tipo_ubicacion", "pasillo", "rack", "nivel", "posicion",
        "capacidad_maxima", "secuencia", "es_surtible", "es_stage",
    ]
    errors = validate_required_columns(df, required)
    if errors:
        return None, [{"fila_excel": "encabezado", "campo": "columnas", "error": err} for err in errors]

    valid_zones = set(zonas["codigo_zona"].astype(str).str.upper()) if not zonas.empty else set()
    existing = set(ubicaciones["codigo_ubicacion"].astype(str).str.upper()) if not ubicaciones.empty else set()
    seen = set()
    rows, preview, row_errors = [], [], []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        codigo = clean_upper(row["codigo_ubicacion"])
        codigo_zona = clean_upper(row["codigo_zona"])
        tipo = clean_text(row["tipo_ubicacion"])
        has_error = False
        if not codigo:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código de ubicación es obligatorio."); has_error = True
        elif codigo in existing:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código de ubicación ya existe."); has_error = True
        elif codigo in seen:
            add_error(row_errors, excel_row, "codigo_ubicacion", "El código está duplicado en el archivo."); has_error = True
        else:
            seen.add(codigo)
        if codigo_zona not in valid_zones:
            add_error(row_errors, excel_row, "codigo_zona", "La zona no existe o está inactiva."); has_error = True
        if not tipo:
            add_error(row_errors, excel_row, "tipo_ubicacion", "El tipo de ubicación es obligatorio."); has_error = True
        try:
            capacidad = to_float(row["capacidad_maxima"], 0.0)
            secuencia = int(to_float(row["secuencia"], 999999))
        except Exception:
            add_error(row_errors, excel_row, "numericos", "Capacidad y secuencia deben ser numéricos."); has_error = True
            capacidad, secuencia = 0.0, 999999
        if not has_error:
            item = {
                "codigo_ubicacion": codigo,
                "id_zona": _zona_id(codigo_zona),
                "tipo_ubicacion": tipo,
                "pasillo": clean_text(row["pasillo"]),
                "rack": clean_text(row["rack"]),
                "nivel": clean_text(row["nivel"]),
                "posicion": clean_text(row["posicion"]),
                "capacidad_maxima": capacidad,
                "secuencia": secuencia,
                "es_surtible": to_bool_int(row["es_surtible"]),
                "es_stage": to_bool_int(row["es_stage"]),
            }
            rows.append(item)
            preview.append({**item, "codigo_zona": codigo_zona})
    if row_errors:
        return None, row_errors
    return pd.DataFrame(preview), rows


tabs = st.tabs([
    "Agregar zona", "Modificar / eliminar zona", "Carga masiva zonas",
    "Agregar ubicación", "Modificar / eliminar ubicación", "Carga masiva ubicaciones", "Listado",
])

with tabs[0]:
    with st.form("form_zona"):
        codigo_zona = st.text_input("Código de zona").strip().upper()
        nombre_zona = st.text_input("Nombre de zona").strip()
        descripcion = st.text_area("Descripción").strip()
        submitted = st.form_submit_button("Guardar zona")
    if submitted:
        if not codigo_zona or not nombre_zona:
            st.error("Completa código y nombre de zona.")
        else:
            try:
                insert_zona(codigo_zona, nombre_zona, descripcion)
                st.session_state["msg_ubicacion"] = "Zona agregada correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la zona."); st.exception(exc)

with tabs[1]:
    if zonas_todas.empty:
        st.info("No hay zonas registradas.")
    else:
        labels = zonas_todas.apply(lambda r: f"{r['codigo_zona']} | {r['nombre_zona']} | {'Activa' if r['activo'] else 'Inactiva'}", axis=1).tolist()
        selected = zonas_todas.iloc[labels.index(st.selectbox("Selecciona zona", labels))]
        with st.form("form_editar_zona"):
            codigo = st.text_input("Código de zona", value=str(selected["codigo_zona"]))
            nombre = st.text_input("Nombre de zona", value=str(selected["nombre_zona"]))
            desc = st.text_area("Descripción", value=clean_text(selected["descripcion"]))
            activo = st.checkbox("Activa", value=bool(selected["activo"]))
            col1, col2 = st.columns(2)
            guardar = col1.form_submit_button("Guardar cambios")
            eliminar = col2.form_submit_button("Eliminar / desactivar")
        if guardar:
            try:
                update_zona(int(selected["id_zona"]), codigo, nombre, desc, int(activo))
                st.session_state["msg_ubicacion"] = "Zona actualizada correctamente."; st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la zona."); st.exception(exc)
        if eliminar:
            try:
                delete_zona(int(selected["id_zona"]))
                st.session_state["msg_ubicacion"] = "Zona desactivada correctamente."; st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la zona."); st.exception(exc)

with tabs[2]:
    columns = ["codigo_zona", "nombre_zona", "descripcion"]
    example = [{"codigo_zona": "RACK-A", "nombre_zona": "Rack Selectivo A", "descripcion": "Zona de racks selectivos"}]
    st.download_button("Exportar plantilla de carga masiva", data=build_excel_template(columns, example), file_name="plantilla_zonas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    uploaded = st.file_uploader("Cargar archivo Excel de zonas", type=["xlsx"], key="upload_zonas")
    if uploaded is not None:
        df_upload = normalize_columns(read_excel_upload(uploaded))
        preview, rows = validar_zonas_excel(df_upload)
        if preview is None:
            show_validation_errors(st, rows)
        else:
            st.success("Archivo validado correctamente."); st.dataframe(preview, use_container_width=True, hide_index=True)
            if st.button("Registrar", key="registrar_zonas_masivo"):
                bulk_insert_zonas(rows); st.session_state["msg_ubicacion"] = f"Se registraron {len(rows)} zonas."; st.rerun()

with tabs[3]:
    if zonas.empty:
        st.warning("Primero registra al menos una zona activa.")
    else:
        with st.form("form_ubicacion"):
            codigo = st.text_input("Código de ubicación").strip().upper()
            zona = st.selectbox("Zona", zonas["codigo_zona"].tolist())
            tipo = st.selectbox("Tipo de ubicación", ["Armario", "Rack", "Estante", "Piso", "Stage", "Otro"])
            pasillo = st.text_input("Pasillo").strip()
            rack = st.text_input("Rack / Armario").strip()
            nivel = st.text_input("Nivel / Repisa").strip()
            posicion = st.text_input("Posición").strip()
            capacidad = st.number_input("Capacidad máxima", min_value=0.0, step=1.0)
            secuencia = st.number_input("Secuencia de picking", min_value=0, step=1, value=999999)
            es_surtible = st.checkbox("Surtible para picking", value=True)
            es_stage = st.checkbox("Es ubicación stage", value=False)
            submitted = st.form_submit_button("Guardar ubicación")
        if submitted:
            if not codigo:
                st.error("Completa el código de ubicación.")
            else:
                try:
                    insert_ubicacion(codigo, _zona_id(zona), tipo, pasillo, rack, nivel, posicion, capacidad, secuencia, int(es_surtible), int(es_stage))
                    st.session_state["msg_ubicacion"] = "Ubicación agregada correctamente."; st.rerun()
                except Exception as exc:
                    st.error("No se pudo guardar la ubicación."); st.exception(exc)

with tabs[4]:
    if ubicaciones.empty:
        st.info("No hay ubicaciones registradas.")
    elif zonas.empty:
        st.warning("No hay zonas activas para editar ubicaciones.")
    else:
        labels = ubicaciones.apply(lambda r: f"{r['codigo_ubicacion']} | Seq {r['secuencia']} | {r['codigo_zona']} | {'Activa' if r['activo'] else 'Inactiva'}", axis=1).tolist()
        selected = ubicaciones.iloc[labels.index(st.selectbox("Selecciona ubicación", labels))]
        zona_options = zonas["codigo_zona"].tolist()
        with st.form("form_editar_ubicacion"):
            codigo = st.text_input("Código de ubicación", value=str(selected["codigo_ubicacion"]))
            zona = st.selectbox("Zona", zona_options, index=zona_options.index(selected["codigo_zona"]) if selected["codigo_zona"] in zona_options else 0)
            tipo = st.text_input("Tipo de ubicación", value=str(selected["tipo_ubicacion"]))
            pasillo = st.text_input("Pasillo", value=clean_text(selected["pasillo"]))
            rack = st.text_input("Rack / Armario", value=clean_text(selected["rack"]))
            nivel = st.text_input("Nivel / Repisa", value=clean_text(selected["nivel"]))
            posicion = st.text_input("Posición", value=clean_text(selected["posicion"]))
            capacidad = st.number_input("Capacidad máxima", min_value=0.0, step=1.0, value=0.0 if pd.isna(selected["capacidad_maxima"]) else float(selected["capacidad_maxima"]))
            secuencia = st.number_input("Secuencia de picking", min_value=0, step=1, value=int(selected["secuencia"]))
            es_surtible = st.checkbox("Surtible para picking", value=bool(selected["es_surtible"]))
            es_stage = st.checkbox("Es ubicación stage", value=bool(selected["es_stage"]))
            activo = st.checkbox("Activa", value=bool(selected["activo"]))
            col1, col2 = st.columns(2)
            guardar = col1.form_submit_button("Guardar cambios")
            eliminar = col2.form_submit_button("Eliminar / desactivar")
        if guardar:
            try:
                update_ubicacion(int(selected["id_ubicacion"]), codigo, _zona_id(zona), tipo, pasillo, rack, nivel, posicion, capacidad, secuencia, int(es_surtible), int(es_stage), int(activo))
                st.session_state["msg_ubicacion"] = "Ubicación actualizada correctamente."; st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la ubicación."); st.exception(exc)
        if eliminar:
            try:
                delete_ubicacion(int(selected["id_ubicacion"]))
                st.session_state["msg_ubicacion"] = "Ubicación desactivada correctamente."; st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la ubicación."); st.exception(exc)

with tabs[5]:
    columns = ["codigo_ubicacion", "codigo_zona", "tipo_ubicacion", "pasillo", "rack", "nivel", "posicion", "capacidad_maxima", "secuencia", "es_surtible", "es_stage"]
    example = [{"codigo_ubicacion": "ARM-01-REP-01", "codigo_zona": zonas["codigo_zona"].iloc[0] if not zonas.empty else "ARM", "tipo_ubicacion": "Armario", "pasillo": "A", "rack": "01", "nivel": "REP-01", "posicion": "P01", "capacidad_maxima": 100, "secuencia": 10, "es_surtible": 1, "es_stage": 0}]
    st.download_button("Exportar plantilla de carga masiva", data=build_excel_template(columns, example), file_name="plantilla_ubicaciones.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    uploaded = st.file_uploader("Cargar archivo Excel de ubicaciones", type=["xlsx"], key="upload_ubicaciones")
    if uploaded is not None:
        df_upload = normalize_columns(read_excel_upload(uploaded))
        preview, rows = validar_ubicaciones_excel(df_upload)
        if preview is None:
            show_validation_errors(st, rows)
        else:
            st.success("Archivo validado correctamente."); st.dataframe(preview, use_container_width=True, hide_index=True)
            if st.button("Registrar", key="registrar_ubicaciones_masivo"):
                bulk_insert_ubicaciones(rows); st.session_state["msg_ubicacion"] = f"Se registraron {len(rows)} ubicaciones."; st.rerun()

with tabs[6]:
    st.subheader("Zonas")
    st.dataframe(zonas_todas, use_container_width=True, hide_index=True)
    st.subheader("Ubicaciones")
    st.dataframe(ubicaciones, use_container_width=True, hide_index=True)
