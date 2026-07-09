import pandas as pd
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from src.db import get_engine, run_db_with_retry


# ---------------------------------------------------------------------------
# Helpers base
# ---------------------------------------------------------------------------

def _ensure_text(statement):
    if isinstance(statement, TextClause):
        return statement

    if isinstance(statement, str):
        return text(statement)

    raise TypeError(f"El SQL debe ser str o text(), no {type(statement).__name__}")


def read_dataframe(query, params: dict | None = None) -> pd.DataFrame:
    sql = _ensure_text(query)

    def _op():
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params=params or {})

    return run_db_with_retry(_op)


def execute_statement(statement, params: dict | None = None) -> None:
    sql = _ensure_text(statement)

    def _op():
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, params or {})

    run_db_with_retry(_op)


def execute_many(statement, rows: list[dict]) -> None:
    if not rows:
        return

    sql = _ensure_text(statement)

    def _op():
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, rows)

    run_db_with_retry(_op)


def clean_text(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def clean_upper(value):
    return clean_text(value).upper()


def normalize_nullable_ean(value):
    """Devuelve None cuando el EAN está vacío.

    La restricción SQL CK_productos_ean_serie permite NULL o 13 dígitos,
    pero NO permite cadena vacía ''. Por eso todo EAN vacío debe viajar
    a Azure SQL como None/NULL.
    """
    value_text = clean_text(value)

    if value_text == "" or value_text.lower() in {"nan", "none", "null"}:
        return None

    # Si Excel lo leyera como número decimal, normalizar 775...0 -> 775...
    if value_text.endswith(".0"):
        maybe_int = value_text[:-2]
        if maybe_int.isdigit():
            return maybe_int

    return value_text


def clean_float(value, default=0.0):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return default

    return float(value)


def clean_bool(value) -> int:
    if value is None or pd.isna(value):
        return 0

    value_text = str(value).strip().lower()

    return 1 if value_text in {
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


# ---------------------------------------------------------------------------
# Consultas generales
# ---------------------------------------------------------------------------

def get_stock_general(sku: str = "", solo_con_stock: bool = True, max_rows: int | None = None):
    filters = []
    params: dict = {}

    if solo_con_stock:
        filters.append("""
            (
                ISNULL(cantidad_total, 0) > 0
                OR ISNULL(cantidad_en_picking, 0) > 0
                OR ISNULL(cantidad_en_ingreso, 0) > 0
                OR ISNULL(cantidad_disponible, 0) > 0
            )
        """)

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku

    top_sql = f"TOP ({int(max_rows)})" if max_rows else ""
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    return read_dataframe(f"""
        SELECT {top_sql}
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            stock_minimo,
            stock_maximo,
            ISNULL(precio_unitario, 0) AS precio_unitario,
            cantidad_total,
            ISNULL(cantidad_en_picking, 0) AS cantidad_en_picking,
            ISNULL(cantidad_en_ingreso, 0) AS cantidad_en_ingreso,
            ISNULL(cantidad_disponible, cantidad_total) AS cantidad_disponible,
            ISNULL(valor_stock_total, cantidad_total * ISNULL(precio_unitario, 0)) AS valor_stock_total,
            ISNULL(valor_stock_en_picking, ISNULL(cantidad_en_picking, 0) * ISNULL(precio_unitario, 0)) AS valor_stock_en_picking,
            ISNULL(valor_stock_en_ingreso, ISNULL(cantidad_en_ingreso, 0) * ISNULL(precio_unitario, 0)) AS valor_stock_en_ingreso,
            ISNULL(valor_stock_disponible, ISNULL(cantidad_disponible, cantidad_total) * ISNULL(precio_unitario, 0)) AS valor_stock_disponible
        FROM dbo.vw_stock_general
        {where_sql}
        ORDER BY nombre_producto
    """, params)

def get_stock_por_ubicacion(sku: str = "", ubicacion: str = "", zona: str = "", solo_con_stock: bool = True, max_rows: int | None = None):
    filters = []
    params: dict = {}

    if solo_con_stock:
        filters.append("""
            (
                ISNULL(cantidad_actual, 0) > 0
                OR ISNULL(cantidad_en_picking, 0) > 0
                OR ISNULL(cantidad_en_ingreso, 0) > 0
                OR ISNULL(cantidad_disponible, 0) > 0
            )
        """)

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku

    if ubicacion:
        filters.append("(codigo_ubicacion LIKE '%' + :ubicacion + '%' OR tipo_ubicacion LIKE '%' + :ubicacion + '%')")
        params["ubicacion"] = ubicacion

    if zona:
        filters.append("(codigo_zona LIKE '%' + :zona + '%' OR nombre_zona LIKE '%' + :zona + '%')")
        params["zona"] = zona

    top_sql = f"TOP ({int(max_rows)})" if max_rows else ""
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    return read_dataframe(f"""
        SELECT {top_sql}
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            codigo_zona,
            nombre_zona,
            id_ubicacion,
            codigo_ubicacion,
            tipo_ubicacion,
            ISNULL(secuencia, 999999) AS secuencia,
            ISNULL(es_surtible, 1) AS es_surtible,
            ISNULL(es_stage, 0) AS es_stage,
            lote,
            ISNULL(precio_unitario, 0) AS precio_unitario,
            cantidad_actual,
            ISNULL(cantidad_en_picking, 0) AS cantidad_en_picking,
            ISNULL(cantidad_en_ingreso, 0) AS cantidad_en_ingreso,
            ISNULL(cantidad_disponible, cantidad_actual) AS cantidad_disponible,
            ISNULL(valor_stock_actual, cantidad_actual * ISNULL(precio_unitario, 0)) AS valor_stock_actual,
            ISNULL(valor_stock_en_picking, ISNULL(cantidad_en_picking, 0) * ISNULL(precio_unitario, 0)) AS valor_stock_en_picking,
            ISNULL(valor_stock_en_ingreso, ISNULL(cantidad_en_ingreso, 0) * ISNULL(precio_unitario, 0)) AS valor_stock_en_ingreso,
            ISNULL(valor_stock_disponible, ISNULL(cantidad_disponible, cantidad_actual) * ISNULL(precio_unitario, 0)) AS valor_stock_disponible,
            fecha_actualizacion
        FROM dbo.vw_stock_por_ubicacion
        {where_sql}
        ORDER BY nombre_producto, secuencia, codigo_ubicacion
    """, params)

def aplicar_vencimientos_stock_cuenta() -> None:
    """Aplica descuentos de stock en cuenta por vida util vencida.

    Se ejecuta antes de consultar stock por cuenta para que la vista muestre
    saldos netos actualizados aun sin un job externo.
    """
    try:
        execute_statement("EXEC dbo.sp_aplicar_vencimientos_stock_cuenta")
    except Exception:
        # Evita romper consultas si la migracion aun no fue ejecutada.
        # Una vez aplicada database/014_..., el procedimiento quedara disponible.
        pass


def get_stock_por_cuenta(cuenta: str = "", sku: str = "", solo_con_stock: bool = True, max_rows: int | None = None):
    aplicar_vencimientos_stock_cuenta()
    filters = []
    params: dict = {}

    if solo_con_stock:
        filters.append("ISNULL(cantidad_neta, 0) > 0")

    if cuenta:
        filters.append("(codigo_cuenta LIKE '%' + :cuenta + '%' OR nombre_cuenta LIKE '%' + :cuenta + '%')")
        params["cuenta"] = cuenta

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku

    top_sql = f"TOP ({int(max_rows)})" if max_rows else ""
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    return read_dataframe(f"""
        SELECT {top_sql}
            id_cuenta,
            codigo_cuenta,
            nombre_cuenta,
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            ISNULL(precio_unitario, 0) AS precio_unitario,
            ISNULL(vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
            cantidad_entregada,
            cantidad_devuelta,
            ISNULL(cantidad_consumida_vida_util, 0) AS cantidad_consumida_vida_util,
            cantidad_neta,
            ISNULL(valor_stock_cuenta, cantidad_neta * ISNULL(precio_unitario, 0)) AS valor_stock_cuenta,
            fecha_actualizacion
        FROM dbo.vw_stock_por_cuenta
        {where_sql}
        ORDER BY nombre_cuenta, nombre_producto
    """, params)


def get_movimientos(fecha_inicio=None, fecha_fin=None, tipo_movimiento: str = "", cuenta: str = "", sku: str = ""):
    filters = [
        "fecha_movimiento IS NOT NULL",
        "NOT (tipo_movimiento = 'SALIDA_AJUSTE' AND ISNULL(referencia, '') LIKE 'CORTO PICKING%')",
    ]
    params = {}

    if fecha_inicio is not None:
        filters.append("fecha_movimiento >= CAST(:fecha_inicio AS date)")
        params["fecha_inicio"] = fecha_inicio
    
    if fecha_fin is not None:
        filters.append("fecha_movimiento < DATEADD(DAY, 1, CAST(:fecha_fin AS date))")
        params["fecha_fin"] = fecha_fin

    if tipo_movimiento:
        filters.append("tipo_movimiento = :tipo_movimiento")
        params["tipo_movimiento"] = tipo_movimiento

    if cuenta:
        filters.append("(codigo_cuenta LIKE '%' + :cuenta + '%' OR nombre_cuenta LIKE '%' + :cuenta + '%')")
        params["cuenta"] = cuenta

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku

    where_sql = " AND ".join(filters)
    return read_dataframe(f"""
        SELECT *
        FROM dbo.vw_movimientos
        WHERE {where_sql}
        ORDER BY fecha_movimiento DESC, id_movimiento DESC
    """, params)


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
# Productos
# ---------------------------------------------------------------------------

def get_productos_activos():
    return read_dataframe("""
        SELECT
            p.id_producto,
            p.sku,
            p.nombre_producto,
            p.descripcion,
            ISNULL(p.ean_serie, '') AS ean_serie,
            ISNULL(p.flag_aplica_ean, 'NO') AS flag_aplica_ean,
            ISNULL(p.precio_unitario, 0) AS precio_unitario,
            ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
            p.id_categoria,
            cp.nombre_categoria,
            p.id_unidad,
            um.codigo_unidad,
            um.nombre_unidad,
            p.stock_minimo,
            p.stock_maximo,
            p.requiere_lote,
            p.activo
        FROM productos p
        INNER JOIN categorias_producto cp ON cp.id_categoria = p.id_categoria
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        WHERE p.activo = 1
        ORDER BY p.nombre_producto
    """)


def get_productos_todos():
    return read_dataframe("""
        SELECT
            p.id_producto,
            p.sku,
            p.nombre_producto,
            p.descripcion,
            ISNULL(p.ean_serie, '') AS ean_serie,
            ISNULL(p.flag_aplica_ean, 'NO') AS flag_aplica_ean,
            ISNULL(p.precio_unitario, 0) AS precio_unitario,
            ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
            p.id_categoria,
            cp.nombre_categoria,
            p.id_unidad,
            um.codigo_unidad,
            um.nombre_unidad,
            p.stock_minimo,
            p.stock_maximo,
            p.requiere_lote,
            p.activo
        FROM productos p
        INNER JOIN categorias_producto cp ON cp.id_categoria = p.id_categoria
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        ORDER BY p.activo DESC, p.nombre_producto
    """)


def insert_producto(
    sku,
    nombre_producto,
    descripcion,
    id_categoria,
    id_unidad,
    stock_minimo,
    stock_maximo,
    requiere_lote,
    precio_unitario=0.0,
    ean_serie="",
    flag_aplica_ean="NO",
    vida_util_cuenta_dias=0,
):
    execute_statement(
        """
        INSERT INTO productos
            (
                sku,
                nombre_producto,
                descripcion,
                ean_serie,
                flag_aplica_ean,
                precio_unitario,
                vida_util_cuenta_dias,
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
                :nombre_producto,
                :descripcion,
                :ean_serie,
                :flag_aplica_ean,
                :precio_unitario,
                :vida_util_cuenta_dias,
                :id_categoria,
                :id_unidad,
                :stock_minimo,
                :stock_maximo,
                :requiere_lote,
                1
            )
        """,
        {
            "sku": clean_upper(sku),
            "nombre_producto": clean_text(nombre_producto),
            "descripcion": clean_text(descripcion),
            "ean_serie": normalize_nullable_ean(ean_serie),
            "flag_aplica_ean": clean_upper(flag_aplica_ean) if clean_upper(flag_aplica_ean) == "SI" else "NO",
            "precio_unitario": clean_float(precio_unitario),
            "vida_util_cuenta_dias": int(clean_float(vida_util_cuenta_dias, 0)),
            "id_categoria": int(id_categoria),
            "id_unidad": int(id_unidad),
            "stock_minimo": clean_float(stock_minimo),
            "stock_maximo": clean_float(stock_maximo, None),
            "requiere_lote": clean_bool(requiere_lote),
        },
    )


def update_producto(
    id_producto,
    sku,
    nombre_producto,
    descripcion,
    id_categoria,
    id_unidad,
    stock_minimo,
    stock_maximo,
    requiere_lote,
    activo=1,
    precio_unitario=0.0,
    ean_serie="",
    flag_aplica_ean="NO",
    vida_util_cuenta_dias=0,
):
    execute_statement(
        """
        UPDATE productos
        SET sku = :sku,
            nombre_producto = :nombre_producto,
            descripcion = :descripcion,
            ean_serie = :ean_serie,
            flag_aplica_ean = :flag_aplica_ean,
            precio_unitario = :precio_unitario,
            vida_util_cuenta_dias = :vida_util_cuenta_dias,
            id_categoria = :id_categoria,
            id_unidad = :id_unidad,
            stock_minimo = :stock_minimo,
            stock_maximo = :stock_maximo,
            requiere_lote = :requiere_lote,
            activo = :activo
        WHERE id_producto = :id_producto
        """,
        {
            "id_producto": int(id_producto),
            "sku": clean_upper(sku),
            "nombre_producto": clean_text(nombre_producto),
            "descripcion": clean_text(descripcion),
            "ean_serie": normalize_nullable_ean(ean_serie),
            "flag_aplica_ean": clean_upper(flag_aplica_ean) if clean_upper(flag_aplica_ean) == "SI" else "NO",
            "precio_unitario": clean_float(precio_unitario),
            "vida_util_cuenta_dias": int(clean_float(vida_util_cuenta_dias, 0)),
            "id_categoria": int(id_categoria),
            "id_unidad": int(id_unidad),
            "stock_minimo": clean_float(stock_minimo),
            "stock_maximo": clean_float(stock_maximo, None),
            "requiere_lote": clean_bool(requiere_lote),
            "activo": clean_bool(activo),
        },
    )


def delete_producto(id_producto):
    execute_statement(
        """
        UPDATE productos
        SET activo = 0
        WHERE id_producto = :id_producto
        """,
        {"id_producto": int(id_producto)},
    )


def bulk_insert_productos(rows: list[dict]):
    normalized_rows = []

    for row in rows:
        row_copy = dict(row)
        row_copy["ean_serie"] = normalize_nullable_ean(row_copy.get("ean_serie"))
        row_copy["flag_aplica_ean"] = "SI" if clean_upper(row_copy.get("flag_aplica_ean")) == "SI" else "NO"
        normalized_rows.append(row_copy)

    execute_many(
        """
        INSERT INTO productos
            (
                sku,
                nombre_producto,
                descripcion,
                ean_serie,
                flag_aplica_ean,
                precio_unitario,
                vida_util_cuenta_dias,
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
                :nombre_producto,
                :descripcion,
                :ean_serie,
                :flag_aplica_ean,
                :precio_unitario,
                :vida_util_cuenta_dias,
                :id_categoria,
                :id_unidad,
                :stock_minimo,
                :stock_maximo,
                :requiere_lote,
                1
            )
        """,
        normalized_rows,
    )


# ---------------------------------------------------------------------------
# Zonas
# ---------------------------------------------------------------------------

def get_zonas():
    return read_dataframe("""
        SELECT
            id_zona,
            codigo_zona,
            nombre_zona,
            descripcion,
            activo
        FROM zonas_almacen
        WHERE activo = 1
        ORDER BY codigo_zona
    """)


def get_zonas_todas():
    return read_dataframe("""
        SELECT
            id_zona,
            codigo_zona,
            nombre_zona,
            descripcion,
            activo
        FROM zonas_almacen
        ORDER BY activo DESC, codigo_zona
    """)


def insert_zona(codigo_zona, nombre_zona, descripcion):
    execute_statement(
        """
        INSERT INTO zonas_almacen
            (
                codigo_zona,
                nombre_zona,
                descripcion,
                activo
            )
        VALUES
            (
                :codigo_zona,
                :nombre_zona,
                :descripcion,
                1
            )
        """,
        {
            "codigo_zona": clean_upper(codigo_zona),
            "nombre_zona": clean_text(nombre_zona),
            "descripcion": clean_text(descripcion),
        },
    )


def update_zona(id_zona, codigo_zona, nombre_zona, descripcion, activo=1):
    execute_statement(
        """
        UPDATE zonas_almacen
        SET codigo_zona = :codigo_zona,
            nombre_zona = :nombre_zona,
            descripcion = :descripcion,
            activo = :activo
        WHERE id_zona = :id_zona
        """,
        {
            "id_zona": int(id_zona),
            "codigo_zona": clean_upper(codigo_zona),
            "nombre_zona": clean_text(nombre_zona),
            "descripcion": clean_text(descripcion),
            "activo": clean_bool(activo),
        },
    )


def delete_zona(id_zona):
    execute_statement(
        """
        UPDATE zonas_almacen
        SET activo = 0
        WHERE id_zona = :id_zona
        """,
        {"id_zona": int(id_zona)},
    )


def bulk_insert_zonas(rows: list[dict]):
    execute_many(
        """
        INSERT INTO zonas_almacen
            (
                codigo_zona,
                nombre_zona,
                descripcion,
                activo
            )
        VALUES
            (
                :codigo_zona,
                :nombre_zona,
                :descripcion,
                1
            )
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# Ubicaciones
# ---------------------------------------------------------------------------

def get_ubicaciones():
    return read_dataframe("""
        SELECT
            ub.id_ubicacion,
            ub.codigo_ubicacion,
            ub.id_zona,
            z.codigo_zona,
            z.nombre_zona,
            ub.tipo_ubicacion,
            ub.pasillo,
            ub.rack,
            ub.nivel,
            ub.posicion,
            ub.capacidad_maxima,
            ISNULL(ub.secuencia, 999999) AS secuencia,
            ISNULL(ub.es_surtible, 1) AS es_surtible,
            ISNULL(ub.es_stage, 0) AS es_stage,
            ub.activo
        FROM ubicaciones ub
        INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona
        WHERE ub.activo = 1
        ORDER BY ISNULL(ub.secuencia, 999999), ub.codigo_ubicacion
    """)


def get_ubicaciones_todas():
    return read_dataframe("""
        SELECT
            ub.id_ubicacion,
            ub.codigo_ubicacion,
            ub.id_zona,
            z.codigo_zona,
            z.nombre_zona,
            ub.tipo_ubicacion,
            ub.pasillo,
            ub.rack,
            ub.nivel,
            ub.posicion,
            ub.capacidad_maxima,
            ISNULL(ub.secuencia, 999999) AS secuencia,
            ISNULL(ub.es_surtible, 1) AS es_surtible,
            ISNULL(ub.es_stage, 0) AS es_stage,
            ub.activo
        FROM ubicaciones ub
        INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona
        ORDER BY ub.activo DESC, ISNULL(ub.secuencia, 999999), ub.codigo_ubicacion
    """)


def insert_ubicacion(
    codigo_ubicacion,
    id_zona,
    tipo_ubicacion,
    pasillo,
    rack,
    nivel,
    posicion,
    capacidad_maxima,
    secuencia=999999,
    es_surtible=1,
    es_stage=0,
):
    execute_statement(
        """
        INSERT INTO ubicaciones
            (
                codigo_ubicacion,
                id_zona,
                tipo_ubicacion,
                pasillo,
                rack,
                nivel,
                posicion,
                capacidad_maxima,
                secuencia,
                es_surtible,
                es_stage,
                activo
            )
        VALUES
            (
                :codigo_ubicacion,
                :id_zona,
                :tipo_ubicacion,
                :pasillo,
                :rack,
                :nivel,
                :posicion,
                :capacidad_maxima,
                :secuencia,
                :es_surtible,
                :es_stage,
                1
            )
        """,
        {
            "codigo_ubicacion": clean_upper(codigo_ubicacion),
            "id_zona": int(id_zona),
            "tipo_ubicacion": clean_text(tipo_ubicacion),
            "pasillo": clean_text(pasillo),
            "rack": clean_text(rack),
            "nivel": clean_text(nivel),
            "posicion": clean_text(posicion),
            "capacidad_maxima": clean_float(capacidad_maxima, None),
            "secuencia": int(clean_float(secuencia, 999999)),
            "es_surtible": clean_bool(es_surtible),
            "es_stage": clean_bool(es_stage),
        },
    )


def update_ubicacion(
    id_ubicacion,
    codigo_ubicacion,
    id_zona,
    tipo_ubicacion,
    pasillo,
    rack,
    nivel,
    posicion,
    capacidad_maxima,
    secuencia=999999,
    es_surtible=1,
    es_stage=0,
    activo=1,
):
    execute_statement(
        """
        UPDATE ubicaciones
        SET codigo_ubicacion = :codigo_ubicacion,
            id_zona = :id_zona,
            tipo_ubicacion = :tipo_ubicacion,
            pasillo = :pasillo,
            rack = :rack,
            nivel = :nivel,
            posicion = :posicion,
            capacidad_maxima = :capacidad_maxima,
            secuencia = :secuencia,
            es_surtible = :es_surtible,
            es_stage = :es_stage,
            activo = :activo
        WHERE id_ubicacion = :id_ubicacion
        """,
        {
            "id_ubicacion": int(id_ubicacion),
            "codigo_ubicacion": clean_upper(codigo_ubicacion),
            "id_zona": int(id_zona),
            "tipo_ubicacion": clean_text(tipo_ubicacion),
            "pasillo": clean_text(pasillo),
            "rack": clean_text(rack),
            "nivel": clean_text(nivel),
            "posicion": clean_text(posicion),
            "capacidad_maxima": clean_float(capacidad_maxima, None),
            "secuencia": int(clean_float(secuencia, 999999)),
            "es_surtible": clean_bool(es_surtible),
            "es_stage": clean_bool(es_stage),
            "activo": clean_bool(activo),
        },
    )


def delete_ubicacion(id_ubicacion):
    execute_statement(
        """
        UPDATE ubicaciones
        SET activo = 0
        WHERE id_ubicacion = :id_ubicacion
        """,
        {"id_ubicacion": int(id_ubicacion)},
    )


def bulk_insert_ubicaciones(rows: list[dict]):
    execute_many(
        """
        INSERT INTO ubicaciones
            (
                codigo_ubicacion,
                id_zona,
                tipo_ubicacion,
                pasillo,
                rack,
                nivel,
                posicion,
                capacidad_maxima,
                secuencia,
                es_surtible,
                es_stage,
                activo
            )
        VALUES
            (
                :codigo_ubicacion,
                :id_zona,
                :tipo_ubicacion,
                :pasillo,
                :rack,
                :nivel,
                :posicion,
                :capacidad_maxima,
                :secuencia,
                :es_surtible,
                :es_stage,
                1
            )
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# Cuentas o áreas logísticas
# ---------------------------------------------------------------------------

def get_cuentas():
    return read_dataframe("""
        SELECT
            id_cuenta,
            codigo_cuenta,
            nombre_cuenta,
            responsable,
            centro_costo,
            activo
        FROM cuentas_logisticas
        WHERE activo = 1
        ORDER BY nombre_cuenta
    """)


def get_cuentas_todas():
    return read_dataframe("""
        SELECT
            id_cuenta,
            codigo_cuenta,
            nombre_cuenta,
            responsable,
            centro_costo,
            activo
        FROM cuentas_logisticas
        ORDER BY activo DESC, nombre_cuenta
    """)


def insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo):
    execute_statement(
        """
        INSERT INTO cuentas_logisticas
            (
                codigo_cuenta,
                nombre_cuenta,
                responsable,
                centro_costo,
                activo
            )
        VALUES
            (
                :codigo_cuenta,
                :nombre_cuenta,
                :responsable,
                :centro_costo,
                1
            )
        """,
        {
            "codigo_cuenta": clean_upper(codigo_cuenta),
            "nombre_cuenta": clean_text(nombre_cuenta),
            "responsable": clean_text(responsable),
            "centro_costo": clean_upper(centro_costo),
        },
    )


def update_cuenta(
    id_cuenta,
    codigo_cuenta,
    nombre_cuenta,
    responsable,
    centro_costo,
    activo=1,
):
    execute_statement(
        """
        UPDATE cuentas_logisticas
        SET codigo_cuenta = :codigo_cuenta,
            nombre_cuenta = :nombre_cuenta,
            responsable = :responsable,
            centro_costo = :centro_costo,
            activo = :activo
        WHERE id_cuenta = :id_cuenta
        """,
        {
            "id_cuenta": int(id_cuenta),
            "codigo_cuenta": clean_upper(codigo_cuenta),
            "nombre_cuenta": clean_text(nombre_cuenta),
            "responsable": clean_text(responsable),
            "centro_costo": clean_upper(centro_costo),
            "activo": clean_bool(activo),
        },
    )


def delete_cuenta(id_cuenta):
    execute_statement(
        """
        UPDATE cuentas_logisticas
        SET activo = 0
        WHERE id_cuenta = :id_cuenta
        """,
        {"id_cuenta": int(id_cuenta)},
    )


def bulk_insert_cuentas(rows: list[dict]):
    execute_many(
        """
        INSERT INTO cuentas_logisticas
            (
                codigo_cuenta,
                nombre_cuenta,
                responsable,
                centro_costo,
                activo
            )
        VALUES
            (
                :codigo_cuenta,
                :nombre_cuenta,
                :responsable,
                :centro_costo,
                1
            )
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------

def get_categorias():
    return read_dataframe("""
        SELECT
            id_categoria,
            nombre_categoria,
            descripcion,
            activo
        FROM categorias_producto
        WHERE activo = 1
        ORDER BY nombre_categoria
    """)


def get_categorias_todas():
    return read_dataframe("""
        SELECT
            id_categoria,
            nombre_categoria,
            descripcion,
            activo
        FROM categorias_producto
        ORDER BY activo DESC, nombre_categoria
    """)


def insert_categoria(nombre_categoria, descripcion):
    execute_statement(
        """
        INSERT INTO categorias_producto
            (
                nombre_categoria,
                descripcion,
                activo
            )
        VALUES
            (
                :nombre_categoria,
                :descripcion,
                1
            )
        """,
        {
            "nombre_categoria": clean_text(nombre_categoria),
            "descripcion": clean_text(descripcion),
        },
    )


def update_categoria(id_categoria, nombre_categoria, descripcion, activo=1):
    execute_statement(
        """
        UPDATE categorias_producto
        SET nombre_categoria = :nombre_categoria,
            descripcion = :descripcion,
            activo = :activo
        WHERE id_categoria = :id_categoria
        """,
        {
            "id_categoria": int(id_categoria),
            "nombre_categoria": clean_text(nombre_categoria),
            "descripcion": clean_text(descripcion),
            "activo": clean_bool(activo),
        },
    )


def delete_categoria(id_categoria):
    execute_statement(
        """
        UPDATE categorias_producto
        SET activo = 0
        WHERE id_categoria = :id_categoria
        """,
        {"id_categoria": int(id_categoria)},
    )


def bulk_insert_categorias(rows: list[dict]):
    execute_many(
        """
        INSERT INTO categorias_producto
            (
                nombre_categoria,
                descripcion,
                activo
            )
        VALUES
            (
                :nombre_categoria,
                :descripcion,
                1
            )
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# Unidades de medida
# ---------------------------------------------------------------------------

def get_unidades():
    return read_dataframe("""
        SELECT
            id_unidad,
            codigo_unidad,
            nombre_unidad,
            activo
        FROM unidades_medida
        WHERE activo = 1
        ORDER BY nombre_unidad
    """)


def get_unidades_todas():
    return read_dataframe("""
        SELECT
            id_unidad,
            codigo_unidad,
            nombre_unidad,
            activo
        FROM unidades_medida
        ORDER BY activo DESC, nombre_unidad
    """)


def insert_unidad(codigo_unidad, nombre_unidad):
    execute_statement(
        """
        INSERT INTO unidades_medida
            (
                codigo_unidad,
                nombre_unidad,
                activo
            )
        VALUES
            (
                :codigo_unidad,
                :nombre_unidad,
                1
            )
        """,
        {
            "codigo_unidad": clean_upper(codigo_unidad),
            "nombre_unidad": clean_text(nombre_unidad),
        },
    )


def update_unidad(id_unidad, codigo_unidad, nombre_unidad, activo=1):
    execute_statement(
        """
        UPDATE unidades_medida
        SET codigo_unidad = :codigo_unidad,
            nombre_unidad = :nombre_unidad,
            activo = :activo
        WHERE id_unidad = :id_unidad
        """,
        {
            "id_unidad": int(id_unidad),
            "codigo_unidad": clean_upper(codigo_unidad),
            "nombre_unidad": clean_text(nombre_unidad),
            "activo": clean_bool(activo),
        },
    )


def delete_unidad(id_unidad):
    execute_statement(
        """
        UPDATE unidades_medida
        SET activo = 0
        WHERE id_unidad = :id_unidad
        """,
        {"id_unidad": int(id_unidad)},
    )


def bulk_insert_unidades(rows: list[dict]):
    execute_many(
        """
        INSERT INTO unidades_medida
            (
                codigo_unidad,
                nombre_unidad,
                activo
            )
        VALUES
            (
                :codigo_unidad,
                :nombre_unidad,
                1
            )
        """,
        rows,
    )

# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------

def get_proveedores():
    return read_dataframe("""
        SELECT
            id_proveedor,
            ruc,
            razon_social,
            rubro_proveedor,
            contacto,
            nro_telefono,
            correo,
            direccion,
            pais,
            ciudad,
            estado,
            activo,
            fecha_creacion,
            fecha_actualizacion
        FROM proveedores
        WHERE activo = 1
          AND estado <> 'INACTIVO'
        ORDER BY razon_social
    """)


def get_proveedores_todos():
    return read_dataframe("""
        SELECT
            id_proveedor,
            ruc,
            razon_social,
            rubro_proveedor,
            contacto,
            nro_telefono,
            correo,
            direccion,
            pais,
            ciudad,
            estado,
            activo,
            fecha_creacion,
            fecha_actualizacion
        FROM proveedores
        ORDER BY activo DESC, razon_social
    """)


def insert_proveedor(
    ruc,
    razon_social,
    rubro_proveedor,
    contacto,
    nro_telefono,
    correo,
    direccion,
    pais,
    ciudad,
    estado="ACTIVO",
):
    execute_statement(
        """
        INSERT INTO proveedores
            (
                ruc,
                razon_social,
                rubro_proveedor,
                contacto,
                nro_telefono,
                correo,
                direccion,
                pais,
                ciudad,
                estado,
                activo
            )
        VALUES
            (
                :ruc,
                :razon_social,
                :rubro_proveedor,
                :contacto,
                :nro_telefono,
                :correo,
                :direccion,
                :pais,
                :ciudad,
                :estado,
                CASE WHEN :estado = 'INACTIVO' THEN 0 ELSE 1 END
            )
        """,
        {
            "ruc": clean_upper(ruc),
            "razon_social": clean_text(razon_social),
            "rubro_proveedor": clean_text(rubro_proveedor),
            "contacto": clean_text(contacto),
            "nro_telefono": clean_text(nro_telefono),
            "correo": clean_text(correo).lower(),
            "direccion": clean_text(direccion),
            "pais": clean_text(pais),
            "ciudad": clean_text(ciudad),
            "estado": clean_upper(estado or "ACTIVO"),
        },
    )


def update_proveedor(
    id_proveedor,
    ruc,
    razon_social,
    rubro_proveedor,
    contacto,
    nro_telefono,
    correo,
    direccion,
    pais,
    ciudad,
    estado="ACTIVO",
    activo=1,
):
    execute_statement(
        """
        UPDATE proveedores
        SET ruc = :ruc,
            razon_social = :razon_social,
            rubro_proveedor = :rubro_proveedor,
            contacto = :contacto,
            nro_telefono = :nro_telefono,
            correo = :correo,
            direccion = :direccion,
            pais = :pais,
            ciudad = :ciudad,
            estado = :estado,
            activo = :activo,
            fecha_actualizacion = dbo.fn_now_bogota_lima()
        WHERE id_proveedor = :id_proveedor
        """,
        {
            "id_proveedor": int(id_proveedor),
            "ruc": clean_upper(ruc),
            "razon_social": clean_text(razon_social),
            "rubro_proveedor": clean_text(rubro_proveedor),
            "contacto": clean_text(contacto),
            "nro_telefono": clean_text(nro_telefono),
            "correo": clean_text(correo).lower(),
            "direccion": clean_text(direccion),
            "pais": clean_text(pais),
            "ciudad": clean_text(ciudad),
            "estado": clean_upper(estado or "ACTIVO"),
            "activo": clean_bool(activo),
        },
    )


def delete_proveedor(id_proveedor):
    execute_statement(
        """
        UPDATE proveedores
        SET activo = 0,
            estado = 'INACTIVO',
            fecha_actualizacion = dbo.fn_now_bogota_lima()
        WHERE id_proveedor = :id_proveedor
        """,
        {"id_proveedor": int(id_proveedor)},
    )


def bulk_insert_proveedores(rows: list[dict]):
    execute_many(
        """
        INSERT INTO proveedores
            (
                ruc,
                razon_social,
                rubro_proveedor,
                contacto,
                nro_telefono,
                correo,
                direccion,
                pais,
                ciudad,
                estado,
                activo
            )
        VALUES
            (
                :ruc,
                :razon_social,
                :rubro_proveedor,
                :contacto,
                :nro_telefono,
                :correo,
                :direccion,
                :pais,
                :ciudad,
                :estado,
                CASE WHEN :estado = 'INACTIVO' THEN 0 ELSE 1 END
            )
        """,
        rows,
    )


# ---------------------------------------------------------------------------
# Pedidos, Picking y Transferencias masivas
# ---------------------------------------------------------------------------

def get_next_pedido_number():
    value = read_dataframe("""
        SELECT ISNULL(MAX(TRY_CAST(SUBSTRING(nro_pedido, 2, 9) AS INT)), 0) + 1 AS next_number
        FROM pedidos
        WHERE nro_pedido LIKE 'P[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
    """)
    next_number = int(value["next_number"].iloc[0]) if not value.empty else 1
    return f"P{next_number:09d}"


def get_next_picking_number():
    value = read_dataframe("""
        SELECT ISNULL(MAX(TRY_CAST(SUBSTRING(nro_picking, 3, 9) AS INT)), 0) + 1 AS next_number
        FROM picking_header
        WHERE nro_picking LIKE 'PK[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
    """)
    next_number = int(value["next_number"].iloc[0]) if not value.empty else 1
    return f"PK{next_number:09d}"


def get_pedidos_resumen(
    solo_hoy: bool = False,
    solo_creados: bool = False,
    fecha_inicio=None,
    fecha_fin=None,
    estado: str | None = None,
):
    """Consulta resumen de pedidos directamente desde tablas.

    Evita depender de una vista que puede estar desactualizada y usa filtros
    de fecha consistentes con Bogotá/Lima.
    """
    where = []
    params = {}

    if solo_hoy:
        where.append("p.fecha_pedido = CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), '-05:00') AS DATE)")
    else:
        if fecha_inicio is not None:
            where.append("p.fecha_pedido >= :fecha_inicio")
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin is not None:
            where.append("p.fecha_pedido <= :fecha_fin")
            params["fecha_fin"] = fecha_fin

    if solo_creados:
        where.append("p.estado = 'CREADO'")
    elif estado:
        where.append("p.estado = :estado")
        params["estado"] = estado

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    return read_dataframe(f"""
        SELECT
            p.id_pedido,
            p.nro_pedido,
            p.fecha_pedido,
            p.fecha_esperada_atencion,
            p.id_cuenta,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.solicitante,
            p.responsable_cuenta,
            p.texto_cabecera,
            CAST(ISNULL(SUM(pd.cantidad_pedida), 0) AS DECIMAL(18,2)) AS qty_total,
            p.estado,
            COUNT(pd.id_pedido_detalle) AS lineas,
            CAST(ISNULL(SUM(pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada), 0) AS DECIMAL(18,2)) AS cantidad_pendiente_picking,
            CAST(ISNULL(SUM(pd.cantidad_asignada - pd.cantidad_atendida - pd.cantidad_cancelada), 0) AS DECIMAL(18,2)) AS cantidad_pendiente_atencion,
            CASE
                WHEN ISNULL(SUM(pd.cantidad_atendida), 0) > 0
                     AND ISNULL(SUM(pd.cantidad_pedida - pd.cantidad_cancelada), 0) <= ISNULL(SUM(pd.cantidad_atendida), 0)
                    THEN 'Atendido'
                WHEN ISNULL(SUM(pd.cantidad_atendida), 0) > 0
                    THEN 'Atendido parcial'
                ELSE 'No atendido'
            END AS estado_atencion,
            CASE
                WHEN ISNULL(SUM(CASE WHEN pd.estado = 'CORTO' THEN 1 ELSE 0 END), 0) > 0 THEN 'Corto pendiente'
                WHEN ISNULL(SUM(pd.cantidad_cancelada), 0) > 0 THEN 'Corto cancelado'
                WHEN ISNULL(SUM(pd.cantidad_atendida), 0) = 0 THEN 'Sin atención registrada'
                ELSE ''
            END AS motivo_no_atendido
        FROM pedidos p
        INNER JOIN cuentas_logisticas c ON c.id_cuenta = p.id_cuenta
        LEFT JOIN pedido_detalle pd ON pd.id_pedido = p.id_pedido
        {where_sql}
        GROUP BY
            p.id_pedido,
            p.nro_pedido,
            p.fecha_pedido,
            p.fecha_esperada_atencion,
            p.id_cuenta,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.solicitante,
            p.responsable_cuenta,
            p.texto_cabecera,
            p.estado
        ORDER BY p.fecha_pedido DESC, p.nro_pedido DESC
    """, params)


def get_pedidos_pendientes_detalle(solo_hoy: bool = True, fecha_inicio=None, fecha_fin=None):
    where = []
    params = {}
    if solo_hoy:
        where.append("p.fecha_pedido = CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), '-05:00') AS DATE)")
    else:
        if fecha_inicio is not None:
            where.append("p.fecha_pedido >= :fecha_inicio")
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin is not None:
            where.append("p.fecha_pedido <= :fecha_fin")
            params["fecha_fin"] = fecha_fin
    date_filter = "AND " + " AND ".join(where) if where else ""
    return read_dataframe(f"""
        SELECT
            p.id_pedido,
            p.nro_pedido,
            p.fecha_pedido,
            p.fecha_esperada_atencion,
            p.estado AS estado_pedido,
            c.id_cuenta,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.solicitante,
            pd.id_pedido_detalle,
            pd.nro_linea,
            pr.id_producto,
            pr.sku,
            pr.nombre_producto,
            pd.codigo_unidad,
            pd.cantidad_pedida,
            pd.cantidad_asignada,
            pd.cantidad_atendida,
            pd.cantidad_cancelada,
            CAST(pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada AS DECIMAL(18,2)) AS cantidad_pendiente_picking,
            pd.texto_item,
            pd.estado AS estado_detalle
        FROM pedidos p
        INNER JOIN pedido_detalle pd ON pd.id_pedido = p.id_pedido
        INNER JOIN productos pr ON pr.id_producto = pd.id_producto
        INNER JOIN cuentas_logisticas c ON c.id_cuenta = p.id_cuenta
        WHERE p.estado = 'CREADO'
          AND pd.estado = 'PENDIENTE'
          AND (pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada) > 0
          {date_filter}
        ORDER BY p.fecha_pedido DESC, p.nro_pedido, pd.nro_linea
    """, params)


def get_pedido_detalle(id_pedido: int):
    return read_dataframe(
        """
        SELECT
            pd.id_pedido_detalle,
            pd.id_pedido,
            pd.nro_linea,
            p.sku,
            p.nombre_producto,
            pd.codigo_unidad,
            pd.cantidad_pedida,
            pd.cantidad_asignada,
            pd.cantidad_atendida,
            pd.cantidad_cancelada,
            pd.texto_item,
            pd.estado
        FROM pedido_detalle pd
        INNER JOIN productos p ON p.id_producto = pd.id_producto
        WHERE pd.id_pedido = :id_pedido
        ORDER BY pd.nro_linea
        """,
        {"id_pedido": int(id_pedido)},
    )


def get_pickings_resumen(fecha_inicio=None, fecha_fin=None, estado: str = ""):
    filters = []
    params = {}

    if fecha_inicio is not None:
        filters.append("fecha_creacion >= CAST(:fecha_inicio AS date)")
        params["fecha_inicio"] = fecha_inicio
    
    if fecha_fin is not None:
        filters.append("fecha_creacion < DATEADD(DAY, 1, CAST(:fecha_fin AS date))")
        params["fecha_fin"] = fecha_fin

    if estado:
        filters.append("estado = :estado")
        params["estado"] = estado

    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    return read_dataframe(f"""
        SELECT
            id_picking,
            nro_picking,
            fecha_creacion,
            estado,
            ISNULL(origen_atencion, 'DESKTOP') AS origen_atencion,
            ISNULL(requiere_aprobacion_admin, 0) AS requiere_aprobacion_admin,
            ISNULL(estado_aprobacion_admin, 'NO_REQUIERE') AS estado_aprobacion_admin,
            usuario_creacion,
            usuario_aprobacion,
            fecha_aprobacion,
            qty_total,
            qty_asignada,
            qty_corto,
            pedidos,
            tareas_pendientes,
            cortos_activos,
            cortos_cancelados,
            tareas_completadas
        FROM dbo.vw_picking_resumen
        {where_sql}
        ORDER BY fecha_creacion DESC, nro_picking DESC
    """, params)


def get_picking_detalle(id_picking: int | None = None):
    where = "WHERE pd.id_picking = :id_picking" if id_picking else ""
    params = {"id_picking": int(id_picking)} if id_picking else {}
    return read_dataframe(
        f"""
        SELECT
            pd.id_picking_detalle,
            ph.nro_picking,
            ph.estado AS estado_picking,
            pd.nro_pedido,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.sku,
            p.nombre_producto,
            um.codigo_unidad,
            ub.codigo_ubicacion AS ubicacion_origen,
            pd.lote,
            pd.cantidad_solicitada,
            pd.cantidad_asignada,
            pd.cantidad_atendida,
            pd.cantidad_cancelada,
            pd.estado,
            pd.secuencia,
            pd.texto_item,
            pd.fecha_creacion
        FROM picking_detalle pd
        INNER JOIN picking_header ph ON ph.id_picking = pd.id_picking
        INNER JOIN productos p ON p.id_producto = pd.id_producto
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        INNER JOIN cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
        LEFT JOIN ubicaciones ub ON ub.id_ubicacion = pd.id_ubicacion_origen
        {where}
        ORDER BY ph.fecha_creacion DESC, ph.nro_picking DESC, pd.secuencia, pd.nro_pedido, p.sku
        """,
        params,
    )


def get_picking_cortos(activos_only: bool = True, fecha_inicio=None, fecha_fin=None):
    filters = ["pd.estado = 'CORTO'" if activos_only else "pd.estado IN ('CORTO','CANCELADO','REASIGNADO')"]
    params: dict = {}

    if fecha_inicio is not None:
        filters.append("ph.fecha_creacion >= CAST(:fecha_inicio AS date)")
        params["fecha_inicio"] = fecha_inicio

    if fecha_fin is not None:
        filters.append("ph.fecha_creacion < DATEADD(DAY, 1, CAST(:fecha_fin AS date))")
        params["fecha_fin"] = fecha_fin

    where_sql = " AND ".join(filters)

    return read_dataframe(f"""
        SELECT
            pd.id_picking_detalle,
            pd.id_picking,
            ph.nro_picking,
            ph.fecha_creacion,
            ph.estado AS estado_picking,
            pd.id_pedido,
            pd.nro_pedido,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.sku,
            p.nombre_producto,
            um.codigo_unidad,
            pd.cantidad_solicitada AS cantidad_corta,
            pd.estado,
            pd.texto_item,
            pd.fecha_creacion AS fecha_creacion_detalle
        FROM picking_detalle pd
        INNER JOIN picking_header ph ON ph.id_picking = pd.id_picking
        INNER JOIN productos p ON p.id_producto = pd.id_producto
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        INNER JOIN cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
        WHERE {where_sql}
        ORDER BY ph.fecha_creacion DESC, ph.nro_picking DESC, p.sku
    """, params)


def get_tareas_picking_pendientes():
    return read_dataframe("""
        SELECT
            CAST(0 AS BIT) AS seleccionar,
            pd.id_picking_detalle,
            pd.id_picking,
            ph.nro_picking,
            ph.estado AS estado_picking,
            pd.nro_pedido,
            c.codigo_cuenta,
            c.nombre_cuenta,
            p.sku,
            p.nombre_producto,
            um.codigo_unidad,
            ub.codigo_ubicacion AS ubicacion_origen,
            pd.lote,
            pd.cantidad_asignada,
            pd.secuencia,
            pd.texto_item,
            pd.fecha_creacion
        FROM picking_detalle pd
        INNER JOIN picking_header ph ON ph.id_picking = pd.id_picking
        INNER JOIN productos p ON p.id_producto = pd.id_producto
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        INNER JOIN cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
        INNER JOIN ubicaciones ub ON ub.id_ubicacion = pd.id_ubicacion_origen
        WHERE pd.estado = 'LIBERADO'
          AND ph.estado IN ('LIBERADO','LIBERADO-CORTO','COMPLETADO-PARCIAL')
        ORDER BY pd.secuencia, ub.codigo_ubicacion, ph.nro_picking, pd.nro_pedido, p.sku
    """)



def get_pickings_rf_pendientes_aprobacion():
    """Pickings RF con movimientos SALIDA_CUENTA pendientes de aprobación.

    Importante: la visibilidad se basa en los movimientos reales en estado
    PENDIENTE_APROBACION. Esto cubre casos donde el header quedó con estado
    desactualizado o incluso marcado como APROBADO por una aprobación parcial
    anterior, pero todavía existen movimientos pendientes y stock en B1.ST.01.
    """
    return read_dataframe("""
        WITH pend_mov AS (
            SELECT
                REPLACE(m.referencia, 'PICKING ', '') AS nro_picking,
                COUNT(DISTINCT m.id_movimiento) AS movimientos_pendientes,
                CAST(SUM(ISNULL(md.cantidad, 0)) AS DECIMAL(18,2)) AS cantidad_pendiente_aprobacion
            FROM dbo.movimientos m
            INNER JOIN dbo.movimiento_detalle md ON md.id_movimiento = m.id_movimiento
            WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
              AND m.estado = 'PENDIENTE_APROBACION'
              AND m.referencia LIKE 'PICKING %'
            GROUP BY REPLACE(m.referencia, 'PICKING ', '')
        ),
        cortos AS (
            SELECT
                id_picking,
                COUNT(1) AS cortos_pendientes,
                CAST(SUM(ISNULL(cantidad_solicitada, 0)) AS DECIMAL(18,2)) AS cantidad_corta_pendiente
            FROM dbo.picking_detalle
            WHERE estado = 'CORTO'
            GROUP BY id_picking
        ),
        liberadas AS (
            SELECT
                id_picking,
                COUNT(1) AS tareas_liberadas_pendientes
            FROM dbo.picking_detalle
            WHERE estado = 'LIBERADO'
            GROUP BY id_picking
        )
        SELECT
            CAST(0 AS BIT) AS seleccionar,
            ph.id_picking,
            ph.nro_picking,
            ph.fecha_creacion,
            ph.fecha_actualizacion,
            ph.estado,
            ISNULL(ph.origen_atencion, 'RF') AS origen_atencion,
            CASE
                WHEN ISNULL(pm.movimientos_pendientes, 0) > 0 THEN 'PENDIENTE'
                ELSE ISNULL(ph.estado_aprobacion_admin, 'PENDIENTE')
            END AS estado_aprobacion_admin,
            uc.usuario_login AS usuario_atencion,
            COUNT(DISTINCT pp.id_pedido) AS pedidos,
            STRING_AGG(CONVERT(NVARCHAR(MAX), ped.nro_pedido), ', ') AS nro_pedidos,
            MIN(c.codigo_cuenta) AS codigo_cuenta,
            MIN(c.nombre_cuenta) AS nombre_cuenta,
            CAST(SUM(CASE WHEN pd.estado = 'COMPLETADO' THEN ISNULL(pd.cantidad_atendida, 0) ELSE 0 END) AS DECIMAL(18,2)) AS cantidad_atendida,
            COUNT(CASE WHEN pd.estado = 'COMPLETADO' THEN 1 END) AS tareas_completadas,
            ISNULL(MAX(co.cortos_pendientes), 0) AS cortos_pendientes,
            ISNULL(MAX(co.cantidad_corta_pendiente), 0) AS cantidad_corta_pendiente,
            ISNULL(MAX(lb.tareas_liberadas_pendientes), 0) AS tareas_liberadas_pendientes,
            COUNT(DISTINCT pd.id_producto) AS codigos,
            COUNT(DISTINCT pd.id_ubicacion_origen) AS ubicaciones,
            CAST(ISNULL(MAX(pm.movimientos_pendientes), 0) AS INT) AS movimientos_pendientes_aprobacion,
            CAST(ISNULL(MAX(pm.cantidad_pendiente_aprobacion), 0) AS DECIMAL(18,2)) AS cantidad_pendiente_aprobacion,
            CASE WHEN ISNULL(MAX(co.cortos_pendientes), 0) > 0
                 THEN CAST(1 AS BIT)
                 ELSE CAST(0 AS BIT)
            END AS tiene_cortos
        FROM dbo.picking_header ph
        INNER JOIN pend_mov pm ON pm.nro_picking = ph.nro_picking
        LEFT JOIN dbo.picking_detalle pd ON pd.id_picking = ph.id_picking
        LEFT JOIN cortos co ON co.id_picking = ph.id_picking
        LEFT JOIN liberadas lb ON lb.id_picking = ph.id_picking
        LEFT JOIN dbo.picking_pedido pp ON pp.id_picking = ph.id_picking
        LEFT JOIN dbo.pedidos ped ON ped.id_pedido = pp.id_pedido
        LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
        LEFT JOIN dbo.usuarios uc ON uc.id_usuario = ph.id_usuario_creacion
        WHERE ISNULL(pm.movimientos_pendientes, 0) > 0
        GROUP BY
            ph.id_picking,
            ph.nro_picking,
            ph.fecha_creacion,
            ph.fecha_actualizacion,
            ph.estado,
            ph.origen_atencion,
            ph.estado_aprobacion_admin,
            uc.usuario_login
        ORDER BY ph.fecha_actualizacion DESC, ph.nro_picking DESC
    """)

def get_stock_para_transferencia():
    return read_dataframe("""
        SELECT
            su.id_stock_ubicacion,
            p.id_producto,
            p.sku,
            p.nombre_producto,
            um.codigo_unidad,
            ub.id_ubicacion,
            ub.codigo_ubicacion,
            su.lote,
            su.cantidad_actual,
            ISNULL(su.cantidad_en_picking, 0) AS cantidad_en_picking,
            CAST(su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible
        FROM stock_ubicacion su
        INNER JOIN productos p ON p.id_producto = su.id_producto
        INNER JOIN unidades_medida um ON um.id_unidad = p.id_unidad
        INNER JOIN ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
        WHERE p.activo = 1
          AND ub.activo = 1
          AND su.cantidad_actual > 0
        ORDER BY p.sku, ub.codigo_ubicacion, su.lote
    """)


# ---------------------------------------------------------------------------
# Dashboard ejecutivo
# ---------------------------------------------------------------------------

def get_dashboard_movimientos(
    fecha_inicio=None,
    fecha_fin=None,
    tipo_movimiento: str = "",
    cuenta: str = "",
    sku: str = "",
    proveedor: str = "",
):
    """Movimientos para dashboard con filtros aplicados en Azure SQL.

    Importante: no cargar todo el historico a Pandas. Esta funcion siempre debe
    recibir rango de fechas desde la vista para que SQL haga el filtrado.
    """
    filters = ["fecha_movimiento IS NOT NULL"]
    params: dict = {}

    if fecha_inicio is not None:
        filters.append("fecha_movimiento >= CAST(:fecha_inicio AS date)")
        params["fecha_inicio"] = fecha_inicio

    if fecha_fin is not None:
        filters.append("fecha_movimiento < DATEADD(DAY, 1, CAST(:fecha_fin AS date))")
        params["fecha_fin"] = fecha_fin

    if tipo_movimiento:
        filters.append("tipo_movimiento = :tipo_movimiento")
        params["tipo_movimiento"] = tipo_movimiento

    if cuenta:
        filters.append("(codigo_cuenta = :cuenta OR codigo_cuenta LIKE '%' + :cuenta + '%' OR nombre_cuenta LIKE '%' + :cuenta + '%')")
        params["cuenta"] = cuenta

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku

    if proveedor:
        filters.append("(ruc_proveedor LIKE '%' + :proveedor + '%' OR razon_social_proveedor LIKE '%' + :proveedor + '%')")
        params["proveedor"] = proveedor

    where_sql = " AND ".join(filters)

    query_view = f"""
        SELECT
            id_movimiento,
            tipo_movimiento,
            fecha_movimiento,
            CAST(fecha_movimiento AS DATE) AS fecha_movimiento_dia,
            ISNULL(codigo_cuenta, '') AS codigo_cuenta,
            ISNULL(nombre_cuenta, '') AS nombre_cuenta,
            ISNULL(ruc_proveedor, '') AS ruc_proveedor,
            ISNULL(razon_social_proveedor, '') AS razon_social_proveedor,
            ISNULL(sku, '') AS sku,
            ISNULL(nombre_producto, '') AS nombre_producto,
            ISNULL(codigo_unidad, '') AS codigo_unidad,
            ISNULL(ubicacion_origen, '') AS ubicacion_origen,
            ISNULL(ubicacion_destino, '') AS ubicacion_destino,
            CAST(ISNULL(cantidad, 0) AS DECIMAL(18,2)) AS cantidad,
            CAST(ISNULL(precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
            CAST(ISNULL(importe_soles, ISNULL(cantidad, 0) * ISNULL(precio_unitario, 0)) AS DECIMAL(18,2)) AS importe_soles,
            ISNULL(vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
            fecha_vencimiento_cuenta,
            ISNULL(lote, '') AS lote,
            ISNULL(referencia, '') AS referencia,
            ISNULL(observacion, '') AS observacion,
            ISNULL(texto_item, '') AS texto_item,
            ISNULL(usuario_login, '') AS usuario_login,
            ISNULL(usuario_nombre, '') AS usuario_nombre,
            estado
        FROM dbo.vw_movimientos
        WHERE {where_sql}
        ORDER BY fecha_movimiento DESC, id_movimiento DESC
    """

    query_fallback = f"""
        SELECT
            m.id_movimiento,
            m.tipo_movimiento,
            m.fecha_movimiento,
            CAST(m.fecha_movimiento AS DATE) AS fecha_movimiento_dia,
            ISNULL(c.codigo_cuenta, '') AS codigo_cuenta,
            ISNULL(c.nombre_cuenta, '') AS nombre_cuenta,
            ISNULL(pr.ruc, '') AS ruc_proveedor,
            ISNULL(pr.razon_social, '') AS razon_social_proveedor,
            ISNULL(p.sku, '') AS sku,
            ISNULL(p.nombre_producto, '') AS nombre_producto,
            ISNULL(um.codigo_unidad, '') AS codigo_unidad,
            ISNULL(ub_origen.codigo_ubicacion, '') AS ubicacion_origen,
            ISNULL(ub_destino.codigo_ubicacion, '') AS ubicacion_destino,
            CAST(ISNULL(md.cantidad, 0) AS DECIMAL(18,2)) AS cantidad,
            CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
            CAST(ISNULL(md.cantidad, 0) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS importe_soles,
            ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
            CAST(NULL AS DATE) AS fecha_vencimiento_cuenta,
            ISNULL(md.lote, '') AS lote,
            ISNULL(m.referencia, '') AS referencia,
            ISNULL(m.observacion, '') AS observacion,
            ISNULL(md.observacion, '') AS texto_item,
            ISNULL(u.usuario_login, '') AS usuario_login,
            LTRIM(RTRIM(ISNULL(u.nombres, '') + ' ' + ISNULL(u.apellidos, ''))) AS usuario_nombre,
            m.estado
        FROM dbo.movimientos m
        LEFT JOIN dbo.movimiento_detalle md ON md.id_movimiento = m.id_movimiento
        LEFT JOIN dbo.productos p ON p.id_producto = md.id_producto
        LEFT JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
        LEFT JOIN dbo.ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
        LEFT JOIN dbo.ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
        LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
        LEFT JOIN dbo.proveedores pr ON pr.id_proveedor = m.id_proveedor
        LEFT JOIN dbo.usuarios u ON u.id_usuario = m.id_usuario
        WHERE {where_sql.replace('fecha_movimiento', 'm.fecha_movimiento').replace('tipo_movimiento', 'm.tipo_movimiento').replace('codigo_cuenta', 'c.codigo_cuenta').replace('nombre_cuenta', 'c.nombre_cuenta').replace('sku', 'p.sku').replace('nombre_producto', 'p.nombre_producto').replace('ruc_proveedor', 'pr.ruc').replace('razon_social_proveedor', 'pr.razon_social')}
        ORDER BY m.fecha_movimiento DESC, m.id_movimiento DESC
    """

    try:
        return read_dataframe(query_view, params)
    except Exception:
        return read_dataframe(query_fallback, params)


def get_dashboard_kpi_counts():
    """KPIs de conteo para dashboard sin cargar tablas maestras completas."""
    return read_dataframe("""
        SELECT
            (SELECT COUNT(1) FROM dbo.productos WHERE ISNULL(activo, 1) = 1) AS skus_activos,
            (SELECT COUNT(1) FROM dbo.ubicaciones WHERE ISNULL(activo, 1) = 1) AS ubicaciones,
            (SELECT COUNT(1) FROM dbo.cuentas_logisticas WHERE ISNULL(activo, 1) = 1) AS cuentas
    """)

# ---------------------------------------------------------------------------
# Salida Ajuste
# ---------------------------------------------------------------------------

def get_stock_ajuste_almacen(sku: str = "", ubicacion: str = "", cuenta: str = "") -> pd.DataFrame:
    """Stock físico para salida por ajuste.

    Para ubicaciones stage de salida/recepción, la vista debe clasificar:
      - B1.ST.% como cantidad_en_picking
      - B1.RE.% como cantidad_en_ingreso
      - ambas con cantidad_disponible = 0

    Esta función recalcula esos campos en la consulta para que la pantalla se
    comporte correctamente incluso si alguna vista SQL no fue refrescada aún.
    """
    filters = ["ISNULL(cantidad_actual, 0) > 0"]
    params: dict = {}

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku
    if ubicacion:
        filters.append("(codigo_ubicacion LIKE '%' + :ubicacion + '%' OR codigo_zona LIKE '%' + :ubicacion + '%')")
        params["ubicacion"] = ubicacion

    where_sql = " AND ".join(filters)
    return read_dataframe(f"""
        WITH base AS (
            SELECT
                id_producto,
                sku,
                nombre_producto,
                codigo_unidad,
                codigo_zona,
                id_ubicacion,
                codigo_ubicacion,
                tipo_ubicacion,
                lote,
                CAST(ISNULL(cantidad_actual, 0) AS decimal(18,3)) AS cantidad_actual,
                CAST(ISNULL(cantidad_en_picking, 0) AS decimal(18,3)) AS cantidad_en_picking_base,
                CAST(ISNULL(cantidad_en_ingreso, 0) AS decimal(18,3)) AS cantidad_en_ingreso_base,
                CAST(ISNULL(cantidad_disponible, 0) AS decimal(18,3)) AS cantidad_disponible_base,
                CAST(ISNULL(precio_unitario, 0) AS decimal(18,4)) AS precio_unitario
            FROM dbo.vw_stock_por_ubicacion
            WHERE {where_sql}
        ), calc AS (
            SELECT
                *,
                CASE
                    WHEN codigo_ubicacion LIKE 'B1.ST.%' THEN cantidad_actual
                    ELSE cantidad_en_picking_base
                END AS cantidad_en_picking_calc,
                CASE
                    WHEN codigo_ubicacion LIKE 'B1.RE.%' THEN cantidad_actual
                    ELSE cantidad_en_ingreso_base
                END AS cantidad_en_ingreso_calc,
                CASE
                    WHEN codigo_ubicacion LIKE 'B1.ST.%' THEN CAST(0 AS decimal(18,3))
                    WHEN codigo_ubicacion LIKE 'B1.RE.%' THEN CAST(0 AS decimal(18,3))
                    ELSE cantidad_disponible_base
                END AS cantidad_disponible_calc
            FROM base
        )
        SELECT
            CAST(0 AS bit) AS seleccionar,
            CAST(0 AS decimal(18,3)) AS cantidad_ajuste,
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            codigo_zona,
            id_ubicacion,
            codigo_ubicacion,
            tipo_ubicacion,
            lote,
            cantidad_actual,
            CAST(cantidad_en_picking_calc AS decimal(18,3)) AS cantidad_en_picking,
            CAST(cantidad_en_ingreso_calc AS decimal(18,3)) AS cantidad_en_ingreso,
            CAST(cantidad_disponible_calc AS decimal(18,3)) AS cantidad_disponible,
            CAST(
                CASE
                    WHEN codigo_ubicacion LIKE 'B1.ST.%' THEN cantidad_actual
                    WHEN codigo_ubicacion LIKE 'B1.RE.%' THEN cantidad_actual
                    ELSE cantidad_disponible_calc
                END AS decimal(18,3)
            ) AS cantidad_max_ajuste,
            precio_unitario,
            CAST(cantidad_disponible_calc * precio_unitario AS decimal(18,2)) AS valor_stock_disponible
        FROM calc
        ORDER BY codigo_ubicacion, sku, lote
    """, params)

def get_stock_ajuste_cuentas(sku: str = "", ubicacion: str = "", cuenta: str = "") -> pd.DataFrame:
    """Stock neto por cuenta disponible para salida por ajuste."""
    aplicar_vencimientos_stock_cuenta()
    filters = ["ISNULL(cantidad_neta, 0) > 0"]
    params: dict = {}

    if sku:
        filters.append("(sku LIKE '%' + :sku + '%' OR nombre_producto LIKE '%' + :sku + '%')")
        params["sku"] = sku
    if cuenta:
        filters.append("(codigo_cuenta LIKE '%' + :cuenta + '%' OR nombre_cuenta LIKE '%' + :cuenta + '%')")
        params["cuenta"] = cuenta

    where_sql = " AND ".join(filters)
    return read_dataframe(f"""
        SELECT
            CAST(0 AS bit) AS seleccionar,
            CAST(0 AS decimal(18,2)) AS cantidad_ajuste,
            id_cuenta,
            codigo_cuenta,
            nombre_cuenta,
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            CAST(ISNULL(cantidad_entregada, 0) AS decimal(18,2)) AS cantidad_entregada,
            CAST(ISNULL(cantidad_devuelta, 0) AS decimal(18,2)) AS cantidad_devuelta,
            CAST(ISNULL(cantidad_consumida_vida_util, 0) AS decimal(18,2)) AS cantidad_consumida_vida_util,
            CAST(ISNULL(cantidad_ajuste_salida, 0) AS decimal(18,2)) AS cantidad_ajuste_salida,
            CAST(ISNULL(cantidad_neta, 0) AS decimal(18,2)) AS cantidad_neta,
            CAST(ISNULL(precio_unitario, 0) AS decimal(18,4)) AS precio_unitario,
            CAST(ISNULL(valor_stock_cuenta, ISNULL(cantidad_neta, 0) * ISNULL(precio_unitario, 0)) AS decimal(18,2)) AS valor_stock_cuenta
        FROM dbo.vw_stock_por_cuenta
        WHERE {where_sql}
        ORDER BY nombre_cuenta, sku
    """, params)
