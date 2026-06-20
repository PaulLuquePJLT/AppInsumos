from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


DefaultRow = dict[str, Any] | Callable[[], dict[str, Any]]


def _make_default(default_row: DefaultRow) -> dict[str, Any]:
    return dict(default_row() if callable(default_row) else default_row)


def ensure_columns(df: pd.DataFrame, columns: list[str], default_row: DefaultRow) -> pd.DataFrame:
    """Devuelve un DataFrame con todas las columnas esperadas.

    Se usa para que st.data_editor no pierda datos cuando hay pegado masivo,
    filas nuevas o columnas calculadas.
    """
    df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    defaults = _make_default(default_row)

    for col in columns:
        if col not in df.columns:
            df[col] = defaults.get(col, "")

    return df[columns]


def append_empty_rows_until(df: pd.DataFrame, row_index: int, columns: list[str], default_row: DefaultRow) -> pd.DataFrame:
    rows = []
    while len(df) <= row_index:
        rows.append(_make_default(default_row))
        df = pd.concat([df, pd.DataFrame(rows[-1:], columns=columns)], ignore_index=True)
    return df


def apply_data_editor_state(
    base_df: pd.DataFrame,
    editor_state: dict | None,
    columns: list[str],
    default_row: DefaultRow,
) -> pd.DataFrame:
    """Aplica cambios de st.data_editor sobre el DataFrame persistido.

    Este patrón evita reconstruir el editor cuando el usuario pega cantidades,
    ubicaciones o textos desde Excel. El estado del editor se fusiona con el
    DataFrame de sesión antes de volver a renderizar.
    """
    df = ensure_columns(base_df, columns, default_row)

    if not isinstance(editor_state, dict):
        return df

    edited_rows = editor_state.get("edited_rows") or {}
    added_rows = editor_state.get("added_rows") or []
    deleted_rows = editor_state.get("deleted_rows") or []

    for raw_index, changes in edited_rows.items():
        try:
            row_index = int(raw_index)
        except Exception:
            continue

        df = append_empty_rows_until(df, row_index, columns, default_row)

        if not isinstance(changes, dict):
            continue

        for col, value in changes.items():
            if col in columns:
                df.at[row_index, col] = value

    for added in added_rows:
        new_row = _make_default(default_row)
        if isinstance(added, dict):
            for col, value in added.items():
                if col in columns:
                    new_row[col] = value
        df = pd.concat([df, pd.DataFrame([new_row], columns=columns)], ignore_index=True)

    if deleted_rows:
        to_drop = []
        for raw_index in deleted_rows:
            try:
                idx = int(raw_index)
            except Exception:
                continue
            if 0 <= idx < len(df):
                to_drop.append(idx)
        if to_drop:
            df = df.drop(index=to_drop).reset_index(drop=True)

    return ensure_columns(df, columns, default_row)
