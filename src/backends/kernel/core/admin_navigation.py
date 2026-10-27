"""Sidebar y badge de entorno del admin con Unfold (issue #2789).

Cada proceso (core o backend por vertical) registra solo los modelos de sus
apps, así que el menú se arma por request desde lo que está registrado en el
sitio, agrupado por dominio. Los admins que corren en otro backend se listan en
"Otros servicios" con los ``admin_links`` de ``config/backends.json``.
"""

from functools import lru_cache
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.utils.html import escape

from config.backends import load_backends_registry
from core.admin_site import puede_usar_admin

# Backend de config/backends.json -> (título, ícono Material Symbols).
DOMINIOS_BACKEND = {
    "comedores": ("Comedores", "restaurant"),
    "cdi": ("CDI", "child_care"),
    "cdf": ("CDF", "family_restroom"),
    "celiaquia": ("Celiaquía", "no_food"),
    "pas": ("PAS", "elderly"),
    "vat": ("VAT", "school"),
    "vpsl": ("VPSL", "visibility"),
    "dispositivos": ("Dispositivos", "devices"),
    "inspecciones": ("Inspecciones", "fact_check"),
    "ocr": ("OCR", "document_scanner"),
}
NUCLEO = ("Núcleo SISOC", "dashboard")
KERNEL = ("Kernel y usuarios", "admin_panel_settings")
AUDITORIA = ("Auditoría", "history")
OTROS = ("Otros", "folder")
OTROS_SERVICIOS = ("Otros servicios", "open_in_new")

APPS_AUDITORIA = {"auditlog", "audittrail"}
APPS_NUCLEO = {"usuarios", "dashboard", "insumos", "encuestas"}

ORDEN_DOMINIOS = [
    *DOMINIOS_BACKEND.values(),
    NUCLEO,
    KERNEL,
    AUDITORIA,
    OTROS,
]

# ENVIRONMENT de settings -> (texto del badge, variante de color de Unfold).
BADGES_ENTORNO = {
    "dev": ("Desarrollo", "info"),
    "qa": ("QA", "success"),
    "homologacion": ("Homologación", "warning"),
    "prd": ("Producción", "danger"),
}


@lru_cache(maxsize=1)
def _dominio_por_modulo() -> dict[str, tuple[str, str]]:
    """Módulo de app (``AppConfig.name``) -> dominio, según backends.json."""
    return {
        app: DOMINIOS_BACKEND[backend]
        for backend, spec in load_backends_registry().items()
        if backend in DOMINIOS_BACKEND
        for app in spec["apps"]
    }


def _directorio_kernel() -> Path:
    return Path(apps.get_app_config("core").path).parent


def dominio_de_app(app_label: str) -> tuple[str, str]:
    """Dominio del sidebar para una app instalada."""
    if app_label in APPS_AUDITORIA:
        return AUDITORIA
    if app_label in APPS_NUCLEO:
        return NUCLEO
    try:
        app_config = apps.get_app_config(app_label)
    except LookupError:
        return OTROS
    if app_config.name in _dominio_por_modulo():
        return _dominio_por_modulo()[app_config.name]
    # Ubicación resuelta por la app (verticales_independientes.md), no por
    # BASE_DIR + nombre: las apps del kernel viven junto a ``core``.
    es_kernel = app_config.name.startswith(("django.", "rest_framework")) or (
        Path(app_config.path).parent == _directorio_kernel()
    )
    return KERNEL if es_kernel else OTROS


def enlaces_admin_de_backends(user) -> list[dict]:
    """Admins que sirve otro backend (solo existen en el proceso del core)."""
    if not puede_usar_admin(user):
        return []
    return [
        link
        for spec in getattr(settings, "SISOC_BACKENDS", {}).values()
        for link in spec.get("admin_links", ())
    ]


def navegacion_sidebar(request) -> list[dict]:
    """``UNFOLD["SIDEBAR"]["navigation"]``: modelos registrados por dominio."""
    grupos = {dominio: [] for dominio in ORDEN_DOMINIOS}
    for app in admin.site.get_app_list(request):
        dominio = dominio_de_app(app["app_label"])
        for modelo in app["models"]:
            if not modelo.get("admin_url"):
                continue
            grupos[dominio].append(
                {
                    # Unfold renderiza el título con |safe.
                    "title": escape(modelo["name"]),
                    "icon": dominio[1],
                    "link": modelo["admin_url"],
                }
            )
    navegacion = [
        {"title": titulo, "collapsible": True, "items": items}
        for (titulo, _icono), items in grupos.items()
        if items
    ]
    externos = enlaces_admin_de_backends(request.user)
    if externos:
        navegacion.append(
            {
                "title": OTROS_SERVICIOS[0],
                "collapsible": True,
                "items": [
                    {
                        "title": escape(link["label"]),
                        "icon": OTROS_SERVICIOS[1],
                        "link": link["url"],
                    }
                    for link in externos
                ],
            }
        )
    return navegacion


def badge_entorno(_request) -> list[str]:
    """``UNFOLD["ENVIRONMENT"]``: badge con el entorno del deploy."""
    texto, variante = BADGES_ENTORNO.get(
        settings.ENVIRONMENT, (settings.ENVIRONMENT.upper(), "info")
    )
    return [texto, variante]


def prefijo_titulo_entorno(request) -> str | None:
    """Prefijo del <title> para no confundir pestañas de QA/HML con PRD."""
    if settings.ENVIRONMENT == "prd":
        return None
    return f"[{badge_entorno(request)[0]}]"
