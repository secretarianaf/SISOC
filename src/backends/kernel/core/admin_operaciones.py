"""Operaciones de soporte desde el admin (issue #2789, Fase 2).

Una ``Operacion`` describe un cambio de estado o corrección que ya resuelve un
service del dueño (``<app>/services/``). El admin nunca edita el campo a mano:
la operación pide confirmación (y motivo cuando aplica), llama al service con
el usuario del request y deja un ``auditlog.LogEntry`` con la operación, el
motivo y el estado antes/después.

Cada operación aparece en tres lugares, todos con la misma pantalla de
confirmación:

- acción en lote del listado (``actions``), con tope de registros;
- acción por fila (``actions_row``) y en el detalle (``actions_detail``) de Unfold.

Uso::

    class LegajoAdmin(OperacionesAdminMixin, SisocModelAdmin):
        operaciones = (
            Operacion(
                slug="aprobar",
                titulo="Aprobar legajo",
                ejecutar=lambda legajo, usuario, datos: RevisionService.aprobar(
                    legajo, usuario
                ),
                campo_estado="revision_tecnico",
            ),
        )
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from auditlog.models import LogEntry
from django import forms
from django.contrib import messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MinLengthValidator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from unfold.decorators import action
from unfold.widgets import (
    UnfoldAdminSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
)


logger = logging.getLogger("django")

# Tope de registros por acción en lote: una operación masiva sobre PRD tiene
# que ser deliberada. Para más registros, filtrar y repetir.
MAX_REGISTROS_POR_LOTE = 100

# Resultado de un service que avisa el error devolviendo False en vez de
# lanzar excepción (p. ej. AdmisionService.marcar_como_*).
SERVICE_SIN_CAMBIOS = "El service no aplicó el cambio."


@dataclass(frozen=True)
class Operacion:
    """Operación de soporte que delega en un service existente."""

    slug: str
    titulo: str
    # (objeto, usuario, datos_del_form) -> resultado del service.
    ejecutar: Callable[[Any, Any, dict], Any]
    descripcion: str = ""
    icono: str = "bolt"
    campo_estado: str | None = None
    motivo_obligatorio: bool = False
    motivo_min_largo: int = 0
    # Campos extra del form de confirmación: callable sin argumentos que
    # devuelve {nombre: forms.Field}. Lo que cargue el usuario llega en ``datos``.
    campos: Callable[[], dict[str, forms.Field]] | None = None
    destructiva: bool = False
    en_lote: bool = True

    @property
    def nombre_accion(self) -> str:
        return f"operacion_{self.slug}"


class ConfirmarOperacionForm(forms.Form):
    """Confirmación con motivo y los campos propios de la operación."""

    motivo = forms.CharField(
        label="Motivo",
        required=False,
        max_length=2000,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
        help_text="Queda registrado en la auditoría junto con la operación.",
    )

    def __init__(self, *args, operacion: Operacion, **kwargs):
        super().__init__(*args, **kwargs)
        self.operacion = operacion
        motivo = self.fields["motivo"]
        motivo.required = operacion.motivo_obligatorio
        if operacion.motivo_min_largo:
            motivo.validators.append(MinLengthValidator(operacion.motivo_min_largo))
        for nombre, campo in (operacion.campos() if operacion.campos else {}).items():
            self.fields[nombre] = _con_widget_unfold(campo)

    def clean_motivo(self):
        return (self.cleaned_data.get("motivo") or "").strip()


def _con_widget_unfold(campo: forms.Field) -> forms.Field:
    """Aplica el widget de Unfold a los selects, simples o múltiples."""
    if isinstance(campo.widget, forms.HiddenInput) or not isinstance(
        campo, forms.ChoiceField
    ):
        return campo
    if isinstance(campo, (forms.MultipleChoiceField, forms.ModelMultipleChoiceField)):
        campo.widget = UnfoldAdminSelectMultipleWidget(choices=campo.choices)
    else:
        campo.widget = UnfoldAdminSelectWidget(choices=campo.choices)
    return campo


def _valor_estado(obj, campo):
    if not campo:
        return None
    valor = getattr(obj, campo, None)
    return str(getattr(valor, "pk", valor)) if valor is not None else None


def _mensaje_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return str(exc) or exc.__class__.__name__


def _datos_auditoria(operacion: Operacion, datos: dict, lote: str) -> dict:
    """``additional_data`` del LogEntry de una operación."""
    return {
        "origen": "admin",
        "operacion": operacion.slug,
        "titulo": operacion.titulo,
        "motivo": datos.get("motivo", ""),
        "datos": {
            clave: str(valor) for clave, valor in datos.items() if clave != "motivo"
        },
        # Origen y lote de AuditEntryMeta: el signal de audittrail los lee de
        # acá, así core no importa audittrail (contrato de .importlinter).
        "audittrail_source": f"admin:{operacion.slug}",
        "audittrail_batch_key": f"admin-{operacion.slug}-{lote}",
    }


def ejecutar_operacion(*, operacion: Operacion, objetos, usuario, datos: dict):
    """Ejecuta la operación objeto por objeto; un error no frena al resto.

    Devuelve ``(ok, errores)`` donde ``errores`` es ``[(objeto, mensaje)]``.
    """
    lote = uuid.uuid4().hex
    ok, errores = [], []
    for obj in objetos:
        antes = _valor_estado(obj, operacion.campo_estado)
        try:
            with transaction.atomic():
                if operacion.ejecutar(obj, usuario, datos) is False:
                    raise ValidationError(SERVICE_SIN_CAMBIOS)
                obj.refresh_from_db()
                despues = _valor_estado(obj, operacion.campo_estado)
                # LogEntry explícito: vale aunque auditlog no trackee el modelo.
                LogEntry.objects.log_create(
                    obj,
                    force_log=True,
                    action=LogEntry.Action.UPDATE,
                    actor=usuario,
                    changes=(
                        {operacion.campo_estado: [antes, despues]}
                        if operacion.campo_estado and antes != despues
                        else None
                    ),
                    additional_data=_datos_auditoria(operacion, datos, lote),
                )
        except (ValidationError, ValueError, PermissionDenied) as exc:
            errores.append((obj, _mensaje_error(exc)))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Un error inesperado en un registro no corta el lote: queda en
            # el log con traceback y se informa en pantalla.
            logger.exception("Operación de admin %s falló para %r", operacion.slug, obj)
            errores.append((obj, f"Error inesperado: {_mensaje_error(exc)}"))
        else:
            ok.append(obj)
    return ok, errores


def _informar(request, operacion, ok, errores):
    if ok:
        messages.success(
            request, f"{operacion.titulo}: {len(ok)} registro(s) procesado(s)."
        )
    for obj, mensaje in errores[:20]:
        messages.error(request, f"{operacion.titulo} — {obj}: {mensaje}")
    if len(errores) > 20:
        messages.error(request, f"… y {len(errores) - 20} error(es) más.")


@dataclass(frozen=True)
class _Pedido:
    """Operación pedida desde una acción: en lote o sobre un registro."""

    operacion: Operacion
    objetos: list
    en_lote: bool
    volver_a: str


def _pantalla_confirmacion(model_admin, request, pedido: _Pedido, form):
    opts = model_admin.model._meta
    context = {
        **model_admin.admin_site.each_context(request),
        "title": pedido.operacion.titulo,
        "operacion": pedido.operacion,
        "objetos": pedido.objetos,
        "form": form,
        "opts": opts,
        "en_lote": pedido.en_lote,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "max_registros": MAX_REGISTROS_POR_LOTE,
        "changelist_url": reverse(
            f"admin:{opts.app_label}_{opts.model_name}_changelist"
        ),
    }
    return TemplateResponse(request, "admin/sisoc/confirmar_operacion.html", context)


def _procesar(model_admin, request, pedido: _Pedido):
    operacion = pedido.operacion
    if "confirmar_operacion" not in request.POST:
        form = ConfirmarOperacionForm(operacion=operacion)
        return _pantalla_confirmacion(model_admin, request, pedido, form)
    form = ConfirmarOperacionForm(request.POST, operacion=operacion)
    if not form.is_valid():
        return _pantalla_confirmacion(model_admin, request, pedido, form)
    ok, errores = ejecutar_operacion(
        operacion=operacion,
        objetos=pedido.objetos,
        usuario=request.user,
        datos=form.cleaned_data,
    )
    _informar(request, operacion, ok, errores)
    return HttpResponseRedirect(pedido.volver_a)


def _accion_en_lote(operacion: Operacion):
    def accion(model_admin, request, queryset):
        objetos = list(queryset[: MAX_REGISTROS_POR_LOTE + 1])
        if len(objetos) > MAX_REGISTROS_POR_LOTE:
            messages.error(
                request,
                f"{operacion.titulo}: se pueden procesar hasta "
                f"{MAX_REGISTROS_POR_LOTE} registros por vez. Filtrá el listado.",
            )
            return None
        return _procesar(
            model_admin,
            request,
            _Pedido(operacion, objetos, True, request.get_full_path()),
        )

    accion.__name__ = f"{operacion.nombre_accion}_lote"
    accion.short_description = operacion.titulo
    accion.allowed_permissions = ("change",)
    return accion


def _accion_por_objeto(operacion: Operacion):
    def accion(model_admin, request, object_id):
        if not model_admin.has_change_permission(request):
            raise PermissionDenied
        obj = model_admin.get_object(request, object_id)
        if obj is None:
            raise PermissionDenied
        opts = model_admin.model._meta
        volver_a = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]
        )
        return _procesar(
            model_admin, request, _Pedido(operacion, [obj], False, volver_a)
        )

    accion.__name__ = operacion.nombre_accion
    return action(
        description=operacion.titulo,
        url_path=f"operacion-{operacion.slug.replace('_', '-')}",
        icon=operacion.icono,
    )(accion)


class OperacionesAdminMixin:
    """Publica ``operaciones`` como acciones de Unfold (fila, detalle y lote).

    Va antes de ``SisocModelAdmin`` en las bases. Al editar un registro, los
    campos de estado de las operaciones quedan de solo lectura: solo cambian por
    la acción. En el alta se cargan normalmente (pueden ser obligatorios).
    """

    operaciones: tuple[Operacion, ...] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("operaciones"):
            return
        nombres = []
        # Incluye las acciones heredadas para no pisar las de una clase padre.
        lote = list(cls.actions or ())
        for operacion in cls.operaciones:
            setattr(cls, operacion.nombre_accion, _accion_por_objeto(operacion))
            nombres.append(operacion.nombre_accion)
            if operacion.en_lote:
                lote.append(_accion_en_lote(operacion))
        cls.actions_row = (*cls.__dict__.get("actions_row", ()), *nombres)
        cls.actions_detail = (*cls.__dict__.get("actions_detail", ()), *nombres)
        cls.actions = lote

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is None:
            return campos
        for operacion in self.operaciones:
            if operacion.campo_estado and operacion.campo_estado not in campos:
                campos.append(operacion.campo_estado)
        return campos
