import pandas as pd
import streamlit as st

from src.bulk_utils import (
    add_error,
    build_excel_template,
    clean_text,
    clean_upper,
    read_excel_upload,
    show_validation_errors,
    to_bool_int,
    to_float,
    validate_required_columns,
    normalize_columns,
)
from src.queries import (
    bulk_insert_productos,
    delete_producto,
    get_categorias,
    get_productos_todos,
    get_unidades,
    insert_producto,
    update_producto,
)

st.title("🧾 Productos")

if "msg_producto" in st.session_state:
    st.success(st.session_state.pop("msg_producto"))

categorias = get_categorias()
unidades = get_unidades()
productos = get_productos_todos()


def _categoria_id(nombre_categoria: str) -> int:
    return int(
        categorias.loc[
            categorias["nombre_categoria"] == nombre_categoria,
            "id_categoria",
        ].iloc[0]
    )


def _unidad_id(codigo_unidad: str) -> int:
    return int(
        unidades.loc[
            unidades["codigo_unidad"] == codigo_unidad,
            "id_unidad",
        ].iloc[0]
    )


def validar_productos_excel(df: pd.DataFrame):
    required = [
        "sku",
        "nombre_producto",
        "descripcion",
        "nombre_categoria",
        "codigo_unidad",
        "stock_minimo",
        "stock_maximo",
        "requiere_lote",
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

    valid_categories = set(categorias["nombre_categoria"].astype(str))
    valid_units = set(unidades["codigo_unidad"].astype(str).str.upper())
    existing_skus = set(productos["sku"].astype(str).str.upper()) if not productos.empty else set()

    file_skus = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        sku = clean_upper(row["sku"])
        nombre_producto = clean_text(row["nombre_producto"])
        descripcion = clean_text(row["descripcion"])
        nombre_categoria = clean_text(row["nombre_categoria"])
        codigo_unidad = clean_upper(row["codigo_unidad"])

        if not sku:
            add_error(row_errors, excel_row, "sku", "El SKU es obligatorio.")
            has_error = True
        elif sku in existing_skus:
            add_error(row_errors, excel_row, "sku", "El SKU ya existe en la base de datos.")
            has_error = True
        elif sku in file_skus:
            add_error(row_errors, excel_row, "sku", "El SKU está duplicado en el archivo.")
            has_error = True
        else:
            file_skus.add(sku)

        if not nombre_producto:
            add_error(row_errors, excel_row, "nombre_producto", "El nombre del producto es obligatorio.")
            has_error = True

        if nombre_categoria not in valid_categories:
            add_error(row_errors, excel_row, "nombre_categoria", "La categoría no existe o está inactiva.")
            has_error = True

        if codigo_unidad not in valid_units:
            add_error(row_errors, excel_row, "codigo_unidad", "La unidad no existe o está inactiva.")
            has_error = True

        try:
            stock_minimo = to_float(row["stock_minimo"], 0.0)
            stock_maximo = to_float(row["stock_maximo"], 0.0)
        except Exception:
            add_error(row_errors, excel_row, "stock", "Los stocks deben ser numéricos.")
            stock_minimo = 0.0
            stock_maximo = 0.0
            has_error = True

        if stock_minimo < 0 or stock_maximo < 0:
            add_error(row_errors, excel_row, "stock", "Los stocks no pueden ser negativos.")
            has_error = True

        if stock_maximo > 0 and stock_maximo < stock_minimo:
            add_error(row_errors, excel_row, "stock_maximo", "El stock máximo no puede ser menor al mínimo.")
            has_error = True

        if not has_error:
            id_categoria = _categoria_id(nombre_categoria)
            id_unidad = _unidad_id(codigo_unidad)
            requiere_lote = to_bool_int(row["requiere_lote"])

            rows.append({
                "sku": sku,
                "nombre_producto": nombre_producto,
                "descripcion": descripcion,
                "id_categoria": id_categoria,
                "id_unidad": id_unidad,
                "stock_minimo": stock_minimo,
                "stock_maximo": stock_maximo,
                "requiere_lote": requiere_lote,
            })

            preview_rows.append({
                "sku": sku,
                "nombre_producto": nombre_producto,
                "descripcion": descripcion,
                "nombre_categoria": nombre_categoria,
                "codigo_unidad": codigo_unidad,
                "stock_minimo": stock_minimo,
                "stock_maximo": stock_maximo,
                "requiere_lote": requiere_lote,
            })

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
    if categorias.empty or unidades.empty:
        st.warning("Antes de registrar productos debes tener categorías y unidades de medida.")
    else:
        with st.form("form_producto"):
            sku = st.text_input("SKU").strip().upper()
            nombre_producto = st.text_input("Nombre del producto").strip()
            descripcion = st.text_area("Descripción").strip()
            categoria = st.selectbox("Categoría", categorias["nombre_categoria"].tolist())
            unidad = st.selectbox("Unidad de medida", unidades["codigo_unidad"].tolist())
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)
            stock_maximo = st.number_input("Stock máximo", min_value=0.0, step=1.0)
            requiere_lote = st.checkbox("Requiere lote", value=False)
            submitted = st.form_submit_button("Guardar producto")

        if submitted:
            if not sku or not nombre_producto:
                st.error("Completa SKU y nombre del producto.")
            else:
                try:
                    insert_producto(
                        sku,
                        nombre_producto,
                        descripcion,
                        _categoria_id(categoria),
                        _unidad_id(unidad),
                        stock_minimo,
                        stock_maximo,
                        int(requiere_lote),
                    )
                    st.session_state["msg_producto"] = "Producto agregado correctamente."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo guardar el producto. Revisa si el SKU ya existe.")
                    st.exception(exc)


