from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

from src.db import get_engine, run_db_with_retry


_COMPONENT_DIR = Path(__file__).resolve().parents[1] / "components" / "rf_voice_assistant"
_rf_voice_assistant = components.declare_component(
    "rf_voice_assistant",
    path=str(_COMPONENT_DIR),
)


VOICE_COMMAND_LABELS = {
    "INICIAR": "Iniciar picking",
    "ESTOY_AQUI": "Estoy aquí",
    "OK": "Confirmación",
    "CONFIRMAR": "Confirmar",
    "REPETIR": "Repetir instrucción",
    "REPETIR_UBICACION": "Repetir ubicación",
    "REPETIR_CODIGO": "Repetir código",
    "REPETIR_CANTIDAD": "Repetir cantidad",
    "CANCELAR_PICKING": "Cancelar picking",
    "CONFIRMAR_CANCELACION": "Confirmar cancelación",
    "CORTO": "Reportar corto",
    "CANTIDAD": "Cantidad informada",
    "CONFIRMAR_CORTO": "Confirmar corto",
    "CONFIRMAR_AUDITORIA": "Confirmar auditoría",
    "AYUDA": "Ayuda",
    "NO_RECONOCIDO": "No reconocido",
}


def _fmt_qty(value: Any) -> str:
    try:
        qty = float(value or 0)
    except Exception:
        qty = 0
    if qty.is_integer():
        return str(int(qty))
    return f"{qty:g}"


def _unit_name(tarea: dict) -> str:
    return str(tarea.get("nombre_unidad") or tarea.get("codigo_unidad") or "unidades").strip()


def _zone_name(tarea: dict) -> str:
    return str(tarea.get("nombre_zona") or tarea.get("codigo_zona") or "zona no informada").strip()


def build_voice_prompt_for_phase(
    tarea: dict,
    *,
    current: int,
    total: int,
    phase: str,
    nro_picking: str = "",
    include_zone: bool = True,
    short_qty: float | None = None,
) -> str:
    """Construye la frase conversacional para una fase de Voice Picking."""
    ubicacion = str(tarea.get("codigo_ubicacion") or "ubicación no informada").strip()
    zona = _zone_name(tarea)
    sku = str(tarea.get("sku") or "").strip()
    producto = str(tarea.get("nombre_producto") or "artículo no informado").strip()
    unidad = _unit_name(tarea)
    qty = _fmt_qty(tarea.get("cantidad_picking"))
    lote = str(tarea.get("lote") or "").strip()

    if phase == "start":
        return (
            f"Buenos días. Empezaremos el surtido del picking {nro_picking}. "
            f"Tienes {total} tareas pendientes. Diga iniciar para comenzar."
        )

    if phase == "location":
        zone_text = f"Diríjase a la zona {zona}. " if include_zone else ""
        return (
            f"Tarea {current} de {total}. {zone_text}Ubicación {ubicacion}. "
            "Cuando llegue, diga estoy aquí. Si necesita repetir, diga repítelo."
        )

    if phase == "material":
        lote_text = f" Lote {lote}." if lote else ""
        return (
            f"Código del material {sku}. Descripción: {producto}.{lote_text} "
            "Si es correcto, diga ok, correcto o conforme. "
            "También puede decir repite código."
        )

    if phase == "quantity":
        return (
            f"Extrae {qty} {unidad}. "
            "Cuando lo tenga, diga ok, correcto o conforme. "
            "Si no encuentra todo, diga tengo corto. "
            "También puede decir repite cantidad."
        )

    if phase == "short_qty":
        return "Indica la cantidad encontrada. Puede decir un número, por ejemplo cinco o diez."

    if phase == "short_confirm":
        q = _fmt_qty(short_qty)
        return (
            f"Confirmas el corto por {q} {unidad}. "
            "Diga confirmar corto para registrar el corto o diga otra cantidad."
        )

    if phase == "cancel_confirm":
        return f"Vuelva a decir cancelar para cancelar el picking {nro_picking}. Diga no para continuar."

    if phase == "audit":
        return "Todas las tareas fueron procesadas. Revise el resumen de auditoría y diga confirmar auditoría para finalizar."

    if phase == "farewell":
        return f"Picking {nro_picking} finalizado. Gracias."

    return "Diga repetir para escuchar nuevamente."


def build_task_prompt(tarea: dict, current: int, total: int) -> str:
    """Compatibilidad con versiones previas."""
    return build_voice_prompt_for_phase(tarea, current=current, total=total, phase="location")


