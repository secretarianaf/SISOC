"""Issue #2789: búsqueda, filtros y listados del admin de OCR."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from ocr.models import OCRJob, OCRJobDocument

pytestmark = pytest.mark.django_db


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize("modelo", [OCRJob, OCRJobDocument])
def test_listados_sin_n_mas_1(auth_client, modelo, django_assert_max_num_queries):
    url = reverse(
        f"admin:ocr_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )

    def _cargar(desde):
        for numero in range(desde, desde + 5):
            usuario = get_user_model().objects.create_user(username=f"ocr{numero}")
            job = OCRJob.objects.create(requested_by=usuario)
            OCRJobDocument.objects.create(job=job, original_filename=f"{numero}.pdf")

    _cargar(100)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(200)

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize("modelo", ["ocrjob", "ocrjobdocument"])
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:ocr_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_busca_lote_por_usuario(auth_client):
    usuario = get_user_model().objects.create_user(username="ocr_buscado")
    job = OCRJob.objects.create(requested_by=usuario)
    OCRJob.objects.create(
        requested_by=get_user_model().objects.create_user(username="ocr_otro")
    )

    respuesta = auth_client.get(
        reverse("admin:ocr_ocrjob_changelist"), {"q": "ocr_buscado"}
    )

    assert respuesta.status_code == 200
    assert list(respuesta.context["cl"].result_list) == [job]
