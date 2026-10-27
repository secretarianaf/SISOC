"""Chequeo de URLs de ``/health/urls/``: servicio, comando, worker y vista."""

import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import include, path, reverse
from django.views.decorators.http import require_POST

from core.management.commands.chequear_urls import Command
from core.url_registry import recolectar, stub_urlpatterns
from core.services import health_urls as services

TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _ok(request):
    return HttpResponse("ok")


def _redirige(request):
    return HttpResponseRedirect("/ok/")


def _falla(request):
    raise RuntimeError("boom")


@require_POST
def _solo_post(request):
    return HttpResponse("ok")


# Vistas de prueba sobre el URLconf real: login, 404 y layout hacen reverse().
urlpatterns = [
    path("ok/", _ok, name="ok"),
    path("redirige/", _redirige),
    path("falla/", _falla, name="falla"),
    path("solo-post/", _solo_post, name="solo_post"),
    path("", include("config.urls_all")),
]


def _entrada(regex, name="", namespace=""):
    return {"name": name, "namespace": namespace, "regex": regex}


@pytest.fixture
def log_dir(settings, tmp_path):
    settings.LOG_DIR = tmp_path
    return tmp_path


@pytest.fixture
def superusuario(db):
    return get_user_model().objects.create_superuser(
        username="health-super", email="health@example.com", password="x"
    )


@pytest.mark.parametrize(
    ("regex", "esperada"),
    [
        (
            r"^comedores/configuracion/actividades\-pnud/\Z",
            "/comedores/configuracion/actividades-pnud/",
        ),
        (r"^admisiones/legales/listar\Z", "/admisiones/legales/listar"),
        (r"^\Z", "/"),
        (r"^comedores/(?P<pk>[0-9]+)/\Z", None),
        (r"^v2/(?P<module>[a-z0-9_-]+)(?:/(?P<asset_path>.*))?$", None),
        (r"^static/.*\Z", None),
    ],
)
def test_ruta_sin_parametros(regex, esperada):
    assert services.ruta_sin_parametros(regex) == esperada


def test_urls_a_chequear_filtra_excluidas_y_parametrizadas():
    registro = [
        _entrada(r"^comedores/\Z", "comedores"),
        _entrada(r"^comedores/\Z", "comedores_alias"),
        _entrada(r"^api/x/\Z", "lista", "api"),
        _entrada(r"^sin-nombre/\Z"),
        _entrada(r"^admin/\Z", "index", "admin"),
        _entrada(r"^logout/\Z", "salir"),
        _entrada(r"^cosas/eliminar/\Z", "cosa_borrar"),
        _entrada(r"^centrodeinfancia/exportar\Z", "centro_export"),
        _entrada(r"^reporte/\Z", "reporte_excel"),
        _entrada(r"^health/urls/\Z", "health_urls"),
        _entrada(r"^comedores/(?P<pk>[0-9]+)/\Z", "comedor_detalle"),
    ]

    urls, excluidas, con_parametros = services.urls_a_chequear(registro)

    assert urls == [
        ("/comedores/", "comedores"),
        ("/api/x/", "api:lista"),
        ("/sin-nombre/", ""),
    ]
    assert excluidas == 6
    assert con_parametros == 1


@pytest.mark.urls(__name__)
def test_chequear_devuelve_el_codigo_e_ignora_solo_post(superusuario):
    urls = [
        ("/ok/", "ok"),
        ("/redirige/", ""),
        ("/falla/", "falla"),
        ("/no-existe/", "x"),
        ("/solo-post/", "solo_post"),
    ]

    resultados, solo_post = services.chequear(urls, superusuario, "testserver")

    assert [(r["url"], r["status"]) for r in resultados] == [
        ("/ok/", 200),
        ("/redirige/", 302),
        ("/falla/", 500),
        ("/no-existe/", 404),
    ]
    assert solo_post == 1


@pytest.mark.urls(__name__)
def test_ejecutar_guarda_el_resultado(superusuario, log_dir, mocker):
    mocker.patch.object(
        services,
        "cargar",
        return_value=[
            _entrada(r"^ok/\Z", "ok"),
            _entrada(r"^falla/\Z", "falla"),
            _entrada(r"^solo\-post/\Z", "solo_post"),
            _entrada(r"^comedores/(?P<pk>[0-9]+)/\Z", "detalle"),
        ],
    )

    resultado = services.ejecutar("testserver")

    assert resultado["resumen"] == {
        "chequeadas": 2,
        "por_status": {"200": 1, "500": 1},
        "ignoradas_solo_post": 1,
        "excluidas": 0,
        "salteadas_con_parametros": 1,
    }
    assert services.leer_resultado() == resultado


@pytest.mark.django_db
def test_usuario_tecnico_se_crea_sin_contrasena_ni_pendientes():
    usuario = services.usuario_tecnico()

    assert usuario.username == services.USUARIO_TECNICO
    assert usuario.is_superuser and usuario.is_active
    assert not usuario.has_usable_password()
    assert usuario.profile.acceso_web
    assert not usuario.profile.must_change_password
    assert not usuario.profile.needs_profile_confirmation


