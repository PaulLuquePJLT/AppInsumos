SET NOCOUNT ON;

/* ================================================================
   008 - Pedidos, Picking, Atención de Picking y Transferencia masiva
   ================================================================ */

/* 1) Ubicaciones: secuencia de picking y flags operativos */
IF COL_LENGTH('dbo.ubicaciones', 'secuencia') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD secuencia INT NOT NULL CONSTRAINT DF_ubicaciones_secuencia DEFAULT 999999;
END;

IF COL_LENGTH('dbo.ubicaciones', 'es_surtible') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD es_surtible BIT NOT NULL CONSTRAINT DF_ubicaciones_es_surtible DEFAULT 1;
END;

IF COL_LENGTH('dbo.ubicaciones', 'es_stage') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD es_stage BIT NOT NULL CONSTRAINT DF_ubicaciones_es_stage DEFAULT 0;
END;

EXEC(N'
UPDATE dbo.ubicaciones
SET es_stage = 1,
    es_surtible = 0,
    secuencia = CASE WHEN secuencia = 999999 THEN 0 ELSE secuencia END
WHERE codigo_ubicacion IN (''B1.RE.01'');
');

/* 2) Stock: cantidad reservada/en picking */
IF COL_LENGTH('dbo.stock_ubicacion', 'cantidad_en_picking') IS NULL
BEGIN
    ALTER TABLE dbo.stock_ubicacion
    ADD cantidad_en_picking DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_ubicacion_cantidad_en_picking DEFAULT 0;
END;

/* 3) Cabecera de pedidos */
IF OBJECT_ID('dbo.pedidos', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.pedidos (
        id_pedido INT IDENTITY(1,1) PRIMARY KEY,
        nro_pedido NVARCHAR(20) NOT NULL UNIQUE,
        fecha_pedido DATE NOT NULL DEFAULT CAST(SYSDATETIME() AS DATE),
        fecha_esperada_atencion DATE NULL,
        id_cuenta INT NOT NULL,
        solicitante NVARCHAR(150) NULL,
        responsable_cuenta NVARCHAR(150) NULL,
        texto_cabecera NVARCHAR(300) NULL,
        qty_total DECIMAL(18,2) NOT NULL DEFAULT 0,
        estado NVARCHAR(30) NOT NULL DEFAULT 'CREADO',
        id_usuario_creacion INT NULL,
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT FK_pedidos_cuenta FOREIGN KEY (id_cuenta) REFERENCES dbo.cuentas_logisticas(id_cuenta),
        CONSTRAINT FK_pedidos_usuario FOREIGN KEY (id_usuario_creacion) REFERENCES dbo.usuarios(id_usuario),
        CONSTRAINT CK_pedidos_estado CHECK (estado IN (
            'CREADO','EN_PICKING','COMPLETADO','COMPLETADO-PARCIAL','COMPLETADO-CORTO','CANCELADO'
        ))
    );
END;

/* 4) Detalle de pedidos */
IF OBJECT_ID('dbo.pedido_detalle', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.pedido_detalle (
        id_pedido_detalle INT IDENTITY(1,1) PRIMARY KEY,
        id_pedido INT NOT NULL,
        nro_linea INT NOT NULL,
        id_producto INT NOT NULL,
        codigo_unidad NVARCHAR(20) NULL,
        cantidad_pedida DECIMAL(18,2) NOT NULL,
        cantidad_asignada DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_atendida DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_cancelada DECIMAL(18,2) NOT NULL DEFAULT 0,
        texto_item NVARCHAR(250) NULL,
        estado NVARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT FK_pedido_detalle_pedido FOREIGN KEY (id_pedido) REFERENCES dbo.pedidos(id_pedido),
        CONSTRAINT FK_pedido_detalle_producto FOREIGN KEY (id_producto) REFERENCES dbo.productos(id_producto),
        CONSTRAINT CK_pedido_detalle_cantidad CHECK (cantidad_pedida > 0),
        CONSTRAINT CK_pedido_detalle_estado CHECK (estado IN (
            'PENDIENTE','EN_PICKING','CORTO','COMPLETADO','CANCELADO'
        ))
    );

    CREATE UNIQUE INDEX UX_pedido_detalle_linea
    ON dbo.pedido_detalle(id_pedido, nro_linea);
END;

/* 5) Cabecera de picking */
IF OBJECT_ID('dbo.picking_header', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.picking_header (
        id_picking INT IDENTITY(1,1) PRIMARY KEY,
        nro_picking NVARCHAR(20) NOT NULL UNIQUE,
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        estado NVARCHAR(30) NOT NULL DEFAULT 'LIBERADO',
        id_usuario_creacion INT NULL,
        texto_cabecera NVARCHAR(300) NULL,
        qty_total DECIMAL(18,2) NOT NULL DEFAULT 0,
        qty_asignada DECIMAL(18,2) NOT NULL DEFAULT 0,
        qty_corto DECIMAL(18,2) NOT NULL DEFAULT 0,
        CONSTRAINT FK_picking_usuario FOREIGN KEY (id_usuario_creacion) REFERENCES dbo.usuarios(id_usuario),
        CONSTRAINT CK_picking_estado CHECK (estado IN (
            'LIBERADO','LIBERADO-CORTO','COMPLETADO','COMPLETADO-PARCIAL','COMPLETADO-CORTO','CANCELADO'
        ))
    );
END;

/* 6) Relación picking-pedido */
IF OBJECT_ID('dbo.picking_pedido', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.picking_pedido (
        id_picking_pedido INT IDENTITY(1,1) PRIMARY KEY,
        id_picking INT NOT NULL,
        id_pedido INT NOT NULL,
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        CONSTRAINT FK_picking_pedido_picking FOREIGN KEY (id_picking) REFERENCES dbo.picking_header(id_picking),
        CONSTRAINT FK_picking_pedido_pedido FOREIGN KEY (id_pedido) REFERENCES dbo.pedidos(id_pedido)
    );

    CREATE UNIQUE INDEX UX_picking_pedido
    ON dbo.picking_pedido(id_picking, id_pedido);
END;

/* 7) Detalle de picking/tareas */
IF OBJECT_ID('dbo.picking_detalle', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.picking_detalle (
        id_picking_detalle INT IDENTITY(1,1) PRIMARY KEY,
        id_picking INT NOT NULL,
        id_pedido INT NOT NULL,
        id_pedido_detalle INT NOT NULL,
        nro_pedido NVARCHAR(20) NULL,
        id_cuenta INT NOT NULL,
        id_producto INT NOT NULL,
        id_ubicacion_origen INT NULL,
        lote NVARCHAR(80) NULL,
        cantidad_solicitada DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_asignada DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_atendida DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_cancelada DECIMAL(18,2) NOT NULL DEFAULT 0,
        estado NVARCHAR(30) NOT NULL DEFAULT 'LIBERADO',
        secuencia INT NOT NULL DEFAULT 999999,
        texto_item NVARCHAR(250) NULL,
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT FK_picking_detalle_picking FOREIGN KEY (id_picking) REFERENCES dbo.picking_header(id_picking),
        CONSTRAINT FK_picking_detalle_pedido FOREIGN KEY (id_pedido) REFERENCES dbo.pedidos(id_pedido),
        CONSTRAINT FK_picking_detalle_pedido_detalle FOREIGN KEY (id_pedido_detalle) REFERENCES dbo.pedido_detalle(id_pedido_detalle),
        CONSTRAINT FK_picking_detalle_cuenta FOREIGN KEY (id_cuenta) REFERENCES dbo.cuentas_logisticas(id_cuenta),
        CONSTRAINT FK_picking_detalle_producto FOREIGN KEY (id_producto) REFERENCES dbo.productos(id_producto),
        CONSTRAINT FK_picking_detalle_ubicacion FOREIGN KEY (id_ubicacion_origen) REFERENCES dbo.ubicaciones(id_ubicacion),
        CONSTRAINT CK_picking_detalle_estado CHECK (estado IN (
            'LIBERADO','CORTO','REASIGNADO','CANCELADO','COMPLETADO'
        ))
    );
END;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_picking_detalle_estado' AND object_id = OBJECT_ID('dbo.picking_detalle'))
BEGIN
    CREATE INDEX IX_picking_detalle_estado
    ON dbo.picking_detalle(estado, id_picking, id_pedido);
END;

/* 8) Vistas actualizadas */
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
    CAST(SUM(ISNULL(su.cantidad_actual, 0)) AS DECIMAL(18,2)) AS cantidad_total,
    CAST(SUM(ISNULL(su.cantidad_en_picking, 0)) AS DECIMAL(18,2)) AS cantidad_en_picking,
    CAST(SUM(ISNULL(su.cantidad_actual, 0) - ISNULL(su.cantidad_en_picking, 0)) AS DECIMAL(18,2)) AS cantidad_disponible
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
    p.stock_maximo;
');

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
    CAST(su.cantidad_actual AS DECIMAL(18,2)) AS cantidad_actual,
    CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_en_picking,
    CAST(su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible,
    su.fecha_actualizacion
FROM dbo.stock_ubicacion su
INNER JOIN dbo.productos p ON p.id_producto = su.id_producto
INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
INNER JOIN dbo.zonas_almacen z ON z.id_zona = ub.id_zona
WHERE ISNULL(p.activo, 1) = 1
  AND ISNULL(ub.activo, 1) = 1;
');

EXEC(N'
CREATE OR ALTER VIEW dbo.vw_pedidos_resumen AS
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
    p.qty_total,
    p.estado,
    COUNT(pd.id_pedido_detalle) AS lineas,
    CAST(SUM(pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada) AS DECIMAL(18,2)) AS cantidad_pendiente_picking,
    CAST(SUM(pd.cantidad_pedida - pd.cantidad_atendida - pd.cantidad_cancelada) AS DECIMAL(18,2)) AS cantidad_pendiente_atencion
FROM dbo.pedidos p
INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = p.id_cuenta
INNER JOIN dbo.pedido_detalle pd ON pd.id_pedido = p.id_pedido
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
    p.qty_total,
    p.estado;
');

EXEC(N'
CREATE OR ALTER VIEW dbo.vw_picking_resumen AS
SELECT
    ph.id_picking,
    ph.nro_picking,
    ph.fecha_creacion,
    ph.estado,
    ph.qty_total,
    ph.qty_asignada,
    ph.qty_corto,
    COUNT(DISTINCT pp.id_pedido) AS pedidos,
    SUM(CASE WHEN pd.estado = ''LIBERADO'' THEN 1 ELSE 0 END) AS tareas_pendientes,
    SUM(CASE WHEN pd.estado = ''CORTO'' THEN 1 ELSE 0 END) AS cortos_activos,
    SUM(CASE WHEN pd.estado = ''CANCELADO'' THEN 1 ELSE 0 END) AS cortos_cancelados,
    SUM(CASE WHEN pd.estado = ''COMPLETADO'' THEN 1 ELSE 0 END) AS tareas_completadas
FROM dbo.picking_header ph
LEFT JOIN dbo.picking_pedido pp ON pp.id_picking = ph.id_picking
LEFT JOIN dbo.picking_detalle pd ON pd.id_picking = ph.id_picking
GROUP BY
    ph.id_picking,
    ph.nro_picking,
    ph.fecha_creacion,
    ph.estado,
    ph.qty_total,
    ph.qty_asignada,
    ph.qty_corto;
');

SELECT 'OK - pedidos, picking, secuencia y transferencia masiva listos' AS resultado;
