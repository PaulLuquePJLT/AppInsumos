/*
021_performance_filtered_queries.sql
Optimización para consultas filtradas en Movimientos, Dashboard, Picking y Stock.

Objetivo:
- Evitar scans completos en tablas históricas.
- Dar soporte a filtros por fecha aplicados desde Azure SQL.
- Agregar índices covering para movimientos, detalle, stock y picking.

Ejecutar en Azure SQL una vez. El script es idempotente.
*/
SET NOCOUNT ON;

PRINT '021 - inicio optimización de consultas filtradas';

/* ==========================================================
   Query Store: recomendado para monitorear top queries.
   Si por permisos falla, el script continúa.
   ========================================================== */
BEGIN TRY
    ALTER DATABASE CURRENT SET QUERY_STORE = ON;
    ALTER DATABASE CURRENT SET QUERY_STORE (OPERATION_MODE = READ_WRITE);
    PRINT 'Query Store habilitado/confirmado.';
END TRY
BEGIN CATCH
    PRINT 'No se pudo habilitar Query Store desde este script. Habilitar desde Azure Portal si aplica.';
    PRINT ERROR_MESSAGE();
END CATCH;

BEGIN TRY
    ALTER DATABASE CURRENT SET AUTOMATIC_TUNING (FORCE_LAST_GOOD_PLAN = ON);
    PRINT 'Automatic tuning FORCE_LAST_GOOD_PLAN habilitado/confirmado.';
END TRY
BEGIN CATCH
    PRINT 'No se pudo habilitar Automatic Tuning desde este script. Habilitar desde Azure Portal si aplica.';
    PRINT ERROR_MESSAGE();
END CATCH;

/* ==========================================================
   STOCK UBICACION
   ========================================================== */
