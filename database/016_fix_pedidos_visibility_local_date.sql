SET NOCOUNT ON;

/* ==========================================================
   016 - Correccion visibilidad de pedidos por fecha local
   ========================================================== */

IF OBJECT_ID('dbo.pedidos', 'U') IS NULL
BEGIN
    THROW 51601, 'No existe la tabla dbo.pedidos.', 1;
END;

IF OBJECT_ID('dbo.pedido_detalle', 'U') IS NULL
BEGIN
    THROW 51602, 'No existe la tabla dbo.pedido_detalle.', 1;
END;

/* Asegura funcion local si no existiera. */
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

/* Reemplaza default de fecha_pedido para inserts directos en SQL. */
DECLARE @constraint_name NVARCHAR(200);
DECLARE @sql NVARCHAR(MAX);

SELECT @constraint_name = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t ON t.object_id = c.object_id
INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'pedidos'
  AND c.name = 'fecha_pedido';

IF @constraint_name IS NOT NULL
BEGIN
    SET @sql = N'ALTER TABLE dbo.pedidos DROP CONSTRAINT ' + QUOTENAME(@constraint_name);
    EXEC sp_executesql @sql;
END;

ALTER TABLE dbo.pedidos
ADD CONSTRAINT DF_pedidos_fecha_pedido_bogota_lima
DEFAULT CAST(dbo.fn_now_bogota_lima() AS DATE)
FOR fecha_pedido;

/* Recreate view with LEFT JOIN so header-only orders are visible for diagnosis. */
EXEC(N'
CREATE OR ALTER VIEW dbo.vw_pedidos_resumen AS
SELECT
    p.id_pedido,
    p.nro_pedido,
    CAST(p.fecha_pedido AS DATE) AS fecha_pedido,
    p.fecha_esperada_atencion,
    p.id_cuenta,
    c.codigo_cuenta,
    c.nombre_cuenta,
    p.solicitante,
    p.responsable_cuenta,
    p.texto_cabecera,
    CAST(ISNULL(p.qty_total, SUM(ISNULL(pd.cantidad_pedida, 0))) AS DECIMAL(18,2)) AS qty_total,
    p.estado,
    COUNT(pd.id_pedido_detalle) AS lineas,
    CAST(SUM(
        ISNULL(pd.cantidad_pedida, 0)
        - ISNULL(pd.cantidad_asignada, 0)
        - ISNULL(pd.cantidad_cancelada, 0)
    ) AS DECIMAL(18,2)) AS cantidad_pendiente_picking,
    CAST(SUM(
        ISNULL(pd.cantidad_pedida, 0)
        - ISNULL(pd.cantidad_atendida, 0)
        - ISNULL(pd.cantidad_cancelada, 0)
    ) AS DECIMAL(18,2)) AS cantidad_pendiente_atencion
FROM dbo.pedidos p
INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = p.id_cuenta
LEFT JOIN dbo.pedido_detalle pd ON pd.id_pedido = p.id_pedido
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

SELECT
    'OK - pedidos visibles con fecha local y vista corregida' AS resultado,
    CAST(dbo.fn_now_bogota_lima() AS DATE) AS fecha_local_bogota_lima;
