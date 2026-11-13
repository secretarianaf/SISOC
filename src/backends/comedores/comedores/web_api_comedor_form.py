"""Web API (G1 v1) of the comedor create/edit form (CO07.02).

``/api/web/comedores/comedores/`` runs the native ``ComedorCreateView`` and
``ComedorUpdateView`` themselves: ``ComedorForm`` + ``ReferenteForm`` (prefix
``referente``) validation, the atomic save with the estado history, the new
images and, on edit, the images marked for deletion. React gets the real form's
fields (in template order), options, values and errors; it never rebuilds a
rule. After the web gate the native route guards apply unchanged:

- create: ``permissions_any_required(["comedores.add_comedor"])``;
- edit: ``permissions_any_required(["comedores.change_comedor"])``, plus the
  object scope of the native view (outside the user's scope is a 404).

Only what ``comedor_form.html`` renders reaches the native view: the controls of
``ComedorForm`` and ``ReferenteForm`` listed below, the new photo and images and
the per-image ``imagen_ciudadano-borrar-<id>`` checkboxes. The model form accepts
more fields (``responsable_tarjeta_*``, ``estado_validacion``…): a request body
cannot set them through this API, exactly as the native page cannot.

Known source behaviours kept as they are (decision
``docs/registro/decisiones/2026-11-10-2785-brechas-acceso-conservadas.md``): the
native image deletion looks the ids up without filtering by comedor, and the
transaction does not roll back bytes already written to storage.
"""

import re

from django.http import HttpResponseRedirect
from django.http.request import QueryDict
from django.urls import reverse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# The exact predicates of the native URL decorators.
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from comedores.views.comedor import ComedorCreateView, ComedorUpdateView
from comedores.web_api_comedores import pending_messages

CREATE_PERMISSIONS = ["comedores.add_comedor"]
EDIT_PERMISSIONS = ["comedores.change_comedor"]
API = "/api/web/comedores/comedores/"

# Controls ``comedor_form.html`` renders, by section and in template order.
SECTIONS = (
    (
        "basic",
        "form",
        (
            "nombre",
            "id_externo",
            "tipocomedor",
            "categoria_espacio_comunitario",
            "categoria_espacio_comunitario_otra",
            "organizacion",
            "programa",
            "proyecto",
            "es_judicializado",
            "es_caritas",
        ),
    ),
    ("estado", "form", ("estado_general", "subestado", "motivo", "comienzo")),
    (
        "ubicacion",
        "form",
        (
            "provincia",
            "municipio",
            "localidad",
            "partido",
            "barrio",
            "codigo_postal",
            "calle",
            "numero",
            "piso",
            "departamento",
            "manzana",
            "lote",
            "entre_calle_1",
            "entre_calle_2",
            "latitud",
            "longitud",
        ),
    ),
    (
        "referente",
        "referente_form",
        ("nombre", "apellido", "mail", "celular", "documento", "funcion"),
    ),
)
POSTED_FIELDS = frozenset(
    name if origin == "form" else f"referente-{name}"
    for _, origin, names in SECTIONS
    for name in names
)
IMAGE_DELETE = re.compile(r"^imagen_ciudadano-borrar-\d+$")
POSTED_FILES = frozenset({"foto_legajo", "imagenes"})


class CrearComedor(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, CREATE_PERMISSIONS)


class EditarComedor(BasePermission):
    def has_permission(self, request, view):
        return _has_any_permissions(request.user, EDIT_PERMISSIONS)


def _valor(bound):
    value = bound.value()
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    if value is None:
        return ""
    return str(value)


def _opciones(bound):
    field = bound.field
    choices = getattr(field, "choices", None)
    if choices is None:
        choices = getattr(field.widget, "choices", None)
    if choices is None:
        return None
    return [{"value": str(v), "label": str(label)} for v, label in choices]


def _campo(bound, section):
    field = bound.field
    widget = field.widget
    opciones = _opciones(bound)
    if bound.is_hidden:
        tipo = "hidden"
    elif opciones is not None:
        tipo = "select"
    else:
        tipo = widget.input_type or "text"
    return {
        "name": bound.html_name,
        "section": section,
        "label": str(bound.label or ""),
        "type": tipo,
        "required": field.required,
        "disabled": field.disabled,
        "help": str(field.help_text or ""),
        "value": _valor(bound),
        "options": opciones,
        "errors": [str(e) for e in bound.errors],
        "attrs": {
            k: str(v)
            for k, v in {**field.widget_attrs(widget), **widget.attrs}.items()
            if k
            in (
                "maxlength",
                "minlength",
                "min",
                "max",
                "step",
                "placeholder",
                "data-placeholder",
            )
        },
    }


