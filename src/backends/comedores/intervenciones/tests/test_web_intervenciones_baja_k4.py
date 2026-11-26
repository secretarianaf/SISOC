"""Web API (G1 v1) of the comedor intervention soft-delete confirmation (CO02).

The route keeps the native permission ``comedores.delete_nomina``; the object is
looked up by its id alone, as ``IntervencionDeleteView`` does.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.utils import timezone

from catalogo_intervenciones.models import (
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from comedores.models import Comedor
from intervenciones.models.intervenciones import Intervencion

ROOT = "/api/web/comedores/intervenciones/"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _cliente(usuario, **kwargs):
    client = Client(**kwargs)
    client.force_login(usuario)
    return client


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor K4", codigo_de_proyecto="")


@pytest.fixture(name="intervencion")
def intervencion_fixture(comedor):
    return Intervencion.objects.create(
        comedor=comedor,
        tipo_intervencion=TipoIntervencion.objects.create(nombre="Visita"),
        destinatario=TipoDestinatario.objects.create(nombre="Titular"),
        forma_contacto=TipoContacto.objects.create(nombre="Presencial"),
        fecha=timezone.make_aware(timezone.datetime(2026, 10, 1, 9, 30)),
    )


@pytest.fixture(name="web")
def web_fixture():
    usuario = _usuario(
        "baja_k4", "comedores.delete_nomina", "intervenciones.view_intervencion"
    )
    return _cliente(usuario), usuario


def _url(comedor, intervencion):
    return f"{ROOT}comedor/{comedor.pk}/baja/{intervencion.pk}/"


def test_confirmation_projects_the_native_page(web, comedor, intervencion):
    cliente, _ = web

    respuesta = cliente.get(_url(comedor, intervencion))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["id"] == intervencion.pk
    assert data["object_name"] == "INTERVENCIÓN EN COMEDOR K4 - 2026-10-01"
    assert data["confirm_text"] == "Dar de baja"
    assert data["cancel_text"] == "Cancelar"
    assert data["cancel_url"] == f"/comedores/intervencion/ver/{comedor.pk}"
    # Native quirk: the breadcrumb links the comedor page with the intervention id.
    assert data["breadcrumb"] == {
        "etiqueta": str(intervencion),
        "url": f"/comedores/{intervencion.pk}",
    }
    assert data["cascade_preview"]["total_afectados"] >= 1
    assert data["messages"] == []
    assert Intervencion.objects.count() == 1


def test_confirmed_post_soft_deletes_and_queues_the_native_message(
    web, comedor, intervencion
):
    cliente, usuario = web

    respuesta = cliente.post(_url(comedor, intervencion))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/intervencion/ver/{comedor.pk}",
    }
    assert not Intervencion.objects.filter(pk=intervencion.pk).exists()
    fila = Intervencion.all_objects.get(pk=intervencion.pk)
    assert fila.deleted_at is not None
    assert fila.deleted_by_id == usuario.pk
    lista = cliente.get(f"{ROOT}comedor/{comedor.pk}/").json()
    assert lista["results"] == []
    assert lista["messages"] == [
        {"message": "Intervención dada de baja correctamente.", "level": "success"}
    ]


def test_baja_rejects_a_comedor_different_from_the_intervention(web, intervencion):
    cliente, _ = web
    otro = Comedor.objects.create(nombre="Otro")

    respuesta = cliente.post(f"{ROOT}comedor/{otro.pk}/baja/{intervencion.pk}/")

    assert respuesta.status_code == 404
    assert Intervencion.all_objects.get(pk=intervencion.pk).deleted_at is None


def test_rejections_leave_the_row_untouched(comedor, intervencion):
    url = _url(comedor, intervencion)
    sin_permiso = _cliente(
        _usuario("sin_baja_k4", "intervenciones.delete_intervencion")
    )
    sin_csrf = _cliente(
        _usuario("csrf_baja_k4", "comedores.delete_nomina"), enforce_csrf_checks=True
    )

    assert Client().get(url).status_code in (401, 403)
    assert Client().post(url).status_code in (401, 403)
    assert sin_permiso.get(url).status_code == 403
    assert sin_permiso.post(url).status_code == 403
    assert sin_csrf.post(url).status_code == 403
    root = _cliente(_usuario("root_baja_k4", "comedores.delete_nomina"))
    assert root.get(f"{ROOT}comedor/{comedor.pk}/baja/999999/").status_code == 404
    assert root.post(f"{ROOT}comedor/{comedor.pk}/baja/999999/").status_code == 404
    assert Intervencion.objects.filter(pk=intervencion.pk).exists()
    assert Intervencion.all_objects.get(pk=intervencion.pk).deleted_at is None
