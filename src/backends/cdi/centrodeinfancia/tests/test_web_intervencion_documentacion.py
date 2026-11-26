"""CDI06/CDI-F2: intervention detail and authenticated document download (web API, G1 v1).

The download resolves the object by primary key inside the actor's scope and
serves the bytes the storage holds for that object; the client never names a
path. Rejections answer 404 without revealing other files and write nothing.
"""

import re

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.models import CentroDeInfancia, IntervencionCentroInfancia
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia

API = "/api/web/cdi/"
VER = "centrodeinfancia.view_centrodeinfancia"
BAJA = "centrodeinfancia.delete_intervencioncentroinfancia"
CONTENIDO = b"%PDF-1.4 contenido sintetico"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _usuario(username, *, perms=(VER, BAJA), superuser=False, grupos=()):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    return _ready(user)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True, name="media")
def media_fixture(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Sintético", provincia=Provincia.objects.create(nombre="Mendoza")
    )


@pytest.fixture(name="intervencion")
def intervencion_fixture(centro):
    return IntervencionCentroInfancia.objects.create(
        centro=centro,
        observaciones="Visita sintética.",
        tiene_documentacion=True,
        documentacion=SimpleUploadedFile("acta.pdf", CONTENIDO),
    )


def _detalle(pk):
    return f"{API}intervenciones/{pk}/"


def _descarga(pk):
    return f"{API}intervenciones/{pk}/documentacion/"


def _baja(pk):
    return f"{API}intervenciones/{pk}/documentacion/eliminar/"


def _estado(pk):
    fila = IntervencionCentroInfancia.all_objects.get(pk=pk)
    return fila.documentacion.name, fila.tiene_documentacion, fila.deleted_at


# --- Detail ---------------------------------------------------------------------


def test_detail_projects_the_native_values(intervencion, centro):
    client = _cliente(_usuario("int-detalle"))

    respuesta = client.get(_detalle(intervencion.pk))
    nativa = client.get(
        reverse("centrodeinfancia_intervencion_detalle", args=[intervencion.pk])
    )

    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert datos["id"] == intervencion.pk
    assert datos["centro"] == {
        "id": centro.pk,
        "nombre": "CDI Sintético",
        "url": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }
    celdas = re.findall(r"<td>\s*(.*?)\s*</td>", nativa.content.decode(), re.S)
    assert datos["fecha"] in celdas
    for campo in (
        "tipo_intervencion",
        "subintervencion",
        "destinatario",
        "forma_contacto",
        "observaciones",
    ):
        assert datos[campo] in celdas, campo
    assert datos["observaciones"] == "Visita sintética."
    assert datos["documentacion"]["name"] == intervencion.documentacion.name
    assert datos["documentacion"]["descargar"] == _descarga(intervencion.pk)
    assert datos["documentacion"]["eliminar"] is None


def test_detail_offers_delete_to_superusers_only_and_none_without_document(centro):
    sin_archivo = IntervencionCentroInfancia.objects.create(centro=centro)
    con_archivo = IntervencionCentroInfancia.objects.create(
        centro=centro, documentacion=SimpleUploadedFile("b.pdf", CONTENIDO)
    )
    root = _cliente(_usuario("int-root", superuser=True))

    assert root.get(_detalle(sin_archivo.pk)).json()["documentacion"] is None
    assert root.get(_detalle(con_archivo.pk)).json()["documentacion"]["eliminar"] == (
        _baja(con_archivo.pk)
    )


def test_detail_outside_the_scope_is_404(intervencion):
    egp = _cliente(_usuario("int-detalle-egp", grupos=[UserGroups.SIMEPI_EGP]))

    assert egp.get(_detalle(intervencion.pk)).status_code == 404


# --- Download -------------------------------------------------------------------


def test_download_serves_the_stored_bytes_with_controlled_headers(intervencion):
    respuesta = _cliente(_usuario("int-descarga")).get(_descarga(intervencion.pk))

    assert respuesta.status_code == 200
    assert b"".join(respuesta.streaming_content) == CONTENIDO
    assert respuesta["Content-Disposition"].startswith("attachment; filename=")
    assert "acta" in respuesta["Content-Disposition"]
    assert "private" in respuesta["Cache-Control"]
    assert "no-store" in respuesta["Cache-Control"]
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert "Cookie" in respuesta["Vary"]


def test_download_head_and_other_methods(intervencion):
    client = _cliente(_usuario("int-metodos"))

    assert client.head(_descarga(intervencion.pk)).status_code == 200
    assert client.post(_descarga(intervencion.pk)).status_code in (403, 405)


