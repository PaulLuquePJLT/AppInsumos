import pandas as pd
import streamlit as st

from src.movimientos import registrar_salida_ajuste_almacen, registrar_salida_ajuste_cuentas
from src.queries import get_stock_ajuste_almacen, get_stock_ajuste_cuentas
from src.session import current_user_id, is_admin

st.title("Salida Ajuste")
st.caption("Descuento administrativo de stock físico o stock asignado a cuentas logísticas.")

if not is_admin():
    st.error("Solo el rol Administrador puede ejecutar salidas por ajuste.")
    st.stop()

if "msg_salida_ajuste" in st.session_state:
    st.success(st.session_state.pop("msg_salida_ajuste"))


def _prepare_editor(df: pd.DataFrame, qty_col: str) -> pd.DataFrame:
    df = df.copy()
    if "seleccionar" not in df.columns:
        df.insert(0, "seleccionar", False)
    if "cantidad_ajuste" not in df.columns:
        df.insert(1, "cantidad_ajuste", 0.0)
    df["seleccionar"] = df["seleccionar"].fillna(False).astype(bool)
    df["cantidad_ajuste"] = pd.to_numeric(df["cantidad_ajuste"], errors="coerce").fillna(0.0)
    df["cantidad_sugerida"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0.0)
    return df


def _selected_rows(editor_df: pd.DataFrame, qty_available_col: str) -> tuple[list[dict], list[str]]:
    selected = editor_df[editor_df["seleccionar"] == True].copy()
    errors: list[str] = []
    items: list[dict] = []

    if selected.empty:
        return [], ["Selecciona al menos una línea."]

    for idx, row in selected.iterrows():
        qty = float(pd.to_numeric(row.get("cantidad_ajuste"), errors="coerce") or 0)
        available = float(pd.to_numeric(row.get(qty_available_col), errors="coerce") or 0)
        sku = str(row.get("sku", ""))
        if qty <= 0:
            errors.append(f"Fila {idx + 1} / {sku}: la cantidad de ajuste debe ser mayor a cero.")
        elif qty > available:
            errors.append(f"Fila {idx + 1} / {sku}: cantidad ajuste {qty} supera disponible {available}.")
        else:
            item = row.to_dict()
            item["cantidad"] = qty
            item["texto_item"] = f"Salida ajuste por {qty:,.2f}"
            items.append(item)

    return items, errors


with st.expander("Datos de cabecera", expanded=True):
    col_ref, col_obs = st.columns([1, 2])
    with col_ref:
        referencia = st.text_input("Referencia", placeholder="Ej. AJUSTE-INV-001")
    with col_obs:
        observacion = st.text_input("Texto de cabecera", placeholder="Motivo del ajuste")


tab_almacen, tab_cuentas = st.tabs(["Stock almacén", "Stock cuentas logísticas"])

