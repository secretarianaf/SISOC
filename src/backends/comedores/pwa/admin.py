from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from unfold.contrib.filters.admin import (
    FieldTextFilter,
    RangeDateTimeFilter,
)

from comedores.models import Comedor
from core.admin_base import SisocModelAdmin, SoloLecturaAdminMixin
from core.admin_operaciones import Operacion, OperacionesAdminMixin
from pwa.models import (
    AccesoComedorPWA,
    AccesoOrganizacionPWA,
    ActividadEspacioPWA,
    AuditoriaOperacionPWA,
    AuditAccesoComedorPWA,
    CatalogoActividadPWA,
    ColaboradorEspacioPWA,
    CoordinadorEquipoTecnicoPWA,
    InscriptoActividadEspacioPWA,
    LecturaMensajePWA,
    NominaEspacioPWA,
    PushSubscriptionPWA,
    RegistroAsistenciaNominaPWA,
)
from pwa.services.accesos import deactivate_coordinador_equipo_tecnico_pwa_access
from pwa.services.actividades_service import (
    bloquear_actividades_espacio,
    soft_delete_actividad_espacio,
)

# ``Nomina.__str__`` usa el ciudadano y el comedor (directo o de la admisión).
NOMINA_RELACIONADAS = (
    "nomina__ciudadano",
    "nomina__comedor",
    "nomina__admision__comedor",
)


@admin.register(AuditoriaOperacionPWA)
class AuditoriaOperacionPWAAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "fecha_evento",
        "accion",
        "entidad",
        "entidad_id",
        "comedor",
        "user",
    )
    list_select_related = ("comedor", "user")
    list_filter = (
        "accion",
        "entidad",
        ("fecha_evento", RangeDateTimeFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = ("entidad", "entidad_id", "user__username", "comedor__nombre")
    readonly_fields = (
        "fecha_evento",
        "accion",
        "entidad",
        "entidad_id",
        "comedor",
        "user",
        "snapshot_antes",
        "snapshot_despues",
        "metadata",
    )


@admin.register(LecturaMensajePWA)
class LecturaMensajePWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comunicado",
        "comedor",
        "user",
        "visto",
        "fecha_visto",
        "fecha_creacion",
    )
    list_select_related = ("comunicado", "comedor", "user")
    list_filter = (
        "visto",
        ("fecha_visto", RangeDateTimeFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "comunicado__titulo",
        "comedor__nombre",
        "user__username",
    )
    raw_id_fields = ("comunicado", "comedor", "user")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


@admin.register(PushSubscriptionPWA)
class PushSubscriptionPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "user",
        "activo",
        "fecha_actualizacion",
        "fecha_baja",
    )
    list_select_related = ("user",)
    list_filter = ("activo", ("fecha_baja", RangeDateTimeFilter))
    search_fields = ("user__username", "endpoint", "user_agent")
    raw_id_fields = ("user",)
    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
        "fecha_baja",
    )


@admin.register(ColaboradorEspacioPWA)
class ColaboradorEspacioPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "comedor",
        "apellido",
        "nombre",
        "dni",
        "telefono",
        "email",
        "rol_funcion",
        "activo",
        "fecha_creacion",
    )
    list_select_related = ("comedor",)
    list_filter = (
        "activo",
        ("fecha_creacion", RangeDateTimeFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "nombre",
        "apellido",
        "dni",
        "email",
        "telefono",
        "rol_funcion",
    )
    raw_id_fields = ("comedor",)
    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
        "fecha_baja",
        "creado_por",
        "actualizado_por",
    )