def build_audit_prompt(auditoria_rows: list[dict] | None = None) -> str:
    rows = auditoria_rows or []
    if not rows:
        return "Auditoría de picking sin líneas. Diga confirmar auditoría para finalizar."
    intro = ["Todas las tareas fueron atendidas. Resumen de auditoría."]
    for row in rows[:12]:
        sku = row.get("sku") or ""
        nombre = row.get("nombre_producto") or ""
        qty = _fmt_qty(row.get("cantidad_atendida"))
        unidad = row.get("nombre_unidad") or row.get("codigo_unidad") or ""
        intro.append(f"{sku}. {nombre}. Cantidad {qty} {unidad}.")
    if len(rows) > 12:
        intro.append(f"Hay {len(rows) - 12} líneas adicionales en pantalla.")
    intro.append("Diga confirmar auditoría para finalizar o repetir resumen.")
    return " ".join(intro)


def render_voice_assistant(
    instruction: str,
    *,
    key: str,
    auto_play: bool = False,
    auto_listen: bool = False,
    listen_timeout_ms: int = 6500,
    height: int = 118,
    rate: float = 1.25,
    show_controls: bool = True,
    commands_hint: str = "confirmar, repetir, cancelar, corto, ayuda",
    emit_played: bool = False,
) -> dict | None:
    """Renderiza el componente de voz de Chrome.

    `show_controls=False` oculta botones y deja una experiencia conversacional.
    """
    auto_play_nonce = st.session_state.get(f"{key}_auto_play_nonce", 0)
    if auto_play:
        st.session_state.setdefault(f"{key}_already_autoplayed", False)
        if not st.session_state[f"{key}_already_autoplayed"]:
            auto_play_nonce = int(auto_play_nonce) + 1
            st.session_state[f"{key}_auto_play_nonce"] = auto_play_nonce
            st.session_state[f"{key}_already_autoplayed"] = True
    else:
        auto_play_nonce = None

    result = _rf_voice_assistant(
        instruction=instruction,
        lang="es-PE",
        rate=float(rate),
        pitch=1.0,
        volume=1.0,
        auto_play=bool(auto_play_nonce),
        auto_play_nonce=auto_play_nonce,
        auto_listen=auto_listen,
        auto_delay_ms=140,
        listen_timeout_ms=int(listen_timeout_ms),
        listen_delay_ms=260,
        height=int(height),
        task_key=key,
        show_controls=bool(show_controls),
        commands_hint=commands_hint,
        emit_played=bool(emit_played),
        default=None,
        key=f"voice_component_{key}",
    )
    return result if isinstance(result, dict) else None


def reset_voice_autoplay(key: str) -> None:
    st.session_state[f"{key}_already_autoplayed"] = False


def consume_voice_event(event: dict | None, state_key: str, *, include_played: bool = False) -> dict | None:
    """Evita procesar dos veces el mismo evento del componente."""
    if not event:
        return None
    if event.get("event") != "command" and not include_played:
        return None
    event_id = f"{event.get('event','')}|{event.get('task_key','')}|{event.get('command','')}|{event.get('transcript','')}|{event.get('ts','')}"
    if st.session_state.get(state_key) == event_id:
        return None
    st.session_state[state_key] = event_id
    return event


