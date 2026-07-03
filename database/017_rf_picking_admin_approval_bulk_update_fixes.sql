SET NOCOUNT ON;

/* ==========================================================
   017 - RF Picking pendiente de aprobacion administrador,
         correccion dashboard/picking y soporte de auditoria.
   ========================================================== */

/* 1) Asegurar funcion de hora local Bogota/Lima */
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

/* 2) Columnas de aprobacion en picking_header */
IF OBJECT_ID('dbo.picking_header', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.picking_header', 'origen_atencion') IS NULL
    BEGIN
        ALTER TABLE dbo.picking_header ADD origen_atencion NVARCHAR(20) NULL;
    END;

    IF COL_LENGTH('dbo.picking_header', 'requiere_aprobacion_admin') IS NULL
    BEGIN
        ALTER TABLE dbo.picking_header
        ADD requiere_aprobacion_admin BIT NOT NULL
            CONSTRAINT DF_picking_header_req_aprobacion DEFAULT 0;
    END;

    IF COL_LENGTH('dbo.picking_header', 'estado_aprobacion_admin') IS NULL
    BEGIN
        ALTER TABLE dbo.picking_header
        ADD estado_aprobacion_admin NVARCHAR(30) NOT NULL
            CONSTRAINT DF_picking_header_estado_aprobacion DEFAULT 'NO_REQUIERE';
    END;

    IF COL_LENGTH('dbo.picking_header', 'id_usuario_aprobacion') IS NULL
    BEGIN
        ALTER TABLE dbo.picking_header ADD id_usuario_aprobacion INT NULL;
    END;

    IF COL_LENGTH('dbo.picking_header', 'fecha_aprobacion') IS NULL
    BEGIN
        ALTER TABLE dbo.picking_header ADD fecha_aprobacion DATETIME2 NULL;
    END;

    EXEC(N'
    UPDATE dbo.picking_header
    SET origen_atencion = ISNULL(origen_atencion, ''DESKTOP''),
        estado_aprobacion_admin = ISNULL(estado_aprobacion_admin, ''NO_REQUIERE'')
    WHERE origen_atencion IS NULL OR estado_aprobacion_admin IS NULL;
    ');
END;

/* 3) Relacion detalle movimiento-tarea picking */
IF OBJECT_ID('dbo.movimiento_detalle', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.movimiento_detalle', 'id_picking_detalle') IS NULL
    BEGIN
        ALTER TABLE dbo.movimiento_detalle ADD id_picking_detalle INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.foreign_keys
        WHERE name = 'FK_movimiento_detalle_picking_detalle'
          AND parent_object_id = OBJECT_ID('dbo.movimiento_detalle')
    )
    BEGIN
        ALTER TABLE dbo.movimiento_detalle
        ADD CONSTRAINT FK_movimiento_detalle_picking_detalle
        FOREIGN KEY (id_picking_detalle) REFERENCES dbo.picking_detalle(id_picking_detalle);
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_movimiento_detalle_picking_detalle'
          AND object_id = OBJECT_ID('dbo.movimiento_detalle')
    )
    BEGIN
        CREATE INDEX IX_movimiento_detalle_picking_detalle
        ON dbo.movimiento_detalle(id_picking_detalle);
    END;
END;

/* 4) Ajustar trigger vida util para solo programar movimientos confirmados */
IF OBJECT_ID('dbo.trg_movimiento_detalle_programar_vida_util_cuenta', 'TR') IS NOT NULL
BEGIN
    DROP TRIGGER dbo.trg_movimiento_detalle_programar_vida_util_cuenta;
END;

IF OBJECT_ID('dbo.stock_cuenta_vencimiento', 'U') IS NOT NULL
BEGIN
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
          AND m.estado = ''CONFIRMADO''
          AND ISNULL(p.vida_util_cuenta_dias, 0) > 0
          AND m.id_cuenta IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM dbo.stock_cuenta_vencimiento v
              WHERE v.id_detalle = i.id_detalle
          );
    END
    ');
END;

/* 5) Vista de resumen de picking compatible con aprobacion */
IF OBJECT_ID('dbo.picking_header', 'U') IS NOT NULL
BEGIN
    EXEC(N'
    CREATE OR ALTER VIEW dbo.vw_picking_resumen AS
    SELECT
        ph.id_picking,
        ph.nro_picking,
        ph.fecha_creacion,
        ph.fecha_actualizacion,
        ph.estado,
        ISNULL(ph.origen_atencion, ''DESKTOP'') AS origen_atencion,
        ISNULL(ph.requiere_aprobacion_admin, 0) AS requiere_aprobacion_admin,
        ISNULL(ph.estado_aprobacion_admin, ''NO_REQUIERE'') AS estado_aprobacion_admin,
        ph.id_usuario_creacion,
        uc.usuario_login AS usuario_creacion,
        ph.id_usuario_aprobacion,
        ua.usuario_login AS usuario_aprobacion,
        ph.fecha_aprobacion,
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
    LEFT JOIN dbo.usuarios uc ON uc.id_usuario = ph.id_usuario_creacion
    LEFT JOIN dbo.usuarios ua ON ua.id_usuario = ph.id_usuario_aprobacion
    GROUP BY
        ph.id_picking,
        ph.nro_picking,
        ph.fecha_creacion,
        ph.fecha_actualizacion,
        ph.estado,
        ph.origen_atencion,
        ph.requiere_aprobacion_admin,
        ph.estado_aprobacion_admin,
        ph.id_usuario_creacion,
        uc.usuario_login,
        ph.id_usuario_aprobacion,
        ua.usuario_login,
        ph.fecha_aprobacion,
        ph.qty_total,
        ph.qty_asignada,
        ph.qty_corto;
    ');
END;

SELECT 'OK - migracion 017 aplicada correctamente' AS resultado;
