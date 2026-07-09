/* Validación de pickings RF con movimientos pendientes de aprobación */
SET NOCOUNT ON;

SELECT
    ph.id_picking,
    ph.nro_picking,
    ph.estado AS estado_picking,
    ph.estado_aprobacion_admin,
    COUNT(DISTINCT m.id_movimiento) AS movimientos_pendientes,
    CAST(SUM(ISNULL(md.cantidad, 0)) AS DECIMAL(18,2)) AS cantidad_pendiente_aprobacion
FROM dbo.picking_header ph
INNER JOIN dbo.movimientos m
    ON m.referencia = 'PICKING ' + ph.nro_picking
INNER JOIN dbo.movimiento_detalle md
    ON md.id_movimiento = m.id_movimiento
WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
  AND m.estado = 'PENDIENTE_APROBACION'
GROUP BY
    ph.id_picking,
    ph.nro_picking,
    ph.estado,
    ph.estado_aprobacion_admin
ORDER BY ph.nro_picking DESC;