with tab_almacen:
    st.subheader("Salida ajuste desde almacén")
    with st.form("filtros_salida_ajuste_almacen"):
        f1, f2, f3, f4 = st.columns([1, 1, 1, .7])
        with f1:
            sku = st.text_input("SKU o producto")
        with f2:
            ubicacion = st.text_input("Ubicación / zona")
        with f3:
            st.text_input("Cuenta logística", value="No aplica", disabled=True)
        with f4:
            consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")

    if consultar or "salida_ajuste_almacen_df" not in st.session_state:
        try:
            st.session_state.salida_ajuste_almacen_df = get_stock_ajuste_almacen(sku=sku.strip(), ubicacion=ubicacion.strip())
        except Exception as exc:
            st.error("No se pudo consultar stock de almacén.")
            with st.expander("Detalle técnico"):
                st.code(str(exc))
            st.stop()

    df = st.session_state.get("salida_ajuste_almacen_df", pd.DataFrame())
    if df.empty:
        st.info("No hay stock físico disponible con los filtros seleccionados.")
    else:
        editor_df = _prepare_editor(df, "cantidad_disponible")
        disabled_cols = [c for c in editor_df.columns if c not in {"seleccionar", "cantidad_ajuste"}]
        edited = st.data_editor(
            editor_df,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_cols,
            key="editor_salida_ajuste_almacen",
            column_config={
                "seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                "cantidad_ajuste": st.column_config.NumberColumn("Cantidad a quitar", min_value=0.0, step=1.0),
            },
        )
        items, errors = _selected_rows(edited, "cantidad_disponible")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            confirmar = st.checkbox("Confirmo salida ajuste almacén", key="conf_salida_ajuste_almacen")
        with col_b:
            ejecutar = st.button("Ejecutar salida ajuste almacén", type="primary", use_container_width=True)
        if ejecutar:
            if errors:
                for error in errors:
                    st.error(error)
            elif not confirmar:
                st.error("Marca la confirmación antes de ejecutar el ajuste.")
            else:
                try:
                    mov_id = registrar_salida_ajuste_almacen(
                        items=items,
                        id_usuario=current_user_id(),
                        referencia=referencia.strip() or None,
                        observacion=observacion.strip() or None,
                    )
                    st.session_state.pop("salida_ajuste_almacen_df", None)
                    st.session_state["msg_salida_ajuste"] = f"Salida ajuste de almacén registrada. Movimiento {mov_id}."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo ejecutar la salida ajuste de almacén.")
                    with st.expander("Detalle técnico"):
                        st.code(str(exc))

with tab_cuentas:
    st.subheader("Salida ajuste desde cuentas logísticas")
    with st.form("filtros_salida_ajuste_cuentas"):
        f1, f2, f3 = st.columns([1, 1, .7])
        with f1:
            cuenta = st.text_input("Cuenta logística")
        with f2:
            sku_c = st.text_input("SKU o producto")
        with f3:
            consultar_c = st.form_submit_button("Consultar", use_container_width=True, type="primary")

    if consultar_c or "salida_ajuste_cuentas_df" not in st.session_state:
        try:
            st.session_state.salida_ajuste_cuentas_df = get_stock_ajuste_cuentas(sku=sku_c.strip(), cuenta=cuenta.strip())
        except Exception as exc:
            st.error("No se pudo consultar stock de cuentas.")
            with st.expander("Detalle técnico"):
                st.code(str(exc))
            st.stop()

    dfc = st.session_state.get("salida_ajuste_cuentas_df", pd.DataFrame())
    if dfc.empty:
        st.info("No hay stock por cuenta disponible con los filtros seleccionados.")
    else:
        editor_df_c = _prepare_editor(dfc, "cantidad_neta")
        disabled_cols_c = [c for c in editor_df_c.columns if c not in {"seleccionar", "cantidad_ajuste"}]
        edited_c = st.data_editor(
            editor_df_c,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_cols_c,
            key="editor_salida_ajuste_cuentas",
            column_config={
                "seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
                "cantidad_ajuste": st.column_config.NumberColumn("Cantidad a quitar", min_value=0.0, step=1.0),
            },
        )
        items_c, errors_c = _selected_rows(edited_c, "cantidad_neta")
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            confirmar_c = st.checkbox("Confirmo salida ajuste cuentas", key="conf_salida_ajuste_cuentas")
        with col_c2:
            ejecutar_c = st.button("Ejecutar salida ajuste cuentas", type="primary", use_container_width=True)
        if ejecutar_c:
            if errors_c:
                for error in errors_c:
                    st.error(error)
            elif not confirmar_c:
                st.error("Marca la confirmación antes de ejecutar el ajuste.")
            else:
                try:
                    movs = registrar_salida_ajuste_cuentas(
                        items=items_c,
                        id_usuario=current_user_id(),
                        referencia=referencia.strip() or None,
                        observacion=observacion.strip() or None,
                    )
                    st.session_state.pop("salida_ajuste_cuentas_df", None)
                    st.session_state["msg_salida_ajuste"] = "Salida ajuste de cuentas registrada. Movimientos: " + ", ".join(str(m) for m in movs)
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo ejecutar la salida ajuste de cuentas.")
                    with st.expander("Detalle técnico"):
                        st.code(str(exc))
