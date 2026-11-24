"""Canonical direct create and edit are distinct from the operational modal."""

from types import ModuleType

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse

from comedores.models import Comedor, Referente
from config.urls_all import urlpatterns as monolith_patterns
from relevamientos.models import Relevamiento
from relevamientos.web_preview import relevamientos_preview_patterns

API = "/api/web/comedores/relevamientos"
pytestmark = pytest.mark.django_db


@pytest.fixture
def editor():
    user = get_user_model().objects.create_user("direct_editor")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=("add_relevamiento", "change_relevamiento"),
        )
    )
    client = Client()
    client.force_login(user)
    return client


def test_create_returns_native_form_and_invalid_submission_does_not_write(editor):
    comedor = Comedor.objects.create(nombre="Comedor de prueba")
    url = f"{API}/{comedor.pk}/relevamiento/crear/"

    response = editor.get(url)

    assert response.status_code == 200
    assert response.json()["comedor"] == {"id": comedor.pk, "nombre": comedor.nombre}
    assert response.json()["urls"]["cancelar"] == reverse(
        "relevamientos", args=[comedor.pk]
    )
    assert response.json()["relevamiento"] is None

    invalid = editor.post(url, {"observacion": "Dato preservado"})

    assert invalid.status_code == 400
    fields = {
        field["name"]: field for field in invalid.json()["forms"]["root"]["fields"]
    }
    assert fields["responsable_es_referente"]["errors"]
    assert "Dato preservado" in str(fields["observacion"]["nodes"])
    assert not Relevamiento.objects.filter(comedor=comedor).exists()


def test_edit_requires_the_comedor_relation_for_read_and_write(editor):
    comedor = Comedor.objects.create(nombre="Comedor del relevamiento")
    otro = Comedor.objects.create(nombre="Otro comedor")
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, observacion="Sin cambios"
    )
    url = f"{API}/{comedor.pk}/relevamiento/{relevamiento.pk}/editar/"
    wrong = f"{API}/{otro.pk}/relevamiento/{relevamiento.pk}/editar/"
    canonical = reverse("relevamiento_editar", args=[otro.pk, relevamiento.pk])

    response = editor.get(url)
    assert response.status_code == 200
    assert response.json()["relevamiento"]["id"] == relevamiento.pk
    assert editor.get(wrong).status_code == 404
    assert editor.post(wrong, {"observacion": "No se guarda"}).status_code == 404
    assert editor.get(canonical).status_code == 404
    assert editor.post(canonical, {"observacion": "No se guarda"}).status_code == 404
    relevamiento.refresh_from_db()
    assert relevamiento.comedor_id == comedor.pk
    assert relevamiento.observacion == "Sin cambios"


def _form_data(response):
    datos = {}
    for form in response.json()["forms"].values():
        for field in form["fields"]:
            for node in field["nodes"]:
                if isinstance(node, str) or node["t"] not in (
                    "input",
                    "select",
                    "textarea",
                ):
                    continue
                attrs = node["a"]
                if "disabled" in attrs:
                    continue
                if node["t"] == "select":
                    options = [
                        option["a"]
                        for option in node["c"]
                        if isinstance(option, dict) and option["t"] == "option"
                    ]
                    selected = [a["value"] for a in options if "selected" in a]
                    if "multiple" in attrs:
                        datos[field["name"]] = selected
                    elif options:
                        datos[field["name"]] = (
                            selected[0] if selected else options[0]["value"]
                        )
                elif node["t"] == "input" and attrs.get("type") not in (
                    "checkbox",
                    "radio",
                ):
                    datos[field["name"]] = attrs.get("value", "")
                elif node["t"] == "textarea":
                    datos[field["name"]] = "".join(
                        c for c in node["c"] if isinstance(c, str)
                    )
    return datos


