SET NOCOUNT ON;

/* ================================================================
   010 - Correcciones UI/Login/Dashboard/MIGO
   - Función de fecha Bogotá/Lima UTC-5 sin error de batch.
   - Default de movimientos.fecha_movimiento.
   - Columnas necesarias para dashboard y vistas.
   - Vistas de stock y movimientos alineadas a la app.
   ================================================================ */

/* 1) Función fecha/hora Bogotá-Lima-Perú */
/* Si el default anterior usa la función, primero se elimina la restricción. */
DECLARE @constraint_to_drop_010 NVARCHAR(200);
DECLARE @drop_sql_010 NVARCHAR(MAX);

SELECT @constraint_to_drop_010 = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t ON t.object_id = c.object_id
INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'movimientos'
  AND c.name = 'fecha_movimiento';

IF @constraint_to_drop_010 IS NOT NULL
BEGIN
    SET @drop_sql_010 = N'ALTER TABLE dbo.movimientos DROP CONSTRAINT ' + QUOTENAME(@constraint_to_drop_010);
    EXEC sp_executesql @drop_sql_010;
END;

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

/* 2) Columnas mínimas requeridas por dashboard y flujo actual */
IF OBJECT_ID('dbo.proveedores', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.proveedores (
        id_proveedor INT IDENTITY(1,1) PRIMARY KEY,
        ruc NVARCHAR(20) NOT NULL,
        razon_social NVARCHAR(200) NOT NULL,
        rubro_proveedor NVARCHAR(100) NULL,
        contacto NVARCHAR(150) NULL,
        nro_telefono NVARCHAR(30) NULL,
        correo NVARCHAR(150) NULL,
        direccion NVARCHAR(250) NULL,
        pais NVARCHAR(80) NULL,
        ciudad NVARCHAR(80) NULL,
        estado NVARCHAR(30) NOT NULL CONSTRAINT DF_proveedores_estado_010 DEFAULT 'ACTIVO',
        activo BIT NOT NULL CONSTRAINT DF_proveedores_activo_010 DEFAULT 1,
        fecha_creacion DATETIME2 NOT NULL CONSTRAINT DF_proveedores_fecha_creacion_010 DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT UQ_proveedores_ruc_010 UNIQUE (ruc)
    );
END;

IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL AND COL_LENGTH('dbo.movimientos', 'id_proveedor') IS NULL
BEGIN
    ALTER TABLE dbo.movimientos ADD id_proveedor INT NULL;
END;

IF OBJECT_ID('dbo.stock_ubicacion', 'U') IS NOT NULL AND COL_LENGTH('dbo.stock_ubicacion', 'cantidad_en_picking') IS NULL
BEGIN
    ALTER TABLE dbo.stock_ubicacion
    ADD cantidad_en_picking DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_ubicacion_cantidad_en_picking_010 DEFAULT 0;
END;


IF OBJECT_ID('dbo.ubicaciones', 'U') IS NOT NULL AND COL_LENGTH('dbo.ubicaciones', 'secuencia') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD secuencia INT NOT NULL CONSTRAINT DF_ubicaciones_secuencia_010 DEFAULT 999999;
END;

IF OBJECT_ID('dbo.ubicaciones', 'U') IS NOT NULL AND COL_LENGTH('dbo.ubicaciones', 'es_surtible') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD es_surtible BIT NOT NULL CONSTRAINT DF_ubicaciones_es_surtible_010 DEFAULT 1;
END;

IF OBJECT_ID('dbo.ubicaciones', 'U') IS NOT NULL AND COL_LENGTH('dbo.ubicaciones', 'es_stage') IS NULL
BEGIN
    ALTER TABLE dbo.ubicaciones
    ADD es_stage BIT NOT NULL CONSTRAINT DF_ubicaciones_es_stage_010 DEFAULT 0;
END;

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
        CONSTRAINT FK_stock_cuenta_cuenta_010 FOREIGN KEY (id_cuenta) REFERENCES dbo.cuentas_logisticas(id_cuenta),
        CONSTRAINT FK_stock_cuenta_producto_010 FOREIGN KEY (id_producto) REFERENCES dbo.productos(id_producto)
    );
