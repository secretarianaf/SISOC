"""Web API (G1 v1) of the CDI institutional form create and edit screens (CDI03).

Session transport over the native views: each API view inherits
``FormularioCDICreateView`` / ``FormularioCDIUpdateView``, so the scoped centre
and form (404 outside the actor's scope), the centre snapshot used as initial
data on create, ``FormularioCDIForm`` with its cleaning, the three fixed
formsets, the transaction that saves form and formsets, ``ensure_fixed_rows``
and the success messages stay the native ones. Order of checks:

1. G1 (``WebGatePermission``): 401/403 JSON, or the signed attestation in the
   runtime.
2. The same permission code as the URL decorator in ``centrodeinfancia/urls.py``
   (``add_formulariocdi`` and ``change_formulariocdi``; superuser bypass included).
3. The native dispatch; the CDI-A3 read-only veto for SIMEPI auditors runs in
   the native ``post`` before anything is built or saved.

Known native behaviour that is kept, not corrected: the edit GET builds the
formsets through ``ensure_fixed_rows``, which creates the rows of the three
fixed catalogues that are missing (the auditor veto only covers POST), and the
POST saves with ``form.save(commit=False)`` plus the formsets, never with
``Form.save(commit=True)``. The API runs the very same native calls.

The page template draws each field with ``{{ field|as_crispy_field }}`` and the
formset cells with the bare widget; the API sends that same server-rendered
markup of the visible widgets (labels, widgets and error feedback are the native ones; the
management forms and the hidden key widgets of each row go as name, id and value) together with
the section layout, the schedule rows and the three formsets including their
management forms, per-row errors and non-form errors. A native redirect becomes
``{"ok": true, "redirect": <Location>}`` and the queued success message shows
on the form page like the HTML; an invalid form returns 400 with the same
payload. Responses are ``private, no-store``.
"""

from django.template import Context, Template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from centrodeinfancia.views_formulario_cdi import (
    FormularioCDICreateView,
    FormularioCDIUpdateView,
)
from centrodeinfancia.web_api import pending_messages
from centrodeinfancia.web_api_observaciones import _json, _ObservacionTransportMixin

PERMISO_ALTA = "centrodeinfancia.add_formulariocdi"
PERMISO_EDICION = "centrodeinfancia.change_formulariocdi"
_CRISPY = Template("{% load crispy_forms_tags %}{{ campo|as_crispy_field }}")

# Per formset: the key widgets of the first column (the row label is a property
# of the form) and the cells that follow,
# in the order of the template.
_FORMSETS = {
    "salas": (
        ("id", "grupo_etario"),
        (
            "cantidad_salas",
            "superficie_exclusiva_m2",
            "cantidad_ninos",
            "cantidad_personal_sala",
        ),
    ),
    "demanda": (
        ("id", "grupo_etario"),
        ("cantidad_demanda_insatisfecha",),
    ),
    "articulacion": (
        ("id", "tipo_institucion"),
        ("frecuencia",),
    ),
}


def _crispy(campo):
    """``{{ field|as_crispy_field }}``, the markup of the native page."""
    return _CRISPY.render(Context({"campo": campo}))


def _errores(errores):
    return [str(error) for error in errores]


def _ocultos(campos):
    """Hidden widgets (management form, id and key of a row) as name, id and value."""
    return [
        {
            "name": campo.html_name,
            "id": campo.auto_id,
            "value": "" if campo.value() is None else str(campo.value()),
        }
        for campo in campos
    ]


def _formset(formset, claves, celdas):
    return {
        "management": _ocultos(formset.management_form),
        "non_form_errors": _errores(formset.non_form_errors()),
        "rows": [
            {
                "hidden": _ocultos(fila[nombre] for nombre in claves),
                "label": str(fila.etiqueta_fila),
                "cells": [
                    {"html": str(fila[nombre]), "errors": _errores(fila[nombre].errors)}
                    for nombre in celdas
                ],
            }
            for fila in formset.forms
        ],
    }


class _FormularioTransportMixin(_ObservacionTransportMixin):
    """The form payload of the native context; an invalid form is a 400."""

    def get_context(self, form, formsets, instance=None):
        contexto = super().get_context(form, formsets, instance)
        self.contexto_nativo = contexto
        return contexto

    def get(self, request, *args, **kwargs):
        # The same composition as the native ``get``, without rendering the HTML.
        mensajes = pending_messages(request)
        instance = self.get_form_instance()
        form = self.construir_formulario(instance=instance)
        formsets = self.construir_formsets(instance=instance)
        return self._respuesta(self.get_context(form, formsets, instance), mensajes)

    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        if respuesta.status_code == 302:
            return respuesta
        # Rejected: the native view rendered its page; the context is the payload.
        return self._respuesta(
            self.contexto_nativo, pending_messages(request), status=400
        )

    def _respuesta(self, context, mensajes, status=200):
        form, centro = context["form"], context["centro"]
        formsets = {
            "salas": context["formset_distribucion_salas"],
            "demanda": context["formset_demanda_insatisfecha"],
            "articulacion": context["formset_articulacion"],
        }
        con_errores = bool(
            form.errors
            or any(f.errors or f.non_form_errors() for f in formsets.values())
        )
        es_edicion = bool(context["is_edit"])
        return _json(
            {
                "is_edit": es_edicion,
                "centro": {
                    "id": centro.pk,
                    "nombre": str(centro.nombre),
                    "codigo": str(centro.codigo_cdi or "Sin codigo"),
                    "listado_url": reverse(
                        "centrodeinfancia_formulario_listado", args=[centro.pk]
                    ),
                    "cancelar_url": (
                        reverse(
                            "centrodeinfancia_formulario_detalle",
                            args=[centro.pk, form.instance.pk],
                        )
                        if es_edicion
                        else reverse("centrodeinfancia_detalle", args=[centro.pk])
                    ),
                },
                "has_errors": con_errores,
                "non_field_errors": _errores(form.non_field_errors()),
                "sections": [
                    {
                        "title": str(seccion["title"]),
                        "rows": [
                            [
                                {
                                    "name": campo["name"],
                                    "col_class": campo["col_class"],
                                    "html": _crispy(campo["bound_field"]),
                                }
                                for campo in fila
                            ]
                            for fila in seccion["rows"]
                        ],
                    }
                    for seccion in context["section_fields"]
                ],
                "horarios": [
                    {
                        "dia": horario["dia"],
                        "etiqueta": str(horario["etiqueta"]),
                        "apertura": _crispy(horario["apertura"]),
                        "cierre": _crispy(horario["cierre"]),
                    }
                    for horario in context["horario_fields"]
                ],
                "formsets": {
                    nombre: _formset(formset, *_FORMSETS[nombre])
                    for nombre, formset in formsets.items()
                },
                "urls": {
                    "departamentos": reverse(
                        "centrodeinfancia_ajax_load_departamentos_ipi"
                    ),
                    "municipios": reverse("ajax_load_municipios"),
                    "localidades": reverse("ajax_load_localidades"),
                },
                "messages": mensajes,
            },
            status=status,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class FormularioCrearWebView(_FormularioTransportMixin, FormularioCDICreateView):
    """``/api/web/cdi/centros/<pk>/formularios/crear/``: native create."""

    permission_code = PERMISO_ALTA


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class FormularioEditarWebView(_FormularioTransportMixin, FormularioCDIUpdateView):
    """``/api/web/cdi/centros/<pk>/formularios/<form_pk>/editar/``: native edit."""

    permission_code = PERMISO_EDICION
