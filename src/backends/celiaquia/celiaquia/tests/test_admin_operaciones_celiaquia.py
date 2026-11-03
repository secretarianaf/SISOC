"""Issue #2789: operaciones de soporte del admin de Celiaquía."""

from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from celiaquia import admin as celiaquia_admin
from celiaquia.models import (
    CupoMovimiento,
    EstadoCupo,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    HistorialCupo,
    HistorialValidacionTecnica,
    PagoExpediente,
    PagoNomina,
    ProvinciaCupo,
    ResultadoSintys,
    RevisionTecnico,
    Subsanacion,
    TipoMovimientoCupo,
    TipoSubsanacion,
)
from celiaquia.services.cupo_service import CupoNoConfigurado, CupoService
from ciudadanos.models import Ciudadano
from core.admin_operaciones import ejecutar_operacion
from core.models import Provincia

pytestmark = pytest.mark.django_db


def _operacion(model, slug):
    model_admin = admin.site.get_model_admin(model)
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(model, slug, obj, usuario, **datos):
    datos.setdefault("motivo", "")
    return ejecutar_operacion(
        operacion=_operacion(model, slug), objetos=[obj], usuario=usuario, datos=datos
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


@pytest.fixture(name="provincia")
def provincia_fixture():
    provincia = Provincia.objects.create(nombre="Provincia Admin")
    ProvinciaCupo.objects.create(provincia=provincia, total_asignado=10, usados=0)
    return provincia


@pytest.fixture(name="expediente")
def expediente_fixture():
    return Expediente.objects.create(
        usuario_provincia=User.objects.create_user("prov-admin-celiaquia"),
        estado=EstadoExpediente.objects.create(nombre="CRUCE_FINALIZADO"),
    )


def _legajo(expediente, provincia, documento, **campos):
    ciudadano = Ciudadano.objects.create(
        apellido="Ape", nombre=f"N{documento}", documento=documento, provincia=provincia
    )
    estado, _ = EstadoLegajo.objects.get_or_create(nombre="VALIDO")
    return ExpedienteCiudadano.objects.create(
        expediente=expediente,
        ciudadano=ciudadano,
        estado=estado,
        rol=ExpedienteCiudadano.ROLE_BENEFICIARIO,
        **campos,
    )


@pytest.fixture(name="legajo")
def legajo_fixture(expediente, provincia):
    return _legajo(expediente, provincia, 30111222)


def _titular(expediente, provincia, documento):
    legajo = _legajo(
        expediente,
        provincia,
        documento,
        revision_tecnico=RevisionTecnico.APROBADO,
        resultado_sintys=ResultadoSintys.MATCH,
    )
    CupoService.reservar_slot(legajo=legajo, usuario=None)
    legajo.refresh_from_db()
    return legajo


# ── Revisión técnica ─────────────────────────────────────────────────────


def test_aprobar_llama_al_service_y_audita(mocker, legajo, superuser):
    aprobar = mocker.patch.object(
        celiaquia_admin.RevisionService, "aprobar", return_value={"success": True}
    )

    ok, errores = _ejecutar(ExpedienteCiudadano, "aprobar", legajo, superuser)

    assert ok == [legajo] and errores == []
    aprobar.assert_called_once_with(legajo, superuser)
    assert _auditado(legajo, "aprobar")


def test_rechazar_pasa_el_motivo_sin_comentarios(mocker, legajo, superuser):
    rechazar = mocker.patch.object(
        celiaquia_admin.RevisionService, "rechazar", return_value={"success": True}
    )

    ok, _ = _ejecutar(
        ExpedienteCiudadano, "rechazar", legajo, superuser, motivo="DNI ilegible"
    )

    assert ok == [legajo]
    rechazar.assert_called_once_with(legajo, superuser, "DNI ilegible", comentarios=())
    assert _auditado(legajo, "rechazar")


def test_subsanar_arma_la_observacion_con_el_tipo_elegido(mocker, legajo, superuser):
    subsanar = mocker.patch.object(
        celiaquia_admin.RevisionService, "subsanar", return_value={"success": True}
    )

    _ejecutar(
        ExpedienteCiudadano,
        "subsanar",
        legajo,
        superuser,
        motivo="Falta el certificado",
        tipo_subsanacion=TipoSubsanacion.DOCUMENTACION,
    )

    subsanar.assert_called_once_with(
        legajo,
        superuser,
        "Falta el certificado",
        tipo_subsanacion=TipoSubsanacion.DOCUMENTACION,
        comentarios=(),
        observaciones_fallback=[
            (TipoSubsanacion.DOCUMENTACION, "Falta el certificado")
        ],
    )
    assert _auditado(legajo, "subsanar")


def test_subsanar_real_crea_la_solicitud(legajo, superuser):
    ok, errores = _ejecutar(
        ExpedienteCiudadano, "subsanar", legajo, superuser, motivo="Foto borrosa"
    )

    assert ok == [legajo] and errores == []
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.SUBSANAR
    subsanacion = Subsanacion.objects.get(legajo=legajo)
    assert subsanacion.motivo_general == "Foto borrosa"
    assert list(subsanacion.observaciones.values_list("tipo", flat=True)) == [
        TipoSubsanacion.OTROS
    ]


def test_revision_respeta_la_transicion_del_service(mocker, legajo, superuser):
    legajo.revision_tecnico = RevisionTecnico.APROBADO
    legajo.save(update_fields=["revision_tecnico"])
    rechazar = mocker.patch.object(celiaquia_admin.RevisionService, "rechazar")

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "rechazar", legajo, superuser, motivo="Tarde"
    )

    assert not ok
    assert "No se puede modificar" in errores[0][1]
    rechazar.assert_not_called()
    assert not _auditado(legajo, "rechazar")


