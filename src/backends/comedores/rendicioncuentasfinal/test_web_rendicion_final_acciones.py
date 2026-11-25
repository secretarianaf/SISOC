"""POST actions of the final rendición web API (RF01.02, RF01.03).

Each action repeats the native view's effects (state, timestamp, history, file in
native storage) and message; the web API additionally needs
``view_rendicioncuentasfinal`` and a CSRF token.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from comedores.models import Comedor
from historial.models import Historial
from rendicioncuentasfinal.models import DocumentoRendicionFinal
from rendicioncuentasfinal.test_web_rendicion_final_api import (  # noqa: F401  # pylint: disable=unused-import
    BASE,
    VIEW,
    _client,
    _documentos,
    _usuario,
    estados_fixture,
    lector_fixture,
    tipos_fixture,
)

pytestmark = pytest.mark.django_db
TOKEN = "t" * 64


def _accion(usuario):
    client = Client(enforce_csrf_checks=True)
    client.force_login(usuario)
    client.cookies["csrftoken"] = TOKEN
    return client


def _post(client, url, data=None):
    return client.post(url, data or {}, HTTP_X_CSRFTOKEN=TOKEN)


def _doc_url(documento, accion):
    return f"{BASE}documentos/{documento.pk}/{accion}/"


@pytest.fixture(name="escenario")
def escenario_fixture(estados, tipos, lector):
    rendicion, docs = _documentos(
        Comedor.objects.create(nombre="Acciones"), estados, tipos
    )
    return rendicion, docs, _accion(lector)


def _historial(documento):
    return list(
        Historial.objects.filter(object_id=str(documento.pk))
        .order_by("id")
        .values_list("accion", "usuario__username")
    )


def test_validar_writes_state_history_and_message(escenario):
    _, docs, client = escenario

    # Kept: no state guard, so a document in «Subsanar» validates too.
    respuesta = _post(client, _doc_url(docs["Contable"], "validar"))

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["ok"] is True
    assert data["message"] == "Documento validado correctamente."
    assert data["documento"]["estado"] == "Validado"
    docs["Contable"].refresh_from_db()
    assert docs["Contable"].estado.nombre == "Validado"
    assert docs["Contable"].fecha_modificacion is not None
    assert _historial(docs["Contable"]) == [("Validar documento", "lector_rf")]


def test_subsanar_with_text_and_with_empty_observation(escenario):
    _, docs, client = escenario

    respuesta = _post(
        client, _doc_url(docs["Dupla"], "subsanar"), {"observacion": "Falta <sello>"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Documento enviado a subsanar correctamente."
    docs["Dupla"].refresh_from_db()
    assert (docs["Dupla"].estado.nombre, docs["Dupla"].observaciones) == (
        "Subsanar",
        "Falta <sello>",
    )
    assert _historial(docs["Dupla"]) == [("Enviar a subsanar documento", "lector_rf")]
    # An empty observation is accepted (the native view does not validate).
    assert _post(client, _doc_url(docs["Legales"], "subsanar")).status_code == 200
    docs["Legales"].refresh_from_db()
    assert docs["Legales"].observaciones == ""


def test_switch_flips_twice_without_history(escenario):
    rendicion, _, client = escenario
    url = f"{BASE}{rendicion.pk}/fisicamente_presentada/"

    primero = _post(client, url).json()
    segundo = _post(client, url).json()

    assert (primero["fisicamente_presentada"], segundo["fisicamente_presentada"]) == (
        True,
        False,
    )
    assert primero["message"] == "Estado de revisión actualizado."
    assert Historial.objects.count() == 0


def test_eliminar_clears_the_file_and_resets_the_state(escenario):
    _, docs, client = escenario

    respuesta = _post(client, _doc_url(docs["Dupla"], "eliminar"))

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Documento eliminado correctamente."
    docs["Dupla"].refresh_from_db()
    assert docs["Dupla"].estado.nombre == "No presentado"
    assert not docs["Dupla"].documento
    assert _historial(docs["Dupla"]) == [("Documento eliminado", "lector_rf")]


def test_adjuntar_stores_the_file_in_native_storage(escenario, tmp_path):
    _, docs, client = escenario
    archivo = SimpleUploadedFile("comprobante.pdf", b"%PDF-1", "application/pdf")

    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = _post(
            client,
            f"{BASE}documentos/adjuntar/",
            {"documento_id": docs["Contable"].pk, "archivo": archivo},
        )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Archivo adjuntado correctamente.",
    }
    docs["Contable"].refresh_from_db()
    assert docs["Contable"].estado.nombre == "En análisis"
    assert docs["Contable"].documento.name.startswith(
        "rendicion_cuentas_final/comprobante"
    )
    assert _historial(docs["Contable"]) == [("Adjuntar documento", "lector_rf")]


def test_adjuntar_without_file_is_the_native_error_and_unknown_id_404(escenario):
    _, docs, client = escenario
    url = f"{BASE}documentos/adjuntar/"

    sin_archivo = _post(client, url, {"documento_id": docs["Dupla"].pk})

    assert sin_archivo.status_code == 400
    assert sin_archivo.json() == {
        "ok": False,
        "message": "No se seleccionó ningún archivo.",
    }
    assert _post(client, url, {"documento_id": 999999}).status_code == 404
    assert _post(client, url).status_code == 404


def test_crear_custom_document_with_and_without_file(escenario, tmp_path):
    rendicion, _, client = escenario
    url = f"{BASE}{rendicion.pk}/crear/"

    with override_settings(MEDIA_ROOT=tmp_path):
        con = _post(
            client,
            url,
            {"nombre": "  Acta  ", "archivo": SimpleUploadedFile("a.pdf", b"x")},
        )
        sin = _post(client, url, {"nombre": "Nota"})

    assert (con.status_code, sin.status_code) == (200, 200)
    acta = rendicion.documentos.get(tipo__nombre="Acta")
    nota = rendicion.documentos.get(tipo__nombre="Nota")
    assert acta.tipo.personalizado and acta.estado.nombre == "En análisis"
    assert nota.estado.nombre == "No presentado" and not nota.documento
    assert [a for a, _ in _historial(acta)] == [
        "Crear documento personalizado",
        "Adjuntar documento",
    ]


RUTAS = [
    "documentos/{d}/validar/",
    "documentos/{d}/subsanar/",
    "documentos/{d}/eliminar/",
    "{r}/crear/",
    "{r}/fisicamente_presentada/",
    "documentos/adjuntar/",
]


@pytest.mark.parametrize("ruta", RUTAS)
def test_actions_need_login_permission_csrf_and_post(escenario, ruta):
    rendicion, docs, client = escenario
    url = BASE + ruta.format(d=docs["Dupla"].pk, r=rendicion.pk)
    antes = list(DocumentoRendicionFinal.objects.values_list("pk", "estado_id"))

    assert Client().post(url).status_code == 401
    assert (
        _post(
            _accion(_usuario("sin_acc_rf", "comedores.view_comedor")), url
        ).status_code
        == 403
    )
    sin_csrf = Client(enforce_csrf_checks=True)
    sin_csrf.force_login(_usuario("csrf_rf", VIEW))
    assert sin_csrf.post(url).status_code == 403
    assert client.get(url).status_code == 405
    assert list(DocumentoRendicionFinal.objects.values_list("pk", "estado_id")) == antes
    assert Historial.objects.count() == 0


def test_actions_on_missing_objects_are_404(escenario):
    _, _, client = escenario
    for ruta in (
        "documentos/999999/validar/",
        "documentos/999999/subsanar/",
        "documentos/999999/eliminar/",
        "999999/crear/",
        "999999/fisicamente_presentada/",
    ):
        assert _post(client, BASE + ruta).status_code == 404, ruta
