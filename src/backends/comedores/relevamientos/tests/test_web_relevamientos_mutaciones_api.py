"""Mutations of the relevamiento pages (R01.02): Numero de IF, baja and coordinator review.

Each test goes through the public API and compares the persisted effect with
what the native view does (``RelevamientoListView.post``,
``RelevamientoDeleteView`` and ``RelevamientoRevisionCoordinadorView``).
"""

from datetime import datetime, timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client

from comedores.models import Comedor
from core import web_gate
from relevamientos.models import Relevamiento

VIEW = "relevamientos.view_relevamiento"
CHANGE = "relevamientos.change_relevamiento"
REVIEW = "relevamientos.review_relevamiento"
API = "/api/web/comedores/relevamientos/"
FECHA = datetime(2026, 3, 4, 15, 7, tzinfo=dt_timezone.utc)

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="comedor_mut")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor <Mut>")


@pytest.fixture(name="rel")
def rel_fixture(comedor_mut):
    return Relevamiento.objects.create(
        comedor=comedor_mut, estado="Finalizado", fecha_visita=FECHA, numero_if="IF-1"
    )


# --- Numero de IF --------------------------------------------------------------


def _if(client, comedor, rel, valor, **extra):
    return client.post(
        f"{API}{comedor.pk}/relevamiento/numero-if/",
        {"relevamiento_id": rel.pk, "numero_if": valor},
        **extra,
    )


def test_numero_if_updates_like_the_native_post(comedor_mut, rel):
    editor = _client(_usuario("editor_if_mut", VIEW, CHANGE))

    respuesta = _if(editor, comedor_mut, rel, "  IF-2  ")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta.json() == {
        "ok": True,
        "message": "Número de IF actualizado correctamente.",
        "redirect": f"/comedores/{comedor_mut.pk}/relevamiento/listar",
        "numero_if": "IF-2",
    }
    rel.refresh_from_db()
    assert rel.numero_if == "IF-2"
    # The native POST does the same through the page.
    nativo = editor.post(
        f"/comedores/{comedor_mut.pk}/relevamiento/listar",
        {"relevamiento_id": rel.pk, "numero_if": "IF-3"},
    )
    assert nativo.status_code == 302
    rel.refresh_from_db()
    assert rel.numero_if == "IF-3"


def test_numero_if_empty_goes_to_null(comedor_mut, rel):
    editor = _client(_usuario("vacio_if_mut", VIEW, CHANGE))

    respuesta = _if(editor, comedor_mut, rel, "   ")

    assert respuesta.status_code == 200 and respuesta.json()["numero_if"] is None
    rel.refresh_from_db()
    assert rel.numero_if is None


def test_numero_if_without_change_permission_is_403_and_untouched(comedor_mut, rel):
    lector = _client(_usuario("lector_if_mut", VIEW))

    respuesta = _if(lector, comedor_mut, rel, "IF-9")

    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detail": "No tiene permisos para editar el Número de IF."
    }
    rel.refresh_from_db()
    assert rel.numero_if == "IF-1"


def test_numero_if_of_another_comedor_confirms_without_change(comedor_mut, rel):
    otro = Comedor.objects.create(nombre="Otro")
    editor = _client(_usuario("otro_if_mut", VIEW, CHANGE))

    respuesta = _if(editor, otro, rel, "IF-9")

    assert respuesta.status_code == 200
    rel.refresh_from_db()
    assert rel.numero_if == "IF-1"
    assert _if(editor, comedor_mut, rel, "IF-1").status_code == 200


def test_numero_if_longer_than_255_is_400_and_untouched(comedor_mut, rel):
    editor = _client(_usuario("largo_if_mut", VIEW, CHANGE))

    respuesta = _if(editor, comedor_mut, rel, "x" * 256)

    assert respuesta.status_code == 400
    error = respuesta.json()["errors"]["numero_if"][0]
    assert error["code"] == "max_length" and "255" in error["message"]
    assert _if(editor, comedor_mut, rel, "x" * 255).status_code == 200


