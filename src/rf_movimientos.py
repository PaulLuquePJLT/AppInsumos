from __future__ import annotations

from src.movimientos import registrar_entrada_migo


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
