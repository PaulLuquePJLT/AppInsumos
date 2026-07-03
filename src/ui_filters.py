from __future__ import annotations

import pandas as pd
import streamlit as st


def filter_bulk_dataframe(
    df: pd.DataFrame,
    key_prefix: str,
    text_columns: list[str],
    active_column: str = "activo",
    extra_options: dict[str, list] | None = None,
) -> pd.DataFrame:
    """Filtros ligeros para pestañas de modificación masiva.

    Permite segmentar la tabla antes de editar para evitar cargar o modificar todo el maestro.
    """
    if df is None or df.empty:
        return df

    with st.container(border=True):
        st.caption("Filtros de modificación masiva")
        col1, col2 = st.columns([2, 1])
        search = col1.text_input("Buscar", key=f"{key_prefix}_search", placeholder="Código, nombre, descripción...")
        estado = col2.selectbox("Estado", ["Todos", "Activos", "Inactivos"], key=f"{key_prefix}_estado")

        filtered = df.copy()

        if search.strip():
            value = search.strip().lower()
            mask = pd.Series(False, index=filtered.index)
            for col in text_columns:
                if col in filtered.columns:
                    mask = mask | filtered[col].astype(str).str.lower().str.contains(value, na=False)
            filtered = filtered[mask]

        if active_column in filtered.columns:
            if estado == "Activos":
                filtered = filtered[filtered[active_column].astype(bool) == True]
            elif estado == "Inactivos":
                filtered = filtered[filtered[active_column].astype(bool) == False]

        if extra_options:
            # Opcional: filtros por valores únicos para columnas específicas.
            for col, label_options in extra_options.items():
                if col not in filtered.columns:
                    continue
                opciones = ["Todos"] + sorted(filtered[col].dropna().astype(str).unique().tolist())
                selected = st.selectbox(label_options[0] if label_options else col, opciones, key=f"{key_prefix}_{col}")
                if selected != "Todos":
                    filtered = filtered[filtered[col].astype(str) == selected]

        st.caption(f"Registros filtrados: {len(filtered):,} de {len(df):,}")

    return filtered.reset_index(drop=True)