@pytest.mark.django_db
def test_usuario_tecnico_repara_contrasena_y_perfil():
    usuario = get_user_model().objects.create_user(
        username=services.USUARIO_TECNICO, password="alguien-la-puso"
    )
    usuario.profile.must_change_password = True
    usuario.profile.needs_profile_confirmation = True
    usuario.profile.acceso_web = False
    usuario.profile.save()

    usuario = services.usuario_tecnico()
    usuario.refresh_from_db()

    assert usuario.is_superuser
    assert not usuario.has_usable_password()
    assert usuario.profile.acceso_web
    assert not usuario.profile.must_change_password
    assert not usuario.profile.needs_profile_confirmation


@pytest.mark.django_db
def test_usuario_tecnico_desactivado_apaga_el_chequeo():
    get_user_model().objects.create_superuser(
        username=services.USUARIO_TECNICO, email="", password=None, is_active=False
    )

    with pytest.raises(ValueError, match="desactivado"):
        services.ejecutar("testserver")


@pytest.mark.urls(__name__)
def test_sin_acceso_a_inicio_no_recorre(superusuario, mocker):
    superusuario.profile.must_change_password = True
    superusuario.profile.save()
    urls = mocker.MagicMock()

    with pytest.raises(ValueError, match="no llega a inicio .*status 302"):
        services.chequear(urls, superusuario, "testserver")
    urls.__iter__.assert_not_called()


def test_host_por_defecto_saltea_comodines(settings):
    settings.ALLOWED_HOSTS = [".sisoc.gob.ar", "sisoc.gob.ar"]
    assert services.host_por_defecto() == "sisoc.gob.ar"
    settings.ALLOWED_HOSTS = ["*"]
    assert services.host_por_defecto() == "localhost"


@pytest.mark.parametrize(
    ("ahora", "esperado"),
    [
        (
            datetime(2026, 10, 27, 5, 0, tzinfo=TZ),
            datetime(2026, 10, 27, 6, 0, tzinfo=TZ),
        ),
        (
            datetime(2026, 10, 27, 6, 0, tzinfo=TZ),
            datetime(2026, 10, 27, 12, 0, tzinfo=TZ),
        ),
        (
            datetime(2026, 10, 27, 13, 30, tzinfo=TZ),
            datetime(2026, 10, 27, 18, 0, tzinfo=TZ),
        ),
        (
            datetime(2026, 10, 27, 18, 1, tzinfo=TZ),
            datetime(2026, 10, 28, 6, 0, tzinfo=TZ),
        ),
    ],
)
def test_proximo_horario(ahora, esperado):
    horarios = [time(18), time(6), time(12)]
    assert services.proximo_horario(ahora, horarios) == esperado


@pytest.mark.urls(__name__)
def test_comando_una_vez(log_dir, mocker, db):
    mocker.patch.object(services, "cargar", return_value=[_entrada(r"^ok/\Z", "ok")])

    call_command("chequear_urls", "--host", "testserver")

    assert services.leer_resultado()["urls"] == [
        {"url": "/ok/", "nombre": "ok", "status": 200}
    ]


@pytest.mark.django_db
def test_comando_falla_si_el_usuario_tecnico_esta_desactivado():
    get_user_model().objects.create_superuser(
        username=services.USUARIO_TECNICO, email="", password=None, is_active=False
    )
    with pytest.raises(CommandError, match="desactivado"):
        call_command("chequear_urls")


def test_comando_horarios_invalidos():
    with pytest.raises(CommandError, match="--horarios"):
        call_command("chequear_urls", "--horarios", "6hs")


def test_ciclo_espera_y_guarda_el_error(log_dir, mocker):
    sleep = mocker.patch("core.management.commands.chequear_urls.time.sleep")
    mocker.patch.object(services, "ejecutar", side_effect=ValueError("apagado"))

    Command().ciclo([time(6)], None)

    sleep.assert_called_once()
    assert services.leer_resultado()["error"] == "apagado"


@pytest.mark.urls(__name__)
class TestVista:
    def test_anonimo_va_al_login(self, client):
        respuesta = client.get(reverse("health_urls"))
        assert respuesta.status_code == 302

    def test_no_superusuario_403(self, client, django_user_model):
        client.force_login(
            django_user_model.objects.create_user(username="u", password="x")
        )
        assert client.get(reverse("health_urls")).status_code == 403

    def test_superusuario_sin_resultados_404(self, client, superusuario, log_dir):
        client.force_login(superusuario)
        respuesta = client.get(reverse("health_urls"))
        assert respuesta.status_code == 404
        assert "chequear_urls" in respuesta.json()["error"]

    def test_superusuario_ve_el_ultimo_resultado(self, client, superusuario, log_dir):
        (log_dir / services.ARCHIVO_RESULTADO).write_text(
            json.dumps({"urls": [{"url": "/ok/", "status": 200}]}), encoding="utf-8"
        )
        client.force_login(superusuario)
        respuesta = client.get(reverse("health_urls"))
        assert respuesta.status_code == 200
        assert respuesta.json() == {"urls": [{"url": "/ok/", "status": 200}]}


def test_registro_incluye_rutas_sin_nombre_y_los_stubs_las_ignoran(tmp_path):
    entradas = recolectar(urlpatterns)
    assert _entrada("^redirige/", "") in [
        {**e, "regex": e["regex"].removesuffix(r"\Z")} for e in entradas
    ]

    registro = tmp_path / "registro.json"
    registro.write_text(
        json.dumps([_entrada(r"^ajena/\Z"), _entrada(r"^ajena/nombrada/\Z", "ajena")]),
        encoding="utf-8",
    )
    stubs = recolectar(stub_urlpatterns([], path=registro))
    assert [e["name"] for e in stubs] == ["ajena"]
