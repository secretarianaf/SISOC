"""Gestión conjunta de auditorías de rendiciones (issue #2673)."""

import calendar
from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Coalesce, Lower, Replace
from django.utils import timezone
from core.services.text_encoding import normalize_text

from rendicioncuentasmensual.forms import (
    RendicionActaMultipleChoiceField,
    _coerce_booleano_nullable,
)
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.services import RendicionCuentaMensualService


class AuditoriaBusquedaForm(forms.Form):
    filtro = forms.ChoiceField(
        choices=[
            ("proyecto", "Proyecto"),
            ("organizacion", "Organización"),
            ("periodo", "Período"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    busqueda = forms.CharField(
        required=True,
        max_length=120,
        label="Buscar",
        error_messages={"required": "Ingresá un texto para realizar la búsqueda."},
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "search",
                "placeholder": "Código o nombre del proyecto",
                "aria-describedby": "ayuda-busqueda-auditoria",
            }
        ),
    )

    @classmethod
    def desde_parametros(cls, parametros):
        datos = parametros.copy() if "busqueda" in parametros else None
        if datos is not None:
            datos.setdefault("filtro", "proyecto")
        return cls(datos, initial={"filtro": "proyecto"})

    def clean(self):
        cleaned = super().clean()
        texto = normalize_text(cleaned.get("busqueda", ""))
        if texto:
            cleaned["busqueda"] = texto
        elif "busqueda" in cleaned:
            self.add_error("busqueda", "Ingresá un texto para realizar la búsqueda.")
        if cleaned.get("filtro") == "periodo" and texto:
            for formato in ("%d/%m/%Y", "%Y-%m-%d", "%m/%Y", "%Y-%m", "%Y"):
                try:
                    inicio = datetime.strptime(texto, formato).date()
                except ValueError:
                    continue
                fin = inicio
                if formato in ("%m/%Y", "%Y-%m"):
                    fin = inicio.replace(
                        day=calendar.monthrange(inicio.year, inicio.month)[1]
                    )
                elif formato == "%Y":
                    fin = inicio.replace(month=12, day=31)
                cleaned["periodo_inicio"] = inicio
                cleaned["periodo_fin"] = fin
                break
            else:
                self.add_error(
                    "busqueda", "Ingresá un período como MM/AAAA, DD/MM/AAAA o AAAA."
                )
        return cleaned


class AuditoriaForm(forms.Form):
    validada = forms.BooleanField(
        label="Validada",
        required=True,
        error_messages={"required": "Marcá Validada para poder guardar la auditoría."},
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    genera_acta_auditoria = forms.TypedChoiceField(
        label="¿Se genera acta de auditoría?",
        required=False,
        choices=[("", "Seleccioná una opción"), (True, "Sí"), (False, "No")],
        coerce=_coerce_booleano_nullable,
        empty_value=None,
    )
    rendiciones_incluidas = RendicionActaMultipleChoiceField(
        queryset=RendicionCuentaMensual.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Rendiciones incluidas en el acta",
    )
    acta_auditoria = forms.FileField(required=False, label="Acta de Auditoría")
    resultado = forms.ChoiceField(
        required=False,
        label="Resultado de la Auditoría",
        choices=[
            ("", "Seleccioná un resultado"),
            ("finalizada", "Finalizada Sin Observaciones"),
            ("finalizada_con_observaciones", "Finalizada con Observaciones"),
        ],
    )
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    documento_regularizacion = forms.FileField(
        required=False, label="Acta Complementaria"
    )

    def __init__(self, *args, rendicion, **kwargs):
        super().__init__(*args, **kwargs)
        self.ya_validada = rendicion.validada is True
        self.fields["genera_acta_auditoria"].required = self.ya_validada
        if self.ya_validada:
            self.initial["validada"] = True
            self.fields["validada"].disabled = True
        self.fields["rendiciones_incluidas"].queryset = (
            RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(
                rendicion
            )
        )
        for nombre, field in self.fields.items():
            if nombre not in {"rendiciones_incluidas", "validada"}:
                field.widget.attrs["class"] = (
                    "form-select"
                    if isinstance(field.widget, forms.Select)
                    else "form-control"
                )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("genera_acta_auditoria") is True:
            if not cleaned.get("resultado"):
                self.add_error("resultado", "Seleccioná el resultado de la auditoría.")
            if (
                cleaned.get("resultado") == "finalizada_con_observaciones"
                and not (cleaned.get("observaciones") or "").strip()
            ):
                self.add_error(
                    "observaciones", "Ingresá las observaciones de auditoría."
                )
        else:
            for nombre in (
                "rendiciones_incluidas",
                "acta_auditoria",
                "resultado",
                "observaciones",
                "documento_regularizacion",
            ):
                if cleaned.get(nombre):
                    self.add_error(
                        nombre, "Este campo requiere seleccionar que se genera un acta."
                    )
        if cleaned.get("resultado") != "finalizada_con_observaciones" and cleaned.get(
            "documento_regularizacion"
        ):
            self.add_error(
                "documento_regularizacion",
                "El acta complementaria corresponde a un resultado con observaciones.",
            )
        return cleaned


class AuditoriaService:
    @staticmethod
    def mensaje_guardado(rendicion):
        if rendicion.fecha_gestion_auditoria:
            return "Auditoría guardada. La gestión de esta rendición quedó cerrada."
        return "Rendición validada. La auditoría continúa en curso para decidir sobre el acta."

    @staticmethod
    def _campo_sin_tildes(expresion):
        """Normalización española portable entre MySQL y SQLite, sin collation fija."""
        expresion = Coalesce(expresion, Value(""), output_field=CharField())
        for letra in "áéíóúüñÁÉÍÓÚÜÑ\u0301\u0308\u0303":
            expresion = Replace(expresion, Value(letra), Value(normalize_text(letra)))
        return Lower(expresion)

    @staticmethod
    def buscar(datos):
        disponibles = AuditoriaService.disponibles()
        texto = normalize_text(datos.get("busqueda"))
        if not texto:
            return disponibles.none()
        if datos["filtro"] == "periodo":
            return disponibles.filter(
                periodo_inicio__lte=datos["periodo_fin"],
                periodo_fin__gte=datos["periodo_inicio"],
            )
        if datos["filtro"] == "organizacion":
            nombre = Case(
                When(proyecto__isnull=False, then=F("proyecto__organizacion__nombre")),
                default=F("comedor__organizacion__nombre"),
                output_field=CharField(),
            )
            return disponibles.alias(
                nombre_busqueda=AuditoriaService._campo_sin_tildes(nombre)
            ).filter(nombre_busqueda__contains=texto)
        if datos["filtro"] != "proyecto":
            return disponibles.none()
        codigo = Case(
            When(proyecto__isnull=False, then=F("proyecto__codigo")),
            default=F("comedor__codigo_de_proyecto"),
            output_field=CharField(),
        )
        return disponibles.alias(
            codigo_busqueda=AuditoriaService._campo_sin_tildes(codigo),
            nombre_busqueda=AuditoriaService._campo_sin_tildes(F("proyecto__nombre")),
        ).filter(
            Q(codigo_busqueda__contains=texto) | Q(nombre_busqueda__contains=texto)
        )

    @staticmethod
    def disponibles():
        return (
            RendicionCuentaMensual.objects.filter(
                deleted_at__isnull=True,
                fecha_gestion_auditoria__isnull=True,
                fecha_auditada__isnull=True,
                etapa_proceso=RendicionCuentaMensual.ETAPA_AUDITORIA,
                subestado_proceso__in=[
                    RendicionCuentaMensual.SUBESTADO_PENDIENTE,
                    RendicionCuentaMensual.SUBESTADO_EN_CURSO,
                ],
            )
            .exclude(genera_acta_auditoria=True)
            .filter(Q(acta_auditoria="") | Q(acta_auditoria__isnull=True))
            .select_related("proyecto__organizacion", "comedor__organizacion")
        )

    @staticmethod
    @transaction.atomic
    def guardar(*, rendicion, datos, actor):
        seleccionadas_ids = {
            item.pk for item in datos.get("rendiciones_incluidas") or []
        }
        # Bloqueo ordenado: dos actas concurrentes no pueden consumir la misma rendición.
        bloqueadas = list(
            RendicionCuentaMensual.objects.select_for_update()
            .filter(
                pk__in=seleccionadas_ids | {rendicion.pk},
                deleted_at__isnull=True,
            )
            .order_by("pk")
        )
        actual = next((item for item in bloqueadas if item.pk == rendicion.pk), None)
        if (
            actual is None
            or not AuditoriaService.disponibles().filter(pk=actual.pk).exists()
        ):
            raise ValidationError(
                "La rendición ya no está disponible para gestionar su auditoría."
            )
        # Revalidar dentro de la transacción, también para callers ajenos a la vista.
        form = AuditoriaForm(
            data={**datos, "rendiciones_incluidas": list(seleccionadas_ids)},
            files={
                key: datos[key]
                for key in ("acta_auditoria", "documento_regularizacion")
                if datos.get(key)
            },
            rendicion=actual,
        )
        if not form.is_valid():
            raise ValidationError(dict(form.errors))
        datos = form.cleaned_data
        ahora = timezone.now()
        actual.fecha_gestion_auditoria = (
            ahora if datos["genera_acta_auditoria"] is not None else None
        )
        actual.validada = True
        actual.genera_acta_auditoria = datos["genera_acta_auditoria"]
        actual.fecha_carga_auditoria = actual.fecha_carga_auditoria or ahora
        actual.subestado_proceso = RendicionCuentaMensual.SUBESTADO_EN_CURSO
        # Observaciones es un campo general: solo se escribe si hay observaciones.
        con_observaciones = datos.get("resultado") == "finalizada_con_observaciones"
        if actual.genera_acta_auditoria:
            actual.rendicion_origen_acta = actual
            actual.estado = RendicionCuentaMensual.ESTADO_FINALIZADA
            actual.subestado_proceso = datos["resultado"]
            actual.fecha_auditada = ahora
            if con_observaciones:
                actual.observaciones = datos["observaciones"]
            for campo in ("acta_auditoria", "documento_regularizacion"):
                if datos.get(campo):
                    setattr(actual, campo, datos[campo])
        # Reutiliza el registro de actor del servicio de rendiciones.
        # pylint: disable=protected-access
        RendicionCuentaMensualService._aplicar_usuario_ultima_modificacion(
            actual, actor
        )
        actual.save()
        if actual.genera_acta_auditoria:
            grupo = [actual] + [
                item for item in bloqueadas if item.pk in seleccionadas_ids
            ]
            for item in grupo:
                if item.pk != actual.pk:
                    for campo in (
                        "estado",
                        "validada",
                        "genera_acta_auditoria",
                        "rendicion_origen_acta_id",
                        "subestado_proceso",
                        "fecha_carga_auditoria",
                        "fecha_auditada",
                        "fecha_gestion_auditoria",
                        "acta_auditoria",
                        "documento_regularizacion",
                        *(("observaciones",) if con_observaciones else ()),
                    ):
                        setattr(item, campo, getattr(actual, campo))
                    RendicionCuentaMensualService._aplicar_usuario_ultima_modificacion(
                        item, actor
                    )  # pylint: disable=protected-access
                    item.save()
                item.rendiciones_incluidas.set(
                    otro for otro in grupo if otro.pk != item.pk
                )
        return actual
