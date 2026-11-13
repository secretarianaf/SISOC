"""Web API (G1 v1) of the comedor ficha: ``/api/web/comedores/comedores/<pk>/`` (CO07.01).

The endpoint runs the native ``ComedorDetailView``; these tests compare its JSON
with what ``comedor_detail.html`` shows and check that reading never writes.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from admisiones.models.admisiones import Admision
from comedores.models import Comedor
from comedores.utils import get_prestacion_conformidad_pending_period
from core import web_gate

pytestmark = pytest.mark.django_db
ROOT = "/api/web/comedores/comedores/"


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: the ficha runs the real services."""


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _client(username, *codenames):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename))
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _client("lector_ficha", "view_comedor")


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Norte")


def test_header_and_title_project_the_native_blocks(lector, comedor):
    datos = lector.get(f"{ROOT}{comedor.pk}/").json()

    assert datos["id"] == comedor.pk
    assert datos["nombre"] == "Comedor Norte"
    header = datos["header"]
    assert header["acciones"]["editar"] == f"/comedores/{comedor.pk}/editar"
    assert header["acciones"]["eliminar"] == f"/comedores/{comedor.pk}/eliminar"
    assert header["acciones"]["equipo_tecnico"] is None
    assert header["acciones"]["responsable_tarjeta"] is None
    assert header["validar"] is False
    assert header["historial"] is None
    assert header["convenios"] == []
    assert (
        header["acompanamiento_territorial"]
        == f"/comedores/{comedor.pk}/relevamiento/listar"
    )
    titulo = datos["titulo"]
    assert titulo["nombre"] == "Comedor Norte"
    assert titulo["programa"] == "Sin programa"
    periodo = get_prestacion_conformidad_pending_period(comedor)
    assert titulo["conformidad_pendiente"] == (
        None if periodo is None else {"periodo": periodo.strftime("%m/%Y")}
    )
    assert titulo["inicio_ejecucion"] is None
    assert datos["messages"] == []


def test_convenios_selector_marks_the_selected_one_and_keeps_the_query(lector, comedor):
    primera = Admision.objects.create(comedor=comedor, activa=False)
    segunda = Admision.objects.create(comedor=comedor, activa=True)

    datos = lector.get(f"{ROOT}{comedor.pk}/", {"admision_id": primera.pk}).json()

    convenios = {c["id"]: c for c in datos["header"]["convenios"]}
    assert set(convenios) == {primera.pk, segunda.pk}
    assert convenios[primera.pk]["seleccionada"] is True
    assert convenios[segunda.pk]["seleccionada"] is False
    assert convenios[segunda.pk]["url"].endswith(f"admision_id={segunda.pk}")
    assert datos["titulo"]["inicio_ejecucion"] == primera.creado.strftime("%d/%m/%Y")


def test_actions_follow_the_permissions_the_template_checks(comedor):
    admin = Client()
    admin.force_login(
        _ready(get_user_model().objects.create_superuser("admin_ficha", password="x"))
    )

    header = admin.get(f"{ROOT}{comedor.pk}/").json()["header"]

    assert header["historial"] == f"/auditoria/comedores/comedor/{comedor.pk}/"
    assert header["acciones"]["equipo_tecnico"]["label"] == "Asignar Equipo Técnico"
    assert header["acciones"]["comenzar_admision"] is False


def test_a_comedor_outside_the_scope_or_missing_is_404(lector, comedor):
    assert lector.get(f"{ROOT}999999/").status_code == 404
    assert lector.get(f"{ROOT}{comedor.pk}/").status_code == 200


def test_reading_the_ficha_writes_nothing(lector, comedor):
    antes = list(Comedor.objects.values())
    admisiones = Admision.objects.count()

    lector.get(f"{ROOT}{comedor.pk}/")

    assert list(Comedor.objects.values()) == antes
    assert Admision.objects.count() == admisiones


def test_only_get_is_served(lector, comedor):
    for metodo in ("post", "put", "delete"):
        assert (
            getattr(lector, metodo)(f"{ROOT}{comedor.pk}/").status_code == 405
        ), metodo
    assert Comedor.objects.filter(pk=comedor.pk).exists()


@pytest.mark.parametrize("codename", ["view_admision", "view_informacionrelevante"])
def test_any_of_the_three_native_permissions_is_enough(codename, comedor):
    assert (
        _client(f"lector_{codename}", codename).get(f"{ROOT}{comedor.pk}/").status_code
        == 200
    )


def test_anonymous_and_without_permission(client, comedor):
    respuesta = client.get(f"{ROOT}{comedor.pk}/")
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    client.force_login(
        _ready(get_user_model().objects.create_user("sin_permiso_ficha", password="x"))
    )
    assert client.get(f"{ROOT}{comedor.pk}/").status_code == 403


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(comedor):
    usuario = get_user_model().objects.create_superuser("pendiente_ficha", password="x")
    usuario.profile.acceso_web = True
    usuario.profile.must_change_password = True
    usuario.profile.save()
    client = Client()
    client.force_login(usuario)
    url = f"{ROOT}{comedor.pk}/"
    falso = web_gate.sign(
        audience="comedores",
        user_pk=usuario.pk,
        session_key=client.cookies["sessionid"].value,
        method="GET",
        target=url,
    )

    respuesta = client.get(url, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=url)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"
