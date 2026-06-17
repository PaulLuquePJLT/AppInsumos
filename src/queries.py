import pandas as pd
from sqlalchemy import text
from src.db import get_engine


def read_dataframe(query: str, params: dict | None = None) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve un DataFrame."""
    engine = get_engine()

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


def execute_statement(statement: str, params: dict | None = None) -> None:
    """Ejecuta un INSERT/UPDATE/DELETE y confirma la transacción."""
    # engine.begin() abre una transacción y hace commit automático al salir
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(statement), params or {})


def get_stock_general():
    return read_dataframe('SELECT * FROM vw_stock_general ORDER BY nombre_producto')


def get_stock_por_ubicacion():
    return read_dataframe('SELECT * FROM vw_stock_por_ubicacion ORDER BY nombre_producto, codigo_ubicacion')


def get_stock_por_cuenta():
    return read_dataframe('SELECT * FROM vw_stock_por_cuenta ORDER BY nombre_cuenta, nombre_producto')


def get_productos_activos():
    return read_dataframe('''
        SELECT id_producto, sku, nombre_producto
        FROM productos
        WHERE activo = 1
        ORDER BY nombre_producto
    ''')


def get_ubicaciones():
    return read_dataframe('''
        SELECT id_ubicacion, codigo_ubicacion, tipo_ubicacion, id_zona
        FROM ubicaciones
        WHERE activo = 1
        ORDER BY codigo_ubicacion
    ''')


def get_cuentas():
    return read_dataframe('''
        SELECT id_cuenta, codigo_cuenta, nombre_cuenta
        FROM cuentas_logisticas
        WHERE activo = 1
        ORDER BY nombre_cuenta
    ''')


def get_zonas():
    return read_dataframe('''
        SELECT id_zona, codigo_zona, nombre_zona, activo
        FROM zonas_almacen
        ORDER BY codigo_zona
    ''')


def get_categorias():
    return read_dataframe('''
        SELECT id_categoria, nombre_categoria
        FROM categorias_producto
        WHERE activo = 1
        ORDER BY nombre_categoria
    ''')


def get_unidades():
    return read_dataframe('''
        SELECT id_unidad, codigo_unidad, nombre_unidad
        FROM unidades_medida
        ORDER BY nombre_unidad
    ''')


def get_movimientos():
    return read_dataframe('SELECT * FROM vw_movimientos ORDER BY fecha_movimiento DESC')


def insert_producto(
    sku,
    nombre,
    descripcion,
    id_categoria,
    id_unidad,
    stock_minimo,
    stock_maximo,
    requiere_lote,
):
    """Inserta un nuevo producto."""
    query = """
    INSERT INTO productos
        (
            sku,
            nombre,
            descripcion,
            id_categoria,
            id_unidad,
            stock_minimo,
            stock_maximo,
            requiere_lote,
            activo
        )
    VALUES
        (
            :sku,
            :nombre,
            :descripcion,
            :id_categoria,
            :id_unidad,
            :stock_minimo,
            :stock_maximo,
            :requiere_lote,
            1
        )
    """  # Sin coma al final: debe ser un string, no una tupla

    params = {
        "sku": sku,
        "nombre": nombre,
        "descripcion": descripcion,
        "id_categoria": id_categoria,
        "id_unidad": id_unidad,
        "stock_minimo": stock_minimo,
        "stock_maximo": stock_maximo,
        "requiere_lote": requiere_lote,
    }

    execute_statement(query, params)


def insert_zona(codigo_zona, nombre_zona, descripcion):
    query = text('''
        INSERT INTO zonas_almacen (codigo_zona, nombre_zona, descripcion)
        VALUES (:codigo_zona, :nombre_zona, :descripcion)
    ''')
    execute_statement(query, {'codigo_zona': codigo_zona, 'nombre_zona': nombre_zona, 'descripcion': descripcion})


def insert_ubicacion(codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima):
    query = text('''
        INSERT INTO ubicaciones (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima)
        VALUES (:codigo_ubicacion, :id_zona, :tipo_ubicacion, :pasillo, :rack, :nivel, :posicion, :capacidad_maxima)
    ''')
    execute_statement(query, {
        'codigo_ubicacion': codigo_ubicacion,
        'id_zona': id_zona,
        'tipo_ubicacion': tipo_ubicacion,
        'pasillo': pasillo,
        'rack': rack,
        'nivel': nivel,
        'posicion': posicion,
        'capacidad_maxima': capacidad_maxima,
    })


def insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo):
    query = text('''
        INSERT INTO cuentas_logisticas (codigo_cuenta, nombre_cuenta, responsable, centro_costo)
        VALUES (:codigo_cuenta, :nombre_cuenta, :responsable, :centro_costo)
    ''')
    execute_statement(query, {
        'codigo_cuenta': codigo_cuenta,
        'nombre_cuenta': nombre_cuenta,
        'responsable': responsable,
        'centro_costo': centro_costo,
    })
