"""Contribucion de Comedores al detalle Ciudadano 360."""

from typing import Any

from django.urls import reverse

from ciudadanos.detail_contributions import (
    fecha_texto,
    registrar_contribucion_detalle,
    registrar_proyector_aporte,
)
from comedores.models import ColaboradorEspacio, Nomina


def consultar_contexto(ciudadano: Any) -> dict[str, Any]:
    """Consulta de nominas y colaboraciones; deja propagar cualquier excepcion."""
    nominas = list(
        Nomina.objects.filter(ciudadano=ciudadano)
        .select_related(
            "admision__comedor__provincia",
            "admision__comedor__municipio",
            "admision__comedor__tipocomedor",
        )
        .order_by("-fecha")
    )
    colaboraciones = list(
        ColaboradorEspacio.objects.filter(ciudadano=ciudadano)
        .select_related(
            "comedor__provincia",
            "comedor__municipio",
            "comedor__tipocomedor",
        )
        .prefetch_related("actividades")
        .order_by("-fecha_alta", "-id")
    )
    contexto = {
        "nominas_comedor": nominas,
        "colaboraciones_comedor": colaboraciones,
    }
    if nominas:
        contexto["nomina_actual"] = nominas[0]
    return contexto


def obtener_contexto(ciudadano: Any, logger: Any) -> dict[str, Any]:
    try:
        return consultar_contexto(ciudadano)
    except Exception:
        logger.exception(
            "Error cargando nominas de comedor para ciudadano %s", ciudadano.pk
        )
        return {"nominas_comedor": [], "colaboraciones_comedor": []}


def _comedor_basico(comedor: Any) -> dict[str, Any] | None:
    """Enlace de comedor como en los templates: sin comedor o sin id, ``-``."""
    if not comedor or not comedor.id:
        return None
    return {
        "id": comedor.id,
        "nombre": comedor.nombre,
        "url": reverse("comedor_detalle", args=[comedor.id]),
    }


def _nombre_o_guion(objeto: Any) -> str:
    return getattr(objeto, "nombre", "") or "-"


def _comedor_actual(comedor: Any) -> dict[str, Any] | None:
    basico = _comedor_basico(comedor)
    if basico is None:
        return None
    return {
        **basico,
        "tipo_texto": _nombre_o_guion(comedor.tipocomedor),
        "provincia_texto": _nombre_o_guion(comedor.provincia),
        "municipio_texto": _nombre_o_guion(comedor.municipio),
    }


def _comedor_de_nomina(nomina: Any) -> Any:
    return getattr(getattr(nomina, "admision", None), "comedor", None)


def proyectar_aporte(ciudadano: Any) -> dict[str, Any]:
    """Secciones ``comedores`` y ``comedores_colaboraciones`` en JSON."""
    contexto = consultar_contexto(ciudadano)
    actual = contexto.get("nomina_actual")
    return {
        "comedores": {
            "nomina_actual": (
                {
                    "estado": actual.estado,
                    "comedor": _comedor_actual(_comedor_de_nomina(actual)),
                    "fecha_texto": fecha_texto(actual.fecha),
                }
                if actual
                else None
            ),
            "historial": [
                {
                    "estado": nomina.estado,
                    "comedor": _comedor_basico(_comedor_de_nomina(nomina)),
                    "fecha_texto": fecha_texto(nomina.fecha),
                }
                for nomina in contexto["nominas_comedor"]
            ],
        },
        "comedores_colaboraciones": [
            {
                "comedor": _comedor_basico(colaboracion.comedor),
                "fecha_alta_texto": fecha_texto(
                    colaboracion.fecha_alta, por_defecto="-"
                ),
                "fecha_baja_texto": fecha_texto(
                    colaboracion.fecha_baja, por_defecto="-"
                ),
                "actividades": [
                    actividad.nombre for actividad in colaboracion.actividades.all()
                ],
            }
            for colaboracion in contexto["colaboraciones_comedor"]
        ],
    }


def registrar_contribucion_ciudadano() -> None:
    registrar_contribucion_detalle(
        "comedores", obtener_contexto, "comedor/ciudadano_seccion.html"
    )
    registrar_contribucion_detalle(
        "comedores_colaboraciones",
        obtener_contexto,
        "comedor/ciudadano_colaboraciones.html",
    )
    registrar_proyector_aporte("comedores", proyectar_aporte)
