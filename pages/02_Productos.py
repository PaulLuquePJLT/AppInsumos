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

@st.cache_data(ttl=300, show_spinner=False)
def load_productos_data():
    return get_categorias(), get_unidades(), get_productos_todos()


categorias, unidades, productos = load_productos_data()


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


def normalizar_flag_ean(value) -> str:
    return "SI" if clean_upper(value) == "SI" else "NO"


def normalizar_ean_excel(value) -> str:
    value_text = clean_text(value)

    if value_text == "" or value_text.lower() in {"nan", "none", "null"}:
        return ""

    if value_text.endswith(".0"):
        maybe_int = value_text[:-2]
        if maybe_int.isdigit():
            return maybe_int

    return value_text


def validar_ean13(flag_aplica_ean: str, ean_serie: str) -> str | None:
    flag = normalizar_flag_ean(flag_aplica_ean)
    ean = normalizar_ean_excel(ean_serie)

    if flag == "SI" and not ean:
        return "El EAN 13 es obligatorio cuando Flag si aplica ean = SI."

    if ean and (not ean.isdigit() or len(ean) != 13):
        return "El EAN 13 debe tener exactamente 13 dígitos numéricos."

    return None


def parse_vida_util(value) -> int:
    value_text = clean_text(value)
    if value_text == "":
        return 0
    numeric = float(str(value_text).replace(",", "."))
    if numeric < 0 or numeric != int(numeric):
        raise ValueError("La vida útil cuenta debe ser un número entero mayor o igual a cero.")
    return int(numeric)


