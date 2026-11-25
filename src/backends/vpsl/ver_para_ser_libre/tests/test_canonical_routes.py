import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.urls import reverse

from ver_para_ser_libre.tests.test_workflow import crear_itinerario

pytestmark = pytest.mark.django_db


def test_vpsl_canonical_keeps_guards_and_uses_shell_for_known_get(
    client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    shell_requests = []

    def shell(request, module, asset_path=""):
        shell_requests.append(
            (request.method, module, asset_path, request.META["QUERY_STRING"])
        )
        return HttpResponse(
            '<meta name="sisoc-vpsl-canonical" content="v1"><div id="vpsl-react"></div>'
        )

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)
    list_url = reverse("vpsl_itinerario_list")
    assert client.get(list_url).status_code == 403
    assert shell_requests == []

    superuser = get_user_model().objects.create_superuser(username="vpsl-canonical")
    client.force_login(superuser)
    missing = reverse("vpsl_itinerario_detail", args=[999999])
    assert client.get(missing).status_code == 404
    assert shell_requests == []

    itinerary = crear_itinerario()
    detail_url = reverse("vpsl_itinerario_detail", args=[itinerary.pk])
    page = client.get(detail_url, {"page": 2})
    assert page.status_code == 200
    assert b'id="vpsl-react"' in page.content
    assert shell_requests == [("GET", "vpsl", "", "")]
    assert "private" in page["Cache-Control"]
    head = client.head(detail_url)
    assert head.status_code == 200
    assert head.content == b""
    assert "X-View" in head  # Existing staff diagnostic intercept.

    settings.REACT_VERTICALES_ACTIVAS = ()
    assert b'id="vpsl-react"' not in client.get(detail_url).content
    assert shell_requests == [("GET", "vpsl", "", "")]


def test_missing_vpsl_upstream_keeps_django_and_non_navigation_never_fetches(
    admin_client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    shell_requests = []

    def shell(request, module):
        shell_requests.append((request.method, module))
        return HttpResponse(status=503)

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)

    page = admin_client.get(reverse("vpsl_sede_list"))
    assert page.status_code == 200
    assert page.template_name
    assert shell_requests == [("GET", "vpsl")]

    post = admin_client.post(reverse("vpsl_sede_create"), {})
    assert post.status_code == 200
    assert post.template_name

    autocomplete = admin_client.get(reverse("vpsl_sedes_autocomplete"), {"q": "Nación"})
    assert autocomplete.status_code == 200
    assert autocomplete["Content-Type"].startswith("application/json")
    assert shell_requests == [("GET", "vpsl")]


def test_canonical_jornada_keeps_the_existing_provincial_scope(
    client, settings, monkeypatch
):
    from django.contrib.auth.models import Permission

    from core.models import Provincia
    from ver_para_ser_libre.tests.test_workflow import (
        crear_jornada,
        crear_sede,
        hacer_usuario_provincial,
    )

    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    own_province = Provincia.objects.create(nombre="Buenos Aires")
    other_province = Provincia.objects.create(nombre="Córdoba")
    own = crear_jornada(
        crear_itinerario(provincia=own_province, sedes=[crear_sede(cueanexo="OWN-WEB")])
    )
    other = crear_jornada(
        crear_itinerario(
            provincia=other_province, sedes=[crear_sede(cueanexo="OTHER-WEB")]
        )
    )
    user = get_user_model().objects.create_user(username="vpsl-canonical-provincia")
    hacer_usuario_provincial(user, own_province)
    client.force_login(user)
    own_url = reverse("vpsl_jornada_detail", args=[own.pk])
    other_url = reverse("vpsl_jornada_detail", args=[other.pk])

    def shell(request, module):
        return HttpResponse(
            '<meta name="sisoc-vpsl-canonical" content="v1"><div id="vpsl-react"></div>'
        )

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)
    assert client.get(own_url).status_code == 403
    user.user_permissions.add(Permission.objects.get(codename="view_jornadavpsl"))
    page = client.get(own_url)
    assert b'id="vpsl-react"' in page.content
    assert client.get(other_url).status_code == 404

    head = client.head(own_url, REMOTE_ADDR="203.0.113.15")
    assert head.status_code == 200
    assert head.content == b""
    assert int(head["Content-Length"]) == len(page.content)
    assert head["Cache-Control"] == page["Cache-Control"]


def test_delete_preview_returns_the_same_parent_as_native_confirmation(admin_client):
    from ver_para_ser_libre.tests.test_workflow import crear_jornada

    itinerary = crear_itinerario()
    jornada = crear_jornada(itinerary)
    native = admin_client.get(reverse("vpsl_jornada_delete", args=[jornada.pk]))
    preview = admin_client.get(
        reverse("vpsl_api_action", args=["eliminar-jornada", jornada.pk]),
        {"next": "https://outside.invalid/"},
        HTTP_REFERER="https://outside.invalid/origin",
    )
    assert native.status_code == preview.status_code == 200
    assert preview.json()["back"] == native.context["cancel_url"]
    assert preview.json()["back"] == reverse(
        "vpsl_itinerario_detail", args=[itinerary.pk]
    )
    assert preview.json()["preview"]["total_afectados"] >= 1


def test_stale_vpsl_build_keeps_django_until_the_shell_supports_canonical_paths(
    admin_client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)

    def old_shell(request, module):
        return HttpResponse('<div id="old-static-vpsl"></div>')

    monkeypatch.setattr("core.v2_frontend.frontend_v2", old_shell)
    page = admin_client.get(reverse("vpsl_sede_list"))
    assert page.status_code == 200
    assert page.template_name
    assert b"old-static-vpsl" not in page.content


def test_existing_list_bookmarks_keep_their_native_filters_and_pagination(
    admin_client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)

    def shell(request, module):
        return HttpResponse(
            '<meta name="sisoc-vpsl-canonical" content="v1"><meta name="sisoc-vpsl-sedes" content="v1"><div id="vpsl-react"></div>'
        )

    monkeypatch.setattr("core.v2_frontend.frontend_v2", shell)
    for route in ("vpsl_itinerario_list",):
        page = admin_client.get(reverse(route), {"busqueda": "Prueba", "page": 1})
        assert page.status_code == 200
        assert page.template_name
        assert b'id="vpsl-react"' not in page.content

    page = admin_client.get(reverse("vpsl_sede_list"), {"sede": 42})
    assert page.status_code == 200
    assert b'id="vpsl-react"' in page.content


def test_forbidden_itinerary_edit_never_fetches_the_shell_or_mutates(
    client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("vpsl",)
    itinerary = crear_itinerario()
    original_name = itinerary.referente_nombre
    user = get_user_model().objects.create_user(username="vpsl-canonical-denied")
    client.force_login(user)
    url = reverse("vpsl_itinerario_update", args=[itinerary.pk])

    def forbidden(*args, **kwargs):
        pytest.fail("Denied canonical request reached the static upstream")

    monkeypatch.setattr("core.v2_frontend.frontend_v2", forbidden)

    assert client.get(url).status_code == 403
    assert (
        client.post(url, {"referente_nombre": "Cambio no autorizado"}).status_code
        == 403
    )
    itinerary.refresh_from_db()
    assert itinerary.referente_nombre == original_name


@pytest.mark.parametrize(
    "active,expected",
    [({"todas"}, True), ({"vpsl"}, True), ({"pas"}, False), (frozenset(), False)],
)
def test_activation_follows_react_activation_semantics(settings, active, expected):
    from ver_para_ser_libre.canonical_entry import react_enabled

    settings.REACT_VERTICALES_ACTIVAS = frozenset(active)
    assert react_enabled() is expected
