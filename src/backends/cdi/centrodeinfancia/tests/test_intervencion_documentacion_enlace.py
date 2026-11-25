"""The current-file link of the CDI intervention edit form uses the authenticated download.

CDI documentation lives in ``cdi/documentacion/`` and nginx blocks ``/media/cdi/``, so the
``FieldFile.url`` link that ``ClearableFileInput`` renders answers 404. The native edit
page and the web API (``form_html``) must link to the authenticated endpoint instead,
keeping the replace and clear behaviour.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from catalogo_intervenciones.models import (
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from centrodeinfancia.models import CentroDeInfancia, IntervencionCentroInfancia

EDICION = "centrodeinfancia.change_intervencioncentroinfancia"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, name="media")
def media_fixture(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


def _cliente():
    user = User.objects.create_user("enlace-edita")
    app, codename = EDICION.split(".")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label=app, codename=codename)
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    client = Client()
    client.force_login(User.objects.get(pk=user.pk))
    return client


@pytest.fixture(name="caso")
def caso_fixture():
    destinatario = TipoDestinatario.objects.create(nombre="Centro")
    tipo = TipoIntervencion.objects.create(nombre="Seguimiento", programa="cdi")
    contacto = TipoContacto.objects.create(nombre="Presencial")
    centro = CentroDeInfancia.objects.create(nombre="CDI Sintético")
    intervencion = IntervencionCentroInfancia.objects.create(
        centro=centro,
        tipo_intervencion=tipo,
        forma_contacto=contacto,
        destinatario=destinatario,
        tiene_documentacion=True,
        documentacion=SimpleUploadedFile("acta.pdf", b"%PDF-1.4 x"),
    )
    return {
        "centro": centro,
        "intervencion": intervencion,
        "tipo": tipo,
        "contacto": contacto,
        "destinatario": destinatario,
    }


def _datos(caso, **extra):
    return {
        "tipo_intervencion": str(caso["tipo"].pk),
        "subintervencion": "",
        "fecha": "2026-01-15",
        "forma_contacto": str(caso["contacto"].pk),
        "destinatario": str(caso["destinatario"].pk),
        "observaciones": "Nota.",
        "tiene_documentacion": "on",
    } | extra


def _descarga(caso):
    return reverse(
        "centrodeinfancia_web_intervencion_documentacion",
        args=[caso["intervencion"].pk],
    )


def _enlaces(html):
    return [parte.split('"')[0] for parte in html.split('href="')[1:]]


def test_native_edit_page_links_to_the_authenticated_download(caso):
    url = reverse(
        "centrodeinfancia_intervencion_editar",
        kwargs={"pk": caso["centro"].pk, "pk2": caso["intervencion"].pk},
    )

    html = _cliente().get(url).content.decode()

    assert _descarga(caso) in _enlaces(html)
    assert "/media/" not in html


def test_api_form_html_links_to_the_authenticated_download(caso):
    url = (
        f"/api/web/cdi/centros/{caso['centro'].pk}/intervenciones/"
        f"{caso['intervencion'].pk}/editar/"
    )

    html = _cliente().get(url).json()["form_html"]

    assert _descarga(caso) in _enlaces(html)
    assert "/media/" not in html


def test_edit_form_keeps_the_clear_checkbox_and_the_file_input(caso):
    url = (
        f"/api/web/cdi/centros/{caso['centro'].pk}/intervenciones/"
        f"{caso['intervencion'].pk}/editar/"
    )

    html = _cliente().get(url).json()["form_html"]

    assert 'name="documentacion-clear"' in html
    assert 'name="documentacion"' in html
    assert "Actualmente" in html


def test_replace_and_clear_still_work(caso):
    url = reverse(
        "centrodeinfancia_intervencion_editar",
        kwargs={"pk": caso["centro"].pk, "pk2": caso["intervencion"].pk},
    )
    client = _cliente()

    client.post(
        url,
        _datos(caso, documentacion=SimpleUploadedFile("nuevo.pdf", b"%PDF-1.4 y")),
    )
    caso["intervencion"].refresh_from_db()
    reemplazado = caso["intervencion"].documentacion.name
    client.post(url, _datos(caso, **{"documentacion-clear": "on"}))
    caso["intervencion"].refresh_from_db()

    assert "nuevo" in reemplazado
    assert not caso["intervencion"].documentacion
