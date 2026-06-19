SET NOCOUNT ON;

/* ================================================================
   007 - Corrección de vistas de stock y stock por cuenta
   Este script corrige los errores de las páginas Stock y Stock Cuentas.
   ================================================================ */

IF OBJECT_ID('dbo.productos', 'U') IS NULL
    THROW 50701, 'No existe la tabla dbo.productos.', 1;

IF OBJECT_ID('dbo.unidades_medida', 'U') IS NULL
    THROW 50702, 'No existe la tabla dbo.unidades_medida.', 1;

IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NULL
    THROW 50703, 'No existe la tabla dbo.stock_ubicacion.', 1;

IF OBJECT_ID('dbo.ubicaciones', 'U') IS NULL
    THROW 50704, 'No existe la tabla dbo.ubicaciones.', 1;

IF OBJECT_ID('dbo.zonas_almacen', 'U') IS NULL
    THROW 50705, 'No existe la tabla dbo.zonas_almacen.', 1;

IF OBJECT_ID('dbo.cuentas_logisticas', 'U') IS NULL
    THROW 50706, 'No existe la tabla dbo.cuentas_logisticas.', 1;

IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.stock_cuenta (
        id_stock_cuenta INT IDENTITY(1,1) PRIMARY KEY,
        id_cuenta INT NOT NULL,
        id_producto INT NOT NULL,
        cantidad_entregada DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_devuelta DECIMAL(18,2) NOT NULL DEFAULT 0,
        cantidad_neta AS (cantidad_entregada - cantidad_devuelta),
        fecha_actualizacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
        CONSTRAINT FK_stock_cuenta_cuenta FOREIGN KEY (id_cuenta) REFERENCES dbo.cuentas_logisticas(id_cuenta),
        CONSTRAINT FK_stock_cuenta_producto FOREIGN KEY (id_producto) REFERENCES dbo.productos(id_producto),
        CONSTRAINT UQ_stock_cuenta_producto UNIQUE (id_cuenta, id_producto)
    );
END;

IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_entregada') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD cantidad_entregada DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_cuenta_entregada DEFAULT 0;
END;

IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_devuelta') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD cantidad_devuelta DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_cuenta_devuelta DEFAULT 0;
END;

IF COL_LENGTH('dbo.stock_cuenta', 'fecha_actualizacion') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD fecha_actualizacion DATETIME2 NOT NULL CONSTRAINT DF_stock_cuenta_fecha DEFAULT SYSDATETIME();
END;

IF COL_LENGTH('dbo.stock_cuenta', 'cantidad_neta') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD cantidad_neta AS (cantidad_entregada - cantidad_devuelta);
END;

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
    CAST(SUM(ISNULL(su.cantidad_actual, 0)) AS DECIMAL(18,2)) AS cantidad_total
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
    ub.codigo_ubicacion,
    ub.tipo_ubicacion,
    su.lote,
    CAST(su.cantidad_actual AS DECIMAL(18,2)) AS cantidad_actual,
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
    CAST(ISNULL(sc.cantidad_entregada, 0) AS DECIMAL(18,2)) AS cantidad_entregada,
    CAST(ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_devuelta,
    CAST(ISNULL(sc.cantidad_entregada, 0) - ISNULL(sc.cantidad_devuelta, 0) AS DECIMAL(18,2)) AS cantidad_neta,
    sc.fecha_actualizacion
FROM dbo.stock_cuenta sc
INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = sc.id_cuenta
INNER JOIN dbo.productos p ON p.id_producto = sc.id_producto
INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
WHERE ISNULL(c.activo, 1) = 1
  AND ISNULL(p.activo, 1) = 1;
');

SELECT 'OK - vistas de stock recreadas correctamente' AS resultado;
