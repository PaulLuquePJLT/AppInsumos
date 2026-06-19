from datetime import date

import pandas as pd
import streamlit as st

from src.movimientos import registrar_entrada_migo
from src.queries import get_productos_activos, get_proveedores, get_ubicaciones
from src.session import current_user_id

STAGE_LOCATION_CODE = "B1.RE.01"
ITEM_COLUMNS = [
    "codigo_producto",
    "nombre_producto",
    "unidad_medida",
    "cantidad",
    "lote",
    "codigo_ubicacion_destino",
    "texts",
    "requiere_lote",
]

st.title("➕ Entrada de mercancías")
st.caption("Flujo Ingreso: cabecera editable, posiciones de materiales, verificación y contabilización.")

if "msg_entrada" in st.session_state:
    st.success(st.session_state.pop("msg_entrada"))

productos = get_productos_activos()
ubicaciones = get_ubicaciones()
proveedores = get_proveedores()

if productos.empty:
    st.warning("Primero registra al menos un producto activo.")
    st.stop()

if ubicaciones.empty:
    st.warning("Primero registra al menos una ubicación activa.")
    st.stop()

if proveedores.empty:
    st.warning("Primero registra al menos un proveedor activo en Maestros → Proveedores.")
    st.stop()

product_map = {
    str(row["sku"]).strip().upper(): row
    for _, row in productos.iterrows()
}

location_map = {
    str(row["codigo_ubicacion"]).strip().upper(): row
    for _, row in ubicaciones.iterrows()
}

provider_labels = proveedores.apply(
    lambda r: f"{r['ruc']} | {r['razon_social']}",
    axis=1,
).tolist()