def validar_productos_excel(df: pd.DataFrame):
    required = [
        "sku",
        "nombre_producto",
        "descripcion",
        "ean_serie",
        "flag_aplica_ean",
        "precio_unitario",
        "vida_util_cuenta",
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
    existing_eans = set(
        productos["ean_serie"].fillna("").astype(str).str.strip()
    ) - {""} if not productos.empty and "ean_serie" in productos.columns else set()

    file_skus = set()
    file_eans = set()
    row_errors = []
    rows = []
    preview_rows = []

    for idx, row in df.iterrows():
        excel_row = idx + 2
        has_error = False

        sku = clean_upper(row["sku"])
        nombre_producto = clean_text(row["nombre_producto"])
        descripcion = clean_text(row["descripcion"])
        ean_serie = normalizar_ean_excel(row["ean_serie"])
        flag_aplica_ean = normalizar_flag_ean(row["flag_aplica_ean"])
        try:
            precio_unitario = to_float(row["precio_unitario"], 0.0)
        except Exception:
            precio_unitario = 0.0
            add_error(row_errors, excel_row, "precio_unitario", "El precio por unidad debe ser numérico.")
            has_error = True
        if precio_unitario < 0:
            add_error(row_errors, excel_row, "precio_unitario", "El precio por unidad no puede ser negativo.")
            has_error = True
        try:
            vida_util_cuenta = parse_vida_util(row["vida_util_cuenta"])
        except Exception:
            vida_util_cuenta = 0
            add_error(row_errors, excel_row, "vida_util_cuenta", "La vida útil cuenta debe ser un número entero mayor o igual a cero.")
            has_error = True
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

        ean_error = validar_ean13(flag_aplica_ean, ean_serie)
        if ean_error:
            add_error(row_errors, excel_row, "ean_serie", ean_error)
            has_error = True
        elif ean_serie:
            if ean_serie in existing_eans:
                add_error(row_errors, excel_row, "ean_serie", "El EAN 13 ya existe en la base de datos.")
                has_error = True
            elif ean_serie in file_eans:
                add_error(row_errors, excel_row, "ean_serie", "El EAN 13 está duplicado en el archivo.")
                has_error = True
            else:
                file_eans.add(ean_serie)

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
                "ean_serie": ean_serie or None,
                "flag_aplica_ean": flag_aplica_ean,
                "precio_unitario": precio_unitario,
                "vida_util_cuenta_dias": vida_util_cuenta,
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
                "ean_serie": ean_serie,
                "flag_aplica_ean": flag_aplica_ean,
                "precio_unitario": precio_unitario,
                "vida_util_cuenta": vida_util_cuenta,
                "nombre_categoria": nombre_categoria,
                "codigo_unidad": codigo_unidad,
                "stock_minimo": stock_minimo,
                "stock_maximo": stock_maximo,
                "requiere_lote": requiere_lote,
            })

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
    if categorias.empty or unidades.empty:
        st.warning("Antes de registrar productos debes tener categorías y unidades de medida.")
    else:
        with st.form("form_producto"):
            sku = st.text_input("SKU").strip().upper()
            nombre_producto = st.text_input("Nombre del producto").strip()
            descripcion = st.text_area("Descripción").strip()
            col_ean1, col_ean2 = st.columns([1.2, 1])
            with col_ean1:
                ean_serie = st.text_input("EAN 13", placeholder="Ejemplo: 7751234567890").strip()
            with col_ean2:
                flag_aplica_ean = st.selectbox("Flag si aplica ean", ["NO", "SI"])
            precio_unitario = st.number_input("Precio por unidad (S/)", min_value=0.0, step=0.01, format="%.4f")
            vida_util_cuenta = st.number_input("Vida Útil Cuenta (días)", min_value=0, step=1, value=0)
            categoria = st.selectbox("Categoría", categorias["nombre_categoria"].tolist())
            unidad = st.selectbox("Unidad de medida", unidades["codigo_unidad"].tolist())
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)
            stock_maximo = st.number_input("Stock máximo", min_value=0.0, step=1.0)
            requiere_lote = st.checkbox("Requiere lote", value=False)
            submitted = st.form_submit_button("Guardar producto")

        if submitted:
            if not sku or not nombre_producto:
                st.error("Completa SKU y nombre del producto.")
            elif validar_ean13(flag_aplica_ean, ean_serie):
                st.error(validar_ean13(flag_aplica_ean, ean_serie))
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
                        precio_unitario,
                        ean_serie,
                        flag_aplica_ean,
                        vida_util_cuenta,
                    )
                    st.session_state["msg_producto"] = "Producto agregado correctamente."
                    load_productos_data.clear()
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
            col_ean1, col_ean2 = st.columns([1.2, 1])
            with col_ean1:
                ean_edit = st.text_input("EAN 13", value=clean_text(selected.get("ean_serie", "")))
            with col_ean2:
                flag_options = ["NO", "SI"]
                flag_current = normalizar_flag_ean(selected.get("flag_aplica_ean", "NO"))
                flag_edit = st.selectbox("Flag si aplica ean", flag_options, index=flag_options.index(flag_current))

            precio_unitario_edit = st.number_input(
                "Precio por unidad (S/)",
                min_value=0.0,
                step=0.01,
                format="%.4f",
                value=float(selected.get("precio_unitario", 0) or 0),
            )
            vida_util_cuenta_edit = st.number_input(
                "Vida Útil Cuenta (días)",
                min_value=0,
                step=1,
                value=int(selected.get("vida_util_cuenta_dias", 0) or 0),
            )

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
            ean_error = validar_ean13(flag_edit, ean_edit)
            if ean_error:
                st.error(ean_error)
                st.stop()
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
                    precio_unitario_edit,
                    ean_edit,
                    flag_edit,
                    vida_util_cuenta_edit,
                )
                st.session_state["msg_producto"] = "Producto actualizado correctamente."
                load_productos_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo actualizar el producto.")
                st.exception(exc)

        if eliminar:
            try:
                delete_producto(int(selected["id_producto"]))
                st.session_state["msg_producto"] = "Producto desactivado correctamente."
                load_productos_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar el producto.")
                st.exception(exc)



