"""Baja de ciudadano en JSON (C05.03): confirmación, baja lógica en cascada y rechazos."""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from ciudadanos.models import Ciudadano, GrupoFamiliar

pytestmark = pytest.mark.django_db

PERM_VER = "ciudadanos.view_ciudadano"
PERM_BAJA = "ciudadanos.delete_ciudadano"


def _cliente(username, permisos=(PERM_BAJA,), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Baja", documento=30111222)
    zoe = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=2)
    GrupoFamiliar.objects.create(ciudadano_1=ana, ciudadano_2=zoe, vinculo="HIJO/A")
    return ana


def _url(ciudadano):
    return f"/api/web/ciudadanos/{ciudadano.pk}/baja/"


def _estado():
    return {
        "ciudadanos": list(
            Ciudadano.all_objects.order_by("pk").values_list("pk", "deleted_at")
        ),
        "familia": list(GrupoFamiliar.all_objects.values_list("pk", "deleted_at")),
    }


def test_confirmacion_proyecta_el_contexto_nativo(ciudadano):
    respuesta = _cliente("baja_get").get(_url(ciudadano))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == ciudadano.pk
    assert datos["nombre_mayusculas"] == "BAJA, ANA"
    assert datos["cancelar_url"] == f"/ciudadanos/ver/{ciudadano.pk}"
    preview = datos["cascade_preview"]
    assert (
        preview["total_afectados"]
        == preview["total_baja_logica"] + preview["total_borrado_fisico"]
    )
    modelos = {fila["modelo"]: fila for fila in preview["desglose"]}
    assert sum(f["cantidad"] for f in modelos.values()) == preview["total_afectados"]
    assert any(f["baja_logica"] for f in modelos.values())
    assert datos["messages"] == []
    assert "no-store" in respuesta["Cache-Control"]
    assert _estado()["ciudadanos"] == [
        (c.pk, None) for c in Ciudadano.objects.order_by("pk")
    ]


def test_baja_escribe_lo_nativo_y_deja_el_mensaje(ciudadano):
    client = _cliente("baja_post")
    respuesta = client.post(_url(ciudadano))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/ciudadanos/listar"}
    estado = _estado()
    por_pk = dict(estado["ciudadanos"])
    assert por_pk[ciudadano.pk] is not None
    assert [v for k, v in por_pk.items() if k != ciudadano.pk] == [None]
    assert all(v is not None for _pk, v in estado["familia"])
    assert not Ciudadano.objects.filter(pk=ciudadano.pk).exists()
    assert Ciudadano.all_objects.get(pk=ciudadano.pk).deleted_by.username == "baja_post"
    # Con la baja hecha, la ficha ya no existe y el mensaje espera a la próxima página.
    assert client.get(_url(ciudadano)).status_code == 404


def test_rechazos_no_dan_de_baja(ciudadano):
    antes = _estado()
    assert Client().post(_url(ciudadano)).status_code == 401
    sin_permiso = _cliente("baja_sin", (PERM_VER,))
    assert sin_permiso.get(_url(ciudadano)).status_code == 403
    assert sin_permiso.post(_url(ciudadano)).status_code == 403
    # Sin permiso un id inexistente tampoco filtra: 403 antes que 404.
    assert sin_permiso.post("/api/web/ciudadanos/999999/baja/").status_code == 403
    con_permiso = _cliente("baja_ok")
    assert con_permiso.get("/api/web/ciudadanos/999999/baja/").status_code == 404
    assert con_permiso.post("/api/web/ciudadanos/999999/baja/").status_code == 404
    assert con_permiso.put(_url(ciudadano)).status_code == 405
    assert _estado() == antes


def test_baja_exige_csrf(ciudadano):
    antes = _estado()
    assert _cliente("baja_csrf", csrf=True).post(_url(ciudadano)).status_code == 403
    assert _estado() == antes
