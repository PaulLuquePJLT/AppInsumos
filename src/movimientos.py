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
                        dbo.fn_now_bogota_lima(),
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
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
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

# ---------------------------------------------------------------------------
# Pedidos, Picking y Transferencias masivas
# ---------------------------------------------------------------------------


def _next_correlative(conn, table: str, column: str, prefix: str, start_position: int) -> str:
    number = conn.execute(
        text(f"""
            SELECT ISNULL(MAX(TRY_CAST(SUBSTRING({column}, :start_position, 9) AS INT)), 0) + 1 AS next_number
            FROM {table} WITH (UPDLOCK, HOLDLOCK)
            WHERE {column} LIKE :pattern
        """),
        {
            "start_position": start_position,
            "pattern": prefix + "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
        },
    ).scalar_one()
    return f"{prefix}{int(number):09d}"


def crear_pedido(
    nro_pedido: str | None,
    fecha_pedido,
    fecha_esperada_atencion,
    id_cuenta: int,
    solicitante: str,
    responsable_cuenta: str,
    texto_cabecera: str,
    id_usuario: int,
    items: list[dict],
) -> str:
    if not items:
        raise ValueError("No hay posiciones válidas para crear el pedido.")

    with get_engine().begin() as conn:
        nro_final = nro_pedido or _next_correlative(conn, "pedidos", "nro_pedido", "P", 2)
        qty_total = sum(float(item["cantidad"]) for item in items)

        id_pedido = conn.execute(
            text("""
                INSERT INTO pedidos
                    (
                        nro_pedido,
                        fecha_pedido,
                        fecha_esperada_atencion,
                        id_cuenta,
                        solicitante,
                        responsable_cuenta,
                        texto_cabecera,
                        qty_total,
                        estado,
                        id_usuario_creacion
                    )
                OUTPUT INSERTED.id_pedido
                VALUES
                    (
                        :nro_pedido,
                        :fecha_pedido,
                        :fecha_esperada_atencion,
                        :id_cuenta,
                        :solicitante,
                        :responsable_cuenta,
                        :texto_cabecera,
                        :qty_total,
                        'CREADO',
                        :id_usuario
                    )
            """),
            {
                "nro_pedido": nro_final,
                "fecha_pedido": fecha_pedido,
                "fecha_esperada_atencion": fecha_esperada_atencion,
                "id_cuenta": int(id_cuenta),
                "solicitante": solicitante,
                "responsable_cuenta": responsable_cuenta,
                "texto_cabecera": texto_cabecera,
                "qty_total": qty_total,
                "id_usuario": int(id_usuario),
            },
        ).scalar_one()

        for line_no, item in enumerate(items, start=1):
            conn.execute(
                text("""
                    INSERT INTO pedido_detalle
                        (
                            id_pedido,
                            nro_linea,
                            id_producto,
                            codigo_unidad,
                            cantidad_pedida,
                            texto_item,
                            estado
                        )
                    VALUES
                        (
                            :id_pedido,
                            :nro_linea,
                            :id_producto,
                            :codigo_unidad,
                            :cantidad_pedida,
                            :texto_item,
                            'PENDIENTE'
                        )
                """),
                {
                    "id_pedido": int(id_pedido),
                    "nro_linea": int(line_no),
                    "id_producto": int(item["id_producto"]),
                    "codigo_unidad": item.get("codigo_unidad"),
                    "cantidad_pedida": float(item["cantidad"]),
                    "texto_item": item.get("texto_item"),
                },
            )

    return nro_final


def eliminar_pedidos(ids_pedidos: list[int]) -> dict:
    """Elimina físicamente pedidos seleccionados en estado CREADO.

    Reglas:
    - Solo permite eliminar pedidos con estado CREADO.
    - Si el pedido estuvo en un picking CANCELADO, limpia esas relaciones históricas
      y permite eliminarlo.
    - Bloquea pedidos con pickings activos o tareas ya COMPLETADAS.
    - Bloquea pedidos con cantidades atendidas o canceladas.

    Este ajuste corrige el caso donde un pedido vuelve a CREADO luego de cancelar
    un picking, pero mantiene registros en picking_pedido/picking_detalle que
    antes impedían eliminarlo.
    """
    ids = [int(v) for v in ids_pedidos if v is not None]
    if not ids:
        raise ValueError("Selecciona al menos un pedido.")

    placeholders = ",".join(f":p{i}" for i, _ in enumerate(ids))
    params = {f"p{i}": int(v) for i, v in enumerate(ids)}

    with get_engine().begin() as conn:
        no_creados = list(conn.execute(
            text(f"""
                SELECT nro_pedido, estado
                FROM pedidos
                WHERE id_pedido IN ({placeholders})
                  AND estado <> 'CREADO'
            """),
            params,
        ).mappings())
        if no_creados:
            pedidos = ", ".join(f"{r['nro_pedido']} ({r['estado']})" for r in no_creados)
            raise ValueError(
                "Solo se pueden eliminar pedidos en estado CREADO. Pedidos no permitidos: "
                + pedidos
            )

        procesados = list(conn.execute(
            text(f"""
                SELECT DISTINCT p.nro_pedido
                FROM pedidos p
                INNER JOIN pedido_detalle pd ON pd.id_pedido = p.id_pedido
                WHERE p.id_pedido IN ({placeholders})
                  AND (
                        ISNULL(pd.cantidad_atendida, 0) > 0
                        OR ISNULL(pd.cantidad_cancelada, 0) > 0
                      )
            """),
            params,
        ).mappings())
        if procesados:
            pedidos = ", ".join(str(r["nro_pedido"]) for r in procesados)
            raise ValueError(
                "No se pueden eliminar pedidos con cantidades atendidas o canceladas: "
                + pedidos
            )

        picking_activo = list(conn.execute(
            text(f"""
                SELECT DISTINCT p.nro_pedido, ph.nro_picking, ph.estado
                FROM pedidos p
                INNER JOIN picking_pedido pp ON pp.id_pedido = p.id_pedido
                INNER JOIN picking_header ph ON ph.id_picking = pp.id_picking
                WHERE p.id_pedido IN ({placeholders})
                  AND ISNULL(ph.estado, '') <> 'CANCELADO'
            """),
            params,
        ).mappings())
        if picking_activo:
            pedidos = ", ".join(
                f"{r['nro_pedido']} / {r['nro_picking']} ({r['estado']})"
                for r in picking_activo
            )
            raise ValueError(
                "No se pueden eliminar pedidos con picking activo. Cancela primero el picking: "
                + pedidos
            )

        tareas_completadas = list(conn.execute(
            text(f"""
                SELECT DISTINCT p.nro_pedido, ph.nro_picking
                FROM pedidos p
                INNER JOIN pedido_detalle pd ON pd.id_pedido = p.id_pedido
                INNER JOIN picking_detalle pkd ON pkd.id_pedido_detalle = pd.id_pedido_detalle
                INNER JOIN picking_header ph ON ph.id_picking = pkd.id_picking
                WHERE p.id_pedido IN ({placeholders})
                  AND pkd.estado = 'COMPLETADO'
            """),
            params,
        ).mappings())
        if tareas_completadas:
            pedidos = ", ".join(
                f"{r['nro_pedido']} / {r['nro_picking']}"
                for r in tareas_completadas
            )
            raise ValueError(
                "No se pueden eliminar pedidos con tareas de picking ya completadas: "
                + pedidos
            )

        # Si el pedido participó en pickings CANCELADOS, limpiar detalles/relaciones
        # para no bloquear la eliminación del pedido CREADO.
        pickings_relacionados = list(conn.execute(
            text(f"""
                SELECT DISTINCT ph.id_picking
                FROM picking_header ph
                INNER JOIN picking_pedido pp ON pp.id_picking = ph.id_picking
                WHERE pp.id_pedido IN ({placeholders})
                  AND ph.estado = 'CANCELADO'
            """),
            params,
        ).scalars())

        picking_detalles_eliminados = conn.execute(
            text(f"""
                DELETE pkd
                FROM picking_detalle pkd
                INNER JOIN picking_header ph ON ph.id_picking = pkd.id_picking
                INNER JOIN pedido_detalle pd ON pd.id_pedido_detalle = pkd.id_pedido_detalle
                WHERE pd.id_pedido IN ({placeholders})
                  AND ph.estado = 'CANCELADO'
                  AND pkd.estado <> 'COMPLETADO'
            """),
            params,
        ).rowcount or 0

        picking_pedido_eliminados = conn.execute(
            text(f"""
                DELETE pp
                FROM picking_pedido pp
                INNER JOIN picking_header ph ON ph.id_picking = pp.id_picking
                WHERE pp.id_pedido IN ({placeholders})
                  AND ph.estado = 'CANCELADO'
            """),
            params,
        ).rowcount or 0

        # Eliminar cabeceras de picking canceladas que quedaron sin pedidos ni detalles.
        pickings_vacios_eliminados = 0
        for id_picking in pickings_relacionados:
            deleted = conn.execute(
                text("""
                    DELETE ph
                    FROM picking_header ph
                    WHERE ph.id_picking = :id_picking
                      AND ph.estado = 'CANCELADO'
                      AND NOT EXISTS (
                            SELECT 1 FROM picking_pedido pp
                            WHERE pp.id_picking = ph.id_picking
                      )
                      AND NOT EXISTS (
                            SELECT 1 FROM picking_detalle pkd
                            WHERE pkd.id_picking = ph.id_picking
                      )
                """),
                {"id_picking": int(id_picking)},
            ).rowcount or 0
            pickings_vacios_eliminados += int(deleted)

        # Si hubiera cantidades asignadas residuales en pedidos CREADOS sin picking activo,
        # se normalizan antes de borrar para evitar falsos bloqueos.
        conn.execute(
            text(f"""
                UPDATE pd
                SET cantidad_asignada = 0,
                    estado = 'PENDIENTE',
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                FROM pedido_detalle pd
                INNER JOIN pedidos p ON p.id_pedido = pd.id_pedido
                WHERE p.id_pedido IN ({placeholders})
                  AND p.estado = 'CREADO'
                  AND ISNULL(pd.cantidad_atendida, 0) = 0
                  AND ISNULL(pd.cantidad_cancelada, 0) = 0
            """),
            params,
        )

        detalles = conn.execute(
            text(f"DELETE FROM pedido_detalle WHERE id_pedido IN ({placeholders})"),
            params,
        ).rowcount or 0

        pedidos_eliminados = conn.execute(
            text(f"DELETE FROM pedidos WHERE id_pedido IN ({placeholders})"),
            params,
        ).rowcount or 0

    return {
        "pedidos_eliminados": int(pedidos_eliminados),
        "detalles_eliminados": int(detalles),
        "picking_detalles_eliminados": int(picking_detalles_eliminados),
        "picking_pedido_eliminados": int(picking_pedido_eliminados),
        "pickings_vacios_eliminados": int(pickings_vacios_eliminados),
    }