with tab_mod_masiva:
    st.write("Edita múltiples productos en la tabla y presiona Guardar modificación masiva.")
    if productos.empty:
        st.info("No hay productos registrados.")
    else:
        editable = productos[[
            "id_producto", "sku", "nombre_producto", "descripcion", "ean_serie", "flag_aplica_ean",
            "precio_unitario", "vida_util_cuenta_dias", "nombre_categoria", "codigo_unidad",
            "stock_minimo", "stock_maximo", "requiere_lote", "activo"
        ]].copy()
        editable = render_multicriteria_filter(
            editable,
            [
                {"column": "sku", "label": "Filtrar por SKU(s)", "mode": "exact", "placeholder": "Pega SKUs desde Excel"},
                {"column": "ean_serie", "label": "Filtrar por EAN(s)", "mode": "exact", "placeholder": "Pega EANs desde Excel"},
                {"column": "nombre_producto", "label": "Filtrar por nombre/descripción", "mode": "contains", "placeholder": "Pega palabras o nombres"},
                {"column": "nombre_categoria", "label": "Filtrar por categoría(s)", "mode": "exact", "placeholder": "Pega categorías"},
                {"column": "codigo_unidad", "label": "Filtrar por unidad(es)", "mode": "exact", "placeholder": "Pega UND, CJ, etc."},
            ],
            key_prefix="productos_mod_masiva",
        )
        edited_mass = st.data_editor(
            editable,
            use_container_width=True,
            hide_index=True,
            disabled=["id_producto"],
            key="productos_modificacion_masiva_editor",
            column_config={
                "requiere_lote": st.column_config.CheckboxColumn("requiere_lote"),
                "activo": st.column_config.CheckboxColumn("activo"),
            },
        )
        if st.button("Guardar modificación masiva", type="primary", use_container_width=True, key="productos_modificacion_masiva_guardar"):
            try:
                if categorias.empty or unidades.empty:
                    st.error("Debes tener categorías y unidades activas para actualizar productos.")
                    st.stop()
                for _, row in edited_mass.iterrows():
                    flag = normalizar_flag_ean(row.get("flag_aplica_ean", "NO"))
                    ean = normalizar_ean_excel(row.get("ean_serie", ""))
                    ean_error = validar_ean13(flag, ean)
                    if ean_error:
                        raise ValueError(f"Producto {row.get('sku')}: {ean_error}")
                    categoria_nombre = clean_text(row.get("nombre_categoria"))
                    unidad_codigo = clean_upper(row.get("codigo_unidad"))
                    if categoria_nombre not in set(categorias["nombre_categoria"].astype(str)):
                        raise ValueError(f"Producto {row.get('sku')}: categoría no válida: {categoria_nombre}")
                    if unidad_codigo not in set(unidades["codigo_unidad"].astype(str).str.upper()):
                        raise ValueError(f"Producto {row.get('sku')}: unidad no válida: {unidad_codigo}")
                    update_producto(
                        int(row["id_producto"]),
                        row.get("sku"),
                        row.get("nombre_producto"),
                        row.get("descripcion"),
                        _categoria_id(categoria_nombre),
                        _unidad_id(unidad_codigo),
                        float(row.get("stock_minimo") or 0),
                        float(row.get("stock_maximo") or 0),
                        int(bool(row.get("requiere_lote"))),
                        int(bool(row.get("activo"))),
                        float(row.get("precio_unitario") or 0),
                        ean,
                        flag,
                        int(float(row.get("vida_util_cuenta_dias") or 0)),
                    )
                st.session_state["msg_producto"] = f"Se actualizaron {len(edited_mass)} productos correctamente."
                load_productos_data.clear()
                st.rerun()
            except Exception as exc:
                st.error("No se pudo guardar la modificación masiva de productos.")
                st.exception(exc)

with tab_carga:
    st.write("Descarga la plantilla, complétala y luego carga el archivo para validarlo.")

    columns = [
        "sku",
        "nombre_producto",
        "descripcion",
        "ean_serie",
        "flag_aplica_ean",
        "precio_unitario",
        "vida_util_cuenta",
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
        "ean_serie": "",
        "flag_aplica_ean": "NO",
        "precio_unitario": 0.00,
        "vida_util_cuenta": 0,
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
                    load_productos_data.clear()
                    st.rerun()

        except Exception as exc:
            st.error("No se pudo procesar el archivo. Verifica que sea un Excel válido.")
            st.exception(exc)


with tab_listado:
    st.dataframe(productos, use_container_width=True, hide_index=True)
