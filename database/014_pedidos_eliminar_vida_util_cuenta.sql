SET NOCOUNT ON;

/* ================================================================
   014 - Eliminar pedidos seleccionados y vida util de stock en cuenta
   ================================================================ */

IF OBJECT_ID('dbo.productos', 'U') IS NULL
BEGIN
    THROW 51401, 'No existe la tabla dbo.productos.', 1;
END;

IF OBJECT_ID('dbo.pedidos', 'U') IS NULL
BEGIN
    THROW 51402, 'No existe la tabla dbo.pedidos. Ejecuta antes la migracion 008.', 1;
END;

IF OBJECT_ID('dbo.pedido_detalle', 'U') IS NULL
BEGIN
    THROW 51403, 'No existe la tabla dbo.pedido_detalle. Ejecuta antes la migracion 008.', 1;
END;

/* 1) Columna vida util en productos */
IF COL_LENGTH('dbo.productos', 'vida_util_cuenta_dias') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD vida_util_cuenta_dias INT NULL;
END;

EXEC(N'
UPDATE dbo.productos
SET vida_util_cuenta_dias = 0
WHERE vida_util_cuenta_dias IS NULL;
');

EXEC(N'
UPDATE dbo.productos
SET vida_util_cuenta_dias = 0
WHERE vida_util_cuenta_dias < 0;
');

EXEC(N'
ALTER TABLE dbo.productos
ALTER COLUMN vida_util_cuenta_dias INT NOT NULL;
');

DECLARE @df_vida NVARCHAR(200);
DECLARE @sql NVARCHAR(MAX);

SELECT @df_vida = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t ON t.object_id = c.object_id
INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'productos'
  AND c.name = 'vida_util_cuenta_dias';

IF @df_vida IS NULL
BEGIN
    EXEC(N'
    ALTER TABLE dbo.productos
    ADD CONSTRAINT DF_productos_vida_util_cuenta_dias
    DEFAULT 0 FOR vida_util_cuenta_dias;
    ');
END;

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_vida_util_cuenta_dias'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos DROP CONSTRAINT CK_productos_vida_util_cuenta_dias;
END;

EXEC(N'
ALTER TABLE dbo.productos
ADD CONSTRAINT CK_productos_vida_util_cuenta_dias
CHECK (vida_util_cuenta_dias >= 0);
');

/* 2) Columna de consumo automatico por vida util en stock_cuenta */
IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_consumida_vida_util') IS NULL
    BEGIN
        ALTER TABLE dbo.stock_cuenta
        ADD cantidad_consumida_vida_util DECIMAL(18,2) NULL;
    END;

    EXEC(N'
    UPDATE dbo.stock_cuenta
    SET cantidad_consumida_vida_util = 0
    WHERE cantidad_consumida_vida_util IS NULL;
    ');

    EXEC(N'
    UPDATE dbo.stock_cuenta
    SET cantidad_consumida_vida_util = 0
    WHERE cantidad_consumida_vida_util < 0;
    ');

    EXEC(N'
    ALTER TABLE dbo.stock_cuenta
    ALTER COLUMN cantidad_consumida_vida_util DECIMAL(18,2) NOT NULL;
    ');

    DECLARE @df_consumo NVARCHAR(200);

    SELECT @df_consumo = dc.name
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
    INNER JOIN sys.tables t ON t.object_id = c.object_id
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = 'stock_cuenta'
      AND c.name = 'cantidad_consumida_vida_util';

    IF @df_consumo IS NULL
    BEGIN
        EXEC(N'
        ALTER TABLE dbo.stock_cuenta
        ADD CONSTRAINT DF_stock_cuenta_consumida_vida_util
        DEFAULT 0 FOR cantidad_consumida_vida_util;
        ');
    END;

    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE name = 'CK_stock_cuenta_consumida_vida_util'
          AND parent_object_id = OBJECT_ID('dbo.stock_cuenta')
    )
    BEGIN
        ALTER TABLE dbo.stock_cuenta DROP CONSTRAINT CK_stock_cuenta_consumida_vida_util;
    END;

    EXEC(N'
    ALTER TABLE dbo.stock_cuenta
    ADD CONSTRAINT CK_stock_cuenta_consumida_vida_util
    CHECK (cantidad_consumida_vida_util >= 0);
    ');
END;

/* 3) Funcion hora local si no existe */
IF OBJECT_ID('dbo.fn_now_bogota_lima', 'FN') IS NULL
BEGIN
    EXEC(N'
    CREATE FUNCTION dbo.fn_now_bogota_lima()
    RETURNS DATETIME2(0)
    AS
    BEGIN
        RETURN CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), ''-05:00'') AS DATETIME2(0));
    END
    ');
END;

/* 4) Tabla de programacion de descuentos por vida util */
IF OBJECT_ID('dbo.stock_cuenta_vencimiento', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.stock_cuenta_vencimiento (
        id_vencimiento INT IDENTITY(1,1) PRIMARY KEY,
        id_movimiento INT NOT NULL,
        id_detalle INT NOT NULL,
        id_cuenta INT NOT NULL,
        id_producto INT NOT NULL,
        cantidad_programada DECIMAL(18,2) NOT NULL,
        cantidad_aplicada DECIMAL(18,2) NOT NULL DEFAULT 0,
        fecha_movimiento DATETIME2 NOT NULL,
        fecha_vencimiento DATE NOT NULL,
        estado NVARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
        fecha_aplicacion DATETIME2 NULL,
        fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT FK_scv_movimiento FOREIGN KEY (id_movimiento) REFERENCES dbo.movimientos(id_movimiento),
        CONSTRAINT FK_scv_detalle FOREIGN KEY (id_detalle) REFERENCES dbo.movimiento_detalle(id_detalle),
        CONSTRAINT FK_scv_cuenta FOREIGN KEY (id_cuenta) REFERENCES dbo.cuentas_logisticas(id_cuenta),
        CONSTRAINT FK_scv_producto FOREIGN KEY (id_producto) REFERENCES dbo.productos(id_producto),
        CONSTRAINT CK_scv_cantidad CHECK (cantidad_programada > 0 AND cantidad_aplicada >= 0),
        CONSTRAINT CK_scv_estado CHECK (estado IN ('PENDIENTE','PARCIAL','APLICADO','CANCELADO'))
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_stock_cuenta_vencimiento_detalle'
      AND object_id = OBJECT_ID('dbo.stock_cuenta_vencimiento')
)
BEGIN
    CREATE UNIQUE INDEX UX_stock_cuenta_vencimiento_detalle
    ON dbo.stock_cuenta_vencimiento(id_detalle);
END;

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_stock_cuenta_vencimiento_estado_fecha'
      AND object_id = OBJECT_ID('dbo.stock_cuenta_vencimiento')
)
BEGIN
    CREATE INDEX IX_stock_cuenta_vencimiento_estado_fecha
    ON dbo.stock_cuenta_vencimiento(estado, fecha_vencimiento, id_cuenta, id_producto);
END;

/* 5) Trigger para programar descuento cada vez que se registra SALIDA_CUENTA */
IF OBJECT_ID('dbo.trg_movimiento_detalle_programar_vida_util_cuenta', 'TR') IS NOT NULL
BEGIN
    DROP TRIGGER dbo.trg_movimiento_detalle_programar_vida_util_cuenta;
END;

EXEC(N'
CREATE TRIGGER dbo.trg_movimiento_detalle_programar_vida_util_cuenta
ON dbo.movimiento_detalle
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO dbo.stock_cuenta_vencimiento
        (
            id_movimiento,
            id_detalle,
            id_cuenta,
            id_producto,
            cantidad_programada,
            cantidad_aplicada,
            fecha_movimiento,
            fecha_vencimiento,
            estado
        )
    SELECT
        m.id_movimiento,
        i.id_detalle,
        m.id_cuenta,
        i.id_producto,
        CAST(i.cantidad AS DECIMAL(18,2)),
        0,
        m.fecha_movimiento,
        DATEADD(DAY, ISNULL(p.vida_util_cuenta_dias, 0), CAST(m.fecha_movimiento AS DATE)),
        ''PENDIENTE''
    FROM inserted i
    INNER JOIN dbo.movimientos m ON m.id_movimiento = i.id_movimiento
    INNER JOIN dbo.productos p ON p.id_producto = i.id_producto
    WHERE m.tipo_movimiento = ''SALIDA_CUENTA''
      AND m.id_cuenta IS NOT NULL
      AND ISNULL(p.vida_util_cuenta_dias, 0) > 0
      AND i.cantidad > 0
      AND NOT EXISTS (
            SELECT 1
            FROM dbo.stock_cuenta_vencimiento v
            WHERE v.id_detalle = i.id_detalle
      );
END
');

/* 6) Procedimiento para aplicar vencimientos pendientes */
IF OBJECT_ID('dbo.sp_aplicar_vencimientos_stock_cuenta', 'P') IS NOT NULL
BEGIN
    DROP PROCEDURE dbo.sp_aplicar_vencimientos_stock_cuenta;
END;

EXEC(N'
CREATE PROCEDURE dbo.sp_aplicar_vencimientos_stock_cuenta
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @hoy DATE = CAST(dbo.fn_now_bogota_lima() AS DATE);

    DECLARE @aplicar TABLE (
        id_vencimiento INT PRIMARY KEY,
        id_cuenta INT NOT NULL,
        id_producto INT NOT NULL,
        qty_aplicar DECIMAL(18,2) NOT NULL
    );

    ;WITH vencidos AS (
        SELECT
            v.id_vencimiento,
            v.id_cuenta,
            v.id_producto,
            CAST(v.cantidad_programada - v.cantidad_aplicada AS DECIMAL(18,2)) AS qty_pendiente,
            CAST(
                ISNULL(sc.cantidad_entregada, 0)
                - ISNULL(sc.cantidad_devuelta, 0)
                - ISNULL(sc.cantidad_consumida_vida_util, 0)
                AS DECIMAL(18,2)
            ) AS cantidad_disponible,
            CAST(
                ISNULL(
                    SUM(v.cantidad_programada - v.cantidad_aplicada) OVER (
                        PARTITION BY v.id_cuenta, v.id_producto
                        ORDER BY v.fecha_vencimiento, v.id_vencimiento
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ),
                    0
                ) AS DECIMAL(18,2)
            ) AS qty_previa
        FROM dbo.stock_cuenta_vencimiento v WITH (UPDLOCK, ROWLOCK)
        INNER JOIN dbo.stock_cuenta sc WITH (UPDLOCK, ROWLOCK)
            ON sc.id_cuenta = v.id_cuenta
           AND sc.id_producto = v.id_producto
        WHERE v.estado IN (''PENDIENTE'', ''PARCIAL'')
          AND v.fecha_vencimiento <= @hoy
          AND (v.cantidad_programada - v.cantidad_aplicada) > 0
    ), calculado AS (
        SELECT
            id_vencimiento,
            id_cuenta,
            id_producto,
            CAST(
                CASE
                    WHEN cantidad_disponible <= qty_previa THEN 0
                    WHEN cantidad_disponible - qty_previa >= qty_pendiente THEN qty_pendiente
                    ELSE cantidad_disponible - qty_previa
                END AS DECIMAL(18,2)
            ) AS qty_aplicar
        FROM vencidos
    )
    INSERT INTO @aplicar (id_vencimiento, id_cuenta, id_producto, qty_aplicar)
    SELECT id_vencimiento, id_cuenta, id_producto, qty_aplicar
    FROM calculado
    WHERE qty_aplicar > 0;

    UPDATE sc
    SET sc.cantidad_consumida_vida_util = ISNULL(sc.cantidad_consumida_vida_util, 0) + a.qty_aplicar,
        sc.fecha_actualizacion = SYSDATETIME()
    FROM dbo.stock_cuenta sc
    INNER JOIN @aplicar a
        ON a.id_cuenta = sc.id_cuenta
       AND a.id_producto = sc.id_producto;

    UPDATE v
    SET v.cantidad_aplicada = v.cantidad_aplicada + a.qty_aplicar,
        v.estado = CASE
            WHEN v.cantidad_programada <= v.cantidad_aplicada + a.qty_aplicar THEN ''APLICADO''
            ELSE ''PARCIAL''
        END,
        v.fecha_aplicacion = CASE
            WHEN v.cantidad_programada <= v.cantidad_aplicada + a.qty_aplicar THEN dbo.fn_now_bogota_lima()
            ELSE v.fecha_aplicacion
        END,
        v.fecha_actualizacion = SYSDATETIME()
    FROM dbo.stock_cuenta_vencimiento v
    INNER JOIN @aplicar a ON a.id_vencimiento = v.id_vencimiento;
END
');

/* 7) Vista de stock por cuenta actualizada */
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
        ISNULL(p.vida_util_cuenta_dias, 0) AS vida_util_cuenta_dias,
        CAST(ISNULL(sc.cantidad_entregada, 0) AS DECIMAL(18,2)) AS cantidad_entregada,
        CAST(ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_devuelta,
        CAST(ISNULL(sc.cantidad_consumida_vida_util, 0) AS DECIMAL(18,2)) AS cantidad_consumida_vida_util,
        CAST(
            ISNULL(sc.cantidad_entregada, 0)
            - ISNULL(sc.cantidad_devuelta, 0)
            - ISNULL(sc.cantidad_consumida_vida_util, 0)
            AS DECIMAL(18,2)
        ) AS cantidad_neta,
        CAST(
            (
                ISNULL(sc.cantidad_entregada, 0)
                - ISNULL(sc.cantidad_devuelta, 0)
                - ISNULL(sc.cantidad_consumida_vida_util, 0)
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
          ) > 0;
    ');
END;

/* 8) Vista de movimientos con fecha de vencimiento en cuenta */
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

SELECT 'OK - vida util cuenta y eliminacion segura de pedidos aplicada' AS resultado;

EXEC(N'
SELECT TOP 10
    id_producto,
    sku,
    nombre_producto,
    vida_util_cuenta_dias
FROM dbo.productos
ORDER BY id_producto DESC;
');
