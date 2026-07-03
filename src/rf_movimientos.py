from __future__ import annotations

from datetime import date

from src.movimientos import (
    atender_tareas_picking,
    registrar_entrada_migo,
    registrar_transferencia_masiva,
)


def confirmar_ingreso_rf(
    id_proveedor: int,
    fecha_ingreso,
    documento_referencia: str,
    texto_cabecera: str,
    id_usuario: int,
    detalles: list[dict],
) -> int:
    """Confirma un ingreso RF usando la misma lógica de entrada MIGO escritorio."""
    if not detalles:
        raise ValueError("No hay detalles para confirmar.")

    items = []
    for detail in detalles:
        items.append(
            {
                "id_producto": int(detail["id_producto"]),
                "id_ubicacion_destino": int(detail["id_ubicacion_destino"]),
                "cantidad": float(detail["cantidad"]),
                "lote": detail.get("lote") or None,
                "texto_item": detail.get("texto_item") or None,
            }
        )

    return registrar_entrada_migo(
        id_proveedor=int(id_proveedor),
        fecha_ingreso=fecha_ingreso,
        documento_referencia=documento_referencia,
        texto_cabecera=texto_cabecera,
        id_usuario=int(id_usuario),
        items=items,
    )


def confirmar_tarea_picking_rf(id_picking_detalle: int, id_usuario: int) -> dict:
    """Atiende una sola tarea de picking usando la lógica de escritorio."""
    return atender_tareas_picking(
        [int(id_picking_detalle)],
        id_usuario=int(id_usuario),
        observacion="Atención RF",
        requiere_aprobacion_admin=True,
        origen_atencion="RF",
    )


def confirmar_transferencia_rf(
    id_producto: int,
    id_ubicacion_origen: int,
    id_ubicacion_destino: int,
    cantidad: float,
    id_usuario: int,
    lote: str | None = None,
    texto_item: str | None = None,
) -> int:
    """Registra una transferencia RF de una sola posición."""
    return registrar_transferencia_masiva(
        fecha_movimiento=date.today(),
        texto_cabecera="Transferencia RF",
        id_usuario=int(id_usuario),
        items=[
            {
                "id_producto": int(id_producto),
                "id_ubicacion_origen": int(id_ubicacion_origen),
                "id_ubicacion_destino": int(id_ubicacion_destino),
                "cantidad": float(cantidad),
                "lote": lote or None,
                "texto_item": texto_item or "Transferencia RF",
            }
        ],
    )
