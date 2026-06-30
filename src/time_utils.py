from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


def local_now() -> datetime:
    """Fecha/hora local operativa para Lima/Bogota (UTC-5)."""
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("America/Lima"))
        except Exception:
            pass
    return datetime.now(timezone.utc) - timedelta(hours=5)


def local_today() -> date:
    """Fecha local operativa para filtros por defecto de la app."""
    return local_now().date()
