"""Operaciones transaccionales compartidas por INET React y las views legacy."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from VAT import models
from VAT.forms import ComisionCursoWizardStep2FormSet, InstitucionContactoAltaFormSet
from VAT.services.inet_forms import form_data
from VAT.services.sesion_comision_service.impl import SesionComisionService


@transaction.atomic
def crear_comision(curso, info, horarios):
    comision = models.ComisionCurso.objects.create(curso=curso, **info)
    total = 0
    for data in horarios:
        if not data or data.get("DELETE"):
            continue
        horario = models.ComisionHorario.objects.create(
            comision_curso=comision,
            dia_semana=data["dia_semana"],
            hora_desde=data["hora_desde"],
            hora_hasta=data["hora_hasta"],
            vigente=data["vigente"] == "1",
        )
        total += SesionComisionService.generar_para_horario(horario)
    return comision, total


def validate_horarios(rows):
    data = form_data({"horarios-TOTAL_FORMS": len(rows), "horarios-INITIAL_FORMS": 0})
    for index, row in enumerate(rows):
        for name, value in row.items():
            data[f"horarios-{index}-{name}"] = str(value)
    formset = ComisionCursoWizardStep2FormSet(data, prefix="horarios")
    if not formset.is_valid():
        raise ValidationError(
            {"horarios": [*formset.errors, *map(str, formset.non_form_errors())]}
        )
    return [form.cleaned_data for form in formset.forms]


@transaction.atomic
def guardar_asistencia(sesion, filas, actor):
    """Sólo inscriptos activos de esta comisión; una carga se guarda completa."""
    active = set(
        models.Inscripcion.objects.filter(
            comision_curso_id=sesion.comision_curso_id,
            estado__in=("inscripta", "validada_presencial"),
        ).values_list("pk", flat=True)
    )
    submitted = [row["inscripcion_id"] for row in filas]
    if len(submitted) != len(set(submitted)) or set(submitted) != active:
        raise ValidationError(
            {"filas": ["La nómina cambió. Recargá la asistencia antes de guardar."]}
        )
    for row in filas:
        models.AsistenciaSesion.objects.update_or_create(
            sesion=sesion,
            inscripcion_id=row["inscripcion_id"],
            defaults={
                "presente": bool(row["presente"]),
                "observaciones": row.get("observaciones", "") or None,
                "registrado_por": actor,
            },
        )
    if sesion.estado == "programada":
        sesion.estado = "realizada"
        sesion.save(update_fields=["estado"])


def contacto_formset(centro, rows):
    data = form_data(
        {
            "contactos-TOTAL_FORMS": len(rows),
            "contactos-INITIAL_FORMS": (
                centro.contactos_adicionales.count() if centro.pk else 0
            ),
        }
    )
    for index, row in enumerate(rows):
        for name, value in row.items():
            data[f"contactos-{index}-{name}"] = (
                "on" if value is True else ("" if value is False else str(value or ""))
            )
    formset = InstitucionContactoAltaFormSet(data, instance=centro, prefix="contactos")
    if not formset.is_valid():
        raise ValidationError(
            {"contactos": [*formset.errors, *map(str, formset.non_form_errors())]}
        )
    return formset


def build_responsable_principal_data(contacto):
    nombre_completo = (contacto.nombre_contacto or "").strip()
    correo = contacto.email_contacto or ""
    telefono = contacto.telefono_contacto or ""
    return {
        "nombre_contacto": nombre_completo,
        "rol_area": contacto.rol_area or "Responsable institucional",
        "documento": contacto.documento or "",
        "telefono_contacto": telefono,
        "email_contacto": correo,
        "tipo": "email" if correo else "telefono",
        "valor": correo or telefono,
        "es_principal": True,
    }


def sync_responsable_principal(centro):
    principal = (
        centro.contactos_adicionales.filter(es_principal=True).order_by("id").first()
    )
    if principal is None:
        principal = centro.contactos_adicionales.order_by("id").first()
    if principal is None:
        return None

    defaults = build_responsable_principal_data(principal)
    for field_name, value in defaults.items():
        setattr(principal, field_name, value)
    principal.save(
        update_fields=[
            "nombre_contacto",
            "rol_area",
            "documento",
            "telefono_contacto",
            "email_contacto",
            "tipo",
            "valor",
            "es_principal",
        ]
    )
    centro.contactos_adicionales.exclude(pk=principal.pk).filter(
        es_principal=True
    ).update(es_principal=False)
    centro.nombre_referente = principal.nombre_contacto or ""
    centro.apellido_referente = ""
    centro.telefono_referente = principal.telefono_contacto or ""
    centro.correo_referente = principal.email_contacto or ""
    centro.save(
        update_fields=[
            "nombre_referente",
            "apellido_referente",
            "telefono_referente",
            "correo_referente",
        ]
    )
    return principal


@transaction.atomic
def crear_centro(form, contactos):
    form.instance.activo = True
    centro_guardado = form.save()

    contactos.instance = centro_guardado
    contactos.save()
    sync_responsable_principal(centro_guardado)

    models.InstitucionIdentificadorHist.objects.create(
        centro=centro_guardado,
        tipo_identificador="cue",
        valor_identificador=form.cleaned_data["codigo"],
        rol_institucional="sede",
        es_actual=True,
    )

    models.InstitucionUbicacion.objects.create(
        centro=centro_guardado,
        localidad=form.cleaned_data["localidad"],
        rol_ubicacion="sede_principal",
        domicilio=form.cleaned_data["domicilio_actividad"],
        es_principal=True,
    )

    return centro_guardado


@transaction.atomic
def actualizar_centro(form, contactos):
    centro = form.save(commit=False)
    centro.save()
    form.save_m2m()
    centro_guardado = centro

    contactos.instance = centro_guardado
    contactos.save()
    sync_responsable_principal(centro_guardado)

    ubicacion_principal = (
        centro_guardado.ubicaciones.filter(rol_ubicacion="sede_principal")
        .order_by("-es_principal", "-vigencia_desde", "-id")
        .first()
        or centro_guardado.ubicaciones.order_by(
            "-es_principal", "-vigencia_desde", "-id"
        ).first()
    )
    if ubicacion_principal is None:
        ubicacion_principal = models.InstitucionUbicacion(
            centro=centro_guardado,
            rol_ubicacion="sede_principal",
        )
    ubicacion_principal.localidad = form.cleaned_data["localidad"]
    ubicacion_principal.domicilio = form.cleaned_data["domicilio_actividad"]
    ubicacion_principal.es_principal = True
    ubicacion_principal.save()

    identificador_cue = (
        centro_guardado.identificadores_hist.filter(tipo_identificador="cue")
        .order_by("-es_actual", "-vigencia_desde", "-id")
        .first()
    )
    if identificador_cue is None:
        identificador_cue = models.InstitucionIdentificadorHist(
            centro=centro_guardado,
            tipo_identificador="cue",
        )
    identificador_cue.valor_identificador = form.cleaned_data["codigo"]
    identificador_cue.rol_institucional = "sede"
    identificador_cue.ubicacion = ubicacion_principal
    identificador_cue.es_actual = True
    identificador_cue.save()

    return centro_guardado


@transaction.atomic
def reemplazar_horarios(comision, rows):
    """Conservar horarios históricos y regenerar sólo las clases programadas."""
    cleaned = validate_horarios(rows)
    current = list(comision.horarios.filter(vigente=True))

    def signature(row):
        return (row.dia_semana_id, row.hora_desde, row.hora_hasta)

    proposed = [
        (row["dia_semana"].pk, row["hora_desde"], row["hora_hasta"]) for row in cleaned
    ]
    if sorted(map(signature, current)) == sorted(proposed):
        return
    for horario in current:
        SesionComisionService.eliminar_para_horario(horario)
        horario.vigente = False
        horario.save(update_fields=["vigente"])
    preserved = set(
        comision.sesiones.exclude(estado="programada").values_list("fecha", flat=True)
    )
    for row in cleaned:
        horario = models.ComisionHorario.objects.create(
            comision_curso=comision,
            dia_semana=row["dia_semana"],
            hora_desde=row["hora_desde"],
            hora_hasta=row["hora_hasta"],
            vigente=True,
        )
        SesionComisionService.generar_para_horario(horario, fechas_excluidas=preserved)