@admin.register(CatalogoActividadPWA)
class CatalogoActividadPWAAdmin(SisocModelAdmin):
    list_display = ("id", "categoria", "actividad", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("categoria", "actividad")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


def baja_actividad_pwa(actividad, usuario, _datos):
    return soft_delete_actividad_espacio(actividad=actividad, actor=usuario)


class ActividadEspacioAdminForm(forms.ModelForm):
    class Meta:
        model = ActividadEspacioPWA
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        destino = datos.get("comedor")
        if destino is None:
            return datos
        origen = self.instance.comedor_id
        ids = {destino.pk}
        if origen is not None:
            ids.add(origen)
        if ids != Comedor.bloquear_para_actividades(ids) or (
            self.instance.pk is not None
            and self.instance.pk
            not in bloquear_actividades_espacio(
                actividad_ids={self.instance.pk}, comedor_id=origen
            )
        ):
            raise ValidationError(
                "El comedor o la actividad cambió. Recargá el formulario."
            )
        return datos


@admin.register(ActividadEspacioPWA)
class ActividadEspacioPWAAdmin(OperacionesAdminMixin, SisocModelAdmin):
    form = ActividadEspacioAdminForm
    operaciones = (
        Operacion(
            slug="baja",
            titulo="Dar de baja actividad PWA",
            descripcion="También desactiva las inscripciones activas.",
            ejecutar=baja_actividad_pwa,
            campo_estado="activo",
            motivo_obligatorio=True,
            destructiva=True,
            icono="event_busy",
        ),
    )
    list_display = (
        "id",
        "comedor",
        "catalogo_actividad",
        "dia_actividad",
        "hora_inicio",
        "hora_fin",
        "responsable_actividad",
        "vigencia_actividad_meses",
        "horario_actividad",
        "activo",
        "fecha_alta",
    )
    list_select_related = ("comedor", "catalogo_actividad", "dia_actividad")
    list_filter = (
        "activo",
        "dia_actividad",
        "catalogo_actividad__categoria",
        ("fecha_alta", RangeDateTimeFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "comedor__nombre",
        "catalogo_actividad__categoria",
        "catalogo_actividad__actividad",
        "responsable_actividad",
    )
    raw_id_fields = ("comedor", "catalogo_actividad")
    readonly_fields = (
        "fecha_alta",
        "fecha_actualizacion",
        "fecha_baja",
        "creado_por",
        "actualizado_por",
    )


class InscriptoActividadAdminForm(forms.ModelForm):
    class Meta:
        model = InscriptoActividadEspacioPWA
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        actividad = datos.get("actividad_espacio")
        if actividad is None:
            return datos

        # El POST de ModelAdmin mantiene la transacción abierta hasta guardar.
        origen = self.instance.actividad_espacio_id
        ids = {actividad.pk}
        if origen is not None:
            ids.add(origen)
        comedores = dict(
            ActividadEspacioPWA.objects.filter(pk__in=ids).values_list(
                "pk", "comedor_id"
            )
        )
        comedores_ids = set(comedores.values())
        if (
            ids != comedores.keys()
            or comedores_ids != Comedor.bloquear_para_actividades(comedores_ids)
        ):
            raise ValidationError(
                "La actividad o la inscripción cambió. Recargá el formulario."
            )
        bloqueadas = bloquear_actividades_espacio(actividad_ids=ids)
        if comedores != {pk: item.comedor_id for pk, item in bloqueadas.items()} or (
            self.instance.pk is not None
            and not InscriptoActividadEspacioPWA.objects.select_for_update()
            .filter(pk=self.instance.pk, actividad_espacio_id=origen)
            .exists()
        ):
            raise ValidationError(
                "La actividad o la inscripción cambió. Recargá el formulario."
            )
        return datos


@admin.register(InscriptoActividadEspacioPWA)
class InscriptoActividadEspacioPWAAdmin(SisocModelAdmin):
    form = InscriptoActividadAdminForm
    list_display = (
        "id",
        "actividad_espacio",
        "nomina",
        "activo",
        "fecha_alta",
    )
    list_select_related = (
        "actividad_espacio__comedor",
        "actividad_espacio__catalogo_actividad",
        *NOMINA_RELACIONADAS,
    )
    list_filter = (
        "activo",
        ("fecha_alta", RangeDateTimeFilter),
        ("actividad_espacio__comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "actividad_espacio__comedor__nombre",
        "nomina__ciudadano__apellido",
        "nomina__ciudadano__nombre",
        "nomina__ciudadano__documento",
    )
    raw_id_fields = ("actividad_espacio", "nomina")
    readonly_fields = (
        "fecha_alta",
        "fecha_actualizacion",
        "fecha_baja",
        "creado_por",
        "actualizado_por",
    )


@admin.register(NominaEspacioPWA)
class NominaEspacioPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "nomina",
        "asistencia_alimentaria",
        "asistencia_actividades",
        "es_indocumentado",
        "pertenece_comunidad_indigena",
        "situacion_calle",
        "persona_con_celiaquia",
        "identificador_interno",
        "activo",
        "fecha_alta",
    )
    list_select_related = NOMINA_RELACIONADAS
    list_filter = (
        "activo",
        "es_indocumentado",
        "pertenece_comunidad_indigena",
        "situacion_calle",
        "persona_con_celiaquia",
        "asistencia_alimentaria",
        "asistencia_actividades",
        ("fecha_alta", RangeDateTimeFilter),
    )
    search_fields = (
        "nomina__ciudadano__apellido",
        "nomina__ciudadano__nombre",
        "nomina__ciudadano__documento",
        "identificador_interno",
    )
    raw_id_fields = ("nomina",)
    readonly_fields = (
        "fecha_alta",
        "fecha_actualizacion",
        "fecha_baja",
        "creado_por",
        "actualizado_por",
    )


@admin.register(RegistroAsistenciaNominaPWA)
class RegistroAsistenciaNominaPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "nomina",
        "periodicidad",
        "periodo_referencia",
        "fecha_toma_asistencia",
        "tomado_por",
    )
    list_select_related = (*NOMINA_RELACIONADAS, "tomado_por")
    list_filter = (
        "periodicidad",
        "periodo_referencia",
        ("fecha_toma_asistencia", RangeDateTimeFilter),
    )
    search_fields = (
        "nomina__ciudadano__apellido",
        "nomina__ciudadano__nombre",
        "nomina__ciudadano__documento",
        "tomado_por__username",
    )
    raw_id_fields = ("nomina", "tomado_por")
    readonly_fields = (
        "fecha_toma_asistencia",
        "metadata",
    )


@admin.register(AuditAccesoComedorPWA)
class AuditAccesoComedorPWAAdmin(SoloLecturaAdminMixin, SisocModelAdmin):
    list_display = (
        "fecha_evento",
        "accion",
        "user",
        "comedor",
        "actor",
    )
    list_select_related = ("user", "comedor", "actor")
    list_filter = ("accion", ("fecha_evento", RangeDateTimeFilter))
    search_fields = (
        "user__username",
        "user__email",
        "actor__username",
        "comedor__nombre",
    )
    raw_id_fields = ("acceso", "user", "comedor", "organizacion", "actor")
    readonly_fields = (
        "acceso",
        "user",
        "comedor",
        "organizacion",
        "accion",
        "fecha_evento",
        "actor",
        "metadata",
    )


# Los accesos se gestionan desde el ABM de usuarios y la PWA (que validan
# roles y alcance). El admin los muestra para soporte; la desactivación de
# operadores queda en la PWA porque el service exige un representante actor.
@admin.register(AccesoComedorPWA)
class AccesoComedorPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "user",
        "comedor",
        "organizacion",
        "rol",
        "tipo_asociacion",
        "activo",
        "fecha_creacion",
        "fecha_baja",
    )
    list_select_related = ("user", "comedor", "organizacion")
    list_filter = (
        "rol",
        "tipo_asociacion",
        "activo",
        ("fecha_creacion", RangeDateTimeFilter),
        ("comedor__nombre", FieldTextFilter),
    )
    search_fields = (
        "user__username",
        "user__email",
        "comedor__nombre",
        "organizacion__nombre",
    )
    raw_id_fields = ("organizacion", "user", "comedor", "creado_por")
    readonly_fields = ("fecha_creacion", "fecha_baja", "fecha_actualizacion")


