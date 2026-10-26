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
    EstadoCupo,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    HistorialCupo,
    HistorialValidacionTecnica,
    ProvinciaCupo,
    ResultadoSintys,
    RevisionTecnico,
    Subsanacion,
    TipoSubsanacion,
)
from celiaquia.services.cupo_service import CupoNoConfigurado, CupoService
from ciudadanos.models import Ciudadano
from core.admin_operaciones import ejecutar_operacion
from core.models import Provincia

pytestmark = pytest.mark.django_db


def _operacion(model, slug):
    model_admin = admin.site._registry[model]  # pylint: disable=protected-access
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


def test_estados_quedan_de_solo_lectura_en_el_form(rf, superuser):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site._registry[  # pylint: disable=protected-access
        ExpedienteCiudadano
    ]

    campos = model_admin.get_readonly_fields(request)

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
