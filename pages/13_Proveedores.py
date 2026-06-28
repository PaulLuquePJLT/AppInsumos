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
    bulk_insert_proveedores,
    delete_proveedor,
    get_proveedores_todos,
    insert_proveedor,
    update_proveedor,
)

st.title("🚚 Proveedores")

if "msg_proveedor" in st.session_state:
    st.success(st.session_state.pop("msg_proveedor"))

@st.cache_data(ttl=300, show_spinner=False)
def load_proveedores_data():
    return get_proveedores_todos()


proveedores = load_proveedores_data()


ESTADOS = ["ACTIVO", "BLOQUEADO", "INACTIVO"]


def _is_valid_email(email: str) -> bool:
    email = clean_text(email)
    return email == "" or ("@" in email and "." in email.split("@")[-1])


def validar_proveedores_excel(df: pd.DataFrame):
    required = [
        "ruc",
        "razon_social",
        "rubro_proveedor",
        "contacto",
        "nro_telefono",
        "correo",
        "direccion",
        "pais",
        "ciudad",
        "estado",
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

    existing_rucs = set(proveedores["ruc"].astype(str).str.upper()) if not proveedores.empty else set()
    file_rucs = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        ruc = clean_upper(row["ruc"])
        razon_social = clean_text(row["razon_social"])
        rubro_proveedor = clean_text(row["rubro_proveedor"])
        contacto = clean_text(row["contacto"])
        nro_telefono = clean_text(row["nro_telefono"])
        correo = clean_text(row["correo"]).lower()
        direccion = clean_text(row["direccion"])
        pais = clean_text(row["pais"])
        ciudad = clean_text(row["ciudad"])
        estado = clean_upper(row["estado"] or "ACTIVO")

        if not ruc:
            add_error(row_errors, excel_row, "ruc", "El RUC es obligatorio.")
            has_error = True
        elif ruc in existing_rucs:
            add_error(row_errors, excel_row, "ruc", "El RUC ya existe en la base de datos.")
            has_error = True
        elif ruc in file_rucs:
            add_error(row_errors, excel_row, "ruc", "El RUC está duplicado en el archivo.")
            has_error = True
        else:
            file_rucs.add(ruc)

        if not razon_social:
            add_error(row_errors, excel_row, "razon_social", "La razón social es obligatoria.")
            has_error = True

        if estado not in ESTADOS:
            add_error(row_errors, excel_row, "estado", "Estado inválido. Usa ACTIVO, BLOQUEADO o INACTIVO.")
            has_error = True

        if not _is_valid_email(correo):
            add_error(row_errors, excel_row, "correo", "El correo no tiene un formato válido.")
            has_error = True

        if not has_error:
            row_dict = {
                "ruc": ruc,
                "razon_social": razon_social,
                "rubro_proveedor": rubro_proveedor,
                "contacto": contacto,
                "nro_telefono": nro_telefono,
                "correo": correo,
                "direccion": direccion,
                "pais": pais,
                "ciudad": ciudad,
                "estado": estado,
            }
            rows.append(row_dict)
            preview_rows.append(row_dict)

    if row_errors:
        return None, row_errors

    return pd.DataFrame(preview_rows), rows


tab_crear, tab_editar, tab_carga, tab_listado = st.tabs([
    "Agregar",
    "Modificar / eliminar",
    "Carga masiva",
    "Listado",
])


with tab_crear:
    with st.form("form_proveedor"):
        ruc = st.text_input("RUC", max_chars=20).strip().upper()
        razon_social = st.text_input("Razón social").strip()
        rubro_proveedor = st.text_input("Rubro proveedor").strip()
        contacto = st.text_input("Contacto").strip()
        nro_telefono = st.text_input("Nro. teléfono").strip()
        correo = st.text_input("Correo").strip().lower()
        direccion = st.text_input("Dirección").strip()
        pais = st.text_input("País", value="Perú").strip()
        ciudad = st.text_input("Ciudad").strip()
        estado = st.selectbox("Estado", ESTADOS, index=0)
        submitted = st.form_submit_button("Guardar proveedor")

    if submitted:
        if not ruc or not razon_social:
            st.error("Completa RUC y razón social.")
        elif not _is_valid_email(correo):
            st.error("El correo no tiene un formato válido.")
        else:
            try:
                insert_proveedor(
                    ruc,
                    razon_social,
                    rubro_proveedor,
                    contacto,
                    nro_telefono,
                    correo,
                    direccion,
                    pais,
                    ciudad,
                    estado,
                )
                st.session_state["msg_proveedor"] = "Proveedor agregado correctamente."
                load_proveedores_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar el proveedor. Revisa si el RUC ya existe.")
                st.exception(exc)


with tab_editar:
    if proveedores.empty:
        st.info("No hay proveedores registrados.")
    else:
        labels = proveedores.apply(
            lambda r: f"{r['ruc']} | {r['razon_social']} | {r['estado']} | {'Activo' if r['activo'] else 'Inactivo'}",
            axis=1,
        ).tolist()

        proveedor_label = st.selectbox("Selecciona proveedor", labels)
        selected = proveedores.iloc[labels.index(proveedor_label)]

        with st.form("form_editar_proveedor"):
            ruc_edit = st.text_input("RUC", value=str(selected["ruc"]), max_chars=20)
            razon_social_edit = st.text_input("Razón social", value=str(selected["razon_social"]))
            rubro_edit = st.text_input("Rubro proveedor", value=clean_text(selected["rubro_proveedor"]))
            contacto_edit = st.text_input("Contacto", value=clean_text(selected["contacto"]))
            telefono_edit = st.text_input("Nro. teléfono", value=clean_text(selected["nro_telefono"]))
            correo_edit = st.text_input("Correo", value=clean_text(selected["correo"]))
            direccion_edit = st.text_input("Dirección", value=clean_text(selected["direccion"]))
            pais_edit = st.text_input("País", value=clean_text(selected["pais"]))
            ciudad_edit = st.text_input("Ciudad", value=clean_text(selected["ciudad"]))

            estado_actual = selected["estado"] if selected["estado"] in ESTADOS else "ACTIVO"
            estado_edit = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(estado_actual))
            activo_edit = st.checkbox("Activo", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            if not ruc_edit.strip() or not razon_social_edit.strip():
                st.error("Completa RUC y razón social.")
            elif not _is_valid_email(correo_edit):
                st.error("El correo no tiene un formato válido.")
            else:
                try:
                    update_proveedor(
                        int(selected["id_proveedor"]),
                        ruc_edit,
                        razon_social_edit,
                        rubro_edit,
                        contacto_edit,
                        telefono_edit,
                        correo_edit,
                        direccion_edit,
                        pais_edit,
                        ciudad_edit,
                        estado_edit,
                        int(activo_edit),
                    )
                    st.session_state["msg_proveedor"] = "Proveedor actualizado correctamente."
                    load_proveedores_data.clear()
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo actualizar el proveedor.")
                    st.exception(exc)

        if eliminar:
            try:
                delete_proveedor(int(selected["id_proveedor"]))
                st.session_state["msg_proveedor"] = "Proveedor desactivado correctamente."
                load_proveedores_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar el proveedor.")
                st.exception(exc)


with tab_carga:
    st.write("Descarga la plantilla, complétala y luego carga el archivo para validarlo.")

    columns = [
        "ruc",
        "razon_social",
        "rubro_proveedor",
        "contacto",
        "nro_telefono",
        "correo",
        "direccion",
        "pais",
        "ciudad",
        "estado",
    ]

    example = [{
        "ruc": "20123456789",
        "razon_social": "Proveedor Demo S.A.C.",
        "rubro_proveedor": "Insumos de embalaje",
        "contacto": "Juan Pérez",
        "nro_telefono": "999888777",
        "correo": "contacto@proveedor.com",
        "direccion": "Av. Demo 123",
        "pais": "Perú",
        "ciudad": "Lima",
        "estado": "ACTIVO",
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_proveedores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de proveedores", type=["xlsx"])

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_proveedores_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_proveedores_masivo"):
                    bulk_insert_proveedores(rows)
                    st.session_state["msg_proveedor"] = f"Se registraron {len(rows)} proveedores correctamente."
                    load_proveedores_data.clear()
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo. Verifica que sea un Excel válido.")
            st.exception(exc)


with tab_listado:
    st.dataframe(proveedores, use_container_width=True, hide_index=True)
