SET NOCOUNT ON;
SET XACT_ABORT ON;

/* ================================================================
   018 - Zona horaria Bogotá/Lima, stage salida y soporte RF
   ================================================================ */

IF OBJECT_ID('dbo.fn_now_bogota_lima', 'FN') IS NOT NULL
BEGIN
    DROP FUNCTION dbo.fn_now_bogota_lima;
END;

EXEC(N'
CREATE FUNCTION dbo.fn_now_bogota_lima()
RETURNS DATETIME2(0)
AS
BEGIN
    RETURN CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), ''-05:00'') AS DATETIME2(0));
END
');

/* Helper: actualizar defaults DATETIME2 a hora Bogotá/Lima si la tabla/columna existe. */
DECLARE @sql NVARCHAR(MAX);
DECLARE @constraint_name SYSNAME;
DECLARE @table SYSNAME;
DECLARE @column SYSNAME;

DECLARE @defaults TABLE (table_name SYSNAME, column_name SYSNAME);
INSERT INTO @defaults(table_name, column_name)
VALUES
('movimientos','fecha_movimiento'),
('stock_ubicacion','fecha_actualizacion'),
('stock_cuenta','fecha_actualizacion'),
('pedidos','fecha_creacion'),
('pedido_detalle','fecha_creacion'),
('picking_header','fecha_creacion'),
('picking_pedido','fecha_creacion'),
('picking_detalle','fecha_creacion'),
('usuarios','fecha_creacion'),
('productos','fecha_creacion'),
('proveedores','fecha_creacion');

DECLARE cur_defaults CURSOR LOCAL FAST_FORWARD FOR
SELECT table_name, column_name FROM @defaults;

OPEN cur_defaults;
FETCH NEXT FROM cur_defaults INTO @table, @column;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF OBJECT_ID(N'dbo.' + QUOTENAME(@table), 'U') IS NOT NULL
       AND COL_LENGTH(N'dbo.' + @table, @column) IS NOT NULL
    BEGIN
        SELECT @constraint_name = dc.name
        FROM sys.default_constraints dc
        INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
        INNER JOIN sys.tables t ON t.object_id = c.object_id
        INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
        WHERE s.name = 'dbo'
          AND t.name = @table
          AND c.name = @column;

        IF @constraint_name IS NOT NULL
        BEGIN
            SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) + N' DROP CONSTRAINT ' + QUOTENAME(@constraint_name) + N';';
            EXEC sp_executesql @sql;
        END;

        SET @sql = N'ALTER TABLE dbo.' + QUOTENAME(@table) +
                   N' ADD CONSTRAINT ' + QUOTENAME(N'DF_' + @table + N'_' + @column + N'_bogota_lima') +
                   N' DEFAULT dbo.fn_now_bogota_lima() FOR ' + QUOTENAME(@column) + N';';
        EXEC sp_executesql @sql;
    END;

    FETCH NEXT FROM cur_defaults INTO @table, @column;
END;

CLOSE cur_defaults;
DEALLOCATE cur_defaults;

/* Asegurar columnas operativas de ubicaciones. */
IF COL_LENGTH('dbo.ubicaciones', 'secuencia') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones ADD secuencia INT NOT NULL CONSTRAINT DF_ubicaciones_secuencia_018 DEFAULT 999999;
END;
IF COL_LENGTH('dbo.ubicaciones', 'es_surtible') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones ADD es_surtible BIT NOT NULL CONSTRAINT DF_ubicaciones_es_surtible_018 DEFAULT 1;
END;
IF COL_LENGTH('dbo.ubicaciones', 'es_stage') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones ADD es_stage BIT NOT NULL CONSTRAINT DF_ubicaciones_es_stage_018 DEFAULT 0;
END;

/* Crear zona STAGE y ubicación stage de salida B1.ST.01. */
IF OBJECT_ID('dbo.zonas_almacen', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dbo.zonas_almacen WHERE codigo_zona = 'STAGE')
    BEGIN
        INSERT INTO dbo.zonas_almacen (codigo_zona, nombre_zona, descripcion, activo)
        VALUES ('STAGE', 'Stage', 'Zona stage de recepción y salida', 1);
    END
    ELSE
    BEGIN
        UPDATE dbo.zonas_almacen
        SET nombre_zona = ISNULL(NULLIF(nombre_zona, ''), 'Stage'),
            activo = 1
        WHERE codigo_zona = 'STAGE';
    END
END;

DECLARE @id_zona_stage INT;
SELECT @id_zona_stage = id_zona FROM dbo.zonas_almacen WHERE codigo_zona = 'STAGE';

IF @id_zona_stage IS NOT NULL AND OBJECT_ID('dbo.ubicaciones', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM dbo.ubicaciones WHERE codigo_ubicacion = 'B1.ST.01')
    BEGIN
        INSERT INTO dbo.ubicaciones
            (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion,
             capacidad_maxima, activo, secuencia, es_surtible, es_stage)
        VALUES
            ('B1.ST.01', @id_zona_stage, 'Stage de salida', '1', '1', '1', '1',
             100000000, 1, 999999, 0, 1);
    END
    ELSE
    BEGIN
        UPDATE dbo.ubicaciones
        SET id_zona = @id_zona_stage,
            tipo_ubicacion = 'Stage de salida',
            pasillo = ISNULL(NULLIF(pasillo, ''), '1'),
            rack = ISNULL(NULLIF(rack, ''), '1'),
            nivel = ISNULL(NULLIF(nivel, ''), '1'),
            posicion = ISNULL(NULLIF(posicion, ''), '1'),
            capacidad_maxima = ISNULL(capacidad_maxima, 100000000),
            secuencia = 999999,
            es_surtible = 0,
            es_stage = 1,
            activo = 1
        WHERE codigo_ubicacion = 'B1.ST.01';
    END
END;

/* Asegurar que movimiento_detalle tenga destino y relación picking si faltara. */
IF OBJECT_ID('dbo.movimiento_detalle', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.movimiento_detalle', 'id_ubicacion_destino') IS NULL
    BEGIN
        ALTER TABLE dbo.movimiento_detalle ADD id_ubicacion_destino INT NULL;
    END;
    IF COL_LENGTH('dbo.movimiento_detalle', 'id_picking_detalle') IS NULL
    BEGIN
        ALTER TABLE dbo.movimiento_detalle ADD id_picking_detalle INT NULL;
    END;
END;

/* Recrear vistas de stock para asegurar que stage salida sea visible con stock. */
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
    CAST(ISNULL(su.cantidad_actual, 0) AS DECIMAL(18,2)) AS cantidad_actual,
    CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_en_picking,
    CAST(ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible,
    CAST(ISNULL(p.precio_unitario, 0) AS DECIMAL(18,4)) AS precio_unitario,
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
  AND (ISNULL(su.cantidad_actual, 0) <> 0 OR ISNULL(su.cantidad_en_picking, 0) <> 0);
');

SELECT
    'OK - zona horaria Bogotá/Lima aplicada y stage salida B1.ST.01 preparado' AS resultado,
    dbo.fn_now_bogota_lima() AS fecha_hora_bogota_lima;
