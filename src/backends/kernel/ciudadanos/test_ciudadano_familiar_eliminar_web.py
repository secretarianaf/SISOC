"""Desvinculación de un familiar en JSON (C03.02): confirmación, baja lógica de la relación y rechazos."""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from ciudadanos.models import Ciudadano, GrupoFamiliar

pytestmark = pytest.mark.django_db

PERM = "ciudadanos.change_ciudadano"


def _cliente(username, permisos=(PERM,), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client, user


@pytest.fixture(name="relacion")
def relacion_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Uno", documento=30111222)
    zoe = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=30111223)
    return GrupoFamiliar.objects.create(
        ciudadano_1=ana, ciudadano_2=zoe, vinculo="HIJO/A"
    )


def _url(relacion, query=""):
    return f"/api/web/ciudadanos/familiares/{relacion.pk}/eliminar/{query}"


def _estado():
    return {
        "relaciones": list(
            GrupoFamiliar.all_objects.order_by("pk").values_list("pk", "deleted_at")
        ),
        "ciudadanos": Ciudadano.objects.count(),
    }


def test_confirmacion_proyecta_el_contexto_nativo(relacion):
    client, _ = _cliente("fam_baja_get")
    respuesta = client.get(_url(relacion))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == relacion.pk
    assert datos["nombre_mayusculas"] == "UNO, ANA - ZETA, ZOE (HIJO/A)"
    assert datos["cancelar_url"] == f"/ciudadanos/ver/{relacion.ciudadano_1_id}"
    preview = datos["cascade_preview"]
    assert preview["total_afectados"] == sum(f["cantidad"] for f in preview["desglose"])
    assert any(f["baja_logica"] for f in preview["desglose"])
    assert datos["messages"] == []
    assert "no-store" in respuesta["Cache-Control"]
    assert _estado()["relaciones"] == [(relacion.pk, None)]


def test_cancelar_sigue_a_next_solo_si_es_interno(relacion):
    client, _ = _cliente("fam_baja_next")
    interno = client.get(_url(relacion, "?next=/ciudadanos/listar")).json()
    assert interno["cancelar_url"] == "/ciudadanos/listar"
    for externo in ("https://evil.example/", "//evil.example/x", "javascript:alert(1)"):
        datos = client.get(_url(relacion, f"?next={externo}")).json()
        assert datos["cancelar_url"] == f"/ciudadanos/ver/{relacion.ciudadano_1_id}"


def test_baja_escribe_lo_nativo_y_deja_el_mensaje(relacion):
    client, user = _cliente("fam_baja_post")
    respuesta = client.post(_url(relacion))
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/ciudadanos/ver/{relacion.ciudadano_1_id}",
    }
    guardada = GrupoFamiliar.all_objects.get(pk=relacion.pk)
    assert guardada.deleted_at is not None
    assert guardada.deleted_by == user
    # Solo la relación: los dos ciudadanos siguen.
    assert _estado()["ciudadanos"] == 2
    assert not GrupoFamiliar.objects.filter(pk=relacion.pk).exists()
    # El mensaje espera a la próxima página y la relación ya no existe.
    assert client.get(_url(relacion)).status_code == 404


def test_baja_vuelve_a_next_interno(relacion):
    client, _ = _cliente("fam_baja_redir")
    respuesta = client.post(_url(relacion, "?next=/ciudadanos/listar"))
    assert respuesta.json() == {"ok": True, "redirect": "/ciudadanos/listar"}
    assert GrupoFamiliar.all_objects.get(pk=relacion.pk).deleted_at is not None


def test_baja_ignora_un_next_externo(relacion):
    client, _ = _cliente("fam_baja_ext")
    respuesta = client.post(_url(relacion, "?next=https://evil.example/"))
    assert respuesta.json()["redirect"] == f"/ciudadanos/ver/{relacion.ciudadano_1_id}"


def test_rechazos_no_dan_de_baja(relacion):
    antes = _estado()
    assert Client().get(_url(relacion)).status_code == 401
    assert Client().post(_url(relacion)).status_code == 401
    sin_permiso, _ = _cliente("fam_baja_sin", ("ciudadanos.view_ciudadano",))
    assert sin_permiso.get(_url(relacion)).status_code == 403
    assert sin_permiso.post(_url(relacion)).status_code == 403
    # Sin permiso un id inexistente tampoco filtra: 403 antes que 404.
    assert (
        sin_permiso.post("/api/web/ciudadanos/familiares/999999/eliminar/").status_code
        == 403
    )
    con_permiso, _ = _cliente("fam_baja_ok")
    assert (
        con_permiso.get("/api/web/ciudadanos/familiares/999999/eliminar/").status_code
        == 404
    )
    assert (
        con_permiso.post("/api/web/ciudadanos/familiares/999999/eliminar/").status_code
        == 404
    )
    assert con_permiso.put(_url(relacion)).status_code == 405
    assert _estado() == antes


def test_baja_exige_csrf(relacion):
    antes = _estado()
    client, _ = _cliente("fam_baja_csrf", csrf=True)
    assert client.post(_url(relacion)).status_code == 403
    assert _estado() == antes
