from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.editor_utils import apply_data_editor_state
from src.movimientos import registrar_entrada_migo
from src.queries import get_productos_activos, get_proveedores, get_ubicaciones
from src.session import current_user_id

LOCAL_TZ = ZoneInfo("America/Lima")
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

DISPLAY_COLUMNS = [
    "codigo_producto",
    "cantidad",
    "lote",
    "codigo_ubicacion_destino",
    "texts",
    "nombre_producto",
    "unidad_medida",
    "requiere_lote",
]

EDITOR_BASE_KEY = "entrada_migo_editor"

st.markdown('<div class="wms-page-kicker">Ingresos</div>', unsafe_allow_html=True)
st.title("➕ Entrada de mercancías")
st.markdown(
    '<div class="wms-soft-banner">Flujo tipo MIGO: cabecera, posiciones, verificación y contabilización en una sola transacción.</div>',
    unsafe_allow_html=True,
)

if "msg_entrada" in st.session_state:
    st.success(st.session_state.pop("msg_entrada"))


@st.cache_data(ttl=120, show_spinner=False)
def load_entrada_reference_data():
    return get_productos_activos(), get_ubicaciones(), get_proveedores()


productos, ubicaciones, proveedores = load_entrada_reference_data()

if productos.empty:
    st.warning("Primero registra al menos un producto activo.")
    st.stop()

if ubicaciones.empty:
    st.warning("Primero registra al menos una ubicación activa.")
    st.stop()

if proveedores.empty:
    st.warning("Primero registra al menos un proveedor activo en Maestros → Proveedores.")
    st.stop()

product_map = {str(row["sku"]).strip().upper(): row for _, row in productos.iterrows()}
location_map = {str(row["codigo_ubicacion"]).strip().upper(): row for _, row in ubicaciones.iterrows()}
provider_labels = proveedores.apply(lambda r: f"{r['ruc']} | {r['razon_social']}", axis=1).tolist()

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


def now_local():
    return datetime.now(LOCAL_TZ).replace(microsecond=0)


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


def default_row() -> dict:
    return {
        "codigo_producto": "",
        "nombre_producto": "",
        "unidad_medida": "",
        "cantidad": "",
        "lote": "",
        "codigo_ubicacion_destino": STAGE_LOCATION_CODE if STAGE_LOCATION_CODE in location_map else "",
        "texts": "",
        "requiere_lote": False,
    }


def empty_items(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame([default_row() for _ in range(rows)], columns=ITEM_COLUMNS)


def ensure_item_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ITEM_COLUMNS:
        if col not in df.columns:
            df[col] = default_row().get(col, "")
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
            "cantidad": clean_text(row.get("cantidad")),
            "lote": clean_upper(row.get("lote")),
            "codigo_ubicacion_destino": codigo_ubicacion,
            "texts": clean_text(row.get("texts")),
            "requiere_lote": bool(product["requiere_lote"]) if product is not None else False,
        })

    return pd.DataFrame(enriched_rows, columns=ITEM_COLUMNS)


def on_entrada_editor_change(editor_key: str):
    editor_state = st.session_state.get(editor_key, {})
    current = st.session_state.get("entrada_migo_items", empty_items())
    merged = apply_data_editor_state(current, editor_state, ITEM_COLUMNS, default_row)
    st.session_state.entrada_migo_items = enrich_items(merged)


def validate_document(df_items: pd.DataFrame, selected_provider_label: str):
    errors = []
    valid_items = []

    if not selected_provider_label:
        errors.append({"fila": "cabecera", "campo": "proveedor", "error": "Selecciona un proveedor."})

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
        errors.append({"fila": "detalle", "campo": "posiciones", "error": "Ingresa al menos una posición de material."})

    return errors, valid_items


if "entrada_migo_items" not in st.session_state:
    st.session_state.entrada_migo_items = empty_items()
if "entrada_migo_valid_items" not in st.session_state:
    st.session_state.entrada_migo_valid_items = []
if "entrada_migo_editor_version" not in st.session_state:
    st.session_state.entrada_migo_editor_version = 0

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
    fecha_ingreso = st.date_input("Fecha de ingreso", value=now_local().date())
with col3:
    documento_referencia = st.text_input("Documento referencia", placeholder="Guía, factura, OC")

texto_cabecera = st.text_area("Texto de cabecera", placeholder="Comentario general del ingreso", height=80)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="migo-box"><div class="migo-section-title">Detalle de posiciones</div>', unsafe_allow_html=True)
st.caption(
    "Pega desde Excel en bloques. Recomendado: SKU | Cantidad | Lote | Ubicación destino | Texto. "
    "Nombre, unidad y requisito de lote se completan al reconocer el código."
)

editor_key = f"{EDITOR_BASE_KEY}_{st.session_state.entrada_migo_editor_version}"
st.session_state.entrada_migo_items = enrich_items(st.session_state.entrada_migo_items)

st.data_editor(
    st.session_state.entrada_migo_items,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    disabled=["nombre_producto", "unidad_medida", "requiere_lote"],
    column_order=DISPLAY_COLUMNS,
    column_config={
        "codigo_producto": st.column_config.TextColumn("Código producto", width="medium"),
        "cantidad": st.column_config.TextColumn("Cantidad", width="small", help="Puedes pegar cantidades desde Excel; se validan al verificar."),
        "lote": st.column_config.TextColumn("Lote", width="medium"),
        "codigo_ubicacion_destino": st.column_config.TextColumn("Ubicación destino", width="medium"),
        "texts": st.column_config.TextColumn("Texts", width="large"),
        "nombre_producto": st.column_config.TextColumn("Nombre producto", width="large"),
        "unidad_medida": st.column_config.TextColumn("UM", width="small"),
        "requiere_lote": st.column_config.CheckboxColumn("Req. lote", width="small"),
    },
    key=editor_key,
    on_change=on_entrada_editor_change,
    args=(editor_key,),
)
st.markdown('</div>', unsafe_allow_html=True)

col_verify, col_post, col_clear = st.columns([1, 1, 1])
verificar = col_verify.button("Verificar", type="secondary", use_container_width=True)
contabilizar = col_post.button("Contabilizar", type="primary", use_container_width=True)
limpiar = col_clear.button("Limpiar", use_container_width=True)

if limpiar:
    st.session_state.entrada_migo_items = empty_items()
    st.session_state.entrada_migo_valid_items = []
    st.session_state.entrada_migo_editor_version += 1
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
                "sku", "nombre_producto", "codigo_unidad", "cantidad", "lote", "codigo_ubicacion_destino", "texto_item",
            ]],
            use_container_width=True,
            hide_index=True,
        )

        if contabilizar:
            selected_provider = proveedores.iloc[provider_labels.index(proveedor_label)]
            try:
                id_movimiento = registrar_entrada_migo(
                    id_proveedor=int(selected_provider["id_proveedor"]),
                    fecha_ingreso=now_local(),
                    documento_referencia=clean_text(documento_referencia),
                    texto_cabecera=clean_text(texto_cabecera),
                    id_usuario=current_user_id(),
                    items=valid_items,
                )
                st.session_state["msg_entrada"] = (
                    f"Documento de entrada contabilizado correctamente. Movimiento: {id_movimiento}. Posiciones: {len(valid_items)}."
                )
                st.session_state.entrada_migo_items = empty_items()
                st.session_state.entrada_migo_valid_items = []
                load_entrada_reference_data.clear()
                st.session_state.entrada_migo_editor_version += 1
                st.rerun()
            except Exception as exc:
                st.error("No se pudo contabilizar la entrada.")
                st.exception(exc)