def _select_stock_para_asignar(conn, id_producto: int):
    return list(conn.execute(
        text("""
            SELECT
                su.id_stock_ubicacion,
                su.id_producto,
                su.id_ubicacion,
                su.lote,
                su.cantidad_actual,
                ISNULL(su.cantidad_en_picking, 0) AS cantidad_en_picking,
                CAST(su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible,
                ub.codigo_ubicacion,
                ISNULL(ub.secuencia, 999999) AS secuencia
            FROM stock_ubicacion su WITH (UPDLOCK, ROWLOCK)
            INNER JOIN ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
            WHERE su.id_producto = :id_producto
              AND ub.activo = 1
              AND ISNULL(ub.es_surtible, 1) = 1
              AND ISNULL(ub.es_stage, 0) = 0
              AND (su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0)) > 0
            ORDER BY ISNULL(ub.secuencia, 999999), ub.codigo_ubicacion, su.lote
        """),
        {"id_producto": int(id_producto)},
    ).mappings())


def _insert_picking_detalle(
    conn,
    id_picking: int,
    pedido_row,
    id_ubicacion_origen,
    lote,
    cantidad_solicitada: float,
    cantidad_asignada: float,
    estado: str,
    secuencia: int,
):
    conn.execute(
        text("""
            INSERT INTO picking_detalle
                (
                    id_picking,
                    id_pedido,
                    id_pedido_detalle,
                    nro_pedido,
                    id_cuenta,
                    id_producto,
                    id_ubicacion_origen,
                    lote,
                    cantidad_solicitada,
                    cantidad_asignada,
                    estado,
                    secuencia,
                    texto_item
                )
            VALUES
                (
                    :id_picking,
                    :id_pedido,
                    :id_pedido_detalle,
                    :nro_pedido,
                    :id_cuenta,
                    :id_producto,
                    :id_ubicacion_origen,
                    :lote,
                    :cantidad_solicitada,
                    :cantidad_asignada,
                    :estado,
                    :secuencia,
                    :texto_item
                )
        """),
        {
            "id_picking": int(id_picking),
            "id_pedido": int(pedido_row["id_pedido"]),
            "id_pedido_detalle": int(pedido_row["id_pedido_detalle"]),
            "nro_pedido": pedido_row["nro_pedido"],
            "id_cuenta": int(pedido_row["id_cuenta"]),
            "id_producto": int(pedido_row["id_producto"]),
            "id_ubicacion_origen": int(id_ubicacion_origen) if id_ubicacion_origen else None,
            "lote": lote,
            "cantidad_solicitada": float(cantidad_solicitada),
            "cantidad_asignada": float(cantidad_asignada),
            "estado": estado,
            "secuencia": int(secuencia or 999999),
            "texto_item": pedido_row.get("texto_item"),
        },
    )


def _recalcular_picking_estado(conn, id_picking: int):
    counts = conn.execute(
        text("""
            SELECT
                SUM(CASE WHEN estado = 'LIBERADO' THEN 1 ELSE 0 END) AS liberado,
                SUM(CASE WHEN estado = 'CORTO' THEN 1 ELSE 0 END) AS corto,
                SUM(CASE WHEN estado = 'CANCELADO' THEN 1 ELSE 0 END) AS cancelado,
                SUM(CASE WHEN estado = 'COMPLETADO' THEN 1 ELSE 0 END) AS completado
            FROM picking_detalle
            WHERE id_picking = :id_picking
        """),
        {"id_picking": int(id_picking)},
    ).mappings().first()

    liberado = int(counts["liberado"] or 0)
    corto = int(counts["corto"] or 0)
    cancelado = int(counts["cancelado"] or 0)
    completado = int(counts["completado"] or 0)

    if liberado > 0:
        if completado > 0:
            estado = "COMPLETADO-PARCIAL"
        elif corto > 0 or cancelado > 0:
            estado = "LIBERADO-CORTO"
        else:
            estado = "LIBERADO"
    else:
        if corto > 0:
            estado = "COMPLETADO-PARCIAL" if completado > 0 else "LIBERADO-CORTO"
        elif cancelado > 0:
            estado = "COMPLETADO-CORTO"
        elif completado > 0:
            estado = "COMPLETADO"
        else:
            estado = "CANCELADO"

    totals = conn.execute(
        text("""
            SELECT
                CAST(SUM(cantidad_solicitada) AS DECIMAL(18,2)) AS qty_total,
                CAST(SUM(CASE WHEN estado IN ('LIBERADO','COMPLETADO') THEN cantidad_asignada ELSE 0 END) AS DECIMAL(18,2)) AS qty_asignada,
                CAST(SUM(CASE WHEN estado = 'CORTO' THEN cantidad_solicitada ELSE 0 END) AS DECIMAL(18,2)) AS qty_corto
            FROM picking_detalle
            WHERE id_picking = :id_picking
        """),
        {"id_picking": int(id_picking)},
    ).mappings().first()

    conn.execute(
        text("""
            UPDATE picking_header
            SET estado = :estado,
                qty_total = ISNULL(:qty_total, 0),
                qty_asignada = ISNULL(:qty_asignada, 0),
                qty_corto = ISNULL(:qty_corto, 0),
                fecha_actualizacion = dbo.fn_now_bogota_lima()
            WHERE id_picking = :id_picking
              AND estado <> 'CANCELADO'
        """),
        {
            "id_picking": int(id_picking),
            "estado": estado,
            "qty_total": totals["qty_total"] or 0,
            "qty_asignada": totals["qty_asignada"] or 0,
            "qty_corto": totals["qty_corto"] or 0,
        },
    )

    # Actualiza pedidos relacionados.
    pedido_ids = [r[0] for r in conn.execute(
        text("SELECT DISTINCT id_pedido FROM picking_pedido WHERE id_picking = :id_picking"),
        {"id_picking": int(id_picking)},
    ).all()]

    for id_pedido in pedido_ids:
        res = conn.execute(
            text("""
                SELECT
                    SUM(CASE WHEN (cantidad_pedida - cantidad_atendida - cantidad_cancelada) > 0 THEN 1 ELSE 0 END) AS pendientes,
                    SUM(CASE WHEN cantidad_atendida > 0 THEN 1 ELSE 0 END) AS atendidos,
                    SUM(CASE WHEN cantidad_cancelada > 0 THEN 1 ELSE 0 END) AS cancelados
                FROM pedido_detalle
                WHERE id_pedido = :id_pedido
            """),
            {"id_pedido": int(id_pedido)},
        ).mappings().first()
        pendientes = int(res["pendientes"] or 0)
        atendidos = int(res["atendidos"] or 0)
        cancelados = int(res["cancelados"] or 0)
        if pendientes == 0:
            pedido_estado = "COMPLETADO-CORTO" if cancelados > 0 else "COMPLETADO"
        else:
            pedido_estado = "COMPLETADO-PARCIAL" if atendidos > 0 else "EN_PICKING"
        conn.execute(
            text("""
                UPDATE pedidos
                SET estado = :estado,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_pedido = :id_pedido
                  AND estado <> 'CANCELADO'
            """),
            {"id_pedido": int(id_pedido), "estado": pedido_estado},
        )

    return estado


