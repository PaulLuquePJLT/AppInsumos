from datetime import datetime
from src.time_utils import local_now

import pandas as pd
import streamlit as st

from src.editor_utils import apply_data_editor_state
from src.movimientos import registrar_transferencia_masiva
from src.queries import get_productos_activos, get_stock_para_transferencia, get_ubicaciones
from src.session import current_user_id

ITEM_COLUMNS = [
    "codigo_producto",
    "nombre_producto",
    "unidad_medida",
    "lote",
    "codigo_ubicacion_origen",
    "stock_disponible",
    "cantidad",
    "codigo_ubicacion_destino",
    "texts",
]

DISPLAY_COLUMNS = [
    "codigo_producto",
    "lote",
    "codigo_ubicacion_origen",
    "cantidad",
    "codigo_ubicacion_destino",
    "texts",
    "nombre_producto",
    "unidad_medida",
    "stock_disponible",
]

EDITOR_BASE_KEY = "transfer_editor"

st.markdown('<div class="wms-page-kicker">Consultas / Operación</div>', unsafe_allow_html=True)
st.title("🔁 Transferencias / Cambio de ubicación")
st.markdown(
    '<div class="wms-soft-banner">Transferencia masiva con cabecera, tabla editable, verificación y confirmación.</div>',
    unsafe_allow_html=True,
)

if "msg_transferencia" in st.session_state:
    st.success(st.session_state.pop("msg_transferencia"))


@st.cache_data(ttl=90, show_spinner=False)
def load_transfer_reference_data():
    return get_productos_activos(), get_ubicaciones(), get_stock_para_transferencia()


productos, ubicaciones, stock = load_transfer_reference_data()

if productos.empty:
    st.warning("Primero registra productos activos.")
    st.stop()
if ubicaciones.empty:
    st.warning("Primero registra ubicaciones activas.")
    st.stop()
if stock.empty:
    st.warning("No hay stock disponible para transferir.")
    st.stop()

product_map = {str(r["sku"]).strip().upper(): r for _, r in productos.iterrows()}
location_map = {str(r["codigo_ubicacion"]).strip().upper(): r for _, r in ubicaciones.iterrows()}


def clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def clean_upper(value) -> str:
    return clean_text(value).upper()


def parse_qty(value) -> float:
    value_text = clean_text(value).replace(",", ".")
    if value_text == "":
        return 0.0
    return float(value_text)


def normalizar_lote(value):
    text = clean_text(value)
    return text if text else None


def default_row() -> dict:
    return {
        "codigo_producto": "",
        "nombre_producto": "",
        "unidad_medida": "",
        "lote": "",
        "codigo_ubicacion_origen": "",
        "stock_disponible": "",
        "cantidad": "",
        "codigo_ubicacion_destino": "",
        "texts": "",
    }


