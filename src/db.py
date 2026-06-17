import os
import streamlit as st
from sqlalchemy import create_engine, text


def _get_secret(key, default=None):
    # 1. Intenta leer de Streamlit Secrets (nube)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    # 2. Si no, lee de variables de entorno (local)
    return os.getenv(key, default)


DB_SERVER = _get_secret("DB_SERVER")
DB_NAME = _get_secret("DB_NAME")
DB_USER = _get_secret("DB_USER")
DB_PASSWORD = _get_secret("DB_PASSWORD")


@st.cache_resource
def get_engine():
    # pymssql NO necesita ODBC Driver instalado en el sistema
    engine = create_engine(
        f"mssql+pymssql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:1433/{DB_NAME}",
        pool_pre_ping=True,
    )
    return engine


def test_connection():
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS test"))
        return result.fetchone()
