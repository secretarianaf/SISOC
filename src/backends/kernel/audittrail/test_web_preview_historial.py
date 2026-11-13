"""Local React preview entry of the instance history (``audittrail.web_preview``)."""

import types
from datetime import date

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from audittrail.web_preview import audittrail_preview_patterns
from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns

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
    module = types.ModuleType("audittrail_preview_test_urls")
    module.urlpatterns = audittrail_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(*permisos):
    user = User.objects.create_user(f"prev_hist_{len(permisos)}")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client()
    client.force_login(user)
    return client


def test_native_guards_then_frozen_index_and_native_export(preview):
    ciudadano = Ciudadano.objects.create(nombre="Ana", apellido="Prev", documento=3114)
    url = f"/auditoria/ciudadanos/ciudadano/{ciudadano.pk}/"
    assert Client().get(url).status_code == 302
    assert _client().get(url).status_code == 403
    lector = _client("auditlog.view_logentry", "audittrail.export_auditlog")
    respuesta = lector.get(url)
    assert respuesta.status_code == 200
    assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert lector.get(url + "?page=9").status_code == 404
    hoy = date.today().isoformat()
    exportado = lector.get(f"{url}?export=json&start_date={hoy}&end_date={hoy}")
    assert exportado["Content-Type"].startswith("application/json")
    assert exportado["Content-Disposition"].startswith("attachment;")


def test_listado_y_evento_keep_native_guards_then_frozen_index(preview):
    ciudadano = Ciudadano.objects.create(nombre="Eva", apellido="Prev", documento=3115)
    evento = LogEntry.objects.filter(object_pk=str(ciudadano.pk)).first()
    urls = ["/auditoria/", f"/auditoria/evento/{evento.pk}/"]
    lector = _client("auditlog.view_logentry")
    sin_permiso = _client()
    for url in urls:
        assert Client().get(url).status_code == 302
        assert sin_permiso.get(url).status_code == 403
        respuesta = lector.get(url)
        assert respuesta.status_code == 200
        assert "/ciudadanos/react/assets/app-1.js" in respuesta.content.decode()
    assert lector.get("/auditoria/evento/0/").status_code == 404
