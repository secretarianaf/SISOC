import json

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.forms import inlineformset_factory
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    Aval,
    SubtipoEntidad,
)
from gestion_organizaciones.models import (
    ConvenioProyecto,
    DatosRegionOrganizacion,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
    RegionAbordaje,
    SubzonaAbordaje,
)
from gestion_organizaciones.services.programas import (
    asociaciones_de_programa,
    es_programa_abordaje,
    ordenar_programas,
    programas_de_organizacion,
    programas_del_legajo,
)
from core.models import Municipio, Provincia, Localidad
from comedores.models import Programas
from comedores.territoriales_pnud import (
    etiqueta_territorial,
    usuarios_territoriales_pnud,
)
from comedores.utils import es_programa_linea_tradicional


class TerritorialesMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return etiqueta_territorial(obj)


class OrganizacionForm(forms.ModelForm):
    # JSON con filas {"codigo", "linea"}; la línea es el id del programa de
    # Abordaje (#2745). Lo arma el JS del formulario.
    proyectos_lineas = forms.CharField(
        required=False,
        label="Proyectos",
        widget=forms.HiddenInput(),
    )
    programas = forms.ModelMultipleChoiceField(
        queryset=Programas.objects.none(),
        required=False,
        label="Programas",
        widget=forms.CheckboxSelectMultiple,
    )
    region = forms.ModelChoiceField(
        queryset=RegionAbordaje.objects.all(),
        required=False,
        label="Región",
    )
    subzona = forms.ModelChoiceField(
        queryset=SubzonaAbordaje.objects.select_related("region"),
        required=False,
        label="Aglomerado/Subzona",
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
        self._configurar_programas()
        self._configurar_region()
        if not self.is_bound and self.instance.pk:
            self.initial["proyectos_lineas"] = json.dumps(
                [
                    {"codigo": fila["codigo"], "linea": fila["linea"]}
                    for fila in self.proyectos_actuales()
                ]
            )

    def _configurar_programas(self):
        # Los programas ya cargados siguen como opción aunque no sean de los
        # tres del legajo (p. ej. PNUD): si no, guardar los quitaría.
        self.programas_asignados = programas_de_organizacion(self.instance)
        opciones = {programa.pk: programa for programa in programas_del_legajo()}
        opciones.update(
            {programa.pk: programa for programa in self.programas_asignados}
        )
        self.programas_opciones = ordenar_programas(opciones.values())
        self.fields["programas"].queryset = Programas.objects.filter(pk__in=opciones)
        if not self.is_bound:
            self.initial["programas"] = [p.pk for p in self.programas_asignados]

    def _configurar_region(self):
        datos = self._datos_region_actuales()
        if datos and not self.is_bound:
            self.initial["region"] = datos.region_id
            self.initial["subzona"] = datos.subzona_id

    def _datos_region_actuales(self):
        if not self.instance.pk:
            return None
        return DatosRegionOrganizacion.objects.filter(
            organizacion=self.instance
        ).first()

    def proyectos_actuales(self):
        """Proyectos activos con su línea y si tienen convenio cargado."""
        if not self.instance.pk:
            return []
        return [
            {
                "id": proyecto.pk,
                "codigo": proyecto.codigo,
                "linea": getattr(getattr(proyecto, "linea", None), "programa_id", None),
                "convenio": hasattr(proyecto, "convenio"),
            }
            for proyecto in self.instance.proyectos.filter(activo=True)
            .select_related("linea", "convenio")
            .order_by("codigo")
        ]

    def datos_formulario(self):
        """Datos que usa el JS: programas de Abordaje, subzonas y proyectos."""
        return {
            "abordaje": [
                {"id": programa.pk, "nombre": programa.nombre}
                for programa in self.programas_opciones
                if es_programa_abordaje(programa)
            ],
            "subzonas": [
                {
                    "id": subzona.pk,
                    "nombre": subzona.nombre,
                    "region": subzona.region_id,
                }
                for subzona in self.fields["subzona"].queryset
            ],
            "proyectos": self.proyectos_actuales(),
        }

    def _configurar_territoriales(self):
        # Los ya asignados siguen siendo opciones aunque hayan perdido el rol:
        # si no, guardar el legajo los quitaría sin que nadie lo haya pedido.
        queryset = usuarios_territoriales_pnud()
        if self.instance.pk:
            asignados = self.instance.territoriales_abordaje_comunitario.values("pk")
            queryset = (
                get_user_model()
                .objects.filter(Q(pk__in=queryset.values("pk")) | Q(pk__in=asignados))
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

        self._validar_programas_quitados(cleaned_data)
        self._validar_lineas_proyecto(cleaned_data)
        self._validar_region(cleaned_data)
        return cleaned_data

    def clean_proyectos_lineas(self):
        crudo = (self.cleaned_data.get("proyectos_lineas") or "").strip()
        if not crudo:
            return []
        try:
            filas = json.loads(crudo)
        except ValueError as error:
            raise forms.ValidationError(
                "No se pudo leer la lista de proyectos."
            ) from error
        if not isinstance(filas, list):
            raise forms.ValidationError("No se pudo leer la lista de proyectos.")

        proyectos = {}
        for fila in filas:
            if not isinstance(fila, dict):
                raise forms.ValidationError("No se pudo leer la lista de proyectos.")
            codigo = str(fila.get("codigo") or "").strip()
            if not codigo:
                continue
            if len(codigo) > 255:
                raise forms.ValidationError(
                    f"El código {codigo[:20]}… supera los 255 caracteres."
                )
            linea = fila.get("linea")
            try:
                linea = int(linea) if linea not in (None, "") else None
            except (TypeError, ValueError) as error:
                raise forms.ValidationError(
                    f"La línea del proyecto {codigo} no es válida."
                ) from error
            proyectos[codigo] = {"codigo": codigo, "linea": linea}
        return [proyectos[codigo] for codigo in sorted(proyectos)]

    def _validar_programas_quitados(self, cleaned_data):
        if "programas" not in cleaned_data:
            return
        elegidos = {programa.pk for programa in cleaned_data["programas"]}
        for programa in self.programas_asignados:
            if programa.pk in elegidos:
                continue
            asociaciones = asociaciones_de_programa(self.instance, programa)
            if asociaciones:
                detalle = ", ".join(
                    f"{total} {clave}" for clave, total in asociaciones.items()
                )
                self.add_error(
                    "programas",
                    f"No se puede quitar {programa}: tiene {detalle} asociados.",
                )

    def _validar_lineas_proyecto(self, cleaned_data):
        if "proyectos_lineas" not in cleaned_data or "programas" not in cleaned_data:
            return
        elegidos = list(cleaned_data["programas"])
        lineas_elegidas = {p.pk: p for p in elegidos if es_programa_abordaje(p)}
        lineas_validas = {
            p.pk: p for p in Programas.objects.all() if es_programa_abordaje(p)
        }
        convenios = (
            {
                convenio.proyecto.codigo: convenio
                for convenio in ConvenioProyecto.objects.filter(
                    proyecto__organizacion=self.instance,
                    imprevistos__isnull=False,
                ).select_related("proyecto")
            }
            if self.instance.pk
            else {}
        )

        for fila in cleaned_data["proyectos_lineas"]:
            codigo, linea = fila["codigo"], fila["linea"]
            if linea is not None and linea not in lineas_validas:
                self.add_error(
                    "proyectos_lineas",
                    f"La línea del proyecto {codigo} debe ser Línea Secos o "
                    "Línea Tradicional.",
                )
                continue
            # Sin programas cargados no se exige la línea (definición 22).
            if elegidos:
                if not lineas_elegidas:
                    self.add_error(
                        "proyectos_lineas",
                        f"El proyecto {codigo} necesita una línea de Abordaje "
                        "Comunitario: elegí el programa o quitá el proyecto.",
                    )
                    continue
                if linea is None:
                    self.add_error(
                        "proyectos_lineas", f"Elegí la línea del proyecto {codigo}."
                    )
                    continue
                if linea not in lineas_elegidas:
                    self.add_error(
                        "proyectos_lineas",
                        f"La línea del proyecto {codigo} no está entre los "
                        "programas elegidos.",
                    )
                    continue
            if (
                codigo in convenios
                and linea is not None
                and not es_programa_linea_tradicional(lineas_validas[linea])
            ):
                self.add_error(
                    "proyectos_lineas",
                    f"El convenio del proyecto {codigo} tiene Imprevistos, que "
                    "solo aplica a Línea Tradicional.",
                )

    def _validar_region(self, cleaned_data):
        region = cleaned_data.get("region")
        subzona = cleaned_data.get("subzona")
        if region and subzona and subzona.region_id != region.pk:
            self.add_error("subzona", "La subzona elegida no pertenece a la región.")
        elif bool(region) != bool(subzona):
            campo = "subzona" if region else "region"
            self.add_error(campo, "Elegí la región y la subzona.")
        elif not region and self._datos_region_actuales():
            self.add_error(
                "region",
                "La región y la subzona ya cargadas no se pueden dejar vacías.",
            )

    def save(self, commit=True):
        with transaction.atomic():
            organizacion = super().save(commit=commit)
            if commit:
                self._guardar_programas(organizacion)
                self._guardar_proyectos(organizacion)
                self._guardar_region(organizacion)
        return organizacion

    def _guardar_programas(self, organizacion):
        if "programas" not in self.cleaned_data:
            return
        elegidos = {programa.pk for programa in self.cleaned_data["programas"]}
        actuales = {
            fila.programa_id: fila
            for fila in ProgramaOrganizacion.objects.filter(organizacion=organizacion)
        }
        for programa_id in elegidos - set(actuales):
            ProgramaOrganizacion.objects.create(
                organizacion=organizacion, programa_id=programa_id
            )
        # Solo llega acá un programa sin datos asociados (_validar_programas_quitados);
        # la baja queda en Historial.
        for programa_id in set(actuales) - elegidos:
            actuales[programa_id].delete()

    def _guardar_proyectos(self, organizacion):
        proyectos = self.cleaned_data.get("proyectos_lineas", [])
        codigos = [fila["codigo"] for fila in proyectos]
        # Los proyectos que se quitan se desactivan; su línea y convenio quedan.
        organizacion.proyectos.exclude(codigo__in=codigos).update(activo=False)
        for fila in proyectos:
            proyecto, _ = ProyectoOrganizacion.objects.update_or_create(
                organizacion=organizacion,
                codigo=fila["codigo"],
                defaults={"activo": True},
            )
            if fila["linea"] is None:
                continue
            linea = LineaProyecto.objects.filter(proyecto=proyecto).first()
            if linea is None:
                LineaProyecto.objects.create(
                    proyecto=proyecto, programa_id=fila["linea"]
                )
            elif linea.programa_id != fila["linea"]:
                linea.programa_id = fila["linea"]
                linea.save()

    def _guardar_region(self, organizacion):
        region = self.cleaned_data.get("region")
        subzona = self.cleaned_data.get("subzona")
        if not (region and subzona):
            return
        datos = DatosRegionOrganizacion.objects.filter(
            organizacion=organizacion
        ).first()
        if datos is None:
            DatosRegionOrganizacion.objects.create(
                organizacion=organizacion, region=region, subzona=subzona
            )
        elif (datos.region_id, datos.subzona_id) != (region.pk, subzona.pk):
            datos.region = region
            datos.subzona = subzona
            datos.save()

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organizacion = getattr(self.instance, "organizacion", None)
        if organizacion is not None:
            self.limitar_programas(organizacion)

    def limitar_programas(self, organizacion):
        """Ofrece solo los programas de la organización (#2745).

        Sin programas cargados se ofrecen todos, como hasta ahora
        (definición 22). El programa actual del firmante se conserva.
        """
        programas = programas_de_organizacion(organizacion)
        if not programas:
            return
        ids = {programa.pk for programa in programas}
        if self.instance.programa_id:
            ids.add(self.instance.programa_id)
        self.fields["programa"].queryset = Programas.objects.filter(pk__in=ids)

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        cuit = cleaned_data.get("cuit")

        if rol == "aval" and not cuit:
            self.add_error("cuit", "El CUIT es obligatorio para el rol Aval")


class ConvenioProyectoForm(forms.ModelForm):
    """Datos de Convenio de un proyecto. Imprevistos solo en Línea Tradicional."""

    class Meta:
        model = ConvenioProyecto
        exclude = ["proyecto"]
        widgets = {
            "fecha": forms.DateInput(
                attrs={"type": "date", "class": "form-control"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, proyecto, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.proyecto = proyecto
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        linea = getattr(proyecto, "linea", None)
        self.permite_imprevistos = bool(
            linea and es_programa_linea_tradicional(linea.programa)
        )
        if not self.permite_imprevistos:
            del self.fields["imprevistos"]
        # Los montos se dibujan a mano (con el prefijo $), sin crispy.
        for nombre in ["monto_total", *self.campos_monto()]:
            self.fields[nombre].widget.attrs.update(
                {"class": "form-control", "inputmode": "decimal", "min": "0"}
            )

    def campos_monto(self):
        """Componentes del convenio presentes en el formulario, en orden."""
        return [
            nombre
            for nombre in (
                "componente_alimentario",
                "componente_gastos_generales",
                "componente_siph",
                "componente_gasto_bancario",
                "imprevistos",
            )
            if nombre in self.fields
        ]

    def componentes(self):
        return [self[nombre] for nombre in self.campos_monto()]


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
