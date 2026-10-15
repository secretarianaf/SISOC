"""Fechas y nombres en el formato del contrato con la app."""

from datetime import date, datetime

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from core.services.layout_claro import iniciales  # noqa: F401


def iso(valor):
    """ISO 8601 con la zona de Argentina (``2026-10-14T14:52:03-03:00``)."""
    if valor is None:
        return None
    if timezone.is_naive(valor):
        valor = timezone.make_aware(valor)
    return timezone.localtime(valor).isoformat(timespec="seconds")


def hoy():
    """Jornada de hoy en Argentina (``TIME_ZONE`` del proyecto)."""
    return timezone.localdate()


def fecha_desde_texto(valor):
    """``date`` desde ``AAAA-MM-DD`` o ``None`` si no es una fecha válida."""
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return parse_date(valor.strip())
    except ValueError:
        return None


def fecha_hora_desde_texto(valor):
    """``datetime`` con zona desde ISO 8601, o ``None`` si no es válido."""
    if isinstance(valor, datetime):
        resultado = valor
    elif isinstance(valor, str) and valor.strip():
        try:
            resultado = parse_datetime(valor.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if resultado is None:
        return None
    if timezone.is_naive(resultado):
        resultado = timezone.make_aware(resultado)
    return resultado


def nombre_actor(user):
    if user is None:
        return ""
    return (user.get_full_name() or user.get_username() or "").strip()
