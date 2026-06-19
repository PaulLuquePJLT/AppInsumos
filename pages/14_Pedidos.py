from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.movimientos import crear_pedido
from src.queries import get_cuentas, get_next_pedido_number, get_productos_activos, get_pedidos_resumen, get_pedido_detalle
from src.session import current_user_id

ITEM_COLUMNS = [
    "codigo_producto",
    "nombre_producto",
    "unidad_medida",
    "cantidad",
    "texts",
]

st.title("📝 Pedidos")
st.caption("Creación de pedidos de insumos con cabecera y posiciones, similar al flujo de entrada tipo MIGO.")

if "msg_pedido" in st.session_state:
    st.success(st.session_state.pop("msg_pedido"))

productos = get_productos_activos()
cuentas = get_cuentas()

if productos.empty:
    st.warning("Primero registra productos activos.")
    st.stop()

if cuentas.empty:
    st.warning("Primero registra áreas o cuentas logísticas activas.")
    st.stop()

product_map = {str(r["sku"]).strip().upper(): r for _, r in productos.iterrows()}


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


def empty_items(rows: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        [{"codigo_producto": "", "nombre_producto": "", "unidad_medida": "", "cantidad": 0.0, "texts": ""} for _ in range(rows)],
        columns=ITEM_COLUMNS,
    )


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ITEM_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col == "cantidad" else ""
    return df[ITEM_COLUMNS]


