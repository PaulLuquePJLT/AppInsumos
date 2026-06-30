
import pandas as pd
import streamlit as st

from src.movimientos import (
    cancelar_cortos_picking,
    cancelar_picking,
    crear_picking_desde_pedidos,
    eliminar_pedidos,
    reasignar_cortos_picking,
)
from src.queries import (
    get_pedidos_pendientes_detalle,
    get_pedidos_resumen,
    get_picking_cortos,
    get_picking_detalle,
    get_pickings_resumen,
)
from src.session import current_user_id
from src.time_utils import local_today

st.title("📋 Picking")
st.caption("Creación, visualización, eliminación y gestión de cortos de picking.")

if "msg_picking" in st.session_state:
    st.success(st.session_state.pop("msg_picking"))


def summarize_units(df: pd.DataFrame) -> str:
    if df.empty or "codigo_unidad" not in df.columns:
        return "0"
    summary = df.groupby("codigo_unidad")["cantidad_pendiente_picking"].sum().reset_index()
    return " | ".join(f"{r['codigo_unidad']}: {r['cantidad_pendiente_picking']:,.2f}" for _, r in summary.iterrows())


def selectable_table(df: pd.DataFrame, key: str):
    if df.empty:
        return df
    display = df.copy()
    if "seleccionar" not in display.columns:
        display.insert(0, "seleccionar", False)
    return st.data_editor(
        display,
        hide_index=True,
        use_container_width=True,
        disabled=[c for c in display.columns if c != "seleccionar"],
        column_config={"seleccionar": st.column_config.CheckboxColumn("Seleccionar")},
        key=key,
    )


tab_crear, tab_visualizar, tab_cortos = st.tabs(["Crear Picking", "Visualizar / eliminar", "Cortos"])

