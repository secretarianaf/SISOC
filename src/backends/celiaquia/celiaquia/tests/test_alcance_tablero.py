"""Alcance efectivo de Celiaquía en la ruta pública."""

from unittest.mock import patch
from types import SimpleNamespace

import pytest
import requests
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.test import Client, override_settings


@pytest.mark.django_db
@override_settings(SISOC_CORE_ORIGIN="")
def test_stub_de_registro_sin_core_responde_no_disponible():
    usuario = User.objects.create_user(username="usuario_stub")
    cliente = Client()
    cliente.force_login(usuario)

    def stub(_request):
        raise Http404("Esta URL la atiende otro servicio")

    resultado = SimpleNamespace(url_name="dashboard_alcance_celiaquia", func=stub)
    with patch("celiaquia.services.alcance_tablero.resolve", return_value=resultado):
        assert cliente.get("/celiaquia/tablero/").status_code == 503
        assert cliente.head("/celiaquia/tablero/", HTTP_X_VIEW="1").status_code == 503


@pytest.mark.django_db
@override_settings(SISOC_CORE_ORIGIN="http://core:8000")
@pytest.mark.parametrize(
    "provincias",
    [
        [True],
        [False],
        [0],
        [-1],
        [2, 2],
        [1, "2"],
        [1, None],
        {"1": 1},
        "1",
        1,
        [1, [2]],
    ],
)
def test_respuesta_provincial_malformada_falla_cerrada(provincias):
    usuario = User.objects.create_user(username="provincial")
    cliente = Client()
    cliente.force_login(usuario)
    with patch("requests.Session.get") as llamada:
        llamada.return_value.status_code = 200
        llamada.return_value.json.return_value = {
            "estado": "provincial",
            "provincias": provincias,
        }
        assert cliente.get("/celiaquia/tablero/").status_code == 503
        assert cliente.head("/celiaquia/tablero/", HTTP_X_VIEW="1").status_code == 503


@pytest.mark.django_db
@override_settings(
    SISOC_CORE_ORIGIN="http://core:8000", REACT_VERTICALES_ACTIVAS=("celiaquia",)
)
def test_concesion_provincial_aplica_al_json_sin_permiso_legacy():
    usuario = User.objects.create_user(username="provincial")
    cliente = Client()
    cliente.force_login(usuario)
    with (
        patch("requests.Session.get") as llamada,
        patch(
            "celiaquia.views.tablero.construir_tablero", return_value={}
        ) as construir,
    ):
        llamada.return_value.status_code = 200
        llamada.return_value.json.return_value = {
            "estado": "provincial",
            "provincias": [10],
        }
        respuesta = cliente.get(
            "/celiaquia/tablero/?provincias=11", HTTP_ACCEPT="application/json"
        )
    assert respuesta.status_code == 200
    construir.assert_called_once_with(provincias_visibles=[10])
    assert llamada.call_args.kwargs["allow_redirects"] is False
    assert set(llamada.call_args.kwargs["cookies"]) == {"sessionid"}


@pytest.mark.django_db
@override_settings(SISOC_CORE_ORIGIN="http://core:8000")
@pytest.mark.parametrize(
    ("estado", "codigo"),
    [
        ({"estado": "denegado"}, 403),
        ({"estado": "provincial", "provincias": []}, 503),
        ({"estado": "provincial", "provincias": [True]}, 503),
        ({"estado": "nacional", "provincias": [1]}, 503),
        ({"estado": "otro"}, 503),
    ],
)
def test_estado_invalido_o_denegado_no_entrega_shell_ni_datos(estado, codigo):
    usuario = User.objects.create_user(username="staff", is_staff=True)
    cliente = Client()
    cliente.force_login(usuario)
    with patch("requests.Session.get") as llamada:
        llamada.return_value.status_code = 200
        llamada.return_value.json.return_value = estado
        for metodo in (cliente.get, cliente.head):
            respuesta = metodo("/celiaquia/tablero/", HTTP_ACCEPT="application/json")
            assert respuesta.status_code == codigo
            assert "X-View" not in respuesta


@pytest.mark.django_db
@override_settings(SISOC_CORE_ORIGIN="http://core:8000")
def test_core_inaccesible_no_se_interpreta_como_politica_inactiva():
    usuario = User.objects.create_superuser(username="admin", password="secreto")
    cliente = Client()
    cliente.force_login(usuario)
    with patch("requests.Session.get", side_effect=requests.ConnectionError):
        assert cliente.get("/celiaquia/tablero/").status_code == 503
        assert cliente.head("/celiaquia/tablero/").status_code == 503
    with patch("requests.Session.get") as llamada:
        llamada.return_value.status_code = 503
        assert cliente.get("/celiaquia/tablero/").status_code == 503