def crear_picking_desde_pedidos(id_pedidos: list[int], id_usuario: int, texto_cabecera: str | None = None) -> dict:
    if not id_pedidos:
        raise ValueError("Selecciona al menos un pedido.")

    with get_engine().begin() as conn:
        nro_picking = _next_correlative(conn, "picking_header", "nro_picking", "PK", 3)
        id_picking = conn.execute(
            text("""
                INSERT INTO picking_header
                    (nro_picking, estado, id_usuario_creacion, texto_cabecera)
                OUTPUT INSERTED.id_picking
                VALUES
                    (:nro_picking, 'LIBERADO', :id_usuario, :texto_cabecera)
            """),
            {
                "nro_picking": nro_picking,
                "id_usuario": int(id_usuario),
                "texto_cabecera": texto_cabecera,
            },
        ).scalar_one()

        for id_pedido in id_pedidos:
            conn.execute(
                text("""
                    INSERT INTO picking_pedido (id_picking, id_pedido)
                    VALUES (:id_picking, :id_pedido)
                """),
                {"id_picking": int(id_picking), "id_pedido": int(id_pedido)},
            )

        placeholders = ",".join(f":p{i}" for i, _ in enumerate(id_pedidos))
        params = {f"p{i}": int(v) for i, v in enumerate(id_pedidos)}
        details = list(conn.execute(
            text(f"""
                SELECT
                    p.id_pedido,
                    p.nro_pedido,
                    p.id_cuenta,
                    pd.id_pedido_detalle,
                    pd.id_producto,
                    pd.texto_item,
                    CAST(pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada AS DECIMAL(18,2)) AS cantidad_pendiente
                FROM pedidos p WITH (UPDLOCK, ROWLOCK)
                INNER JOIN pedido_detalle pd WITH (UPDLOCK, ROWLOCK) ON pd.id_pedido = p.id_pedido
                WHERE p.id_pedido IN ({placeholders})
                  AND p.estado = 'CREADO'
                  AND pd.estado = 'PENDIENTE'
                  AND (pd.cantidad_pedida - pd.cantidad_asignada - pd.cantidad_cancelada) > 0
                ORDER BY p.nro_pedido, pd.nro_linea
            """),
            params,
        ).mappings())

        if not details:
            raise ValueError("No hay detalles pendientes para crear picking.")

        qty_total = 0.0
        qty_asignada = 0.0
        qty_corto = 0.0
        cortos = []

        for d in details:
            pending = float(d["cantidad_pendiente"])
            qty_total += pending
            remaining = pending
            assigned_total = 0.0
            stock_rows = _select_stock_para_asignar(conn, int(d["id_producto"]))

            for stock in stock_rows:
                if remaining <= 0:
                    break
                available = float(stock["cantidad_disponible"] or 0)
                if available <= 0:
                    continue
                assign_qty = min(available, remaining)
                conn.execute(
                    text("""
                        UPDATE stock_ubicacion
                        SET cantidad_en_picking = ISNULL(cantidad_en_picking, 0) + :assign_qty,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_stock_ubicacion = :id_stock_ubicacion
                    """),
                    {"assign_qty": assign_qty, "id_stock_ubicacion": int(stock["id_stock_ubicacion"])},
                )
                _insert_picking_detalle(
                    conn,
                    int(id_picking),
                    d,
                    int(stock["id_ubicacion"]),
                    stock["lote"],
                    assign_qty,
                    assign_qty,
                    "LIBERADO",
                    int(stock["secuencia"] or 999999),
                )
                remaining -= assign_qty
                assigned_total += assign_qty
                qty_asignada += assign_qty

            if assigned_total > 0:
                conn.execute(
                    text("""
                        UPDATE pedido_detalle
                        SET cantidad_asignada = cantidad_asignada + :assigned_total,
                            estado = CASE WHEN :remaining > 0 THEN 'CORTO' ELSE 'EN_PICKING' END,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_pedido_detalle = :id_pedido_detalle
                    """),
                    {
                        "assigned_total": assigned_total,
                        "remaining": remaining,
                        "id_pedido_detalle": int(d["id_pedido_detalle"]),
                    },
                )

            if remaining > 0:
                _insert_picking_detalle(
                    conn,
                    int(id_picking),
                    d,
                    None,
                    None,
                    remaining,
                    0,
                    "CORTO",
                    999999,
                )
                qty_corto += remaining
                cortos.append({
                    "nro_pedido": d["nro_pedido"],
                    "id_pedido_detalle": int(d["id_pedido_detalle"]),
                    "id_producto": int(d["id_producto"]),
                    "cantidad_corta": remaining,
                })
                if assigned_total == 0:
                    conn.execute(
                        text("""
                            UPDATE pedido_detalle
                            SET estado = 'CORTO',
                                fecha_actualizacion = dbo.fn_now_bogota_lima()
                            WHERE id_pedido_detalle = :id_pedido_detalle
                        """),
                        {"id_pedido_detalle": int(d["id_pedido_detalle"])},
                    )

        conn.execute(
            text("""
                UPDATE pedidos
                SET estado = 'EN_PICKING',
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_pedido IN (
                    SELECT id_pedido FROM picking_pedido WHERE id_picking = :id_picking
                )
            """),
            {"id_picking": int(id_picking)},
        )

        estado = "LIBERADO-CORTO" if qty_corto > 0 else "LIBERADO"
        conn.execute(
            text("""
                UPDATE picking_header
                SET estado = :estado,
                    qty_total = :qty_total,
                    qty_asignada = :qty_asignada,
                    qty_corto = :qty_corto,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_picking = :id_picking
            """),
            {
                "id_picking": int(id_picking),
                "estado": estado,
                "qty_total": qty_total,
                "qty_asignada": qty_asignada,
                "qty_corto": qty_corto,
            },
        )

    return {
        "id_picking": int(id_picking),
        "nro_picking": nro_picking,
        "estado": estado,
        "qty_total": qty_total,
        "qty_asignada": qty_asignada,
        "qty_corto": qty_corto,
        "cortos": cortos,
    }


def cancelar_picking(id_picking: int) -> None:
    with get_engine().begin() as conn:
        completed = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM picking_detalle
                WHERE id_picking = :id_picking
                  AND estado = 'COMPLETADO'
            """),
            {"id_picking": int(id_picking)},
        ).scalar_one()
        if completed:
            raise ValueError("No se puede eliminar un picking con tareas ya atendidas.")

        liberados = list(conn.execute(
            text("""
                SELECT id_producto, id_ubicacion_origen, lote, cantidad_asignada, id_pedido_detalle
                FROM picking_detalle
                WHERE id_picking = :id_picking
                  AND estado = 'LIBERADO'
            """),
            {"id_picking": int(id_picking)},
        ).mappings())

        for row in liberados:
            conn.execute(
                text("""
                    UPDATE stock_ubicacion
                    SET cantidad_en_picking = CASE
                            WHEN ISNULL(cantidad_en_picking, 0) >= :qty THEN ISNULL(cantidad_en_picking, 0) - :qty
                            ELSE 0
                        END,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion_origen
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "qty": float(row["cantidad_asignada"]),
                    "id_producto": int(row["id_producto"]),
                    "id_ubicacion_origen": int(row["id_ubicacion_origen"]),
                    "lote": row["lote"],
                },
            )
            conn.execute(
                text("""
                    UPDATE pedido_detalle
                    SET cantidad_asignada = CASE
                            WHEN cantidad_asignada >= :qty THEN cantidad_asignada - :qty
                            ELSE 0
                        END,
                        estado = 'PENDIENTE',
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_pedido_detalle = :id_pedido_detalle
                """),
                {
                    "qty": float(row["cantidad_asignada"]),
                    "id_pedido_detalle": int(row["id_pedido_detalle"]),
                },
            )

        conn.execute(
            text("""
                UPDATE pedido_detalle
                SET estado = 'PENDIENTE', fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_pedido_detalle IN (
                    SELECT id_pedido_detalle FROM picking_detalle
                    WHERE id_picking = :id_picking AND estado = 'CORTO'
                )
            """),
            {"id_picking": int(id_picking)},
        )

        conn.execute(
            text("""
                UPDATE pedidos
                SET estado = 'CREADO', fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_pedido IN (
                    SELECT id_pedido FROM picking_pedido WHERE id_picking = :id_picking
                )
            """),
            {"id_picking": int(id_picking)},
        )

        conn.execute(
            text("""
                UPDATE picking_detalle
                SET estado = 'CANCELADO', fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_picking = :id_picking
                  AND estado IN ('LIBERADO','CORTO')
            """),
            {"id_picking": int(id_picking)},
        )
        conn.execute(
            text("""
                UPDATE picking_header
                SET estado = 'CANCELADO', fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_picking = :id_picking
            """),
            {"id_picking": int(id_picking)},
        )


