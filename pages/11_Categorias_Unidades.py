import pandas as pd
import streamlit as st

from src.bulk_utils import (
    add_error,
    build_excel_template,
    clean_text,
    clean_upper,
    read_excel_upload,
    show_validation_errors,
    validate_required_columns,
    normalize_columns,
)
from src.queries import (
    bulk_insert_categorias,
    bulk_insert_unidades,
    delete_categoria,
    delete_unidad,
    get_categorias_todas,
    get_unidades_todas,
    insert_categoria,
    insert_unidad,
    update_categoria,
    update_unidad,
)

st.title("🗂️ Categorías y unidades")

if "msg_maestro" in st.session_state:
    st.success(st.session_state.pop("msg_maestro"))

@st.cache_data(ttl=300, show_spinner=False)
def load_categorias_unidades_data():
    return get_categorias_todas(), get_unidades_todas()


categorias, unidades = load_categorias_unidades_data()


def validar_categorias_excel(df: pd.DataFrame):
    required = [
        "nombre_categoria",
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

    existing_names = set(categorias["nombre_categoria"].astype(str).str.upper()) if not categorias.empty else set()
    file_names = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        nombre_categoria = clean_text(row["nombre_categoria"])
        descripcion = clean_text(row["descripcion"])
        name_key = nombre_categoria.upper()

        if not nombre_categoria:
            add_error(row_errors, excel_row, "nombre_categoria", "El nombre de categoría es obligatorio.")
            has_error = True
        elif name_key in existing_names:
            add_error(row_errors, excel_row, "nombre_categoria", "La categoría ya existe.")
            has_error = True
        elif name_key in file_names:
            add_error(row_errors, excel_row, "nombre_categoria", "La categoría está duplicada en el archivo.")
            has_error = True
        else:
            file_names.add(name_key)

        if not has_error:
            row_dict = {
                "nombre_categoria": nombre_categoria,
                "descripcion": descripcion,
            }

            rows.append(row_dict)
            preview_rows.append(row_dict)

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


def validar_unidades_excel(df: pd.DataFrame):
    required = [
        "codigo_unidad",
        "nombre_unidad",
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

    existing_codes = set(unidades["codigo_unidad"].astype(str).str.upper()) if not unidades.empty else set()
    file_codes = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        codigo_unidad = clean_upper(row["codigo_unidad"])
        nombre_unidad = clean_text(row["nombre_unidad"])

        if not codigo_unidad:
            add_error(row_errors, excel_row, "codigo_unidad", "El código de unidad es obligatorio.")
            has_error = True
        elif codigo_unidad in existing_codes:
            add_error(row_errors, excel_row, "codigo_unidad", "El código de unidad ya existe.")
            has_error = True
        elif codigo_unidad in file_codes:
            add_error(row_errors, excel_row, "codigo_unidad", "El código de unidad está duplicado en el archivo.")
            has_error = True
        else:
            file_codes.add(codigo_unidad)

        if not nombre_unidad:
            add_error(row_errors, excel_row, "nombre_unidad", "El nombre de unidad es obligatorio.")
            has_error = True

        if not has_error:
            row_dict = {
                "codigo_unidad": codigo_unidad,
                "nombre_unidad": nombre_unidad,
            }

            rows.append(row_dict)
            preview_rows.append(row_dict)

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


tabs = st.tabs([
    "Agregar categoría",
    "Modificar / eliminar categoría",
    "Carga masiva categorías",
    "Agregar unidad",
    "Modificar / eliminar unidad",
    "Carga masiva unidades",
    "Listado",
])


with tabs[0]:
    with st.form("form_categoria"):
        nombre_categoria = st.text_input("Nombre de categoría").strip()
        descripcion = st.text_area("Descripción").strip()
        submitted = st.form_submit_button("Guardar categoría")

    if submitted:
        if not nombre_categoria:
            st.error("Completa el nombre de la categoría.")
        else:
            try:
                insert_categoria(nombre_categoria, descripcion)
                st.session_state["msg_maestro"] = "Categoría agregada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la categoría. Revisa si ya existe.")
                st.exception(exc)


with tabs[1]:
    if categorias.empty:
        st.info("No hay categorías registradas.")
    else:
        labels = categorias.apply(
            lambda r: f"{r['nombre_categoria']} | {'Activa' if r['activo'] else 'Inactiva'}",
            axis=1,
        ).tolist()

        selected_label = st.selectbox("Selecciona categoría", labels)
        selected = categorias.iloc[labels.index(selected_label)]

        with st.form("form_editar_categoria"):
            nombre_edit = st.text_input("Nombre de categoría", value=str(selected["nombre_categoria"]))
            descripcion_edit = st.text_area("Descripción", value=clean_text(selected["descripcion"]))
            activo_edit = st.checkbox("Activa", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_categoria(
                    int(selected["id_categoria"]),
                    nombre_edit,
                    descripcion_edit,
                    int(activo_edit),
                )
                st.session_state["msg_maestro"] = "Categoría actualizada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la categoría.")
                st.exception(exc)

        if eliminar:
            try:
                delete_categoria(int(selected["id_categoria"]))
                st.session_state["msg_maestro"] = "Categoría desactivada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la categoría.")
                st.exception(exc)


