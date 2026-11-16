"""CDI-F2: CDI documents live under the private ``cdi/documentacion/`` prefix.

Covers new uploads, the ``mover_documentacion_cdi`` command (dry-run, apply,
idempotence, Comedores files untouched, missing sources) and the authenticated
download of a moved file.
"""

from io import StringIO

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DataError
from django.test import Client, override_settings
from django.urls import reverse

from centrodeinfancia.management.commands.mover_documentacion_cdi import Command
from centrodeinfancia.models import CentroDeInfancia, IntervencionCentroInfancia
from core.models import Provincia

VER = "centrodeinfancia.view_centrodeinfancia"
CONTENIDO = b"%PDF-1.4 contenido sintetico"
PREFIJO = "cdi/documentacion/"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, name="media")
def media_fixture(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Sintético", provincia=Provincia.objects.create(nombre="Mendoza")
    )


def _legado(media, centro, nombre="acta.pdf", contenido=CONTENIDO):
    """A row saved before the change: file in the shared ``documentacion/``."""
    carpeta = media / "documentacion"
    carpeta.mkdir(exist_ok=True)
    (carpeta / nombre).write_bytes(contenido)
    fila = IntervencionCentroInfancia.objects.create(
        centro=centro, tiene_documentacion=True
    )
    IntervencionCentroInfancia.objects.filter(pk=fila.pk).update(
        documentacion=f"documentacion/{nombre}"
    )
    fila.refresh_from_db()
    return fila


def _mover(*args):
    salida, error = StringIO(), StringIO()
    call_command("mover_documentacion_cdi", *args, stdout=salida, stderr=error)
    return salida.getvalue(), error.getvalue()


def _nombre(pk):
    return IntervencionCentroInfancia.all_objects.get(pk=pk).documentacion.name


def _usuario(username, perms=(VER,)):
    user = User.objects.create_user(username=username)
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def test_new_uploads_land_under_the_cdi_prefix(centro, media):
    fila = IntervencionCentroInfancia.objects.create(
        centro=centro, documentacion=SimpleUploadedFile("nuevo.pdf", CONTENIDO)
    )

    assert fila.documentacion.name.startswith(PREFIJO)
    assert (media / fila.documentacion.name).read_bytes() == CONTENIDO


def test_dry_run_changes_nothing(centro, media):
    fila = _legado(media, centro)

    salida, _ = _mover()

    assert "dry-run" in salida
    assert "MOVER" in salida
    assert _nombre(fila.pk) == "documentacion/acta.pdf"
    assert (media / "documentacion" / "acta.pdf").exists()
    assert not (media / "cdi").exists()


def test_apply_moves_only_cdi_files_and_is_idempotent(centro, media):
    fila = _legado(media, centro)
    ajeno = media / "documentacion" / "comedor.pdf"
    ajeno.write_bytes(b"archivo de comedores")

    salida, _ = _mover("--aplicar")

    nuevo = _nombre(fila.pk)
    assert nuevo.startswith(PREFIJO)
    assert (media / nuevo).read_bytes() == CONTENIDO
    assert not (media / "documentacion" / "acta.pdf").exists()
    assert ajeno.read_bytes() == b"archivo de comedores"
    assert "movidos=1" in salida

    salida2, error2 = _mover("--aplicar")

    assert "movidos=0" in salida2
    assert error2 == ""
    assert _nombre(fila.pk) == nuevo
    assert (media / nuevo).read_bytes() == CONTENIDO


def test_apply_resumes_after_an_interrupted_copy(centro, media):
    fila = _legado(media, centro)
    _mover("--aplicar")
    nuevo = _nombre(fila.pk)
    # Simulate a crash after the copy and before the row update.
    IntervencionCentroInfancia.objects.filter(pk=fila.pk).update(
        documentacion="documentacion/acta.pdf"
    )
    (media / "documentacion" / "acta.pdf").write_bytes(CONTENIDO)

    _mover("--aplicar")

    assert _nombre(fila.pk) == nuevo
    assert sorted(p.name for p in (media / PREFIJO).iterdir()) == [
        nuevo.rsplit("/", 1)[1]
    ]
    assert not (media / "documentacion" / "acta.pdf").exists()


