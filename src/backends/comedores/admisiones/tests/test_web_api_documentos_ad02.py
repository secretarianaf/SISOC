"""Web API (G1 v1) of the documentation of an admision (AD02.03).

Every test asserts the exact persisted effects, and that a rejected request leaves the
stored data untouched. The answers never carry the Django markup of the row.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from admisiones.models.admisiones import (
    Admision,
    ArchivoAdmision,
    Documentacion,
    TipoConvenio,
)
from admisiones.tests.test_web_api_informe_detalle_ad02 import (
    _cliente,
    _ready,
    _usuario,
)
from comedores.models import Comedor

pytestmark = pytest.mark.django_db


@pytest.fixture(name="admision")
def admision_fixture():
    convenio = TipoConvenio.objects.create(nombre="Personería Jurídica")
    comedor = Comedor.objects.create(nombre="Comedor Documentos")
    return Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        tipo_convenio=convenio,
        estado_admision="documentacion_en_proceso",
    )


@pytest.fixture(name="documentacion")
def documentacion_fixture(admision):
    documentacion = Documentacion.objects.create(nombre="Acta", obligatorio=True)
    documentacion.convenios.add(admision.tipo_convenio)
    return documentacion


@pytest.fixture(name="root")
def root_fixture():
    root = get_user_model().objects.create_superuser("root_documentos")
    return _cliente(_ready(root))


def _api(admision, resto):
    return f"/api/web/comedores/admisiones/{admision.pk}/documentacion/{resto}"


def _pdf(nombre="doc.pdf"):
    return SimpleUploadedFile(nombre, b"%PDF-synthetic")


def _abogado():
    usuario = _usuario("abogado_documentos")
    tipo, _ = ContentType.objects.get_or_create(app_label="auth", model="permission")
    permiso, _ = Permission.objects.get_or_create(
        codename="role_abogado_dupla",
        content_type=tipo,
        defaults={"name": "Rol abogado dupla"},
    )
    usuario.user_permissions.add(permiso)
    return _cliente(usuario)


def test_upload_stores_the_file_cleans_the_if_and_returns_the_row_data(
    admision, documentacion, root
):
    Admision.objects.filter(pk=admision.pk).update(numero_if_tecnico="IF-1")

    respuesta = root.post(
        _api(admision, f"{documentacion.pk}/subir/"), {"archivo": _pdf()}
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["success"] is True
    assert "html" not in datos
    archivo = ArchivoAdmision.objects.get(
        admision=admision, documentacion=documentacion
    )
    assert datos["archivo_id"] == archivo.pk
    assert datos["estado_display"] == archivo.estado == "Documento adjunto"
    assert datos["estado_valor"] == "Documento adjunto"
    assert (
        datos["row_id"] and datos["documento"]["documentacion_id"] == documentacion.pk
    )
    admision.refresh_from_db()
    assert admision.numero_if_tecnico is None
    # A second upload replaces the same row.
    root.post(
        _api(admision, f"{documentacion.pk}/subir/"), {"archivo": _pdf("otro.pdf")}
    )
    assert ArchivoAdmision.objects.filter(admision=admision).count() == 1


def test_upload_without_file_or_by_the_lawyer_changes_nothing(
    admision, documentacion, root
):
    url = _api(admision, f"{documentacion.pk}/subir/")

    sin_archivo = root.post(url, {})
    assert sin_archivo.status_code == 400
    assert sin_archivo.json() == {"success": False, "error": "No se recibio un archivo"}
    abogado = _abogado().post(url, {"archivo": _pdf()})
    assert abogado.status_code == 403
    assert abogado.json() == {
        "success": False,
        "error": "El abogado de la dupla no puede adjuntar archivos.",
    }
    desconocido = root.post(_api(admision, "999999/subir/"), {"archivo": _pdf()})
    assert desconocido.status_code == 400
    assert not ArchivoAdmision.objects.exists()


def test_extra_document_is_created_and_a_rejection_stores_nothing(admision, root):
    url = _api(admision, "personalizada/agregar/")

    sin_nombre = root.post(url, {"nombre": "  ", "archivo": _pdf()})
    sin_archivo = root.post(url, {"nombre": "Nota"})
    assert sin_nombre.status_code == sin_archivo.status_code == 400
    assert sin_nombre.json()["error"] == "Debe indicar un nombre para el documento."
    assert sin_archivo.json()["error"] == "Debe adjuntar un archivo."
    assert not ArchivoAdmision.objects.exists()

    creado = root.post(url, {"nombre": " Nota adicional ", "archivo": _pdf()})

    assert creado.status_code == 201
    datos = creado.json()
    assert datos["success"] is True and "html" not in datos
    archivo = ArchivoAdmision.objects.get(admision=admision)
    assert archivo.nombre_personalizado == "Nota adicional"
    assert archivo.documentacion is None
    assert datos["documento"]["nombre"] == "Nota adicional"


def test_delete_previews_without_changes_then_removes_the_file(admision, root):
    archivo = ArchivoAdmision.objects.create(
        admision=admision,
        nombre_personalizado="Nota",
        archivo=_pdf(),
        estado="Documento adjunto",
    )
    url = _api(admision, f"{archivo.pk}/eliminar/") + f"?archivo_id={archivo.pk}"

    vista = root.delete(url + "&preview=1")
    assert vista.status_code == 200
    assert vista.json()["success"] is True and "preview" in vista.json()
    assert ArchivoAdmision.objects.filter(pk=archivo.pk).exists()

    eliminado = root.delete(url)

    assert eliminado.status_code == 200
    assert eliminado.json() == {
        "success": True,
        "nombre": "Nota",
        "personalizado": True,
    }
    assert not ArchivoAdmision.objects.filter(pk=archivo.pk).exists()


def test_delete_keeps_the_native_guards(admision, root):
    archivo = ArchivoAdmision.objects.create(
        admision=admision,
        nombre_personalizado="Nota",
        archivo=_pdf(),
        estado="Documento adjunto",
    )
    url = _api(admision, f"{archivo.pk}/eliminar/") + f"?archivo_id={archivo.pk}"

    assert _abogado().delete(url).status_code == 403
    assert root.post(url).status_code == 405
    assert root.delete(_api(admision, "999999/eliminar/")).status_code == 404
    Admision.objects.filter(pk=admision.pk).update(
        estado_admision="informe_tecnico_finalizado"
    )
    bloqueado = root.delete(url)
    assert bloqueado.status_code == 400
    assert "No se pueden eliminar documentos" in bloqueado.json()["error"]
    assert ArchivoAdmision.objects.filter(pk=archivo.pk).exists()


def test_documents_keep_the_session_gate_and_the_csrf_check(admision, documentacion):
    urls = (
        ("post", _api(admision, f"{documentacion.pk}/subir/")),
        ("post", _api(admision, "personalizada/agregar/")),
        ("delete", _api(admision, f"{documentacion.pk}/eliminar/")),
    )
    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(_ready(get_user_model().objects.create_superuser("csrf_doc")))
    for metodo, url in urls:
        assert getattr(Client(), metodo)(url).status_code in (401, 403)
        assert getattr(con_csrf, metodo)(url).status_code == 403
    assert not ArchivoAdmision.objects.exists()
