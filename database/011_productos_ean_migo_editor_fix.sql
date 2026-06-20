SET NOCOUNT ON;

/* ================================================================
   011 - EAN 13 en productos y soporte de editor MIGO
   ================================================================ */

IF OBJECT_ID('dbo.productos', 'U') IS NULL
    THROW 51101, 'No existe la tabla dbo.productos.', 1;

IF COL_LENGTH('dbo.productos', 'ean_serie') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD ean_serie NVARCHAR(20) NULL;
END;

IF COL_LENGTH('dbo.productos', 'flag_aplica_ean') IS NULL
BEGIN
    ALTER TABLE dbo.productos
    ADD flag_aplica_ean NVARCHAR(2) NOT NULL
        CONSTRAINT DF_productos_flag_aplica_ean DEFAULT 'NO';
END;

EXEC(N'
UPDATE dbo.productos
SET flag_aplica_ean = CASE
        WHEN UPPER(LTRIM(RTRIM(ISNULL(flag_aplica_ean, '''')))) = ''SI'' THEN ''SI''
        ELSE ''NO''
    END,
    ean_serie = NULLIF(LTRIM(RTRIM(ISNULL(ean_serie, ''''))), '''');
');

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_flag_aplica_ean'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos
    ADD CONSTRAINT CK_productos_flag_aplica_ean
    CHECK (flag_aplica_ean IN ('SI', 'NO'));
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_productos_ean_serie_13'
      AND parent_object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    ALTER TABLE dbo.productos
    ADD CONSTRAINT CK_productos_ean_serie_13
    CHECK (
        ean_serie IS NULL
        OR ean_serie = ''
        OR (
            LEN(ean_serie) = 13
            AND ean_serie NOT LIKE '%[^0-9]%'
        )
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_productos_ean_serie'
      AND object_id = OBJECT_ID('dbo.productos')
)
BEGIN
    CREATE UNIQUE INDEX UX_productos_ean_serie
    ON dbo.productos(ean_serie)
    WHERE ean_serie IS NOT NULL AND ean_serie <> '';
END;

SELECT 'OK - columnas EAN agregadas a productos' AS resultado;
