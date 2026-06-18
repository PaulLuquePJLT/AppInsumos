SET NOCOUNT ON;

/* 1) Normalizar roles principales */
IF EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'ADMIN')
   AND NOT EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'Administrador')
BEGIN
    UPDATE roles
    SET nombre_rol = 'Administrador',
        descripcion = 'Administrador del sistema'
    WHERE nombre_rol = 'ADMIN';
END;

IF EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'OPERADOR')
   AND NOT EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'Usuario')
BEGIN
    UPDATE roles
    SET nombre_rol = 'Usuario',
        descripcion = 'Usuario operativo del sistema'
    WHERE nombre_rol = 'OPERADOR';
END;

IF NOT EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'Administrador')
BEGIN
    INSERT INTO roles (nombre_rol, descripcion, activo)
    VALUES ('Administrador', 'Administrador del sistema', 1);
END;

IF NOT EXISTS (SELECT 1 FROM roles WHERE nombre_rol = 'Usuario')
BEGIN
    INSERT INTO roles (nombre_rol, descripcion, activo)
    VALUES ('Usuario', 'Usuario operativo del sistema', 1);
END;
GO

/* 2) Agregar campos de autenticación a usuarios */
IF COL_LENGTH('dbo.usuarios', 'usuario_login') IS NULL
BEGIN
    ALTER TABLE usuarios ADD usuario_login NVARCHAR(80) NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'nombres') IS NULL
BEGIN
    ALTER TABLE usuarios ADD nombres NVARCHAR(100) NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'apellidos') IS NULL
BEGIN
    ALTER TABLE usuarios ADD apellidos NVARCHAR(100) NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'ultimo_login') IS NULL
BEGIN
    ALTER TABLE usuarios ADD ultimo_login DATETIME2 NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'fecha_actualizacion') IS NULL
BEGIN
    ALTER TABLE usuarios ADD fecha_actualizacion DATETIME2 NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'reset_code_hash') IS NULL
BEGIN
    ALTER TABLE usuarios ADD reset_code_hash NVARCHAR(255) NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'reset_code_expires_at') IS NULL
BEGIN
    ALTER TABLE usuarios ADD reset_code_expires_at DATETIME2 NULL;
END;
GO

IF COL_LENGTH('dbo.usuarios', 'reset_code_attempts') IS NULL
BEGIN
    ALTER TABLE usuarios ADD reset_code_attempts INT NOT NULL CONSTRAINT DF_usuarios_reset_code_attempts DEFAULT 0;
END;
GO

/* 3) Completar datos para usuarios existentes */
UPDATE usuarios
SET usuario_login = LOWER(LEFT(email, CHARINDEX('@', email + '@') - 1))
WHERE usuario_login IS NULL OR LTRIM(RTRIM(usuario_login)) = '';
GO

UPDATE usuarios
SET nombres = ISNULL(nombres, nombre),
    apellidos = ISNULL(apellidos, ''),
    fecha_actualizacion = ISNULL(fecha_actualizacion, SYSDATETIME())
WHERE nombres IS NULL OR apellidos IS NULL OR fecha_actualizacion IS NULL;
GO

/* 4) Evitar usuario_login duplicado antes de crear índice único */
;WITH duplicated AS (
    SELECT
        id_usuario,
        usuario_login,
        ROW_NUMBER() OVER (PARTITION BY usuario_login ORDER BY id_usuario) AS rn
    FROM usuarios
    WHERE usuario_login IS NOT NULL
)
UPDATE u
SET usuario_login = CONCAT(u.usuario_login, '_', u.id_usuario)
FROM usuarios u
INNER JOIN duplicated d ON d.id_usuario = u.id_usuario
WHERE d.rn > 1;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_usuarios_usuario_login'
      AND object_id = OBJECT_ID('dbo.usuarios')
)
BEGIN
    CREATE UNIQUE INDEX UX_usuarios_usuario_login
    ON usuarios(usuario_login)
    WHERE usuario_login IS NOT NULL;
END;
GO

/* 5) Asegurar usuario admin base si no existe. La app podrá rehashear la contraseña. */
DECLARE @id_rol_admin INT;

SELECT TOP 1 @id_rol_admin = id_rol
FROM roles
WHERE nombre_rol IN ('Administrador', 'ADMIN')
ORDER BY CASE WHEN nombre_rol = 'Administrador' THEN 1 ELSE 2 END;

IF NOT EXISTS (
    SELECT 1
    FROM usuarios
    WHERE LOWER(usuario_login) = 'admin'
       OR LOWER(email) = 'admin@wms.com'
)
BEGIN
    INSERT INTO usuarios
        (usuario_login, nombres, apellidos, nombre, email, password_hash, id_rol, activo)
    VALUES
        ('admin', 'Administrador', 'WMS', 'Administrador WMS', 'admin@wms.com', 'changeme', @id_rol_admin, 1);
END
ELSE
BEGIN
    UPDATE usuarios
    SET usuario_login = ISNULL(usuario_login, 'admin'),
        nombres = ISNULL(nombres, 'Administrador'),
        apellidos = ISNULL(apellidos, 'WMS'),
        id_rol = @id_rol_admin,
        activo = 1
    WHERE LOWER(usuario_login) = 'admin'
       OR LOWER(email) = 'admin@wms.com';
END;
GO

/* 6) Mejorar vista de movimientos para mostrar usuario */
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
    ISNULL(u.usuario_login, '') AS usuario_login,
    LTRIM(RTRIM(ISNULL(u.nombres, '') + ' ' + ISNULL(u.apellidos, ''))) AS usuario_nombre,
    m.estado
FROM movimientos m
LEFT JOIN movimiento_detalle md ON md.id_movimiento = m.id_movimiento
LEFT JOIN productos p ON p.id_producto = md.id_producto
LEFT JOIN ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
LEFT JOIN ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
LEFT JOIN cuentas_logisticas c ON c.id_cuenta = m.id_cuenta
LEFT JOIN usuarios u ON u.id_usuario = m.id_usuario;
GO