def reasignar_cortos_picking(ids_cortos: list[int]) -> dict:
    if not ids_cortos:
        raise ValueError("Selecciona al menos un corto.")

    with get_engine().begin() as conn:
        placeholders = ",".join(f":c{i}" for i, _ in enumerate(ids_cortos))
        params = {f"c{i}": int(v) for i, v in enumerate(ids_cortos)}
        cortos = list(conn.execute(
            text(f"""
                SELECT *
                FROM picking_detalle WITH (UPDLOCK, ROWLOCK)
                WHERE id_picking_detalle IN ({placeholders})
                  AND estado = 'CORTO'
            """),
            params,
        ).mappings())

        reasignado = 0.0
        sigue_corto = 0.0
        picking_ids = set()

        for corto in cortos:
            picking_ids.add(int(corto["id_picking"]))
            remaining = float(corto["cantidad_solicitada"])
            assigned = 0.0
            stock_rows = _select_stock_para_asignar(conn, int(corto["id_producto"]))
            for stock in stock_rows:
                if remaining <= 0:
                    break
                available = float(stock["cantidad_disponible"] or 0)
                if available <= 0:
                    continue
                assign_qty = min(available, remaining)
                conn.execute(
                    text("""
                        UPDATE stock_ubicacion
                        SET cantidad_en_picking = ISNULL(cantidad_en_picking, 0) + :qty,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_stock_ubicacion = :id_stock_ubicacion
                    """),
                    {"qty": assign_qty, "id_stock_ubicacion": int(stock["id_stock_ubicacion"])},
                )
                _insert_picking_detalle(
                    conn,
                    int(corto["id_picking"]),
                    corto,
                    int(stock["id_ubicacion"]),
                    stock["lote"],
                    assign_qty,
                    assign_qty,
                    "LIBERADO",
                    int(stock["secuencia"] or 999999),
                )
                remaining -= assign_qty
                assigned += assign_qty
                reasignado += assign_qty

            if assigned > 0:
                conn.execute(
                    text("""
                        UPDATE pedido_detalle
                        SET cantidad_asignada = cantidad_asignada + :assigned,
                            estado = CASE WHEN :remaining > 0 THEN 'CORTO' ELSE 'EN_PICKING' END,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_pedido_detalle = :id_pedido_detalle
                    """),
                    {
                        "assigned": assigned,
                        "remaining": remaining,
                        "id_pedido_detalle": int(corto["id_pedido_detalle"]),
                    },
                )

            if remaining <= 0:
                conn.execute(
                    text("""
                        UPDATE picking_detalle
                        SET estado = 'REASIGNADO', fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_picking_detalle = :id_picking_detalle
                    """),
                    {"id_picking_detalle": int(corto["id_picking_detalle"])},
                )
            else:
                sigue_corto += remaining
                conn.execute(
                    text("""
                        UPDATE picking_detalle
                        SET cantidad_solicitada = :remaining,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_picking_detalle = :id_picking_detalle
                    """),
                    {
                        "remaining": remaining,
                        "id_picking_detalle": int(corto["id_picking_detalle"]),
                    },
                )

        for id_picking in picking_ids:
            _recalcular_picking_estado(conn, int(id_picking))

    return {"reasignado": reasignado, "sigue_corto": sigue_corto, "cortos_procesados": len(cortos)}


def cancelar_cortos_picking(ids_cortos: list[int]) -> dict:
    if not ids_cortos:
        raise ValueError("Selecciona al menos un corto.")

    with get_engine().begin() as conn:
        placeholders = ",".join(f":c{i}" for i, _ in enumerate(ids_cortos))
        params = {f"c{i}": int(v) for i, v in enumerate(ids_cortos)}
        cortos = list(conn.execute(
            text(f"""
                SELECT *
                FROM picking_detalle WITH (UPDLOCK, ROWLOCK)
                WHERE id_picking_detalle IN ({placeholders})
                  AND estado = 'CORTO'
            """),
            params,
        ).mappings())
        picking_ids = set()
        qty_cancelada = 0.0
        for corto in cortos:
            picking_ids.add(int(corto["id_picking"]))
            qty = float(corto["cantidad_solicitada"])
            qty_cancelada += qty
            conn.execute(
                text("""
                    UPDATE picking_detalle
                    SET estado = 'CANCELADO',
                        cantidad_cancelada = cantidad_solicitada,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking_detalle = :id_picking_detalle
                """),
                {"id_picking_detalle": int(corto["id_picking_detalle"])},
            )
            conn.execute(
                text("""
                    UPDATE pedido_detalle
                    SET cantidad_cancelada = cantidad_cancelada + :qty,
                        estado = CASE
                            WHEN cantidad_pedida <= cantidad_atendida + cantidad_cancelada + :qty THEN 'CANCELADO'
                            ELSE estado
                        END,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_pedido_detalle = :id_pedido_detalle
                """),
                {"qty": qty, "id_pedido_detalle": int(corto["id_pedido_detalle"])},
            )

        for id_picking in picking_ids:
            estado_final = _recalcular_picking_estado(conn, int(id_picking))
            # Si el picking fue atendido por RF y tiene movimientos reales
            # pendientes de aprobación, debe volver a mostrarse en
            # Atención de Picking → Aprobación RF después de cancelar cortos.
            conn.execute(
                text("""
                    UPDATE ph
                    SET requiere_aprobacion_admin = 1,
                        estado_aprobacion_admin = CASE
                            WHEN ISNULL(ph.estado_aprobacion_admin, '') IN ('', 'PENDIENTE') THEN 'PENDIENTE'
                            ELSE ph.estado_aprobacion_admin
                        END,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    FROM dbo.picking_header ph
                    WHERE ph.id_picking = :id_picking
                      AND EXISTS (
                            SELECT 1
                            FROM dbo.movimientos m
                            WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
                              AND m.estado = 'PENDIENTE_APROBACION'
                              AND m.referencia = 'PICKING ' + ph.nro_picking
                      )
                """),
                {"id_picking": int(id_picking)},
            )

    return {"cortos_cancelados": len(cortos), "qty_cancelada": qty_cancelada}


