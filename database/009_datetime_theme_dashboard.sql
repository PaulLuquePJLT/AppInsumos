SET NOCOUNT ON;

/* ==========================================================
   Corrección función fecha/hora Bogotá - Lima - Perú UTC-5
   ========================================================== */

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

/* ==========================================================
   Actualizar valores NULL si existieran
   ========================================================== */

IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    UPDATE dbo.movimientos
    SET fecha_movimiento = dbo.fn_now_bogota_lima()
    WHERE fecha_movimiento IS NULL;
END;

/* ==========================================================
   Eliminar default anterior de movimientos.fecha_movimiento
   ========================================================== */

DECLARE @constraint_name NVARCHAR(200);
DECLARE @sql NVARCHAR(MAX);

SELECT @constraint_name = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c
    ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t
    ON t.object_id = c.object_id
INNER JOIN sys.schemas s
    ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'movimientos'
  AND c.name = 'fecha_movimiento';

IF @constraint_name IS NOT NULL
BEGIN
    SET @sql = N'ALTER TABLE dbo.movimientos DROP CONSTRAINT ' + QUOTENAME(@constraint_name);
    EXEC sp_executesql @sql;
END;

/* ==========================================================
   Crear nuevo default con hora Bogotá/Lima
   ========================================================== */

IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    ALTER TABLE dbo.movimientos
    ADD CONSTRAINT DF_movimientos_fecha_movimiento_bogota_lima
    DEFAULT dbo.fn_now_bogota_lima()
    FOR fecha_movimiento;
END;

SELECT dbo.fn_now_bogota_lima() AS fecha_hora_bogota_lima;