def test_numero_if_needs_csrf_login_and_post(comedor_mut, rel):
    editor = _usuario("csrf_if_mut", VIEW, CHANGE)
    estricto = _client(editor, enforce_csrf_checks=True)
    url = f"{API}{comedor_mut.pk}/relevamiento/numero-if/"

    assert _if(estricto, comedor_mut, rel, "IF-9").status_code == 403
    assert Client().post(url, {}).status_code == 401
    assert _client(editor).get(url).status_code == 405
    rel.refresh_from_db()
    assert rel.numero_if == "IF-1"
    anonimo = Client().post(url, {})
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


# --- Baja ----------------------------------------------------------------------


def _baja(comedor, rel):
    return f"{API}{comedor.pk}/relevamiento/{rel.pk}/eliminar/"


def test_baja_confirmation_projects_the_native_preview(comedor_mut, rel):
    editor = _client(_usuario("baja_get_mut", CHANGE))

    respuesta = editor.get(_baja(comedor_mut, rel))

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["id"] == rel.pk and data["nombre"] == str(rel)
    assert (data["confirm_text"], data["cancel_text"]) == ("Dar de baja", "Cancelar")
    assert data["cancel_url"] == f"/comedores/{comedor_mut.pk}/relevamiento/{rel.pk}"
    preview = data["cascade_preview"]
    assert preview["total_afectados"] >= 1
    assert {i["modelo"] for i in preview["desglose_por_modelo"]}
    nativa = editor.get(f"/comedores/{comedor_mut.pk}/relevamiento/{rel.pk}/eliminar")
    assert nativa.status_code == 200
    assert f"{preview['total_afectados']}" in nativa.content.decode()


def test_baja_soft_deletes_and_redirects_to_the_comedor(comedor_mut, rel):
    editor = _client(_usuario("baja_post_mut", CHANGE))

    respuesta = editor.post(_baja(comedor_mut, rel), {})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Acompañamiento Territorial dado de baja correctamente.",
        "redirect": f"/comedores/{comedor_mut.pk}",
    }
    assert not Relevamiento.objects.filter(pk=rel.pk).exists()
    # The message stays queued for the native page the redirect goes to.
    assert "Acompañamiento Territorial dado de baja correctamente." in [
        str(m) for m in get_messages(respuesta.wsgi_request)
    ]
    assert editor.post(_baja(comedor_mut, rel), {}).status_code == 404
    assert editor.get(_baja(comedor_mut, rel)).status_code == 404


def test_baja_needs_change_permission_and_matching_comedor(comedor_mut, rel):
    otro = Comedor.objects.create(nombre="Otro")
    sin = _client(_usuario("baja_sin_mut", VIEW))
    editor = _client(_usuario("baja_ok_mut", CHANGE))

    assert sin.get(_baja(comedor_mut, rel)).status_code == 403
    assert sin.post(_baja(comedor_mut, rel), {}).status_code == 403
    assert Relevamiento.objects.filter(pk=rel.pk).exists()
    assert Client().post(_baja(comedor_mut, rel), {}).status_code == 401
    respuesta = editor.post(_baja(otro, rel), {})
    assert respuesta.status_code == 404
    assert Relevamiento.objects.filter(pk=rel.pk).exists()
    respuesta = editor.post(_baja(comedor_mut, rel), {})
    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == f"/comedores/{comedor_mut.pk}"
    assert not Relevamiento.objects.filter(pk=rel.pk).exists()


def test_baja_post_needs_csrf(comedor_mut, rel):
    estricto = _client(_usuario("baja_csrf_mut", CHANGE), enforce_csrf_checks=True)

    assert estricto.post(_baja(comedor_mut, rel), {}).status_code == 403
    assert Relevamiento.objects.filter(pk=rel.pk).exists()


# --- Review --------------------------------------------------------------------


def _revision(client, comedor, rel, estado, observaciones=""):
    return client.post(
        f"{API}{comedor.pk}/relevamiento/{rel.pk}/revision/",
        {"estado_validacion": estado, "observaciones_coordinador": observaciones},
    )


