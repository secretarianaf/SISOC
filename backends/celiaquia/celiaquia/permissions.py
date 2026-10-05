"""
Módulo centralizado para validaciones de permisos en celiaquia.
"""

from django.core.exceptions import PermissionDenied
from celiaquia.models import RevisionTecnico, Subsanacion, SubsanacionEstado
from iam.services import user_has_permission_code
from users.territorial_scope import is_territorial_user, user_can_access_territory

ROLE_COORDINADOR_PERMISSION = "auth.role_coordinadorceliaquia"
ROLE_TECNICO_PERMISSION = "auth.role_tecnicoceliaquia"
ROLE_PROVINCIA_PERMISSION = "auth.role_provinciaceliaquia"


def _has_permission(user, permission_code: str) -> bool:
    return user_has_permission_code(user, permission_code)


def _legajo_in_territorial_scope(user, expediente, legajo):
    if not is_territorial_user(user):
        return False
    ciudadano = getattr(legajo, "ciudadano", None)
    return user_can_access_territory(
        user,
        provincia_id=getattr(ciudadano, "provincia_id", None),
        municipio_id=getattr(ciudadano, "municipio_id", None),
        localidad_id=getattr(ciudadano, "localidad_id", None),
        owner=getattr(expediente, "usuario_provincia", None),
    )


def _expediente_fully_in_territorial_scope(user, expediente, legajo=None):
    if legajo is not None:
        return _legajo_in_territorial_scope(user, expediente, legajo)
    if not is_territorial_user(user):
        return False
    legajos = expediente.expediente_ciudadanos.select_related("ciudadano")
    if not legajos.exists():
        return user_can_access_territory(
            user,
            provincia_id=None,
            owner=getattr(expediente, "usuario_provincia", None),
        )
    return all(
        _legajo_in_territorial_scope(user, expediente, expediente_legajo)
        for expediente_legajo in legajos
    )


def can_edit_legajo_files(user, expediente, legajo=None):
    """
    Verifica si el usuario puede editar archivos de legajo.

    Args:
        user: Usuario actual
        expediente: Expediente al que pertenece el legajo
        legajo: Legajo específico (opcional)

    Returns:
        bool: True si puede editar, False en caso contrario

    Raises:
        PermissionDenied: Si no tiene permisos
    """
    if not user.is_authenticated:
        raise PermissionDenied("Autenticación requerida.")

    is_admin = user.is_superuser
    is_coord = _has_permission(user, ROLE_COORDINADOR_PERMISSION)
    is_tec = _has_permission(user, ROLE_TECNICO_PERMISSION)
    is_prov = _has_permission(user, ROLE_PROVINCIA_PERMISSION)

    if not (is_admin or is_coord or is_tec or is_prov):
        raise PermissionDenied("Permiso denegado.")

    # Provincia: validaciones específicas
    if is_prov and not (is_admin or is_coord):
        if not _expediente_fully_in_territorial_scope(user, expediente, legajo):
            raise PermissionDenied(
                "No pertenece al alcance territorial del expediente."
            )

        # Verificar estados permitidos
        estado_nombre = getattr(getattr(expediente, "estado", None), "nombre", "")
        legajo_subsanar = legajo and legajo.revision_tecnico == RevisionTecnico.SUBSANAR

        if not (estado_nombre == "EN_ESPERA" or legajo_subsanar):
            raise PermissionDenied("No puede editar archivos en el estado actual.")

    # Técnico: debe estar asignado
    if is_tec and not (is_admin or is_coord):
        if not expediente.asignaciones_tecnicos.filter(tecnico=user).exists():
            raise PermissionDenied("No sos el técnico asignado a este expediente.")

    return True


# Estados del expediente en los que aún se pueden cargar/reemplazar los
# documentos originales del legajo. Una vez enviado a evaluación, quedan
# bloqueados.
ESTADOS_DOCS_EDITABLES = {"CREADO", "PROCESADO", "EN_ESPERA"}


def documentos_legajo_bloqueados(legajo):
    """Los documentos originales (archivo1/2/3) no se pueden reemplazar cuando el
    expediente ya fue enviado a evaluación o el legajo está en subsanación: las
    correcciones se cargan como archivos de subsanación (evidencia nueva).

    Vivía en `celiaquia/views/legajo.py`; se comparte para que la API aplique el
    mismo bloqueo que la pantalla."""
    estado = getattr(getattr(legajo.expediente, "estado", None), "nombre", "")
    if estado not in ESTADOS_DOCS_EDITABLES:
        return True
    if legajo.revision_tecnico == RevisionTecnico.SUBSANAR:
        return True
    return Subsanacion.objects.filter(
        legajo=legajo, estado=SubsanacionEstado.PENDIENTE
    ).exists()


# Estados del expediente en los que la provincia trabaja sus legajos antes de
# enviarlo a evaluación. Una vez confirmado el envío (CONFIRMACION_DE_ENVIO en
# adelante) la provincia ya no puede eliminar legajos.
ESTADOS_PROVINCIA_PRE_ENVIO = {"EN_ESPERA"}


