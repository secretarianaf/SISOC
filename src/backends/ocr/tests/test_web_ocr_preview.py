"""Local React preview entries of OCR (``ocr.web_preview``)."""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings

from config.urls_all import urlpatterns as monolith_patterns
from ocr.models import OCRJob
from ocr.web_preview import ocr_preview_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview", autouse=True)
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("ocr_preview_test_urls")
    module.urlpatterns = ocr_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _client(username, permiso=True):
    user = get_user_model().objects.create_user(username)
    if permiso:
        user.user_permissions.add(Permission.objects.get(codename="use_ocr"))
    client = Client()
    client.force_login(user)
    return client, user


def test_pages_get_the_frozen_index_and_a_csrf_cookie():
    client, user = _client("prev_dueno")
    job = OCRJob.objects.create(requested_by=user)

    for url in ("/ocr/", f"/ocr/{job.pk}/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 200, url
        assert b"/ocr/react/assets/app-1.js" in respuesta.content, url
        assert "csrftoken" in respuesta.cookies
    assert client.get("/ocr/react/assets/app-1.js").status_code == 200


def test_native_guards_decide_before_the_index():
    anonimo = Client().get("/ocr/")
    assert anonimo.status_code == 302
    sin_permiso, _ = _client("prev_sin", permiso=False)
    assert sin_permiso.get("/ocr/").status_code == 403

    client, user = _client("prev_otro")
    job = OCRJob.objects.create(requested_by=get_user_model().objects.create_user("x"))
    assert client.get(f"/ocr/{job.pk}/").status_code == 404
    assert client.get("/ocr/999999/").status_code == 404
    assert user is not None


def test_superuser_previews_any_batch_and_download_stays_native():
    root = get_user_model().objects.create_user("prev_root", is_superuser=True)
    job = OCRJob.objects.create(requested_by=get_user_model().objects.create_user("y"))
    client = Client()
    client.force_login(root)

    assert client.get(f"/ocr/{job.pk}/").status_code == 200
    assert client.get("/ocr/documentos/999999/descargar/").status_code == 404
