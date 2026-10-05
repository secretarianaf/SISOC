"""Redirecciones desde URLs viejas, SOLO por compatibilidad.

Cuando un vertical pasa a tener un prefijo propio (por ejemplo Centro de
Familia, de ``/centros/`` a ``/centrodefamilia/centros/``), sus URLs viejas
siguen andando para favoritos, links ya enviados por mail y bookmarks. El
código nuevo NO debe generarlas: usar ``{% url %}``/``reverse()``, que ya
devuelven la URL nueva.

GET/HEAD responden 301; el resto 308, que conserva el método y el body.
"""

import re

from django.http import HttpResponsePermanentRedirect
from django.urls import re_path


class _Redireccion308(HttpResponsePermanentRedirect):
    status_code = 308


def _vista(prefijo_nuevo):
    def redirigir(request, resto):
        destino = "/" + prefijo_nuevo + resto
        if request.META.get("QUERY_STRING"):
            destino += "?" + request.META["QUERY_STRING"]
        if request.method in ("GET", "HEAD"):
            return HttpResponsePermanentRedirect(destino)
        return _Redireccion308(destino)

    return redirigir


def redirecciones_legacy(prefijo_nuevo, prefijos_viejos):
    """``re_path`` que mandan cada prefijo viejo a ``prefijo_nuevo`` + resto."""
    vista = _vista(prefijo_nuevo)
    return [
        re_path(rf"^(?P<resto>{re.escape(viejo)}.*)$", vista)
        for viejo in prefijos_viejos
    ]
