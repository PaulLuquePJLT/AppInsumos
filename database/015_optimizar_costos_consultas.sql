/*
015_optimizar_costos_consultas.sql
Indexes and small schema helpers for the Mini WMS app on Azure SQL.

Run first in a non-production copy if possible. Extra indexes reduce read CPU
but add a small write/storage cost. Keep the indexes that show usage in Query Store.
*/
SET NOCOUNT ON;

PRINT '015 - optimization indexes for Mini WMS';

/* Stock by product/location/lote. The computed key avoids ISNULL(lote,'') predicates. */
IF OBJECT_ID(N'dbo.stock_ubicacion', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.stock_ubicacion', N'lote_key') IS NULL
    BEGIN
        EXEC(N'ALTER TABLE dbo.stock_ubicacion ADD lote_key AS ISNULL(lote, N'''') PERSISTED;');
    END;

    IF COL_LENGTH(N'dbo.stock_ubicacion', N'cantidad_en_picking') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stock_ubicacion_producto_ubicacion_lotekey' AND object_id = OBJECT_ID(N'dbo.stock_ubicacion'))
    BEGIN
        EXEC(N'CREATE INDEX IX_stock_ubicacion_producto_ubicacion_lotekey
              ON dbo.stock_ubicacion(id_producto, id_ubicacion, lote_key)
              INCLUDE (cantidad_actual, cantidad_en_picking, fecha_actualizacion);');
    END;

    IF COL_LENGTH(N'dbo.stock_ubicacion', N'cantidad_en_picking') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_stock_ubicacion_producto_disponible' AND object_id = OBJECT_ID(N'dbo.stock_ubicacion'))
    BEGIN
        EXEC(N'CREATE INDEX IX_stock_ubicacion_producto_disponible
              ON dbo.stock_ubicacion(id_producto)
              INCLUDE (id_stock_ubicacion, id_ubicacion, lote, lote_key, cantidad_actual, cantidad_en_picking, fecha_actualizacion);');
    END;
END;
GO

/* Master data used on most pages. */
IF OBJECT_ID(N'dbo.productos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_productos_activo_nombre' AND object_id = OBJECT_ID(N'dbo.productos'))
BEGIN
    CREATE INDEX IX_productos_activo_nombre
    ON dbo.productos(activo, nombre_producto)
    INCLUDE (sku, id_categoria, id_unidad, stock_minimo, stock_maximo, requiere_lote);
END;
GO

IF OBJECT_ID(N'dbo.cuentas_logisticas', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_cuentas_logisticas_activo_nombre' AND object_id = OBJECT_ID(N'dbo.cuentas_logisticas'))
BEGIN
    CREATE INDEX IX_cuentas_logisticas_activo_nombre
    ON dbo.cuentas_logisticas(activo, nombre_cuenta)
    INCLUDE (codigo_cuenta, responsable, centro_costo);
END;
GO

IF OBJECT_ID(N'dbo.ubicaciones', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ubicaciones', N'es_surtible') IS NOT NULL
   AND COL_LENGTH(N'dbo.ubicaciones', N'es_stage') IS NOT NULL
   AND COL_LENGTH(N'dbo.ubicaciones', N'secuencia') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ubicaciones_picking' AND object_id = OBJECT_ID(N'dbo.ubicaciones'))
BEGIN
    EXEC(N'CREATE INDEX IX_ubicaciones_picking
          ON dbo.ubicaciones(activo, es_surtible, es_stage, secuencia, codigo_ubicacion)
          INCLUDE (id_zona, tipo_ubicacion);');
END;
GO

/* Movements and dashboard history. */
IF OBJECT_ID(N'dbo.movimientos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimientos_fecha_tipo' AND object_id = OBJECT_ID(N'dbo.movimientos'))
BEGIN
    CREATE INDEX IX_movimientos_fecha_tipo
    ON dbo.movimientos(fecha_movimiento DESC, tipo_movimiento)
    INCLUDE (id_movimiento, id_cuenta, id_proveedor, referencia, observacion, id_usuario, estado);
END;
GO

IF OBJECT_ID(N'dbo.movimiento_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_movimiento_detalle_movimiento' AND object_id = OBJECT_ID(N'dbo.movimiento_detalle'))
BEGIN
    CREATE INDEX IX_movimiento_detalle_movimiento
    ON dbo.movimiento_detalle(id_movimiento)
    INCLUDE (id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, lote, observacion);
END;
GO

/* Orders and picking. */
IF OBJECT_ID(N'dbo.pedidos', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_pedidos_estado_fecha' AND object_id = OBJECT_ID(N'dbo.pedidos'))
BEGIN
    CREATE INDEX IX_pedidos_estado_fecha
    ON dbo.pedidos(estado, fecha_pedido DESC, nro_pedido)
    INCLUDE (id_cuenta, solicitante, responsable_cuenta, qty_total, fecha_esperada_atencion);
END;
GO

IF OBJECT_ID(N'dbo.pedido_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_pedido_detalle_estado_pedido' AND object_id = OBJECT_ID(N'dbo.pedido_detalle'))
BEGIN
    CREATE INDEX IX_pedido_detalle_estado_pedido
    ON dbo.pedido_detalle(estado, id_pedido)
    INCLUDE (id_producto, nro_linea, codigo_unidad, cantidad_pedida, cantidad_asignada, cantidad_atendida, cantidad_cancelada, texto_item);
END;
GO

IF OBJECT_ID(N'dbo.picking_header', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_picking_header_estado_fecha' AND object_id = OBJECT_ID(N'dbo.picking_header'))
BEGIN
    CREATE INDEX IX_picking_header_estado_fecha
    ON dbo.picking_header(estado, fecha_creacion DESC, nro_picking)
    INCLUDE (qty_total, qty_asignada, qty_corto);
END;
GO

IF OBJECT_ID(N'dbo.picking_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_picking_detalle_picking_estado' AND object_id = OBJECT_ID(N'dbo.picking_detalle'))
BEGIN
    CREATE INDEX IX_picking_detalle_picking_estado
    ON dbo.picking_detalle(id_picking, estado)
    INCLUDE (id_pedido, id_pedido_detalle, id_cuenta, id_producto, id_ubicacion_origen, lote, cantidad_solicitada, cantidad_asignada, cantidad_atendida, cantidad_cancelada, secuencia, texto_item);
END;
GO

IF OBJECT_ID(N'dbo.picking_detalle', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_picking_detalle_pedido_detalle' AND object_id = OBJECT_ID(N'dbo.picking_detalle'))
BEGIN
    CREATE INDEX IX_picking_detalle_pedido_detalle
    ON dbo.picking_detalle(id_pedido_detalle, estado)
    INCLUDE (id_picking, id_producto, cantidad_asignada, cantidad_atendida, cantidad_cancelada);
END;
GO

/* Login lookup. Remove LOWER(column) in auth.py to benefit from these indexes. */
IF OBJECT_ID(N'dbo.usuarios', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.usuarios', N'usuario_login') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_usuarios_usuario_login_activo' AND object_id = OBJECT_ID(N'dbo.usuarios'))
BEGIN
    CREATE INDEX IX_usuarios_usuario_login_activo
    ON dbo.usuarios(usuario_login)
    INCLUDE (id_usuario, password_hash, id_rol, email, nombre)
    WHERE activo = 1;
END;
GO

IF OBJECT_ID(N'dbo.usuarios', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.usuarios', N'email') IS NOT NULL
   AND COL_LENGTH(N'dbo.usuarios', N'usuario_login') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_usuarios_email_activo' AND object_id = OBJECT_ID(N'dbo.usuarios'))
BEGIN
    CREATE INDEX IX_usuarios_email_activo
    ON dbo.usuarios(email)
    INCLUDE (id_usuario, password_hash, id_rol, usuario_login, nombre)
    WHERE activo = 1;
END;
GO

PRINT '015 - done';
