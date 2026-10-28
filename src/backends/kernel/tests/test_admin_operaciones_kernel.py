"""Issue #2789 (Fase 2): admin de soporte del kernel (ciudadanos, organizaciones)."""

from auditlog.models import LogEntry
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from ciudadanos import admin as ciudadanos_admin
from ciudadanos.models import Ciudadano, CiudadanosImportJob
from core.models import Provincia
from organizaciones.models import Organizacion

pytestmark = pytest.mark.django_db

# Consultas de un listado del admin con pocas filas: sesión, usuario, conteo,
# página y auditoría de request. Tiene que quedar fijo al sumar filas.
MAX_CONSULTAS_LISTADO = 20


def _crear_job(usuario, status=CiudadanosImportJob.Status.FAILED):
    return CiudadanosImportJob.objects.create(
        requested_by=usuario,
        original_filename="ciudadanos.xlsx",
        archivo="ciudadanos/import_jobs/test/ciudadanos.xlsx",
        status=status,
        last_error_message="Timeout",
    )


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        response = client.get(url)
    assert response.status_code == 200
    return len(contexto.captured_queries)


def test_reanudar_importacion_ciudadanos_llama_al_service(
    auth_client, superuser, mocker
):
    job = _crear_job(superuser)
    service = mocker.patch.object(
        ciudadanos_admin, "request_resume_ciudadanos_import_job", return_value=job
    )

    response = auth_client.post(
        reverse(
            "admin:ciudadanos_ciudadanosimportjob_operacion_reanudar", args=[job.pk]
        ),
        {"confirmar_operacion": "1", "motivo": "Se cayó el worker"},
    )

    assert response.status_code == 302
    service.assert_called_once_with(job=job)
    assert (
        LogEntry.objects.get_for_object(job)
        .filter(additional_data__operacion="reanudar")
        .exists()
    )


def test_reanudar_importacion_ciudadanos_de_punta_a_punta(auth_client, superuser):
    job = _crear_job(superuser)

    response = auth_client.post(
        reverse(
            "admin:ciudadanos_ciudadanosimportjob_operacion_reanudar", args=[job.pk]
        ),
        {"confirmar_operacion": "1", "motivo": "Se cayó el worker"},
    )

    assert response.status_code == 302
    job.refresh_from_db()
    assert job.status == CiudadanosImportJob.Status.PENDING
    assert job.resume_count == 1
    entrada = LogEntry.objects.get_for_object(job).get(
        additional_data__operacion="reanudar"
    )
    assert entrada.changes_dict == {"status": ["failed", "pending"]}
    assert entrada.additional_data["motivo"] == "Se cayó el worker"


def test_reanudar_lote_no_fallido_informa_error_sin_auditar(auth_client, superuser):
    job = _crear_job(superuser, status=CiudadanosImportJob.Status.COMPLETED)

    auth_client.post(
        reverse(
            "admin:ciudadanos_ciudadanosimportjob_operacion_reanudar", args=[job.pk]
        ),
        {"confirmar_operacion": "1"},
    )

    job.refresh_from_db()
    assert job.status == CiudadanosImportJob.Status.COMPLETED
    assert not LogEntry.objects.get_for_object(job).exists()


def test_lote_de_ciudadanos_no_se_edita_desde_el_formulario(auth_client, superuser):
    job = _crear_job(superuser)

    response = auth_client.post(
        reverse("admin:ciudadanos_ciudadanosimportjob_change", args=[job.pk]),
        {"status": CiudadanosImportJob.Status.COMPLETED},
    )

    assert response.status_code in (302, 403)
    job.refresh_from_db()
    assert job.status == CiudadanosImportJob.Status.FAILED


def _crear_ciudadanos(desde, cantidad, usuario):
    for numero in range(desde, desde + cantidad):
        Ciudadano.objects.create(
            apellido=f"Apellido{numero}",
            nombre=f"Nombre{numero}",
            documento=30000000 + numero,
            creado_por=usuario,
        )


def test_listado_de_ciudadanos_sin_n_mas_1(
    auth_client, superuser, django_assert_max_num_queries
):
    url = reverse("admin:ciudadanos_ciudadano_changelist")
    _crear_ciudadanos(0, 5, superuser)
    con_cinco = _consultas(auth_client, url)

    _crear_ciudadanos(5, 10, superuser)
    with django_assert_max_num_queries(MAX_CONSULTAS_LISTADO):
        con_quince = _consultas(auth_client, url)

    assert con_quince == con_cinco


def _crear_organizaciones(desde, cantidad):
    for numero in range(desde, desde + cantidad):
        provincia = Provincia.objects.create(nombre=f"Provincia {numero}")
        Organizacion.objects.create(
            nombre=f"Organización {numero}",
            cuit=20000000000 + numero,
            provincia=provincia,
        )


def test_listado_de_organizaciones_sin_n_mas_1(
    auth_client, django_assert_max_num_queries
):
    url = reverse("admin:organizaciones_organizacion_changelist")
    _crear_organizaciones(0, 5)
    con_cinco = _consultas(auth_client, url)

    _crear_organizaciones(5, 10)
    with django_assert_max_num_queries(MAX_CONSULTAS_LISTADO):
        con_quince = _consultas(auth_client, url)

    assert con_quince == con_cinco


def test_organizacion_se_busca_por_cuit_y_nombre(auth_client):
    _crear_organizaciones(0, 2)
    url = reverse("admin:organizaciones_organizacion_changelist")

    por_cuit = auth_client.get(url, {"q": "20000000001"})
    por_nombre = auth_client.get(url, {"q": "Organización 1"})

    assert list(por_cuit.context["cl"].result_list.values_list("cuit", flat=True)) == [
        20000000001
    ]
    assert [o.nombre for o in por_nombre.context["cl"].result_list] == [
        "Organización 1"
    ]


@pytest.mark.parametrize(
    "url_name",
    [
        "admin:ciudadanos_ciudadano_changelist",
        "admin:ciudadanos_ciudadanosimportjob_changelist",
        "admin:ciudadanos_ciudadanosimportjobrow_changelist",
        "admin:ciudadanos_interaccion_changelist",
        "admin:organizaciones_organizacion_changelist",
        "admin:organizaciones_proyectoorganizacion_changelist",
        "admin:organizaciones_archivoorganizacion_changelist",
        "admin:core_localidad_changelist",
        "admin:core_municipio_changelist",
        "admin:users_profile_changelist",
        "admin:auth_user_changelist",
    ],
)
def test_listados_con_filtros_cargan(auth_client, url_name):
    response = auth_client.get(reverse(url_name), {"q": "x"})

    assert response.status_code == 200


def test_formularios_de_alta_con_autocomplete_cargan(auth_client):
    for url_name in (
        "admin:ciudadanos_ciudadano_add",
        "admin:organizaciones_organizacion_add",
        "admin:organizaciones_archivoorganizacion_add",
        "admin:users_profile_add",
    ):
        assert auth_client.get(reverse(url_name)).status_code == 200, url_name
