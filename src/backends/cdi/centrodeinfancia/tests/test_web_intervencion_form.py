"""CDI06 intervention create and edit form: web API (G1 v1) over the native views.

The API runs the native views, so the form, the fixed recipient, the author, the
messages and the redirect are the native ones; the page markup is ``form.as_p``.
"""

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
import pytest

from catalogo_intervenciones.models import (
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from centrodeinfancia.models import CentroDeInfancia, IntervencionCentroInfancia

API = "/api/web/cdi/"
ALTA = "centrodeinfancia.add_intervencioncentroinfancia"
EDICION = "centrodeinfancia.change_intervencioncentroinfancia"

pytestmark = pytest.mark.django_db


def _usuario(username, *perms):
    user = User.objects.create_user(username)
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _cliente(user, **extra):
    client = Client(**extra)
    client.force_login(user)
    return client


def _crear(pk):
    return f"{API}centros/{pk}/intervenciones/crear/"


def _editar(pk, pk2):
    return f"{API}centros/{pk}/intervenciones/{pk2}/editar/"


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    TipoDestinatario.objects.create(nombre="Centro")
    return {
        "tipo": TipoIntervencion.objects.create(nombre="Seguimiento", programa="cdi"),
        "contacto": TipoContacto.objects.create(nombre="Presencial"),
    }


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(nombre="CDI Sintético")


def _datos(catalogo, **extra):
    return {
        "tipo_intervencion": str(catalogo["tipo"].pk),
        "subintervencion": "",
        "fecha": "2026-01-15",
        "forma_contacto": str(catalogo["contacto"].pk),
        "observaciones": "Nota sintética.",
    } | extra


def test_create_form_projects_the_native_markup(centro, catalogo):
    respuesta = _cliente(_usuario("int-form", ALTA)).get(_crear(centro.pk))

    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert cuerpo["volver_url"] == reverse("centrodeinfancia_detalle", args=[centro.pk])
    assert cuerpo["messages"] == []
    assert 'name="tipo_intervencion"' in cuerpo["form_html"]
    assert 'name="documentacion"' in cuerpo["form_html"]
    assert 'type="hidden" name="destinatario"' in cuerpo["form_html"]
    assert "csrfmiddlewaretoken" not in cuerpo["form_html"]


def test_create_accepts_multipart_with_the_attachment_and_redirects(
    centro, catalogo, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _usuario("int-alta", ALTA)
    archivo = SimpleUploadedFile("acta.pdf", b"%PDF-1.4 sintetico")

    respuesta = _cliente(user).post(
        _crear(centro.pk),
        _datos(catalogo, tiene_documentacion="on", documentacion=archivo),
    )

    creada = IntervencionCentroInfancia.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }
    assert creada.centro_id == centro.pk
    assert creada.creado_por_id == user.pk
    assert creada.destinatario.nombre == "Centro"
    assert creada.documentacion.name


def test_create_accepts_urlencoded_and_rejects_json(centro, catalogo):
    client = _cliente(_usuario("int-formatos", ALTA))

    json_post = client.post(_crear(centro.pk), "{}", content_type="application/json")
    urlencoded = client.post(
        _crear(centro.pk),
        "&".join(f"{k}={v}" for k, v in _datos(catalogo).items()),
        content_type="application/x-www-form-urlencoded",
    )

    assert json_post.status_code == 415
    assert urlencoded.status_code == 200
    assert IntervencionCentroInfancia.objects.count() == 1


def test_create_invalid_returns_400_with_the_bound_form_and_writes_nothing(
    centro, catalogo
):
    respuesta = _cliente(_usuario("int-invalida", ALTA)).post(
        _crear(centro.pk), _datos(catalogo, fecha="")
    )

    assert respuesta.status_code == 400
    assert "errorlist" in respuesta.json()["form_html"]
    assert "Nota sintética." in respuesta.json()["form_html"]
    assert IntervencionCentroInfancia.objects.count() == 0


def test_edit_projects_the_instance_updates_it_and_stays_in_the_centre(
    centro, catalogo
):
    destinatario = TipoDestinatario.objects.get(nombre="Centro")
    intervencion = IntervencionCentroInfancia.objects.create(
        centro=centro,
        tipo_intervencion=catalogo["tipo"],
        forma_contacto=catalogo["contacto"],
        destinatario=destinatario,
        observaciones="Original.",
    )
    otro = CentroDeInfancia.objects.create(nombre="Otro CDI")
    client = _cliente(_usuario("int-edita", EDICION))

    lectura = client.get(_editar(centro.pk, intervencion.pk))
    ajena = client.get(_editar(otro.pk, intervencion.pk))
    guardado = client.post(
        _editar(centro.pk, intervencion.pk),
        _datos(catalogo, observaciones="Cambiada.", destinatario=str(destinatario.pk)),
    )

    intervencion.refresh_from_db()
    assert "Original." in lectura.json()["form_html"]
    assert ajena.status_code == 404
    assert guardado.json()["redirect"] == reverse(
        "centrodeinfancia_detalle", args=[centro.pk]
    )
    assert intervencion.observaciones == "Cambiada."


def test_access_guards_match_the_native_routes(centro, catalogo):
    sin_permiso = _cliente(_usuario("int-sin-permiso"))
    solo_alta = _cliente(_usuario("int-solo-alta", ALTA))

    for client in (Client(),):
        assert client.get(_crear(centro.pk)).status_code == 401
        assert client.post(_crear(centro.pk), _datos(catalogo)).status_code == 401
    assert sin_permiso.get(_crear(centro.pk)).status_code == 403
    assert sin_permiso.post(_crear(centro.pk), _datos(catalogo)).status_code == 403
    assert solo_alta.get(_editar(centro.pk, 1)).status_code == 403
    assert IntervencionCentroInfancia.objects.count() == 0


def test_post_without_csrf_token_is_rejected(centro, catalogo):
    client = _cliente(_usuario("int-csrf", ALTA), enforce_csrf_checks=True)

    respuesta = client.post(_crear(centro.pk), _datos(catalogo))

    assert respuesta.status_code == 403
    assert IntervencionCentroInfancia.objects.count() == 0


def test_native_create_page_keeps_its_behaviour(centro, catalogo):
    client = _cliente(_usuario("int-nativa", ALTA))
    url = reverse("centrodeinfancia_intervencion_crear", kwargs={"pk": centro.pk})

    pagina = client.get(url)
    guardado = client.post(url, _datos(catalogo))

    assert pagina.status_code == 200
    assert "Guardar" in pagina.content.decode()
    assert guardado.status_code == 302
