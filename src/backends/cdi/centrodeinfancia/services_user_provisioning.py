"""Provisionamiento automático de usuarios vinculados al dominio CDI.

El referente se identifica por DNI (o, en fichas sin DNI, por nombre y
apellido), nunca por email: el email del referente suele ser el institucional
del centro y lo comparten varias personas, incluso cuentas de otros programas.
"""

import logging
import unicodedata

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.services_accesos_cdi import asignar_responsable
from core.constants import UserGroups
from core.validators import solo_digitos
from users.models import Profile
from users.services_generate_user import DatosUsuarioDelegado, generar_usuario_delegado
from users.territorial_scope import sync_profile_territorial_scopes


logger = logging.getLogger(__name__)
User = get_user_model()


def _dni_desde(dni, cuil):
    """DNI informado o, si falta, el que está dentro del CUIL."""
    dni = solo_digitos(dni)
    if dni:
        return dni
    cuil = solo_digitos(cuil)
    return cuil[2:10].lstrip("0") if len(cuil) == 11 else ""


def _dni_referente(centro):
    return _dni_desde(centro.dni_referente, centro.cuil_referente)


def _normalizar_nombre(*partes):
    texto = unicodedata.normalize("NFKD", " ".join(p or "" for p in partes))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.lower().split())


def _nombre_referente(centro):
    return _normalizar_nombre(centro.nombre_referente, centro.apellido_referente)


def _dni_cuenta(user):
    """DNI de la cuenta: el del perfil, el del CUIL o un usuario que es un DNI.

    Las cuentas de referentes (y las de otros programas, como PNUD) usan el DNI
    como nombre de usuario.
    """
    profile = getattr(user, "profile", None)
    dni = _dni_desde(getattr(profile, "dni", ""), getattr(profile, "cuil", ""))
    if dni:
        return dni
    return user.username if user.username.isdigit() else ""


def _es_la_persona_del_referente(user, centro):
    """La cuenta es de la persona de la ficha: mismo DNI o, sin DNI, mismo nombre."""
    dni_ficha = _dni_referente(centro)
    dni_cuenta = _dni_cuenta(user)
    if dni_ficha and dni_cuenta:
        return dni_ficha == dni_cuenta
    return _normalizar_nombre(user.first_name, user.last_name) == _nombre_referente(
        centro
    )


def _usuario_del_referente(centro):
    """Cuenta existente de la persona de la ficha, o ``None`` si hay que crearla.

    Primero se busca entre los usuarios del CDI (recupera un referente histórico)
    y después, por DNI, una cuenta de la misma persona en otro programa.
    """
    accesos = AccesoCDI.objects.select_related("user__profile").filter(centro=centro)
    for acceso in accesos.order_by("pk"):
        if _es_la_persona_del_referente(acceso.user, centro):
            return acceso.user
    dni = _dni_referente(centro)
    if not dni:
        return None
    cuentas = list(
        User.objects.filter(Q(profile__dni=dni) | Q(username=dni))
        .distinct()
        .order_by("pk")[:2]
    )
    return cuentas[0] if len(cuentas) == 1 else None


def _vincular_referente_responsable(user, centro, actor):
    with transaction.atomic():
        # El CDI se bloquea antes de insertar el acceso: su FK toma un bloqueo
        # compartido y dos inserciones no deben intentar promoverlo a exclusivo.
        CentroDeInfancia.objects.select_for_update().get(pk=centro.pk)
        acceso, _ = AccesoCDI.objects.get_or_create(
            user=user, centro=centro, defaults={"creado_por": actor}
        )
        return asignar_responsable(acceso)


