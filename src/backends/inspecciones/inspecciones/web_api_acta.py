"""Web API (G1 v1) of one acta's backoffice page and its two actions.

``GET /api/web/inspecciones/actas/<numero>/`` runs ``ActaDetalleView`` itself
(same 404, breadcrumb, initials and ``detalle_acta_panel`` context) and
projects it to JSON. Every text is formatted here exactly as
``inspecciones/acta_detalle.html`` prints it, so the React screen does not
format dates, numbers or defaults. Files (PDF, photos, signature,
notification pages) stay native URLs with their own guard.

``POST .../anular/`` and ``POST .../prueba/`` run the native views'
``post()`` (``views_anulacion``): same service, same messages, same ``next``
validation. The native redirect becomes ``{"ok": true, "redirect": ...}``;
the messages are consumed by the next page load, like the native toastr.
Access: ``WebGatePermission`` and then the native ``puede_gestionar``.
"""

from django.contrib import messages
from django.http import Http404
from django.template.defaultfilters import date as formato_fecha
from django.urls import reverse
from django.utils.timezone import template_localtime
from django.views import View
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from inspecciones.views_actas import ActaDetalleView
from inspecciones.views_anulacion import AnularActaView, MarcarPruebaActaView
from inspecciones.web_api import _layout, _WebView

SIN_DATO = "—"
MESSAGE_LEVELS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}


def pending_messages(request):
    """Consume queued Django messages, as the native page does when it renders."""
    return [
        {"message": str(mensaje), "level": MESSAGE_LEVELS.get(mensaje.level, "info")}
        for mensaje in messages.get_messages(request)
    ]


def _fecha(valor, formato):
    """``{{ valor|date:formato }}``: empty for ``None``, local time for aware values."""
    if not valor:
        return ""
    return formato_fecha(template_localtime(valor), formato)


def _o(valor):
    """``|default:"—"``."""
    return valor if valor else SIN_DATO


def _texto(valor):
    """``{{ valor }}`` of a value that may be ``None``."""
    return "" if valor is None else str(valor)


def _acta(acta, context):
    anulada_por = acta.anulada_por
    numero = acta.numero
    return {
        "numero": numero,
        "anulada": acta.estado == "anulada",
        "anulada_at": _fecha(acta.anulada_at, "d/m/Y H:i"),
        "anulada_por": (
            (anulada_por.get_full_name() or anulada_por.username) if anulada_por else ""
        ),
        "motivo_anulacion": acta.motivo_anulacion or "",
        "notificacion_cargada": acta.notificacion_estado == "cargada",
        "prueba": acta.es_prueba,
        "linea": (
            f"{_texto(context['escuela']['nombre']) or 'Escuela sin nombre'} · "
            f"Turno {_texto(context['turno']).lower()} · "
            f"cierre oficial {_fecha(acta.cerrada_at, 'd/m/Y H:i')}"
        ),
        "pdf_url": (
            reverse("inspecciones_acta_pdf", args=[numero]) if acta.pdf else None
        ),
        "anular_url": reverse("inspecciones_web_acta_anular", args=[numero]),
        "prueba_url": reverse("inspecciones_web_acta_prueba", args=[numero]),
    }


def _respuestas(filas):
    return [
        {
            "codigo": fila["codigo"],
            "pregunta": _texto(fila["pregunta"]),
            "respuesta": _texto(fila["respuesta"]),
            "notas": [_texto(nota) for nota in fila["notas"]],
        }
        for fila in filas
    ]


def _evidencia(numero, evidencia):
    filas = []
    for imagen in evidencia:
        descripcion = _texto(imagen["descripcion"])
        titulo = imagen["titulo"]
        filas.append(
            {
                "url": reverse(
                    "inspecciones_acta_imagen", args=[numero, imagen["uuid"]]
                ),
                "titulo": titulo,
                "descripcion": descripcion,
                "alt": f"{titulo}: {descripcion}" if descripcion else titulo,
                "capturada": _fecha(imagen["capturada_at"], "H:i"),
                "subida": _fecha(imagen["subida_at"], "H:i"),
            }
        )
    return filas