with tab_crear:
    if "pick_pend_solo_hoy" not in st.session_state:
        st.session_state.pick_pend_solo_hoy = True
    if "pick_pend_fecha_inicio" not in st.session_state:
        st.session_state.pick_pend_fecha_inicio = local_today()
    if "pick_pend_fecha_fin" not in st.session_state:
        st.session_state.pick_pend_fecha_fin = local_today()

    with st.form("form_filtros_pedidos_picking"):
        col0, col1, col2, col3, col4 = st.columns([1.2, 1, 1, 2, .85])
        with col0:
            solo_hoy = st.checkbox("Pedidos de hoy", value=st.session_state.pick_pend_solo_hoy)
        with col1:
            fecha_inicio = st.date_input("Desde", value=st.session_state.pick_pend_fecha_inicio, disabled=solo_hoy)
        with col2:
            fecha_fin = st.date_input("Hasta", value=st.session_state.pick_pend_fecha_fin, disabled=solo_hoy)
        with col3:
            texto_cabecera = st.text_input("Texto de cabecera del picking", placeholder="Opcional")
        with col4:
            consultar_pedidos = st.form_submit_button("Consultar", use_container_width=True, type="primary")

    if consultar_pedidos:
        if not solo_hoy and fecha_fin < fecha_inicio:
            st.error("La fecha fin no puede ser menor que la fecha inicio.")
            st.stop()
        st.session_state.pick_pend_solo_hoy = bool(solo_hoy)
        st.session_state.pick_pend_fecha_inicio = fecha_inicio
        st.session_state.pick_pend_fecha_fin = fecha_fin

    st.caption(f"Fecha local operativa usada por Pedidos de hoy: {local_today().strftime('%Y-%m-%d')}")

    try:
        pedidos = get_pedidos_resumen(
            solo_hoy=st.session_state.pick_pend_solo_hoy,
            solo_creados=True,
            fecha_inicio=st.session_state.pick_pend_fecha_inicio,
            fecha_fin=st.session_state.pick_pend_fecha_fin,
        )
        detalle = get_pedidos_pendientes_detalle(
            solo_hoy=st.session_state.pick_pend_solo_hoy,
            fecha_inicio=st.session_state.pick_pend_fecha_inicio,
            fecha_fin=st.session_state.pick_pend_fecha_fin,
        )
    except Exception as exc:
        st.error("No se pudo cargar pedidos pendientes. Ejecuta la migración 008 en Azure SQL.")
        st.exception(exc)
        st.stop()

    pending_orders = len(pedidos)
    pending_codes = detalle["sku"].nunique() if not detalle.empty else 0
    unit_summary = summarize_units(detalle)

    m1, m2, m3 = st.columns(3)
    m1.metric("Pedidos pendientes", pending_orders)
    m2.metric("Códigos pendientes", pending_codes)
    m3.metric("Unidades pendientes", unit_summary)

    st.subheader("Pedidos pendientes")

    if pedidos.empty:
        st.info("No hay pedidos pendientes para crear picking con los filtros seleccionados. Si acabas de crear pedidos y no aparecen, desmarca Pedidos de hoy o amplía el rango Desde/Hasta para revisar la fecha registrada.")
    else:
        table = pedidos[[
            "id_pedido",
            "nro_pedido",
            "fecha_pedido",
            "fecha_esperada_atencion",
            "codigo_cuenta",
            "nombre_cuenta",
            "solicitante",
            "qty_total",
            "lineas",
            "estado",
        ]].copy()
        edited = selectable_table(table, "pick_pedidos_editor")
        selected_ids = edited.loc[edited["seleccionar"] == True, "id_pedido"].astype(int).tolist()

        colb1, colb2, colb3 = st.columns([1, 1, 3])
        crear = colb1.button("Crear Picking", type="primary", use_container_width=True)
        eliminar_pedido = colb2.button("Eliminar pedido(s)", type="secondary", use_container_width=True)
        colb3.caption("Puedes seleccionar uno o varios pedidos para consolidarlos. También puedes eliminar pedidos sin picking ni cantidades procesadas.")

        if eliminar_pedido:
            if not selected_ids:
                st.error("Selecciona al menos un pedido para eliminar.")
            else:
                try:
                    result = eliminar_pedidos(selected_ids)
                    st.session_state["msg_picking"] = f"Se eliminaron {result['pedidos_eliminados']} pedido(s) y {result['detalles_eliminados']} posición(es)."
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("No se pudo eliminar el pedido seleccionado.")
                    st.exception(exc)

        if crear:
            if not selected_ids:
                st.error("Selecciona al menos un pedido.")
            else:
                try:
                    result = crear_picking_desde_pedidos(selected_ids, current_user_id(), texto_cabecera)
                    msg = (
                        f"Picking {result['nro_picking']} creado con estado {result['estado']}. "
                        f"Asignado: {result['qty_asignada']:,.2f}. Corto: {result['qty_corto']:,.2f}."
                    )
                    st.session_state["msg_picking"] = msg
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo crear el picking.")
                    st.exception(exc)

