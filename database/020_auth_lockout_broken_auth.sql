SET NOCOUNT ON;

/* ==========================================================
   020 - Seguridad de login: intentos fallidos y bloqueo
   ========================================================== */

IF OBJECT_ID('dbo.usuarios', 'U') IS NULL
BEGIN
    THROW 52001, 'No existe la tabla dbo.usuarios.', 1;
END;

IF COL_LENGTH('dbo.usuarios', 'failed_login_attempts') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD failed_login_attempts INT NOT NULL CONSTRAINT DF_usuarios_failed_login_attempts DEFAULT 0;
END;

IF COL_LENGTH('dbo.usuarios', 'last_failed_login') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD last_failed_login DATETIME2 NULL;
END;

IF COL_LENGTH('dbo.usuarios', 'account_locked') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD account_locked BIT NOT NULL CONSTRAINT DF_usuarios_account_locked DEFAULT 0;
END;

IF COL_LENGTH('dbo.usuarios', 'account_locked_at') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD account_locked_at DATETIME2 NULL;
END;

IF COL_LENGTH('dbo.usuarios', 'account_locked_reason') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD account_locked_reason NVARCHAR(200) NULL;
END;

IF COL_LENGTH('dbo.usuarios', 'account_unlocked_at') IS NULL
BEGIN
    ALTER TABLE dbo.usuarios
    ADD account_unlocked_at DATETIME2 NULL;
END;

/* Normalizacion de registros existentes. Usar SQL dinamico para columnas agregadas en el mismo lote. */
EXEC(N'
UPDATE dbo.usuarios
SET failed_login_attempts = ISNULL(failed_login_attempts, 0),
    account_locked = ISNULL(account_locked, 0)
WHERE failed_login_attempts IS NULL
   OR account_locked IS NULL;
');

/* Indices de apoyo para autenticacion. */
IF COL_LENGTH('dbo.usuarios', 'usuario_login') IS NOT NULL
   AND NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_usuarios_login_auth_lock'
          AND object_id = OBJECT_ID('dbo.usuarios')
   )
BEGIN
    CREATE INDEX IX_usuarios_login_auth_lock
    ON dbo.usuarios(usuario_login, activo, account_locked)
    INCLUDE (email, failed_login_attempts);
END;

IF COL_LENGTH('dbo.usuarios', 'email') IS NOT NULL
   AND NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_usuarios_email_auth_lock'
          AND object_id = OBJECT_ID('dbo.usuarios')
   )
BEGIN
    CREATE INDEX IX_usuarios_email_auth_lock
    ON dbo.usuarios(email, activo, account_locked)
    INCLUDE (usuario_login, failed_login_attempts);
END;

SELECT 'OK - columnas de bloqueo de login creadas correctamente' AS resultado;
