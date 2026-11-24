"""Web API (G1 v1) del formulario de alta y edición de un centro de VAT (V06.02).

``/api/web/vat/centros-formulario/nuevo/`` y ``/api/web/vat/centros-formulario/<pk>/editar/`` corren ``CentroCreateView`` y
``CentroUpdateView`` (su guarda de ``dispatch``: 403 sin permiso de alta o de edición del centro y 404 si no existe, el
``get_form`` con ``CentroAltaForm``, el formset de contactos y el ``post`` completo con ``crear_centro`` o
``actualizar_centro``) y proyectan lo que imprime ``centro_create_form.html``. Un POST válido responde
``{"ok": true, "redirect": <url nativa>}``; uno inválido responde 400 con el formulario ligado (valores y errores), de modo
que un rechazo deja los datos guardados sin cambios. El prefijo ``centros/`` es de la API INET. Acceso: ``VAT.view_centro``,
como las rutas.
"""

from django.http import HttpResponse
from django.urls import reverse
from rest_framework.response import Response

from VAT.views.centro import CentroCreateView, CentroUpdateView
from VAT.web_api_common import campo_formulario, mensajes_pendientes, valor_de_campo
from VAT.web_api_vat_centros_base import VatEscrituraWebView, redireccion

_VER = ["VAT.view_centro"]
# Order in which the template draws the ``as_crispy_field`` fields (the same name can be absent: the CFP operator loses three).
_CAMPOS = (
    "nombre",
    "codigo",
    "clase_institucion",
    "tipo_gestion",
    "situacion",
    "domicilio_actividad",
    "calle",
    "numero",
    "codigo_postal",
    "lote",
    "manzana",
    "entre_calles",
    "provincia",
    "municipio",
    "localidad",
    "correo",
    "telefono",
    "celular",
    "sitio_web",
)
_CAMPOS_CONTACTO = (
    "nombre_contacto",
    "rol_area",
    "documento",
    "telefono_contacto",
    "email_contacto",
)


def _campo(bound):
    """One bound field as the native widget renders it (a locked field is ``disabled``)."""
    campo = campo_formulario(bound)
    if bound.field.widget.is_hidden:
        # A ``ModelChoiceField`` whose queryset is narrowed after ``HiddenInput`` is set gets ``choices`` on it: not a select.
        campo.update(
            tag="input",
            attrs={**campo["attrs"], "type": "hidden"},
            choices=[],
            value=valor_de_campo(bound),
        )
    campo["disabled"] = bool(bound.field.disabled)
    # ``field.field.required``: the asterisk of the crispy label.
    campo["required"] = bool(bound.field.required)
    return campo


def _errores(bound):
    return [str(error) for error in bound.errors]


def _usuarios(form, nombre, opciones, extra=None):
    """The hidden ``<select multiple>`` of referentes or revisores, with the options of their search box."""
    bound = form[nombre]
    errores = _errores(bound) + (_errores(form[extra]) if extra else [])
    return {
        "label": str(bound.label),
        "choices": [
            {"value": str(valor), "label": str(etiqueta)}
            for valor, etiqueta in bound.field.choices
        ],
        "selected": [str(v) for v in bound.field.widget.format_value(bound.value())],
        "options": list(opciones),
        "errors": errores,
    }


def _errores_contacto(formulario):
    """``{{ contacto_form.errors }}``: the field name and its messages, in the order Django prints them."""
    return [
        {"field": nombre, "messages": [str(m) for m in mensajes]}
        for nombre, mensajes in formulario.errors.items()
    ]


def _contacto(formulario):
    return {
        "hidden": [
            {"name": bound.name, "value": valor_de_campo(bound)}
            for bound in formulario.hidden_fields()
        ],
        "fields": [_campo(formulario[nombre]) for nombre in _CAMPOS_CONTACTO],
        "errors": _errores_contacto(formulario),
    }