def atender_tarea_picking_con_corto_parcial(
    id_picking_detalle: int,
    cantidad_encontrada: float,
    id_usuario: int,
    observacion: str | None = None,
    requiere_aprobacion_admin: bool = False,
    origen_atencion: str = 'RF',
    transcript: str | None = None,
    confidence: float | None = None,
) -> dict:
    """Atiende parcialmente una tarea y genera un corto por la diferencia.

    Ejemplo operativo:
        Tarea asignada: 5
        Operario reporta: 3

    Resultado:
        - Se atienden 3 unidades.
        - Se libera toda la reserva original de 5.
        - Se descuenta del stock físico la cantidad asignada original para no
          dejar stock fantasma en la ubicación donde el operario no encontró todo.
        - Se crea una línea adicional de picking_detalle en estado CORTO por 2.
        - El pedido queda pendiente/corto por esas 2 unidades hasta reasignación
          o cancelación administrativa.
    """
    found_qty = float(cantidad_encontrada or 0)
    if found_qty < 0:
        raise ValueError("La cantidad encontrada no puede ser negativa.")

    movimiento_estado = 'PENDIENTE_APROBACION' if requiere_aprobacion_admin else 'CONFIRMADO'
    origen_atencion = str(origen_atencion or ('RF' if requiere_aprobacion_admin else 'DESKTOP')).upper()

    with get_engine().begin() as conn:
        tarea = conn.execute(
            text("""
                SELECT
                    pd.*,
                    ph.nro_picking,
                    p.sku
                FROM dbo.picking_detalle pd WITH (UPDLOCK, ROWLOCK)
                INNER JOIN dbo.picking_header ph ON ph.id_picking = pd.id_picking
                INNER JOIN dbo.productos p ON p.id_producto = pd.id_producto
                WHERE pd.id_picking_detalle = :id_picking_detalle
                  AND pd.estado = 'LIBERADO'
            """),
            {"id_picking_detalle": int(id_picking_detalle)},
        ).mappings().first()

        if not tarea:
            raise ValueError("La tarea no está liberada o ya fue procesada.")

        assigned_qty = float(tarea["cantidad_asignada"] or 0)
        if assigned_qty <= 0:
            raise ValueError("La tarea no tiene cantidad asignada.")
        if found_qty > assigned_qty:
            raise ValueError("La cantidad encontrada no puede superar la cantidad asignada.")

        short_qty = round(assigned_qty - found_qty, 6)
        if short_qty <= 0:
            # Si no hay corto, usar la ruta normal de atención.
            return atender_tareas_picking(
                [int(id_picking_detalle)],
                id_usuario=int(id_usuario),
                observacion=observacion,
                requiere_aprobacion_admin=requiere_aprobacion_admin,
                origen_atencion=origen_atencion,
            )

        stage_salida_id = None
        if requiere_aprobacion_admin and found_qty > 0:
            stage_salida_id = conn.execute(
                text("""
                    SELECT id_ubicacion
                    FROM dbo.ubicaciones
                    WHERE codigo_ubicacion = 'B1.ST.01'
                      AND activo = 1
                """)
            ).scalar()
            if not stage_salida_id:
                raise ValueError("No existe la ubicación stage de salida B1.ST.01 activa. Ejecuta la migración 018.")
            stage_salida_id = int(stage_salida_id)

        stock = conn.execute(
            text("""
                SELECT cantidad_actual, ISNULL(cantidad_en_picking, 0) AS cantidad_en_picking
                FROM dbo.stock_ubicacion WITH (UPDLOCK, ROWLOCK)
                WHERE id_producto = :id_producto
                  AND id_ubicacion = :id_ubicacion
                  AND ISNULL(lote, '') = ISNULL(:lote, '')
            """),
            {
                "id_producto": int(tarea["id_producto"]),
                "id_ubicacion": int(tarea["id_ubicacion_origen"]),
                "lote": tarea["lote"],
            },
        ).mappings().first()

        if not stock or float(stock["cantidad_actual"] or 0) < assigned_qty:
            raise ValueError(f"Stock insuficiente al registrar corto parcial del SKU {tarea['sku']}.")

        # Se descuenta toda la cantidad originalmente reservada: la parte encontrada
        # sale a stage/cuenta, la parte no encontrada queda trazada como corto.
        conn.execute(
            text("""
                UPDATE dbo.stock_ubicacion
                SET cantidad_actual = cantidad_actual - :assigned_qty,
                    cantidad_en_picking = CASE
                        WHEN ISNULL(cantidad_en_picking, 0) >= :assigned_qty THEN ISNULL(cantidad_en_picking, 0) - :assigned_qty
                        ELSE 0
                    END,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_producto = :id_producto
                  AND id_ubicacion = :id_ubicacion
                  AND ISNULL(lote, '') = ISNULL(:lote, '')
            """),
            {
                "assigned_qty": assigned_qty,
                "id_producto": int(tarea["id_producto"]),
                "id_ubicacion": int(tarea["id_ubicacion_origen"]),
                "lote": tarea["lote"],
            },
        )

        conn.execute(
            text("""
                DELETE FROM dbo.stock_ubicacion
                WHERE id_producto = :id_producto
                  AND id_ubicacion = :id_ubicacion
                  AND ISNULL(lote, '') = ISNULL(:lote, '')
                  AND cantidad_actual <= 0
                  AND ISNULL(cantidad_en_picking, 0) <= 0
            """),
            {
                "id_producto": int(tarea["id_producto"]),
                "id_ubicacion": int(tarea["id_ubicacion_origen"]),
                "lote": tarea["lote"],
            },
        )

        id_cuenta = int(tarea["id_cuenta"])
        id_movimiento = None
        qty_atendida = 0.0

        if found_qty > 0:
            id_movimiento = conn.execute(
                text("""
                    INSERT INTO dbo.movimientos
                        (tipo_movimiento, fecha_movimiento, id_cuenta, referencia, observacion, id_usuario, estado)
                    OUTPUT INSERTED.id_movimiento
                    VALUES
                        ('SALIDA_CUENTA', dbo.fn_now_bogota_lima(), :id_cuenta, :referencia, :observacion, :id_usuario, :estado)
                """),
                {
                    "id_cuenta": id_cuenta,
                    "referencia": f"PICKING {tarea['nro_picking']}",
                    "observacion": observacion or "Atención parcial con corto",
                    "id_usuario": int(id_usuario),
                    "estado": movimiento_estado,
                },
            ).scalar_one()

            if requiere_aprobacion_admin:
                conn.execute(
                    text("""
                        IF EXISTS (
                            SELECT 1
                            FROM dbo.stock_ubicacion WITH (UPDLOCK, ROWLOCK)
                            WHERE id_producto = :id_producto
                              AND id_ubicacion = :id_stage
                              AND ISNULL(lote, '') = ISNULL(:lote, '')
                        )
                        BEGIN
                            UPDATE dbo.stock_ubicacion
                            SET cantidad_actual = cantidad_actual + :qty,
                                fecha_actualizacion = dbo.fn_now_bogota_lima()
                            WHERE id_producto = :id_producto
                              AND id_ubicacion = :id_stage
                              AND ISNULL(lote, '') = ISNULL(:lote, '')
                        END
                        ELSE
                        BEGIN
                            INSERT INTO dbo.stock_ubicacion
                                (id_producto, id_ubicacion, lote, cantidad_actual, cantidad_en_picking, fecha_actualizacion)
                            VALUES
                                (:id_producto, :id_stage, :lote, :qty, 0, dbo.fn_now_bogota_lima())
                        END
                    """),
                    {
                        "id_producto": int(tarea["id_producto"]),
                        "id_stage": int(stage_salida_id),
                        "lote": tarea["lote"],
                        "qty": found_qty,
                    },
                )

            conn.execute(
                text("""
                    INSERT INTO dbo.movimiento_detalle
                        (id_movimiento, id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, lote, observacion, id_picking_detalle)
                    VALUES
                        (:id_movimiento, :id_producto, :id_ubicacion_origen, :id_ubicacion_destino, :cantidad, :lote, :observacion, :id_picking_detalle)
                """),
                {
                    "id_movimiento": int(id_movimiento),
                    "id_producto": int(tarea["id_producto"]),
                    "id_ubicacion_origen": int(tarea["id_ubicacion_origen"]),
                    "id_ubicacion_destino": stage_salida_id if requiere_aprobacion_admin else None,
                    "cantidad": found_qty,
                    "lote": tarea["lote"],
                    "observacion": tarea.get("texto_item") or observacion,
                    "id_picking_detalle": int(tarea["id_picking_detalle"]),
                },
            )

            if not requiere_aprobacion_admin:
                conn.execute(
                    text("""
                        IF EXISTS (SELECT 1 FROM dbo.stock_cuenta WHERE id_cuenta = :id_cuenta AND id_producto = :id_producto)
                        BEGIN
                            UPDATE dbo.stock_cuenta
                            SET cantidad_entregada = cantidad_entregada + :qty,
                                fecha_actualizacion = dbo.fn_now_bogota_lima()
                            WHERE id_cuenta = :id_cuenta
                              AND id_producto = :id_producto
                        END
                        ELSE
                        BEGIN
                            INSERT INTO dbo.stock_cuenta (id_cuenta, id_producto, cantidad_entregada, cantidad_devuelta)
                            VALUES (:id_cuenta, :id_producto, :qty, 0)
                        END
                    """),
                    {"id_cuenta": id_cuenta, "id_producto": int(tarea["id_producto"]), "qty": found_qty},
                )

            conn.execute(
                text("""
                    UPDATE dbo.picking_detalle
                    SET estado = 'COMPLETADO',
                        cantidad_solicitada = :found_qty,
                        cantidad_asignada = :found_qty,
                        cantidad_atendida = :found_qty,
                        metodo_confirmacion = 'VOZ_CORTO',
                        confirmado_por_voz = CASE WHEN COL_LENGTH('dbo.picking_detalle', 'confirmado_por_voz') IS NOT NULL THEN 1 ELSE confirmado_por_voz END,
                        texto_confirmacion_voz = :transcript,
                        confianza_voz = :confidence,
                        cantidad_reportada_voz = :found_qty,
                        fecha_confirmacion_voz = dbo.fn_now_bogota_lima(),
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking_detalle = :id_picking_detalle
                """),
                {
                    "id_picking_detalle": int(tarea["id_picking_detalle"]),
                    "found_qty": found_qty,
                    "transcript": transcript,
                    "confidence": confidence,
                },
            )
            qty_atendida = found_qty
        else:
            conn.execute(
                text("""
                    UPDATE dbo.picking_detalle
                    SET estado = 'CORTO',
                        cantidad_asignada = 0,
                        cantidad_atendida = 0,
                        metodo_confirmacion = 'VOZ_CORTO',
                        texto_confirmacion_voz = :transcript,
                        confianza_voz = :confidence,
                        cantidad_reportada_voz = 0,
                        fecha_confirmacion_voz = dbo.fn_now_bogota_lima(),
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking_detalle = :id_picking_detalle
                """),
                {
                    "id_picking_detalle": int(tarea["id_picking_detalle"]),
                    "transcript": transcript,
                    "confidence": confidence,
                },
            )

        if short_qty > 0 and found_qty > 0:
            _insert_picking_detalle(
                conn,
                int(tarea["id_picking"]),
                tarea,
                None,
                tarea["lote"],
                short_qty,
                0,
                "CORTO",
                999999,
            )

        # No se genera movimiento por el corto. El corto queda gestionable solo
        # en picking_detalle/pedido_detalle para reasignación o cancelación.
        # Los movimientos deben reflejar únicamente ingresos, salidas reales y
        # transferencias.

        conn.execute(
            text("""
                UPDATE dbo.pedido_detalle
                SET cantidad_asignada = CASE
                        WHEN cantidad_asignada >= :short_qty THEN cantidad_asignada - :short_qty
                        ELSE 0
                    END,
                    cantidad_atendida = cantidad_atendida + :found_qty,
                    estado = CASE
                        WHEN :short_qty > 0 THEN 'CORTO'
                        WHEN cantidad_pedida <= cantidad_atendida + cantidad_cancelada + :found_qty THEN 'COMPLETADO'
                        ELSE estado
                    END,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_pedido_detalle = :id_pedido_detalle
            """),
            {
                "short_qty": short_qty,
                "found_qty": found_qty,
                "id_pedido_detalle": int(tarea["id_pedido_detalle"]),
            },
        )

        if requiere_aprobacion_admin and found_qty > 0:
            conn.execute(
                text("""
                    UPDATE dbo.picking_header
                    SET origen_atencion = :origen_atencion,
                        requiere_aprobacion_admin = 1,
                        estado_aprobacion_admin = ISNULL(estado_aprobacion_admin, 'PENDIENTE'),
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking = :id_picking
                """),
                {
                    "id_picking": int(tarea["id_picking"]),
                    "origen_atencion": origen_atencion,
                },
            )

        estado_final = _recalcular_picking_estado(conn, int(tarea["id_picking"]))

    return {
        "tareas_atendidas": 1 if found_qty > 0 else 0,
        "qty_atendida": qty_atendida,
        "qty_corto": short_qty,
        "estado_picking": estado_final,
    }