def test_rechazar_titular_libera_el_cupo_antes(expediente, provincia, superuser):
    legajo = _titular(expediente, provincia, 30111333)
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 1
    legajo.revision_tecnico = RevisionTecnico.SUBSANADO
    legajo.save(update_fields=["revision_tecnico"])

    ok, _ = _ejecutar(
        ExpedienteCiudadano, "rechazar", legajo, superuser, motivo="No corresponde"
    )

    assert ok == [legajo]
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.RECHAZADO
    assert legajo.estado_cupo == EstadoCupo.NO_EVAL
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 0


# ── Volver a pendiente (issues #2758 y #2861) ───────────────────────────


def test_volver_a_pendiente_desde_aprobado_libera_cupo_y_registra(
    expediente, provincia, superuser
):
    legajo = _titular(expediente, provincia, 30111666)
    assert legajo.estado_cupo == EstadoCupo.DENTRO
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 1

    ok, errores = _ejecutar(
        ExpedienteCiudadano,
        "volver_a_pendiente",
        legajo,
        superuser,
        motivo="Aprobado por error (#2861)",
    )

    assert ok == [legajo] and errores == []
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE
    assert legajo.estado_cupo == EstadoCupo.NO_EVAL
    assert legajo.es_titular_activo is False
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 0
    movimiento = CupoMovimiento.objects.get(legajo=legajo, tipo=TipoMovimientoCupo.BAJA)
    assert movimiento.delta == -1 and movimiento.usuario == superuser
    assert HistorialCupo.objects.filter(
        legajo=legajo, tipo_movimiento=TipoMovimientoCupo.BAJA
    ).exists()
    historial = HistorialValidacionTecnica.objects.get(
        legajo=legajo, estado_nuevo=RevisionTecnico.PENDIENTE
    )
    assert historial.estado_anterior == RevisionTecnico.APROBADO
    assert historial.usuario == superuser
    assert "Aprobado por error (#2861)" in historial.motivo
    entrada = LogEntry.objects.get(
        object_pk=str(legajo.pk), additional_data__operacion="volver_a_pendiente"
    )
    assert entrada.changes_dict == {
        "revision_tecnico": [RevisionTecnico.APROBADO, RevisionTecnico.PENDIENTE]
    }
    assert entrada.additional_data["motivo"] == "Aprobado por error (#2861)"


