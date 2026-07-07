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
    "CONFIRMAR": "Confirmar tarea",
    "REPETIR": "Repetir instrucción",
    "CANCELAR": "Cancelar proceso",
    "CORTO": "Reportar corto",
    "CANTIDAD": "Cantidad informada",
    "CONFIRMAR_CORTO": "Confirmar corto",
    "CONFIRMAR_AUDITORIA": "Confirmar auditoría",
    "AYUDA": "Ayuda",
    "NO_RECONOCIDO": "No reconocido",
}


def build_task_prompt(tarea: dict, current: int, total: int) -> str:
    """Construye el texto que el navegador debe leer para una tarea de picking."""
    ubicacion = tarea.get("codigo_ubicacion") or "ubicación no informada"
    sku = tarea.get("sku") or ""
    producto = tarea.get("nombre_producto") or "artículo no informado"
    unidad = tarea.get("codigo_unidad") or ""
    lote = tarea.get("lote") or ""
    qty = float(tarea.get("cantidad_picking") or 0)

    parts = [
        f"Tarea {current} de {total}.",
        f"Ubicación {ubicacion}.",
        f"Artículo {sku}. {producto}.",
        f"Cantidad {qty:g} {unidad}.",
    ]
    if lote:
        parts.append(f"Lote {lote}.")
    parts.append("Diga confirmar, repetir, corto o cancelar.")
    return " ".join(parts)


def build_audit_prompt(auditoria_rows: list[dict] | None = None) -> str:
    rows = auditoria_rows or []
    if not rows:
        return "Auditoría de picking sin líneas. Diga confirmar auditoría para finalizar."
    intro = ["Todas las tareas fueron atendidas. Resumen de auditoría."]
    for row in rows[:12]:
        sku = row.get("sku") or ""
        nombre = row.get("nombre_producto") or ""
        qty = float(row.get("cantidad_atendida") or 0)
        unidad = row.get("codigo_unidad") or ""
        intro.append(f"{sku}. {nombre}. Cantidad {qty:g} {unidad}.")
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
) -> dict | None:
    """Renderiza controles de voz y retorna el último evento del navegador.

    Usa Web Speech API de Chrome: speechSynthesis para salida de voz y
    webkitSpeechRecognition/SpeechRecognition para comandos simples.
    """
    auto_play_nonce = st.session_state.get(f"{key}_auto_play_nonce", 0)
    if auto_play:
        # Reproduce una vez por tarea o cuando el llamador incremente el nonce.
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
        rate=1.02,
        pitch=1.0,
        volume=1.0,
        auto_play=bool(auto_play_nonce),
        auto_play_nonce=auto_play_nonce,
        auto_listen=auto_listen,
        auto_delay_ms=220,
        listen_timeout_ms=int(listen_timeout_ms),
        listen_delay_ms=380,
        height=int(height),
        task_key=key,
        default=None,
        key=f"voice_component_{key}",
    )
    return result if isinstance(result, dict) else None


def reset_voice_autoplay(key: str) -> None:
    st.session_state[f"{key}_already_autoplayed"] = False


def consume_voice_event(event: dict | None, state_key: str) -> dict | None:
    """Evita procesar dos veces el mismo evento del componente."""
    if not event or event.get("event") != "command":
        return None
    event_id = f"{event.get('task_key','')}|{event.get('command','')}|{event.get('transcript','')}|{event.get('ts','')}"
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
            exists = conn.execute(
                text("SELECT OBJECT_ID('dbo.voice_event_log', 'U')")
            ).scalar()
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
        # La voz no debe bloquear la operación RF.
        return


def handle_help_text() -> str:
    return (
        "Comandos disponibles: confirmar, repetir, cancelar, corto, "
        "confirmar auditoría. Para cantidad, diga un número."
    )


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
    """Registra una incidencia de corto por voz sin confirmar la tarea.

    La tarea queda LIBERADO/PENDIENTE para manejo posterior. Esto evita descontar
    stock incorrectamente cuando el operario reporta diferencia.
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
            if conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'cantidad_reportada_voz')")).scalar():
                conn.execute(
                    text(
                        """
                        UPDATE dbo.picking_detalle
                        SET metodo_confirmacion = 'VOZ_CORTO',
                            texto_confirmacion_voz = :transcript,
                            confianza_voz = :confidence,
                            cantidad_reportada_voz = :cantidad_reportada,
                            fecha_confirmacion_voz = dbo.fn_now_bogota_lima()
                        WHERE id_picking_detalle = :id_picking_detalle
                        """
                    ),
                    {
                        "id_picking_detalle": int(id_picking_detalle),
                        "transcript": transcript,
                        "confidence": confidence,
                        "cantidad_reportada": cantidad_reportada,
                    },
                )
    try:
        run_db_with_retry(_op)
    except Exception:
        return