def atender_tareas_picking(
    ids_tareas: list[int],
    id_usuario: int,
    observacion: str | None = None,
    requiere_aprobacion_admin: bool = False,
    origen_atencion: str = 'DESKTOP',
) -> dict:
    if not ids_tareas:
        raise ValueError("Selecciona al menos una tarea.")

    movimiento_estado = 'PENDIENTE_APROBACION' if requiere_aprobacion_admin else 'CONFIRMADO'
    origen_atencion = str(origen_atencion or ('RF' if requiere_aprobacion_admin else 'DESKTOP')).upper()

    with get_engine().begin() as conn:
        placeholders = ",".join(f":t{i}" for i, _ in enumerate(ids_tareas))
        params = {f"t{i}": int(v) for i, v in enumerate(ids_tareas)}
        tareas = list(conn.execute(
            text(f"""
                SELECT
                    pd.*,
                    ph.nro_picking,
                    p.sku
                FROM picking_detalle pd WITH (UPDLOCK, ROWLOCK)
                INNER JOIN picking_header ph ON ph.id_picking = pd.id_picking
                INNER JOIN productos p ON p.id_producto = pd.id_producto
                WHERE pd.id_picking_detalle IN ({placeholders})
                  AND pd.estado = 'LIBERADO'
            """),
            params,
        ).mappings())
        if not tareas:
            raise ValueError("No hay tareas liberadas para atender.")

        stage_salida_id = None
        if requiere_aprobacion_admin:
            stage_salida_id = conn.execute(
                text("""
                    SELECT id_ubicacion
                    FROM ubicaciones
                    WHERE codigo_ubicacion = 'B1.ST.01'
                      AND activo = 1
                """)
            ).scalar()
            if not stage_salida_id:
                raise ValueError("No existe la ubicación stage de salida B1.ST.01 activa. Ejecuta la migración 018.")
            stage_salida_id = int(stage_salida_id)

        movements_by_account = {}
        picking_ids = set()
        qty_atendida = 0.0

        for tarea in tareas:
            qty = float(tarea["cantidad_asignada"])
            picking_ids.add(int(tarea["id_picking"]))
            stock = conn.execute(
                text("""
                    SELECT cantidad_actual, ISNULL(cantidad_en_picking, 0) AS cantidad_en_picking
                    FROM stock_ubicacion WITH (UPDLOCK, ROWLOCK)
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "id_producto": int(tarea["id_producto"]),
                    "id_ubicacion": int(tarea["id_ubicacion_origen"]),
                    "lote": tarea["lote"],
                },
            ).mappings().first()
            if not stock or float(stock["cantidad_actual"] or 0) < qty:
                raise ValueError(f"Stock insuficiente al atender SKU {tarea['sku']}.")

            conn.execute(
                text("""
                    UPDATE stock_ubicacion
                    SET cantidad_actual = cantidad_actual - :qty,
                        cantidad_en_picking = CASE
                            WHEN ISNULL(cantidad_en_picking, 0) >= :qty THEN ISNULL(cantidad_en_picking, 0) - :qty
                            ELSE 0
                        END,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "qty": qty,
                    "id_producto": int(tarea["id_producto"]),
                    "id_ubicacion": int(tarea["id_ubicacion_origen"]),
                    "lote": tarea["lote"],
                },
            )

            id_cuenta = int(tarea["id_cuenta"])
            if id_cuenta not in movements_by_account:
                id_mov = conn.execute(
                    text("""
                        INSERT INTO movimientos
                            (tipo_movimiento, fecha_movimiento, id_cuenta, referencia, observacion, id_usuario, estado)
                        OUTPUT INSERTED.id_movimiento
                        VALUES
                            ('SALIDA_CUENTA', dbo.fn_now_bogota_lima(), :id_cuenta, :referencia, :observacion, :id_usuario, :estado)
                    """),
                    {
                        "id_cuenta": id_cuenta,
                        "referencia": f"PICKING {tarea['nro_picking']}",
                        "observacion": observacion,
                        "id_usuario": int(id_usuario),
                        "estado": movimiento_estado,
                    },
                ).scalar_one()
                movements_by_account[id_cuenta] = int(id_mov)

            id_movimiento = movements_by_account[id_cuenta]
            if requiere_aprobacion_admin:
                # El stock atendido por RF queda físicamente en stage de salida
                # hasta que el administrador apruebe la entrega a cuenta.
                conn.execute(
                    text("""
                        IF EXISTS (
                            SELECT 1
                            FROM stock_ubicacion WITH (UPDLOCK, ROWLOCK)
                            WHERE id_producto = :id_producto
                              AND id_ubicacion = :id_stage
                              AND ISNULL(lote, '') = ISNULL(:lote, '')
                        )
                        BEGIN
                            UPDATE stock_ubicacion
                            SET cantidad_actual = cantidad_actual + :qty,
                                fecha_actualizacion = dbo.fn_now_bogota_lima()
                            WHERE id_producto = :id_producto
                              AND id_ubicacion = :id_stage
                              AND ISNULL(lote, '') = ISNULL(:lote, '')
                        END
                        ELSE
                        BEGIN
                            INSERT INTO stock_ubicacion
                                (id_producto, id_ubicacion, lote, cantidad_actual, cantidad_en_picking, fecha_actualizacion)
                            VALUES
                                (:id_producto, :id_stage, :lote, :qty, 0, dbo.fn_now_bogota_lima())
                        END
                    """),
                    {
                        "id_producto": int(tarea["id_producto"]),
                        "id_stage": stage_salida_id,
                        "lote": tarea["lote"],
                        "qty": qty,
                    },
                )

            conn.execute(
                text("""
                    INSERT INTO movimiento_detalle
                        (id_movimiento, id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, lote, observacion, id_picking_detalle)
                    VALUES
                        (:id_movimiento, :id_producto, :id_ubicacion_origen, :id_ubicacion_destino, :cantidad, :lote, :observacion, :id_picking_detalle)
                """),
                {
                    "id_movimiento": id_movimiento,
                    "id_producto": int(tarea["id_producto"]),
                    "id_ubicacion_origen": int(tarea["id_ubicacion_origen"]),
                    "id_ubicacion_destino": stage_salida_id if requiere_aprobacion_admin else None,
                    "cantidad": qty,
                    "lote": tarea["lote"],
                    "observacion": tarea.get("texto_item"),
                    "id_picking_detalle": int(tarea["id_picking_detalle"]),
                },
            )

            if not requiere_aprobacion_admin:
                conn.execute(
                    text("""
                        IF EXISTS (SELECT 1 FROM stock_cuenta WHERE id_cuenta = :id_cuenta AND id_producto = :id_producto)
                        BEGIN
                            UPDATE stock_cuenta
                            SET cantidad_entregada = cantidad_entregada + :qty,
                                fecha_actualizacion = dbo.fn_now_bogota_lima()
                            WHERE id_cuenta = :id_cuenta
                              AND id_producto = :id_producto
                        END
                        ELSE
                        BEGIN
                            INSERT INTO stock_cuenta (id_cuenta, id_producto, cantidad_entregada, cantidad_devuelta)
                            VALUES (:id_cuenta, :id_producto, :qty, 0)
                        END
                    """),
                    {"id_cuenta": id_cuenta, "id_producto": int(tarea["id_producto"]), "qty": qty},
                )

            conn.execute(
                text("""
                    UPDATE picking_detalle
                    SET estado = 'COMPLETADO',
                        cantidad_atendida = cantidad_asignada,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking_detalle = :id_picking_detalle
                """),
                {"id_picking_detalle": int(tarea["id_picking_detalle"])},
            )
            conn.execute(
                text("""
                    UPDATE pedido_detalle
                    SET cantidad_atendida = cantidad_atendida + :qty,
                        estado = CASE
                            WHEN cantidad_pedida <= cantidad_atendida + cantidad_cancelada + :qty THEN 'COMPLETADO'
                            ELSE estado
                        END,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_pedido_detalle = :id_pedido_detalle
                """),
                {"qty": qty, "id_pedido_detalle": int(tarea["id_pedido_detalle"])},
            )
            qty_atendida += qty

        for id_picking in picking_ids:
            estado_final = _recalcular_picking_estado(conn, int(id_picking))
            if requiere_aprobacion_admin:
                conn.execute(
                    text("""
                        UPDATE picking_header
                        SET origen_atencion = :origen_atencion,
                            requiere_aprobacion_admin = 1,
                            estado_aprobacion_admin = CASE
                                WHEN :estado_final IN ('COMPLETADO','COMPLETADO-CORTO') THEN 'PENDIENTE'
                                ELSE ISNULL(estado_aprobacion_admin, 'PENDIENTE')
                            END,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_picking = :id_picking
                    """),
                    {
                        "id_picking": int(id_picking),
                        "origen_atencion": origen_atencion,
                        "estado_final": estado_final,
                    },
                )

    return {"tareas_atendidas": len(tareas), "qty_atendida": qty_atendida}