@pytest.mark.parametrize(
    "estado", [RevisionTecnico.RECHAZADO, RevisionTecnico.SUBSANADO]
)
def test_volver_a_pendiente_desde_otras_evaluaciones(legajo, superuser, estado):
    legajo.revision_tecnico = estado
    legajo.save(update_fields=["revision_tecnico"])

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )

    assert ok == [legajo] and errores == []
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE
    assert HistorialValidacionTecnica.objects.filter(
        legajo=legajo, estado_anterior=estado, estado_nuevo=RevisionTecnico.PENDIENTE
    ).exists()
    assert not CupoMovimiento.objects.filter(legajo=legajo).exists()


def test_volver_a_pendiente_saca_de_la_lista_de_espera(legajo, superuser):
    legajo.revision_tecnico = RevisionTecnico.APROBADO
    legajo.estado_cupo = EstadoCupo.FUERA
    legajo.save(update_fields=["revision_tecnico", "estado_cupo"])

    ok, _ = _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )

    assert ok == [legajo]
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE
    assert legajo.estado_cupo == EstadoCupo.NO_EVAL


@pytest.mark.parametrize(
    ("estado", "mensaje"),
    [
        (RevisionTecnico.PENDIENTE, "El legajo ya está en PENDIENTE."),
        (RevisionTecnico.SUBSANAR, "subsanación abierta"),
    ],
)
def test_volver_a_pendiente_rechaza_estados_no_permitidos(
    legajo, superuser, estado, mensaje
):
    legajo.revision_tecnico = estado
    legajo.save(update_fields=["revision_tecnico"])

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )

    assert not ok
    assert mensaje in errores[0][1]
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == estado
    assert not HistorialValidacionTecnica.objects.filter(legajo=legajo).exists()
    assert not _auditado(legajo, "volver_a_pendiente")


def test_volver_a_pendiente_no_toca_legajos_con_pago(expediente, provincia, superuser):
    legajo = _titular(expediente, provincia, 30111777)
    pago = PagoExpediente.objects.create(
        provincia=provincia, periodo="2026-10", creado_por=superuser
    )
    PagoNomina.objects.create(pago=pago, legajo=legajo, documento="30111777")

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )

    assert not ok
    assert "nómina de pago" in errores[0][1]
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.APROBADO
    assert legajo.estado_cupo == EstadoCupo.DENTRO
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 1


def test_volver_a_pendiente_sin_cupo_configurado_no_cambia_nada(
    mocker, expediente, provincia, superuser
):
    legajo = _titular(expediente, provincia, 30111888)
    mocker.patch(
        "celiaquia.services.revision_service.impl.CupoService.liberar_slot",
        side_effect=CupoNoConfigurado("La provincia no tiene cupo configurado."),
    )

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )

    assert not ok
    assert errores == [(legajo, "La provincia no tiene cupo configurado.")]
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.APROBADO
    assert not HistorialValidacionTecnica.objects.filter(
        legajo=legajo, estado_nuevo=RevisionTecnico.PENDIENTE
    ).exists()


def test_volver_a_pendiente_exige_motivo_y_es_destructiva():
    operacion = _operacion(ExpedienteCiudadano, "volver_a_pendiente")
    assert operacion.motivo_obligatorio
    assert operacion.destructiva and not operacion.en_lote
    assert operacion.campo_estado == "revision_tecnico"


def test_legajo_vuelto_a_pendiente_se_puede_volver_a_evaluar(legajo, superuser):
    legajo.revision_tecnico = RevisionTecnico.APROBADO
    legajo.save(update_fields=["revision_tecnico"])
    _ejecutar(
        ExpedienteCiudadano, "volver_a_pendiente", legajo, superuser, motivo="Error"
    )
    legajo.refresh_from_db()

    ok, errores = _ejecutar(ExpedienteCiudadano, "aprobar", legajo, superuser)

    assert ok == [legajo] and errores == []
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.APROBADO