def test_download_ignores_client_supplied_paths(intervencion):
    client = _cliente(_usuario("int-path"))

    respuesta = client.get(
        _descarga(intervencion.pk), {"path": "../../etc/passwd", "name": "x"}
    )

    assert b"".join(respuesta.streaming_content) == CONTENIDO


def test_download_hides_foreign_deleted_absent_and_missing_files(
    intervencion, centro, media
):
    client = _cliente(_usuario("int-oculto"))
    egp = _cliente(_usuario("int-egp", grupos=[UserGroups.SIMEPI_EGP]))
    sin_archivo = IntervencionCentroInfancia.objects.create(centro=centro)
    borrada = IntervencionCentroInfancia.objects.create(
        centro=centro, documentacion=SimpleUploadedFile("c.pdf", CONTENIDO)
    )
    borrada.delete()

    assert egp.get(_descarga(intervencion.pk)).status_code == 404
    assert client.get(_descarga(sin_archivo.pk)).status_code == 404
    assert client.get(_descarga(borrada.pk)).status_code == 404
    assert client.get(_descarga(999999)).status_code == 404
    assert client.get(_descarga(intervencion.pk)).status_code == 200
    for archivo in media.rglob("acta*"):
        archivo.unlink()
    assert client.get(_descarga(intervencion.pk)).status_code == 404


def test_download_requires_the_view_permission_and_the_gate(intervencion):
    sin_permiso = _cliente(_usuario("int-sin-permiso", perms=()))
    pendiente = _usuario("int-pendiente")
    pendiente.profile.must_change_password = True
    pendiente.profile.save()

    anonimo = Client().get(_descarga(intervencion.pk))

    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert sin_permiso.get(_descarga(intervencion.pk)).status_code == 403
    bloqueado = _cliente(pendiente).get(_descarga(intervencion.pk))
    assert bloqueado.status_code == 403
    assert bloqueado.json()["detail"] == web_gate.DETAIL_REQUIREMENT


# --- Delete ---------------------------------------------------------------------


def test_delete_removes_the_file_and_the_flag_and_redirects_with_the_message(
    intervencion, centro, media
):
    client = _cliente(_usuario("int-baja", superuser=True))
    ruta = media / intervencion.documentacion.name

    respuesta = client.post(_baja(intervencion.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }
    assert _estado(intervencion.pk) == ("", False, None)
    assert not ruta.exists()
    mensajes = client.get(_detalle(intervencion.pk)).json()["messages"]
    assert mensajes == [
        {"message": "El archivo fue eliminado correctamente.", "level": "success"}
    ]


def test_delete_rejections_change_nothing(intervencion):
    antes = _estado(intervencion.pk)
    egp = _cliente(_usuario("int-baja-egp", grupos=[UserGroups.SIMEPI_EGP]))
    sin_permiso = _cliente(_usuario("int-baja-sin", perms=(VER,)))
    pendiente = _usuario("int-baja-pendiente")
    pendiente.profile.must_change_password = True
    pendiente.profile.save()

    assert egp.post(_baja(intervencion.pk)).status_code == 404
    assert sin_permiso.post(_baja(intervencion.pk)).status_code == 403
    assert _cliente(pendiente).post(_baja(intervencion.pk)).status_code == 403
    assert Client().post(_baja(intervencion.pk)).status_code == 401
    obtener = _cliente(_usuario("int-baja-get")).get(_baja(intervencion.pk))
    assert obtener.status_code == 405
    assert _estado(intervencion.pk) == antes


def test_delete_without_csrf_token_is_rejected(intervencion):
    client = Client(enforce_csrf_checks=True)
    client.force_login(_usuario("int-baja-csrf"))
    antes = _estado(intervencion.pk)

    assert client.post(_baja(intervencion.pk)).status_code == 403
    assert _estado(intervencion.pk) == antes


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


@pytest.mark.usefixtures("runtime")
def test_runtime_download_needs_a_signed_get(intervencion):
    user = _usuario("int-runtime")
    client = _cliente(user)
    target = _descarga(intervencion.pk)

    sin_firma = client.get(target, RAW_URI=target)
    firmada = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=web_gate.sign(
            audience="cdi",
            user_pk=user.pk,
            session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
            method="GET",
            target=target,
        ),
    )

    assert sin_firma.status_code == 403
    assert firmada.status_code == 200
    assert b"".join(firmada.streaming_content) == CONTENIDO


def test_admindocs_head_does_not_bypass_the_download(intervencion):
    staff = User.objects.create_user("int-staff", is_staff=True)

    respuesta = _cliente(_ready(staff)).head(_descarga(intervencion.pk))

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403
