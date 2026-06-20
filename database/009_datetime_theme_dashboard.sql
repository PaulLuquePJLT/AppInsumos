SET NOCOUNT ON;

/* ================================================================
   009 - Fecha/hora local Bogota-Lima, vista dashboard y UI
   ================================================================ */

/* 1) Funcion central para fecha/hora local Bogota/Lima/Peru.
      Bogota y Lima usan UTC-05:00. Se usa SYSUTCDATETIME para evitar
      depender de la zona horaria del servidor de Azure SQL. */
CREATE OR ALTER FUNCTION dbo.fn_now_bogota_lima()
RETURNS DATETIME2(0)
AS
BEGIN
    RETURN CAST(DATEADD(HOUR, -5, SYSUTCDATETIME()) AS DATETIME2(0));
END;
GO

/* 2) Default de movimientos.fecha_movimiento con hora local de ejecucion. */
IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
   AND COL_LENGTH('dbo.movimientos', 'fecha_movimiento') IS NOT NULL
BEGIN
    DECLARE @constraint_name SYSNAME;

    SELECT @constraint_name = dc.name
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c
        ON c.default_object_id = dc.object_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.movimientos')
      AND c.name = 'fecha_movimiento';

    IF @constraint_name IS NOT NULL
    BEGIN
        DECLARE @sql NVARCHAR(MAX) = N'ALTER TABLE dbo.movimientos DROP CONSTRAINT ' + QUOTENAME(@constraint_name) + N';';
        EXEC sp_executesql @sql;
    END;

    ALTER TABLE dbo.movimientos
    ADD CONSTRAINT DF_movimientos_fecha_movimiento_bogota_lima
    DEFAULT dbo.fn_now_bogota_lima() FOR fecha_movimiento;
END;
GO

/* 3) Vista de movimientos enriquecida para dashboard. */
CREATE OR ALTER VIEW dbo.vw_movimientos AS
SELECT
    m.id_movimiento,
    m.tipo_movimiento,
    m.fecha_movimiento,
    ISNULL(c.codigo_cuenta, '') AS codigo_cuenta,
    ISNULL(c.nombre_cuenta, '') AS nombre_cuenta,
    ISNULL(pr.ruc, '') AS ruc_proveedor,
    ISNULL(pr.razon_social, '') AS razon_social_proveedor,
    p.sku,
    p.nombre_producto,
    ISNULL(um.codigo_unidad, '') AS codigo_unidad,
    ISNULL(um.nombre_unidad, '') AS nombre_unidad,
    ub_origen.codigo_ubicacion AS ubicacion_origen,
    ub_destino.codigo_ubicacion AS ubicacion_destino,
    CAST(ISNULL(md.cantidad, 0) AS DECIMAL(18,2)) AS cantidad,
    md.lote,
    m.referencia,
    m.observacion,
    md.observacion AS texto_item,
    m.id_usuario,
    ISNULL(u.usuario_login, '') AS usuario_login,
    LTRIM(RTRIM(ISNULL(u.nombres, '') + ' ' + ISNULL(u.apellidos, ''))) AS usuario_nombre,
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
GO

SELECT
    'OK - 009 aplicado. Fecha movimiento ahora usa dbo.fn_now_bogota_lima().' AS resultado,
    dbo.fn_now_bogota_lima() AS fecha_hora_bogota_lima;