def _notificaciones(numero, notificaciones):
    return [
        {
            "version": notificacion["version"],
            "cargada": (
                f"{_fecha(notificacion['cargada_at'], 'd/m/Y H:i')} · por "
                f"{notificacion['cargada_por']}"
            ),
            "notificada": _fecha(notificacion["notificada_at"], "d/m/Y H:i"),
            "receptor": _o(notificacion["receptor"]),
            "condicion_firma": _texto(notificacion["condicion_firma"]),
            "motivo": notificacion["motivo"] or "",
            "observaciones": notificacion["observaciones"] or "",
            "motivo_correccion": notificacion["motivo_correccion"] or "",
            "archivos": [
                {
                    "url": reverse(
                        "inspecciones_acta_notificacion_archivo",
                        args=[numero, archivo["uuid"]],
                    ),
                    "alt": f"Notificación, página {archivo['orden']}",
                }
                for archivo in notificacion["archivos"]
            ],
        }
        for notificacion in notificaciones
    ]


def _inspector(acta, context):
    filas = [
        [
            "Jornada",
            f"{_fecha(acta.fecha_visita, 'd/m/Y')} · turno "
            f"{_texto(context['turno']).lower()}",
        ],
        ["Inicio", _o(_fecha(context["iniciada_at"], "H:i"))],
        ["Cierre oficial", _fecha(acta.cerrada_at, "H:i")],
        ["Formulario", _texto(context["formulario_version"])],
    ]
    if context["motivo_nueva_visita"]:
        filas.append(["Nueva visita", _texto(context["motivo_nueva_visita"])])
    return {
        "nombre": _texto(context["inspector_nombre"]),
        "usuario": _texto(context["inspector_usuario"]),
        "filas": filas,
    }


def _institucion(context):
    escuela = context["escuela"]
    catalogo = context["escuela_catalogo"]
    if catalogo:
        distrito = (
            f" · {catalogo.distrito}"
            if catalogo.distrito and catalogo.distrito != catalogo.localidad
            else ""
        )
        cp = f" · {catalogo.cp}" if catalogo.cp else ""
        return {
            "editar_url": f"{reverse('inspecciones_panel')}?editar={catalogo.pk}",
            "carga_manual": False,
            "filas": [
                ["Cueanexo", _o(escuela["cueanexo"])],
                ["Provincia", _o(escuela["provincia"])],
                ["Localidad", f"{_o(catalogo.localidad)}{distrito}"],
                ["Domicilio", f"{_o(catalogo.domicilio)}{cp}"],
                ["Teléfono", _o(catalogo.telefono)],
                ["Mail", _o(catalogo.mail)],
            ],
        }
    snapshot = context["escuela_snapshot"]
    distrito = snapshot.get("distrito")
    return {
        "editar_url": None,
        "carga_manual": bool(context["carga_manual"]),
        "filas": [
            ["Cueanexo", _o(escuela["cueanexo"])],
            [
                "Localidad",
                f"{_o(snapshot.get('localidad'))}{f' · {distrito}' if distrito else ''}",
            ],
            ["Domicilio", _o(snapshot.get("domicilio"))],
        ],
    }


def _ubicacion(ubicacion):
    filas = []
    lat, lng = _texto(ubicacion["lat"]), _texto(ubicacion["lng"])
    if ubicacion["tiene_coordenadas"]:
        filas.append(["Coordenadas", f"{lat}, {lng}"])
    if ubicacion["precision_m"] is not None:
        filas.append(["Precisión", f"± {ubicacion['precision_m']} m"])
    if ubicacion["capturada_at"]:
        filas.append(["Capturada", _fecha(ubicacion["capturada_at"], "H:i")])
    if ubicacion["motivo_sin_gps"]:
        filas.append(["Sin GPS", _texto(ubicacion["motivo_sin_gps"])])
    mapa = None
    if ubicacion["tiene_coordenadas"]:
        mapa = (
            f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=18/{lat}/{lng}"
        )
    return {
        "fuente": _texto(ubicacion["fuente"]),
        "es_gps": ubicacion["es_gps"],
        "filas": filas,
        "mapa_url": mapa,
    }


