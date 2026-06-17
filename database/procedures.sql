SET NOCOUNT ON;

CREATE OR ALTER PROCEDURE sp_registrar_entrada
    @id_producto INT,
    @id_ubicacion_destino INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @id_movimiento INT;

        INSERT INTO movimientos (tipo_movimiento, referencia, observacion, id_usuario)
        VALUES ('ENTRADA', @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_destino, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_destino, @cantidad, @lote);

        IF EXISTS (SELECT 1 FROM stock_ubicacion
                   WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
                   AND ISNULL(lote,'') = ISNULL(@lote,''))
            UPDATE stock_ubicacion
            SET cantidad_actual = cantidad_actual + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
              AND ISNULL(lote,'') = ISNULL(@lote,'');
        ELSE
            INSERT INTO stock_ubicacion (id_producto, id_ubicacion, lote, cantidad_actual)
            VALUES (@id_producto, @id_ubicacion_destino, @lote, @cantidad);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE sp_registrar_salida_cuenta
    @id_producto INT,
    @id_ubicacion_origen INT,
    @id_cuenta INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @stock_actual DECIMAL(18,2);
        DECLARE @id_movimiento INT;

        SELECT @stock_actual = cantidad_actual
        FROM stock_ubicacion
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF @stock_actual IS NULL OR @stock_actual < @cantidad
            THROW 50001, 'Stock insuficiente en la ubicación seleccionada.', 1;

        INSERT INTO movimientos (tipo_movimiento, id_cuenta, referencia, observacion, id_usuario)
        VALUES ('SALIDA_CUENTA', @id_cuenta, @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_origen, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_origen, @cantidad, @lote);

        UPDATE stock_ubicacion
        SET cantidad_actual = cantidad_actual - @cantidad,
            fecha_actualizacion = SYSDATETIME()
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF EXISTS (SELECT 1 FROM stock_cuenta WHERE id_cuenta=@id_cuenta AND id_producto=@id_producto)
            UPDATE stock_cuenta
            SET cantidad_entregada = cantidad_entregada + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_cuenta=@id_cuenta AND id_producto=@id_producto;
        ELSE
            INSERT INTO stock_cuenta (id_cuenta, id_producto, cantidad_entregada, cantidad_devuelta)
            VALUES (@id_cuenta, @id_producto, @cantidad, 0);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE sp_registrar_transferencia
    @id_producto INT,
    @id_ubicacion_origen INT,
    @id_ubicacion_destino INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @id_ubicacion_origen = @id_ubicacion_destino
            THROW 50002, 'La ubicación origen y destino no pueden ser iguales.', 1;

        BEGIN TRANSACTION;
        DECLARE @stock_actual DECIMAL(18,2);
        DECLARE @id_movimiento INT;

        SELECT @stock_actual = cantidad_actual
        FROM stock_ubicacion
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF @stock_actual IS NULL OR @stock_actual < @cantidad
            THROW 50003, 'Stock insuficiente en la ubicación origen.', 1;

        INSERT INTO movimientos (tipo_movimiento, referencia, observacion, id_usuario)
        VALUES ('TRANSFERENCIA', @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_origen, @id_ubicacion_destino, @cantidad, @lote);

        UPDATE stock_ubicacion
        SET cantidad_actual = cantidad_actual - @cantidad,
            fecha_actualizacion = SYSDATETIME()
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF EXISTS (SELECT 1 FROM stock_ubicacion
                   WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
                     AND ISNULL(lote,'') = ISNULL(@lote,''))
            UPDATE stock_ubicacion
            SET cantidad_actual = cantidad_actual + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
              AND ISNULL(lote,'') = ISNULL(@lote,'');
        ELSE
            INSERT INTO stock_ubicacion (id_producto, id_ubicacion, lote, cantidad_actual)
            VALUES (@id_producto, @id_ubicacion_destino, @lote, @cantidad);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