def enrich_items(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_columns(df)
    rows = []
    for _, row in df.iterrows():
        codigo = clean_upper(row.get("codigo_producto"))
        product = product_map.get(codigo)
        rows.append({
            "codigo_producto": codigo,
            "nombre_producto": clean_text(product["nombre_producto"]) if product is not None else "",
            "unidad_medida": clean_text(product["codigo_unidad"]) if product is not None else "",
            "cantidad": row.get("cantidad", 0.0),
            "texts": clean_text(row.get("texts")),
        })
    return pd.DataFrame(rows, columns=ITEM_COLUMNS)


def validate_items(df: pd.DataFrame):
    errors = []
    valid = []
    df = enrich_items(df)

    for idx, row in df.iterrows():
        fila = idx + 1
        codigo = clean_upper(row.get("codigo_producto"))
        qty_raw = row.get("cantidad")
        texto = clean_text(row.get("texts"))

        row_has_data = bool(codigo or clean_text(qty_raw) not in {"", "0", "0.0"} or texto)
        if not row_has_data:
            continue

        product = product_map.get(codigo)
        if not codigo:
            errors.append({"fila": fila, "campo": "codigo_producto", "error": "El código de producto es obligatorio."})
            continue
        if product is None:
            errors.append({"fila": fila, "campo": "codigo_producto", "error": "El código no existe o está inactivo."})
            continue
        try:
            qty = parse_qty(qty_raw)
        except Exception:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser numérica."})
            continue
        if qty <= 0:
            errors.append({"fila": fila, "campo": "cantidad", "error": "La cantidad debe ser mayor a cero."})
            continue

        valid.append({
            "id_producto": int(product["id_producto"]),
            "sku": codigo,
            "nombre_producto": clean_text(product["nombre_producto"]),
            "codigo_unidad": clean_text(product["codigo_unidad"]),
            "cantidad": qty,
            "texto_item": texto,
        })

    if not valid and not errors:
        errors.append({"fila": "detalle", "campo": "posiciones", "error": "Ingresa al menos una posición."})

    return errors, valid


if "pedido_items" not in st.session_state:
    st.session_state.pedido_items = empty_items()
if "pedido_verified_items" not in st.session_state:
    st.session_state.pedido_verified_items = []
if "pedido_nro" not in st.session_state:
    try:
        st.session_state.pedido_nro = get_next_pedido_number()
    except Exception:
        st.session_state.pedido_nro = "P000000001"


def limpiar_pedido():
    st.session_state.pedido_items = empty_items()
    st.session_state.pedido_verified_items = []
    try:
        st.session_state.pedido_nro = get_next_pedido_number()
    except Exception:
        st.session_state.pedido_nro = "P000000001"


tab_crear, tab_visualizar = st.tabs(["Crear Pedido", "Visualizar pedidos"])

with tab_crear:
    st.subheader("Datos de cabecera")
    cuenta_labels = cuentas.apply(lambda r: f"{r['codigo_cuenta']} | {r['nombre_cuenta']}", axis=1).tolist()
    col1, col2, col3 = st.columns([1.2, 2, 1.2])
    with col1:
        nro_pedido = st.text_input("Nro pedido", value=st.session_state.pedido_nro, disabled=True)
    with col2:
        cuenta_label = st.selectbox("Cuenta solicitante", cuenta_labels)
    with col3:
        fecha_pedido = st.date_input("Fecha de pedido", value=date.today())

    selected_cuenta = cuentas.iloc[cuenta_labels.index(cuenta_label)]
    default_responsable = clean_text(selected_cuenta.get("responsable"))

    col4, col5 = st.columns([1.5, 2])
    with col4:
        fecha_esperada = st.date_input("Fecha esperada de atención", value=date.today() + timedelta(days=1))
    with col5:
        solicitante = st.text_input("Solicitante", value=default_responsable)

    texto_cabecera = st.text_area("Texto de cabecera", placeholder="Referencia del pedido, observaciones, campaña, urgencia, etc.")

    st.subheader("Datos de contenido")
    st.info("Completa el código de producto y la cantidad. El nombre y la unidad se completan automáticamente.")

    edited = st.data_editor(
        enrich_items(st.session_state.pedido_items),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=["nombre_producto", "unidad_medida"],
        column_config={
            "codigo_producto": st.column_config.TextColumn("Código producto", help="SKU del producto"),
            "nombre_producto": st.column_config.TextColumn("Nombre producto"),
            "unidad_medida": st.column_config.TextColumn("UM"),
            "cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
            "texts": st.column_config.TextColumn("Texts", help="Texto referencial por código", width="large"),
        },
        key="pedido_editor",
    )
    st.session_state.pedido_items = enrich_items(edited)

    colv, colc, coll = st.columns([1, 1, 1])
    verificar = colv.button("Verificar", type="secondary", use_container_width=True)
    crear = colc.button("Crear Pedido", type="primary", use_container_width=True)
    limpiar = coll.button("Limpiar", use_container_width=True)

    if limpiar:
        limpiar_pedido()
        st.rerun()

    if verificar or crear:
        errors, valid_items = validate_items(st.session_state.pedido_items)
        if not cuenta_label:
            errors.append({"fila": "cabecera", "campo": "cuenta", "error": "Selecciona una cuenta solicitante."})
        if not solicitante.strip():
            errors.append({"fila": "cabecera", "campo": "solicitante", "error": "Completa el solicitante."})

        if errors:
            st.error("Existen errores en el pedido.")
            st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
            st.session_state.pedido_verified_items = []
        else:
            preview = pd.DataFrame(valid_items)[["sku", "nombre_producto", "codigo_unidad", "cantidad", "texto_item"]]
            st.success("Pedido verificado correctamente.")
            st.dataframe(preview, use_container_width=True, hide_index=True)
            st.session_state.pedido_verified_items = valid_items

            if crear:
                try:
                    nro_creado = crear_pedido(
                        nro_pedido=st.session_state.pedido_nro,
                        fecha_pedido=fecha_pedido,
                        fecha_esperada_atencion=fecha_esperada,
                        id_cuenta=int(selected_cuenta["id_cuenta"]),
                        solicitante=solicitante,
                        responsable_cuenta=default_responsable,
                        texto_cabecera=texto_cabecera,
                        id_usuario=current_user_id(),
                        items=valid_items,
                    )
                    limpiar_pedido()
                    st.session_state["msg_pedido"] = f"Pedido {nro_creado} creado correctamente."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo crear el pedido.")
                    st.exception(exc)

with tab_visualizar:
    colf1, colf2 = st.columns(2)
    with colf1:
        solo_hoy = st.checkbox("Solo pedidos de hoy", value=False)
    with colf2:
        solo_creados = st.checkbox("Solo pedidos en estado CREADO", value=False)

    try:
        pedidos = get_pedidos_resumen(solo_hoy=solo_hoy, solo_creados=solo_creados)
    except Exception as exc:
        st.error("No se pudo cargar pedidos. Ejecuta la migración 008 en Azure SQL.")
        st.exception(exc)
        st.stop()

    if pedidos.empty:
        st.info("No hay pedidos para mostrar.")
    else:
        labels = pedidos.apply(lambda r: f"{r['nro_pedido']} | {r['nombre_cuenta']} | {r['estado']}", axis=1).tolist()
        selected_label = st.selectbox("Ver detalle de pedido", labels)
        selected = pedidos.iloc[labels.index(selected_label)]
        st.dataframe(pedidos, use_container_width=True, hide_index=True)
        st.subheader(f"Detalle {selected['nro_pedido']}")
        st.dataframe(get_pedido_detalle(int(selected["id_pedido"])), use_container_width=True, hide_index=True)
