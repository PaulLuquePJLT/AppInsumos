from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.queries import (
    get_cuentas,
    get_dashboard_movimientos,
    get_productos_activos,
    get_stock_general,
    get_stock_por_cuenta,
    get_ubicaciones,
)
from src.theme import PALETTE

st.markdown('<div class="wms-page-kicker">Reportes</div>', unsafe_allow_html=True)
st.title("Dashboard operativo")
st.markdown(
    '<div class="wms-soft-banner">Resumen ejecutivo de ingresos, salidas, stock valorizado y movimientos. Cambia entre unidades y soles peruanos para analizar cantidades o valor económico.</div>',
    unsafe_allow_html=True,
)


@st.cache_data(ttl=90, show_spinner=False)
def load_dashboard_data():
    return {
        "movimientos": get_dashboard_movimientos(),
        "stock": get_stock_general(),
        "stock_cuentas": get_stock_por_cuenta(),
        "productos": get_productos_activos(),
        "ubicaciones": get_ubicaciones(),
        "cuentas": get_cuentas(),
    }


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
    data = load_dashboard_data()
except Exception as exc:
    st.error(
        "No se pudo cargar la información del dashboard. "
        "Ejecuta en Azure SQL el script database/012_precio_dashboard_optimization.sql "
        "y luego reinicia la app."
    )
    with st.expander("Detalle técnico"):
        st.code(str(exc))
    st.stop()

mov = data["movimientos"].copy()
stock = data["stock"].copy()
stock_cuentas = data["stock_cuentas"].copy()
productos = data["productos"].copy()
ubicaciones = data["ubicaciones"].copy()
cuentas = data["cuentas"].copy()

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

for col in ["cantidad_total", "cantidad_disponible", "cantidad_en_picking", "valor_stock_total", "valor_stock_disponible"]:
    if col in stock.columns:
        stock[col] = pd.to_numeric(stock[col], errors="coerce").fillna(0.0)

for col in ["cantidad_neta", "valor_stock_cuenta"]:
    if col in stock_cuentas.columns:
        stock_cuentas[col] = pd.to_numeric(stock_cuentas[col], errors="coerce").fillna(0.0)

# ---------------------------------------------------------------------------
# Primera fila: filtros
# ---------------------------------------------------------------------------
st.markdown('<div class="wms-card"><div class="wms-card-title">Filtros</div>', unsafe_allow_html=True)

if not mov.empty and mov["fecha"].notna().any():
    max_date = max(mov["fecha"].dropna())
    min_date = max_date - timedelta(days=1)
    available_min_date = min(mov["fecha"].dropna())
else:
    max_date = date.today()
    min_date = max_date - timedelta(days=1)
    available_min_date = max_date - timedelta(days=365)

col1, col2, col3, col4 = st.columns([1.25, 1, 1.2, 1])
with col1:
    fecha_rango = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=available_min_date,
        max_value=max_date,
    )
with col2:
    tipo_options = [""] + sorted(mov["tipo_movimiento"].dropna().astype(str).unique().tolist())
    tipo_filter = st.selectbox("Tipo movimiento", tipo_options, format_func=lambda x: "Todos" if x == "" else x)
with col3:
    cuenta_options = [""]
    cuenta_label_to_code = {"": ""}
    if not cuentas.empty:
        for _, r in cuentas.iterrows():
            label = f"{r['codigo_cuenta']} | {r['nombre_cuenta']}"
            cuenta_options.append(label)
            cuenta_label_to_code[label] = str(r["codigo_cuenta"])
    cuenta_label = st.selectbox("Cuenta logística", cuenta_options, format_func=lambda x: "Todas" if x == "" else x)
    cuenta_filter = cuenta_label_to_code.get(cuenta_label, "")
with col4:
    modo = st.radio("Mostrar", ["Unidades", "Soles (S/.)"], horizontal=True)

col5, col6, col7 = st.columns([1, 1, .7])
with col5:
    sku_filter = st.text_input("SKU / producto")
with col6:
    proveedor_filter = st.text_input("Proveedor")
with col7:
    if st.button("Actualizar", use_container_width=True):
        load_dashboard_data.clear()
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

filtered = mov.copy()

if isinstance(fecha_rango, tuple) and len(fecha_rango) == 2:
    start_date, end_date = fecha_rango
else:
    start_date = fecha_rango
    end_date = fecha_rango

