import streamlit as st
from src.session import current_user_id

from src.queries import (
    get_productos_activos,
    get_cuentas,
    get_stock_disponible_por_producto,
)
from src.movimientos import registrar_salida_cuenta

st.title("➖ Salida a cuenta logística")


def normalizar_lote(value):
    if value is None:
        return None
    value_text = str(value).strip()
    if value_text == "" or value_text.lower() == "nan":
        return None
    return value_text


productos = get_productos_activos()
cuentas = get_cuentas()

if productos.empty:
    st.warning("Primero registra al menos un producto activo.")
    st.stop()

if cuentas.empty:
    st.warning("Primero registra al menos una cuenta logística activa.")
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
    st.warning("El producto seleccionado no tiene stock disponible en ubicaciones.")
    st.stop()

stock_disponible["ubicacion_label"] = stock_disponible.apply(
    lambda r: f"{r['codigo_ubicacion']} | Disponible: {r['cantidad_actual']} | Lote: {normalizar_lote(r['lote']) or '-'}",
    axis=1,
)

with st.form("form_salida"):
    ubicacion_label = st.selectbox(
        "Ubicación origen",
        stock_disponible["ubicacion_label"].tolist(),
    )
    cuenta_label = st.selectbox("Cuenta logística", cuentas["nombre_cuenta"].tolist())
    cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0)
    referencia = st.text_input("Referencia").strip()
    observacion = st.text_area("Observación").strip()
    submitted = st.form_submit_button("Registrar salida")

if submitted:
    row_stock = stock_disponible.loc[
        stock_disponible["ubicacion_label"] == ubicacion_label
    ].iloc[0]
    row_cuenta = cuentas.loc[cuentas["nombre_cuenta"] == cuenta_label].iloc[0]

    if cantidad > float(row_stock["cantidad_actual"]):
        st.error("La cantidad solicitada supera el stock disponible de la ubicación.")
        st.stop()

    try:
        registrar_salida_cuenta(
            id_producto=id_producto,
            id_ubicacion_origen=int(row_stock["id_ubicacion"]),
            id_cuenta=int(row_cuenta["id_cuenta"]),
            cantidad=cantidad,
            id_usuario=current_user_id(),
            referencia=referencia,
            observacion=observacion,
            lote=normalizar_lote(row_stock["lote"]),
        )
        st.success("Salida registrada correctamente.")
    except Exception as exc:
        st.error("No se pudo registrar la salida.")
        st.exception(exc)
