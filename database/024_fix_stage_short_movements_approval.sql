SET NOCOUNT ON;
SET XACT_ABORT ON;

/* ==========================================================
   024 - Fix stage stock, cortos sin movimientos y aprobación RF
   - B1.ST.% se muestra como cantidad_en_picking y no disponible.
   - B1.RE.% se muestra como cantidad_en_ingreso y no disponible.
   - Elimina movimientos de cortos generados como SALIDA_AJUSTE con referencia CORTO PICKING%.
   - Asegura que pickings RF con movimientos pendientes vuelvan a Aprobación RF tras cancelar cortos.
   ========================================================== */

IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NULL
    THROW 52401, 'No existe dbo.stock_ubicacion.', 1;
IF OBJECT_ID('dbo.ubicaciones', 'U') IS NULL
    THROW 52402, 'No existe dbo.ubicaciones.', 1;
IF OBJECT_ID('dbo.productos', 'U') IS NULL
    THROW 52403, 'No existe dbo.productos.', 1;
IF OBJECT_ID('dbo.unidades_medida', 'U') IS NULL
    THROW 52404, 'No existe dbo.unidades_medida.', 1;

EXEC(N'
CREATE OR ALTER VIEW dbo.vw_stock_por_ubicacion AS
WITH base AS (
    SELECT
        p.id_producto,
        p.sku,
        p.nombre_producto,
        um.codigo_unidad,
        um.nombre_unidad,
        za.codigo_zona,
        za.nombre_zona,
        ub.id_ubicacion,
        ub.codigo_ubicacion,
        ub.tipo_ubicacion,
        ISNULL(ub.secuencia, 999999) AS secuencia,
        ISNULL(ub.es_surtible, 1) AS es_surtible,
        ISNULL(ub.es_stage, 0) AS es_stage,
        su.lote,
        CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
        CAST(ISNULL(su.cantidad_actual, 0) AS DECIMAL(18,3)) AS cantidad_actual_raw,
        CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,3)) AS cantidad_en_picking_raw,
        su.fecha_actualizacion
    FROM dbo.stock_ubicacion su
    INNER JOIN dbo.productos p ON p.id_producto = su.id_producto
    INNER JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
    INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
    INNER JOIN dbo.zonas_almacen za ON za.id_zona = ub.id_zona
    WHERE ISNULL(p.activo, 1) = 1
      AND ISNULL(ub.activo, 1) = 1
), calc AS (
    SELECT
        *,
        CASE
            WHEN codigo_ubicacion LIKE ''B1.ST.%'' THEN cantidad_actual_raw
            ELSE cantidad_en_picking_raw
        END AS cantidad_en_picking_calc,
        CASE
            WHEN codigo_ubicacion LIKE ''B1.RE.%'' THEN cantidad_actual_raw
            ELSE CAST(0 AS DECIMAL(18,3))
        END AS cantidad_en_ingreso_calc,
        CASE
            WHEN codigo_ubicacion LIKE ''B1.ST.%'' THEN CAST(0 AS DECIMAL(18,3))
            WHEN codigo_ubicacion LIKE ''B1.RE.%'' THEN CAST(0 AS DECIMAL(18,3))
            ELSE
                CASE
                    WHEN cantidad_actual_raw - cantidad_en_picking_raw < 0 THEN CAST(0 AS DECIMAL(18,3))
                    ELSE cantidad_actual_raw - cantidad_en_picking_raw
                END
        END AS cantidad_disponible_calc
    FROM base
)
SELECT
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
    secuencia,
    es_surtible,
    es_stage,
    lote,
    precio_unitario,
    CAST(cantidad_actual_raw AS DECIMAL(18,3)) AS cantidad_actual,
    CAST(cantidad_en_picking_calc AS DECIMAL(18,3)) AS cantidad_en_picking,
    CAST(cantidad_en_ingreso_calc AS DECIMAL(18,3)) AS cantidad_en_ingreso,
    CAST(cantidad_disponible_calc AS DECIMAL(18,3)) AS cantidad_disponible,
    CAST(cantidad_actual_raw * precio_unitario AS DECIMAL(18,2)) AS valor_stock_actual,
    CAST(cantidad_en_picking_calc * precio_unitario AS DECIMAL(18,2)) AS valor_stock_en_picking,
    CAST(cantidad_en_ingreso_calc * precio_unitario AS DECIMAL(18,2)) AS valor_stock_en_ingreso,
    CAST(cantidad_disponible_calc * precio_unitario AS DECIMAL(18,2)) AS valor_stock_disponible,
    fecha_actualizacion
