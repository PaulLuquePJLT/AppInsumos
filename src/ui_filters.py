from __future__ import annotations

import re
from typing import Iterable, Literal, TypedDict

import pandas as pd
import streamlit as st


class FilterSpec(TypedDict, total=False):
    column: str
    label: str
    mode: Literal["exact", "contains"]
    placeholder: str
    help: str


def parse_pasted_values(value: str) -> list[str]:
    """Parsea valores copiados desde Excel o texto libre.

    Acepta listas separadas por salto de línea, tab, coma o punto y coma.
    No divide por espacios para no romper nombres/descripciones.
    """
    text = str(value or "").strip()
    if not text:
        return []

    parts = re.split(r"[\n\r\t;,]+", text)
    return [item.strip() for item in parts if item and item.strip()]


def _norm_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.upper()


def apply_values_filter(
    df: pd.DataFrame,
    column: str,
    values: Iterable[str],
    mode: str = "exact",
) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df

    cleaned = [str(v).strip() for v in values if str(v).strip()]
    if not cleaned:
        return df

    col_norm = _norm_series(df[column])

    if mode == "contains":
        mask = pd.Series(False, index=df.index)
        for value in cleaned:
            mask = mask | col_norm.str.contains(re.escape(value.upper()), na=False)
        return df[mask]

    allowed = {value.upper() for value in cleaned}
    return df[col_norm.isin(allowed)]


def render_multicriteria_filter(
    df: pd.DataFrame,
    specs: list[FilterSpec],
    key_prefix: str,
    title: str = "Filtros de modificación masiva",
) -> pd.DataFrame:
    """Renderiza filtros multi-criterio para modificaciones masivas.

    Permite pegar columnas de Excel. Ejemplo: pegar 100 SKUs en el filtro SKU
    y editar únicamente esos registros.
    """
    if df.empty:
        return df

    with st.expander(title, expanded=False):
        st.caption(
            "Puedes copiar una columna desde Excel y pegarla aquí. "
            "Se aceptan valores separados por salto de línea, tab, coma o punto y coma."
        )
        filtered = df.copy()
        cols = st.columns(2)
        for idx, spec in enumerate(specs):
            column = spec["column"]
            label = spec.get("label", column)
            mode = spec.get("mode", "exact")
            placeholder = spec.get("placeholder", "Pega uno o varios valores")
            help_text = spec.get("help", None)
            with cols[idx % 2]:
                raw = st.text_area(
                    label,
                    key=f"{key_prefix}_{column}_multifilter",
                    placeholder=placeholder,
                    help=help_text,
                    height=72,
                )
            values = parse_pasted_values(raw)
            if values:
                filtered = apply_values_filter(filtered, column, values, mode=mode)

        if "activo" in filtered.columns:
            estado = st.selectbox(
                "Estado",
                ["Todos", "Activos", "Inactivos"],
                key=f"{key_prefix}_activo_filter",
            )
            if estado == "Activos":
                filtered = filtered[filtered["activo"].astype(bool)]
            elif estado == "Inactivos":
                filtered = filtered[~filtered["activo"].astype(bool)]

        st.info(f"Mostrando {len(filtered):,} de {len(df):,} registros para modificar.")
        return filtered
