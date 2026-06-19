SET NOCOUNT ON;

/* ================================================================
   1) Maestro de proveedores
   ================================================================ */
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
        estado NVARCHAR(30) NOT NULL CONSTRAINT DF_proveedores_estado DEFAULT 'ACTIVO',
        activo BIT NOT NULL CONSTRAINT DF_proveedores_activo DEFAULT 1,
        fecha_creacion DATETIME2 NOT NULL CONSTRAINT DF_proveedores_fecha_creacion DEFAULT SYSDATETIME(),
        fecha_actualizacion DATETIME2 NULL,
        CONSTRAINT UQ_proveedores_ruc UNIQUE (ruc),
        CONSTRAINT CK_proveedores_estado CHECK (estado IN ('ACTIVO', 'INACTIVO', 'BLOQUEADO'))
    );
END;
GO

/* Agregar columnas si la tabla ya existía con estructura incompleta */
IF COL_LENGTH('dbo.proveedores', 'rubro_proveedor') IS NULL
    ALTER TABLE dbo.proveedores ADD rubro_proveedor NVARCHAR(100) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'contacto') IS NULL
    ALTER TABLE dbo.proveedores ADD contacto NVARCHAR(150) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'nro_telefono') IS NULL
    ALTER TABLE dbo.proveedores ADD nro_telefono NVARCHAR(30) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'correo') IS NULL
    ALTER TABLE dbo.proveedores ADD correo NVARCHAR(150) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'direccion') IS NULL
    ALTER TABLE dbo.proveedores ADD direccion NVARCHAR(250) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'pais') IS NULL
    ALTER TABLE dbo.proveedores ADD pais NVARCHAR(80) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'ciudad') IS NULL
    ALTER TABLE dbo.proveedores ADD ciudad NVARCHAR(80) NULL;
GO
IF COL_LENGTH('dbo.proveedores', 'estado') IS NULL
    ALTER TABLE dbo.proveedores ADD estado NVARCHAR(30) NOT NULL CONSTRAINT DF_proveedores_estado_2 DEFAULT 'ACTIVO';
GO
IF COL_LENGTH('dbo.proveedores', 'activo') IS NULL
    ALTER TABLE dbo.proveedores ADD activo BIT NOT NULL CONSTRAINT DF_proveedores_activo_2 DEFAULT 1;
GO
IF COL_LENGTH('dbo.proveedores', 'fecha_creacion') IS NULL
    ALTER TABLE dbo.proveedores ADD fecha_creacion DATETIME2 NOT NULL CONSTRAINT DF_proveedores_fecha_creacion_2 DEFAULT SYSDATETIME();
GO
IF COL_LENGTH('dbo.proveedores', 'fecha_actualizacion') IS NULL
    ALTER TABLE dbo.proveedores ADD fecha_actualizacion DATETIME2 NULL;
GO

/* ================================================================
   2) Relación de movimientos con proveedores
   ================================================================ */
IF COL_LENGTH('dbo.movimientos', 'id_proveedor') IS NULL
BEGIN
    ALTER TABLE dbo.movimientos ADD id_proveedor INT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_movimientos_proveedor'
      AND parent_object_id = OBJECT_ID('dbo.movimientos')
)
BEGIN
    ALTER TABLE dbo.movimientos WITH NOCHECK
    ADD CONSTRAINT FK_movimientos_proveedor
    FOREIGN KEY (id_proveedor) REFERENCES dbo.proveedores(id_proveedor);
END;
GO

/* ================================================================
   3) Ubicación stage de ingresos B1.RE.01
      Si ya existe, no hace nada.
   ================================================================ */
DECLARE @id_zona_recepcion INT;

SELECT @id_zona_recepcion = id_zona
FROM dbo.zonas_almacen
WHERE codigo_zona = 'RECEPCION';

IF @id_zona_recepcion IS NULL
BEGIN
    INSERT INTO dbo.zonas_almacen (codigo_zona, nombre_zona, descripcion, activo)
    VALUES ('RECEPCION', 'Recepción / Stage de ingresos', 'Zona temporal para ingresos de mercadería', 1);

    SET @id_zona_recepcion = SCOPE_IDENTITY();
END;

IF NOT EXISTS (SELECT 1 FROM dbo.ubicaciones WHERE codigo_ubicacion = 'B1.RE.01')
BEGIN
    INSERT INTO dbo.ubicaciones
        (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima, activo)
    VALUES
        ('B1.RE.01', @id_zona_recepcion, 'Stage ingreso', 'B1', 'RE', '01', '01', NULL, 1);
END;
GO

/* ================================================================
   4) Vista de movimientos incluyendo proveedor
   ================================================================ */
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
    ub_origen.codigo_ubicacion AS ubicacion_origen,
    ub_destino.codigo_ubicacion AS ubicacion_destino,
    md.cantidad,
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
LEFT JOIN dbo.ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
LEFT JOIN dbo.ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
LEFT JOIN dbo.cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
LEFT JOIN dbo.proveedores pr ON pr.id_proveedor = m.id_proveedor
LEFT JOIN dbo.usuarios u ON u.id_usuario = m.id_usuario;
GO
