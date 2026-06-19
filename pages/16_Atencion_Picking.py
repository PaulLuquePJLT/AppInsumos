import streamlit as st

from src.movimientos import atender_tareas_picking
from src.queries import get_tareas_picking_pendientes
from src.session import current_user_id

st.title("✅ Atención de Picking")
st.caption("Atención desktop de tareas liberadas. Más adelante este flujo puede ser atendido por RF/Zebra.")

if "msg_atencion_picking" in st.session_state:
    st.success(st.session_state.pop("msg_atencion_picking"))

try:
    tareas = get_tareas_picking_pendientes()
except Exception as exc:
    st.error("No se pudo cargar tareas pendientes de picking. Ejecuta la migración 008 en Azure SQL.")
    st.exception(exc)
    st.stop()

if tareas.empty:
    st.success("No hay tareas pendientes de picking.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    filtro_pk = st.text_input("Filtrar PK")
with col2:
    filtro_pedido = st.text_input("Filtrar pedido")
with col3:
    filtro_cuenta = st.text_input("Filtrar cuenta solicitante")

filtered = tareas.copy()
if filtro_pk.strip():
    v = filtro_pk.strip().lower()
    filtered = filtered[filtered["nro_picking"].astype(str).str.lower().str.contains(v, na=False)]
if filtro_pedido.strip():
    v = filtro_pedido.strip().lower()
    filtered = filtered[filtered["nro_pedido"].astype(str).str.lower().str.contains(v, na=False)]
if filtro_cuenta.strip():
    v = filtro_cuenta.strip().lower()
    filtered = filtered[
        filtered["codigo_cuenta"].astype(str).str.lower().str.contains(v, na=False)
        | filtered["nombre_cuenta"].astype(str).str.lower().str.contains(v, na=False)
    ]

m1, m2, m3 = st.columns(3)
m1.metric("Tareas visibles", len(filtered))
m2.metric("Unidades a atender", f"{filtered['cantidad_asignada'].sum():,.2f}")
m3.metric("Pickings visibles", filtered["nro_picking"].nunique())

st.subheader("Tareas pendientes")

edited = st.data_editor(
    filtered,
    use_container_width=True,
    hide_index=True,
    disabled=[c for c in filtered.columns if c != "seleccionar"],
    column_config={"seleccionar": st.column_config.CheckboxColumn("Seleccionar")},
    key="atencion_picking_editor",
)

selected_ids = edited.loc[edited["seleccionar"] == True, "id_picking_detalle"].astype(int).tolist()
all_filtered_ids = filtered["id_picking_detalle"].astype(int).tolist()

observacion = st.text_area("Observación de atención", placeholder="Opcional")

colb1, colb2, colb3 = st.columns([1, 1, 2])
atender_sel = colb1.button("Atender tareas seleccionadas", type="primary", use_container_width=True)
atender_todo = colb2.button("Atender todas las filtradas", use_container_width=True)
colb3.caption("Las tareas atendidas descuentan stock, liberan cantidad en picking y cargan stock a la cuenta logística.")

if atender_sel:
    if not selected_ids:
        st.error("Selecciona al menos una tarea.")
    else:
        try:
            result = atender_tareas_picking(selected_ids, current_user_id(), observacion)
            st.session_state["msg_atencion_picking"] = (
                f"Tareas atendidas: {result['tareas_atendidas']}. "
                f"Cantidad atendida: {result['qty_atendida']:,.2f}."
            )
            st.rerun()
        except Exception as exc:
            st.error("No se pudieron atender las tareas seleccionadas.")
            st.exception(exc)

if atender_todo:
    try:
        result = atender_tareas_picking(all_filtered_ids, current_user_id(), observacion)
        st.session_state["msg_atencion_picking"] = (
            f"Tareas atendidas: {result['tareas_atendidas']}. "
            f"Cantidad atendida: {result['qty_atendida']:,.2f}."
        )
        st.rerun()
    except Exception as exc:
        st.error("No se pudieron atender las tareas filtradas.")
        st.exception(exc)
