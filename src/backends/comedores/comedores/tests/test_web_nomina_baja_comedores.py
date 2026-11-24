"""Comedor nómina soft-delete confirmations (CO01 «Dar de baja»), direct and admission.

The web API runs the native ``NominaDeleteView`` / ``NominaDirectaDeleteView``
(scope, cascade preview, soft delete, message and redirect); the canonical URLs
serve the React index on GET only after the native guard and scope, and every
other method reaches the native view.
"""

import types
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano, Sexo
from comedores.models import Comedor, Nomina, Programas
from comedores.web_preview_nomina import nomina_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/"
MARK = '<div id="root-nomina-baja"></div>'
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    f"<body>{MARK}</body></html>"
)

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _permission(code):
    app, codename = code.split(".")
    if app == "auth":
        # Role permissions are seeded by migrations that SQLite tests may skip.
        content_type = ContentType.objects.get_for_model(get_user_model())
        return Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": codename}
        )[0]
    return Permission.objects.get(content_type__app_label=app, codename=codename)


def _client(username, *codes, enforce_csrf=False):
    usuario = _ready(get_user_model().objects.create_user(username, password="x"))
    for code in codes:
        usuario.user_permissions.add(_permission(code))
    client = Client(enforce_csrf_checks=enforce_csrf)
    client.force_login(usuario)
    return client, usuario


def _persona(documento):
    sexo, _ = Sexo.objects.get_or_create(sexo="Femenino")
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento=documento,
        sexo=sexo,
        fecha_nacimiento=date(2000, 1, 1),
    )


@pytest.fixture(name="directa")
def directa_fixture():
    comedor = Comedor.objects.create(
        nombre="Comedor Baja Directa",
        programa=Programas.objects.create(
            nombre="Programa directo baja", usa_admision_para_nomina=False
        ),
    )
    nomina = Nomina.objects.create(
        comedor=comedor, ciudadano=_persona("30111222"), estado="activo"
    )
    return comedor, nomina


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Baja Admision")
    admision = Admision.objects.create(comedor=comedor)
    nomina = Nomina.objects.create(
        admision=admision, ciudadano=_persona("30111333"), estado="activo"
    )
    return comedor, admision, nomina


def _api_directa(comedor, nomina):
    return f"{API}comedores/{comedor.pk}/nomina/{nomina.pk}/eliminar/"


def _api_admision(comedor, admision, nomina):
    return (
        f"{API}comedores/{comedor.pk}/admision/{admision.pk}/nomina/{nomina.pk}"
        "/eliminar/"
    )


def _canonical_directa(comedor, nomina):
    return f"/comedores/{comedor.pk}/nomina/{nomina.pk}/eliminar/"


def _canonical_admision(comedor, admision, nomina):
    return (
        f"/comedores/{comedor.pk}/admision/{admision.pk}/nomina/{nomina.pk}/eliminar/"
    )


def _snapshot():
    return list(Nomina.all_objects.order_by("pk").values_list("pk", "deleted_at"))


# --- Web API -----------------------------------------------------------------


def test_direct_confirmation_projects_the_native_page(directa):
    comedor, nomina = directa
    web, _ = _client("baja_directa_lee", "comedores.delete_nomina")

    respuesta = web.get(_api_directa(comedor, nomina))

    assert respuesta.status_code == 200
    assert "no-store" in respuesta["Cache-Control"]
    data = respuesta.json()
    assert data["id"] == nomina.pk
    assert data["object_name"] == str(nomina).upper()
    assert data["confirm_text"] == "Dar de baja"
    assert data["cancel_text"] == "Cancelar"
    assert data["cancel_url"] == f"/comedores/{comedor.pk}/nomina/"
    # Native quirk: the breadcrumb links ``comedor_detalle`` with the nómina id.
    assert data["breadcrumb"] == {
        "etiqueta": str(nomina),
        "url": f"/comedores/{nomina.pk}",
    }
    assert data["cascade_preview"]["total_afectados"] >= 1
    assert data["messages"] == []
    assert Nomina.all_objects.get(pk=nomina.pk).deleted_at is None


def test_admission_confirmation_cancels_to_the_admission_nomina(admision):
    comedor, adm, nomina = admision
    web, _ = _client("baja_admision_lee", "comedores.delete_nomina")

    data = web.get(_api_admision(comedor, adm, nomina)).json()

    assert data["id"] == nomina.pk
    assert data["object_name"] == str(nomina).upper()
    assert data["cancel_url"] == f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/"


def test_confirmed_direct_post_soft_deletes_with_the_native_message(directa):
    comedor, nomina = directa
    web, usuario = _client(
        "baja_directa_post", "comedores.delete_nomina", "comedores.view_nomina"
    )

    respuesta = web.post(_api_directa(comedor, nomina))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/{comedor.pk}/nomina/",
    }
    fila = Nomina.all_objects.get(pk=nomina.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == usuario.pk
    assert web.get(f"{API}comedores/{comedor.pk}/nomina/").json()["messages"] == [
        {
            "message": "Registro de nómina dado de baja correctamente.",
            "level": "success",
        }
    ]


def test_confirmed_admission_post_redirects_to_the_admission_nomina(admision):
    comedor, adm, nomina = admision
    web, _ = _client("baja_admision_post", "comedores.delete_nomina")

    respuesta = web.post(_api_admision(comedor, adm, nomina))

    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/{comedor.pk}/admision/{adm.pk}/nomina/",
    }
    assert Nomina.all_objects.get(pk=nomina.pk).deleted_at is not None