def empty_items(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame([default_row() for _ in range(rows)], columns=ITEM_COLUMNS)


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ITEM_COLUMNS:
        if col not in df.columns:
            df[col] = default_row().get(col, "")
    return df[ITEM_COLUMNS]


def get_available(codigo_producto: str, codigo_ubicacion: str, lote):
    codigo_producto = clean_upper(codigo_producto)
    codigo_ubicacion = clean_upper(codigo_ubicacion)
    lote_key = normalizar_lote(lote) or ""
    if not codigo_producto or not codigo_ubicacion:
        return 0.0
    rows = stock[
        (stock["sku"].astype(str).str.upper() == codigo_producto)
        & (stock["codigo_ubicacion"].astype(str).str.upper() == codigo_ubicacion)
    ].copy()
    if rows.empty:
        return 0.0
    if lote_key:
        rows = rows[rows["lote"].fillna("").astype(str) == lote_key]
    elif rows["lote"].fillna("").astype(str).nunique() > 1:
        return 0.0
    return float(rows["cantidad_disponible"].sum())


def enrich_items(df: pd.DataFrame, recalc_stock: bool = False) -> pd.DataFrame:
    df = ensure_columns(df)
    rows = []
    for _, row in df.iterrows():
        codigo = clean_upper(row.get("codigo_producto"))
        origen = clean_upper(row.get("codigo_ubicacion_origen"))
        destino = clean_upper(row.get("codigo_ubicacion_destino"))
        lote = clean_upper(row.get("lote"))
        product = product_map.get(codigo)
        stock_disponible = get_available(codigo, origen, lote) if recalc_stock else row.get("stock_disponible", "")
        rows.append({
            "codigo_producto": codigo,
            "nombre_producto": clean_text(product["nombre_producto"]) if product is not None else "",
            "unidad_medida": clean_text(product["codigo_unidad"]) if product is not None else "",
            "lote": lote,
            "codigo_ubicacion_origen": origen,
            "stock_disponible": stock_disponible,
            "cantidad": clean_text(row.get("cantidad")),
            "codigo_ubicacion_destino": destino,
            "texts": clean_text(row.get("texts")),
        })
    return pd.DataFrame(rows, columns=ITEM_COLUMNS)


def on_transfer_editor_change(editor_key: str):
    editor_state = st.session_state.get(editor_key, {})
    current = st.session_state.get("transfer_items", empty_items())
    merged = apply_data_editor_state(current, editor_state, ITEM_COLUMNS, default_row)
    st.session_state.transfer_items = enrich_items(merged, recalc_stock=False)


def validate_items(df: pd.DataFrame):
    errors = []
    valid = []
    df = enrich_items(df, recalc_stock=True)
    st.session_state.transfer_items = df

    for idx, row in df.iterrows():
        fila = idx + 1
        codigo = clean_upper(row.get("codigo_producto"))
        origen = clean_upper(row.get("codigo_ubicacion_origen"))
        destino = clean_upper(row.get("codigo_ubicacion_destino"))
        lote = normalizar_lote(row.get("lote"))
        texto = clean_text(row.get("texts"))
        qty_raw = row.get("cantidad")

        row_has_data = bool(codigo or origen or destino or lote or texto or clean_text(qty_raw) not in {"", "0", "0.0"})
        if not row_has_data:
            continue

        product = product_map.get(codigo)
        origin = location_map.get(origen)
        dest = location_map.get(destino)

        if product is None:
            errors.append({"fila": fila, "campo": "codigo_producto", "error": "El producto no existe o está inactivo."})
            continue
        if origin is None:
            errors.append({"fila": fila, "campo": "codigo_ubicacion_origen", "error": "La ubicación origen no existe o está inactiva."})
            continue
        if dest is None:
            errors.append({"fila": fila, "campo": "codigo_ubicacion_destino", "error": "La ubicación destino no existe o está inactiva."})
            continue
        if int(origin["id_ubicacion"]) == int(dest["id_ubicacion"]):
            errors.append({"fila": fila, "campo": "ubicaciones", "error": "Origen y destino no pueden ser iguales."})
            continue
        try:
            qty = parse_qty(qty_raw)
        except Exception:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser numérica."})
            continue
        if qty <= 0:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser mayor a cero."})
            continue

        rows_stock = stock[
            (stock["id_producto"].astype(int) == int(product["id_producto"]))
            & (stock["id_ubicacion"].astype(int) == int(origin["id_ubicacion"]))
        ].copy()
        if rows_stock.empty:
            errors.append({"fila": fila, "campo": "stock", "error": "No hay stock del producto en la ubicación origen."})
            continue
        if lote:
            rows_stock = rows_stock[rows_stock["lote"].fillna("").astype(str) == lote]
        elif rows_stock["lote"].fillna("").astype(str).nunique() > 1:
            errors.append({"fila": fila, "campo": "lote", "error": "El producto tiene más de un lote en origen. Indica lote."})
            continue

        disponible = float(rows_stock["cantidad_disponible"].sum()) if not rows_stock.empty else 0.0
        if disponible < qty:
            errors.append({"fila": fila, "campo": "cantidad", "error": f"Stock disponible insuficiente. Disponible: {disponible:,.2f}."})
            continue

        valid.append({
            "id_producto": int(product["id_producto"]),
            "sku": codigo,
            "nombre_producto": clean_text(product["nombre_producto"]),
            "codigo_unidad": clean_text(product["codigo_unidad"]),
            "id_ubicacion_origen": int(origin["id_ubicacion"]),
            "codigo_ubicacion_origen": origen,
            "id_ubicacion_destino": int(dest["id_ubicacion"]),
            "codigo_ubicacion_destino": destino,
            "lote": lote,
            "cantidad": qty,
            "texto_item": texto,
        })

    if not valid and not errors:
        errors.append({"fila": "detalle", "campo": "posiciones", "error": "Ingresa al menos una posición."})

    return errors, valid


if "transfer_items" not in st.session_state:
    st.session_state.transfer_items = empty_items()
if "transfer_valid_items" not in st.session_state:
    st.session_state.transfer_valid_items = []
if "transfer_editor_version" not in st.session_state:
    st.session_state.transfer_editor_version = 0


def limpiar_transferencia():
    st.session_state.transfer_items = empty_items()
    st.session_state.transfer_valid_items = []
    st.session_state.transfer_editor_version += 1


st.subheader("Datos de cabecera")
col1, col2 = st.columns([1, 3])
with col1:
    fecha_movimiento = st.text_input("Fecha movimiento", value=local_now().strftime("%Y-%m-%d %H:%M:%S"), disabled=True)
with col2:
    texto_cabecera = st.text_input("Texto de cabecera", placeholder="Opcional")

st.subheader("Datos de contenido")
st.info("Pega desde Excel en bloques. Recomendado: SKU | Lote | Origen | Cantidad | Destino | Texto.")

editor_key = f"{EDITOR_BASE_KEY}_{st.session_state.transfer_editor_version}"
st.session_state.transfer_items = enrich_items(st.session_state.transfer_items, recalc_stock=False)

st.data_editor(
    st.session_state.transfer_items,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    disabled=["nombre_producto", "unidad_medida", "stock_disponible"],
    column_order=DISPLAY_COLUMNS,
    column_config={
        "codigo_producto": st.column_config.TextColumn("Código producto"),
        "lote": st.column_config.TextColumn("Lote"),
        "codigo_ubicacion_origen": st.column_config.TextColumn("Ubicación actual"),
        "cantidad": st.column_config.TextColumn("Cantidad", help="Puedes pegar cantidades desde Excel; se validan al verificar."),
        "codigo_ubicacion_destino": st.column_config.TextColumn("Ubicación destino"),
        "texts": st.column_config.TextColumn("Texto referencia", width="large"),
        "nombre_producto": st.column_config.TextColumn("Nombre producto"),
        "unidad_medida": st.column_config.TextColumn("UM"),
        "stock_disponible": st.column_config.TextColumn("Stock disponible"),
    },
    key=editor_key,
    on_change=on_transfer_editor_change,
    args=(editor_key,),
)

colv, colc, coll = st.columns([1, 1, 1])
verificar = colv.button("Verificar", type="secondary", use_container_width=True)
confirmar = colc.button("Confirmar transferencia", type="primary", use_container_width=True)
limpiar = coll.button("Limpiar", use_container_width=True)

if limpiar:
    limpiar_transferencia()
    st.rerun()

if verificar or confirmar:
    errors, valid = validate_items(st.session_state.transfer_items)
    if errors:
        st.error("Existen errores en la transferencia.")
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
        st.session_state.transfer_valid_items = []
    else:
        preview = pd.DataFrame(valid)[[
            "sku", "nombre_producto", "codigo_unidad", "codigo_ubicacion_origen", "codigo_ubicacion_destino", "lote", "cantidad", "texto_item",
        ]]
        st.success("Transferencia verificada correctamente.")
        st.dataframe(preview, use_container_width=True, hide_index=True)
        st.session_state.transfer_valid_items = valid

        if confirmar:
            try:
                id_movimiento = registrar_transferencia_masiva(
                    fecha_movimiento=local_now(),
                    texto_cabecera=texto_cabecera,
                    id_usuario=current_user_id(),
                    items=valid,
                )
                limpiar_transferencia()
                load_transfer_reference_data.clear()
                st.session_state["msg_transferencia"] = f"Transferencia contabilizada. Movimiento {id_movimiento}."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo confirmar la transferencia.")
                st.exception(exc)
