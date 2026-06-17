import streamlit as st

from src.queries import (
    get_productos_activos,
    get_ubicaciones,
    get_stock_disponible_por_producto,
)
from src.movimientos import registrar_transferencia

st.title("🔁 Transferencias")


def normalizar_lote(value):
    if value is None:
        return None
    value_text = str(value).strip()
    if value_text == "" or value_text.lower() == "nan":
        return None
    return value_text


productos = get_productos_activos()
ubicaciones = get_ubicaciones()

if productos.empty:
    st.warning("Primero registra al menos un producto activo.")
    st.stop()

if ubicaciones.empty:
    st.warning("Primero registra al menos una ubicación activa.")
    st.stop()

producto_label = st.selectbox("Producto", productos["nombre_producto"].tolist())
id_producto = int(
    productos.loc[
        productos["nombre_producto"] == producto_label,
        "id_producto",
    ].iloc[0]
)

stock_disponible = get_stock_disponible_por_producto(id_producto)

if stock_disponible.empty:
    st.warning("El producto seleccionado no tiene stock disponible para transferir.")
    st.stop()

stock_disponible["origen_label"] = stock_disponible.apply(
    lambda r: f"{r['codigo_ubicacion']} | Disponible: {r['cantidad_actual']} | Lote: {normalizar_lote(r['lote']) or '-'}",
    axis=1,
)

with st.form("form_transferencia"):
    origen_label = st.selectbox("Ubicación origen", stock_disponible["origen_label"].tolist())
    destino_label = st.selectbox("Ubicación destino", ubicaciones["codigo_ubicacion"].tolist())
    cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0)
    referencia = st.text_input("Referencia").strip()
    observacion = st.text_area("Observación").strip()
    submitted = st.form_submit_button("Registrar transferencia")

if submitted:
    row_origen = stock_disponible.loc[
        stock_disponible["origen_label"] == origen_label
    ].iloc[0]
    row_destino = ubicaciones.loc[
        ubicaciones["codigo_ubicacion"] == destino_label
    ].iloc[0]

    if int(row_origen["id_ubicacion"]) == int(row_destino["id_ubicacion"]):
        st.error("La ubicación origen y destino no pueden ser iguales.")
        st.stop()

    if cantidad > float(row_origen["cantidad_actual"]):
        st.error("La cantidad solicitada supera el stock disponible en origen.")
        st.stop()

    try:
        registrar_transferencia(
            id_producto=id_producto,
            id_ubicacion_origen=int(row_origen["id_ubicacion"]),
            id_ubicacion_destino=int(row_destino["id_ubicacion"]),
            cantidad=cantidad,
            id_usuario=1,
            referencia=referencia,
            observacion=observacion,
            lote=normalizar_lote(row_origen["lote"]),
        )
        st.success("Transferencia registrada correctamente.")
    except Exception as exc:
        st.error("No se pudo registrar la transferencia.")
        st.exception(exc)
