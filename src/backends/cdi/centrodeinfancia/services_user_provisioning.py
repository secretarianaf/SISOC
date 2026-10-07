"""Provisionamiento automático de usuarios vinculados al dominio CDI."""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction

from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.services_accesos_cdi import asignar_responsable
from core.constants import UserGroups
from users.models import Profile
from users.services_generate_user import DatosUsuarioDelegado, generar_usuario_delegado
from users.territorial_scope import sync_profile_territorial_scopes


logger = logging.getLogger(__name__)
User = get_user_model()


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
    usuarios_existentes = list(
        User.objects.filter(email__iexact=datos_referente["email"]).order_by("pk")[:2]
    )
    if len(usuarios_existentes) == 1:
        usuario = usuarios_existentes[0]
        grupo, _ = Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)
        usuario.groups.add(grupo)
        # Si tenía un acceso suspendido o dado de baja, vuelve a estar activo.
        _vincular_referente_responsable(usuario, centro, request.user)
        messages.success(
            request,
            f"Usuario existente «{usuario.username}» asociado como referente responsable.",
        )
        return
    if usuarios_existentes:
        logger.warning(
            "No se vinculó referente CDI por email ambiguo centro_id=%s email=%s",
            centro.id,
            datos_referente["email"],
        )
        messages.warning(
            request,
            "El CDI se guardó sin vincular referente: el email está asociado a más de un usuario.",
        )
        return

    try:
        resultado = generar_usuario_delegado(
            actor=request.user,
            datos=DatosUsuarioDelegado(**datos_referente),
            grupo_nombre=UserGroups.CDI_REFERENTE_CENTRO,
            vinculo_callback=lambda nuevo_usuario: _vincular_referente_responsable(
                nuevo_usuario, centro, request.user
            ),
            request=request,
            # Quien puede editar la ficha del CDI define a su referente; el
            # usuario se crea solo para este CDI.
            delegacion_autorizada=True,
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


def _cambio_persona_referente(dni_anterior, dni_actual):
    """El referente es otra persona si cambió el DNI.

    Sin DNI anterior (fichas previas) no se puede saber: se toma como la misma
    persona y, si cambió el email, se sincroniza como antes.
    """
    anterior = "".join(ch for ch in str(dni_anterior or "") if ch.isdigit())
    actual = "".join(ch for ch in str(dni_actual or "") if ch.isdigit())
    return bool(anterior and actual and anterior != actual)


def actualizar_referente_cdi(request, centro, *, dni_anterior, email_anterior):
    """Refleja en los usuarios del CDI el referente guardado en la ficha.

    - CDI sin usuarios: crea el referente inicial como responsable.
    - Cambió la persona (otro DNI): el nuevo pasa a ser el responsable y el
      anterior conserva su acceso; solo el responsable nuevo puede suspenderlo o
      darlo de baja. No se toca el email de la cuenta anterior.
    - Misma persona con otro email: se sincroniza el email de su cuenta.
    """
    if not AccesoCDI.objects.filter(centro=centro).exists():
        crear_referente_cdi_automaticamente(request, centro)
        return
    if _cambio_persona_referente(dni_anterior, centro.dni_referente):
        crear_referente_cdi_automaticamente(request, centro, reemplaza_responsable=True)
        return
    if not AccesoCDI.objects.filter(
        centro=centro, activo=True, es_responsable=True
    ).exists():
        # Recuperar la cuenta de la misma persona antes de sincronizar el email;
        # buscar solo por el email nuevo podría crear otra cuenta innecesariamente.
        candidatos = list(
            AccesoCDI.objects.filter(
                centro=centro,
                user__email__iexact=(
                    email_anterior or centro.email_referente or ""
                ).strip(),
            )[:2]
        )
        if len(candidatos) == 1:
            asignar_responsable(candidatos[0])
        else:
            crear_referente_cdi_automaticamente(
                request, centro, reemplaza_responsable=True
            )
    email_actual = (centro.email_referente or "").strip()
    if email_actual.lower() != (email_anterior or "").strip().lower():
        sincronizar_email_referente_cdi(request, centro, email_anterior)


def sincronizar_email_referente_cdi(request, centro, email_anterior):
    """Actualiza solo el acceso que corresponde al email anterior del referente."""
    accesos = AccesoCDI.objects.select_related("user", "user__profile").filter(
        centro=centro,
        activo=True,
    )
    # El responsable es el referente de la ficha: es la cuenta a sincronizar.
    candidatos = list(accesos.filter(es_responsable=True)[:2])
    if not candidatos and email_anterior:
        candidatos = list(
            accesos.filter(user__email__iexact=(email_anterior or "").strip())[:2]
        )
    if not candidatos:
        candidatos = list(accesos.order_by("pk")[:2])
    acceso = candidatos[0] if len(candidatos) == 1 else None
    if acceso:
        _sincronizar_email_si_cuenta_temporal(
            request,
            acceso.user,
            centro.email_referente,
            "referente",
        )
    elif candidatos:
        logger.warning(
            "No se sincronizó email de referente por accesos ambiguos centro_id=%s",
            centro.id,
        )
        messages.warning(
            request,
            "No se actualizó el email del referente porque el CDI tiene múltiples accesos activos.",
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
