import os

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def _get_secret(key: str, default=None):
    """Lee primero Streamlit Secrets y luego variables de entorno."""
    try:
        if key in st.secrets and st.secrets[key] not in (None, ""):
            return str(st.secrets[key])
    except Exception:
        pass

    value = os.getenv(key, default)
    return str(value) if value not in (None, "") else default


def _normalize_server(server: str) -> str:
    """Acepta formatos como tcp:servidor.database.windows.net,1433."""
    server = server.strip()
    server = server.replace("tcp:", "")
    server = server.replace(",1433", "")
    return server


@st.cache_resource
def get_engine():
    db_server = _get_secret("DB_SERVER")
    db_name = _get_secret("DB_NAME")
    db_user = _get_secret("DB_USER")
    db_password = _get_secret("DB_PASSWORD")

    missing = [
        name
        for name, value in {
            "DB_SERVER": db_server,
            "DB_NAME": db_name,
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Faltan variables de conexión en Streamlit Secrets: "
            + ", ".join(missing)
        )

    url = URL.create(
        drivername="mssql+pymssql",
        username=db_user,
        password=db_password,
        host=_normalize_server(db_server),
        port=1433,
        database=db_name,
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


def test_connection() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS test")).scalar_one()
    return result == 1
