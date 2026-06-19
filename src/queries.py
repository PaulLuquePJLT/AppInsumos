import pandas as pd
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from src.db import get_engine


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
    engine = get_engine()

    with engine.connect() as conn:
        return pd.read_sql(_ensure_text(query), conn, params=params or {})


def execute_statement(statement, params: dict | None = None) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(_ensure_text(statement), params or {})


def execute_many(statement, rows: list[dict]) -> None:
    if not rows:
        return

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(_ensure_text(statement), rows)


def clean_text(value):
    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def clean_upper(value):
    return clean_text(value).upper()


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

def get_stock_general():
    return read_dataframe("""
        SELECT
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            stock_minimo,
            stock_maximo,
            cantidad_total
        FROM dbo.vw_stock_general
        ORDER BY nombre_producto
    """)


def get_stock_por_ubicacion():
    return read_dataframe("""
        SELECT
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            codigo_zona,
            nombre_zona,
            codigo_ubicacion,
            tipo_ubicacion,
            lote,
            cantidad_actual,
            fecha_actualizacion
        FROM dbo.vw_stock_por_ubicacion
        ORDER BY nombre_producto, codigo_ubicacion
    """)


def get_stock_por_cuenta():
    return read_dataframe("""
        SELECT
            id_cuenta,
            codigo_cuenta,
            nombre_cuenta,
            id_producto,
            sku,
            nombre_producto,
            codigo_unidad,
            nombre_unidad,
            cantidad_entregada,
            cantidad_devuelta,
            cantidad_neta,
            fecha_actualizacion
        FROM dbo.vw_stock_por_cuenta
        ORDER BY nombre_cuenta, nombre_producto
    """)


def get_movimientos():
    return read_dataframe("""
        SELECT *
        FROM vw_movimientos
        ORDER BY fecha_movimiento DESC
    """)


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
):
    execute_statement(
        """
        INSERT INTO productos
            (
                sku,
                nombre_producto,
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
                :nombre_producto,
                :descripcion,
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
):
    execute_statement(
        """
        UPDATE productos
        SET sku = :sku,
            nombre_producto = :nombre_producto,
            descripcion = :descripcion,
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
    execute_many(
        """
        INSERT INTO productos
            (
                sku,
                nombre_producto,
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
                :nombre_producto,
                :descripcion,
                :id_categoria,
                :id_unidad,
                :stock_minimo,
                :stock_maximo,
                :requiere_lote,
                1
            )
        """,
        rows,
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
            ub.activo
        FROM ubicaciones ub
        INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona
        WHERE ub.activo = 1
        ORDER BY ub.codigo_ubicacion
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
            ub.activo
        FROM ubicaciones ub
        INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona
        ORDER BY ub.activo DESC, ub.codigo_ubicacion
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


def update_unidad(id_unidad, codigo_unidad, nombre_unidad):
    execute_statement(
        """
        UPDATE unidades_medida
        SET codigo_unidad = :codigo_unidad,
            nombre_unidad = :nombre_unidad
        WHERE id_unidad = :id_unidad
        """,
        {
            "id_unidad": int(id_unidad),
            "codigo_unidad": clean_upper(codigo_unidad),
            "nombre_unidad": clean_text(nombre_unidad),
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
            fecha_actualizacion = SYSDATETIME()
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
            fecha_actualizacion = SYSDATETIME()
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