def test_api_rejections_expose_nothing_and_write_nothing(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    antes = _snapshot()
    sin_permiso, _ = _client("baja_sin_permiso", "comedores.view_nomina")
    sin_csrf, _ = _client("baja_sin_csrf", "comedores.delete_nomina", enforce_csrf=True)
    fuera, _ = _client(
        "baja_fuera_alcance", "comedores.delete_nomina", "auth.role_tecnico_comedor"
    )
    web, _ = _client("baja_lookup", "comedores.delete_nomina")
    urls = [_api_directa(comedor, nomina), _api_admision(comedor_adm, adm, nomina_adm)]

    for url in urls:
        for metodo in ("get", "post"):
            assert getattr(Client(), metodo)(url).status_code in (401, 403)
            negada = getattr(sin_permiso, metodo)(url)
            assert negada.status_code == 403
            assert "object_name" not in negada.json()
            assert getattr(fuera, metodo)(url).status_code == 404
        assert sin_csrf.post(url).status_code == 403
    # The nómina must belong to the comedor/admission of the URL.
    otro = Comedor.objects.create(nombre="Otro directo", programa=comedor.programa)
    assert web.get(_api_directa(otro, nomina)).status_code == 404
    assert web.post(_api_directa(otro, nomina)).status_code == 404
    assert web.get(_api_admision(comedor, adm, nomina_adm)).status_code == 404
    assert web.post(_api_admision(comedor, adm, nomina_adm)).status_code == 404
    assert _snapshot() == antes


def test_admindocs_head_does_not_bypass_the_web_api(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    staff, _ = _client("baja_staff_head")
    staff_user = get_user_model().objects.get(username="baja_staff_head")
    staff_user.is_staff = True
    staff_user.save()

    for url in (
        _api_directa(comedor, nomina),
        _api_admision(comedor_adm, adm, nomina_adm),
    ):
        respuesta = staff.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- Canonical URLs ----------------------------------------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("comedores_nomina_baja_preview_test_urls")
    module.urlpatterns = nomina_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_canonical_get_serves_react_after_the_native_guard(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    web, _ = _client("baja_react", "comedores.delete_nomina")

    for url in (
        _canonical_directa(comedor, nomina),
        _canonical_admision(comedor_adm, adm, nomina_adm),
    ):
        respuesta = web.get(url)
        assert respuesta.status_code == 200
        assert MARK in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies


@pytest.mark.usefixtures("preview")
def test_canonical_denials_are_native_and_carry_no_data(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    sin_permiso, _ = _client("baja_react_sin", "comedores.view_nomina")
    fuera, _ = _client(
        "baja_react_fuera", "comedores.delete_nomina", "auth.role_tecnico_comedor"
    )
    web, _ = _client("baja_react_lookup", "comedores.delete_nomina")

    for url in (
        _canonical_directa(comedor, nomina),
        _canonical_admision(comedor_adm, adm, nomina_adm),
    ):
        assert Client().get(url).status_code in (302, 403)
        negada = sin_permiso.get(url)
        assert negada.status_code == 403
        assert MARK not in negada.content.decode()
        oculta = fuera.get(url)
        assert oculta.status_code == 404
        assert MARK not in oculta.content.decode()
    assert web.get(_canonical_admision(comedor, adm, nomina_adm)).status_code == 404


@pytest.mark.usefixtures("preview")
def test_canonical_post_is_processed_by_the_native_view(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    web, _ = _client("baja_react_post", "comedores.delete_nomina")

    directa_post = web.post(_canonical_directa(comedor, nomina))
    admision_post = web.post(_canonical_admision(comedor_adm, adm, nomina_adm))

    assert directa_post.status_code == 302
    assert directa_post["Location"] == f"/comedores/{comedor.pk}/nomina/"
    assert admision_post.status_code == 302
    assert (
        admision_post["Location"]
        == f"/comedores/{comedor_adm.pk}/admision/{adm.pk}/nomina/"
    )
    assert Nomina.all_objects.get(pk=nomina.pk).deleted_at is not None
    assert Nomina.all_objects.get(pk=nomina_adm.pk).deleted_at is not None


def test_without_react_the_canonical_pages_are_native(directa, admision):
    comedor, nomina = directa
    comedor_adm, adm, nomina_adm = admision
    web, _ = _client("baja_nativa", "comedores.delete_nomina")

    module = types.ModuleType("comedores_nomina_baja_native_urls")
    module.urlpatterns = list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        for url, registro in (
            (_canonical_directa(comedor, nomina), nomina),
            (_canonical_admision(comedor_adm, adm, nomina_adm), nomina_adm),
        ):
            respuesta = web.get(url)
            assert respuesta.status_code == 200
            contenido = respuesta.content.decode()
            assert MARK not in contenido
            assert "Dar de baja" in contenido
            assert str(registro).upper() in contenido
