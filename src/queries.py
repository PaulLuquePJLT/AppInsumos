import pandas as pd
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from src.db import get_engine


def _ensure_text(statement):
    """Acepta SQL como string o como objeto text()."""
    if isinstance(statement, TextClause):
        return statement
    if isinstance(statement, str):
        return text(statement)
    raise TypeError(f"El SQL debe ser str o text(), no {type(statement).__name__}")


def read_dataframe(query, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(_ensure_text(query), conn, params=params or {})


def execute_statement(statement, params: dict | None = None) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(_ensure_text(statement), params or {})


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def get_stock_general():
    return read_dataframe("SELECT * FROM vw_stock_general ORDER BY nombre_producto")


def get_stock_por_ubicacion():
    return read_dataframe(
        "SELECT * FROM vw_stock_por_ubicacion ORDER BY nombre_producto, codigo_ubicacion"
    )


def get_stock_por_cuenta():
    return read_dataframe(
        "SELECT * FROM vw_stock_por_cuenta ORDER BY nombre_cuenta, nombre_producto"
    )


def get_productos_activos():
    return read_dataframe("""
        SELECT
            id_producto,
            sku,
            nombre_producto,
            id_categoria,
            id_unidad,
            stock_minimo,
            stock_maximo,
            requiere_lote
        FROM productos
        WHERE activo = 1
        ORDER BY nombre_producto
    """)


def get_ubicaciones():
    return read_dataframe("""
        SELECT
            ub.id_ubicacion,
            ub.codigo_ubicacion,
            ub.tipo_ubicacion,
            ub.id_zona,
            z.codigo_zona,
            z.nombre_zona
        FROM ubicaciones ub
        LEFT JOIN zonas_almacen z ON z.id_zona = ub.id_zona
        WHERE ub.activo = 1
        ORDER BY ub.codigo_ubicacion
    """)


def get_cuentas():
    return read_dataframe("""
        SELECT id_cuenta, codigo_cuenta, nombre_cuenta
        FROM cuentas_logisticas
        WHERE activo = 1
        ORDER BY nombre_cuenta
    """)


def get_zonas():
    return read_dataframe("""
        SELECT id_zona, codigo_zona, nombre_zona, descripcion, activo
        FROM zonas_almacen
        WHERE activo = 1
        ORDER BY codigo_zona
    """)


def get_categorias():
    return read_dataframe("""
        SELECT id_categoria, nombre_categoria
        FROM categorias_producto
        WHERE activo = 1
        ORDER BY nombre_categoria
    """)


def get_unidades():
    return read_dataframe("""
        SELECT id_unidad, codigo_unidad, nombre_unidad
        FROM unidades_medida
        ORDER BY nombre_unidad
    """)


def get_movimientos():
    return read_dataframe("SELECT * FROM vw_movimientos ORDER BY fecha_movimiento DESC")


def get_stock_disponible_por_producto(id_producto: int):
    return read_dataframe(
        """
        SELECT
            su.id_producto,
            su.id_ubicacion,
            p.sku,
            p.nombre_producto,
            ub.codigo_ubicacion,
            su.lote,
            su.cantidad_actual
        FROM stock_ubicacion su
        INNER JOIN productos p ON p.id_producto = su.id_producto
        INNER JOIN ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
        WHERE su.id_producto = :id_producto
          AND su.cantidad_actual > 0
          AND p.activo = 1
          AND ub.activo = 1
        ORDER BY ub.codigo_ubicacion
        """,
        {"id_producto": id_producto},
    )


# ---------------------------------------------------------------------------
# Inserciones
# ---------------------------------------------------------------------------

def insert_producto(
    sku,
    nombre_producto,
    descripcion,
    id_categoria,
    id_unidad,
    stock_minimo,
    stock_maximo,
    requiere_lote,
):
    query = """
        INSERT INTO productos
            (sku, nombre_producto, descripcion, id_categoria, id_unidad,
             stock_minimo, stock_maximo, requiere_lote, activo)
        VALUES
            (:sku, :nombre_producto, :descripcion, :id_categoria, :id_unidad,
             :stock_minimo, :stock_maximo, :requiere_lote, 1)
    """
    params = {
        "sku": sku,
        "nombre_producto": nombre_producto,
        "descripcion": descripcion,
        "id_categoria": id_categoria,
        "id_unidad": id_unidad,
        "stock_minimo": stock_minimo,
        "stock_maximo": stock_maximo,
        "requiere_lote": requiere_lote,
    }
    execute_statement(query, params)


def insert_zona(codigo_zona, nombre_zona, descripcion):
    query = """
        INSERT INTO zonas_almacen (codigo_zona, nombre_zona, descripcion, activo)
        VALUES (:codigo_zona, :nombre_zona, :descripcion, 1)
    """
    execute_statement(query, {
        "codigo_zona": codigo_zona,
        "nombre_zona": nombre_zona,
        "descripcion": descripcion,
    })


def insert_ubicacion(
    codigo_ubicacion,
    id_zona,
    tipo_ubicacion,
    pasillo,
    rack,
    nivel,
    posicion,
    capacidad_maxima,
):
    query = """
        INSERT INTO ubicaciones
            (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack,
             nivel, posicion, capacidad_maxima, activo)
        VALUES
            (:codigo_ubicacion, :id_zona, :tipo_ubicacion, :pasillo, :rack,
             :nivel, :posicion, :capacidad_maxima, 1)
    """
    execute_statement(query, {
        "codigo_ubicacion": codigo_ubicacion,
        "id_zona": id_zona,
        "tipo_ubicacion": tipo_ubicacion,
        "pasillo": pasillo,
        "rack": rack,
        "nivel": nivel,
        "posicion": posicion,
        "capacidad_maxima": capacidad_maxima,
    })


def insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo):
    query = """
        INSERT INTO cuentas_logisticas
            (codigo_cuenta, nombre_cuenta, responsable, centro_costo, activo)
        VALUES (:codigo_cuenta, :nombre_cuenta, :responsable, :centro_costo, 1)
    """
    execute_statement(query, {
        "codigo_cuenta": codigo_cuenta,
        "nombre_cuenta": nombre_cuenta,
        "responsable": responsable,
        "centro_costo": centro_costo,
    })