with tabs[2]:
    columns = [
        "nombre_categoria",
        "descripcion",
    ]

    example = [{
        "nombre_categoria": "Embalaje",
        "descripcion": "Insumos de embalaje",
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_categorias.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de categorías", type=["xlsx"], key="upload_categorias")

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_categorias_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_categorias_masivo"):
                    bulk_insert_categorias(rows)
                    st.session_state["msg_maestro"] = f"Se registraron {len(rows)} categorías correctamente."
                    load_categorias_unidades_data.clear()
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo.")
            st.exception(exc)


with tabs[3]:
    with st.form("form_unidad"):
        codigo_unidad = st.text_input("Código de unidad").strip().upper()
        nombre_unidad = st.text_input("Nombre de unidad").strip()
        submitted = st.form_submit_button("Guardar unidad")

    if submitted:
        if not codigo_unidad or not nombre_unidad:
            st.error("Completa código y nombre de unidad.")
        else:
            try:
                insert_unidad(codigo_unidad, nombre_unidad)
                st.session_state["msg_maestro"] = "Unidad agregada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la unidad. Revisa si el código ya existe.")
                st.exception(exc)


with tabs[4]:
    if unidades.empty:
        st.info("No hay unidades registradas.")
    else:
        labels = unidades.apply(
            lambda r: f"{r['codigo_unidad']} | {r['nombre_unidad']} | {'Activa' if r['activo'] else 'Inactiva'}",
            axis=1,
        ).tolist()

        selected_label = st.selectbox("Selecciona unidad", labels)
        selected = unidades.iloc[labels.index(selected_label)]

        with st.form("form_editar_unidad"):
            codigo_edit = st.text_input("Código de unidad", value=str(selected["codigo_unidad"]))
            nombre_edit = st.text_input("Nombre de unidad", value=str(selected["nombre_unidad"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_unidad(
                    int(selected["id_unidad"]),
                    codigo_edit,
                    nombre_edit,
                )
                st.session_state["msg_maestro"] = "Unidad actualizada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar la unidad.")
                st.exception(exc)

        if eliminar:
            try:
                delete_unidad(int(selected["id_unidad"]))
                st.session_state["msg_maestro"] = "Unidad desactivada correctamente."
                load_categorias_unidades_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar la unidad.")
                st.exception(exc)


with tabs[5]:
    columns = [
        "codigo_unidad",
        "nombre_unidad",
    ]

    example = [{
        "codigo_unidad": "UND",
        "nombre_unidad": "Unidad",
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_unidades.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de unidades", type=["xlsx"], key="upload_unidades")

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_unidades_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_unidades_masivo"):
                    bulk_insert_unidades(rows)
                    st.session_state["msg_maestro"] = f"Se registraron {len(rows)} unidades correctamente."
                    load_categorias_unidades_data.clear()
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo.")
            st.exception(exc)


with tabs[6]:
    st.subheader("Categorías")
    st.dataframe(categorias, use_container_width=True, hide_index=True)

    st.subheader("Unidades")
    st.dataframe(unidades, use_container_width=True, hide_index=True)
