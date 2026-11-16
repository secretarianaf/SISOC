"""Local React preview entries of the encuestas screens (``encuestas.web_preview_encuestas``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    solicitar_publicacion,
)
from encuestas.models import Pregunta, TipoPregunta, TipoSegmentacion
from encuestas.web_preview_encuestas import encuestas_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("encuestas_preview_test_urls")
    module.urlpatterns = encuestas_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(username, *permisos):
    user = User.objects.create_user(username)
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(user)
    return user, client


def test_segmentacion_keeps_native_guards_then_frozen_index(preview):
    gestor, client = _client("prev_seg_gestor", "encuestas.change_encuesta")
    encuesta = crear_encuesta(
        usuario=gestor, titulo="Preview", es_obligatoria=True, duracion_ronda_dias=3
    )
    url = f"/encuestas/{encuesta.pk}/segmentacion/"
    assert Client().get(url).status_code == 403
    assert _client("prev_seg_sin")[1].get(url).status_code == 403
    response = client.get(url)
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    assert client.get("/encuestas/0/segmentacion/").status_code == 404


def test_segmentacion_pending_survey_keeps_the_native_redirect(preview):
    gestor, client = _client("prev_seg_pend", "encuestas.change_encuesta")
    encuesta = crear_encuesta(
        usuario=gestor, titulo="Pendiente", es_obligatoria=True, duracion_ronda_dias=3
    )
    Pregunta.objects.create(
        encuesta=encuesta, texto="¿Sí?", tipo=TipoPregunta.SI_NO, orden=1
    )
    actualizar_segmentacion(encuesta, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    solicitar_publicacion(encuesta, usuario=gestor)
    response = client.get(f"/encuestas/{encuesta.pk}/segmentacion/")
    assert response.status_code == 302
    assert response["Location"] == f"/encuestas/{encuesta.pk}/revision/"


def test_segmentacion_post_stays_native(preview):
    gestor, client = _client("prev_seg_post", "encuestas.change_encuesta")
    encuesta = crear_encuesta(
        usuario=gestor, titulo="Nativo", es_obligatoria=True, duracion_ronda_dias=3
    )
    response = client.post(
        f"/encuestas/{encuesta.pk}/segmentacion/tipo/", {"tipo": "todos_los_usuarios"}
    )
    assert response.status_code == 302
    encuesta.refresh_from_db()
    assert encuesta.segmentacion.tipo == "todos_los_usuarios"


def test_resultados_keeps_native_guards_then_frozen_index(preview):
    lector, client = _client("prev_res_lector", "encuestas.ver_resultados")
    encuesta = crear_encuesta(
        usuario=lector, titulo="Resultados", es_obligatoria=True, duracion_ronda_dias=3
    )
    url = f"/encuestas/{encuesta.pk}/resultados/"
    assert Client().get(url).status_code == 403
    assert (
        _client("prev_res_sin", "encuestas.view_encuesta")[1].get(url).status_code
        == 403
    )
    response = client.get(url)
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    assert client.get("/encuestas/0/resultados/").status_code == 404
    assert client.get(url + "?ronda=999").status_code == 200


def test_lista_keeps_native_guards_legacy_redirect_and_page_check(preview):
    lector, client = _client("prev_lista", "encuestas.view_encuesta")
    crear_encuesta(
        usuario=lector, titulo="Lista", es_obligatoria=True, duracion_ronda_dias=3
    )
    assert Client().get("/encuestas/").status_code == 403
    assert _client("prev_lista_sin")[1].get("/encuestas/").status_code == 403
    response = client.get("/encuestas/")
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    legacy = client.get("/encuestas/?busqueda=Lista")
    assert legacy.status_code == 302 and "filters=" in legacy["Location"]
    assert client.get("/encuestas/?page=9").status_code == 404


def test_revision_keeps_native_guards_then_frozen_index(preview):
    aprobador, client = _client("prev_rev", "encuestas.aprobar_encuesta")
    encuesta = crear_encuesta(
        usuario=aprobador, titulo="Revision", es_obligatoria=True, duracion_ronda_dias=3
    )
    url = f"/encuestas/{encuesta.pk}/revision/"
    assert Client().get(url).status_code == 403
    assert _client("prev_rev_sin")[1].get(url).status_code == 403
    response = client.get(url)
    assert response.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in response.content.decode()
    assert client.get("/encuestas/0/revision/").status_code == 404
