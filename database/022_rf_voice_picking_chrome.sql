SET NOCOUNT ON;

/* ==========================================================
   022 - RF Voice Picking con Web Speech API / Chrome
   - Auditoría de eventos de voz.
   - Campos opcionales para método de confirmación.
   - No usa servicios pagados Azure AI Speech.
   ========================================================== */

IF OBJECT_ID('dbo.fn_now_bogota_lima', 'FN') IS NULL
BEGIN
    EXEC(N'
    CREATE FUNCTION dbo.fn_now_bogota_lima()
    RETURNS DATETIME2(0)
    AS
    BEGIN
        RETURN CAST(SWITCHOFFSET(SYSDATETIMEOFFSET(), ''-05:00'') AS DATETIME2(0));
    END
    ');
END;
GO

IF OBJECT_ID('dbo.voice_event_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.voice_event_log (
        id_voice_event BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_usuario INT NULL,
        id_picking INT NULL,
        id_picking_detalle INT NULL,
        evento NVARCHAR(60) NOT NULL,
        texto_emitido NVARCHAR(MAX) NULL,
        texto_reconocido NVARCHAR(500) NULL,
        comando_normalizado NVARCHAR(80) NULL,
        confianza DECIMAL(10,6) NULL,
        fecha_evento DATETIME2(0) NOT NULL CONSTRAINT DF_voice_event_log_fecha DEFAULT dbo.fn_now_bogota_lima(),
        dispositivo NVARCHAR(120) NULL
    );
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'metodo_confirmacion') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD metodo_confirmacion NVARCHAR(30) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'confirmado_por_voz') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD confirmado_por_voz BIT NOT NULL CONSTRAINT DF_picking_detalle_confirmado_por_voz DEFAULT 0;
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'texto_confirmacion_voz') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD texto_confirmacion_voz NVARCHAR(500) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'confianza_voz') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD confianza_voz DECIMAL(10,6) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'fecha_confirmacion_voz') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD fecha_confirmacion_voz DATETIME2(0) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_detalle', 'cantidad_reportada_voz') IS NULL
BEGIN
    ALTER TABLE dbo.picking_detalle ADD cantidad_reportada_voz DECIMAL(18,2) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_header', 'modo_atencion') IS NULL
BEGIN
    ALTER TABLE dbo.picking_header ADD modo_atencion NVARCHAR(30) NULL;
END;
GO

IF COL_LENGTH('dbo.picking_header', 'usa_voice_picking') IS NULL
BEGIN
    ALTER TABLE dbo.picking_header ADD usa_voice_picking BIT NOT NULL CONSTRAINT DF_picking_header_usa_voice_picking DEFAULT 0;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.voice_event_log')
      AND name = 'IX_voice_event_log_picking_fecha'
)
BEGIN
    CREATE INDEX IX_voice_event_log_picking_fecha
    ON dbo.voice_event_log(id_picking, id_picking_detalle, fecha_evento)
    INCLUDE (evento, comando_normalizado);
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.voice_event_log')
      AND name = 'IX_voice_event_log_usuario_fecha'
)
BEGIN
    CREATE INDEX IX_voice_event_log_usuario_fecha
    ON dbo.voice_event_log(id_usuario, fecha_evento)
    INCLUDE (evento, comando_normalizado);
END;
GO

SELECT 'OK - Voice Picking RF preparado correctamente' AS resultado;