def test_create_and_edit_save_the_visible_form_and_keep_the_existing_associations(
    editor,
):
    comedor = Comedor.objects.create(nombre="Comedor de prueba")
    crear = f"{API}/{comedor.pk}/relevamiento/crear/"
    initial = editor.get(crear)
    assert initial.status_code == 200
    assert "existe_punto_entregas" in {
        field["name"]
        for field in initial.json()["forms"]["punto_entregas_form"]["fields"]
    }
    assert not {"cocina", "prestacion"} & {
        field["name"] for field in initial.json()["forms"]["espacio_form"]["fields"]
    }
    data = _form_data(initial)
    data.update(
        observacion="Alto nivel",
        existe_punto_entregas="True",
        responsable_es_referente="False",
        nombre="Responsable sintético",
    )
    response = editor.post(crear, data)

    assert response.status_code == 200, {
        key: {f["name"]: f["errors"] for f in form["fields"] if f["errors"]}
        for key, form in response.json().get("forms", {}).items()
    }
    relevamiento = Relevamiento.objects.get(comedor=comedor)
    assert response.json()["redirect"] == reverse(
        "relevamiento_detalle", args=[comedor.pk, relevamiento.pk]
    )
    assert relevamiento.observacion == "Alto nivel"
    assert relevamiento.punto_entregas.existe_punto_entregas
    assert relevamiento.responsable_relevamiento.nombre == "Responsable sintético"
    responsable_id = relevamiento.responsable_relevamiento_id
    espacio_id = relevamiento.espacio_id
    editar = f"{API}/{comedor.pk}/relevamiento/{relevamiento.pk}/editar/"
    data = _form_data(editor.get(editar))
    assert data["observacion"] == "Alto nivel"
    assert data["responsable_es_referente"] == "False"
    assert data["nombre"] == "Responsable sintético"
    data.update(observacion="Observación corregida", existe_punto_entregas="False")

    edit_response = editor.post(editar, data)
    assert edit_response.status_code == 200
    assert edit_response.json()["redirect"] == response.json()["redirect"]
    relevamiento.refresh_from_db()
    assert relevamiento.observacion == "Observación corregida"
    assert not relevamiento.punto_entregas.existe_punto_entregas
    assert relevamiento.espacio_id == espacio_id
    assert relevamiento.responsable_relevamiento_id == responsable_id
    assert Relevamiento.objects.filter(comedor=comedor).count() == 1


def test_editor_requires_session_write_permission_and_csrf(editor):
    comedor = Comedor.objects.create(nombre="Comedor protegido")
    url = f"{API}/{comedor.pk}/relevamiento/crear/"
    secured = Client(enforce_csrf_checks=True)
    secured.cookies = editor.cookies.copy()
    assert secured.post(url, {}).status_code == 403

    user = get_user_model().objects.get(username="direct_editor")
    user.user_permissions.clear()
    assert editor.get(url).status_code == 403
    assert editor.post(url, {}).status_code == 403
    assert Client().get(url).status_code in {401, 403}
    assert not Relevamiento.objects.filter(comedor=comedor).exists()


def test_preview_serves_canonical_form_and_preserves_native_guard(editor, tmp_path):
    (tmp_path / "index.html").write_text(
        "<div id='root'>SISOC-React</div>", encoding="utf-8"
    )
    module = ModuleType("relevamientos_editor_test_urls")
    module.urlpatterns = relevamientos_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    comedor = Comedor.objects.create(nombre="Comedor de prueba")
    otro = Comedor.objects.create(nombre="Otro comedor")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    create = reverse("relevamiento_crear", args=[comedor.pk])
    edit = reverse("relevamiento_editar", args=[comedor.pk, relevamiento.pk])
    wrong = reverse("relevamiento_editar", args=[otro.pk, relevamiento.pk])

    with override_settings(ROOT_URLCONF=module):
        for url in (create, edit):
            response = editor.get(url)
            assert response.status_code == 200
            assert b"SISOC-React" in response.content
            assert "csrftoken" in response.cookies
            assert Client().get(url).status_code == 403
        assert editor.get(wrong).status_code == 404

    assert b"SISOC-React" not in editor.get(create).content


def test_list_and_detail_disclose_editor_links_only_for_the_matching_permission(editor):
    comedor = Comedor.objects.create(nombre="Comedor visible")
    relevamiento = Relevamiento.objects.create(comedor=comedor)
    user = get_user_model().objects.get(username="direct_editor")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    list_url = f"{API}/{comedor.pk}/"
    detail_url = f"{API}/{comedor.pk}/relevamiento/{relevamiento.pk}/"

    assert editor.get(list_url).json()["urls"]["crear_formulario"] == reverse(
        "relevamiento_crear", args=[comedor.pk]
    )
    assert editor.get(detail_url).json()["urls"]["editar_formulario"] == reverse(
        "relevamiento_editar", args=[comedor.pk, relevamiento.pk]
    )
    user.user_permissions.remove(
        *user.user_permissions.exclude(codename="view_relevamiento")
    )
    assert editor.get(list_url).json()["urls"]["crear_formulario"] is None
    assert editor.get(detail_url).json()["urls"]["editar_formulario"] is None


def test_create_with_existing_referente_links_it_without_duplicate(editor):
    referente = Referente.objects.create(nombre="Referente del comedor")
    comedor = Comedor.objects.create(
        nombre="Comedor con referente", referente=referente
    )
    url = f"{API}/{comedor.pk}/relevamiento/crear/"
    initial = editor.get(url)
    assert initial.json()["tiene_referente"] is True
    data = _form_data(initial)
    data.update(responsable_es_referente="True")

    response = editor.post(url, data)

    assert response.status_code == 200
    assert (
        Relevamiento.objects.get(comedor=comedor).responsable_relevamiento == referente
    )
    assert list(Referente.objects.values_list("pk", flat=True)) == [referente.pk]
