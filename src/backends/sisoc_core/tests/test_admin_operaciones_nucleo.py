"""Issue #2789 (Fase 2): operaciones de soporte del admin del núcleo SISOC."""

from auditlog.models import LogEntry
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from encuestas import admin as encuestas_admin
from encuestas.models import (
    Encuesta,
    EstadoEncuesta,
    EstadoRonda,
    Pregunta,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_segmentacion,
    publicar,
    solicitar_publicacion,
)
from users.models import BulkCredentialsJob, UserImportJob
from usuarios import admin as usuarios_admin

pytestmark = pytest.mark.django_db

MAX_CONSULTAS_LISTADO = 20
CONFIRMAR = {"confirmar_operacion": "1", "motivo": "Pedido de soporte"}


def _url(app_modelo, slug, obj):
    return reverse(f"admin:{app_modelo}_operacion_{slug}", args=[obj.pk])


def _assert_auditado(obj, slug):
    assert (
        LogEntry.objects.get_for_object(obj)
        .filter(additional_data__operacion=slug)
        .exists()
    )


# --- Lotes de usuarios ------------------------------------------------------


def _user_import_job(usuario):
    return UserImportJob.objects.create(
        requested_by=usuario,
        original_filename="usuarios.xlsx",
        archivo="usuarios/import_jobs/test/usuarios.xlsx",
        status=UserImportJob.Status.FAILED,
    )


def _bulk_credentials_job(usuario):
    return BulkCredentialsJob.objects.create(
        requested_by=usuario,
        original_filename="credenciales.xlsx",
        archivo="usuarios/bulk_credentials/test/credenciales.xlsx",
        send_type="alta",
        status=BulkCredentialsJob.Status.FAILED,
    )


def test_reanudar_importacion_de_usuarios_llama_al_service(
    auth_client, superuser, mocker
):
    job = _user_import_job(superuser)
    service = mocker.patch.object(
        usuarios_admin, "request_resume_user_import_job", return_value=job
    )

    response = auth_client.post(_url("users_userimportjob", "reanudar", job), CONFIRMAR)

    assert response.status_code == 302
    service.assert_called_once_with(job=job)
    _assert_auditado(job, "reanudar")


def test_reanudar_importacion_de_usuarios_de_punta_a_punta(auth_client, superuser):
    job = _user_import_job(superuser)

    response = auth_client.post(_url("users_userimportjob", "reanudar", job), CONFIRMAR)

    assert response.status_code == 302
    job.refresh_from_db()
    assert job.status == UserImportJob.Status.PENDING
    assert job.resume_count == 1
    _assert_auditado(job, "reanudar")


def test_reanudar_envio_de_credenciales_llama_al_service(
    auth_client, superuser, mocker
):
    job = _bulk_credentials_job(superuser)
    service = mocker.patch.object(
        usuarios_admin, "request_resume_bulk_credentials_job", return_value=job
    )

    response = auth_client.post(
        _url("users_bulkcredentialsjob", "reanudar", job), CONFIRMAR
    )

    assert response.status_code == 302
    service.assert_called_once_with(job=job)
    _assert_auditado(job, "reanudar")


@pytest.mark.parametrize(
    "url_name",
    [
        "admin:users_userimportjob_changelist",
        "admin:users_userimportjobrow_changelist",
        "admin:users_bulkcredentialsjob_changelist",
        "admin:users_bulkcredentialsjobrow_changelist",
        "admin:encuestas_rondaencuesta_changelist",
        "admin:encuestas_respuestaronda_changelist",
        "admin:encuestas_respuestapregunta_changelist",
        "admin:encuestas_recordatoriousuario_changelist",
        "admin:insumos_insumo_changelist",
        "admin:dashboard_dashboard_changelist",
    ],
)
def test_listados_del_nucleo_cargan(auth_client, url_name):
    assert auth_client.get(reverse(url_name), {"q": "x"}).status_code == 200


def test_lotes_de_usuarios_no_se_editan_ni_se_crean(auth_client, superuser):
    job = _user_import_job(superuser)

    alta = auth_client.get(reverse("admin:users_userimportjob_add"))
    auth_client.post(
        reverse("admin:users_userimportjob_change", args=[job.pk]),
        {"status": UserImportJob.Status.COMPLETED},
    )

    assert alta.status_code == 403
    job.refresh_from_db()
    assert job.status == UserImportJob.Status.FAILED


# --- Encuestas ----------------------------------------------------------------


def _encuesta(usuario, titulo="Para revisar"):
    encuesta = Encuesta.objects.create(
        titulo=titulo,
        usuario_creador=usuario,
        es_opcional=True,
        duracion_ronda_dias=7,
    )
    Pregunta.objects.create(
        encuesta=encuesta, texto="¿Conforme?", tipo=TipoPregunta.SI_NO
    )
    actualizar_segmentacion(
        encuesta,
        tipo=TipoSegmentacion.LISTADO_DOCUMENTOS,
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "12345678"}],
    )
    return encuesta


