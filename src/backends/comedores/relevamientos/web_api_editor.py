"""G1 web adapter for the canonical RelevamientoCreateView/UpdateView."""

from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.response import Response

from comedores.models import Comedor
from core.web_gate import WebGatePermission
from relevamientos.helpers import RelevamientoFormManager
from relevamientos.views.web_views import RelevamientoCreateView, RelevamientoUpdateView
from relevamientos.web_api_forms import acceso
from relevamientos.web_api_serializers import (
    FORM_ERROR,
    campo,
    mostrar,
    pending_messages,
)
from relevamientos.web_api_views import _NativeReadView


def _formulario(form, *, omitidos=()):
    return {
        "fields": [
            {**campo(bound), "required": bound.field.required}
            for bound in form
            if bound.name not in omitidos
        ],
        "non_field_errors": [str(error) for error in form.non_field_errors()],
    }


class _RelevamientoEditorWebView(_NativeReadView):
    http_method_names = ["get", "head", "post", "options"]
    native_view = RelevamientoCreateView

    def _vista(self, request, comedor_pk, **kwargs):
        get_object_or_404(Comedor.objects, pk=comedor_pk)
        return self.native(self.native_view, request, comedor_pk=comedor_pk, **kwargs)

    @staticmethod
    def _cuerpo(vista, contexto):
        comedor = contexto["comedor"]
        comedor_pk = comedor["id"]
        comedor_url = reverse("comedor_detalle", args=[comedor_pk])
        relevamiento = vista.object
        detalle = (
            reverse("relevamiento_detalle", args=[comedor_pk, relevamiento.pk])
            if relevamiento
            else None
        )
        formularios = {
            key: _formulario(
                contexto[key],
                omitidos=("cocina", "prestacion") if key == "espacio_form" else (),
            )
            for key in RelevamientoFormManager.FORM_CLASSES
        }
        return {
            "comedor": comedor,
            "tiene_referente": Comedor.objects.filter(
                pk=comedor_pk, referente__isnull=False
            ).exists(),
            "responsable_congelado": bool(
                relevamiento and relevamiento.datos_comedor_congelados
            ),
            "relevamiento": (
                {
                    "id": relevamiento.pk,
                    "fecha_visita": mostrar(
                        relevamiento.fecha_visita, "Sin información"
                    ),
                }
                if relevamiento
                else None
            ),
            "forms": {"root": _formulario(contexto["form"]), **formularios},
            "urls": {
                "comedores": reverse("comedores"),
                "comedor": comedor_url,
                "detalle": detalle,
                "cancelar": detalle or reverse("relevamientos", args=[comedor_pk]),
            },
        }

    def get(self, request, comedor_pk, **kwargs):
        vista = self._vista(request, comedor_pk, **kwargs)
        respuesta = vista.get(vista.request, **vista.kwargs)
        return Response(self._cuerpo(vista, respuesta.context_data))

    def post(self, request, comedor_pk, **kwargs):
        _ = request.data  # Bind native forms to the parsed, form-encoded POST.
        vista = self._vista(request, comedor_pk, **kwargs)
        with transaction.atomic():
            respuesta = vista.post(vista.request, **vista.kwargs)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response(
                {
                    "ok": True,
                    "message": "Acompañamiento territorial guardado correctamente.",
                    "redirect": respuesta.url,
                }
            )
        # Extract bound fields directly; never render or send the page HTML.
        pending_messages(vista.request)
        return Response(
            {"detail": FORM_ERROR, **self._cuerpo(vista, respuesta.context_data)},
            status=400,
        )


class RelevamientoCrearWebView(_RelevamientoEditorWebView):
    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.add_relevamiento"),
    ]


class RelevamientoEditarWebView(_RelevamientoEditorWebView):
    native_view = RelevamientoUpdateView
    permission_classes = [
        WebGatePermission,
        acceso("relevamientos.change_relevamiento"),
    ]