def _formulario(vista, rechazo=None):
    """The page: ``centro_create_form.html`` with the context of the native view (the rejected POST, when there is one)."""
    ligados = {"form": rechazo[0], "contacto_formset": rechazo[1]} if rechazo else {}
    contexto = vista.get_context_data(**ligados)
    form, formset = contexto["form"], contexto["contacto_formset"]
    activo = None
    if contexto.get("show_activo_toggle"):
        bound = form["activo"]
        activo = {
            "id": bound.id_for_label,
            "label": str(bound.label),
            "checked": bool(bound.value()),
            "errors": _errores(bound),
        }
    return {
        "editing": form.instance.pk is not None,
        "title": contexto["page_title"],
        "fields": [_campo(form[nombre]) for nombre in _CAMPOS if nombre in form.fields],
        "referentes": _usuarios(
            form, "referentes", form.referente_search_options, extra="referente"
        ),
        "referente": _campo(form["referente"]),
        "revisores": _usuarios(form, "revisores", form.revisor_search_options),
        "non_field_errors": [str(e) for e in form.non_field_errors()],
        "contactos": {
            "initial_forms": formset.initial_form_count(),
            "min_num": formset.min_num,
            "max_num": formset.max_num,
            "forms": [_contacto(c) for c in formset.forms],
            "empty": _contacto(formset.empty_form),
            "non_form_errors": [str(e) for e in formset.non_form_errors()],
        },
        "activo": activo,
        "actions": {
            "cancel": contexto["cancel_url"],
            "submit": contexto["submit_text"],
            "submit_continue": contexto.get(
                "submit_continue_text", "Guardar y continuar"
            ),
            "save_continue": contexto.get("show_save_continue") is not False,
        },
        "urls": {
            "municipios": reverse("ajax_load_municipios"),
            "localidades": reverse("ajax_load_localidades"),
        },
        "messages": mensajes_pendientes(vista.request),
    }


def _con_guarda(native_class):
    """The native view with its ``dispatch`` intact (the create/edit guard) and without running its ``get``/``post``."""

    class _Guarda(native_class):
        def get(self, request, *args, **kwargs):
            return HttpResponse()

        post = get

    return _Guarda


def _con_rechazo(native_class):
    """The native view that keeps the bound form and formset of a rejected POST instead of rendering the template."""

    class _Rechazo(native_class):
        rechazo = None

        def form_invalid(self, form, contacto_formset):
            self.rechazo = (form, contacto_formset)
            return HttpResponse(status=400)

    return _Rechazo


class _CentroFormularioWebView(VatEscrituraWebView):
    """GET (form) and POST (native ``post``) of the centro create/update view."""

    codigos = _VER
    crear = False

    def preparar(self, kwargs):
        django_request = self.request._request  # pylint: disable=protected-access
        # ``CentroCreateView.dispatch`` / ``CentroUpdateView.dispatch``: 403 without the create/edit scope, 404 for an unknown centro.
        guarda = _con_guarda(self.native_class)()
        guarda.setup(django_request, **kwargs)
        guarda.dispatch(django_request, **kwargs)
        vista = _con_rechazo(self.native_class)()
        vista.setup(django_request, **kwargs)
        vista.object = None if self.crear else vista.get_object()
        return vista

    def get(self, request, **kwargs):
        vista = self.preparar(kwargs)
        return Response(_formulario(vista))

    def post(self, request, **kwargs):
        vista = self.preparar(kwargs)
        respuesta = vista.post(
            request._request, **kwargs  # pylint: disable=protected-access
        )
        if vista.rechazo is None:
            return redireccion(respuesta)
        return Response(_formulario(vista, vista.rechazo), status=400)


class CentroCreateFormWebView(_CentroFormularioWebView):
    """``.../centros-formulario/nuevo/``: ``CentroCreateView``."""

    native_class = CentroCreateView
    crear = True


class CentroUpdateFormWebView(_CentroFormularioWebView):
    """``.../centros-formulario/<pk>/editar/``: ``CentroUpdateView``."""

    native_class = CentroUpdateView