def test_review_validates_and_stores_the_coordinator(comedor_mut, rel):
    revisor = _usuario("rev_ok_mut", REVIEW)

    respuesta = _revision(_client(revisor), comedor_mut, rel, "Validado", " ok ")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Acompañamiento Territorial validado correctamente.",
        "redirect": f"/comedores/{comedor_mut.pk}/relevamiento/{rel.pk}",
    }
    rel.refresh_from_db()
    assert rel.estado_validacion == "Validado" and rel.observaciones_coordinador == "ok"
    assert rel.coordinador == revisor and rel.fecha_revision_coordinador


def test_review_returns_to_subsanar_with_observations(comedor_mut, rel):
    revisor = _client(_usuario("rev_sub_mut", REVIEW))

    respuesta = _revision(revisor, comedor_mut, rel, "A subsanar", "Corregir")

    assert respuesta.json()["message"] == (
        "Acompañamiento Territorial devuelto al territorial para subsanar."
    )
    rel.refresh_from_db()
    assert rel.estado_validacion == "A subsanar"
    assert _revision(revisor, comedor_mut, rel, "Validado").status_code == 200


def test_review_rejections_keep_the_record_and_map_to_400_and_409(comedor_mut, rel):
    revisor = _client(_usuario("rev_err_mut", REVIEW))
    sin_obs = _revision(revisor, comedor_mut, rel, "A subsanar", "  ")
    invalido = _revision(revisor, comedor_mut, rel, "Otro")

    assert sin_obs.status_code == 400
    assert sin_obs.json() == {
        "errors": {
            "__all__": [
                {
                    "message": "Para devolver el acompañamiento territorial debe indicar qué corregir.",
                    "code": "invalid",
                }
            ]
        }
    }
    assert invalido.status_code == 400
    assert invalido.json()["errors"]["__all__"][0]["message"] == (
        "Seleccione un resultado de revisión válido."
    )
    rel.refresh_from_db()
    assert rel.estado_validacion is None
    _revision(revisor, comedor_mut, rel, "Validado")
    ya = _revision(revisor, comedor_mut, rel, "A subsanar", "x")
    assert ya.status_code == 409
    assert ya.json() == {
        "detail": "El acompañamiento territorial ya está validado: no admite otra revisión."
    }


def test_review_of_an_unsent_relevamiento_is_409(comedor_mut):
    sin_cargar = Relevamiento.objects.create(
        comedor=comedor_mut, estado="Visita pendiente"
    )
    revisor = _client(_usuario("rev_sin_mut", REVIEW))

    respuesta = _revision(revisor, comedor_mut, sin_cargar, "Validado")

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"].startswith("Todavía no hay nada que revisar")
    sin_cargar.refresh_from_db()
    assert sin_cargar.estado_validacion is None


def test_review_access_and_lookup(comedor_mut, rel):
    otro = Comedor.objects.create(nombre="Otro")
    sin = _client(_usuario("rev_perm_mut", VIEW))
    revisor = _client(_usuario("rev_404_mut", REVIEW))
    estricto = _client(_usuario("rev_csrf_mut", REVIEW), enforce_csrf_checks=True)

    assert _revision(sin, comedor_mut, rel, "Validado").status_code == 403
    assert _revision(revisor, otro, rel, "Validado").status_code == 404
    assert _revision(estricto, comedor_mut, rel, "Validado").status_code == 403
    assert (
        Client()
        .post(f"{API}{comedor_mut.pk}/relevamiento/{rel.pk}/revision/", {})
        .status_code
        == 401
    )
    rel.refresh_from_db()
    assert rel.estado_validacion is None


def test_native_review_and_baja_are_untouched(comedor_mut, rel):
    revisor = _client(_usuario("nativo_mut", REVIEW, CHANGE))

    nativa = revisor.post(
        f"/comedores/{comedor_mut.pk}/relevamiento/{rel.pk}/revision",
        {"estado_validacion": "Validado"},
    )
    assert nativa.status_code == 302
    rel.refresh_from_db()
    assert rel.estado_validacion == "Validado"
    baja = revisor.post(f"/comedores/{comedor_mut.pk}/relevamiento/{rel.pk}/eliminar")
    assert baja.status_code == 302 and baja.url == f"/comedores/{comedor_mut.pk}"
    assert not Relevamiento.objects.filter(pk=rel.pk).exists()
