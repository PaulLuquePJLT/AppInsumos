from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.queries import (
    get_cuentas,
    get_dashboard_kpi_counts,
    get_dashboard_movimientos,
    get_stock_general,
    get_stock_por_cuenta,
)
from src.theme import PALETTE
from src.time_utils import local_today

st.markdown('<div class="wms-page-kicker">Reportes</div>', unsafe_allow_html=True)
st.title("Dashboard operativo")
st.markdown(
    '<div class="wms-soft-banner">Resumen ejecutivo de ingresos, salidas, stock valorizado y operación. Los movimientos se consultan directamente en Azure SQL usando el rango filtrado.</div>',
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_static_data():
    return {
        "stock": get_stock_general(),
        "stock_cuentas": get_stock_por_cuenta(),
        "counts": get_dashboard_kpi_counts(),
        "cuentas": get_cuentas(),
    }


@st.cache_data(ttl=90, show_spinner=False)
def load_dashboard_movimientos(fecha_inicio, fecha_fin, tipo_movimiento, cuenta, sku, proveedor):
    return get_dashboard_movimientos(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_movimiento=tipo_movimiento,
        cuenta=cuenta,
        sku=sku,
        proveedor=proveedor,
    )


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _format_qty(value: float) -> str:
    return f"{value:,.2f}"


def _format_pen(value: float) -> str:
    return f"S/ {value:,.2f}"


def _style_fig(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["navy"]),
        margin=dict(l=16, r=16, t=52, b=22),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(20,37,52,.08)")
    return fig


try:
    static_data = load_dashboard_static_data()
except Exception as exc:
    st.error("No se pudo cargar maestros/stock para el dashboard.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

stock = static_data["stock"].copy()
stock_cuentas = static_data["stock_cuentas"].copy()
counts = static_data["counts"].copy()
cuentas = static_data["cuentas"].copy()

for col in ["cantidad_total", "cantidad_disponible", "cantidad_en_picking", "valor_stock_total", "valor_stock_disponible"]:
    if col in stock.columns:
        stock[col] = pd.to_numeric(stock[col], errors="coerce").fillna(0.0)

for col in ["cantidad_neta", "valor_stock_cuenta"]:
    if col in stock_cuentas.columns:
        stock_cuentas[col] = pd.to_numeric(stock_cuentas[col], errors="coerce").fillna(0.0)

# ---------------------------------------------------------------------------
# Primera fila: filtros. Importante: estos filtros se aplican en SQL, no en Pandas.
# ---------------------------------------------------------------------------
st.markdown('<div class="wms-card"><div class="wms-card-title">Filtros</div>', unsafe_allow_html=True)

if "dash_fecha_inicio" not in st.session_state:
    st.session_state.dash_fecha_inicio = local_today() - timedelta(days=1)
if "dash_fecha_fin" not in st.session_state:
    st.session_state.dash_fecha_fin = local_today()
if "dash_tipo" not in st.session_state:
    st.session_state.dash_tipo = ""
if "dash_cuenta" not in st.session_state:
    st.session_state.dash_cuenta = ""
if "dash_sku" not in st.session_state:
    st.session_state.dash_sku = ""
if "dash_proveedor" not in st.session_state:
    st.session_state.dash_proveedor = ""

with st.form("form_dashboard_filtros"):
    col1, col2, col3, col4 = st.columns([1, 1, 1.2, 1])
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=st.session_state.dash_fecha_inicio)
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=st.session_state.dash_fecha_fin)
    with col3:
        tipo_options = ["", "ENTRADA", "SALIDA_CUENTA", "TRANSFERENCIA", "SALIDA_AJUSTE"]
        tipo_filter = st.selectbox(
            "Tipo movimiento",
            tipo_options,
            index=tipo_options.index(st.session_state.dash_tipo) if st.session_state.dash_tipo in tipo_options else 0,
            format_func=lambda x: "Todos" if x == "" else x,
        )
    with col4:
        modo = st.radio("Mostrar", ["Unidades", "Soles (S/.)"], horizontal=True)

    col5, col6, col7, col8 = st.columns([1.3, 1, 1, .7])
    with col5:
        cuenta_options = [""]
        cuenta_label_to_code = {"": ""}
        if not cuentas.empty:
            for _, r in cuentas.iterrows():
                label = f"{r['codigo_cuenta']} | {r['nombre_cuenta']}"
                cuenta_options.append(label)
                cuenta_label_to_code[label] = str(r["codigo_cuenta"])
        selected_label = None
        for k, v in cuenta_label_to_code.items():
            if v == st.session_state.dash_cuenta:
                selected_label = k
                break
        cuenta_label = st.selectbox(
            "Cuenta logística",
            cuenta_options,
            index=cuenta_options.index(selected_label or "") if (selected_label or "") in cuenta_options else 0,
            format_func=lambda x: "Todas" if x == "" else x,
        )
        cuenta_filter = cuenta_label_to_code.get(cuenta_label, "")
    with col6:
        sku_filter = st.text_input("SKU / producto", value=st.session_state.dash_sku)
    with col7:
        proveedor_filter = st.text_input("Proveedor", value=st.session_state.dash_proveedor)
    with col8:
        consultar = st.form_submit_button("Consultar", use_container_width=True, type="primary")