with tab_visualizar:
    if "pick_fecha_inicio" not in st.session_state:
        st.session_state.pick_fecha_inicio = local_today()
    if "pick_fecha_fin" not in st.session_state:
        st.session_state.pick_fecha_fin = local_today()
    if "pick_estado" not in st.session_state:
        st.session_state.pick_estado = ""

    with st.form("form_filtros_pickings"):
        colf1, colf2, colf3, colf4 = st.columns([1, 1, 1, .7])
        with colf1:
            fecha_inicio = st.date_input("Fecha inicio", value=st.session_state.pick_fecha_inicio)
        with colf2:
            fecha_fin = st.date_input("Fecha fin", value=st.session_state.pick_fecha_fin)
        with colf3:
            estado_options = ["", "LIBERADO", "LIBERADO-CORTO", "COMPLETADO", "COMPLETADO-PARCIAL", "COMPLETADO-CORTO", "CANCELADO"]
            estado = st.selectbox(
                "Estado",
                estado_options,
                index=estado_options.index(st.session_state.pick_estado) if st.session_state.pick_estado in estado_options else 0,
                format_func=lambda x: "Todos" if x == "" else x,
            )
        with colf4:
            consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")

    if consultar:
        if fecha_fin < fecha_inicio:
            st.error("La fecha fin no puede ser menor que la fecha inicio.")
            st.stop()
        st.session_state.pick_fecha_inicio = fecha_inicio
        st.session_state.pick_fecha_fin = fecha_fin
        st.session_state.pick_estado = estado

    try:
        pickings = get_pickings_resumen(
            fecha_inicio=st.session_state.pick_fecha_inicio,
            fecha_fin=st.session_state.pick_fecha_fin,
            estado=st.session_state.pick_estado,
        )
    except Exception as exc:
        st.error("No se pudo cargar pickings. Ejecuta la migración 008 en Azure SQL.")
        st.exception(exc)
        st.stop()

    if pickings.empty:
        st.info("No hay pickings para los filtros seleccionados.")
    else:
        filtro = st.text_input("Buscar PK", key="filtro_pk")
        filtered = pickings.copy()
        if filtro.strip():
            v = filtro.strip().lower()
            filtered = filtered[filtered["nro_picking"].astype(str).str.lower().str.contains(v, na=False)]

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        labels = filtered.apply(lambda r: f"{r['nro_picking']} | {r['estado']} | Pedidos: {r['pedidos']}", axis=1).tolist()
        if labels:
            selected_label = st.selectbox("Selecciona picking", labels)
            selected = filtered.iloc[labels.index(selected_label)]
            colv1, colv2 = st.columns([1, 2])
            if colv1.button("Eliminar / cancelar picking", use_container_width=True):
                try:
                    cancelar_picking(int(selected["id_picking"]))
                    st.session_state["msg_picking"] = f"Picking {selected['nro_picking']} cancelado correctamente."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo cancelar el picking.")
                    st.exception(exc)
            colv2.caption("Solo se puede cancelar un picking si no tiene tareas ya atendidas.")

            st.subheader(f"Detalle {selected['nro_picking']}")
            st.dataframe(get_picking_detalle(int(selected["id_picking"])), use_container_width=True, hide_index=True)

with tab_cortos:
    try:
        cortos = get_picking_cortos(activos_only=True)
    except Exception as exc:
        st.error("No se pudo cargar cortos de picking.")
        st.exception(exc)
        st.stop()

    if cortos.empty:
        st.success("No hay cortos activos.")
    else:
        st.warning("Hay detalles cortos pendientes de reasignar o cancelar.")
        edited = selectable_table(cortos, "cortos_editor")
        selected_ids = edited.loc[edited["seleccionar"] == True, "id_picking_detalle"].astype(int).tolist()

        colc1, colc2, colc3 = st.columns([1, 1, 2])
        reasignar = colc1.button("Reasignar seleccionados", type="primary", use_container_width=True)
        cancelar = colc2.button("Cancelar seleccionados", use_container_width=True)
        colc3.caption("Reasignar vuelve a buscar stock surtible. Cancelar marca la cantidad como no atendible.")

        if reasignar:
            if not selected_ids:
                st.error("Selecciona al menos un corto.")
            else:
                try:
                    result = reasignar_cortos_picking(selected_ids)
                    st.session_state["msg_picking"] = (
                        f"Cortos procesados: {result['cortos_procesados']}. "
                        f"Reasignado: {result['reasignado']:,.2f}. "
                        f"Sigue corto: {result['sigue_corto']:,.2f}."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo reasignar los cortos.")
                    st.exception(exc)

        if cancelar:
            if not selected_ids:
                st.error("Selecciona al menos un corto.")
            else:
                try:
                    result = cancelar_cortos_picking(selected_ids)
                    st.session_state["msg_picking"] = (
                        f"Cortos cancelados: {result['cortos_cancelados']}. "
                        f"Cantidad cancelada: {result['qty_cancelada']:,.2f}."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo cancelar los cortos.")
                    st.exception(exc)