if not filtered.empty:
    filtered = filtered[(filtered["fecha"] >= start_date) & (filtered["fecha"] <= end_date)]

if tipo_filter:
    filtered = filtered[filtered["tipo_movimiento"].astype(str) == tipo_filter]

if cuenta_filter:
    value = cuenta_filter.lower()
    filtered = filtered[filtered["codigo_cuenta"].astype(str).str.lower() == value]

if proveedor_filter.strip():
    value = proveedor_filter.strip().lower()
    filtered = filtered[
        filtered["razon_social_proveedor"].astype(str).str.lower().str.contains(value, na=False)
        | filtered["ruc_proveedor"].astype(str).str.lower().str.contains(value, na=False)
    ]

if sku_filter.strip():
    value = sku_filter.strip().lower()
    filtered = filtered[
        filtered["sku"].astype(str).str.lower().str.contains(value, na=False)
        | filtered["nombre_producto"].astype(str).str.lower().str.contains(value, na=False)
    ]

y_col = "importe_soles" if modo.startswith("Soles") else "cantidad"
y_label = "Monto S/." if y_col == "importe_soles" else "Cantidad"
formatter = _format_pen if y_col == "importe_soles" else _format_qty

# ---------------------------------------------------------------------------
# Segunda fila: KPI cards
# ---------------------------------------------------------------------------
ingresos = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "ENTRADA"]
salidas = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "SALIDA_CUENTA"]
transferencias = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "TRANSFERENCIA"]

stock_disponible = float(stock.get("cantidad_disponible", pd.Series(dtype=float)).sum()) if not stock.empty else 0.0
stock_valor_disponible = float(stock.get("valor_stock_disponible", pd.Series(dtype=float)).sum()) if not stock.empty else 0.0
low_stock = stock[
    pd.to_numeric(stock.get("cantidad_disponible", pd.Series(dtype=float)), errors="coerce").fillna(0)
    <= pd.to_numeric(stock.get("stock_minimo", pd.Series(dtype=float)), errors="coerce").fillna(0)
] if not stock.empty else _empty_df()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ingresos", formatter(float(ingresos[y_col].sum())))
k2.metric("Salidas a cuenta", formatter(float(salidas[y_col].sum())))
k3.metric("Transferencias", formatter(float(transferencias[y_col].sum())))
k4.metric("Stock disponible", _format_pen(stock_valor_disponible) if y_col == "importe_soles" else _format_qty(stock_disponible))
k5.metric("Bajo mínimo", len(low_stock))

k6, k7, k8, k9 = st.columns(4)
k6.metric("SKUs activos", len(productos))
k7.metric("Ubicaciones", len(ubicaciones))
k8.metric("Cuentas", len(cuentas))
k9.metric("Movimientos", filtered["id_movimiento"].nunique() if "id_movimiento" in filtered.columns else len(filtered))

if filtered.empty:
    st.info("No hay movimientos para los filtros seleccionados.")
    st.stop()

filtered["fecha_str"] = pd.to_datetime(filtered["fecha"], errors="coerce")

# ---------------------------------------------------------------------------
# Gráficas principales
# ---------------------------------------------------------------------------
row1_col1, row1_col2 = st.columns([1.25, 1])

with row1_col1:
    daily = (
        filtered.groupby(["fecha_str", "tipo_movimiento"], as_index=False)[y_col]
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
    by_type = filtered.groupby("tipo_movimiento", as_index=False)[y_col].sum()
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
        filtered.groupby(["sku", "nombre_producto"], as_index=False)[y_col]
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
    if cuenta_filter and not stock_cuentas_view.empty:
        stock_cuentas_view = stock_cuentas_view[stock_cuentas_view["codigo_cuenta"].astype(str).str.lower() == cuenta_filter.lower()]
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
    mov_valor = filtered[filtered["tipo_movimiento"].astype(str).str.upper().isin(["ENTRADA", "SALIDA_CUENTA"])].copy()
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

st.markdown("### Movimientos filtrados")
cols = [
    "fecha_movimiento", "tipo_movimiento", "sku", "nombre_producto", "cantidad", "codigo_unidad",
    "precio_unitario", "importe_soles", "codigo_cuenta", "nombre_cuenta", "razon_social_proveedor", "referencia",
]
st.dataframe(filtered[[c for c in cols if c in filtered.columns]].reset_index(drop=True), use_container_width=True, hide_index=True)