def test_volver_a_pendiente_por_url_del_admin(auth_client, legajo):
    legajo.revision_tecnico = RevisionTecnico.APROBADO
    legajo.save(update_fields=["revision_tecnico"])
    url = reverse(
        "admin:celiaquia_expedienteciudadano_operacion_volver_a_pendiente",
        args=[legajo.pk],
    )

    sin_motivo = auth_client.post(url, {"confirmar_operacion": "1", "motivo": ""})
    legajo.refresh_from_db()
    estado_sin_motivo = legajo.revision_tecnico
    con_motivo = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Aprobado por error"}
    )

    assert sin_motivo.status_code == 200
    assert estado_sin_motivo == RevisionTecnico.APROBADO
    assert con_motivo.status_code == 302
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE


# ── Eliminar legajo (issues #2483 y #2488) ───────────────────────────────


def test_eliminar_legajo_hace_baja_logica_y_libera_cupo(
    expediente, provincia, superuser
):
    legajo = _titular(expediente, provincia, 30111999)
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 1

    ok, errores = _ejecutar(
        ExpedienteCiudadano,
        "eliminar",
        legajo,
        superuser,
        motivo="Duplicado con CUIL incorrecto (#2488)",
    )

    assert ok == [legajo] and errores == []
    assert not ExpedienteCiudadano.objects.filter(pk=legajo.pk).exists()
    borrado = ExpedienteCiudadano.all_objects.get(pk=legajo.pk)
    assert borrado.deleted_at is not None
    assert borrado.deleted_by == superuser
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 0
    entrada = LogEntry.objects.get(
        object_pk=str(legajo.pk), additional_data__operacion="eliminar"
    )
    assert entrada.additional_data["motivo"] == "Duplicado con CUIL incorrecto (#2488)"


def test_eliminar_legajo_llama_al_service(mocker, legajo, superuser):
    eliminar = mocker.patch.object(
        celiaquia_admin.RevisionService, "eliminar", return_value={"success": True}
    )

    ok, _ = _ejecutar(
        ExpedienteCiudadano, "eliminar", legajo, superuser, motivo="Duplicado"
    )

    assert ok == [legajo]
    eliminar.assert_called_once_with(legajo, superuser)


def test_eliminar_legajo_exige_permiso_del_service(mocker, legajo):
    sin_rol = User.objects.create_user("sin-rol-celiaquia", is_staff=True)
    eliminar = mocker.patch.object(celiaquia_admin.RevisionService, "eliminar")

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "eliminar", legajo, sin_rol, motivo="Duplicado"
    )

    assert not ok and errores
    eliminar.assert_not_called()
    assert ExpedienteCiudadano.objects.filter(pk=legajo.pk).exists()


def test_eliminar_legajo_exige_motivo_y_es_destructiva():
    operacion = _operacion(ExpedienteCiudadano, "eliminar")
    assert operacion.motivo_obligatorio and operacion.destructiva


# ── Cupo ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("slug", "metodo"),
    [
        ("suspender_cupo", "suspender_slot"),
        ("reactivar_cupo", "reactivar_slot"),
        ("liberar_cupo", "liberar_slot"),
    ],
)
def test_cupo_llama_al_service(mocker, legajo, superuser, slug, metodo):
    servicio = mocker.patch.object(
        celiaquia_admin.CupoService, metodo, return_value=True
    )

    ok, _ = _ejecutar(ExpedienteCiudadano, slug, legajo, superuser, motivo="Ticket 7")

    assert ok == [legajo]
    servicio.assert_called_once_with(
        legajo=legajo, usuario=superuser, motivo="Ticket 7"
    )
    assert _auditado(legajo, slug)


def test_suspender_y_reactivar_titular_real(expediente, provincia, superuser):
    legajo = _titular(expediente, provincia, 30111444)
    assert legajo.es_titular_activo

    _ejecutar(ExpedienteCiudadano, "suspender_cupo", legajo, superuser, motivo="Pausa")
    legajo.refresh_from_db()
    suspendido = legajo.es_titular_activo
    _ejecutar(ExpedienteCiudadano, "reactivar_cupo", legajo, superuser)
    legajo.refresh_from_db()

    assert suspendido is False
    assert legajo.es_titular_activo is True
    assert ProvinciaCupo.objects.get(provincia=provincia).usados == 1
    assert HistorialCupo.objects.filter(legajo=legajo).count() >= 2