def test_missing_source_is_reported_without_failing(centro, media):
    fila = _legado(media, centro)
    (media / "documentacion" / "acta.pdf").unlink()
    otra = _legado(media, centro, nombre="otra.pdf")

    salida, error = _mover("--aplicar")

    assert f"FALTANTE pk={fila.pk}" in error
    assert "faltantes=1" in salida
    assert _nombre(fila.pk) == "documentacion/acta.pdf"
    assert _nombre(otra.pk).startswith(PREFIJO)


def test_authenticated_download_serves_the_moved_file(centro, media):
    fila = _legado(media, centro)
    _mover("--aplicar")
    url = f"/api/web/cdi/intervenciones/{fila.pk}/documentacion/"
    cliente = Client()
    cliente.force_login(_usuario("mover-ok"))
    sin_permiso = Client()
    sin_permiso.force_login(_usuario("mover-sin-permiso", perms=()))

    respuesta = cliente.get(url)

    assert respuesta.status_code == 200
    assert b"".join(respuesta.streaming_content) == CONTENIDO
    assert Client().get(url).status_code == 401
    assert sin_permiso.get(url).status_code == 403


def test_native_detail_links_to_the_authenticated_download(centro, media):
    fila = _legado(media, centro)
    _mover("--aplicar")
    cliente = Client()
    cliente.force_login(_usuario("mover-nativo"))

    html = cliente.get(
        reverse("centrodeinfancia_intervencion_detalle", args=[fila.pk])
    ).content.decode()

    assert f"/api/web/cdi/intervenciones/{fila.pk}/documentacion/" in html
    assert "/media/" not in html


def test_long_legacy_name_gets_a_destination_that_fits_max_length(centro, media):
    nombre = "a" * 82 + ".pdf"
    fila = _legado(media, centro, nombre=nombre)
    assert len(_nombre(fila.pk)) == 100

    _mover("--aplicar")

    nuevo = _nombre(fila.pk)
    maximo = IntervencionCentroInfancia._meta.get_field("documentacion").max_length
    assert nuevo.startswith(PREFIJO)
    assert nuevo.endswith(".pdf")
    assert len(nuevo) <= maximo
    assert (media / nuevo).read_bytes() == CONTENIDO
    assert not (media / "documentacion" / nombre).exists()


def test_data_error_on_update_is_reported_and_the_copy_removed(
    centro, media, monkeypatch
):
    fila = _legado(media, centro)
    otra = _legado(media, centro, nombre="otra.pdf")
    original = Command._actualizar

    def fallar(pk, origen, destino):
        if pk == fila.pk:
            raise DataError("Data too long")
        return original(pk, origen, destino)

    monkeypatch.setattr(Command, "_actualizar", staticmethod(fallar))

    salida, error = _mover("--aplicar")

    assert f"CONFLICTO pk={fila.pk}" in error
    assert "conflictos=1" in salida
    assert _nombre(fila.pk) == "documentacion/acta.pdf"
    assert (media / "documentacion" / "acta.pdf").exists()
    assert sorted(p.name for p in (media / PREFIJO).iterdir()) == [
        _nombre(otra.pk).rsplit("/", 1)[1]
    ]


def test_old_file_is_kept_when_a_comedores_row_still_uses_it(centro, media):
    fila = _legado(media, centro)
    comedores = apps.get_model("intervenciones", "Intervencion")
    comedores.all_objects.bulk_create(
        [comedores(documentacion="documentacion/acta.pdf")]
    )

    _mover("--aplicar")

    assert _nombre(fila.pk).startswith(PREFIJO)
    assert (media / "documentacion" / "acta.pdf").exists()
