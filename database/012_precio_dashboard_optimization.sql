SET NOCOUNT ON;

/* ================================================================
   012 - Precio unitario, valorización, vistas optimizadas
   ================================================================ */

IF OBJECT_ID('dbo.productos', 'U') IS NULL
BEGIN
    THROW 51201, 'No existe la tabla dbo.productos.', 1;
END;

/* 1) Agregar precio unitario al maestro de productos */
IF COL_LENGTH('dbo.productos', 'precio_unitario') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD precio_unitario DECIMAL(18,4) NULL;
END;

EXEC(N'
UPDATE dbo.productos
SET precio_unitario = 0
WHERE precio_unitario IS NULL;
');

EXEC(N'
ALTER TABLE dbo.productos
ALTER COLUMN precio_unitario DECIMAL(18,4) NOT NULL;
');

DECLARE @default_name NVARCHAR(200);

SELECT @default_name = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t ON t.object_id = c.object_id
INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'productos'
  AND c.name = 'precio_unitario';

IF @default_name IS NULL
BEGIN
    EXEC(N'
    ALTER TABLE dbo.productos
    ADD CONSTRAINT DF_productos_precio_unitario
    DEFAULT 0 FOR precio_unitario;
    ');
END;

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_precio_unitario_nonnegative'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos
    DROP CONSTRAINT CK_productos_precio_unitario_nonnegative;
END;

EXEC(N'
ALTER TABLE dbo.productos
ADD CONSTRAINT CK_productos_precio_unitario_nonnegative
CHECK (precio_unitario >= 0);
');

/* 2) Asegurar columna cantidad_en_picking si no existe */
IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.stock_ubicacion', 'cantidad_en_picking') IS NULL
BEGIN
    ALTER TABLE dbo.stock_ubicacion
    ADD cantidad_en_picking DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_ubicacion_cantidad_en_picking_012 DEFAULT 0;
END;

/* 3) Recrear vistas de stock valorizadas y sin líneas cero */
IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.unidades_medida', 'U') IS NOT NULL
BEGIN
    EXEC(N'
    CREATE OR ALTER VIEW dbo.vw_stock_general AS
    SELECT
        p.id_producto,
        p.sku,
        p.nombre_producto,
        u.codigo_unidad,
        u.nombre_unidad,
        p.stock_minimo,
        p.stock_maximo,
        CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
        CAST(SUM(ISNULL(su.cantidad_actual, 0)) AS DECIMAL(18,2)) AS cantidad_total,
        CAST(SUM(ISNULL(su.cantidad_en_picking, 0)) AS DECIMAL(18,2)) AS cantidad_en_picking,
        CAST(SUM(ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0)) AS DECIMAL(18,2)) AS cantidad_disponible,
        CAST(SUM(ISNULL(su.cantidad_actual, 0)) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_total,
        CAST(SUM(ISNULL(su.cantidad_en_picking, 0)) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_en_picking,
        CAST(SUM(ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0)) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_disponible
    FROM dbo.productos p
    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
    LEFT JOIN dbo.stock_ubicacion su ON su.id_producto = p.id_producto
    WHERE ISNULL(p.activo, 1) = 1
    GROUP BY
        p.id_producto,
        p.sku,
        p.nombre_producto,
        u.codigo_unidad,
        u.nombre_unidad,
        p.stock_minimo,
        p.stock_maximo,
        p.precio_unitario
    HAVING
        SUM(ISNULL(su.cantidad_actual, 0)) > 0
        OR SUM(ISNULL(su.cantidad_en_picking, 0)) > 0;
    ');
END;

IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.ubicaciones', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.zonas_almacen', 'U') IS NOT NULL
BEGIN
    EXEC(N'
    CREATE OR ALTER VIEW dbo.vw_stock_por_ubicacion AS
    SELECT
        p.id_producto,
        p.sku,
        p.nombre_producto,
        u.codigo_unidad,
        u.nombre_unidad,
        z.codigo_zona,
        z.nombre_zona,
        ub.id_ubicacion,
        ub.codigo_ubicacion,
        ub.tipo_ubicacion,
        ISNULL(ub.secuencia, 999999) AS secuencia,
        ISNULL(ub.es_surtible, 1) AS es_surtible,
        ISNULL(ub.es_stage, 0) AS es_stage,
        su.lote,
        CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
        CAST(ISNULL(su.cantidad_actual, 0) AS DECIMAL(18,2)) AS cantidad_actual,
        CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_en_picking,
        CAST(ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible,
        CAST(ISNULL(su.cantidad_actual, 0) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_actual,
        CAST(ISNULL(su.cantidad_en_picking, 0) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_en_picking,
        CAST((ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0)) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_disponible,
        su.fecha_actualizacion
    FROM dbo.stock_ubicacion su
    INNER JOIN dbo.productos p ON p.id_producto = su.id_producto
    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
    INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
    INNER JOIN dbo.zonas_almacen z ON z.id_zona = ub.id_zona
    WHERE ISNULL(p.activo, 1) = 1
      AND ISNULL(ub.activo, 1) = 1
      AND (ISNULL(su.cantidad_actual, 0) > 0 OR ISNULL(su.cantidad_en_picking, 0) > 0);
    ');
END;

IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL
BEGIN
    EXEC(N'
    CREATE OR ALTER VIEW dbo.vw_stock_por_cuenta AS
    SELECT
        c.id_cuenta,
        c.codigo_cuenta,
        c.nombre_cuenta,
        p.id_producto,
        p.sku,
        p.nombre_producto,
        u.codigo_unidad,
        u.nombre_unidad,
        CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
        CAST(ISNULL(sc.cantidad_entregada, 0) AS DECIMAL(18,2)) AS cantidad_entregada,
        CAST(ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_devuelta,
        CAST(ISNULL(sc.cantidad_entregada, 0) - ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_neta,
        CAST((ISNULL(sc.cantidad_entregada, 0) - ISNULL(sc.cantidad_devuelta, 0)) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS valor_stock_cuenta,
        sc.fecha_actualizacion
    FROM dbo.stock_cuenta sc
    INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = sc.id_cuenta
    INNER JOIN dbo.productos p ON p.id_producto = sc.id_producto
    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
    WHERE ISNULL(c.activo, 1) = 1
      AND ISNULL(p.activo, 1) = 1
      AND (ISNULL(sc.cantidad_entregada, 0) - ISNULL(sc.cantidad_devuelta, 0)) > 0;
    ');
END;

/* 4) Vista de movimientos con valorización */
IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.movimiento_detalle', 'U') IS NOT NULL
BEGIN
    EXEC(N'
    CREATE OR ALTER VIEW dbo.vw_movimientos AS
    SELECT
        m.id_movimiento,
        m.tipo_movimiento,
        m.fecha_movimiento,
        ISNULL(c.codigo_cuenta, '''') AS codigo_cuenta,
        ISNULL(c.nombre_cuenta, '''') AS nombre_cuenta,
        ISNULL(pr.ruc, '''') AS ruc_proveedor,
        ISNULL(pr.razon_social, '''') AS razon_social_proveedor,
        ISNULL(p.sku, '''') AS sku,
        ISNULL(p.nombre_producto, '''') AS nombre_producto,
        ISNULL(um.codigo_unidad, '''') AS codigo_unidad,
        ISNULL(um.nombre_unidad, '''') AS nombre_unidad,
        ISNULL(ub_origen.codigo_ubicacion, '''') AS ubicacion_origen,
        ISNULL(ub_destino.codigo_ubicacion, '''') AS ubicacion_destino,
        CAST(ISNULL(md.cantidad, 0) AS DECIMAL(18,2)) AS cantidad,
        CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
        CAST(ISNULL(md.cantidad, 0) * ISNULL(p.precio_unitario, 0) AS DECIMAL(18,2)) AS importe_soles,
        ISNULL(md.lote, '''') AS lote,
        ISNULL(m.referencia, '''') AS referencia,
        ISNULL(m.observacion, '''') AS observacion,
        ISNULL(md.observacion, '''') AS texto_item,
        m.id_usuario,
        ISNULL(u.usuario_login, '''') AS usuario_login,
        LTRIM(RTRIM(ISNULL(u.nombres, '''') + '' '' + ISNULL(u.apellidos, ''''))) AS usuario_nombre,
        m.estado
    FROM dbo.movimientos m
    LEFT JOIN dbo.movimiento_detalle md ON md.id_movimiento = m.id_movimiento
    LEFT JOIN dbo.productos p ON p.id_producto = md.id_producto
    LEFT JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
    LEFT JOIN dbo.ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
    LEFT JOIN dbo.ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
    LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
    LEFT JOIN dbo.proveedores pr ON pr.id_proveedor = m.id_proveedor
    LEFT JOIN dbo.usuarios u ON u.id_usuario = m.id_usuario;
    ');
END;

SELECT 'OK - precio unitario, vistas valorizadas y filtros de stock aplicados' AS resultado;

EXEC(N'
SELECT TOP 10
    id_producto,
    sku,
    nombre_producto,
    precio_unitario,
    ean_serie,
    flag_aplica_ean
FROM dbo.productos
ORDER BY id_producto DESC;
');
