"""Registro de nombres de URL entre servicios.

El core y cada backend (src/backends/config/backends.json) corren con su propio URLconf,
pero sus templates y vistas hacen ``reverse()`` de nombres del otro: el menú
del core enlaza ``dispositivos_listar`` y el layout de un backend enlaza
``inicio``. ``src/backends/config/url_registry.json`` guarda, para la composición completa
(``config.settings_all``), el patrón de cada nombre. Cada servicio agrega con
``stub_urlpatterns`` los nombres que no define: sirven para ``reverse()`` y,
si alguien los pidiera directo a ese proceso, responden 404. El tráfico real
llega al dueño por el proxy del core (``core.backend_proxy``).

Regenerar: ``python manage.py generar_registro_urls`` (con settings_all). Un
test de CI verifica que esté al día.
"""

import json
from pathlib import Path

from django.http import Http404
from django.urls import URLPattern, URLResolver, include, re_path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "url_registry.json"

# Solo de desarrollo: no existen en los procesos de deploy.
NAMESPACES_EXCLUIDOS = {"djdt", "silk"}


def _regex(pattern):
    return pattern.regex.pattern.lstrip("^")


def recolectar(patterns, prefijo="", namespace=()):
    """``[{"name", "namespace", "regex"}]`` de todos los nombres del URLconf."""
    entradas = []
    for entry in patterns:
        if isinstance(entry, URLResolver):
            ns = namespace + ((entry.namespace,) if entry.namespace else ())
            if set(ns) & NAMESPACES_EXCLUIDOS:
                continue
            entradas += recolectar(
                entry.url_patterns, prefijo + _regex(entry.pattern), ns
            )
        elif isinstance(entry, URLPattern) and entry.name:
            entradas.append(
                {
                    "name": entry.name,
                    "namespace": ":".join(namespace),
                    "regex": "^" + prefijo + _regex(entry.pattern),
                }
            )
    vistos, unicas = set(), []
    for entrada in entradas:
        clave = (entrada["namespace"], entrada["name"])
        if clave not in vistos:
            vistos.add(clave)
            unicas.append(entrada)
    return unicas


def generar(urlconf_patterns):
    return sorted(
        recolectar(urlconf_patterns), key=lambda e: (e["namespace"], e["name"])
    )


def cargar(path=REGISTRY_PATH):
    # Sin archivo (primer generación) no hay stubs: el comando lo crea.
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as registro:
        return json.load(registro)


def _no_servida_aca(request, *args, **kwargs):
    raise Http404("Esta URL la atiende otro servicio.")


def stub_urlpatterns(locales, path=REGISTRY_PATH):
    """Patrones solo-``reverse()`` para los nombres que ``locales`` no define."""
    locales_recolectados = recolectar(locales)
    definidos = {(e["namespace"], e["name"]) for e in locales_recolectados}
    # Un namespace que ya existe acá no se duplica (urls.W005): sus nombres
    # ajenos, como el admin de modelos de otro backend, no se enlazan.
    namespaces_locales = {e["namespace"] for e in locales_recolectados}
    faltantes = [
        e
        for e in cargar(path)
        if (e["namespace"], e["name"]) not in definidos
        and (not e["namespace"] or e["namespace"] not in namespaces_locales)
    ]
    raiz, por_namespace = [], {}
    for entrada in faltantes:
        patron = re_path(entrada["regex"], _no_servida_aca, name=entrada["name"])
        if entrada["namespace"]:
            por_namespace.setdefault(entrada["namespace"], []).append(patron)
        else:
            raiz.append(patron)
    for namespace, patrones in por_namespace.items():
        # Namespaces anidados ("a:b") no se usan hoy en SISOC.
        raiz.append(re_path(r"^", include((patrones, namespace), namespace=namespace)))
    return raiz
