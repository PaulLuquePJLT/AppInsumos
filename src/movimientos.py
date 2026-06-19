from sqlalchemy import text

from src.db import get_engine


def registrar_entrada(
    id_producto,
    id_ubicacion_destino,
    cantidad,
    id_usuario,
    referencia=None,
    observacion=None,
    lote=None,
):
    query = text("""
        EXEC sp_registrar_entrada
            @id_producto = :id_producto,
            @id_ubicacion_destino = :id_ubicacion_destino,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    """)
    params = {
        "id_producto": id_producto,
        "id_ubicacion_destino": id_ubicacion_destino,
        "cantidad": cantidad,
        "id_usuario": id_usuario,
        "referencia": referencia,
        "observacion": observacion,
        "lote": lote,
    }
    with get_engine().begin() as conn:
        conn.execute(query, params)


def registrar_entrada_migo(
    id_proveedor: int,
    fecha_ingreso,
    documento_referencia: str,
    texto_cabecera: str,
    id_usuario: int,
    items: list[dict],
) -> int:
    """Registra una entrada tipo MIGO con cabecera y múltiples posiciones.

    Cada item debe contener:
        id_producto, id_ubicacion_destino, cantidad, lote, texto_item
    """
    if not items:
        raise ValueError("No hay posiciones válidas para contabilizar.")

    with get_engine().begin() as conn:
        id_movimiento = conn.execute(
            text("""
                INSERT INTO movimientos
                    (
                        tipo_movimiento,
                        fecha_movimiento,
                        id_proveedor,
                        referencia,
                        observacion,
                        id_usuario,
                        estado
                    )
                OUTPUT INSERTED.id_movimiento
                VALUES
                    (
                        'ENTRADA',
                        :fecha_ingreso,
                        :id_proveedor,
                        :referencia,
                        :observacion,
                        :id_usuario,
                        'CONFIRMADO'
                    )
            """),
            {
                "fecha_ingreso": fecha_ingreso,
                "id_proveedor": int(id_proveedor),
                "referencia": documento_referencia,
                "observacion": texto_cabecera,
                "id_usuario": int(id_usuario),
            },
        ).scalar_one()

        for item in items:
            params = {
                "id_movimiento": int(id_movimiento),
                "id_producto": int(item["id_producto"]),
                "id_ubicacion_destino": int(item["id_ubicacion_destino"]),
                "cantidad": float(item["cantidad"]),
                "lote": item.get("lote") or None,
                "texto_item": item.get("texto_item") or None,
            }

            conn.execute(
                text("""
                    INSERT INTO movimiento_detalle
                        (
                            id_movimiento,
                            id_producto,
                            id_ubicacion_destino,
                            cantidad,
                            lote,
                            observacion
                        )
                    VALUES
                        (
                            :id_movimiento,
                            :id_producto,
                            :id_ubicacion_destino,
                            :cantidad,
                            :lote,
                            :texto_item
                        )
                """),
                params,
            )

            conn.execute(
                text("""
                    IF EXISTS (
                        SELECT 1
                        FROM stock_ubicacion
                        WHERE id_producto = :id_producto
                          AND id_ubicacion = :id_ubicacion_destino
                          AND ISNULL(lote, '') = ISNULL(:lote, '')
                    )
                    BEGIN
                        UPDATE stock_ubicacion
                        SET cantidad_actual = cantidad_actual + :cantidad,
                            fecha_actualizacion = SYSDATETIME()
                        WHERE id_producto = :id_producto
                          AND id_ubicacion = :id_ubicacion_destino
                          AND ISNULL(lote, '') = ISNULL(:lote, '')
                    END
                    ELSE
                    BEGIN
                        INSERT INTO stock_ubicacion
                            (
                                id_producto,
                                id_ubicacion,
                                lote,
                                cantidad_actual
                            )
                        VALUES
                            (
                                :id_producto,
                                :id_ubicacion_destino,
                                :lote,
                                :cantidad
                            )
                    END
                """),
                params,
            )

    return int(id_movimiento)


def registrar_salida_cuenta(
    id_producto,
    id_ubicacion_origen,
    id_cuenta,
    cantidad,
    id_usuario,
    referencia=None,
    observacion=None,
    lote=None,
):
    query = text("""
        EXEC sp_registrar_salida_cuenta
            @id_producto = :id_producto,
            @id_ubicacion_origen = :id_ubicacion_origen,
            @id_cuenta = :id_cuenta,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    """)
    params = {
        "id_producto": id_producto,
        "id_ubicacion_origen": id_ubicacion_origen,
        "id_cuenta": id_cuenta,
        "cantidad": cantidad,
        "id_usuario": id_usuario,
        "referencia": referencia,
        "observacion": observacion,
        "lote": lote,
    }
    with get_engine().begin() as conn:
        conn.execute(query, params)


def registrar_transferencia(
    id_producto,
    id_ubicacion_origen,
    id_ubicacion_destino,
    cantidad,
    id_usuario,
    referencia=None,
    observacion=None,
    lote=None,
):
    query = text("""
        EXEC sp_registrar_transferencia
            @id_producto = :id_producto,
            @id_ubicacion_origen = :id_ubicacion_origen,
            @id_ubicacion_destino = :id_ubicacion_destino,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    """)
    params = {
        "id_producto": id_producto,
        "id_ubicacion_origen": id_ubicacion_origen,
        "id_ubicacion_destino": id_ubicacion_destino,
        "cantidad": cantidad,
        "id_usuario": id_usuario,
        "referencia": referencia,
        "observacion": observacion,
        "lote": lote,
    }
    with get_engine().begin() as conn:
        conn.execute(query, params)