with tab_editar:
    if productos.empty:
        st.info("No hay productos registrados.")
    else:
        labels = productos.apply(
            lambda r: f"{r['sku']} | {r['nombre_producto']} | {'Activo' if r['activo'] else 'Inactivo'}",
            axis=1,
        ).tolist()

        producto_label = st.selectbox("Selecciona producto", labels)
        selected = productos.iloc[labels.index(producto_label)]

        with st.form("form_editar_producto"):
            sku_edit = st.text_input("SKU", value=str(selected["sku"]))
            nombre_edit = st.text_input("Nombre del producto", value=str(selected["nombre_producto"]))
            descripcion_edit = st.text_area("Descripción", value=clean_text(selected["descripcion"]))

            categoria_edit = st.selectbox(
                "Categoría",
                categorias["nombre_categoria"].tolist(),
                index=categorias["nombre_categoria"].tolist().index(selected["nombre_categoria"]),
            )

            unidad_edit = st.selectbox(
                "Unidad de medida",
                unidades["codigo_unidad"].tolist(),
                index=unidades["codigo_unidad"].tolist().index(selected["codigo_unidad"]),
            )

            stock_min_edit = st.number_input(
                "Stock mínimo",
                min_value=0.0,
                step=1.0,
                value=float(selected["stock_minimo"]),
            )

            stock_max_value = 0.0 if pd.isna(selected["stock_maximo"]) else float(selected["stock_maximo"])

            stock_max_edit = st.number_input(
                "Stock máximo",
                min_value=0.0,
                step=1.0,
                value=stock_max_value,
            )

            requiere_lote_edit = st.checkbox("Requiere lote", value=bool(selected["requiere_lote"]))
            activo_edit = st.checkbox("Activo", value=bool(selected["activo"]))

            col_a, col_b = st.columns(2)
            guardar = col_a.form_submit_button("Guardar cambios")
            eliminar = col_b.form_submit_button("Eliminar / desactivar")

        if guardar:
            try:
                update_producto(
                    int(selected["id_producto"]),
                    sku_edit,
                    nombre_edit,
                    descripcion_edit,
                    _categoria_id(categoria_edit),
                    _unidad_id(unidad_edit),
                    stock_min_edit,
                    stock_max_edit,
                    int(requiere_lote_edit),
                    int(activo_edit),
                )
                st.session_state["msg_producto"] = "Producto actualizado correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar el producto.")
                st.exception(exc)

        if eliminar:
            try:
                delete_producto(int(selected["id_producto"]))
                st.session_state["msg_producto"] = "Producto desactivado correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar el producto.")
                st.exception(exc)


with tab_carga:
    st.write("Descarga la plantilla, complétala y luego carga el archivo para validarlo.")

    columns = [
        "sku",
        "nombre_producto",
        "descripcion",
        "nombre_categoria",
        "codigo_unidad",
        "stock_minimo",
        "stock_maximo",
        "requiere_lote",
    ]

    example = [{
        "sku": "FILM-STRETCH-050CM",
        "nombre_producto": "Film stretch 50 cm",
        "descripcion": "Rollo de film para embalaje",
        "nombre_categoria": categorias["nombre_categoria"].iloc[0] if not categorias.empty else "Embalaje",
        "codigo_unidad": unidades["codigo_unidad"].iloc[0] if not unidades.empty else "RLL",
        "stock_minimo": 10,
        "stock_maximo": 100,
        "requiere_lote": 0,
    }]

    st.download_button(
        "Exportar plantilla de carga masiva",
        data=build_excel_template(columns, example),
        file_name="plantilla_productos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Cargar archivo Excel de productos", type=["xlsx"])

    if uploaded is not None:
        try:
            df_upload = normalize_columns(read_excel_upload(uploaded))
            preview, rows = validar_productos_excel(df_upload)

            if preview is None:
                show_validation_errors(st, rows)
            else:
                st.success("Archivo validado correctamente. Vista previa:")
                st.dataframe(preview, use_container_width=True, hide_index=True)

                if st.button("Registrar", key="registrar_productos_masivo"):
                    bulk_insert_productos(rows)
                    st.session_state["msg_producto"] = f"Se registraron {len(rows)} productos correctamente."
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo. Verifica que sea un Excel válido.")
            st.exception(exc)


with tab_listado:
    st.dataframe(productos, use_container_width=True, hide_index=True)
