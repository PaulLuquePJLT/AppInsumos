SET NOCOUNT ON;

/* ================================================================
   015 - App RF Mobile: rol Operario y validaciones base
   ================================================================ */

IF OBJECT_ID('dbo.roles', 'U') IS NULL
BEGIN
    THROW 51501, 'No existe la tabla dbo.roles.', 1;
END;

IF OBJECT_ID('dbo.usuarios', 'U') IS NULL
BEGIN
    THROW 51502, 'No existe la tabla dbo.usuarios.', 1;
END;

IF OBJECT_ID('dbo.productos', 'U') IS NULL
BEGIN
    THROW 51503, 'No existe la tabla dbo.productos.', 1;
END;

IF OBJECT_ID('dbo.ubicaciones', 'U') IS NULL
BEGIN
    THROW 51504, 'No existe la tabla dbo.ubicaciones.', 1;
END;

/* 1) Crear rol Operario para la app RF */
IF NOT EXISTS (
    SELECT 1
    FROM dbo.roles
    WHERE nombre_rol = 'Operario'
)
BEGIN
    INSERT INTO dbo.roles (nombre_rol, descripcion, activo)
    VALUES ('Operario', 'Operario RF para ejecución de tareas móviles', 1);
END;
ELSE
BEGIN
    UPDATE dbo.roles
    SET activo = 1,
        descripcion = ISNULL(descripcion, 'Operario RF para ejecución de tareas móviles')
    WHERE nombre_rol = 'Operario';
END;

/* 2) Asegurar columnas EAN en productos para escaneo por SKU o EAN */
IF COL_LENGTH('dbo.productos', 'ean_serie') IS NULL
BEGIN
    ALTER TABLE dbo.productos ADD ean_serie NVARCHAR(13) NULL;
END;

IF COL_LENGTH('dbo.productos', 'flag_aplica_ean') IS NULL
BEGIN
    ALTER TABLE dbo.productos ADD flag_aplica_ean NVARCHAR(2) NULL;
END;

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = ''NO''
WHERE flag_aplica_ean IS NULL OR LTRIM(RTRIM(flag_aplica_ean)) = '''';
');

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = UPPER(LTRIM(RTRIM(flag_aplica_ean)))
WHERE flag_aplica_ean IS NOT NULL;
');

/* 3) Asegurar ubicación stage B1.RE.01 */
IF NOT EXISTS (
    SELECT 1
    FROM dbo.ubicaciones
    WHERE codigo_ubicacion = 'B1.RE.01'
)
BEGIN
    DECLARE @id_zona INT;

    SELECT TOP 1 @id_zona = id_zona
    FROM dbo.zonas_almacen
    WHERE activo = 1
    ORDER BY id_zona;

    IF @id_zona IS NULL
    BEGIN
        INSERT INTO dbo.zonas_almacen (codigo_zona, nombre_zona, descripcion, activo)
        VALUES ('RE', 'Recepción', 'Zona stage de recepción RF', 1);

        SET @id_zona = SCOPE_IDENTITY();
    END;

    INSERT INTO dbo.ubicaciones
        (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima, activo)
    VALUES
        ('B1.RE.01', @id_zona, 'STAGE', 'B1', 'RE', '01', '01', 0, 1);
END;

/* 4) Marcar B1.RE.01 como stage si esas columnas existen */
IF COL_LENGTH('dbo.ubicaciones', 'es_stage') IS NOT NULL
BEGIN
    EXEC(N'
    UPDATE dbo.ubicaciones
    SET es_stage = 1
    WHERE codigo_ubicacion = ''B1.RE.01'';
    ');
END;

IF COL_LENGTH('dbo.ubicaciones', 'es_surtible') IS NOT NULL
BEGIN
    EXEC(N'
    UPDATE dbo.ubicaciones
    SET es_surtible = 0
    WHERE codigo_ubicacion = ''B1.RE.01'';
    ');
END;

IF COL_LENGTH('dbo.ubicaciones', 'secuencia') IS NOT NULL
BEGIN
    EXEC(N'
    UPDATE dbo.ubicaciones
    SET secuencia = 0
    WHERE codigo_ubicacion = ''B1.RE.01'';
    ');
END;

SELECT 'OK - rol Operario y base RF preparados correctamente' AS resultado;