def can_delete_legajo(user, expediente, legajo=None):
    """
    Verifica si el usuario puede eliminar un legajo del expediente.

    - Admin y coordinadores: sin restricción de estado (comportamiento actual).
    - Provincia: solo dentro de su alcance territorial y mientras el expediente
      no haya sido enviado a evaluación (estado EN_ESPERA).

    Raises:
        PermissionDenied: Si no tiene permisos para eliminar el legajo.
    """
    if not user.is_authenticated:
        raise PermissionDenied("Autenticación requerida.")

    is_admin = user.is_superuser
    is_coord = _has_permission(user, ROLE_COORDINADOR_PERMISSION)
    # Provincial por rol explícito o por alcance territorial, en línea con la
    # detección usada en las vistas (_is_provincial).
    is_prov = _has_permission(user, ROLE_PROVINCIA_PERMISSION) or is_territorial_user(
        user
    )

    if is_admin or is_coord:
        return True

    if is_prov:
        if not _expediente_fully_in_territorial_scope(user, expediente, legajo):
            raise PermissionDenied(
                "No pertenece al alcance territorial del expediente."
            )

        estado_nombre = getattr(getattr(expediente, "estado", None), "nombre", "")
        if estado_nombre not in ESTADOS_PROVINCIA_PRE_ENVIO:
            raise PermissionDenied(
                "No se pueden eliminar legajos una vez enviado el expediente a "
                "evaluación."
            )
        return True

    raise PermissionDenied("No tenés permiso para eliminar legajos.")


def can_review_legajo(user, expediente):
    """
    Verifica si el usuario puede revisar legajos (aprobar/rechazar/subsanar).
    """
    if not user.is_authenticated:
        raise PermissionDenied("Autenticación requerida.")

    is_admin = user.is_superuser
    is_coord = _has_permission(user, ROLE_COORDINADOR_PERMISSION)
    is_tec = _has_permission(user, ROLE_TECNICO_PERMISSION)

    if not (is_admin or is_coord or is_tec):
        raise PermissionDenied("Permiso denegado.")

    # Técnico: debe estar asignado
    if is_tec and not (is_admin or is_coord):
        if not expediente.asignaciones_tecnicos.filter(tecnico=user).exists():
            raise PermissionDenied("No sos el técnico asignado a este expediente.")

    return True


def can_confirm_subsanacion(user, expediente):
    """
    Verifica si el usuario puede confirmar subsanación.
    """
    if not user.is_authenticated:
        raise PermissionDenied("Autenticación requerida.")

    is_admin = user.is_superuser
    is_prov = _has_permission(user, ROLE_PROVINCIA_PERMISSION)

    if not (is_admin or is_prov):
        raise PermissionDenied(
            "No tenés permiso para confirmar la subsanación de este expediente."
        )

    # Verificar que pertenezca a la misma provincia
    if is_prov and not is_admin:
        if not _expediente_fully_in_territorial_scope(user, expediente):
            raise PermissionDenied(
                "No tenés permiso para confirmar la subsanación de este expediente."
            )

    return True


def exigir_rol_nacion_a_comentarios(user):
    """Reglas 1 y 2 de `exigir_acceso_nacion_a_comentarios`, sin el legajo.

    La vista las corre antes de buscar el legajo: si el rol no alcanza, la
    respuesta es 403 exista o no el legajo, y no revela cuales existen.
    """

    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Autenticación requerida.")

    if is_territorial_user(user):
        raise PermissionDenied("Permiso denegado.")

    if not (
        user.is_superuser
        or _has_permission(user, ROLE_COORDINADOR_PERMISSION)
        or _has_permission(user, ROLE_TECNICO_PERMISSION)
    ):
        raise PermissionDenied("Permiso denegado.")


def exigir_acceso_nacion_a_comentarios(user, legajo):
    """Quien puede leer y escribir los comentarios internos de un legajo.

    Vivia en `_resolver_legajo_para_nacion`, dentro de la vista de comentarios.
    Se extrae para que la API aplique la misma regla; duplicarla significaria
    que un usuario provincial pueda leer por la API un comentario interno que la
    pantalla le oculta hasta que se publica al subsanar o rechazar.

    Reglas, en orden:

    1. El perfil territorial define a un usuario de Provincia aunque acumule
       permisos de Nacion: no ve comentarios internos.
    2. Solo admin, coordinador o tecnico.
    3. El tecnico, ademas, tiene que estar asignado al expediente.
    """

    exigir_rol_nacion_a_comentarios(user)

    es_admin = user.is_superuser
    es_coord = _has_permission(user, ROLE_COORDINADOR_PERMISSION)
    es_tecnico = _has_permission(user, ROLE_TECNICO_PERMISSION)

    if es_tecnico and not (es_admin or es_coord):
        if not legajo.expediente.asignaciones_tecnicos.filter(tecnico=user).exists():
            raise PermissionDenied("No sos el técnico asignado a este expediente.")

    return True
