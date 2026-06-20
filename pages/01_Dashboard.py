from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.queries import (
    get_cuentas,
    get_dashboard_movimientos,
    get_productos_activos,
    get_stock_general,
    get_ubicaciones,
)
from src.theme import PALETTE

st.markdown('<div class="wms-page-kicker">Reportes</div>', unsafe_allow_html=True)
st.title("📊 Dashboard operativo")
st.markdown(
    '<div class="wms-soft-banner">Resumen ejecutivo de ingresos, salidas, stock y movimientos. Usa los filtros para analizar por período, cuenta, proveedor o SKU.</div>',
    unsafe_allow_html=True,
)

@st.cache_data(ttl=90, show_spinner=False)
def load_dashboard_data():
    return {
        "movimientos": get_dashboard_movimientos(),
        "stock": get_stock_general(),
        "productos": get_productos_activos(),
        "ubicaciones": get_ubicaciones(),
        "cuentas": get_cuentas(),
    }


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _format_qty(value: float) -> str:
    return f"{value:,.2f}"


def _style_fig(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["navy"]),
        margin=dict(l=16, r=16, t=52, b=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(20,37,52,.08)")
    return fig


data = load_dashboard_data()
mov = data["movimientos"].copy()
stock = data["stock"].copy()
productos = data["productos"].copy()
ubicaciones = data["ubicaciones"].copy()
cuentas = data["cuentas"].copy()

if not mov.empty:
    mov["fecha_movimiento"] = pd.to_datetime(mov["fecha_movimiento"], errors="coerce")
    mov["fecha"] = mov["fecha_movimiento"].dt.date
    mov["cantidad"] = pd.to_numeric(mov["cantidad"], errors="coerce").fillna(0.0)
else:
    mov = pd.DataFrame(columns=[
        "fecha_movimiento", "fecha", "tipo_movimiento", "cantidad", "codigo_cuenta",
        "nombre_cuenta", "razon_social_proveedor", "sku", "nombre_producto", "codigo_unidad"
    ])

# ---------------------------------------------------------------------------
# Primera fila: filtros
# ---------------------------------------------------------------------------
st.markdown('<div class="wms-card"><div class="wms-card-title">🔎 Filtros</div>', unsafe_allow_html=True)

if not mov.empty and mov["fecha"].notna().any():
    min_date = min(mov["fecha"].dropna())
    max_date = max(mov["fecha"].dropna())
else:
    max_date = date.today()
    min_date = max_date - timedelta(days=30)

col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
with col1:
    fecha_rango = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
with col2:
    tipo_options = [""] + sorted(mov["tipo_movimiento"].dropna().astype(str).unique().tolist())
    tipo_filter = st.selectbox("Tipo movimiento", tipo_options, format_func=lambda x: "Todos" if x == "" else x)
with col3:
    cuenta_filter = st.text_input("Cuenta")
with col4:
    sku_filter = st.text_input("SKU / producto")

col5, col6 = st.columns([1, 1])
with col5:
    proveedor_filter = st.text_input("Proveedor")
with col6:
    if st.button("Actualizar datos", use_container_width=True):
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

if cuenta_filter.strip():
    value = cuenta_filter.strip().lower()
    filtered = filtered[
        filtered["codigo_cuenta"].astype(str).str.lower().str.contains(value, na=False)
        | filtered["nombre_cuenta"].astype(str).str.lower().str.contains(value, na=False)
    ]

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

# ---------------------------------------------------------------------------
# Segunda fila: KPI cards
# ---------------------------------------------------------------------------
ingresos = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "ENTRADA"]
salidas = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "SALIDA_CUENTA"]
transferencias = filtered[filtered["tipo_movimiento"].astype(str).str.upper() == "TRANSFERENCIA"]