st.markdown(
    """
    <style>
        .migo-box {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1rem;
            background: #fbfbfd;
            margin-bottom: 1rem;
        }
        .migo-section-title {
            font-weight: 700;
            font-size: 1rem;
            color: #111827;
            margin-bottom: .4rem;
        }
        div[data-testid="stDataFrame"] {font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def clean_upper(value) -> str:
    return clean_text(value).upper()


def parse_quantity(value):
    value_text = clean_text(value).replace(",", ".")
    if value_text == "":
        return 0.0
    return float(value_text)


def empty_items(rows: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "codigo_producto": "",
                "nombre_producto": "",
                "unidad_medida": "",
                "cantidad": 0.0,
                "lote": "",
                "codigo_ubicacion_destino": STAGE_LOCATION_CODE if STAGE_LOCATION_CODE in location_map else "",
                "texts": "",
                "requiere_lote": False,
            }
            for _ in range(rows)
        ],
        columns=ITEM_COLUMNS,
    )


def ensure_item_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ITEM_COLUMNS:
        if col not in df.columns:
            if col == "cantidad":
                df[col] = 0.0
            elif col == "requiere_lote":
                df[col] = False
            else:
                df[col] = ""
    return df[ITEM_COLUMNS]


def enrich_items(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_item_columns(df)
    enriched_rows = []

    for _, row in df.iterrows():
        codigo_producto = clean_upper(row.get("codigo_producto"))
        codigo_ubicacion = clean_upper(row.get("codigo_ubicacion_destino"))

        if not codigo_ubicacion:
            codigo_ubicacion = STAGE_LOCATION_CODE if STAGE_LOCATION_CODE in location_map else ""

        product = product_map.get(codigo_producto)

        enriched_rows.append({
            "codigo_producto": codigo_producto,
            "nombre_producto": clean_text(product["nombre_producto"]) if product is not None else "",
            "unidad_medida": clean_text(product["codigo_unidad"]) if product is not None else "",
            "cantidad": row.get("cantidad", 0.0),
            "lote": clean_upper(row.get("lote")),
            "codigo_ubicacion_destino": codigo_ubicacion,
            "texts": clean_text(row.get("texts")),
            "requiere_lote": bool(product["requiere_lote"]) if product is not None else False,
        })

    return pd.DataFrame(enriched_rows, columns=ITEM_COLUMNS)


def df_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    left_cmp = ensure_item_columns(left).fillna("").astype(str)
    right_cmp = ensure_item_columns(right).fillna("").astype(str)
    return left_cmp.equals(right_cmp)


def validate_document(df_items: pd.DataFrame, selected_provider_label: str):
    errors = []
    valid_items = []

    if not selected_provider_label:
        errors.append({
            "fila": "cabecera",
            "campo": "proveedor",
            "error": "Selecciona un proveedor.",
        })

    df_items = enrich_items(df_items)

    for idx, row in df_items.iterrows():
        fila = idx + 1
        codigo_producto = clean_upper(row.get("codigo_producto"))
        cantidad_raw = row.get("cantidad")
        lote = clean_upper(row.get("lote"))
        codigo_ubicacion = clean_upper(row.get("codigo_ubicacion_destino"))
        texto_item = clean_text(row.get("texts"))

        row_has_data = bool(codigo_producto or clean_text(cantidad_raw) not in {"", "0", "0.0"} or lote or texto_item)

        if not row_has_data:
            continue

        product = product_map.get(codigo_producto)
        location = location_map.get(codigo_ubicacion)

        if not codigo_producto:
            errors.append({"fila": fila, "campo": "codigo_producto", "error": "El código de producto es obligatorio."})
            continue

        if product is None:
            errors.append({"fila": fila, "campo": "codigo_producto", "error": "El código de producto no existe o está inactivo."})
            continue

        try:
            cantidad = parse_quantity(cantidad_raw)
        except Exception:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser numérica."})
            continue

        if cantidad <= 0:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser mayor a cero."})
            continue

        if not codigo_ubicacion:
            errors.append({"fila": fila, "campo": "codigo_ubicacion_destino", "error": "La ubicación destino es obligatoria."})
            continue

        if location is None:
            errors.append({"fila": fila, "campo": "codigo_ubicacion_destino", "error": "La ubicación destino no existe o está inactiva."})
            continue

        if bool(product["requiere_lote"]) and not lote:
            errors.append({"fila": fila, "campo": "lote", "error": "El producto requiere lote."})
            continue

        valid_items.append({
            "id_producto": int(product["id_producto"]),
            "sku": codigo_producto,
            "nombre_producto": clean_text(product["nombre_producto"]),
            "codigo_unidad": clean_text(product["codigo_unidad"]),
            "cantidad": cantidad,
            "lote": lote or None,
            "id_ubicacion_destino": int(location["id_ubicacion"]),
            "codigo_ubicacion_destino": codigo_ubicacion,
            "texto_item": texto_item,
        })

    if not valid_items and not errors:
        errors.append({
            "fila": "detalle",
            "campo": "posiciones",
            "error": "Ingresa al menos una posición de material.",
        })

    return errors, valid_items


if "entrada_migo_items" not in st.session_state:
    st.session_state.entrada_migo_items = empty_items()

if "entrada_migo_valid_items" not in st.session_state:
    st.session_state.entrada_migo_valid_items = []

if STAGE_LOCATION_CODE not in location_map:
    st.warning(
        f"No existe la ubicación stage {STAGE_LOCATION_CODE}. "
        "Créala en Maestros → Ubicaciones o ejecuta la migración SQL propuesta."
    )

st.markdown('<div class="migo-box"><div class="migo-section-title">Datos de cabecera</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([2.2, 1, 1.4])

with col1:
    proveedor_label = st.selectbox("Proveedor", provider_labels)

with col2:
    fecha_ingreso = st.date_input("Fecha de ingreso", value=date.today())

with col3:
    documento_referencia = st.text_input("Documento referencia", placeholder="Guía, factura, OC")

texto_cabecera = st.text_area("Texto de cabecera", placeholder="Comentario general del ingreso", height=80)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="migo-box"><div class="migo-section-title">Detalle de posiciones</div>', unsafe_allow_html=True)
st.caption(
    "Edita Código producto, Cantidad, Lote, Ubicación destino y Texts. "
    "Nombre, unidad y requisito de lote se completan automáticamente al reconocer el código."
)

edited_items = st.data_editor(
    st.session_state.entrada_migo_items,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    disabled=["nombre_producto", "unidad_medida", "requiere_lote"],
    column_order=ITEM_COLUMNS,
    column_config={
        "codigo_producto": st.column_config.TextColumn("Código producto", width="medium"),
        "nombre_producto": st.column_config.TextColumn("Nombre producto", width="large"),
        "unidad_medida": st.column_config.TextColumn("UM", width="small"),
        "cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0, format="%.2f"),
        "lote": st.column_config.TextColumn("Lote", width="medium"),
        "codigo_ubicacion_destino": st.column_config.TextColumn("Ubicación destino", width="medium"),
        "texts": st.column_config.TextColumn("Texts", width="large"),
        "requiere_lote": st.column_config.CheckboxColumn("Req. lote", width="small"),
    },
)

enriched_items = enrich_items(edited_items)

if not df_equal(enriched_items, st.session_state.entrada_migo_items):
    st.session_state.entrada_migo_items = enriched_items
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

col_verify, col_post, col_clear = st.columns([1, 1, 1])

verificar = col_verify.button("Verificar", type="secondary", use_container_width=True)
contabilizar = col_post.button("Contabilizar", type="primary", use_container_width=True)
limpiar = col_clear.button("Limpiar", use_container_width=True)

if limpiar:
    st.session_state.entrada_migo_items = empty_items()
    st.session_state.entrada_migo_valid_items = []
    st.rerun()

if verificar or contabilizar:
    errors, valid_items = validate_document(st.session_state.entrada_migo_items, proveedor_label)

    if errors:
        st.error("El documento tiene errores. Corrige las posiciones antes de contabilizar.")
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
        st.session_state.entrada_migo_valid_items = []
    else:
        st.session_state.entrada_migo_valid_items = valid_items
        st.success("Documento verificado correctamente.")
        st.subheader("Vista previa de contabilización")
        st.dataframe(
            pd.DataFrame(valid_items)[[
                "sku",
                "nombre_producto",
                "codigo_unidad",
                "cantidad",
                "lote",
                "codigo_ubicacion_destino",
                "texto_item",
            ]],
            use_container_width=True,
            hide_index=True,
        )

        if contabilizar:
            selected_provider = proveedores.iloc[provider_labels.index(proveedor_label)]

            try:
                id_movimiento = registrar_entrada_migo(
                    id_proveedor=int(selected_provider["id_proveedor"]),
                    fecha_ingreso=fecha_ingreso,
                    documento_referencia=clean_text(documento_referencia),
                    texto_cabecera=clean_text(texto_cabecera),
                    id_usuario=current_user_id(),
                    items=valid_items,
                )
                st.session_state["msg_entrada"] = (
                    f"Documento de entrada contabilizado correctamente. "
                    f"Movimiento: {id_movimiento}. Posiciones: {len(valid_items)}."
                )
                st.session_state.entrada_migo_items = empty_items()
                st.session_state.entrada_migo_valid_items = []
                st.rerun()
            except Exception as exc:
                st.error("No se pudo contabilizar la entrada.")
                st.exception(exc)