def crear_referente_cdi_automaticamente(
    request, centro, *, reemplaza_responsable=False
):
    """Vincula al referente de la ficha como responsable, sin comprometer el guardado.

    Sin ``reemplaza_responsable`` solo actúa si el CDI todavía no tiene usuarios
    (referente inicial). Con él, el referente cambió de persona: se crea o vincula
    su usuario como nuevo responsable y el anterior conserva su acceso.
    """
    datos_referente = {
        "first_name": (centro.nombre_referente or "").strip(),
        "last_name": (centro.apellido_referente or "").strip(),
        "email": (centro.email_referente or "").strip(),
    }
    if not datos_referente["email"]:
        messages.warning(
            request,
            "El CDI se guardó sin crear referente: falta el email del referente.",
        )
        return
    if not all(datos_referente.values()):
        messages.warning(
            request,
            "El CDI se guardó sin crear referente: complete nombre, apellido y email.",
        )
        return
    if not reemplaza_responsable and AccesoCDI.objects.filter(centro=centro).exists():
        return
    usuario = _usuario_del_referente(centro)
    if usuario:
        grupo, _ = Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)
        usuario.groups.add(grupo)
        # Si tenía un acceso suspendido o dado de baja, vuelve a estar activo.
        _vincular_referente_responsable(usuario, centro, request.user)
        messages.success(
            request,
            f"Usuario existente «{usuario.username}» asociado como referente responsable.",
        )
        return

    # Persona sin cuenta: se crea aunque su email ya lo use otra cuenta.
    try:
        resultado = generar_usuario_delegado(
            actor=request.user,
            datos=DatosUsuarioDelegado(
                **datos_referente,
                dni=_dni_referente(centro),
                cuil=solo_digitos(centro.cuil_referente),
            ),
            grupo_nombre=UserGroups.CDI_REFERENTE_CENTRO,
            vinculo_callback=lambda nuevo_usuario: _vincular_referente_responsable(
                nuevo_usuario, centro, request.user
            ),
            request=request,
            # Quien puede editar la ficha del CDI define a su referente; el
            # usuario se crea solo para este CDI.
            delegacion_autorizada=True,
            # El email suele ser institucional: si ya lo usa otra cuenta, el
            # usuario se arma con el DNI.
            usuario_dni_si_email_en_uso=True,
        )
    except ValidationError as exc:
        logger.warning(
            "No se creó referente CDI automáticamente centro_id=%s actor_id=%s: %s",
            centro.id,
            request.user.id,
            "; ".join(exc.messages),
        )
        messages.warning(
            request,
            "El CDI se guardó, pero no se pudo crear el referente automáticamente.",
        )
    except Exception:  # noqa: BLE001 - el guardado primario no debe fallar
        logger.exception(
            "Error inesperado al crear referente CDI automáticamente centro_id=%s actor_id=%s",
            centro.id,
            request.user.id,
        )
        messages.warning(
            request,
            "El CDI se guardó, pero no se pudo crear el referente automáticamente.",
        )
    else:
        if resultado["email_enviado"]:
            messages.success(
                request,
                f"Referente «{resultado['user'].username}» creado automáticamente y credenciales enviadas.",
            )
        else:
            messages.warning(
                request,
                f"Referente «{resultado['user'].username}» creado automáticamente, pero no se pudieron enviar las credenciales por email.",
            )


def _vincular_usuario_trabajador(trabajador, user):
    trabajador.usuario = user
    trabajador.save(update_fields=["usuario"])


def crear_usuario_trabajador_automaticamente(request, trabajador):
    """Vincula un usuario al trabajador sin afectar el guardado de la nómina."""
    if trabajador.usuario_id or not (trabajador.email or "").strip():
        return

    try:
        resultado = generar_usuario_delegado(
            actor=request.user,
            datos=DatosUsuarioDelegado(
                first_name=trabajador.nombre,
                last_name=trabajador.apellido,
                email=trabajador.email,
            ),
            grupo_nombre=UserGroups.CDI_TRABAJADOR,
            vinculo_callback=lambda nuevo_usuario: _vincular_usuario_trabajador(
                trabajador,
                nuevo_usuario,
            ),
            request=request,
        )
    except ValidationError as exc:
        logger.warning(
            "No se creó usuario de trabajador automáticamente trabajador_id=%s actor_id=%s: %s",
            trabajador.id,
            request.user.id,
            "; ".join(exc.messages),
        )
        messages.warning(
            request,
            "El trabajador se guardó, pero no se pudo crear su usuario automáticamente.",
        )
    except Exception:  # noqa: BLE001 - el guardado primario no debe fallar
        logger.exception(
            "Error inesperado al crear usuario de trabajador trabajador_id=%s actor_id=%s",
            trabajador.id,
            request.user.id,
        )
        messages.warning(
            request,
            "El trabajador se guardó, pero no se pudo crear su usuario automáticamente.",
        )
    else:
        trabajador.usuario = resultado["user"]
        if resultado["email_enviado"]:
            messages.success(
                request,
                f"Usuario de trabajador «{resultado['user'].username}» creado automáticamente y credenciales enviadas.",
            )
        else:
            messages.warning(
                request,
                f"Usuario de trabajador «{resultado['user'].username}» creado "
                "automáticamente, pero no se pudieron enviar las credenciales por email.",
            )


def _sincronizar_email_si_cuenta_temporal(request, user, email, tipo_usuario):
    email = (email or "").strip()
    if not user or user.email == email:
        return

    profile = getattr(user, "profile", None)
    if not getattr(profile, "must_change_password", False):
        messages.warning(
            request,
            f"No se actualizó el email del {tipo_usuario} porque ya modificó su cuenta.",
        )
        return

    user.email = email
    user.save(update_fields=["email"])
    messages.success(request, f"Email del {tipo_usuario} actualizado.")


