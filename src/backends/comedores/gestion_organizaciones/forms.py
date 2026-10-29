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
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
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
    # Abordaje (#2745). Lo arma el JS del formulario. Va antes que
    # asignaciones_territoriales: su validación usa estos códigos.
    proyectos_lineas = forms.CharField(
        required=False,
        label="Proyectos",
        widget=forms.HiddenInput(),
    )
    # JSON con filas {"proyecto", "territorial"} (#2642).
    asignaciones_territoriales = forms.JSONField(
        required=False, widget=forms.HiddenInput()
    )
    programas = forms.ModelMultipleChoiceField(
        queryset=Programas.objects.none(),
        required=False,
        label="Programas",
        widget=forms.CheckboxSelectMultiple,
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
    quitar_territoriales_sin_proyecto = TerritorialesMultipleChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        label="Quitar asignaciones anteriores sin proyecto",
        widget=forms.CheckboxSelectMultiple,
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
        self._configurar_programas()
        if not self.is_bound and self.instance.pk:
            self.initial["asignaciones_territoriales"] = [
                {"proyecto": proyecto.codigo, "territorial": usuario.pk}
                for proyecto in self.instance.proyectos.filter(
                    activo=True
                ).prefetch_related("territoriales")
                for usuario in proyecto.territoriales.all()
            ]
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
        """Datos que usa el JS: programas de Abordaje, territoriales y proyectos."""
        territoriales = self.fields["territoriales_abordaje_comunitario"].queryset
        return {
            "abordaje": [
                {"id": programa.pk, "nombre": programa.nombre}
                for programa in self.programas_opciones
                if es_programa_abordaje(programa)
            ],
            "territoriales": [
                {"id": usuario.pk, "nombre": etiqueta_territorial(usuario)}
                for usuario in territoriales
            ],
            "proyectos": self.proyectos_actuales(),
            "inactivos": self.lineas_de_proyectos_quitados(),
        }

    def lineas_de_proyectos_quitados(self):
        """Línea de cada proyecto quitado, por código.

        Si se vuelve a agregar uno, el JS la propone: guardar no la pisa.
        """
        if not self.instance.pk:
            return {}
        return dict(
            LineaProyecto.objects.filter(
                proyecto__organizacion=self.instance, proyecto__activo=False
            ).values_list("proyecto__codigo", "programa_id")
        )

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
            self.fields["quitar_territoriales_sin_proyecto"].queryset = (
                self.instance.territoriales_abordaje_comunitario.order_by(
                    "last_name", "first_name", "username"
                )
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

        self._validar_programas_quitados(cleaned_data)
        self._validar_lineas_proyecto(cleaned_data)
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

    def clean_asignaciones_territoriales(self):
        asignaciones = self.cleaned_data.get("asignaciones_territoriales") or []
        if not isinstance(asignaciones, list):
            raise forms.ValidationError("Las asignaciones deben ser una lista.")
        if "proyectos_lineas" not in self.cleaned_data:
            # La lista de proyectos ya tiene su error; no se puede validar contra ella.
            return []
        codigos = {fila["codigo"] for fila in self.cleaned_data["proyectos_lineas"]}
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

    @transaction.atomic
    def save(self, commit=True):
        # El formulario nuevo no reescribe las asignaciones históricas sin
        # proyecto. Los clientes antiguos siguen conservando su contrato (#2642).
        nuevo_formato = self.add_prefix("asignaciones_territoriales") in self.data
        if nuevo_formato and self.instance.pk:
            self.cleaned_data["territoriales_abordaje_comunitario"] = (
                self.instance.territoriales_abordaje_comunitario.all()
            )
        organizacion = super().save(commit=commit)
        if commit:
            self._guardar_programas(organizacion)
            self._guardar_proyectos(organizacion)
            if nuevo_formato:
                self._guardar_territoriales(organizacion)
        return organizacion

    def _guardar_territoriales(self, organizacion):
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
        # se conservan hasta que se elija su proyecto o se quiten.
        organizacion.territoriales_abordaje_comunitario.remove(
            *{item["territorial"] for item in asignaciones},
            *self.cleaned_data.get("quitar_territoriales_sin_proyecto", []),
        )

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
