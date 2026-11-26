"""Alta de un familiar en JSON (C05.02): formulario, escritura nativa y rechazos."""

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
    return client


@pytest.fixture(name="par")
def par_fixture():
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Uno", documento=30111222)
    zoe = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=30111223)
    return ana, zoe


def _url(ciudadano):
    return f"/api/web/ciudadanos/{ciudadano.pk}/familiares/nuevo/"


def _datos(zoe, **extra):
    return {"ciudadano_2_id": str(zoe.pk), "ciudadano_2": "Zeta, Zoe", **extra}


def _relaciones():
    return list(GrupoFamiliar.all_objects.order_by("pk").values())


def test_formulario_proyecta_lo_que_imprime_el_template(par):
    ana, _ = par
    respuesta = _cliente("fam_get").get(_url(ana))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ciudadano"] == {
        "id": ana.pk,
        "texto": "Uno, Ana",
        "volver_url": f"/ciudadanos/ver/{ana.pk}",
    }
    campos = datos["campos"]
    assert campos["ciudadano_2"]["label"] == "Familiar"
    assert campos["ciudadano_2"]["placeholder"] == "Buscar por documento (4+ dígitos)"
    assert campos["vinculo"]["options"][0] == {"value": "", "label": "---------"}
    assert [o["label"] for o in campos["vinculo"]["options"][1:]] == [
        "Padre/Madre",
        "Hijo/a",
        "Pareja",
        "Hermano/a",
        "Tutor/a",
        "Otro",
    ]
    assert [o["value"] for o in campos["estado_relacion"]["options"]] == [
        "",
        "bueno",
        "regular",
        "conflictivo",
    ]
    assert datos["values"] == {
        "ciudadano_2": "",
        "vinculo": "",
        "estado_relacion": "",
        "conviven": False,
        "cuidador_principal": False,
        "observaciones": "",
    }
    assert datos["errors"] == {} and datos["messages"] == []
    assert "no-store" in respuesta["Cache-Control"]
    assert _relaciones() == []


def test_post_valido_escribe_la_relacion_nativa_y_deja_el_mensaje(par):
    ana, zoe = par
    client = _cliente("fam_post", (PERM, "ciudadanos.view_ciudadano"))
    respuesta = client.post(
        _url(ana),
        _datos(
            zoe,
            vinculo="HIJO/A",
            estado_relacion="bueno",
            conviven="on",
            observaciones="Nota",
        ),
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/ciudadanos/ver/{ana.pk}"}
    (relacion,) = _relaciones()
    assert (relacion["ciudadano_1_id"], relacion["ciudadano_2_id"]) == (ana.pk, zoe.pk)
    assert (relacion["vinculo"], relacion["estado_relacion"]) == ("HIJO/A", "bueno")
    assert (relacion["conviven"], relacion["cuidador_principal"]) == (True, False)
    assert relacion["observaciones"] == "Nota"
    assert relacion["deleted_at"] is None
    ficha = client.get(f"/api/web/ciudadanos/{ana.pk}/").json()
    assert ficha["messages"] == [
        {"message": "Familiar agregado correctamente.", "level": "success"}
    ]
    assert ficha["familia"][0]["apellido"] == "Zeta"


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ({"ciudadano_2_id": ""}, "Este campo es requerido."),
        ({"ciudadano_2_id": "99999"}, "Familiar no válido."),
        ({"ciudadano_2_id": "abc"}, "Familiar no válido."),
    ],
)
def test_post_invalido_responde_400_con_el_formulario_ligado_y_no_escribe(
    par, datos, mensaje
):
    ana, _ = par
    respuesta = _cliente("fam_inv").post(
        _url(ana), {**datos, "vinculo": "OTRO", "observaciones": "x"}
    )
    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["errors"] == {"ciudadano_2": [mensaje]}
    # El template re-imprime lo posteado: el input de texto lleva el id enviado.
    assert cuerpo["values"]["ciudadano_2"] == datos["ciudadano_2_id"]
    assert cuerpo["values"]["vinculo"] == "OTRO"
    assert cuerpo["values"]["observaciones"] == "x"
    assert _relaciones() == []


def test_autorreferencia_y_duplicado_se_rechazan(par):
    ana, zoe = par
    client = _cliente("fam_dup")
    assert client.post(_url(ana), _datos(ana)).json()["errors"] == {
        "ciudadano_2": ["No puede autoreferenciarse."]
    }
    assert client.post(_url(ana), _datos(zoe)).status_code == 200
    antes = _relaciones()
    inverso = client.post(_url(zoe), _datos(ana))
    assert inverso.status_code == 400
    assert inverso.json()["errors"] == {
        "ciudadano_2": ["Ya existe una relación registrada con este familiar."]
    }
    assert _relaciones() == antes


def test_rechazos_de_acceso_no_escriben(par):
    ana, zoe = par
    assert Client().post(_url(ana), _datos(zoe)).status_code == 401
    sin_permiso = _cliente("fam_sin", ())
    assert sin_permiso.get(_url(ana)).status_code == 403
    assert sin_permiso.post(_url(ana), _datos(zoe)).status_code == 403
    # Como la vista nativa, el ciudadano se busca antes que el permiso.
    inexistente = "/api/web/ciudadanos/999999/familiares/nuevo/"
    assert sin_permiso.post(inexistente, _datos(zoe)).status_code == 404
    assert _cliente("fam_ok").put(_url(ana)).status_code == 405
    assert _relaciones() == []


def test_post_exige_csrf(par):
    ana, zoe = par
    client = _cliente("fam_csrf", csrf=True)
    assert client.post(_url(ana), _datos(zoe)).status_code == 403
    assert _relaciones() == []
