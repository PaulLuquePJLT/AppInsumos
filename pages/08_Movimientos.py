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
