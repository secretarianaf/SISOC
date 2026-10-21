from django import forms
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import inlineformset_factory
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    Aval,
    SubtipoEntidad,
)
from gestion_organizaciones.models import Firmante
from core.models import Municipio, Provincia, Localidad
from comedores.territoriales_pnud import (
    etiqueta_territorial,
    usuarios_territoriales_pnud,
)


class TerritorialesMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return etiqueta_territorial(obj)


class OrganizacionForm(forms.ModelForm):
    asignaciones_territoriales = forms.JSONField(
        required=False, widget=forms.HiddenInput()
    )
    codigos_proyecto = forms.CharField(
        required=False,
        label="Códigos de Proyecto",
        widget=forms.HiddenInput(),
    )
    cuit = forms.RegexField(
        regex=r"^[0-9]{11}$",
        required=False,
        strip=False,
        error_messages={
            "invalid": "Ingresá un CUIT de 11 dígitos, solo con números y sin espacios.",
        },
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "maxlength": "11",
                "pattern": "[0-9]{11}",
                "title": "Ingresá 11 dígitos, solo con números y sin espacios.",
            }
        ),
    )
    territoriales_abordaje_comunitario = TerritorialesMultipleChoiceField(
        queryset=usuarios_territoriales_pnud(),
        required=False,
        label="Territorial Asignado Abordaje Comunitario",
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    cuil_duplicado_confirmado = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput,
    )
    cuil_duplicado_confirmado_valor = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Asegura que el campo date cargue el valor previo (almacenado como DateTime)
        fecha_vencimiento = getattr(self.instance, "fecha_vencimiento", None)
        if not self.is_bound and fecha_vencimiento:
            self.initial["fecha_vencimiento"] = fecha_vencimiento.date()
        self.fields["fecha_vencimiento"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_vencimiento"].required = False

        self.popular_campos_ubicacion()
        subtipo_actual_id = (
            self.data.get(self.add_prefix("subtipo_entidad"))
            if self.is_bound
            else getattr(self.instance, "subtipo_entidad_id", None)
        )
        subtipos = SubtipoEntidad.objects.filter(activo=True)
        if subtipo_actual_id:
            subtipos = subtipos | SubtipoEntidad.objects.filter(pk=subtipo_actual_id)
        self.fields["subtipo_entidad"].queryset = subtipos.order_by("nombre")
        self._configurar_territoriales()
        for name in ("region_abordaje", "subzona_abordaje"):
            field = self.fields[name]
            field.queryset = field.queryset.filter(
                Q(activo=True) | Q(pk=getattr(self.instance, f"{name}_id", None))
            )
        self._configurar_subzonas()
        if not self.is_bound and self.instance.pk:
            self.initial["asignaciones_territoriales"] = [
                {"proyecto": proyecto.codigo, "territorial": usuario.pk}
                for proyecto in self.instance.proyectos.filter(
                    activo=True
                ).prefetch_related("territoriales")
                for usuario in proyecto.territoriales.all()
            ]
        if not self.is_bound and self.instance.pk:
            self.initial["codigos_proyecto"] = ", ".join(
                self.instance.proyectos.filter(activo=True).values_list(
                    "codigo", flat=True
                )
            )

    def _configurar_subzonas(self):
        region = (
            self.data.get(self.add_prefix("region_abordaje"))
            if self.is_bound
            else self.initial.get("region_abordaje")
        )
        region_id = int(region) if region and str(region).isdigit() else None
        field = self.fields["subzona_abordaje"]
        self.subzonas_abordaje = list(
            field.queryset.values("id", "nombre", "region_id")
        )
        permitidas = Q(region_id=region_id, region__isnull=False)
        if region_id == self.instance.region_abordaje_id:
            permitidas |= Q(pk=self.instance.subzona_abordaje_id, region__isnull=True)
        field.queryset = field.queryset.filter(permitidas)

    def _configurar_territoriales(self):
        # Los ya asignados siguen siendo opciones aunque hayan perdido el rol:
        # si no, guardar el legajo los quitaría sin que nadie lo haya pedido.
        queryset = usuarios_territoriales_pnud()
        if self.instance.pk:
            asignados = self.instance.territoriales_abordaje_comunitario.values("pk")
            por_proyecto = (
                get_user_model()
                .objects.filter(proyectos_abordaje__organizacion=self.instance)
                .values("pk")
            )
            queryset = (
                get_user_model()
                .objects.filter(
                    Q(pk__in=queryset.values("pk"))
                    | Q(pk__in=asignados)
                    | Q(pk__in=por_proyecto)
                )
                .order_by("last_name", "first_name", "username")
            )
        self.fields["territoriales_abordaje_comunitario"].queryset = queryset

    def popular_campos_ubicacion(self):

        def pk_formatter(value):
            return int(value) if value and value.isdigit() else None

        provincia = Provincia.objects.filter(
            pk=pk_formatter(self.data.get("provincia"))
        ).first() or getattr(self.instance, "provincia", None)

        municipio = Municipio.objects.filter(
            pk=pk_formatter(self.data.get("municipio"))
        ).first() or getattr(self.instance, "municipio", None)

        localidad = Localidad.objects.filter(
            pk=pk_formatter(self.data.get("localidad"))
        ).first() or getattr(self.instance, "localidad", None)

        if provincia:
            self.fields["provincia"].initial = Provincia.objects.get(id=provincia.id)
            self.fields["provincia"].queryset = Provincia.objects.all()
            self.fields["municipio"].queryset = Municipio.objects.filter(
                provincia=provincia
            )
        else:
            self.fields["provincia"].queryset = Provincia.objects.all()
            self.fields["municipio"].queryset = Municipio.objects.none()
            self.fields["localidad"].queryset = Localidad.objects.none()

        if municipio:
            self.fields["municipio"].initial = municipio
            self.fields["localidad"].queryset = Localidad.objects.filter(
                municipio=municipio
            )

        if localidad:
            self.fields["localidad"].initial = localidad

    def clean_cuit(self):
        cuit = self.cleaned_data.get("cuit")
        if not cuit:
            return None
        return int(cuit)

    def clean(self):
        cleaned_data = super().clean()
        cuit = cleaned_data.get("cuit")
        confirmado = cleaned_data.get("cuil_duplicado_confirmado")
        cuit_confirmado = cleaned_data.get("cuil_duplicado_confirmado_valor")

        if cuit is not None:
            exclude_pk = (
                self.instance.pk if self.instance and self.instance.pk else None
            )
            qs = Organizacion.objects.filter(cuit=cuit)
            if exclude_pk:
                qs = qs.exclude(pk=exclude_pk)

            if qs.exists() and (not confirmado or cuit_confirmado != str(cuit)):
                self.add_error(
                    "cuit",
                    forms.ValidationError(
                        "El CUIL ingresado ya está registrado en otra organización. "
                        "Revisá la advertencia y confirmá para continuar.",
                        code="cuil_duplicado_sin_confirmar",
                    ),
                )

        sin_vencimiento = cleaned_data.get("sin_vencimiento")
        if sin_vencimiento:
            cleaned_data["fecha_vencimiento"] = None
        elif not cleaned_data.get("fecha_vencimiento"):
            self.add_error(
                "fecha_vencimiento",
                "Ingresá una fecha o seleccioná Sin Vencimiento.",
            )

        seleccionados = cleaned_data.get("territoriales_abordaje_comunitario")
        existentes = (
            set(
                self.instance.territoriales_abordaje_comunitario.values_list(
                    "pk", flat=True
                )
            )
            if self.instance.pk
            else set()
        )
        asociados = {
            item["territorial"]
            for item in cleaned_data.get("asignaciones_territoriales", []) or []
        }
        if (
            seleccionados is not None
            and set(seleccionados.values_list("pk", flat=True)) - existentes - asociados
        ):
            self.add_error(
                None,
                "Para asignar un nuevo Territorial debés seleccionar también su Código de Proyecto.",
            )

        return cleaned_data

    def clean_codigos_proyecto(self):
        codigos = {
            codigo.strip()
            for codigo in (self.cleaned_data.get("codigos_proyecto") or "").split(",")
            if codigo.strip()
        }
        return sorted(codigos)

    def clean_asignaciones_territoriales(self):
        asignaciones = self.cleaned_data.get("asignaciones_territoriales") or []
        if not isinstance(asignaciones, list):
            raise forms.ValidationError("Las asignaciones deben ser una lista.")
        codigos = [
            codigo.strip()
            for codigo in self.data.get(self.add_prefix("codigos_proyecto"), "").split(
                ","
            )
            if codigo.strip()
        ]
        usuarios = self.fields["territoriales_abordaje_comunitario"].queryset
        permitidos = set(usuarios.values_list("pk", flat=True))
        resultado = []
        vistos = set()
        for item in asignaciones:
            if not isinstance(item, dict) or item.get("proyecto") not in codigos:
                raise forms.ValidationError(
                    "Seleccioná un código de proyecto de esta organización."
                )
            usuario_id = item.get("territorial")
            if (
                not isinstance(usuario_id, int)
                or isinstance(usuario_id, bool)
                or usuario_id not in permitidos
            ):
                raise forms.ValidationError(
                    "Seleccioná un territorial válido para cada proyecto."
                )
            par = (item["proyecto"], usuario_id)
            if par not in vistos:
                resultado.append(item)
                vistos.add(par)
        return resultado

    @transaction.atomic
    def save(self, commit=True):
        # El formulario nuevo no reescribe las asignaciones históricas sin
        # proyecto. Los clientes antiguos siguen conservando su contrato.
        nuevo_formato = self.add_prefix("asignaciones_territoriales") in self.data
        if nuevo_formato and self.instance.pk:
            self.cleaned_data["territoriales_abordaje_comunitario"] = (
                self.instance.territoriales_abordaje_comunitario.all()
            )
        organizacion = super().save(commit=commit)
        if commit:
            codigos = self.cleaned_data.get("codigos_proyecto", [])
            organizacion.proyectos.exclude(codigo__in=codigos).update(activo=False)
            for codigo in codigos:
                ProyectoOrganizacion.objects.update_or_create(
                    organizacion=organizacion,
                    codigo=codigo,
                    defaults={"activo": True},
                )
            if nuevo_formato:
                asignaciones = self.cleaned_data["asignaciones_territoriales"]
                for proyecto in organizacion.proyectos.all():
                    proyecto.territoriales.set(
                        [
                            item["territorial"]
                            for item in asignaciones
                            if item["proyecto"] == proyecto.codigo
                        ]
                    )
                # Al asociar explícitamente una persona a un proyecto deja de
                # ser una asignación general. Las demás asignaciones legadas
                # se conservan hasta que se elija su proyecto.
                organizacion.territoriales_abordaje_comunitario.remove(
                    *{item["territorial"] for item in asignaciones}
                )
        return organizacion

    class Meta:
        model = Organizacion
        fields = "__all__"
        widgets = {
            "fecha_vencimiento": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
        }


class FirmanteForm(forms.ModelForm):
    class Meta:
        model = Firmante
        fields = ["nombre", "rol", "cuit", "programa"]

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        cuit = cleaned_data.get("cuit")

        if rol == "aval" and not cuit:
            self.add_error("cuit", "El CUIT es obligatorio para el rol Aval")


class AvalForm(forms.ModelForm):
    class Meta:
        model = Aval
        fields = ["nombre", "cuit"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].required = False
        self.fields["cuit"].required = False


AvalFormset = inlineformset_factory(
    Organizacion, Aval, form=AvalForm, extra=1, max_num=1, can_delete=True
)
FirmanteFormset = inlineformset_factory(
    Organizacion, Firmante, form=FirmanteForm, extra=0, can_delete=True
)