def _archivo(archivo):
    if not archivo:
        return None
    return {"url": archivo.url, "name": archivo.name}


def _formulario(context, comedor_pk):
    form = context["form"]
    referente = context["referente_form"]
    fields = []
    for section, origin, names in SECTIONS:
        origen = form if origin == "form" else referente
        fields.extend(_campo(origen[name], section) for name in names)
    return {
        "comedor_id": comedor_pk,
        "fields": fields,
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "referente_non_field_errors": [str(e) for e in referente.non_field_errors()],
        "estado_locked": bool(form.fields["estado_general"].disabled),
        "estado_tree": form.estado_tree,
        "codigo_de_proyecto_programa_ids": form.codigo_de_proyecto_programa_ids,
        "foto_legajo": _archivo(form.instance.foto_legajo),
        "imagenes": [
            {"id": imagen.pk, **(_archivo(imagen.imagen) or {})}
            for imagen in context.get("imagenes_borrar", [])
        ],
        "urls": {
            "cancel": (
                reverse("comedor_detalle", args=[comedor_pk])
                if comedor_pk
                else reverse("comedores")
            ),
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
            "organizaciones": reverse("ajax_load_organizaciones"),
            "proyectos": reverse("organizacion_proyectos_ajax", args=[0]),
            "address_preview": reverse("address_preview"),
        },
    }


def _native(view_class, django_request, **kwargs):
    view = view_class()
    view.setup(django_request, **kwargs)
    return view


def _whitelist(django_request):
    """Keep what the native template renders; the rest of the model form is not settable."""
    entrada = django_request.POST
    permitido = QueryDict(mutable=True)
    for clave in entrada:
        if clave in POSTED_FIELDS or IMAGE_DELETE.match(clave):
            permitido.setlist(clave, entrada.getlist(clave))
    django_request.POST = permitido
    archivos = django_request.FILES
    for clave in [c for c in archivos if c not in POSTED_FILES]:
        archivos.pop(clave)


class _FormView(APIView):
    authentication_classes = [SessionAuthentication]
    renderer_classes = [JSONRenderer]

    @staticmethod
    def _django(request):
        return request._request  # pylint: disable=protected-access

    def _vista(self, request, pk):
        django_request = self._django(request)
        if pk is None:
            vista = _native(ComedorCreateView, django_request)
            vista.object = None
        else:
            vista = _native(ComedorUpdateView, django_request, pk=pk)
            vista.object = vista.get_object()
        return vista


class ComedorFormularioWebView(_FormView):
    """``GET .../formulario/`` and ``.../<pk>/formulario/``: the native form."""

    http_method_names = ["get", "head"]

    def get_permissions(self):
        clase = CrearComedor if self.kwargs.get("pk") is None else EditarComedor
        return [WebGatePermission(), clase()]

    def get(self, request, pk=None):
        vista = self._vista(request, pk)
        context = vista.get_context_data()
        return Response(
            {
                "form": _formulario(context, pk),
                "messages": pending_messages(request),
            }
        )


class ComedorGuardarWebView(_FormView):
    """``POST .../crear/`` (201) and ``.../<pk>/editar/`` (200): the native ``post``."""

    http_method_names = ["post"]

    def get_permissions(self):
        clase = CrearComedor if self.kwargs.get("pk") is None else EditarComedor
        return [WebGatePermission(), clase()]

    def post(self, request, pk=None):
        django_request = self._django(request)
        _whitelist(django_request)
        if pk is None:
            vista = _native(ComedorCreateView, django_request)
        else:
            vista = _native(ComedorUpdateView, django_request, pk=pk)
        respuesta = vista.post(django_request)
        if isinstance(respuesta, HttpResponseRedirect):
            return Response(
                {"redirect": respuesta.url},
                status=status.HTTP_201_CREATED if pk is None else status.HTTP_200_OK,
            )
        context = respuesta.context_data
        form = context["form"]
        referente = context["referente_form"]
        return Response(
            {
                "errors": {
                    **{
                        n: [str(e) for e in es]
                        for n, es in form.errors.items()
                        if n != "__all__"
                    },
                    **{
                        referente.add_prefix(n): [str(e) for e in es]
                        for n, es in referente.errors.items()
                        if n != "__all__"
                    },
                },
                "non_field_errors": [str(e) for e in form.non_field_errors()],
                "form": _formulario(context, pk),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
