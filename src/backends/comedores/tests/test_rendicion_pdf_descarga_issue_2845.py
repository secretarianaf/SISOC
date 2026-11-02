"""PDF consolidado de rendición generado en segundo plano (issue #2845)."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader, PdfWriter

from config import celery as celery_config
from rendicioncuentasmensual import services_pdf_descarga as servicio
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
    RendicionPdfDescarga,
)

pytestmark = pytest.mark.django_db


def _pdf_bytes(paginas=1):
    writer = PdfWriter()
    for _ in range(paginas):
        writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture(name="media")
def media_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture(name="send_task")
def send_task_fixture(mocker):
    return mocker.patch.object(celery_config.app, "send_task")


def _rendicion_finalizada(paginas=1):
    rendicion = RendicionCuentaMensual.objects.create(
        mes=6, anio=2026, estado=RendicionCuentaMensual.ESTADO_FINALIZADA
    )
    documento = DocumentacionAdjunta.objects.create(
        nombre="comprobante.pdf",
        categoria=DocumentacionAdjunta.CATEGORIA_COMPROBANTES,
        estado=DocumentacionAdjunta.ESTADO_VALIDADO,
        rendicion_cuenta_mensual=rendicion,
        archivo=SimpleUploadedFile(
            "comprobante.pdf", _pdf_bytes(paginas), content_type="application/pdf"
        ),
    )
    return rendicion, documento


def _solicitar(rendicion, capture, usuario=None):
    with capture(execute=True):
        return servicio.solicitar_pdf_descarga(rendicion, usuario)


def test_solicitar_encola_en_cola_comedores_y_tarea_deja_pdf_listo(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada(paginas=2)

    solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)

    assert solicitud.estado == RendicionPdfDescarga.ESTADO_PENDIENTE
    send_task.assert_called_once_with(
        "rendicioncuentasmensual.tasks.generar_pdf_descarga",
        args=[solicitud.pk, solicitud.token],
        queue="comedores",
    )

    servicio.generar_pdf_descarga(solicitud.pk, solicitud.token)

    solicitud.refresh_from_db()
    assert solicitud.estado == RendicionPdfDescarga.ESTADO_LISTO
    assert solicitud.fecha_fin is not None
    with solicitud.archivo.open("rb") as archivo:
        assert len(PdfReader(archivo).pages) == 2
    assert servicio.obtener_pdf_vigente(rendicion) == solicitud


def test_solicitar_reutiliza_pdf_listo_si_los_documentos_no_cambiaron(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    primera = _solicitar(rendicion, django_capture_on_commit_callbacks)
    servicio.generar_pdf_descarga(primera.pk, primera.token)
    send_task.reset_mock()

    segunda = _solicitar(rendicion, django_capture_on_commit_callbacks)

    assert segunda.estado == RendicionPdfDescarga.ESTADO_LISTO
    assert segunda.token == primera.token
    send_task.assert_not_called()


def test_solicitar_en_curso_no_vuelve_a_encolar(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    _solicitar(rendicion, django_capture_on_commit_callbacks)

    _solicitar(rendicion, django_capture_on_commit_callbacks)

    assert send_task.call_count == 1


def test_documento_modificado_regenera_y_borra_el_pdf_anterior(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, documento = _rendicion_finalizada()
    primera = _solicitar(rendicion, django_capture_on_commit_callbacks)
    servicio.generar_pdf_descarga(primera.pk, primera.token)
    primera.refresh_from_db()
    archivo_anterior = media / primera.archivo.name
    assert archivo_anterior.exists()

    documento.archivo = SimpleUploadedFile(
        "comprobante-nuevo.pdf", _pdf_bytes(3), content_type="application/pdf"
    )
    documento.save()
    assert servicio.obtener_pdf_vigente(rendicion) is None

    segunda = _solicitar(rendicion, django_capture_on_commit_callbacks)

    assert segunda.estado == RendicionPdfDescarga.ESTADO_PENDIENTE
    assert segunda.token != primera.token
    assert send_task.call_count == 2
    assert not archivo_anterior.exists()


def test_tarea_de_solicitud_reemplazada_no_pisa_la_nueva(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    vieja = _solicitar(rendicion, django_capture_on_commit_callbacks)
    token_viejo = vieja.token
    # La solicitud vieja quedó colgada en proceso y venció.
    RendicionPdfDescarga.objects.filter(pk=vieja.pk).update(
        estado=RendicionPdfDescarga.ESTADO_PROCESANDO,
        fecha_inicio=timezone.now() - timedelta(hours=1),
    )
    nueva = _solicitar(rendicion, django_capture_on_commit_callbacks)
    assert nueva.token != token_viejo

    servicio.generar_pdf_descarga(nueva.pk, token_viejo)

    nueva.refresh_from_db()
    assert nueva.estado == RendicionPdfDescarga.ESTADO_PENDIENTE
    assert not nueva.archivo
    carpeta = media / "rendicioncuentasmensual_pdf_consolidado"
    assert not carpeta.exists() or not any(carpeta.iterdir())


def test_error_al_generar_deja_estado_error_con_mensaje_generico(
    media, send_task, mocker, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)
    mocker.patch.object(
        servicio.RendicionCuentaMensualService,
        "generar_pdf_descarga_rendicion",
        side_effect=RuntimeError("libreoffice colgado"),
    )

    servicio.generar_pdf_descarga(solicitud.pk, solicitud.token)

    solicitud.refresh_from_db()
    assert solicitud.estado == RendicionPdfDescarga.ESTADO_ERROR
    assert solicitud.error == servicio.MENSAJE_ERROR_GENERICO


def test_broker_caido_informa_error_en_vez_de_quedar_pendiente(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    send_task.side_effect = ConnectionError("redis caído")

    solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)
    solicitud.refresh_from_db()

    assert solicitud.estado == RendicionPdfDescarga.ESTADO_ERROR
    assert solicitud.error == servicio.MENSAJE_ERROR_GENERICO
    estado = servicio.obtener_estado_pdf_descarga(rendicion)
    assert estado.estado == RendicionPdfDescarga.ESTADO_ERROR


def test_estado_en_curso_vencido_se_informa_como_error(
    media, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)
    RendicionPdfDescarga.objects.filter(pk=solicitud.pk).update(
        fecha_solicitud=timezone.now() - timedelta(hours=1)
    )

    estado = servicio.obtener_estado_pdf_descarga(rendicion)

    assert estado.estado == RendicionPdfDescarga.ESTADO_ERROR
    assert estado.error == servicio.MENSAJE_VENCIDO


def test_purga_borra_pdfs_de_mas_de_siete_dias_y_conserva_recientes(
    media, send_task, django_capture_on_commit_callbacks
):
    vieja_rendicion, _ = _rendicion_finalizada()
    reciente_rendicion, _ = _rendicion_finalizada()
    for rendicion in (vieja_rendicion, reciente_rendicion):
        solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)
        servicio.generar_pdf_descarga(solicitud.pk, solicitud.token)
    vieja = RendicionPdfDescarga.objects.get(rendicion=vieja_rendicion)
    RendicionPdfDescarga.objects.filter(pk=vieja.pk).update(
        fecha_fin=timezone.now() - timedelta(days=8)
    )

    assert servicio.purgar_pdfs_descarga() == 1

    assert not RendicionPdfDescarga.objects.filter(pk=vieja.pk).exists()
    assert not (media / vieja.archivo.name).exists()
    reciente = RendicionPdfDescarga.objects.get(rendicion=reciente_rendicion)
    assert (media / reciente.archivo.name).exists()


def test_solicitar_view_rechaza_rendicion_no_finalizada(client, superuser, send_task):
    rendicion = RendicionCuentaMensual.objects.create(
        mes=6, anio=2026, estado=RendicionCuentaMensual.ESTADO_REVISION
    )
    client.force_login(superuser)

    response = client.post(
        reverse(
            "rendicioncuentasmensual_download_pdf_solicitar",
            kwargs={"pk": rendicion.pk},
        )
    )

    assert response.status_code == 400
    assert response.json()["estado"] == "error"
    assert "finalizada" in response.json()["mensaje"]
    send_task.assert_not_called()
    assert not RendicionPdfDescarga.objects.exists()


def test_estado_view_informa_url_de_descarga_cuando_esta_listo(
    media, client, superuser, send_task, django_capture_on_commit_callbacks
):
    rendicion, _ = _rendicion_finalizada()
    client.force_login(superuser)
    estado_url = reverse(
        "rendicioncuentasmensual_download_pdf_estado", kwargs={"pk": rendicion.pk}
    )
    assert client.get(estado_url).json() == {"estado": "sin_solicitar", "mensaje": ""}

    solicitud = _solicitar(rendicion, django_capture_on_commit_callbacks)
    servicio.generar_pdf_descarga(solicitud.pk, solicitud.token)

    assert client.get(estado_url).json() == {
        "estado": "listo",
        "mensaje": "",
        "url_descarga": reverse(
            "rendicioncuentasmensual_download_pdf", kwargs={"pk": rendicion.pk}
        ),
    }


def test_descarga_sin_pdf_listo_redirige_al_detalle_sin_generar(
    media, client, superuser, mocker
):
    rendicion, _ = _rendicion_finalizada()
    generar = mocker.patch.object(
        servicio.RendicionCuentaMensualService, "generar_pdf_descarga_rendicion"
    )
    client.force_login(superuser)

    response = client.get(
        reverse("rendicioncuentasmensual_download_pdf", kwargs={"pk": rendicion.pk})
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "rendicioncuentasmensual_detail", kwargs={"pk": rendicion.pk}
    )
    generar.assert_not_called()


def test_descarga_requiere_permiso_de_rendiciones(client, django_user_model):
    rendicion = RendicionCuentaMensual.objects.create(
        mes=6, anio=2026, estado=RendicionCuentaMensual.ESTADO_FINALIZADA
    )
    usuario = django_user_model.objects.create_user(username="sin-permiso")
    client.force_login(usuario)

    for nombre in (
        "rendicioncuentasmensual_download_pdf",
        "rendicioncuentasmensual_download_pdf_estado",
    ):
        response = client.get(reverse(nombre, kwargs={"pk": rendicion.pk}))
        assert response.status_code in (302, 403)
    response = client.post(
        reverse(
            "rendicioncuentasmensual_download_pdf_solicitar",
            kwargs={"pk": rendicion.pk},
        )
    )
    assert response.status_code in (302, 403)
    assert not RendicionPdfDescarga.objects.exists()


def test_celery_descubre_solo_tareas_de_apps_instaladas(mocker):
    mocker.patch(
        "django.apps.apps.is_installed",
        side_effect=lambda nombre: nombre == "rendicioncuentasmensual",
    )

    assert celery_config._task_packages() == [  # pylint: disable=protected-access
        "rendicioncuentasmensual"
    ]


def test_beat_envia_la_purga_a_la_cola_de_comedores():
    entrada = celery_config.app.conf.beat_schedule["rendiciones-purgar-pdfs-descarga"]

    assert entrada["task"] == "rendicioncuentasmensual.tasks.purgar_pdfs_descarga"
    assert entrada["options"]["queue"] == "comedores"