def _recepcion(numero, recepcion):
    tipo = recepcion["tipo"]
    firmada = _o(_fecha(recepcion["firmada_at"], "d/m/Y H:i"))
    if recepcion["es_firma"]:
        filas = [
            ["Firmó", f"{recepcion['nombre']} · {recepcion['cargo']}"],
            ["Firmada", firmada],
        ]
        if recepcion["texto_mostrado"]:
            filas.append(["Texto leído", _texto(recepcion["texto_mostrado"])])
        imagen = recepcion["imagen_uuid"]
        return {
            "tipo": "firma",
            "imagen_url": (
                reverse("inspecciones_acta_imagen", args=[numero, imagen])
                if imagen
                else None
            ),
            "imagen_alt": f"Firma de {recepcion['nombre']}",
            "filas": filas,
        }
    if tipo == "excepcion":
        filas = [
            ["Excepción", _texto(recepcion["motivo_tipo"])],
            ["Motivo", _o(recepcion["motivo"])],
        ]
        if recepcion["nombre"] or recepcion["cargo"]:
            cargo = f" · {recepcion['cargo']}" if recepcion["cargo"] else ""
            filas.append(["Quién atendió", f"{recepcion['nombre']}{cargo}"])
        filas.append(["Registrada", firmada])
        return {
            "tipo": "excepcion",
            "imagen_url": None,
            "imagen_alt": "",
            "filas": filas,
        }
    return {"tipo": "", "imagen_url": None, "imagen_alt": "", "filas": []}


def _historial(historial):
    return [
        {
            "hora": _fecha(evento["at"], "d/m H:i"),
            "codigo": _texto(evento["codigo"]),
            "texto": _texto(evento["accion"])
            + (f" · {evento['actor']}" if evento["actor"] else ""),
            "motivo": _texto(evento["motivo"]),
        }
        for evento in historial
    ]


class ActaDetalleWebView(_WebView):
    """``GET /api/web/inspecciones/actas/<numero>/``: the acta page as JSON."""

    http_method_names = ["get", "head"]

    def get(self, request, numero):
        vista = ActaDetalleView()
        vista.setup(request._request, numero=numero)  # pylint: disable=protected-access
        try:
            context = vista.get_context_data()
        except Http404 as exc:
            raise NotFound() from exc
        context["request"] = request
        acta = context["acta"]
        resumen = context["resumen_acta"]
        return Response(
            {
                "layout": _layout(context),
                "acta": _acta(acta, context),
                "resumen": {
                    "abierta": _texto(resumen["abierta"]),
                    "resultado": _texto(resumen["resultado"]),
                    "motivo_parcial": _texto(resumen["motivo_parcial"]),
                    "personal": resumen["personal"],
                    "aulas": resumen["aulas"],
                },
                "formulario_version": _texto(context["formulario_version"]),
                "respuestas": _respuestas(context["respuestas"]),
                "evidencia": _evidencia(acta.numero, context["evidencia"]),
                "notificaciones": _notificaciones(
                    acta.numero, context["notificaciones"]
                ),
                "inspector": _inspector(acta, context),
                "institucion": _institucion(context),
                "ubicacion": _ubicacion(context["ubicacion"]),
                "recepcion": _recepcion(acta.numero, context["recepcion"]),
                "historial": _historial(context["historial"]),
                "messages": pending_messages(request),
            }
        )


class _AccionActaWebView(_WebView):
    """Run the native action's ``post()``; its redirect becomes JSON."""

    http_method_names = ["post"]
    view_class = View  # each action names its native view

    def post(self, request, numero):
        django_request = request._request  # pylint: disable=protected-access
        vista = self.view_class()
        vista.setup(django_request, numero=numero)
        respuesta = vista.post(django_request, numero)
        return Response({"ok": True, "redirect": respuesta["Location"]})


class AnularActaWebView(_AccionActaWebView):
    """``POST /api/web/inspecciones/actas/<numero>/anular/`` (``AnularActaView``)."""

    view_class = AnularActaView


class MarcarPruebaWebView(_AccionActaWebView):
    """``POST /api/web/inspecciones/actas/<numero>/prueba/`` (``MarcarPruebaActaView``)."""

    view_class = MarcarPruebaActaView
