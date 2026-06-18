SET NOCOUNT ON;

IF COL_LENGTH('dbo.unidades_medida', 'activo') IS NULL
BEGIN
    ALTER TABLE unidades_medida
    ADD activo BIT NOT NULL CONSTRAINT DF_unidades_medida_activo DEFAULT 1;
END;
GO
