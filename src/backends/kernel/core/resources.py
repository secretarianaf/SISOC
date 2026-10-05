"""Resources de django-import-export para los modelos de ``core``.

Solo se definen los que necesitan acotar campos o mostrar relaciones por
nombre. Los catálogos de un único campo usan el ``ModelResource`` por defecto.
"""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, Widget

from core.models import (
    Localidad,
    MontoPrestacionPrograma,
    Municipio,
    Programa,
    Provincia,
    organismo_model,
)

MUNICIPIO_CAMPOS = ("id", "nombre", "provincia")
LOCALIDAD_CAMPOS = ("id", "nombre", "municipio", "provincia")
PROGRAMA_CAMPOS = ("id", "nombre", "estado", "organismo", "descripcion")
MONTO_PRESTACION_CAMPOS = (
    "id",
    "programa",
    "desayuno_valor",
    "almuerzo_valor",
    "merienda_valor",
    "cena_valor",
    "fecha_creacion",
    "fecha_modificacion",
)


class MunicipioResource(resources.ModelResource):
    provincia = fields.Field(
        column_name="provincia",
        attribute="provincia",
        widget=ForeignKeyWidget(Provincia, "nombre"),
    )

    class Meta:
        model = Municipio
        fields = MUNICIPIO_CAMPOS
        export_order = MUNICIPIO_CAMPOS


class LocalidadResource(resources.ModelResource):
    municipio = fields.Field(
        column_name="municipio",
        attribute="municipio",
        widget=ForeignKeyWidget(Municipio, "nombre"),
    )
    provincia = fields.Field(column_name="provincia", readonly=True)

    class Meta:
        model = Localidad
        fields = LOCALIDAD_CAMPOS
        export_order = LOCALIDAD_CAMPOS

    def dehydrate_provincia(self, localidad):
        municipio = getattr(localidad, "municipio", None)
        provincia = getattr(municipio, "provincia", None)
        return str(provincia) if provincia else ""


class OrganismoPorNombreWidget(Widget):
    """``organismo_id`` de Programa, importado y exportado por nombre.

    Resuelve el modelo al usarse y no al importar el módulo: este admin se
    carga también en backends que no instalan ``organizaciones``.
    """

    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        return organismo_model().objects.get(nombre=value).pk

    def render(self, value, obj=None, **kwargs):
        modelo = organismo_model()
        if value is None or modelo is None:
            return ""
        organismo = modelo.objects.filter(pk=value).first()
        return organismo.nombre if organismo else ""


class ProgramaResource(resources.ModelResource):
    organismo = fields.Field(
        column_name="organismo",
        attribute="organismo_id",
        widget=OrganismoPorNombreWidget(),
    )

    class Meta:
        model = Programa
        fields = PROGRAMA_CAMPOS
        export_order = PROGRAMA_CAMPOS


class MontoPrestacionProgramaResource(resources.ModelResource):
    """Excluye ``usuario_creador``: es dato de usuario y no aporta al análisis."""

    programa = fields.Field(
        column_name="programa",
        attribute="programa",
        widget=ForeignKeyWidget(Programa, "nombre"),
    )

    class Meta:
        model = MontoPrestacionPrograma
        fields = MONTO_PRESTACION_CAMPOS
        export_order = MONTO_PRESTACION_CAMPOS