def aprobar_pickings_rf(ids_picking: list[int], id_usuario: int) -> dict:
    """Aprueba pickings atendidos por RF y carga el stock a la cuenta logística.

    Durante la atención RF se descuenta stock físico y se generan movimientos
    SALIDA_CUENTA en estado PENDIENTE_APROBACION, pero no se actualiza
    stock_cuenta. Esta función confirma esos movimientos y actualiza el stock
    de la cuenta solicitante.
    """
    if not ids_picking:
        raise ValueError("Selecciona al menos un picking para aprobar.")

    with get_engine().begin() as conn:
        placeholders = ",".join(f":p{i}" for i, _ in enumerate(ids_picking))
        params = {f"p{i}": int(v) for i, v in enumerate(ids_picking)}

        pickings = list(conn.execute(
            text(f"""
                SELECT
                    ph.id_picking,
                    ph.nro_picking,
                    ph.estado,
                    ISNULL(ph.estado_aprobacion_admin, 'PENDIENTE') AS estado_aprobacion_admin,
                    (
                        SELECT COUNT(1)
                        FROM dbo.movimientos m
                        WHERE m.tipo_movimiento = 'SALIDA_CUENTA'
                          AND m.estado = 'PENDIENTE_APROBACION'
                          AND m.referencia = 'PICKING ' + ph.nro_picking
                    ) AS movimientos_pendientes
                FROM dbo.picking_header ph WITH (UPDLOCK, ROWLOCK)
                WHERE ph.id_picking IN ({placeholders})
            """),
            params,
        ).mappings())

        if not pickings:
            raise ValueError("No se encontraron pickings para aprobar.")

        invalid = [
            p["nro_picking"]
            for p in pickings
            if str(p["estado_aprobacion_admin"] or "PENDIENTE") != "PENDIENTE"
            and int(p.get("movimientos_pendientes") or 0) <= 0
        ]
        if invalid:
            raise ValueError("Solo se pueden aprobar pickings RF en estado de aprobación PENDIENTE: " + ", ".join(invalid))

        invalid_estado = [
            p["nro_picking"]
            for p in pickings
            if str(p["estado"] or "") not in {"COMPLETADO", "COMPLETADO-CORTO", "COMPLETADO-PARCIAL"}
        ]
        if invalid_estado:
            raise ValueError("Solo se pueden aprobar pickings completados por RF: " + ", ".join(invalid_estado))

        sin_movimientos = [p["nro_picking"] for p in pickings if int(p.get("movimientos_pendientes") or 0) <= 0]
        if sin_movimientos:
            raise ValueError("El picking no tiene movimientos reales pendientes de aprobación: " + ", ".join(sin_movimientos))

        # Bloqueo operativo: no aprobar pickings RF si todavía tienen cortos activos.
        # El administrador debe reasignar o cancelar los cortos antes de aprobar. Esto
        # evita dejar movimientos PENDIENTE_APROBACION sin cierre y stock detenido en B1.ST.01.
        cortos = list(conn.execute(
            text(f"""
                SELECT
                    ph.nro_picking,
                    COUNT(*) AS cortos_pendientes,
                    CAST(SUM(ISNULL(pd.cantidad_solicitada, 0)) AS DECIMAL(18,2)) AS cantidad_corta
                FROM picking_header ph
                INNER JOIN picking_detalle pd ON pd.id_picking = ph.id_picking
                WHERE ph.id_picking IN ({placeholders})
                  AND pd.estado = 'CORTO'
                GROUP BY ph.nro_picking
            """),
            params,
        ).mappings())
        if cortos:
            msg = ", ".join(
                f"{r['nro_picking']} ({int(r['cortos_pendientes'] or 0)} cortos / {float(r['cantidad_corta'] or 0):,.2f} und.)"
                for r in cortos
            )
            raise ValueError("Picking con cortos, Reasigne o cancele cortos para aprobar: " + msg)

        nro_by_id = {int(p["id_picking"]): str(p["nro_picking"]) for p in pickings}
        qty_aprobada = 0.0
        movimientos_aprobados = 0

        for id_picking, nro_picking in nro_by_id.items():
            movimientos = list(conn.execute(
                text("""
                    SELECT id_movimiento, id_cuenta
                    FROM movimientos WITH (UPDLOCK, ROWLOCK)
                    WHERE tipo_movimiento = 'SALIDA_CUENTA'
                      AND estado = 'PENDIENTE_APROBACION'
                      AND referencia = :referencia
                """),
                {"referencia": f"PICKING {nro_picking}"},
            ).mappings())

            if not movimientos:
                raise ValueError(f"El picking {nro_picking} no tiene movimientos pendientes de aprobación.")

            for mov in movimientos:
                detalles = list(conn.execute(
                    text("""
                        SELECT id_detalle, id_producto, id_ubicacion_destino, lote, cantidad
                        FROM movimiento_detalle
                        WHERE id_movimiento = :id_movimiento
                    """),
                    {"id_movimiento": int(mov["id_movimiento"])},
                ).mappings())

                for det in detalles:
                    qty = float(det["cantidad"] or 0)
                    if qty <= 0:
                        continue
                    # Al aprobar, el stock sale del stage B1.ST.01 y recién se entrega a la cuenta.
                    if det.get("id_ubicacion_destino"):
                        conn.execute(
                            text("""
                                UPDATE stock_ubicacion
                                SET cantidad_actual = cantidad_actual - :qty,
                                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                                WHERE id_producto = :id_producto
                                  AND id_ubicacion = :id_ubicacion_destino
                                  AND ISNULL(lote, '') = ISNULL(:lote, '')
                            """),
                            {
                                "qty": qty,
                                "id_producto": int(det["id_producto"]),
                                "id_ubicacion_destino": int(det["id_ubicacion_destino"]),
                                "lote": det.get("lote"),
                            },
                        )
                        conn.execute(
                            text("""
                                DELETE FROM stock_ubicacion
                                WHERE id_ubicacion = :id_ubicacion_destino
                                  AND id_producto = :id_producto
                                  AND ISNULL(lote, '') = ISNULL(:lote, '')
                                  AND ISNULL(cantidad_actual, 0) <= 0
                                  AND ISNULL(cantidad_en_picking, 0) <= 0
                            """),
                            {
                                "id_producto": int(det["id_producto"]),
                                "id_ubicacion_destino": int(det["id_ubicacion_destino"]),
                                "lote": det.get("lote"),
                            },
                        )

                    conn.execute(
                        text("""
                            IF EXISTS (SELECT 1 FROM stock_cuenta WHERE id_cuenta = :id_cuenta AND id_producto = :id_producto)
                            BEGIN
                                UPDATE stock_cuenta
                                SET cantidad_entregada = cantidad_entregada + :qty,
                                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                                WHERE id_cuenta = :id_cuenta
                                  AND id_producto = :id_producto
                            END
                            ELSE
                            BEGIN
                                INSERT INTO stock_cuenta (id_cuenta, id_producto, cantidad_entregada, cantidad_devuelta)
                                VALUES (:id_cuenta, :id_producto, :qty, 0)
                            END
                        """),
                        {"id_cuenta": int(mov["id_cuenta"]), "id_producto": int(det["id_producto"]), "qty": qty},
                    )
                    qty_aprobada += qty

                    # Programa vencimiento de stock cuenta si aplica y si existe la tabla.
                    conn.execute(
                        text("""
                            IF OBJECT_ID('dbo.stock_cuenta_vencimiento', 'U') IS NOT NULL
                            BEGIN
                                INSERT INTO dbo.stock_cuenta_vencimiento
                                    (id_movimiento, id_detalle, id_cuenta, id_producto, cantidad_programada,
                                     cantidad_aplicada, fecha_movimiento, fecha_vencimiento, estado)
                                SELECT
                                    m.id_movimiento,
                                    md.id_detalle,
                                    m.id_cuenta,
                                    md.id_producto,
                                    CAST(md.cantidad AS DECIMAL(18,2)),
                                    0,
                                    m.fecha_movimiento,
                                    DATEADD(DAY, ISNULL(p.vida_util_cuenta_dias, 0), CAST(m.fecha_movimiento AS DATE)),
                                    'PENDIENTE'
                                FROM dbo.movimientos m
                                INNER JOIN dbo.movimiento_detalle md ON md.id_movimiento = m.id_movimiento
                                INNER JOIN dbo.productos p ON p.id_producto = md.id_producto
                                WHERE md.id_detalle = :id_detalle
                                  AND ISNULL(p.vida_util_cuenta_dias, 0) > 0
                                  AND m.id_cuenta IS NOT NULL
                                  AND NOT EXISTS (
                                      SELECT 1 FROM dbo.stock_cuenta_vencimiento v WHERE v.id_detalle = md.id_detalle
                                  );
                            END
                        """),
                        {"id_detalle": int(det["id_detalle"])},
                    )

                conn.execute(
                    text("""
                        UPDATE movimientos
                        SET estado = 'CONFIRMADO'
                        WHERE id_movimiento = :id_movimiento
                    """),
                    {"id_movimiento": int(mov["id_movimiento"])},
                )
                movimientos_aprobados += 1

            conn.execute(
                text("""
                    UPDATE picking_header
                    SET estado_aprobacion_admin = 'APROBADO',
                        id_usuario_aprobacion = :id_usuario,
                        fecha_aprobacion = dbo.fn_now_bogota_lima(),
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking = :id_picking
                """),
                {"id_picking": int(id_picking), "id_usuario": int(id_usuario)},
            )

    return {
        "pickings_aprobados": len(pickings),
        "movimientos_aprobados": movimientos_aprobados,
        "qty_aprobada": qty_aprobada,
    }


