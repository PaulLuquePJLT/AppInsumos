from __future__ import annotations

import re
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
    "ESTOY_AQUI": "Estoy en ubicación",
    "OK": "Confirmación",
    "REPETIR": "Repetir instrucción",
    "REPETIR_UBICACION": "Repetir ubicación",
    "REPETIR_CODIGO": "Repetir código",
    "REPETIR_CANTIDAD": "Repetir cantidad",
    "CANCELAR_PICKING": "Cancelar picking",
    "TENGO_CORTO": "Reportar corto",
    "CANTIDAD": "Cantidad informada",
    "CONFIRMAR_CORTO": "Confirmar corto",
    "CONFIRMAR_AUDITORIA": "Confirmar auditoría",
    "PRESENCIA": "Operario presente",
    "AYUDA": "Ayuda",
    "NO_INPUT": "Sin respuesta",
    "NO_RECONOCIDO": "No reconocido",
}

_DIGIT_WORDS = {
    "0": "cero",
    "1": "uno",
    "2": "dos",
    "3": "tres",
    "4": "cuatro",
    "5": "cinco",
    "6": "seis",
    "7": "siete",
    "8": "ocho",
    "9": "nueve",
}

_LETTER_WORDS = {
    "A": "a", "B": "be", "C": "ce", "D": "de", "E": "e", "F": "efe",
    "G": "ge", "H": "hache", "I": "i", "J": "jota", "K": "ka", "L": "ele",
    "M": "eme", "N": "ene", "Ñ": "eñe", "O": "o", "P": "pe", "Q": "cu",
    "R": "erre", "S": "ese", "T": "te", "U": "u", "V": "ve", "W": "doble ve",
    "X": "equis", "Y": "ye", "Z": "zeta",
}

