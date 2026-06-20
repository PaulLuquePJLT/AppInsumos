SET NOCOUNT ON;

/* ==========================================================
   011 - Productos EAN / Flag EAN - Script corregido Azure SQL
   ========================================================== */

IF OBJECT_ID('dbo.productos', 'U') IS NULL
BEGIN
    THROW 51101, 'No existe la tabla dbo.productos.', 1;
END;

/* ==========================================================
   1. Crear columnas si no existen
   ========================================================== */

IF COL_LENGTH('dbo.productos', 'ean_serie') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD ean_serie NVARCHAR(13) NULL;
END;

IF COL_LENGTH('dbo.productos', 'flag_aplica_ean') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD flag_aplica_ean NVARCHAR(2) NULL;
END;

/* ==========================================================
   2. Normalizar datos existentes
   Importante: usar SQL dinámico porque las columnas pueden
   haberse creado en este mismo lote.
   ========================================================== */

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = ''NO''
WHERE flag_aplica_ean IS NULL
   OR LTRIM(RTRIM(flag_aplica_ean)) = '''';
');

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = UPPER(LTRIM(RTRIM(flag_aplica_ean)))
WHERE flag_aplica_ean IS NOT NULL;
');

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean =
    CASE
        WHEN flag_aplica_ean IN (''S'', ''SI'', ''YES'', ''Y'', ''1'', ''TRUE'') THEN ''SI''
        ELSE ''NO''
    END
WHERE flag_aplica_ean NOT IN (''SI'', ''NO'');
');

EXEC(N'
UPDATE dbo.productos
SET ean_serie = NULL
WHERE ean_serie IS NOT NULL
  AND LTRIM(RTRIM(ean_serie)) = '''';
');

EXEC(N'
UPDATE dbo.productos
SET ean_serie = LTRIM(RTRIM(ean_serie))
WHERE ean_serie IS NOT NULL;
');

/* ==========================================================
   3. Si hay EAN inválidos preexistentes, dejarlos en NULL.
   Esto evita que falle la creación de la restricción.
   ========================================================== */

EXEC(N'
UPDATE dbo.productos
SET ean_serie = NULL
WHERE ean_serie IS NOT NULL
  AND (
        LEN(ean_serie) <> 13
        OR ean_serie LIKE ''%[^0-9]%''
      );
');

/* Si el producto decía SI pero quedó sin EAN válido, se normaliza a NO. */
EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = ''NO''
WHERE flag_aplica_ean = ''SI''
  AND ean_serie IS NULL;
');

/* ==========================================================
   4. Hacer flag_aplica_ean obligatorio
   ========================================================== */

EXEC(N'
ALTER TABLE dbo.productos
ALTER COLUMN flag_aplica_ean NVARCHAR(2) NOT NULL;
');

/* ==========================================================
   5. Crear default para flag_aplica_ean si no existe
   ========================================================== */

DECLARE @default_name NVARCHAR(200);
DECLARE @sql NVARCHAR(MAX);

SELECT @default_name = dc.name
FROM sys.default_constraints dc
INNER JOIN sys.columns c
    ON c.default_object_id = dc.object_id
INNER JOIN sys.tables t
    ON t.object_id = c.object_id
INNER JOIN sys.schemas s
    ON s.schema_id = t.schema_id
WHERE s.name = 'dbo'
  AND t.name = 'productos'
  AND c.name = 'flag_aplica_ean';

IF @default_name IS NULL
BEGIN
    EXEC(N'
    ALTER TABLE dbo.productos
    ADD CONSTRAINT DF_productos_flag_aplica_ean
    DEFAULT ''NO'' FOR flag_aplica_ean;
    ');
END;

/* ==========================================================
   6. Eliminar restricciones anteriores si existen
   ========================================================== */

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_flag_aplica_ean'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos
    DROP CONSTRAINT CK_productos_flag_aplica_ean;
END;

IF EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_ean_serie'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos
    DROP CONSTRAINT CK_productos_ean_serie;
END;

/* ==========================================================
   7. Crear restricciones usando SQL dinámico
   ========================================================== */

EXEC(N'
ALTER TABLE dbo.productos
ADD CONSTRAINT CK_productos_flag_aplica_ean
CHECK (flag_aplica_ean IN (''SI'', ''NO''));
');

EXEC(N'
ALTER TABLE dbo.productos
ADD CONSTRAINT CK_productos_ean_serie
CHECK (
    ean_serie IS NULL
    OR (
        LEN(ean_serie) = 13
        AND ean_serie NOT LIKE ''%[^0-9]%''
    )
);
');

/* ==========================================================
   8. Índice único filtrado para EAN
   ========================================================== */

IF EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_productos_ean_serie'
      AND object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    DROP INDEX UX_productos_ean_serie
    ON dbo.productos;
END;

EXEC(N'
CREATE UNIQUE INDEX UX_productos_ean_serie
ON dbo.productos(ean_serie)
WHERE ean_serie IS NOT NULL;
');

/* ==========================================================
   9. Resultado
   ========================================================== */

SELECT
    'OK - columnas EAN creadas y normalizadas correctamente' AS resultado;

EXEC(N'
SELECT TOP 10
    id_producto,
    sku,
    nombre_producto,
    ean_serie,
    flag_aplica_ean
FROM dbo.productos
ORDER BY id_producto DESC;
');