FROM calc
WHERE ISNULL(cantidad_actual_raw, 0) > 0
   OR ISNULL(cantidad_en_picking_calc, 0) > 0
   OR ISNULL(cantidad_en_ingreso_calc, 0) > 0
   OR ISNULL(cantidad_disponible_calc, 0) > 0;
');

EXEC(N'
CREATE OR ALTER VIEW dbo.vw_stock_general AS
SELECT
    p.id_producto,
    p.sku,
    p.nombre_producto,
    um.codigo_unidad,
    um.nombre_unidad,
    p.stock_minimo,
    p.stock_maximo,
    CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
    CAST(SUM(ISNULL(v.cantidad_actual, 0)) AS DECIMAL(18,3)) AS cantidad_total,
    CAST(SUM(ISNULL(v.cantidad_en_picking, 0)) AS DECIMAL(18,3)) AS cantidad_en_picking,
    CAST(SUM(ISNULL(v.cantidad_en_ingreso, 0)) AS DECIMAL(18,3)) AS cantidad_en_ingreso,
    CAST(SUM(ISNULL(v.cantidad_disponible, 0)) AS DECIMAL(18,3)) AS cantidad_disponible,
    CAST(SUM(ISNULL(v.valor_stock_actual, 0)) AS DECIMAL(18,2)) AS valor_stock_total,
    CAST(SUM(ISNULL(v.valor_stock_en_picking, 0)) AS DECIMAL(18,2)) AS valor_stock_en_picking,
    CAST(SUM(ISNULL(v.valor_stock_en_ingreso, 0)) AS DECIMAL(18,2)) AS valor_stock_en_ingreso,
    CAST(SUM(ISNULL(v.valor_stock_disponible, 0)) AS DECIMAL(18,2)) AS valor_stock_disponible
FROM dbo.productos p
INNER JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
LEFT JOIN dbo.vw_stock_por_ubicacion v ON v.id_producto = p.id_producto
WHERE ISNULL(p.activo, 1) = 1
GROUP BY
    p.id_producto,
    p.sku,
    p.nombre_producto,
    um.codigo_unidad,
    um.nombre_unidad,
    p.stock_minimo,
    p.stock_maximo,
    p.precio_unitario
HAVING
    SUM(ISNULL(v.cantidad_actual, 0)) > 0
    OR SUM(ISNULL(v.cantidad_en_picking, 0)) > 0
    OR SUM(ISNULL(v.cantidad_en_ingreso, 0)) > 0
    OR SUM(ISNULL(v.cantidad_disponible, 0)) > 0;
');

/* Limpiar movimientos antiguos de cortos que fueron generados como ajuste.
   Los cortos deben vivir en picking_detalle para reasignación/cancelación, no
   en movimientos operativos. */
IF OBJECT_ID('dbo.movimiento_detalle', 'U') IS NOT NULL AND OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    DELETE md
    FROM dbo.movimiento_detalle md
    INNER JOIN dbo.movimientos m ON m.id_movimiento = md.id_movimiento
    WHERE m.tipo_movimiento = 'SALIDA_AJUSTE'
      AND ISNULL(m.referencia, '') LIKE 'CORTO PICKING%';

    DELETE FROM dbo.movimientos
    WHERE tipo_movimiento = 'SALIDA_AJUSTE'
      AND ISNULL(referencia, '') LIKE 'CORTO PICKING%';
END;

/* Reponer estado de aprobación RF para pickings con movimientos reales pendientes. */
IF OBJECT_ID('dbo.picking_header', 'U') IS NOT NULL AND OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    UPDATE ph
    SET requiere_aprobacion_admin = 1,
        estado_aprobacion_admin = CASE
            WHEN ISNULL(ph.estado_aprobacion_admin, '') IN ('', 'PENDIENTE') THEN 'PENDIENTE'
            ELSE ph.estado_aprobacion_admin
        END,
        fecha_actualizacion = dbo.fn_now_bogota_lima()
    FROM dbo.picking_header ph
    WHERE EXISTS (
        SELECT 1
        FROM dbo.movimientos m
        WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
          AND m.estado = 'PENDIENTE_APROBACION'
          AND m.referencia = 'PICKING ' + ph.nro_picking
    );
END;

SELECT 'OK - fix stage, cortos sin movimientos y aprobacion RF aplicado' AS resultado;
