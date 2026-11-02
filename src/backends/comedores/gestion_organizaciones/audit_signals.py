"""Eventos de auditoría de Firmante (antes en organizaciones.audit_signals) y de
los datos por programa de la organización (#2745)."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from audittrail.api import (
    ACTION_CREATE,
    ACTION_DELETE,
    ACTION_UPDATE,
    registrar_evento,
)
from core.soft_delete.signals import post_soft_delete
from gestion_organizaciones.models import (
    ConvenioProyecto,
    DatosRegionOrganizacion,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
)
from organizaciones.audit_signals import (
    PREVIOUS_STATE_ATTR,
    _registrar_baja_relacionada,
)


@receiver(pre_save, sender=Firmante)
def cache_firmante_state(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        setattr(
            instance,
            PREVIOUS_STATE_ATTR,
            sender.objects.select_related("rol", "organizacion").get(pk=instance.pk),
        )
    except sender.DoesNotExist:
        setattr(instance, PREVIOUS_STATE_ATTR, None)


@receiver(post_save, sender=Firmante)
def registrar_cambios_firmante(sender, instance, created: bool, **kwargs):
    if not instance.organizacion:
        return
    if created:
        registrar_evento(
            instance.organizacion,
            {"Firmante": [None, str(instance)]},
            ACTION_CREATE,
        )
        return
    previous = getattr(instance, PREVIOUS_STATE_ATTR, None)
    changes = {}
    if previous:
        if previous.nombre != instance.nombre:
            changes["Firmante: Nombre"] = [previous.nombre, instance.nombre]
        if previous.cuit != instance.cuit:
            changes["Firmante: CUIT"] = [previous.cuit, instance.cuit]
        if previous.rol_id != instance.rol_id:
            changes["Firmante: Rol"] = [
                str(previous.rol) if previous.rol else None,
                str(instance.rol) if instance.rol else None,
            ]
    if hasattr(instance, PREVIOUS_STATE_ATTR):
        delattr(instance, PREVIOUS_STATE_ATTR)
    if changes:
        registrar_evento(instance.organizacion, changes, ACTION_UPDATE)


@receiver(post_soft_delete, sender=Firmante)
@receiver(post_delete, sender=Firmante)
def registrar_baja_firmante(sender, instance, **kwargs):
    _registrar_baja_relacionada(instance, "Firmante")


# Datos por programa de la organización (#2745): el evento se registra en el
# Historial de la organización, directa o a través del proyecto.
_AUDITADOS = {
    ProgramaOrganizacion: ("Programa", ("programa",)),
    LineaProyecto: ("Línea de proyecto", ("programa",)),
    DatosRegionOrganizacion: ("Datos de región", ("region", "subzona")),
    ConvenioProyecto: (
        "Convenio",
        (
            "numero",
            "fecha",
            "meses",
            "monto_total",
            "componente_alimentario",
            "componente_gastos_generales",
            "componente_siph",
            "componente_gasto_bancario",
            "imprevistos",
        ),
    ),
}


def _organizacion_de(instance):
    organizacion = getattr(instance, "organizacion", None)
    if organizacion is None:
        organizacion = getattr(
            getattr(instance, "proyecto", None), "organizacion", None
        )
    return organizacion


def _valor(instance, campo):
    valor = getattr(instance, campo, None)
    return None if valor is None else str(valor)


def cache_estado_programa(sender, instance, **kwargs):
    if not instance.pk:
        return
    setattr(
        instance, PREVIOUS_STATE_ATTR, sender.objects.filter(pk=instance.pk).first()
    )


def registrar_cambios_programa(sender, instance, created: bool, **kwargs):
    organizacion = _organizacion_de(instance)
    if not organizacion:
        return
    etiqueta, campos = _AUDITADOS[sender]
    if created:
        registrar_evento(organizacion, {etiqueta: [None, str(instance)]}, ACTION_CREATE)
        return
    previous = getattr(instance, PREVIOUS_STATE_ATTR, None)
    if hasattr(instance, PREVIOUS_STATE_ATTR):
        delattr(instance, PREVIOUS_STATE_ATTR)
    if previous is None:
        return
    changes = {
        f"{etiqueta}: {sender._meta.get_field(campo).verbose_name}": [
            _valor(previous, campo),
            _valor(instance, campo),
        ]
        for campo in campos
        if _valor(previous, campo) != _valor(instance, campo)
    }
    if changes:
        registrar_evento(organizacion, changes, ACTION_UPDATE)


def registrar_baja_programa(sender, instance, **kwargs):
    organizacion = _organizacion_de(instance)
    if not organizacion:
        return
    etiqueta, _ = _AUDITADOS[sender]
    registrar_evento(
        organizacion, {etiqueta: [str(instance), "Eliminado"]}, ACTION_DELETE
    )


for _modelo in _AUDITADOS:
    pre_save.connect(
        cache_estado_programa,
        sender=_modelo,
        dispatch_uid=f"audit_pre_{_modelo.__name__}",
    )
    post_save.connect(
        registrar_cambios_programa,
        sender=_modelo,
        dispatch_uid=f"audit_post_{_modelo.__name__}",
    )
    post_delete.connect(
        registrar_baja_programa,
        sender=_modelo,
        dispatch_uid=f"audit_del_{_modelo.__name__}",
    )
