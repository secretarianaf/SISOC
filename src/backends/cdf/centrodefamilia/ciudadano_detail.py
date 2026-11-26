"""Contribucion de Centro de Familia al detalle Ciudadano 360."""

from typing import Any

from django.db.models import Sum
from django.template.defaultfilters import floatformat

from centrodefamilia.models import ParticipanteActividad
from ciudadanos.detail_contributions import (
    fecha_texto,
    registrar_contribucion_detalle,
    registrar_proyector_aporte,
)


def consultar_contexto(ciudadano: Any) -> dict[str, Any]:
    """Participaciones y monto; propaga excepciones y evalua los querysets."""
    participaciones = list(
        ParticipanteActividad.objects.filter(ciudadano=ciudadano)
        .select_related("actividad_centro__centro", "actividad_centro__actividad")
        .order_by("-fecha_registro")
    )
    costo_total_cdf = (
        ParticipanteActividad.objects.filter(
            ciudadano=ciudadano, estado="inscrito"
        ).aggregate(total=Sum("actividad_centro__precio"))["total"]
        or 0
    )
    return {
        "participaciones_cdf": participaciones,
        "costo_total_cdf": costo_total_cdf,
    }


def obtener_contexto(ciudadano: Any, logger: Any) -> dict[str, Any]:
    try:
        return consultar_contexto(ciudadano)
    except Exception:
        logger.exception(
            "Error cargando participaciones CDF para ciudadano %s", ciudadano.pk
        )
        return {"participaciones_cdf": [], "costo_total_cdf": 0}


def proyectar_aporte(ciudadano: Any) -> dict[str, Any]:
    """Secciones ``centrodefamilia`` y ``centrodefamilia_monto`` en JSON."""
    contexto = consultar_contexto(ciudadano)
    total = contexto["costo_total_cdf"]
    return {
        "centrodefamilia": [
            {
                "centro_nombre": participacion.actividad_centro.centro.nombre,
                "actividad_nombre": participacion.actividad_centro.actividad.nombre,
                "estado": participacion.estado,
                "fecha_registro_texto": fecha_texto(participacion.fecha_registro),
            }
            for participacion in contexto["participaciones_cdf"]
        ],
        "centrodefamilia_monto": {
            "total": str(total),
            # Mismo filtro que ``ciudadano_detalle_monto.html``, con el locale del request.
            "total_texto": f"${floatformat(total, 2)}",
        },
    }


def registrar_contribucion_ciudadano() -> None:
    registrar_contribucion_detalle(
        "centrodefamilia",
        obtener_contexto,
        "centrodefamilia/ciudadano_detalle_seccion.html",
    )
    registrar_contribucion_detalle(
        "centrodefamilia_monto",
        obtener_contexto,
        "centrodefamilia/ciudadano_detalle_monto.html",
    )
    registrar_proyector_aporte("centrodefamilia", proyectar_aporte)
