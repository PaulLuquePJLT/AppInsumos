from sqlalchemy import text
from src.db import get_engine


def execute_non_query(sql, params=None):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})
