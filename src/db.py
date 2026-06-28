import os
import time
from typing import Callable, TypeVar

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.pool import NullPool

T = TypeVar("T")


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
        poolclass=NullPool,
        pool_pre_ping=True,
        future=True,
        connect_args={
            "login_timeout": 30,
            "timeout": 60,
        },
    )


def reset_engine_pool() -> None:
    """Descarta el engine actual para forzar una conexión limpia en el siguiente intento."""
    try:
        engine = get_engine()
        engine.dispose()
    except Exception:
        pass

    try:
        get_engine.clear()
    except Exception:
        pass


def _is_retryable_db_error(exc: Exception) -> bool:
    text_error = str(exc).lower()
    retry_markers = [
        "login timeout",
        "timeout expired",
        "connection timed out",
        "connection is closed",
        "closed connection",
        "server is not currently configured",
        "adaptive server connection failed",
        "transport-level error",
        "connection reset",
        "db-lib error message 20009",
        "db-lib error message 20003",
        "azure sql",
        "is not available",
        "database is not currently available",
    ]

    return isinstance(exc, (OperationalError, InterfaceError, DBAPIError)) or any(
        marker in text_error for marker in retry_markers
    )


def run_db_with_retry(operation: Callable[[], T], attempts: int = 3) -> T:
    """Ejecuta una operación SQL con reintentos.

    Esto ayuda cuando Azure SQL Serverless está pausado o el engine tiene
    una conexión stale. Si falla, se descarta el engine y se reintenta.
    """
    last_exc: Exception | None = None
    delays = [2, 5, 10]

    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts - 1 or not _is_retryable_db_error(exc):
                raise
            reset_engine_pool()
            time.sleep(delays[min(attempt, len(delays) - 1)])

    if last_exc:
        raise last_exc
    raise RuntimeError("No se pudo ejecutar la operación de base de datos.")


def test_connection() -> bool:
    def _op():
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test")).scalar_one()
        return result == 1

    return run_db_with_retry(_op)
