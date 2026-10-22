"""Catálogo de escuelas en el backoffice: listado, alta, edición y búsqueda.

El listado se pagina del lado del servidor (el padrón tiene ~64.500
escuelas). El alta y la edición guardan los textos que lee la app
(``localidad`` y ``distrito``) a partir de la localidad vinculada y limpian
la marca "a revisar": el formulario exige localidad de SISOC y mail válido.
"""

from django.db.models import Q

from inspecciones.models import Escuela
from inspecciones.services.geografia import etiqueta_localidad, textos_de_ubicacion

MIN_BUSQUEDA = 3
MAX_RESULTADOS = 20


def filtro_de_texto(texto):
    """Nombre, Cueanexo o domicilio, por texto contenido.

    El Cueanexo también por contenido y no por prefijo: lleva el 0 inicial y
    quien busca suele escribirlo sin él (``60556200`` encuentra ``060556200``).
    """
    texto = (texto or "").strip()
    if not texto:
        return Q()
    filtro = Q(nombre__icontains=texto) | Q(domicilio__icontains=texto)
    if texto.isdigit():
        filtro |= Q(cue__contains=texto) | Q(codigo__contains=texto)
    return filtro


def listar_escuelas(*, texto="", provincia_id=None, localidad_id=None, a_revisar=False):
    queryset = Escuela.objects.select_related(
        "provincia", "localidad_vinculada__municipio"
    ).filter(filtro_de_texto(texto))
    if provincia_id:
        queryset = queryset.filter(provincia_id=provincia_id)
    if localidad_id:
        queryset = queryset.filter(localidad_vinculada_id=localidad_id)
    if a_revisar:
        queryset = queryset.filter(a_revisar=True)
    return queryset.order_by("nombre", "id")


def contar_a_revisar(*, provincia_id=None):
    queryset = Escuela.objects.filter(a_revisar=True)
    if provincia_id:
        queryset = queryset.filter(provincia_id=provincia_id)
    return queryset.count()


def escuela_con_cueanexo(cueanexo, *, excluir_id=None):
    """Escuela que ya usa el Cueanexo (en ``codigo`` o ``cue``), o ``None``."""
    if not cueanexo:
        return None
    queryset = Escuela.all_objects.filter(Q(codigo=cueanexo) | Q(cue=cueanexo))
    if excluir_id:
        queryset = queryset.exclude(pk=excluir_id)
    return queryset.order_by("deleted_at").first()


def guardar_escuela(escuela, datos):
    """Alta o edición desde el formulario del backoffice.

    ``datos`` es el ``cleaned_data`` de ``EscuelaForm``. En el alta el
    Cueanexo es también el ``codigo``; en la edición el ``codigo`` no cambia.
    """
    localidad = datos["localidad"]
    texto, distrito = textos_de_ubicacion(localidad)
    if escuela.pk is None:
        escuela.codigo = datos["cueanexo"]
        escuela.localidad_original = localidad.nombre
        escuela.jurisdiccion_original = datos["provincia"].nombre
    escuela.cue = datos["cueanexo"]
    escuela.nombre = datos["nombre"]
    escuela.provincia = datos["provincia"]
    escuela.localidad_vinculada = localidad
    escuela.localidad = texto
    escuela.distrito = distrito
    escuela.domicilio = datos["domicilio"]
    escuela.cp = datos["cp"]
    escuela.telefono = datos["telefono"]
    escuela.mail = datos["mail"]
    escuela.a_revisar = False
    escuela.motivos_revision = []
    escuela.save()
    return escuela


def opcion_escuela(escuela):
    """Opción de Select2: nombre, y Cueanexo con la localidad debajo."""
    provincia = escuela.provincia.nombre if escuela.provincia_id else ""
    detalle = " · ".join(
        parte for parte in (escuela.cueanexo, escuela.localidad, provincia) if parte
    )
    return {"id": escuela.pk, "text": escuela.nombre, "detalle": detalle}


def opcion_escuela_por_id(escuela_id):
    """Opción inicial del Select2 del filtro (``None`` si no hay o no existe)."""
    if not escuela_id:
        return None
    escuela = Escuela.objects.select_related("provincia").filter(pk=escuela_id).first()
    return opcion_escuela(escuela) if escuela else None


def buscar_escuelas_select(texto):
    """Para el alta de asignaciones: desde 3 letras, hasta 20 resultados."""
    texto = (texto or "").strip()
    if len(texto) < MIN_BUSQUEDA:
        return []
    escuelas = (
        Escuela.objects.select_related("provincia")
        .filter(filtro_de_texto(texto))
        .order_by("nombre", "id")[:MAX_RESULTADOS]
    )
    return [opcion_escuela(escuela) for escuela in escuelas]


def opcion_localidad(escuela):
    """Localidad actual de la escuela como opción inicial del Select2."""
    localidad = escuela.localidad_vinculada
    if localidad is None:
        return None
    municipio = localidad.municipio.nombre if localidad.municipio_id else ""
    return {"id": localidad.pk, "text": etiqueta_localidad(localidad.nombre, municipio)}
