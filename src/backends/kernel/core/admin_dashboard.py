"""Dashboard del admin con métricas por dominio (issue #2789, Fase 3).

Cada app aporta sus métricas con un módulo ``<app>/admin_metricas.py`` que
define ``metricas() -> list[Seccion]``. El dashboard descubre esos módulos entre
las apps instaladas del proceso, así que:

- en ``/admin/`` del core se ven kernel y núcleo (y todo junto en
  ``settings_all``, que usan local y los tests);
- cada vertical muestra las suyas en su índice (``/admin/<app>/``), que sirve
  su propio runtime.

Las consultas son agregadas (``COUNT``/``GROUP BY``) y se cachean por app
durante ``DASHBOARD_CACHE_TIMEOUT``. Una sección que falla se informa y no
rompe el resto del panel.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

logger = logging.getLogger("django")

MODULO_METRICAS = "admin_metricas"
PREFIJO_CACHE = "admin_dashboard:v1:"
# Paleta institucional (skill tema-verde-institucional).
COLORES = ["#04756F", "#FFC000", "#379F9B", "#78716C", "#045049", "#E86A00"]
MESES_HISTORIA = 12


@dataclass
class Kpi:
    """Número destacado. ``alerta`` lo marca como algo a revisar."""

    titulo: str
    valor: int
    detalle: str = ""
    alerta: bool = False


@dataclass
class Grafico:
    """Gráfico de Chart.js (``bar`` o ``line``) listo para Unfold."""

    titulo: str
    etiquetas: list
    series: list  # [(nombre, [valores])]
    tipo: str = "bar"

    @property
    def datos_json(self) -> str:
        return json.dumps(
            {
                "labels": [str(etiqueta) for etiqueta in self.etiquetas],
                "datasets": [
                    {
                        "label": nombre,
                        "data": valores,
                        "backgroundColor": COLORES[indice % len(COLORES)],
                        "borderColor": COLORES[indice % len(COLORES)],
                    }
                    for indice, (nombre, valores) in enumerate(self.series)
                ],
            }
        )


@dataclass
class Seccion:
    """Bloque del dashboard para un dominio o app."""

    titulo: str
    kpis: list = field(default_factory=list)
    graficos: list = field(default_factory=list)
    error: bool = False


def contar_por(queryset, campo: str, titulo: str, etiquetas: dict | None = None):
    """Gráfico de barras con la cantidad de registros por valor de ``campo``.

    Si no se pasan ``etiquetas`` y ``campo`` es un campo propio con ``choices``,
    se muestran los textos de esos choices.
    """
    if etiquetas is None and "__" not in campo:
        choices = queryset.model._meta.get_field(campo).choices or ()
        etiquetas = {valor: str(texto) for valor, texto in choices}
    etiquetas = etiquetas or {}
    filas = (
        queryset.order_by()
        .values(campo)
        .annotate(cantidad=Count("pk"))
        .order_by("-cantidad")[:20]
    )
    return Grafico(
        titulo=titulo,
        etiquetas=[
            etiquetas.get(
                fila[campo], fila[campo] if fila[campo] is not None else "Sin dato"
            )
            for fila in filas
        ],
        series=[("Registros", [fila["cantidad"] for fila in filas])],
    )


def altas_por_mes(queryset, campo_fecha: str, titulo: str, meses=MESES_HISTORIA):
    """Gráfico de línea con las altas de los últimos ``meses`` meses.

    El alias de la anotación evita chocar con campos del modelo (p. ej. ``mes``).
    """
    desde = (timezone.now() - timedelta(days=31 * meses)).replace(day=1)
    filas = [
        fila
        for fila in queryset.order_by()
        .filter(**{f"{campo_fecha}__gte": desde})
        .annotate(mes_dashboard=TruncMonth(campo_fecha))
        .values("mes_dashboard")
        .annotate(cantidad=Count("pk"))
        .order_by("mes_dashboard")
        if fila["mes_dashboard"]
    ]
    return Grafico(
        titulo=titulo,
        etiquetas=[fila["mes_dashboard"].strftime("%m/%Y") for fila in filas],
        series=[("Altas", [fila["cantidad"] for fila in filas])],
        tipo="line",
    )


def _calcular_secciones(app_config) -> list[dict]:
    try:
        modulo = import_module(f"{app_config.name}.{MODULO_METRICAS}")
    except ModuleNotFoundError as exc:
        if exc.name != f"{app_config.name}.{MODULO_METRICAS}":
            raise
        return []
    try:
        secciones = modulo.metricas()
    except Exception:  # pylint: disable=broad-exception-caught
        # Una métrica rota no puede tirar el admin: queda en el log.
        logger.exception("Métricas del admin fallaron para %s", app_config.label)
        secciones = [
            Seccion(titulo=app_config.verbose_name, error=True),
        ]
    return [
        {
            **asdict(seccion),
            "graficos": [
                {**asdict(grafico), "datos_json": grafico.datos_json}
                for grafico in seccion.graficos
            ],
        }
        for seccion in secciones
    ]


def secciones_de_app(app_label: str) -> list[dict]:
    """Secciones cacheadas de una app instalada (vacío si no aporta métricas)."""
    app_config = apps.get_app_config(app_label)
    return cache.get_or_set(
        f"{PREFIJO_CACHE}{app_label}",
        lambda: _calcular_secciones(app_config),
        getattr(settings, "DASHBOARD_CACHE_TIMEOUT", 300),
    )


def dashboard_callback(_request, context):
    """``UNFOLD["DASHBOARD_CALLBACK"]``: métricas de todas las apps del proceso."""
    context["sisoc_secciones"] = [
        seccion
        for app_config in apps.get_app_configs()
        for seccion in secciones_de_app(app_config.label)
    ]
    return context