stock_total = float(pd.to_numeric(stock.get("cantidad_total", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not stock.empty else 0.0
stock_disponible = float(pd.to_numeric(stock.get("cantidad_disponible", stock.get("cantidad_total", pd.Series(dtype=float))), errors="coerce").fillna(0).sum()) if not stock.empty else 0.0
low_stock = stock[
    pd.to_numeric(stock.get("cantidad_disponible", stock.get("cantidad_total", pd.Series(dtype=float))), errors="coerce").fillna(0)
    <= pd.to_numeric(stock.get("stock_minimo", pd.Series(dtype=float)), errors="coerce").fillna(0)
] if not stock.empty else _empty_df()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Ingresos", _format_qty(float(ingresos["cantidad"].sum())))
k2.metric("Salidas a cuenta", _format_qty(float(salidas["cantidad"].sum())))
k3.metric("Transferencias", _format_qty(float(transferencias["cantidad"].sum())))
k4.metric("Stock disponible", _format_qty(stock_disponible))
k5.metric("Bajo mínimo", len(low_stock))

k6, k7, k8, k9 = st.columns(4)
k6.metric("SKUs activos", len(productos))
k7.metric("Ubicaciones", len(ubicaciones))
k8.metric("Cuentas", len(cuentas))
k9.metric("Movimientos", filtered["id_movimiento"].nunique() if "id_movimiento" in filtered.columns else len(filtered))

# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------
if filtered.empty:
    st.info("No hay movimientos para los filtros seleccionados.")
    st.stop()

filtered["fecha_str"] = pd.to_datetime(filtered["fecha"], errors="coerce")

row1_col1, row1_col2 = st.columns([1.25, 1])

with row1_col1:
    daily = (
        filtered.groupby(["fecha_str", "tipo_movimiento"], as_index=False)["cantidad"]
        .sum()
        .sort_values("fecha_str")
    )
    fig = px.area(
        daily,
        x="fecha_str",
        y="cantidad",
        color="tipo_movimiento",
        title="Movimientos por día",
        color_discrete_sequence=[PALETTE["teal_dark"], PALETTE["teal"], PALETTE["gold"], PALETTE["navy"]],
    )
    st.plotly_chart(_style_fig(fig), use_container_width=True)

with row1_col2:
    by_type = filtered.groupby("tipo_movimiento", as_index=False)["cantidad"].sum()
    fig = px.pie(
        by_type,
        values="cantidad",
        names="tipo_movimiento",
        title="Distribución por tipo de movimiento",
        color_discrete_sequence=[PALETTE["teal_dark"], PALETTE["teal"], PALETTE["gold"], PALETTE["navy"]],
        hole=.48,
    )
    st.plotly_chart(_style_fig(fig), use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    top_sku = (
        filtered.groupby(["sku", "nombre_producto"], as_index=False)["cantidad"]
        .sum()
        .sort_values("cantidad", ascending=False)
        .head(10)
    )
    top_sku["producto"] = top_sku["sku"].astype(str) + " | " + top_sku["nombre_producto"].astype(str).str.slice(0, 34)
    fig = px.bar(
        top_sku,
        x="cantidad",
        y="producto",
        orientation="h",
        title="Top 10 productos movidos",
        color="cantidad",
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
            salidas_cuenta.groupby(["codigo_cuenta", "nombre_cuenta"], as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=False)
            .head(10)
        )
        by_account["cuenta"] = by_account["codigo_cuenta"].astype(str) + " | " + by_account["nombre_cuenta"].astype(str).str.slice(0, 30)
        fig = px.bar(
            by_account,
            x="cuenta",
            y="cantidad",
            title="Top cuentas por salidas",
            color_discrete_sequence=[PALETTE["teal"]],
        )
        st.plotly_chart(_style_fig(fig), use_container_width=True)

row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    ingresos_proveedor = ingresos.copy()
    if ingresos_proveedor.empty:
        st.info("No hay ingresos por proveedor para mostrar.")
    else:
        by_provider = (
            ingresos_proveedor.groupby("razon_social_proveedor", as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=False)
            .head(10)
        )
        fig = px.bar(
            by_provider,
            x="cantidad",
            y="razon_social_proveedor",
            orientation="h",
            title="Top proveedores por cantidad ingresada",
            color_discrete_sequence=[PALETTE["gold"]],
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(_style_fig(fig), use_container_width=True)

with row3_col2:
    if low_stock.empty:
        st.success("No hay productos bajo mínimo.")
    else:
        low_view = low_stock[["sku", "nombre_producto", "cantidad_disponible", "stock_minimo"]].copy() if "cantidad_disponible" in low_stock.columns else low_stock[["sku", "nombre_producto", "cantidad_total", "stock_minimo"]].copy()
        st.markdown("### ⚠️ Productos bajo mínimo")
        st.dataframe(low_view.head(15), use_container_width=True, hide_index=True)

st.markdown("### 📄 Movimientos filtrados")
st.dataframe(
    filtered[[
        "fecha_movimiento",
        "tipo_movimiento",
        "sku",
        "nombre_producto",
        "cantidad",
        "codigo_unidad",
        "codigo_cuenta",
        "nombre_cuenta",
        "razon_social_proveedor",
        "referencia",
    ]].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)

