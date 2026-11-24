"""Local React preview entries of the mailing (``comunicados.web_preview_mailing``)."""

import types
from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from openpyxl import Workbook

from comunicados.models import MailingJob
from comunicados.services_mailing_jobs import create_mailing_job
from comunicados.web_preview_mailing import mailing_preview_patterns
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
BASE = "/comunicados/mailing/"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


@pytest.fixture(name="preview")
def preview_fixture(build):
    module = types.ModuleType("mailing_preview_test_urls")
    module.urlpatterns = mailing_preview_patterns(build) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, **flags):
    client = Client()
    client.force_login(User.objects.create_user(nombre, **flags))
    return client


@pytest.fixture(name="lote")
def lote_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    libro = Workbook()
    libro.active.title = "mailing"
    libro.active.append(["mail"])
    libro.active.append(["uno@example.com"])
    salida = BytesIO()
    libro.save(salida)
    return create_mailing_job(
        uploaded_file=SimpleUploadedFile("d.xlsx", salida.getvalue()),
        asunto="A",
        cuerpo="C",
        requested_by=User.objects.create_user("duenio_prev_mailing"),
    )


@pytest.mark.usefixtures("preview")
def test_the_admin_gets_the_frozen_index(lote):
    admin = _login("admin_prev_mailing", is_superuser=True)
    for url in (BASE, f"{BASE}lotes/{lote.pk}/"):
        respuesta = admin.get(url)
        assert respuesta.status_code == 200, url
        assert (
            '/comunicados/mailing-react/assets/app-1.js"' in respuesta.content.decode()
        )
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
    assert (
        admin.get("/comunicados/mailing-react/assets/app-1.js").content
        == b"console.log(1);"
    )


@pytest.mark.usefixtures("preview")
def test_native_guards_decide_first(lote):
    # The admin check of the native dispatch runs before the login redirect.
    assert Client().get(BASE).status_code == 403
    assert Client().get(f"{BASE}lotes/{lote.pk}/").status_code == 403
    comun = _login("comun_prev_mailing")
    assert comun.get(BASE).status_code == 403
    assert comun.get(f"{BASE}lotes/{lote.pk}/").status_code == 403
    admin = _login("admin2_prev_mailing", is_superuser=True)
    assert admin.get(f"{BASE}lotes/999999/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_posts_and_the_template_still_reach_the_native_views(lote):
    admin = _login("admin3_prev_mailing", is_superuser=True)
    respuesta = admin.post(f"{BASE}lotes/{lote.pk}/reanudar/")
    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"{BASE}lotes/{lote.pk}/"
    assert MailingJob.objects.get(pk=lote.pk).resume_count == 0
    assert admin.get(f"{BASE}plantilla/").status_code == 200


def test_build_without_index_is_refused(tmp_path):
    with pytest.raises(ValueError):
        mailing_preview_patterns(tmp_path)