def registrar_transferencia_masiva(fecha_movimiento, texto_cabecera: str, id_usuario: int, items: list[dict]) -> int:
    if not items:
        raise ValueError("No hay posiciones válidas para transferir.")

    with get_engine().begin() as conn:
        id_movimiento = conn.execute(
            text("""
                INSERT INTO movimientos
                    (tipo_movimiento, fecha_movimiento, referencia, observacion, id_usuario, estado)
                OUTPUT INSERTED.id_movimiento
                VALUES
                    ('TRANSFERENCIA', dbo.fn_now_bogota_lima(), 'TRANSFERENCIA_MASIVA', :observacion, :id_usuario, 'CONFIRMADO')
            """),
            {
                "fecha_movimiento": fecha_movimiento,
                "observacion": texto_cabecera,
                "id_usuario": int(id_usuario),
            },
        ).scalar_one()

        for item in items:
            qty = float(item["cantidad"])
            if int(item["id_ubicacion_origen"]) == int(item["id_ubicacion_destino"]):
                raise ValueError("La ubicación origen y destino no pueden ser iguales.")

            stock = conn.execute(
                text("""
                    SELECT cantidad_actual, ISNULL(cantidad_en_picking, 0) AS cantidad_en_picking
                    FROM stock_ubicacion WITH (UPDLOCK, ROWLOCK)
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion_origen
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "id_producto": int(item["id_producto"]),
                    "id_ubicacion_origen": int(item["id_ubicacion_origen"]),
                    "lote": item.get("lote"),
                },
            ).mappings().first()

            available = 0.0
            if stock:
                available = float(stock["cantidad_actual"] or 0) - float(stock["cantidad_en_picking"] or 0)
            if available < qty:
                raise ValueError(f"Stock insuficiente para transferir {item.get('sku', '')}.")

            conn.execute(
                text("""
                    UPDATE stock_ubicacion
                    SET cantidad_actual = cantidad_actual - :qty,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion_origen
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "qty": qty,
                    "id_producto": int(item["id_producto"]),
                    "id_ubicacion_origen": int(item["id_ubicacion_origen"]),
                    "lote": item.get("lote"),
                },
            )

            conn.execute(
                text("""
                    IF EXISTS (
                        SELECT 1 FROM stock_ubicacion
                        WHERE id_producto = :id_producto
                          AND id_ubicacion = :id_ubicacion_destino
                          AND ISNULL(lote, '') = ISNULL(:lote, '')
                    )
                    BEGIN
                        UPDATE stock_ubicacion
                        SET cantidad_actual = cantidad_actual + :qty,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_producto = :id_producto
                          AND id_ubicacion = :id_ubicacion_destino
                          AND ISNULL(lote, '') = ISNULL(:lote, '')
                    END
                    ELSE
                    BEGIN
                        INSERT INTO stock_ubicacion
                            (id_producto, id_ubicacion, lote, cantidad_actual, cantidad_en_picking)
                        VALUES
                            (:id_producto, :id_ubicacion_destino, :lote, :qty, 0)
                    END
                """),
                {
                    "qty": qty,
                    "id_producto": int(item["id_producto"]),
                    "id_ubicacion_destino": int(item["id_ubicacion_destino"]),
                    "lote": item.get("lote"),
                },
            )

            conn.execute(
                text("""
                    INSERT INTO movimiento_detalle
                        (
                            id_movimiento,
                            id_producto,
                            id_ubicacion_origen,
                            id_ubicacion_destino,
                            cantidad,
                            lote,
                            observacion
                        )
                    VALUES
                        (
                            :id_movimiento,
                            :id_producto,
                            :id_ubicacion_origen,
                            :id_ubicacion_destino,
                            :cantidad,
                            :lote,
                            :observacion
                        )
                """),
                {
                    "id_movimiento": int(id_movimiento),
                    "id_producto": int(item["id_producto"]),
                    "id_ubicacion_origen": int(item["id_ubicacion_origen"]),
                    "id_ubicacion_destino": int(item["id_ubicacion_destino"]),
                    "cantidad": qty,
                    "lote": item.get("lote"),
                    "observacion": item.get("texto_item"),
                },
            )

    return int(id_movimiento)

# ---------------------------------------------------------------------------
# Salida Ajuste
# ---------------------------------------------------------------------------

def registrar_salida_ajuste_almacen(
    items: list[dict],
    id_usuario: int,
    referencia: str | None = None,
    observacion: str | None = None,
) -> int:
    """Descuenta stock físico de almacén y registra movimiento SALIDA_AJUSTE."""
    if not items:
        raise ValueError("Selecciona al menos una línea de stock de almacén.")

    with get_engine().begin() as conn:
        id_movimiento = conn.execute(
            text("""
                INSERT INTO movimientos
                    (tipo_movimiento, fecha_movimiento, referencia, observacion, id_usuario, estado)
                OUTPUT INSERTED.id_movimiento
                VALUES
                    ('SALIDA_AJUSTE', dbo.fn_now_bogota_lima(), :referencia, :observacion, :id_usuario, 'CONFIRMADO')
            """),
            {
                "referencia": referencia,
                "observacion": observacion,
                "id_usuario": int(id_usuario),
            },
        ).scalar_one()

        for item in items:
            id_producto = int(item["id_producto"])
            id_ubicacion = int(item["id_ubicacion"])
            cantidad = float(item["cantidad"])
            lote = item.get("lote") or None
            texto_item = item.get("texto_item") or "Salida ajuste almacén"

            disponible = conn.execute(
                text("""
                    SELECT CAST(ISNULL(cantidad_actual, 0) - ISNULL(cantidad_en_picking, 0) AS DECIMAL(18,2))
                    FROM stock_ubicacion WITH (UPDLOCK, HOLDLOCK)
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "id_producto": id_producto,
                    "id_ubicacion": id_ubicacion,
                    "lote": lote,
                },
            ).scalar()

            if disponible is None or float(disponible) < cantidad:
                raise ValueError(
                    f"Stock insuficiente para producto {id_producto} en ubicación {id_ubicacion}. "
                    f"Disponible: {disponible or 0}, solicitado: {cantidad}."
                )

            conn.execute(
                text("""
                    INSERT INTO movimiento_detalle
                        (id_movimiento, id_producto, id_ubicacion_origen, cantidad, lote, observacion)
                    VALUES
                        (:id_movimiento, :id_producto, :id_ubicacion, :cantidad, :lote, :observacion)
                """),
                {
                    "id_movimiento": int(id_movimiento),
                    "id_producto": id_producto,
                    "id_ubicacion": id_ubicacion,
                    "cantidad": cantidad,
                    "lote": lote,
                    "observacion": texto_item,
                },
            )

            conn.execute(
                text("""
                    UPDATE stock_ubicacion
                    SET cantidad_actual = cantidad_actual - :cantidad,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                """),
                {
                    "cantidad": cantidad,
                    "id_producto": id_producto,
                    "id_ubicacion": id_ubicacion,
                    "lote": lote,
                },
            )

            conn.execute(
                text("""
                    DELETE FROM stock_ubicacion
                    WHERE id_producto = :id_producto
                      AND id_ubicacion = :id_ubicacion
                      AND ISNULL(lote, '') = ISNULL(:lote, '')
                      AND ISNULL(cantidad_actual, 0) <= 0
                      AND ISNULL(cantidad_en_picking, 0) <= 0
                """),
                {
                    "id_producto": id_producto,
                    "id_ubicacion": id_ubicacion,
                    "lote": lote,
                },
            )

    return int(id_movimiento)


def registrar_salida_ajuste_cuentas(
    items: list[dict],
    id_usuario: int,
    referencia: str | None = None,
    observacion: str | None = None,
) -> list[int]:
    """Descuenta stock neto de cuentas logísticas y registra SALIDA_AJUSTE.

    Se crea una cabecera de movimiento por cuenta para mantener trazabilidad.
    """
    if not items:
        raise ValueError("Selecciona al menos una línea de stock de cuenta.")

    movements: list[int] = []
    grouped: dict[int, list[dict]] = {}
    for item in items:
        grouped.setdefault(int(item["id_cuenta"]), []).append(item)

    with get_engine().begin() as conn:
        for id_cuenta, group_items in grouped.items():
            id_movimiento = conn.execute(
                text("""
                    INSERT INTO movimientos
                        (tipo_movimiento, fecha_movimiento, id_cuenta, referencia, observacion, id_usuario, estado)
                    OUTPUT INSERTED.id_movimiento
                    VALUES
                        ('SALIDA_AJUSTE', dbo.fn_now_bogota_lima(), :id_cuenta, :referencia, :observacion, :id_usuario, 'CONFIRMADO')
                """),
                {
                    "id_cuenta": int(id_cuenta),
                    "referencia": referencia,
                    "observacion": observacion,
                    "id_usuario": int(id_usuario),
                },
            ).scalar_one()
            movements.append(int(id_movimiento))

            for item in group_items:
                id_producto = int(item["id_producto"])
                cantidad = float(item["cantidad"])
                texto_item = item.get("texto_item") or "Salida ajuste cuenta"

                disponible = conn.execute(
                    text("""
                        SELECT CAST(
                            ISNULL(cantidad_entregada, 0)
                            - ISNULL(cantidad_devuelta, 0)
                            - ISNULL(cantidad_consumida_vida_util, 0)
                            - ISNULL(cantidad_ajuste_salida, 0)
                            AS DECIMAL(18,2)
                        )
                        FROM stock_cuenta WITH (UPDLOCK, HOLDLOCK)
                        WHERE id_cuenta = :id_cuenta
                          AND id_producto = :id_producto
                    """),
                    {
                        "id_cuenta": int(id_cuenta),
                        "id_producto": id_producto,
                    },
                ).scalar()

                if disponible is None or float(disponible) < cantidad:
                    raise ValueError(
                        f"Stock insuficiente en cuenta {id_cuenta} para producto {id_producto}. "
                        f"Disponible: {disponible or 0}, solicitado: {cantidad}."
                    )

                conn.execute(
                    text("""
                        INSERT INTO movimiento_detalle
                            (id_movimiento, id_producto, cantidad, observacion)
                        VALUES
                            (:id_movimiento, :id_producto, :cantidad, :observacion)
                    """),
                    {
                        "id_movimiento": int(id_movimiento),
                        "id_producto": id_producto,
                        "cantidad": cantidad,
                        "observacion": texto_item,
                    },
                )

                conn.execute(
                    text("""
                        UPDATE stock_cuenta
                        SET cantidad_ajuste_salida = ISNULL(cantidad_ajuste_salida, 0) + :cantidad,
                            fecha_actualizacion = dbo.fn_now_bogota_lima()
                        WHERE id_cuenta = :id_cuenta
                          AND id_producto = :id_producto
                    """),
                    {
                        "cantidad": cantidad,
                        "id_cuenta": int(id_cuenta),
                        "id_producto": id_producto,
                    },
                )

    return movements
