from io import BytesIO

import pandas as pd


def build_excel_template(columns: list[str], example_rows: list[dict] | None = None) -> bytes:
    """Crea una plantilla Excel en memoria con encabezados y filas de ejemplo."""
    df = pd.DataFrame(example_rows or [], columns=columns)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Plantilla")

    return output.getvalue()


def read_excel_upload(uploaded_file) -> pd.DataFrame:
    """Lee el primer sheet de un Excel subido desde st.file_uploader."""
    return pd.read_excel(uploaded_file, dtype=object).fillna("")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza encabezados quitando espacios laterales."""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        return ["Faltan columnas obligatorias: " + ", ".join(missing)]

    return []


def clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def clean_upper(value) -> str:
    return clean_text(value).upper()


def to_float(value, default=0.0):
    value = clean_text(value)

    if value == "":
        return default

    return float(value)


def to_bool_int(value) -> int:
    value = clean_text(value).lower()

    return 1 if value in {
        "1",
        "si",
        "sí",
        "s",
        "true",
        "verdadero",
        "x",
        "yes",
        "y",
    } else 0


def add_error(errors: list[dict], row_number: int, field: str, message: str) -> None:
    errors.append({
        "fila_excel": row_number,
        "campo": field,
        "error": message,
    })


def show_validation_errors(st, errors: list[dict]) -> None:
    st.error("El archivo tiene errores. Corrige el Excel y vuelve a cargarlo.")
    st.dataframe(
        pd.DataFrame(errors),
        use_container_width=True,
        hide_index=True,
    )
