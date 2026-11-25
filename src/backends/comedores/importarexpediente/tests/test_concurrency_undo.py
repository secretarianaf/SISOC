"""MySQL regression tests for concurrent undo operations."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections, connection
from django.db.models.query import QuerySet
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from comedores.models import Comedor
from importarexpediente.models import ArchivosImportados, CambioEstadoImportacion
from importarexpediente import views
from importarexpediente.tests.test_import_flow import _upload_csv


@pytest.mark.django_db(transaction=True)
def test_undo_preserva_cambio_concurrente_de_mes(monkeypatch):
    if connection.vendor != "mysql":
        pytest.skip("Requires real MySQL row locking")
    user = get_user_model().objects.create_user(username="concurrent-undo")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="importarexpediente",
            codename="change_archivosimportados",
        )
    )
    comedor = Comedor.objects.create(nombre="Concurrent", mes_ejecucion=4)
    batch = ArchivosImportados.objects.create(
        usuario=user,
        archivo="test.csv",
        importacion_completada=True,
        fecha_importacion=timezone.now(),
    )
    CambioEstadoImportacion.objects.create(
        archivo_importado=batch,
        comedor=comedor,
        mes_ejecucion_anterior=3,
        mes_ejecucion_nuevo=4,
    )
    waiting, proceed = Event(), Event()
    update = QuerySet.update

    def delayed_update(queryset, **kwargs):
        if queryset.model is Comedor and current_thread().name.startswith("undo"):
            waiting.set()
            assert proceed.wait(15)
        return update(queryset, **kwargs)

    monkeypatch.setattr(QuerySet, "update", delayed_update)

    def undo():
        close_old_connections()
        client = Client()
        client.force_login(user)
        try:
            return client.post(reverse("borrar_datos_importados", args=[batch.pk]))
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="undo") as pool:
        result = pool.submit(undo)
        try:
            assert waiting.wait(15)
            Comedor.all_objects.filter(pk=comedor.pk).update(mes_ejecucion=99)
        finally:
            proceed.set()
        assert result.result(timeout=30).status_code == 302

    comedor.refresh_from_db()
    assert comedor.mes_ejecucion == 99


@pytest.mark.django_db(transaction=True)
def test_deshacer_se_serializa_con_otra_importacion(monkeypatch, settings, tmp_path):
    if connection.vendor != "mysql":
        pytest.skip("Requires real MySQL row locking")
    settings.MEDIA_ROOT = tmp_path
    user = get_user_model().objects.create_user(username="batch-order")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="importarexpediente",
            codename="change_archivosimportados",
        )
    )
    client = Client()
    client.force_login(user)
    first = _upload_csv(
        client, Comedor.objects.create(nombre="first"), expediente_pago="EX-1"
    )
    client.post(reverse("importar_datos", args=[first.pk]))
    first.refresh_from_db()
    assert first.importacion_completada
    second = _upload_csv(
        client, Comedor.objects.create(nombre="second"), expediente_pago="EX-2"
    )
    checked, proceed, imported = Event(), Event(), Event()
    original = views.motivo_no_deshacer_importacion

    def pause_after_check(batch):
        result = original(batch)
        if current_thread().name.startswith("undo-order"):
            checked.set()
            assert proceed.wait(15)
        return result

    monkeypatch.setattr(views, "motivo_no_deshacer_importacion", pause_after_check)

    def post(route, pk, signal=None):
        close_old_connections()
        worker_client = Client()
        worker_client.force_login(user)
        try:
            response = worker_client.post(reverse(route, args=[pk]))
            if signal:
                signal.set()
            return response.status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="undo-order"
    ) as undo_pool:
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="import-order"
        ) as import_pool:
            undo = undo_pool.submit(post, "borrar_datos_importados", first.pk)
            try:
                assert checked.wait(15)
                importing = import_pool.submit(
                    post, "importar_datos", second.pk, imported
                )
                assert not imported.wait(3), "Import committed during an in-flight undo"
            finally:
                proceed.set()
            assert undo.result(timeout=30) == 302
            assert importing.result(timeout=30) == 302
    first.refresh_from_db()
    second.refresh_from_db()
    assert not first.importacion_completada
    assert second.importacion_completada