IF OBJECT_ID(N'dbo.stock_ubicacion', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.stock_ubicacion', N'lote_key') IS NULL
    BEGIN
        EXEC(N'ALTER TABLE dbo.stock_ubicacion ADD lote_key AS ISNULL(lote, N'''') PERSISTED;');
    END;

    IF COL_LENGTH(N'dbo.stock_ubicacion', N'cantidad_en_picking') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stock_ubicacion_ubicacion_producto_lotekey' AND object_id = OBJECT_ID(N'dbo.stock_ubicacion'))
    BEGIN
        EXEC(N'
        CREATE INDEX IX_stock_ubicacion_ubicacion_producto_lotekey
        ON dbo.stock_ubicacion(id_ubicacion, id_producto, lote_key)
        INCLUDE (cantidad_actual, cantidad_en_picking, fecha_actualizacion);
        ');
    END;

    IF COL_LENGTH(N'dbo.stock_ubicacion', N'cantidad_en_picking') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stock_ubicacion_disponible_picking' AND object_id = OBJECT_ID(N'dbo.stock_ubicacion'))
    BEGIN
        EXEC(N'
        CREATE INDEX IX_stock_ubicacion_disponible_picking
        ON dbo.stock_ubicacion(id_producto, cantidad_actual, cantidad_en_picking)
        INCLUDE (id_stock_ubicacion, id_ubicacion, lote, lote_key, fecha_actualizacion);
        ');
    END;
END;

/* ==========================================================
   MOVIMIENTOS Y DETALLE
   ========================================================== */
IF OBJECT_ID(N'dbo.movimientos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimientos_fecha_cuenta_tipo' AND object_id = OBJECT_ID(N'dbo.movimientos'))
BEGIN
    CREATE INDEX IX_movimientos_fecha_cuenta_tipo
    ON dbo.movimientos(fecha_movimiento DESC, id_cuenta, tipo_movimiento)
    INCLUDE (id_movimiento, id_proveedor, referencia, observacion, id_usuario, estado);
END;

IF OBJECT_ID(N'dbo.movimientos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimientos_tipo_fecha' AND object_id = OBJECT_ID(N'dbo.movimientos'))
BEGIN
    CREATE INDEX IX_movimientos_tipo_fecha
    ON dbo.movimientos(tipo_movimiento, fecha_movimiento DESC)
    INCLUDE (id_movimiento, id_cuenta, id_proveedor, referencia, observacion, id_usuario, estado);
END;

IF OBJECT_ID(N'dbo.movimiento_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimiento_detalle_producto_movimiento' AND object_id = OBJECT_ID(N'dbo.movimiento_detalle'))
BEGIN
    CREATE INDEX IX_movimiento_detalle_producto_movimiento
    ON dbo.movimiento_detalle(id_producto, id_movimiento)
    INCLUDE (cantidad, id_ubicacion_origen, id_ubicacion_destino, lote, observacion);
END;

IF OBJECT_ID(N'dbo.movimiento_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimiento_detalle_ubicaciones' AND object_id = OBJECT_ID(N'dbo.movimiento_detalle'))
BEGIN
    CREATE INDEX IX_movimiento_detalle_ubicaciones
    ON dbo.movimiento_detalle(id_ubicacion_origen, id_ubicacion_destino)
    INCLUDE (id_movimiento, id_producto, cantidad, lote);
END;

/* ==========================================================
   STOCK CUENTA
   ========================================================== */
IF OBJECT_ID(N'dbo.stock_cuenta', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stock_cuenta_cuenta_producto_ext' AND object_id = OBJECT_ID(N'dbo.stock_cuenta'))
BEGIN
    DECLARE @sql_stock_cuenta NVARCHAR(MAX) = N'
    CREATE INDEX IX_stock_cuenta_cuenta_producto_ext
    ON dbo.stock_cuenta(id_cuenta, id_producto)
    INCLUDE (cantidad_entregada, cantidad_devuelta';

    IF COL_LENGTH(N'dbo.stock_cuenta', N'cantidad_consumida_vida_util') IS NOT NULL
        SET @sql_stock_cuenta += N', cantidad_consumida_vida_util';
    IF COL_LENGTH(N'dbo.stock_cuenta', N'cantidad_ajuste_salida') IS NOT NULL
        SET @sql_stock_cuenta += N', cantidad_ajuste_salida';
    IF COL_LENGTH(N'dbo.stock_cuenta', N'fecha_actualizacion') IS NOT NULL
        SET @sql_stock_cuenta += N', fecha_actualizacion';

    SET @sql_stock_cuenta += N');';
    EXEC sp_executesql @sql_stock_cuenta;
END;

/* ==========================================================
   PEDIDOS Y PICKING
   ========================================================== */
IF OBJECT_ID(N'dbo.pedidos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_pedidos_fecha_estado' AND object_id = OBJECT_ID(N'dbo.pedidos'))
BEGIN
    CREATE INDEX IX_pedidos_fecha_estado
    ON dbo.pedidos(fecha_pedido DESC, estado)
    INCLUDE (id_pedido, nro_pedido, id_cuenta, solicitante, responsable_cuenta, qty_total, fecha_esperada_atencion);
END;

IF OBJECT_ID(N'dbo.pedido_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_pedido_detalle_pendiente_picking' AND object_id = OBJECT_ID(N'dbo.pedido_detalle'))
BEGIN
    CREATE INDEX IX_pedido_detalle_pendiente_picking
    ON dbo.pedido_detalle(estado, id_pedido, id_producto)
    INCLUDE (nro_linea, codigo_unidad, cantidad_pedida, cantidad_asignada, cantidad_atendida, cantidad_cancelada, texto_item);
END;

IF OBJECT_ID(N'dbo.picking_header', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_picking_header_fecha_estado' AND object_id = OBJECT_ID(N'dbo.picking_header'))
BEGIN
    CREATE INDEX IX_picking_header_fecha_estado
    ON dbo.picking_header(fecha_creacion DESC, estado)
    INCLUDE (id_picking, nro_picking, qty_total, qty_asignada, qty_corto);
END;

IF OBJECT_ID(N'dbo.picking_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_picking_detalle_estado_secuencia' AND object_id = OBJECT_ID(N'dbo.picking_detalle'))
BEGIN
    CREATE INDEX IX_picking_detalle_estado_secuencia
    ON dbo.picking_detalle(estado, id_picking, secuencia)
    INCLUDE (id_pedido, id_pedido_detalle, id_cuenta, id_producto, id_ubicacion_origen, lote, cantidad_solicitada, cantidad_asignada, cantidad_atendida, cantidad_cancelada, nro_pedido, fecha_creacion);
END;

/* ==========================================================
   MAESTROS: búsquedas por código
   ========================================================== */
IF OBJECT_ID(N'dbo.productos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_productos_sku_activo' AND object_id = OBJECT_ID(N'dbo.productos'))
BEGIN
    CREATE INDEX IX_productos_sku_activo
    ON dbo.productos(sku, activo)
    INCLUDE (nombre_producto, id_categoria, id_unidad, ean_serie, precio_unitario);
END;

IF OBJECT_ID(N'dbo.ubicaciones', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ubicaciones_codigo_activo' AND object_id = OBJECT_ID(N'dbo.ubicaciones'))
BEGIN
    CREATE INDEX IX_ubicaciones_codigo_activo
    ON dbo.ubicaciones(codigo_ubicacion, activo)
    INCLUDE (id_zona, tipo_ubicacion, secuencia, es_surtible, es_stage);
END;

/* ==========================================================
   Estadísticas
   ========================================================== */
BEGIN TRY
    IF OBJECT_ID(N'dbo.movimientos', N'U') IS NOT NULL UPDATE STATISTICS dbo.movimientos;
    IF OBJECT_ID(N'dbo.movimiento_detalle', N'U') IS NOT NULL UPDATE STATISTICS dbo.movimiento_detalle;
    IF OBJECT_ID(N'dbo.stock_ubicacion', N'U') IS NOT NULL UPDATE STATISTICS dbo.stock_ubicacion;
    IF OBJECT_ID(N'dbo.stock_cuenta', N'U') IS NOT NULL UPDATE STATISTICS dbo.stock_cuenta;
    IF OBJECT_ID(N'dbo.pedidos', N'U') IS NOT NULL UPDATE STATISTICS dbo.pedidos;
    IF OBJECT_ID(N'dbo.pedido_detalle', N'U') IS NOT NULL UPDATE STATISTICS dbo.pedido_detalle;
    IF OBJECT_ID(N'dbo.picking_header', N'U') IS NOT NULL UPDATE STATISTICS dbo.picking_header;
    IF OBJECT_ID(N'dbo.picking_detalle', N'U') IS NOT NULL UPDATE STATISTICS dbo.picking_detalle;
END TRY
BEGIN CATCH
    PRINT 'No se pudieron actualizar algunas estadísticas.';
    PRINT ERROR_MESSAGE();
END CATCH;

SELECT 'OK - optimización 021 aplicada correctamente' AS resultado;