@pytest.mark.django_db
@override_settings(
    SISOC_CORE_ORIGIN="http://core:8000", REACT_VERTICALES_ACTIVAS=("celiaquia",)
)
def test_concesion_nacional_no_depende_del_permiso_legacy():
    usuario = User.objects.create_user(username="nacional")
    cliente = Client()
    cliente.force_login(usuario)
    with (
        patch("requests.Session.get") as llamada,
        patch(
            "celiaquia.views.tablero.construir_tablero", return_value={}
        ) as construir,
    ):
        llamada.return_value.status_code = 200
        llamada.return_value.json.return_value = {"estado": "nacional"}
        respuesta = cliente.get("/celiaquia/tablero/", HTTP_ACCEPT="application/json")
    assert respuesta.status_code == 200
    construir.assert_called_once_with(provincias_visibles=None)


@pytest.mark.django_db
@override_settings(
    SISOC_CORE_ORIGIN="http://core:8000", REACT_VERTICALES_ACTIVAS=("celiaquia",)
)
def test_politica_inactiva_conserva_permiso_legacy():
    usuario = User.objects.create_user(username="legacy")
    cliente = Client()
    cliente.force_login(usuario)
    with (
        patch("requests.Session.get") as llamada,
        patch("celiaquia.views.tablero.construir_tablero", return_value={}),
    ):
        llamada.return_value.status_code = 200
        llamada.return_value.json.return_value = {"estado": "inactiva"}
        assert cliente.get("/celiaquia/tablero/").status_code == 403
        content_type = ContentType.objects.get(
            app_label="celiaquia", model="expediente"
        )
        permiso, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename="view_tablero_celiaquia",
            defaults={"name": "Ver tablero"},
        )
        usuario.user_permissions.add(permiso)
        respuesta = cliente.get("/celiaquia/tablero/", HTTP_ACCEPT="application/json")
        assert respuesta.status_code == 200


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="celiaquia_runtime.urls", SISOC_CORE_ORIGIN="")
def test_runtime_vertical_sin_origen_no_hace_fallback_legacy():
    usuario = User.objects.create_user(username="legacy_vertical")
    content_type = ContentType.objects.get(app_label="celiaquia", model="expediente")
    permiso, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename="view_tablero_celiaquia",
        defaults={"name": "Ver tablero"},
    )
    usuario.user_permissions.add(permiso)
    cliente = Client()
    cliente.force_login(usuario)
    assert cliente.get("/celiaquia/tablero/").status_code == 503
    assert cliente.head("/celiaquia/tablero/").status_code == 503


@pytest.mark.django_db
@override_settings(
    ROOT_URLCONF="celiaquia_runtime.urls",
    SISOC_CORE_ORIGIN="http://django:8000",
    ALLOWED_HOSTS=["sisoc.example"],
    USE_X_FORWARDED_HOST=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    SECURE_SSL_REDIRECT=True,
    REACT_VERTICALES_ACTIVAS=("celiaquia",),
)
def test_origen_interno_preserva_host_y_esquema_validados_sin_cabeceras_ajenas():
    usuario = User.objects.create_user(username="legacy_con_core")
    tipo = ContentType.objects.get(app_label="celiaquia", model="expediente")
    permiso, _ = Permission.objects.get_or_create(
        content_type=tipo,
        codename="view_tablero_celiaquia",
        defaults={"name": "Ver tablero"},
    )
    usuario.user_permissions.add(permiso)
    cliente = Client()
    cliente.force_login(usuario)

    def pedir_core(url, **opciones):
        assert url == "http://django:8000/interno/tableros/celiaquia/alcance/"
        assert opciones["headers"] == {
            "Host": "sisoc.example",
            "X-Forwarded-Proto": "https",
            "Accept": "application/json",
        }
        assert set(opciones["cookies"]) == {"sessionid"}
        assert opciones["allow_redirects"] is False
        core = Client()
        core.cookies["sessionid"] = opciones["cookies"]["sessionid"]
        with override_settings(ROOT_URLCONF="config.urls_all"):
            return core.get(
                "/interno/tableros/celiaquia/alcance/",
                HTTP_HOST=opciones["headers"]["Host"],
                HTTP_X_FORWARDED_PROTO=opciones["headers"]["X-Forwarded-Proto"],
            )

    with (
        patch("requests.Session.get", side_effect=pedir_core),
        patch("celiaquia.views.tablero.construir_tablero", return_value={}),
    ):
        respuesta = cliente.get(
            "/celiaquia/tablero/",
            HTTP_HOST="sisoc.example",
            HTTP_X_FORWARDED_HOST="sisoc.example",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_X_SISOC_WEB_GATE="forjado",
            HTTP_X_SECRET_FORGED="no-propagar",
            HTTP_ACCEPT="application/json",
        )
    assert respuesta.status_code == 200


@pytest.mark.django_db
@override_settings(
    SISOC_CORE_ORIGIN="http://django:8000",
    ALLOWED_HOSTS=["sisoc.example"],
    USE_X_FORWARDED_HOST=True,
)
def test_host_no_permitido_no_se_reenvia_al_nucleo():
    usuario = User.objects.create_user(username="host_invalido")
    cliente = Client()
    cliente.force_login(usuario)
    with patch("requests.Session.get") as llamada:
        respuesta = cliente.get(
            "/celiaquia/tablero/", HTTP_X_FORWARDED_HOST="ajeno.invalid"
        )
    assert respuesta.status_code == 400
    llamada.assert_not_called()
