SET NOCOUNT ON;
SET XACT_ABORT ON;

/* ==========================================================
   019 - Salida Ajuste, reportes XLSX y legal
   - Habilita tipo movimiento SALIDA_AJUSTE.
   - Agrega cantidad_ajuste_salida a stock_cuenta.
   - Actualiza vistas de stock cuenta y movimientos.
   ========================================================== */

/* 1) Asegurar funcion de fecha/hora Bogotá - Lima */
EXEC(N'
CREATE OR ALTER FUNCTION dbo.fn_now_bogota_lima()
RETURNS DATETIME2(0)
AS
BEGIN
    RETURN CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), ''-05:00'') AS DATETIME2(0));
END
');

/* 2) Agregar SALIDA_AJUSTE al check constraint de movimientos */
DECLARE @sql NVARCHAR(MAX) = N'';

SELECT @sql = @sql + N'ALTER TABLE dbo.movimientos DROP CONSTRAINT ' + QUOTENAME(cc.name) + N';'
FROM sys.check_constraints cc
WHERE cc.parent_object_id = OBJECT_ID('dbo.movimientos')
  AND cc.definition LIKE '%tipo_movimiento%';

IF @sql <> N''
BEGIN
    EXEC sp_executesql @sql;
END;

IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.movimientos
    ADD CONSTRAINT CK_movimientos_tipo
    CHECK (tipo_movimiento IN (
        'ENTRADA',
        'SALIDA_CUENTA',
        'TRANSFERENCIA',
        'AJUSTE_POSITIVO',
        'AJUSTE_NEGATIVO',
        'DEVOLUCION_CUENTA',
        'SALIDA_AJUSTE'
    ));
END;

/* 3) Asegurar columnas requeridas en stock_cuenta */
IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_consumida_vida_util') IS NULL
    BEGIN
        ALTER TABLE dbo.stock_cuenta
        ADD cantidad_consumida_vida_util DECIMAL(18,2) NOT NULL
            CONSTRAINT DF_stock_cuenta_consumida_vida_util_019 DEFAULT 0;
    END;

    IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_ajuste_salida') IS NULL
    BEGIN
        ALTER TABLE dbo.stock_cuenta
        ADD cantidad_ajuste_salida DECIMAL(18,2) NOT NULL
            CONSTRAINT DF_stock_cuenta_ajuste_salida DEFAULT 0;
    END;
END;

/* 4) Asegurar columnas de productos necesarias para valorización */
IF OBJECT_ID('dbo.productos', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.productos', 'precio_unitario') IS NULL
    BEGIN
        ALTER TABLE dbo.productos
        ADD precio_unitario DECIMAL(18,4) NOT NULL
            CONSTRAINT DF_productos_precio_unitario_019 DEFAULT 0;
    END;

    IF COL_LENGTH('dbo.productos', 'vida_util_cuenta_dias') IS NULL
    BEGIN
        ALTER TABLE dbo.productos
        ADD vida_util_cuenta_dias INT NOT NULL
            CONSTRAINT DF_productos_vida_util_cuenta_019 DEFAULT 0;
    END;
END;

/* 5) Recrear vista stock por cuenta incorporando salida ajuste */
IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.cuentas_logisticas', 'U') IS NOT NULL
   AND OBJECT_ID('dbo.productos', 'U') IS NOT NULL
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
        ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
        CAST(ISNULL(sc.cantidad_entregada, 0) AS DECIMAL(18,2)) AS cantidad_entregada,
        CAST(ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_devuelta,
        CAST(ISNULL(sc.cantidad_consumida_vida_util, 0) AS DECIMAL(18,2)) AS cantidad_consumida_vida_util,
        CAST(ISNULL(sc.cantidad_ajuste_salida, 0) AS DECIMAL(18,2)) AS cantidad_ajuste_salida,
        CAST(
            ISNULL(sc.cantidad_entregada, 0)
            - ISNULL(sc.cantidad_devuelta, 0)
            - ISNULL(sc.cantidad_consumida_vida_util, 0)
            - ISNULL(sc.cantidad_ajuste_salida, 0)
            AS DECIMAL(18,2)
        ) AS cantidad_neta,
        CAST(
            (
                ISNULL(sc.cantidad_entregada, 0)
                - ISNULL(sc.cantidad_devuelta, 0)
                - ISNULL(sc.cantidad_consumida_vida_util, 0)
                - ISNULL(sc.cantidad_ajuste_salida, 0)
            ) * ISNULL(p.precio_unitario, 0)
            AS DECIMAL(18,2)
        ) AS valor_stock_cuenta,
        sc.fecha_actualizacion
    FROM dbo.stock_cuenta sc
    INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = sc.id_cuenta
    INNER JOIN dbo.productos p ON p.id_producto = sc.id_producto
    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
    WHERE ISNULL(c.activo, 1) = 1
      AND ISNULL(p.activo, 1) = 1
      AND (
            ISNULL(sc.cantidad_entregada, 0)
            - ISNULL(sc.cantidad_devuelta, 0)
            - ISNULL(sc.cantidad_consumida_vida_util, 0)
            - ISNULL(sc.cantidad_ajuste_salida, 0)
          ) > 0;
    ');
END;

/* 6) Recrear vista de movimientos para incluir SALIDA_AJUSTE y columnas útiles */
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
        ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
        sv.fecha_vencimiento AS fecha_vencimiento_cuenta,
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
    LEFT JOIN dbo.stock_cuenta_vencimiento sv ON sv.id_detalle = md.id_detalle
    LEFT JOIN dbo.productos p ON p.id_producto = md.id_producto
    LEFT JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
    LEFT JOIN dbo.ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
    LEFT JOIN dbo.ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
    LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
    LEFT JOIN dbo.proveedores pr ON pr.id_proveedor = m.id_proveedor
    LEFT JOIN dbo.usuarios u ON u.id_usuario = m.id_usuario;
    ');
END;

SELECT 'OK - Salida Ajuste y vistas actualizadas correctamente' AS resultado;