END;


IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL AND COL_LENGTH('dbo.stock_cuenta', 'cantidad_entregada') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD cantidad_entregada DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_cuenta_entregada_010 DEFAULT 0;
END;

IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL AND COL_LENGTH('dbo.stock_cuenta', 'cantidad_devuelta') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD cantidad_devuelta DECIMAL(18,2) NOT NULL CONSTRAINT DF_stock_cuenta_devuelta_010 DEFAULT 0;
END;

IF OBJECT_ID('dbo.stock_cuenta', 'U') IS NOT NULL AND COL_LENGTH('dbo.stock_cuenta', 'fecha_actualizacion') IS NULL
BEGIN
    ALTER TABLE dbo.stock_cuenta ADD fecha_actualizacion DATETIME2 NOT NULL CONSTRAINT DF_stock_cuenta_fecha_010 DEFAULT SYSDATETIME();
END;

IF OBJECT_ID('dbo.usuarios', 'U') IS NOT NULL AND COL_LENGTH('dbo.usuarios', 'usuario_login') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios ADD usuario_login NVARCHAR(80) NULL;
END;

IF OBJECT_ID('dbo.usuarios', 'U') IS NOT NULL AND COL_LENGTH('dbo.usuarios', 'nombres') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios ADD nombres NVARCHAR(100) NULL;
END;

IF OBJECT_ID('dbo.usuarios', 'U') IS NOT NULL AND COL_LENGTH('dbo.usuarios', 'apellidos') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios ADD apellidos NVARCHAR(100) NULL;
END;

/* 3) Default de fecha_movimiento con hora local */
IF OBJECT_ID('dbo.movimientos', 'U') IS NOT NULL
BEGIN
    UPDATE dbo.movimientos
    SET fecha_movimiento = dbo.fn_now_bogota_lima()
    WHERE fecha_movimiento IS NULL;

    DECLARE @constraint_name NVARCHAR(200);
    DECLARE @sql NVARCHAR(MAX);

    SELECT @constraint_name = dc.name
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c ON c.default_object_id = dc.object_id
    INNER JOIN sys.tables t ON t.object_id = c.object_id
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'dbo'
      AND t.name = 'movimientos'
      AND c.name = 'fecha_movimiento';

    IF @constraint_name IS NOT NULL
    BEGIN
        SET @sql = N'ALTER TABLE dbo.movimientos DROP CONSTRAINT ' + QUOTENAME(@constraint_name);
        EXEC sp_executesql @sql;
    END;

    ALTER TABLE dbo.movimientos
    ADD CONSTRAINT DF_movimientos_fecha_movimiento_bogota_lima_010
    DEFAULT dbo.fn_now_bogota_lima()
    FOR fecha_movimiento;
END;

/* 4) Vistas de stock robustas para dashboard */
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

/* 5) Vista de movimientos con todas las columnas que usa el dashboard */
EXEC(N'
CREATE OR ALTER VIEW dbo.vw_movimientos AS
SELECT
    m.id_movimiento,
    m.tipo_movimiento,
    m.fecha_movimiento,
    CAST(m.fecha_movimiento AS DATE) AS fecha_movimiento_dia,
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
LEFT JOIN dbo.productos p ON p.id_producto = md.id_producto
LEFT JOIN dbo.unidades_medida um ON um.id_unidad = p.id_unidad
LEFT JOIN dbo.ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
LEFT JOIN dbo.ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
LEFT JOIN dbo.proveedores pr ON pr.id_proveedor = m.id_proveedor
LEFT JOIN dbo.usuarios u ON u.id_usuario = m.id_usuario;
');

SELECT
    ''OK - 010 aplicado correctamente'' AS resultado,
    dbo.fn_now_bogota_lima() AS fecha_hora_bogota_lima;