def log_voice_event(
    *,
    id_usuario: int | None = None,
    id_picking: int | None = None,
    id_picking_detalle: int | None = None,
    evento: str,
    texto_emitido: str | None = None,
    texto_reconocido: str | None = None,
    comando_normalizado: str | None = None,
    confianza: float | None = None,
) -> None:
    """Registra auditoría de voz si la migración SQL fue aplicada.

    Si la tabla no existe, la función no rompe la operación RF.
    """
    def _op():
        with get_engine().begin() as conn:
            exists = conn.execute(text("SELECT OBJECT_ID('dbo.voice_event_log', 'U')")).scalar()
            if not exists:
                return
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.voice_event_log
                        (
                            id_usuario,
                            id_picking,
                            id_picking_detalle,
                            evento,
                            texto_emitido,
                            texto_reconocido,
                            comando_normalizado,
                            confianza,
                            fecha_evento
                        )
                    VALUES
                        (
                            :id_usuario,
                            :id_picking,
                            :id_picking_detalle,
                            :evento,
                            :texto_emitido,
                            :texto_reconocido,
                            :comando_normalizado,
                            :confianza,
                            dbo.fn_now_bogota_lima()
                        )
                    """
                ),
                {
                    "id_usuario": id_usuario,
                    "id_picking": id_picking,
                    "id_picking_detalle": id_picking_detalle,
                    "evento": evento,
                    "texto_emitido": texto_emitido,
                    "texto_reconocido": texto_reconocido,
                    "comando_normalizado": comando_normalizado,
                    "confianza": confianza,
                },
            )
    try:
        run_db_with_retry(_op)
    except Exception:
        return


def handle_help_text(phase: str | None = None) -> str:
    if phase == "location":
        return "Puede decir: estoy aquí, repítelo, repite ubicación o cancelar picking."
    if phase == "material":
        return "Puede decir: ok, correcto, conforme, repite código o cancelar picking."
    if phase == "quantity":
        return "Puede decir: ok, correcto, conforme, tengo corto, repite cantidad o cancelar picking."
    if phase == "short_qty":
        return "Indique la cantidad encontrada con un número."
    if phase == "short_confirm":
        return "Puede decir confirmar corto o indicar otra cantidad."
    return "Comandos: iniciar, estoy aquí, ok, repetir, repite ubicación, repite código, repite cantidad, tengo corto o cancelar picking."


def mark_task_voice_confirmation(
    *,
    id_picking_detalle: int,
    transcript: str | None = None,
    confidence: float | None = None,
) -> None:
    """Marca en picking_detalle que la confirmación fue por voz, si columnas existen."""
    def _op():
        with get_engine().begin() as conn:
            if not conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'confirmado_por_voz')")).scalar():
                return
            conn.execute(
                text(
                    """
                    UPDATE dbo.picking_detalle
                    SET metodo_confirmacion = 'VOZ',
                        confirmado_por_voz = 1,
                        texto_confirmacion_voz = :transcript,
                        confianza_voz = :confidence,
                        fecha_confirmacion_voz = dbo.fn_now_bogota_lima()
                    WHERE id_picking_detalle = :id_picking_detalle
                    """
                ),
                {
                    "id_picking_detalle": int(id_picking_detalle),
                    "transcript": transcript,
                    "confidence": confidence,
                },
            )
    try:
        run_db_with_retry(_op)
    except Exception:
        return


def register_voice_short_incident(
    *,
    id_usuario: int,
    id_picking: int,
    id_picking_detalle: int,
    cantidad_reportada: float | None,
    transcript: str | None = None,
    confidence: float | None = None,
) -> None:
    """Registra una incidencia de corto por voz y marca la tarea como CORTO.

    No descuenta stock ni confirma la tarea. El corto queda visible en la vista
    de cortos de la app desktop para revisión/reasignación/cancelación.
    """
    log_voice_event(
        id_usuario=id_usuario,
        id_picking=id_picking,
        id_picking_detalle=id_picking_detalle,
        evento="CORTO_REPORTADO_VOZ",
        texto_emitido=None,
        texto_reconocido=transcript,
        comando_normalizado="CORTO",
        confianza=confidence,
    )

    def _op():
        with get_engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1
                        id_picking,
                        cantidad_asignada,
                        texto_item
                    FROM dbo.picking_detalle WITH (UPDLOCK, ROWLOCK)
                    WHERE id_picking_detalle = :id_picking_detalle
                    """
                ),
                {"id_picking_detalle": int(id_picking_detalle)},
            ).mappings().first()
            if not row:
                return
            cantidad_asignada = float(row.get("cantidad_asignada") or 0)
            texto_actual = str(row.get("texto_item") or "")
            texto_corto = f"CORTO VOZ. Cantidad encontrada: {cantidad_reportada if cantidad_reportada is not None else 'no informada'}. Motivo: no stock físico en ubicación."
            texto_final = (texto_actual + " | " + texto_corto).strip(" |") if texto_actual else texto_corto

            set_cols = [
                "estado = 'CORTO'",
                "cantidad_atendida = 0",
                "fecha_actualizacion = dbo.fn_now_bogota_lima()",
                "texto_item = :texto_item",
            ]
            params = {
                "id_picking_detalle": int(id_picking_detalle),
                "texto_item": texto_final,
                "transcript": transcript,
                "confidence": confidence,
                "cantidad_reportada": cantidad_reportada,
            }
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'metodo_confirmacion')")).scalar():
                set_cols.append("metodo_confirmacion = 'VOZ_CORTO'")
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'texto_confirmacion_voz')")).scalar():
                set_cols.append("texto_confirmacion_voz = :transcript")
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'confianza_voz')")).scalar():
                set_cols.append("confianza_voz = :confidence")
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'cantidad_reportada_voz')")).scalar():
                set_cols.append("cantidad_reportada_voz = :cantidad_reportada")
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'fecha_confirmacion_voz')")).scalar():
                set_cols.append("fecha_confirmacion_voz = dbo.fn_now_bogota_lima()")

            conn.execute(
                text(
                    "UPDATE dbo.picking_detalle SET " + ", ".join(set_cols) + " WHERE id_picking_detalle = :id_picking_detalle"
                ),
                params,
            )
            conn.execute(
                text(
                    """
                    UPDATE dbo.picking_header
                    SET estado = 'LIBERADO-CORTO',
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_picking = :id_picking
                      AND estado IN ('LIBERADO','LIBERADO-CORTO','COMPLETADO-PARCIAL')
                    """
                ),
                {"id_picking": int(id_picking)},
            )
    try:
        run_db_with_retry(_op)
    except Exception:
        return