def test_reactivar_sin_suspension_es_error(expediente, provincia, superuser):
    legajo = _titular(expediente, provincia, 30111555)
    assert legajo.es_titular_activo

    ok, errores = _ejecutar(ExpedienteCiudadano, "reactivar_cupo", legajo, superuser)

    assert not ok and errores
    assert not _auditado(legajo, "reactivar_cupo")


def test_cupo_no_configurado_se_informa_como_error(mocker, legajo, superuser):
    mocker.patch.object(
        celiaquia_admin.CupoService,
        "liberar_slot",
        side_effect=CupoNoConfigurado("La provincia no tiene cupo configurado."),
    )

    ok, errores = _ejecutar(
        ExpedienteCiudadano, "liberar_cupo", legajo, superuser, motivo="Baja"
    )

    assert not ok
    assert errores == [(legajo, "La provincia no tiene cupo configurado.")]


def test_liberar_cupo_es_destructiva_y_no_va_en_lote():
    operacion = _operacion(ExpedienteCiudadano, "liberar_cupo")
    assert operacion.destructiva and not operacion.en_lote
    assert operacion.motivo_obligatorio


# ── Expediente ───────────────────────────────────────────────────────────


def test_reprocesar_registros_erroneos_llama_al_service(mocker, expediente, superuser):
    reprocesar = mocker.patch.object(
        celiaquia_admin.registros_erroneos_service,
        "reprocesar",
        return_value={"creados": 0},
    )

    ok, _ = _ejecutar(
        Expediente, "reprocesar_registros_erroneos", expediente, superuser
    )

    assert ok == [expediente]
    reprocesar.assert_called_once_with(expediente, superuser)
    assert _auditado(expediente, "reprocesar_registros_erroneos")


def test_reprocesar_sin_registros_es_error(expediente, superuser):
    ok, errores = _ejecutar(
        Expediente, "reprocesar_registros_erroneos", expediente, superuser
    )

    assert not ok
    assert errores == [(expediente, "No hay registros erróneos para reprocesar.")]


# ── Punta a punta y listados ─────────────────────────────────────────────


def test_aprobar_por_url_del_admin(auth_client, legajo, superuser):
    url = reverse(
        "admin:celiaquia_expedienteciudadano_operacion_aprobar", args=[legajo.pk]
    )

    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Revisado por soporte"}
    )

    assert respuesta.status_code == 302
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.APROBADO
    historial = HistorialValidacionTecnica.objects.get(legajo=legajo)
    assert historial.usuario == superuser
    entrada = LogEntry.objects.get(
        object_pk=str(legajo.pk), additional_data__operacion="aprobar"
    )
    assert entrada.changes_dict == {
        "revision_tecnico": [RevisionTecnico.PENDIENTE, RevisionTecnico.APROBADO]
    }
    assert entrada.additional_data["motivo"] == "Revisado por soporte"


def test_estados_quedan_de_solo_lectura_en_el_form(rf, superuser, mocker):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site.get_model_admin(ExpedienteCiudadano)

    # Al editar un legajo, los estados solo cambian por las operaciones.
    campos = model_admin.get_readonly_fields(request, mocker.Mock())

    assert {"revision_tecnico", "estado_cupo", "es_titular_activo"} <= set(campos)


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize(
    "modelo",
    [ExpedienteCiudadano, Expediente, HistorialValidacionTecnica],
)
def test_listados_sin_n_mas_1(
    auth_client, expediente, provincia, superuser, modelo, django_assert_max_num_queries
):
    url = reverse(
        f"admin:celiaquia_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )

    def _cargar(desde, cantidad):
        for documento in range(desde, desde + cantidad):
            exp = Expediente.objects.create(
                usuario_provincia=User.objects.create_user(f"prov-{documento}"),
                estado=expediente.estado,
            )
            legajo = _legajo(exp, provincia, documento)
            HistorialValidacionTecnica.objects.create(
                legajo=legajo,
                estado_nuevo=RevisionTecnico.PENDIENTE,
                usuario=superuser,
            )

    _cargar(40000000, 5)
    with django_assert_max_num_queries(10):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(40000100, 5)
    consultas_con_10 = _consultas(auth_client, url)

    assert consultas_con_10 == consultas_con_5