@pytest.mark.parametrize(
    ("slug", "service", "pendiente", "kwargs_extra"),
    [
        ("solicitar_publicacion", "solicitar_publicacion", False, {}),
        ("publicar", "publicar", True, {}),
        (
            "rechazar_publicacion",
            "rechazar_publicacion",
            True,
            {"motivo": "Pedido de soporte"},
        ),
    ],
)
def test_operaciones_de_encuesta_llaman_al_service(
    auth_client, superuser, mocker, slug, service, pendiente, kwargs_extra
):
    encuesta = _encuesta(superuser)
    if pendiente:
        solicitar_publicacion(encuesta, usuario=superuser)
    mock = mocker.patch.object(encuestas_admin, service)

    response = auth_client.post(_url("encuestas_encuesta", slug, encuesta), CONFIRMAR)

    assert response.status_code == 302
    mock.assert_called_once_with(encuesta, usuario=superuser, **kwargs_extra)
    _assert_auditado(encuesta, slug)


def test_publicar_encuesta_de_punta_a_punta_abre_la_ronda(auth_client, superuser):
    encuesta = _encuesta(superuser)
    auth_client.post(
        _url("encuestas_encuesta", "solicitar_publicacion", encuesta), CONFIRMAR
    )

    response = auth_client.post(
        _url("encuestas_encuesta", "publicar", encuesta), CONFIRMAR
    )

    assert response.status_code == 302
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PUBLICADA
    assert encuesta.rondas.filter(estado=EstadoRonda.ABIERTA).count() == 1
    entrada = LogEntry.objects.get_for_object(encuesta).get(
        additional_data__operacion="publicar"
    )
    assert entrada.changes_dict == {
        "estado": [EstadoEncuesta.PENDIENTE_APROBACION, EstadoEncuesta.PUBLICADA]
    }


def test_rechazar_publicacion_exige_motivo(auth_client, superuser):
    encuesta = _encuesta(superuser)
    solicitar_publicacion(encuesta, usuario=superuser)

    response = auth_client.post(
        _url("encuestas_encuesta", "rechazar_publicacion", encuesta),
        {"confirmar_operacion": "1", "motivo": ""},
    )

    assert response.status_code == 200
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION


def test_rechazar_publicacion_de_punta_a_punta(auth_client, superuser):
    encuesta = _encuesta(superuser)
    solicitar_publicacion(encuesta, usuario=superuser)

    auth_client.post(
        _url("encuestas_encuesta", "rechazar_publicacion", encuesta),
        {"confirmar_operacion": "1", "motivo": "Falta una pregunta"},
    )

    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.BORRADOR
    assert encuesta.motivo_rechazo == "Falta una pregunta"
    _assert_auditado(encuesta, "rechazar_publicacion")


def _ronda_abierta(usuario):
    encuesta = _encuesta(usuario)
    solicitar_publicacion(encuesta, usuario=usuario)
    return publicar(encuesta, usuario=usuario)


def test_cerrar_ronda_llama_al_service(auth_client, superuser, mocker):
    ronda = _ronda_abierta(superuser)
    mock = mocker.patch.object(encuestas_admin, "cerrar_ronda")

    response = auth_client.post(
        _url("encuestas_rondaencuesta", "cerrar", ronda), CONFIRMAR
    )

    assert response.status_code == 302
    mock.assert_called_once_with(ronda, manual=True)
    _assert_auditado(ronda, "cerrar")


def test_cerrar_ronda_de_punta_a_punta(auth_client, superuser):
    ronda = _ronda_abierta(superuser)

    auth_client.post(_url("encuestas_rondaencuesta", "cerrar", ronda), CONFIRMAR)

    ronda.refresh_from_db()
    assert ronda.estado == EstadoRonda.CERRADA
    assert ronda.cerrada_manualmente is True
    _assert_auditado(ronda, "cerrar")


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        response = client.get(url)
    assert response.status_code == 200
    return len(contexto.captured_queries)


def test_listado_de_encuestas_sin_n_mas_1(
    auth_client, superuser, django_user_model, django_assert_max_num_queries
):
    url = reverse("admin:encuestas_encuesta_changelist")

    def crear(desde, cantidad):
        for numero in range(desde, desde + cantidad):
            Encuesta.objects.create(
                titulo=f"Encuesta {numero}",
                duracion_ronda_dias=7,
                usuario_creador=django_user_model.objects.create_user(
                    username=f"creador{numero}"
                ),
            )

    crear(0, 5)
    con_cinco = _consultas(auth_client, url)

    crear(5, 10)
    with django_assert_max_num_queries(MAX_CONSULTAS_LISTADO):
        con_quince = _consultas(auth_client, url)

    assert con_quince == con_cinco
