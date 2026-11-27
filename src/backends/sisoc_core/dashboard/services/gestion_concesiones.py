"""Operaciones aditivas sobre concesiones individuales de tableros.

La vista llamante debe autorizar al actor antes de invocar estas funciones.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Provincia
from dashboard.models import AudienciaTableros, ConcesionTablero
from dashboard.services.selector_cdi import validar_centros


def agregar_lote_concesiones(request, datos, *, usuario=None, audiencia=None):
    """Agrega todas las combinaciones del formulario, sin reemplazar concesiones."""
    tipo = datos["tipo"]
    if tipo == ConcesionTablero.Tipo.CDI:
        territorios = [
            {"cdi_id": pk} for pk in sorted(validar_centros(request, datos["cdis"]))
        ]
    elif tipo == ConcesionTablero.Tipo.PROVINCIA:
        territorios = [
            {"provincia_id": provincia.pk} for provincia in datos["provincias"]
        ]
    else:
        territorios = [{}]
    tableros = list(datos["tableros"])
    if len(tableros) * len(territorios) > 100:
        raise ValidationError("No se pueden agregar más de 100 asignaciones por lote.")
    with transaction.atomic():
        if usuario is not None:
            get_user_model().objects.select_for_update().get(pk=usuario.pk)
        else:
            AudienciaTableros.objects.select_for_update().get(pk=audiencia.pk)
        for tablero in tableros:
            for territorio in territorios:
                ConcesionTablero.objects.create(
                    tablero=tablero,
                    tipo=tipo,
                    usuario=usuario,
                    audiencia=audiencia,
                    **territorio,
                )


def agregar_cdis_usuario(request, usuario, tablero, ids):
    """Valida en el dueño CDI antes de guardar el lote individual."""
    validados = validar_centros(request, ids)
    _guardar_cdis(usuario, None, tablero, validados)


def agregar_cdis_audiencia(request, audiencia, tablero, ids):
    """Valida en el dueño CDI antes de guardar el lote de audiencia."""
    validados = validar_centros(request, ids)
    _guardar_cdis(None, audiencia, tablero, validados)


@transaction.atomic
def _guardar_cdis(usuario, audiencia, tablero, ids):
    if usuario is not None:
        get_user_model().objects.select_for_update().get(pk=usuario.pk)
    else:
        AudienciaTableros.objects.select_for_update().get(pk=audiencia.pk)
    for cdi_id in sorted(ids):
        ConcesionTablero.objects.create(
            tablero=tablero,
            usuario=usuario,
            audiencia=audiencia,
            tipo=ConcesionTablero.Tipo.CDI,
            cdi_id=cdi_id,
        )


@transaction.atomic
def agregar_concesiones(usuario, tablero, tipo, provincias):
    """Agrega un alcance nacional o un lote completo de provincias válidas."""
    get_user_model().objects.select_for_update().get(pk=usuario.pk)
    _agregar({"usuario": usuario}, tablero, tipo, provincias)


@transaction.atomic
def agregar_concesiones_audiencia(audiencia, tablero, tipo, provincias):
    """Agrega concesiones de una audiencia sin tocar asignaciones individuales."""
    AudienciaTableros.objects.select_for_update().get(pk=audiencia.pk)
    _agregar({"audiencia": audiencia}, tablero, tipo, provincias)


def _agregar(sujeto, tablero, tipo, provincias):
    if tipo == ConcesionTablero.Tipo.NACIONAL:
        if provincias:
            raise ValidationError("El alcance nacional no admite provincias.")
        ConcesionTablero.objects.create(tablero=tablero, tipo=tipo, **sujeto)
        return
    if tipo != ConcesionTablero.Tipo.PROVINCIA:
        raise ValidationError("El alcance seleccionado no está disponible.")
    valores = list(provincias)
    if (
        not valores
        or len(valores) > 100
        or any(
            isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0
            for valor in valores
        )
    ):
        raise ValidationError("Seleccione provincias válidas.")
    ids = set(valores)
    if len(ids) != len(valores):
        raise ValidationError("No repita provincias.")
    validas = set(Provincia.objects.filter(pk__in=ids).values_list("pk", flat=True))
    if ids != validas:
        raise ValidationError("Una o más provincias no existen.")
    for provincia_id in sorted(ids):
        ConcesionTablero.objects.create(
            tablero=tablero, tipo=tipo, provincia_id=provincia_id, **sujeto
        )


@transaction.atomic
def revocar_concesion(usuario, tablero, concesion_id):
    """Revoca una asignación individual sin modificar concesiones de audiencias."""
    get_user_model().objects.select_for_update().get(pk=usuario.pk)
    _revocar({"usuario": usuario, "audiencia__isnull": True}, tablero, concesion_id)


@transaction.atomic
def revocar_concesion_audiencia(audiencia, tablero, concesion_id):
    """Revoca solo una concesión perteneciente a la audiencia indicada."""
    AudienciaTableros.objects.select_for_update().get(pk=audiencia.pk)
    _revocar({"audiencia": audiencia, "usuario__isnull": True}, tablero, concesion_id)


def _revocar(sujeto, tablero, concesion_id):
    concesion = ConcesionTablero.objects.filter(
        pk=concesion_id, tablero=tablero, **sujeto
    ).first()
    if concesion is None:
        raise ValidationError("La asignación no existe.")
    concesion.delete()