if consultar:
    if fecha_fin < fecha_inicio:
        st.error("La fecha fin no puede ser menor que la fecha inicio.")
        st.stop()
    st.session_state.dash_fecha_inicio = fecha_inicio
    st.session_state.dash_fecha_fin = fecha_fin
    st.session_state.dash_tipo = tipo_filter
    st.session_state.dash_cuenta = cuenta_filter
    st.session_state.dash_sku = sku_filter.strip()
    st.session_state.dash_proveedor = proveedor_filter.strip()
    load_dashboard_movimientos.clear()

col_refresh, _ = st.columns([.9, 4])
with col_refresh:
    if st.button("Actualizar datos", use_container_width=True):
        load_dashboard_static_data.clear()
        load_dashboard_movimientos.clear()
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

try:
    mov = load_dashboard_movimientos(
        st.session_state.dash_fecha_inicio,
        st.session_state.dash_fecha_fin,
        st.session_state.dash_tipo,
        st.session_state.dash_cuenta,
        st.session_state.dash_sku,
        st.session_state.dash_proveedor,
    ).copy()
except Exception as exc:
    st.error("No se pudo consultar movimientos del dashboard con los filtros seleccionados.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

if not mov.empty:
    mov["fecha_movimiento"] = pd.to_datetime(mov["fecha_movimiento"], errors="coerce")
    mov["fecha"] = mov["fecha_movimiento"].dt.date
    mov["cantidad"] = pd.to_numeric(mov.get("cantidad", 0), errors="coerce").fillna(0.0)
    mov["precio_unitario"] = pd.to_numeric(mov.get("precio_unitario", 0), errors="coerce").fillna(0.0)
    mov["importe_soles"] = pd.to_numeric(
        mov.get("importe_soles", mov["cantidad"] * mov["precio_unitario"]),
        errors="coerce",
    ).fillna(0.0)
else:
    mov = pd.DataFrame(columns=[
        "fecha_movimiento", "fecha", "tipo_movimiento", "cantidad", "importe_soles", "precio_unitario",
        "codigo_cuenta", "nombre_cuenta", "razon_social_proveedor", "ruc_proveedor", "sku", "nombre_producto", "codigo_unidad"
    ])

y_col = "importe_soles" if modo.startswith("Soles") else "cantidad"
y_label = "Monto S/." if y_col == "importe_soles" else "Cantidad"
formatter = _format_pen if y_col == "importe_soles" else _format_qty

# ---------------------------------------------------------------------------
# Segunda fila: KPI cards
# ---------------------------------------------------------------------------
ingresos = mov[mov["tipo_movimiento"].astype(str).str.upper() == "ENTRADA"]
salidas = mov[mov["tipo_movimiento"].astype(str).str.upper() == "SALIDA_CUENTA"]
transferencias = mov[mov["tipo_movimiento"].astype(str).str.upper() == "TRANSFERENCIA"]

stock_disponible = float(stock.get("cantidad_disponible", pd.Series(dtype=float)).sum()) if not stock.empty else 0.0
stock_valor_disponible = float(stock.get("valor_stock_disponible", pd.Series(dtype=float)).sum()) if not stock.empty else 0.0
low_stock = stock[
    pd.to_numeric(stock.get("cantidad_disponible", pd.Series(dtype=float)), errors="coerce").fillna(0)
    <= pd.to_numeric(stock.get("stock_minimo", pd.Series(dtype=float)), errors="coerce").fillna(0)
] if not stock.empty else _empty_df()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ingresos", formatter(float(ingresos[y_col].sum())) if not ingresos.empty else formatter(0))
k2.metric("Salidas a cuenta", formatter(float(salidas[y_col].sum())) if not salidas.empty else formatter(0))
k3.metric("Transferencias", formatter(float(transferencias[y_col].sum())) if not transferencias.empty else formatter(0))
k4.metric("Stock disponible", _format_pen(stock_valor_disponible) if y_col == "importe_soles" else _format_qty(stock_disponible))
k5.metric("Bajo mínimo", len(low_stock))

k6, k7, k8, k9 = st.columns(4)
skus_activos = int(counts["skus_activos"].iloc[0]) if not counts.empty and "skus_activos" in counts.columns else 0
ubicaciones_count = int(counts["ubicaciones"].iloc[0]) if not counts.empty and "ubicaciones" in counts.columns else 0
cuentas_count = int(counts["cuentas"].iloc[0]) if not counts.empty and "cuentas" in counts.columns else len(cuentas)
k6.metric("SKUs activos", skus_activos)
k7.metric("Ubicaciones", ubicaciones_count)
k8.metric("Cuentas", cuentas_count)
k9.metric("Movimientos", mov["id_movimiento"].nunique() if "id_movimiento" in mov.columns else len(mov))

if mov.empty:
    st.info("No hay movimientos para los filtros seleccionados.")
    st.stop()

mov["fecha_str"] = pd.to_datetime(mov["fecha"], errors="coerce")

# ---------------------------------------------------------------------------
# Gráficas principales. No se muestra tabla de movimientos en Dashboard.
# ---------------------------------------------------------------------------
row1_col1, row1_col2 = st.columns([1.25, 1])

with row1_col1:
    daily = (
        mov.groupby(["fecha_str", "tipo_movimiento"], as_index=False)[y_col]
        .sum()
        .sort_values("fecha_str")
    )
    fig = px.area(
        daily,
        x="fecha_str",
        y=y_col,
        color="tipo_movimiento",
        title=f"Movimientos por día - {y_label}",
        labels={y_col: y_label, "fecha_str": "Fecha"},
        color_discrete_sequence=[PALETTE["teal_dark"], PALETTE["teal"], PALETTE["gold"], PALETTE["navy"]],
    )
    st.plotly_chart(_style_fig(fig), use_container_width=True)

with row1_col2:
    by_type = mov.groupby("tipo_movimiento", as_index=False)[y_col].sum()
    fig = px.pie(
        by_type,
        values=y_col,
        names="tipo_movimiento",
        title=f"Distribución por tipo - {y_label}",
        color_discrete_sequence=[PALETTE["teal_dark"], PALETTE["teal"], PALETTE["gold"], PALETTE["navy"]],
        hole=.48,
    )
    st.plotly_chart(_style_fig(fig), use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    top_sku = (
        mov.groupby(["sku", "nombre_producto"], as_index=False)[y_col]
        .sum()
        .sort_values(y_col, ascending=False)
        .head(10)
    )
    top_sku["producto"] = top_sku["sku"].astype(str) + " | " + top_sku["nombre_producto"].astype(str).str.slice(0, 34)
    fig = px.bar(
        top_sku,
        x=y_col,
        y="producto",
        orientation="h",
        title=f"Top 10 productos movidos - {y_label}",
        labels={y_col: y_label},
        color=y_col,
        color_continuous_scale=[[0, PALETTE["teal_soft"]], [0.65, PALETTE["teal"]], [1, PALETTE["teal_dark"]]],
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    st.plotly_chart(_style_fig(fig), use_container_width=True)

with row2_col2:
    salidas_cuenta = salidas.copy()
    if salidas_cuenta.empty:
        st.info("No hay salidas a cuenta para mostrar.")
    else:
        by_account = (
            salidas_cuenta.groupby(["codigo_cuenta", "nombre_cuenta"], as_index=False)[y_col]
            .sum()
            .sort_values(y_col, ascending=False)
            .head(10)
        )
        by_account["cuenta"] = by_account["codigo_cuenta"].astype(str) + " | " + by_account["nombre_cuenta"].astype(str).str.slice(0, 30)
        fig = px.bar(
            by_account,
            x="cuenta",
            y=y_col,
            title=f"Top cuentas por salidas - {y_label}",
            labels={y_col: y_label},
            color_discrete_sequence=[PALETTE["teal"]],
        )
        st.plotly_chart(_style_fig(fig), use_container_width=True)

row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    stock_cuentas_view = stock_cuentas.copy()
    if st.session_state.dash_cuenta and not stock_cuentas_view.empty:
        stock_cuentas_view = stock_cuentas_view[stock_cuentas_view["codigo_cuenta"].astype(str).str.lower() == st.session_state.dash_cuenta.lower()]
    if stock_cuentas_view.empty or "valor_stock_cuenta" not in stock_cuentas_view.columns:
        st.info("No hay stock valorizado por cuenta para mostrar.")
    else:
        valor_cuenta = (
            stock_cuentas_view.groupby(["codigo_cuenta", "nombre_cuenta"], as_index=False)["valor_stock_cuenta"]
            .sum()
            .sort_values("valor_stock_cuenta", ascending=False)
            .head(12)
        )
        valor_cuenta["cuenta"] = valor_cuenta["codigo_cuenta"].astype(str) + " | " + valor_cuenta["nombre_cuenta"].astype(str).str.slice(0, 30)
        fig = px.bar(
            valor_cuenta,
            x="valor_stock_cuenta",
            y="cuenta",
            orientation="h",
            title="Valor de stock por cuenta logística (S/.)",
            labels={"valor_stock_cuenta": "Monto S/."},
            color_discrete_sequence=[PALETTE["teal_dark"]],
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(_style_fig(fig), use_container_width=True)

with row3_col2:
    mov_valor = mov[mov["tipo_movimiento"].astype(str).str.upper().isin(["ENTRADA", "SALIDA_CUENTA"])].copy()
    if mov_valor.empty:
        st.info("No hay ingresos o salidas para graficar valorización.")
    else:
        line_valor = (
            mov_valor.groupby(["fecha_str", "tipo_movimiento"], as_index=False)["importe_soles"]
            .sum()
            .sort_values("fecha_str")
        )
        fig = px.line(
            line_valor,
            x="fecha_str",
            y="importe_soles",
            color="tipo_movimiento",
            markers=True,
            title="Entradas vs salidas del almacén principal (S/.)",
            labels={"importe_soles": "Monto S/.", "fecha_str": "Fecha"},
            color_discrete_sequence=[PALETTE["teal_dark"], PALETTE["gold"]],
        )
        st.plotly_chart(_style_fig(fig), use_container_width=True)

row4_col1, row4_col2 = st.columns(2)

with row4_col1:
    ingresos_proveedor = ingresos.copy()
    if ingresos_proveedor.empty:
        st.info("No hay ingresos por proveedor para mostrar.")
    else:
        by_provider = (
            ingresos_proveedor.groupby("razon_social_proveedor", as_index=False)[y_col]
            .sum()
            .sort_values(y_col, ascending=False)
            .head(10)
        )
        fig = px.bar(
            by_provider,
            x=y_col,
            y="razon_social_proveedor",
            orientation="h",
            title=f"Top proveedores por ingresos - {y_label}",
            labels={y_col: y_label},
            color_discrete_sequence=[PALETTE["gold"]],
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(_style_fig(fig), use_container_width=True)

with row4_col2:
    if low_stock.empty:
        st.success("No hay productos bajo mínimo.")
    else:
        low_cols = [c for c in ["sku", "nombre_producto", "cantidad_disponible", "valor_stock_disponible", "stock_minimo"] if c in low_stock.columns]
        st.markdown("### Productos bajo mínimo")
        st.dataframe(low_stock[low_cols].head(15), use_container_width=True, hide_index=True)