_UNIT_NAMES = {
    "UND": "unidades",
    "UN": "unidades",
    "UNI": "unidades",
    "CJ": "cajas",
    "CAJ": "cajas",
    "CAJA": "cajas",
    "RLL": "rollos",
    "ROLLO": "rollos",
    "PAQ": "paquetes",
    "PQT": "paquetes",
    "MILLAR": "millares",
    "MILLARES": "millares",
    "MLL": "millares",
    "KG": "kilogramos",
    "M": "metros",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _digits_to_words(text: str) -> str:
    return " ".join(_DIGIT_WORDS.get(ch, ch) for ch in str(text) if ch.strip())


def speak_sku(value: Any) -> str:
    """Vocaliza SKU/código material.

    Si es numérico, lo dice dígito por dígito. Si contiene letras, deletrea
    letras y dígitos para evitar confusiones operativas.
    """
    text = _clean_text(value).upper()
    if not text:
        return "código no informado"
    if text.isdigit():
        return _digits_to_words(text)
    parts: list[str] = []
    for ch in text:
        if ch.isdigit():
            parts.append(_DIGIT_WORDS.get(ch, ch))
        elif ch.isalpha() or ch == "Ñ":
            parts.append(_LETTER_WORDS.get(ch, ch))
        elif ch in {".", "-", "_", "/"}:
            parts.append("pausa")
    return ", ".join(p for p in parts if p.strip())

def speak_location(value: Any) -> str:
    """Vocaliza ubicaciones como B1.ARM.03.02 sin que Chrome las lea como horas."""
    text = _clean_text(value).upper()
    if not text:
        return "ubicación no informada"
    segments = re.split(r"[.\-_/\s]+", text)
    spoken_segments: list[str] = []
    for seg in segments:
        if not seg:
            continue
        chars: list[str] = []
        for ch in seg:
            if ch.isdigit():
                chars.append(_DIGIT_WORDS.get(ch, ch))
            elif ch.isalpha() or ch == "Ñ":
                chars.append(_LETTER_WORDS.get(ch, ch))
        if chars:
            spoken_segments.append(", ".join(chars))
    return ". ".join(spoken_segments) if spoken_segments else text

def speak_description(value: Any) -> str:
    """Vocaliza descripciones como frase, no como siglas.

    Convertir a minúsculas ayuda a que Chrome lea palabras como bolig, trilux,
    caste, etc. como palabras y no como B-O-L-I-G.
    """
    text = _clean_text(value)
    if not text:
        return "artículo no informado"
    text = re.sub(r"[_|/\\]+", " ", text)
    text = re.sub(r"[:;]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()

def speak_qty(value: Any) -> str:
    try:
        qty = float(value or 0)
        if qty.is_integer():
            return str(int(qty))
        return (f"{qty:.2f}").rstrip("0").rstrip(".")
    except Exception:
        return str(value or "0")


def speak_unit(code: Any, name: Any | None = None) -> str:
    name_text = _clean_text(name)
    if name_text:
        return name_text.lower()
    code_text = _clean_text(code).upper()
    return _UNIT_NAMES.get(code_text, code_text.lower() or "unidades")


def zone_label(tarea: dict) -> str:
    code = _clean_text(tarea.get("codigo_zona"))
    name = _clean_text(tarea.get("nombre_zona"))
    if name and code:
        return f"{code} {name}".strip()
    return name or code or "zona no informada"


def build_voice_instruction(
    tarea: dict,
    current: int,
    total: int,
    *,
    step: str,
    include_zone: bool,
    greeting: bool = False,
    resume: bool = False,
    cancel_confirm: bool = False,
    short_pending: bool = False,
    short_qty: float | None = None,
) -> str:
    """Construye instrucciones conversacionales por paso.

    Pasos soportados:
    - ubicacion: el operario debe responder "estoy aquí".
    - material: el operario confirma el código/material con ok/correcto/conforme.
    - cantidad: el operario confirma cantidad o reporta corto.
    """
    nro_picking = _clean_text(tarea.get("nro_picking")) or _clean_text(tarea.get("id_picking"))
    ubicacion = speak_location(tarea.get("codigo_ubicacion"))
    sku = speak_sku(tarea.get("sku"))
    producto = speak_description(tarea.get("nombre_producto"))
    unidad = speak_unit(tarea.get("codigo_unidad"), tarea.get("nombre_unidad"))
    qty = speak_qty(tarea.get("cantidad_picking"))
    zone = zone_label(tarea)

    if cancel_confirm:
        return f"Vuelva a decir cancelar para cancelar el picking {nro_picking}. Si desea continuar, diga no o continuar."

    if short_pending:
        if short_qty is None:
            return "Indica la cantidad encontrada. Puedes decir un número, o cancelar picking."
        return f"Confirmas el corto por {speak_qty(short_qty)} {unidad}. Diga confirmar corto, o indique la cantidad correcta."

    intro: list[str] = []
    if greeting:
        intro.append(f"Buenos días. Empezaremos el surtido del picking {nro_picking}.")
    if resume:
        intro.append(f"Seguimos con la tarea {current} de {total}.")

    if step == "ubicacion":
        intro.append(f"Tarea {current} de {total}.")
        if include_zone:
            intro.append(f"Diríjase a la zona {speak_description(zone)}.")
        intro.append(f"Ubicación {ubicacion}.")
        intro.append("Cuando llegue diga estoy aquí. Si necesita repetir diga repítelo.")
        return " ".join(intro)

    if step == "material":
        intro.append(f"Código {sku}.")
        intro.append(f"Descripción {producto}.")
        intro.append("Diga ok, correcto o conforme para continuar. También puede decir repite código.")
        return " ".join(intro)

    if step == "cantidad":
        intro.append(f"Extrae {qty} {unidad}.")
        intro.append("Diga ok, correcto o conforme para confirmar. Si no encuentra toda la mercadería, diga tengo corto.")
        return " ".join(intro)

    return f"Tarea {current} de {total}. Ubicación {ubicacion}. Código {sku}. Extrae {qty} {unidad}."


def build_task_prompt(tarea: dict, current: int, total: int) -> str:
    """Compatibilidad con versiones anteriores."""
    return build_voice_instruction(
        tarea,
        current,
        total,
        step="ubicacion",
        include_zone=True,
        greeting=False,
    )


def build_audit_prompt(auditoria_rows: list[dict] | None = None) -> str:
    rows = auditoria_rows or []
    if not rows:
        return "Auditoría de picking sin líneas. Diga confirmar auditoría para finalizar."
    intro = ["Todas las tareas fueron atendidas. Resumen de auditoría."]
    for row in rows[:12]:
        sku = speak_sku(row.get("sku") or "")
        nombre = speak_description(row.get("nombre_producto") or "")
        qty = speak_qty(row.get("cantidad_atendida") or 0)
        unidad = speak_unit(row.get("codigo_unidad"), row.get("nombre_unidad"))
        intro.append(f"Código {sku}. {nombre}. Cantidad {qty} {unidad}.")
    if len(rows) > 12:
        intro.append(f"Hay {len(rows) - 12} líneas adicionales en pantalla.")
    intro.append("Diga confirmar auditoría para finalizar o repetir resumen.")
    return " ".join(intro)


def render_voice_assistant(
    instruction: str,
    *,
    key: str,
    auto_play: bool = False,
    auto_listen: bool = True,
    listen_timeout_ms: int = 7000,
    height: int = 92,
    keepalive: bool = True,
    keepalive_ms: int = 30000,
    presence_mode: bool = False,
) -> dict | None:
    """Renderiza el asistente de voz conversacional.

    Usa Chrome Web Speech API: speechSynthesis para salida de voz y
    webkitSpeechRecognition/SpeechRecognition para comandos. No usa Azure AI Speech
    ni Google Cloud Speech-to-Text API.
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
        rate=1.28,
        pitch=1.0,
        volume=1.0,
        auto_play=bool(auto_play_nonce),
        auto_play_nonce=auto_play_nonce,
        auto_listen=auto_listen,
        auto_delay_ms=160,
        listen_timeout_ms=int(listen_timeout_ms),
        listen_delay_ms=260,
        keepalive=bool(keepalive),
        keepalive_ms=int(keepalive_ms),
        keepalive_prompt="¿Estás ahí?",
        presence_mode=bool(presence_mode),
        height=int(height),
        show_controls=False,
        task_key=key,
        default=None,
        key=f"voice_component_{key}",
    )
    return result if isinstance(result, dict) else None


def reset_voice_autoplay(key: str) -> None:
    st.session_state[f"{key}_already_autoplayed"] = False


def consume_voice_event(event: dict | None, state_key: str) -> dict | None:
    """Evita procesar dos veces el mismo evento del componente."""
    if not event:
        return None
    if event.get("event") not in {"command", "no_input"}:
        return None
    event_id = f"{event.get('task_key','')}|{event.get('event','')}|{event.get('command','')}|{event.get('transcript','')}|{event.get('ts','')}"
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
    """Registra auditoría de voz si la migración SQL fue aplicada."""
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


def handle_help_text(step: str | None = None) -> str:
    step = str(step or "").lower()
    if step == "ubicacion":
        return "Puedes decir: estoy aquí, repítelo, repite ubicación o cancelar picking."
    if step == "material":
        return "Puedes decir: ok, correcto, conforme, repite código o cancelar picking."
    if step == "cantidad":
        return "Puedes decir: ok, correcto, conforme, repite cantidad, tengo corto o cancelar picking."
    return "Puedes decir: estoy aquí, ok, correcto, conforme, repítelo, tengo corto o cancelar picking."


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
    """Registra incidencia de corto por voz y mueve la tarea a estado CORTO."""
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
            has_qty_col = conn.execute(text("SELECT COL_LENGTH('dbo.picking_detalle', 'cantidad_reportada_voz')")).scalar()
            if has_qty_col:
                conn.execute(
                    text(
                        """
                        UPDATE dbo.picking_detalle
                        SET estado = 'CORTO',
                            metodo_confirmacion = 'VOZ_CORTO',
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
            else:
                conn.execute(
                    text(
                        """
                        UPDATE dbo.picking_detalle
                        SET estado = 'CORTO'
                        WHERE id_picking_detalle = :id_picking_detalle
                        """
                    ),
                    {"id_picking_detalle": int(id_picking_detalle)},
                )
    try:
        run_db_with_retry(_op)
    except Exception:
        return
