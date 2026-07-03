import streamlit as st

from src.movimientos import aprobar_pickings_rf, atender_tareas_picking
from src.queries import get_pickings_rf_pendientes_aprobacion, get_tareas_picking_pendientes
from src.session import current_user_id

st.title("✅ Atención de Picking")
st.caption("Atención desktop de tareas liberadas y aprobación de pickings completados por RF.")

if "msg_atencion_picking" in st.session_state:
    st.success(st.session_state.pop("msg_atencion_picking"))

tab_tareas, tab_aprobacion_rf = st.tabs(["Atención desktop", "Aprobación RF"])

with tab_tareas:
    try:
        tareas = get_tareas_picking_pendientes()
    except Exception as exc:
        st.error("No se pudo cargar tareas pendientes de picking. Ejecuta la migración 008 en Azure SQL.")
        st.exception(exc)
        st.stop()

    if tareas.empty:
        st.success("No hay tareas pendientes de picking desktop.")
    else:
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
        colb3.caption("Atención desktop: descuenta stock, libera picking y carga stock a la cuenta logística inmediatamente.")

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

with tab_aprobacion_rf:
    st.markdown("### Pickings completados por RF pendientes de aprobación")
    st.caption(
        "Al aprobar, el sistema confirma los movimientos SALIDA_CUENTA generados por RF y recién carga el stock a la cuenta logística."
    )

    try:
        pendientes = get_pickings_rf_pendientes_aprobacion()
    except Exception as exc:
        st.error("No se pudo cargar pickings RF pendientes. Ejecuta la migración 017 en Azure SQL.")
        st.exception(exc)
        st.stop()

    if pendientes.empty:
        st.success("No hay pickings RF pendientes de aprobación.")
    else:
        colf1, colf2 = st.columns(2)
        with colf1:
            filtro_pk_rf = st.text_input("Filtrar PK", key="rf_aprob_filtro_pk")
        with colf2:
            filtro_cuenta_rf = st.text_input("Filtrar cuenta", key="rf_aprob_filtro_cuenta")

        filtered_rf = pendientes.copy()
        if filtro_pk_rf.strip():
            v = filtro_pk_rf.strip().lower()
            filtered_rf = filtered_rf[filtered_rf["nro_picking"].astype(str).str.lower().str.contains(v, na=False)]
        if filtro_cuenta_rf.strip():
            v = filtro_cuenta_rf.strip().lower()
            filtered_rf = filtered_rf[
                filtered_rf["codigo_cuenta"].astype(str).str.lower().str.contains(v, na=False)
                | filtered_rf["nombre_cuenta"].astype(str).str.lower().str.contains(v, na=False)
            ]

        m1, m2, m3 = st.columns(3)
        m1.metric("Pickings RF", filtered_rf["id_picking"].nunique())
        m2.metric("Cantidad pendiente aprobar", f"{filtered_rf['cantidad_atendida'].sum():,.2f}")
        m3.metric("Tareas completadas", int(filtered_rf["tareas_completadas"].sum()))

        edited_rf = st.data_editor(
            filtered_rf,
            use_container_width=True,
            hide_index=True,
            disabled=[c for c in filtered_rf.columns if c != "seleccionar"],
            column_config={"seleccionar": st.column_config.CheckboxColumn("Seleccionar")},
            key="rf_aprobacion_editor",
        )

        selected_rf = edited_rf.loc[edited_rf["seleccionar"] == True, "id_picking"].astype(int).tolist()
        col1, col2 = st.columns([1, 2])
        aprobar = col1.button("Aprobar seleccionados", type="primary", use_container_width=True)
        col2.caption("Solo se aprueban pickings RF completados y con estado de aprobación PENDIENTE.")

        if aprobar:
            if not selected_rf:
                st.error("Selecciona al menos un picking RF para aprobar.")
            else:
                try:
                    result = aprobar_pickings_rf(selected_rf, current_user_id())
                    st.session_state["msg_atencion_picking"] = (
                        f"Pickings aprobados: {result['pickings_aprobados']}. "
                        f"Movimientos confirmados: {result['movimientos_aprobados']}. "
                        f"Cantidad aprobada: {result['qty_aprobada']:,.2f}."
                    )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("No se pudo aprobar el picking RF.")
                    st.exception(exc)