def _cambio_persona_referente(anterior, centro):
    """El referente es otra persona si cambió el DNI o, sin DNI, nombre y apellido.

    Sin DNI, corregir solo el nombre o solo el apellido es la misma persona: si
    no, arreglar un error de tipeo le crearía otra cuenta. El email no cuenta:
    dos referentes pueden compartir el institucional.
    """
    dni_anterior = _dni_desde(
        anterior.get("dni_referente"), anterior.get("cuil_referente")
    )
    dni_actual = _dni_referente(centro)
    if dni_anterior and dni_actual:
        return dni_anterior != dni_actual
    cambio_nombre = _normalizar_nombre(
        anterior.get("nombre_referente")
    ) != _normalizar_nombre(centro.nombre_referente)
    cambio_apellido = _normalizar_nombre(
        anterior.get("apellido_referente")
    ) != _normalizar_nombre(centro.apellido_referente)
    return cambio_nombre and cambio_apellido


def _es_el_referente(user, centro, anterior, cambio_persona):
    """La cuenta es la del referente de la ficha.

    Una cuenta sin DNI (las creadas antes de identificar por DNI) que coincide
    con el nombre previo también lo es si la persona no cambió: así corregir el
    nombre en la ficha no la reemplaza por una cuenta nueva.
    """
    if _es_la_persona_del_referente(user, centro):
        return True
    return (
        not cambio_persona
        and not _dni_cuenta(user)
        and _normalizar_nombre(user.first_name, user.last_name)
        == _normalizar_nombre(
            anterior.get("nombre_referente"), anterior.get("apellido_referente")
        )
    )


def _acceso_responsable(centro):
    return (
        AccesoCDI.objects.select_related("user__profile")
        .filter(centro=centro, activo=True, es_responsable=True)
        .first()
    )


def actualizar_referente_cdi(request, centro, *, anterior):
    """Refleja en los usuarios del CDI el referente guardado en la ficha.

    ``anterior`` son los datos del referente antes de guardar la ficha.

    - CDI sin usuarios: crea el referente inicial como responsable.
    - Cambió la persona: el nuevo pasa a ser el responsable con su propia
      cuenta (existente por DNI o nueva) y el anterior conserva la suya y su
      acceso; solo el responsable nuevo puede suspenderlo o darlo de baja.
    - El responsable no es la persona de la ficha (o no hay): se recupera la
      cuenta de esa persona o se crea.
    - Misma persona con otro email: se sincroniza el email de su cuenta.
    """
    if not AccesoCDI.objects.filter(centro=centro).exists():
        crear_referente_cdi_automaticamente(request, centro)
        return
    responsable = _acceso_responsable(centro)
    cambio_persona = _cambio_persona_referente(anterior, centro)
    es_el_referente = responsable is not None and _es_el_referente(
        responsable.user, centro, anterior, cambio_persona
    )
    if cambio_persona or not es_el_referente:
        crear_referente_cdi_automaticamente(request, centro, reemplaza_responsable=True)
        responsable = _acceso_responsable(centro)
        es_el_referente = responsable is not None and _es_la_persona_del_referente(
            responsable.user, centro
        )
    email_actual = (centro.email_referente or "").strip()
    email_anterior = (anterior.get("email_referente") or "").strip()
    # Un referente que vuelve recupera su cuenta, que puede tener un email viejo
    # aunque el de la ficha sea el mismo que el del referente saliente.
    if es_el_referente and (
        cambio_persona or email_actual.lower() != email_anterior.lower()
    ):
        _sincronizar_email_si_cuenta_temporal(
            request, responsable.user, email_actual, "referente"
        )


def sincronizar_email_trabajador(request, trabajador):
    _sincronizar_email_si_cuenta_temporal(
        request,
        trabajador.usuario,
        trabajador.email,
        "trabajador",
    )


def vincular_scope_provincial_egp(nuevo_usuario, provincias):
    """Marca un EGP como territorial y lo limita a provincias completas."""
    profile, _ = Profile.objects.get_or_create(user=nuevo_usuario)
    profile.es_usuario_provincial = True
    profile.save(update_fields=["es_usuario_provincial"])
    sync_profile_territorial_scopes(
        profile,
        [
            {
                "provincia_id": provincia.id,
                "municipio_id": None,
                "localidad_id": None,
            }
            for provincia in provincias
        ],
    )
