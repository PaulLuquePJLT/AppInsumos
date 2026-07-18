SET NOCOUNT ON;

/* ==========================================================
   025 - Corregir visibilidad de pickings RF pendientes de aprobación
   ==========================================================
   Caso que corrige:
   - Existen movimientos SALIDA_CUENTA en PENDIENTE_APROBACION
     para un picking.
   - El picking no aparece en Atención Picking -> Aprobación RF
     porque el header quedó con estado o estado_aprobacion_admin
     desalineado luego de gestionar cortos.

   Este script no confirma movimientos ni descuenta stock.
   Solo marca el header para que vuelva a verse como pendiente.
   ========================================================== */

IF OBJECT_ID('dbo.picking_header', 'U') IS NULL
    THROW 52501, 'No existe dbo.picking_header.', 1;

IF OBJECT_ID('dbo.movimientos', 'U') IS NULL
    THROW 52502, 'No existe dbo.movimientos.', 1;

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

;WITH pending AS (
    SELECT DISTINCT
        REPLACE(m.referencia, 'PICKING ', '') AS nro_picking
    FROM dbo.movimientos m
    WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
      AND m.estado = 'PENDIENTE_APROBACION'
      AND m.referencia LIKE 'PICKING %'
)
UPDATE ph
SET requiere_aprobacion_admin = 1,
    estado_aprobacion_admin = 'PENDIENTE',
    fecha_actualizacion = dbo.fn_now_bogota_lima()
FROM dbo.picking_header ph
INNER JOIN pending p
    ON p.nro_picking = ph.nro_picking;

SELECT
    'OK - headers de picking con movimientos pendientes de aprobacion actualizados' AS resultado,
    @@ROWCOUNT AS pickings_actualizados;

SELECT
    ph.id_picking,
    ph.nro_picking,
    ph.estado,
    ph.requiere_aprobacion_admin,
    ph.estado_aprobacion_admin,
    COUNT(DISTINCT m.id_movimiento) AS movimientos_pendientes
FROM dbo.picking_header ph
INNER JOIN dbo.movimientos m
    ON m.referencia = 'PICKING ' + ph.nro_picking
WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
  AND m.estado = 'PENDIENTE_APROBACION'
GROUP BY
    ph.id_picking,
    ph.nro_picking,
    ph.estado,
    ph.requiere_aprobacion_admin,
    ph.estado_aprobacion_admin
ORDER BY ph.nro_picking;
