SET NOCOUNT ON;

CREATE OR ALTER VIEW vw_stock_general AS
SELECT
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    p.stock_minimo,
    p.stock_maximo,
    SUM(ISNULL(su.cantidad_actual, 0)) AS cantidad_total
FROM productos p
LEFT JOIN unidades_medida u ON u.id_unidad = p.id_unidad
LEFT JOIN stock_ubicacion su ON su.id_producto = p.id_producto
GROUP BY p.id_producto, p.sku, p.nombre_producto, u.codigo_unidad, u.nombre_unidad, p.stock_minimo, p.stock_maximo;
GO

CREATE OR ALTER VIEW vw_stock_por_ubicacion AS
SELECT
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    z.codigo_zona,
    z.nombre_zona,
    ub.codigo_ubicacion,
    ub.tipo_ubicacion,
    su.lote,
    su.cantidad_actual,
    su.fecha_actualizacion
FROM stock_ubicacion su
INNER JOIN productos p ON p.id_producto = su.id_producto
INNER JOIN unidades_medida u ON u.id_unidad = p.id_unidad
INNER JOIN ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona;
GO

CREATE OR ALTER VIEW vw_stock_por_cuenta AS
SELECT
    c.id_cuenta,
    c.codigo_cuenta,
    c.nombre_cuenta,
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    sc.cantidad_entregada,
    sc.cantidad_devuelta,
    sc.cantidad_neta,
    sc.fecha_actualizacion
FROM stock_cuenta sc
INNER JOIN cuentas_logisticas c ON c.id_cuenta = sc.id_cuenta
INNER JOIN productos p ON p.id_producto = sc.id_producto
INNER JOIN unidades_medida u ON u.id_unidad = p.id_unidad;
GO

CREATE OR ALTER VIEW vw_movimientos AS
SELECT
    m.id_movimiento,
    m.tipo_movimiento,
    m.fecha_movimiento,
    ISNULL(c.codigo_cuenta, '') AS codigo_cuenta,
    ISNULL(c.nombre_cuenta, '') AS nombre_cuenta,
    p.sku,
    p.nombre_producto,
    ub_origen.codigo_ubicacion AS ubicacion_origen,
    ub_destino.codigo_ubicacion AS ubicacion_destino,
    md.cantidad,
    md.lote,
    m.referencia,
    m.observacion,
    m.id_usuario,
    m.estado
FROM movimientos m
LEFT JOIN movimiento_detalle md ON md.id_movimiento = m.id_movimiento
LEFT JOIN productos p ON p.id_producto = md.id_producto
LEFT JOIN ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
LEFT JOIN ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
LEFT JOIN cuentas_logisticas c ON c.id_cuenta = m.id_cuenta;
GO