@admin.register(AccesoOrganizacionPWA)
class AccesoOrganizacionPWAAdmin(SisocModelAdmin):
    list_display = (
        "id",
        "user",
        "organizacion",
        "activo",
        "fecha_creacion",
        "fecha_baja",
    )
    list_select_related = ("user", "organizacion")
    list_filter = ("activo", ("fecha_creacion", RangeDateTimeFilter))
    search_fields = (
        "user__username",
        "user__email",
        "organizacion__nombre",
        "organizacion__cuit",
    )
    raw_id_fields = ("organizacion", "user", "creado_por")
    readonly_fields = ("fecha_creacion", "fecha_baja", "fecha_actualizacion")


def desactivar_coordinador_pwa(coordinador, _usuario, _datos):
    if not coordinador.activo:
        raise ValidationError("El coordinador PWA ya está inactivo.")
    return deactivate_coordinador_equipo_tecnico_pwa_access(coordinador.user)


@admin.register(CoordinadorEquipoTecnicoPWA)
class CoordinadorEquipoTecnicoPWAAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (
        Operacion(
            slug="desactivar",
            titulo="Desactivar coordinador PWA",
            descripcion="Quita el alcance PWA de solo lectura del coordinador.",
            ejecutar=desactivar_coordinador_pwa,
            campo_estado="activo",
            motivo_obligatorio=True,
            destructiva=True,
            icono="person_off",
        ),
    )
    list_display = ("id", "user", "activo", "fecha_creacion", "fecha_actualizacion")
    list_select_related = ("user",)
    list_filter = ("activo", ("fecha_creacion", RangeDateTimeFilter))
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user", "duplas", "comedores_adicionales")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
