import pandas as pd
import streamlit as st

from src.ui_filters import render_multicriteria_filter

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
    bulk_insert_cuentas,
    delete_cuenta,
    get_cuentas_todas,
    insert_cuenta,
    update_cuenta,
)

st.title("🏢 Áreas / cuentas logísticas")

if "msg_cuenta" in st.session_state:
    st.success(st.session_state.pop("msg_cuenta"))

@st.cache_data(ttl=300, show_spinner=False)
def load_cuentas_data():
    return get_cuentas_todas()


cuentas = load_cuentas_data()


def validar_cuentas_excel(df: pd.DataFrame):
    required = [
        "codigo_cuenta",
        "nombre_cuenta",
        "responsable",
        "centro_costo",
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

    existing_codes = set(cuentas["codigo_cuenta"].astype(str).str.upper()) if not cuentas.empty else set()
    file_codes = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        codigo_cuenta = clean_upper(row["codigo_cuenta"])
        nombre_cuenta = clean_text(row["nombre_cuenta"])
        responsable = clean_text(row["responsable"])
        centro_costo = clean_upper(row["centro_costo"])

        if not codigo_cuenta:
            add_error(row_errors, excel_row, "codigo_cuenta", "El código de cuenta es obligatorio.")
            has_error = True
        elif codigo_cuenta in existing_codes:
            add_error(row_errors, excel_row, "codigo_cuenta", "El código de cuenta ya existe.")
            has_error = True
        elif codigo_cuenta in file_codes:
            add_error(row_errors, excel_row, "codigo_cuenta", "El código de cuenta está duplicado en el archivo.")
            has_error = True
        else:
            file_codes.add(codigo_cuenta)

        if not nombre_cuenta:
            add_error(row_errors, excel_row, "nombre_cuenta", "El nombre de cuenta es obligatorio.")
            has_error = True

        if not has_error:
            row_dict = {
                "codigo_cuenta": codigo_cuenta,
                "nombre_cuenta": nombre_cuenta,
                "responsable": responsable,
                "centro_costo": centro_costo,
            }

            rows.append(row_dict)
            preview_rows.append(row_dict)

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


tab_crear, tab_editar, tab_mod_masiva, tab_carga, tab_listado = st.tabs([
    "Agregar",
    "Modificar / eliminar",
    "Modificación masiva",
    "Carga masiva",
    "Listado",
])


with tab_crear:
    with st.form("form_cuenta"):
        codigo_cuenta = st.text_input("Código de área / cuenta").strip().upper()
        nombre_cuenta = st.text_input("Nombre de área / cuenta").strip()
        responsable = st.text_input("Responsable").strip()
        centro_costo = st.text_input("Centro de costo").strip().upper()
        submitted = st.form_submit_button("Guardar")

    if submitted:
        if not codigo_cuenta or not nombre_cuenta:
            st.error("Completa código y nombre.")
        else:
            try:
                insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo)
                st.session_state["msg_cuenta"] = "Área logística agregada correctamente."
                load_cuentas_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar. Revisa si el código ya existe.")
                st.exception(exc)


with tab_editar:
    if cuentas.empty:
        st.info("No hay áreas logísticas registradas.")
    else:
        labels = cuentas.apply(
            lambda r: f"{r['codigo_cuenta']} | {r['nombre_cuenta']} | {'Activa' if r['activo'] else 'Inactiva'}",
            axis=1,
        ).tolist()

        cuenta_label = st.selectbox("Selecciona área / cuenta", labels)
        selected = cuentas.iloc[labels.index(cuenta_label)]

        with st.form("form_editar_cuenta"):
            codigo_edit = st.text_input("Código", value=str(selected["codigo_cuenta"]))
            nombre_edit = st.text_input("Nombre", value=str(selected["nombre_cuenta"]))
            responsable_edit = st.text_input("Responsable", value=clean_text(selected["responsable"]))
            centro_costo_edit = st.text_input("Centro de costo", value=clean_text(selected["centro_costo"]))
            activo_edit = st.checkbox("Activa", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_cuenta(
                    int(selected["id_cuenta"]),
                    codigo_edit,
                    nombre_edit,
                    responsable_edit,
                    centro_costo_edit,
                    int(activo_edit),
                )
                st.session_state["msg_cuenta"] = "Área logística actualizada correctamente."
                load_cuentas_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar.")
                st.exception(exc)

        if eliminar:
            try:
                delete_cuenta(int(selected["id_cuenta"]))
                st.session_state["msg_cuenta"] = "Área logística desactivada correctamente."
                load_cuentas_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar.")
                st.exception(exc)



with tab_mod_masiva:
    st.write("Edita varias áreas logísticas y presiona Guardar modificación masiva.")
    if cuentas.empty:
        st.info("No hay áreas logísticas registradas.")
    else:
        editable = cuentas[["id_cuenta", "codigo_cuenta", "nombre_cuenta", "responsable", "centro_costo", "activo"]].copy()
        editable = render_multicriteria_filter(
            editable,
            [
                {"column": "codigo_cuenta", "label": "Filtrar por código(s) de cuenta", "mode": "exact", "placeholder": "Pega códigos de cuenta"},
                {"column": "nombre_cuenta", "label": "Filtrar por nombre(s)", "mode": "contains", "placeholder": "Pega nombres o palabras"},
                {"column": "responsable", "label": "Filtrar por responsable(s)", "mode": "contains", "placeholder": "Pega responsables"},
                {"column": "centro_costo", "label": "Filtrar por centro(s) de costo", "mode": "exact", "placeholder": "Pega centros de costo"},
            ],
            key_prefix="cuentas_mod_masiva",
        )
        edited_mass = st.data_editor(
            editable,
            use_container_width=True,
            hide_index=True,
            disabled=["id_cuenta"],
            key="cuentas_modificacion_masiva_editor",
            column_config={"activo": st.column_config.CheckboxColumn("activo")},
        )
        if st.button("Guardar modificación masiva", type="primary", use_container_width=True, key="cuentas_modificacion_masiva_guardar"):
            try:
                for _, row in edited_mass.iterrows():
                    update_cuenta(
                        int(row["id_cuenta"]),
                        row.get("codigo_cuenta"),
                        row.get("nombre_cuenta"),
                        row.get("responsable"),
                        row.get("centro_costo"),
                        int(bool(row.get("activo"))),
                    )
                st.session_state["msg_cuenta"] = f"Se actualizaron {len(edited_mass)} áreas logísticas correctamente."
                load_cuentas_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la modificación masiva.")
                st.exception(exc)

with tab_carga:
    columns = [
        "codigo_cuenta",
        "nombre_cuenta",
        "responsable",
        "centro_costo",
    ]

    example = [{
        "codigo_cuenta": "RET-LIM-01",
        "nombre_cuenta": "Operación Retail Lima",
        "responsable": "Responsable Retail",
        "centro_costo": "CC-RET-LIM",
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_areas_logisticas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de áreas logísticas", type=["xlsx"])

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_cuentas_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_cuentas_masivo"):
                    bulk_insert_cuentas(rows)
                    st.session_state["msg_cuenta"] = f"Se registraron {len(rows)} áreas logísticas correctamente."
                    load_cuentas_data.clear()
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo.")
            st.exception(exc)


with tab_listado:
    st.dataframe(cuentas, use_container_width=True, hide_index=True)
