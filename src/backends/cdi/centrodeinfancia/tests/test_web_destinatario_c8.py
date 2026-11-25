"""CDI destinatario create and edit: web API (G1 v1) over the native views.

The API inherits ``NominaCentroInfanciaCreateView`` / ``NominaCentroInfanciaEditView``,
so the form, the DNI search, the signed RENAPER prefill, the citizen creation,
the nomina lock, the messages and the CDI-A3 auditor veto are the native ones.
RENAPER is always stubbed.
"""

from datetime import date, timedelta
from unittest import mock
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client
from django.test.client import MULTIPART_CONTENT as MULTIPART

from centrodeinfancia.models import CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.tests.test_destinatario_form import datos_validos
from centrodeinfancia.web_api_destinatario import CAMPOS, MULTIPLES
from ciudadanos.models import Ciudadano
from core import web_gate
from core.constants import UserGroups
from core.models import Provincia
from users.models import Profile

API = "/api/web/cdi/"
RENAPER = "centrodeinfancia.views.obtener_datos_ciudadano_desde_renaper"
VETO = "El rol Auditoría tiene acceso de solo lectura."
ALTA = "centrodeinfancia.add_nominacentroinfancia"
EDICION = "centrodeinfancia.change_nominacentroinfancia"

pytestmark = pytest.mark.django_db


class WebClient(Client):
    """Posts to the web API URL-encoded, as the React page does."""

    def post(self, path, data=None, content_type=None, **extra):
        if content_type is None and str(path).startswith(API):
            return super().post(
                path,
                urlencode(data or {}, doseq=True),
                content_type="application/x-www-form-urlencoded",
                **extra,
            )
        return super().post(path, data, content_type=content_type or MULTIPART, **extra)


def _usuario(username, perms=(ALTA, EDICION)):
    user = User.objects.create_user(username=username)
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    perfil = Profile.objects.get_or_create(user=user)[0]
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    return User.objects.get(pk=user.pk)


def _cliente(user, **kwargs):
    client = WebClient(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Sintético", provincia=Provincia.objects.create(nombre="Mendoza")
    )


@pytest.fixture(name="admin")
def admin_fixture():
    user = User.objects.create_superuser("c8-admin", "", "test1234")
    return _usuario_listo(user)


def _usuario_listo(user):
    perfil = Profile.objects.get_or_create(user=user)[0]
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    return User.objects.get(pk=user.pk)


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(
        apellido="Ramirez",
        nombre="Sofia",
        fecha_nacimiento=date.today() - timedelta(days=365 * 3),
        documento=44555666,
    )


def _crear(pk):
    return f"{API}centros/{pk}/nomina/crear/"


def _editar(pk, nomina_id):
    return f"{API}centros/{pk}/nomina/{nomina_id}/editar/"


def _campos(cuerpo):
    return {campo["name"]: campo for campo in cuerpo["fields"]}


def _nomina(centro, ciudadano):
    return NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        dni=ciudadano.documento,
        apellido=ciudadano.apellido,
        nombre=ciudadano.nombre,
        fecha_nacimiento=ciudadano.fecha_nacimiento,
        estado=NominaCentroInfancia.ESTADO_ACTIVO,
    )


def _estado():
    return (
        list(
            NominaCentroInfancia.objects.order_by("pk").values_list(
                "pk", "apellido", "nombre", "dni", "observaciones"
            )
        ),
        Ciudadano.objects.count(),
    )


# --- Form ---------------------------------------------------------------------


def test_create_without_query_shows_only_the_search(centro, admin):
    respuesta = _cliente(admin).get(_crear(centro.pk))
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert cuerpo["is_edit"] is False
    assert cuerpo["mostrar_formulario"] is False
    assert cuerpo["search"] == {
        "query": "",
        "ciudadanos": [],
        "no_resultados": False,
        "renaper_precarga": False,
        "renaper_prefill_token": None,
    }
    assert cuerpo["selected"] is None
    assert cuerpo["centro"]["nombre"] == "CDI Sintético"
    assert cuerpo["centro"]["provincia"] == "Mendoza"
    assert cuerpo["centro"]["departamento"] == "—"
    assert cuerpo["urls"]["cancelar"] == f"/centrodeinfancia/{centro.pk}/nomina/"


def test_form_projects_the_fields_the_template_draws(centro, admin):
    cuerpo = _cliente(admin).get(_crear(centro.pk) + "?query=99").json()

    assert [c["name"] for c in cuerpo["fields"]] == [
        n for n in CAMPOS if n not in MULTIPLES
    ]
    assert set(cuerpo["multiples"]) == set(MULTIPLES)
    campos = _campos(cuerpo)
    assert campos["apellido"]["required"] is True
    assert campos["sexo"]["widget"] == "select"
    assert campos["observaciones"]["widget"] == "textarea"
    assert campos["sin_cuil_nino"]["widget"] == "checkbox"
    assert campos["edad_calculada"]["disabled"] is True
    # A new ficha asks the RENAPER block of the responsables, not the child's.
    assert cuerpo["renaper"]["nino"] is None
    assert cuerpo["renaper"]["responsable_legal_1"]["permite_cambiar"] is True
    assert cuerpo["renaper"]["responsable_legal_2"]["opcional"] is True
    assert cuerpo["renaper"]["responsable_legal_1"]["token"] == ""


def test_search_by_dni_lists_local_citizens_without_asking_renaper(
    centro, admin, ciudadano
):
    with mock.patch(RENAPER) as consulta:
        cuerpo = _cliente(admin).get(_crear(centro.pk) + "?query=44555666").json()

    consulta.assert_not_called()
    assert cuerpo["mostrar_formulario"] is False
    assert cuerpo["search"]["query"] == "44555666"
    assert cuerpo["search"]["ciudadanos"] == [
        {
            "id": ciudadano.pk,
            "apellido": "Ramirez",
            "nombre": "Sofia",
            "documento": "44555666",
        }
    ]


def test_selected_citizen_prefills_the_ficha(centro, admin, ciudadano):
    url = _crear(centro.pk) + f"?query=44555666&ciudadano_id={ciudadano.pk}"

    cuerpo = _cliente(admin).get(url).json()

    campos = _campos(cuerpo)
    assert cuerpo["mostrar_formulario"] is True
    assert cuerpo["selected"]["id"] == ciudadano.pk
    assert campos["apellido"]["value"] == "Ramirez"
    assert campos["dni"]["value"] == "44555666"
    assert campos["fecha_nacimiento"]["value"] == ciudadano.fecha_nacimiento.isoformat()
    assert campos["provincia_domicilio"]["value"] == str(centro.provincia_id)


def test_query_without_results_asks_renaper_and_prefills_from_its_answer(centro, admin):
    respuesta = {
        "success": True,
        "message": "Datos obtenidos desde RENAPER.",
        "data": {
            "documento": 28456789,
            "apellido": "Pérez",
            "nombre": "Luis",
            "fecha_nacimiento": "2022-02-03",
        },
    }
    with mock.patch(RENAPER, return_value=respuesta) as consulta:
        cuerpo = _cliente(admin).get(_crear(centro.pk) + "?query=28456789").json()

    consulta.assert_called_once_with("28456789")
    assert cuerpo["mostrar_formulario"] is True
    assert cuerpo["search"]["no_resultados"] is True
    assert cuerpo["search"]["renaper_precarga"] is True
    assert cuerpo["search"]["renaper_prefill_token"]
    assert cuerpo["renaper_prefill_token"] == cuerpo["search"]["renaper_prefill_token"]
    assert _campos(cuerpo)["apellido"]["value"] == "Pérez"
    assert {"message": "Datos obtenidos desde RENAPER.", "level": "info"} in cuerpo[
        "messages"
    ]


def test_edit_projects_the_ficha_with_the_child_block(centro, admin, ciudadano):
    nomina = _nomina(centro, ciudadano)

    cuerpo = _cliente(admin).get(_editar(centro.pk, nomina.pk)).json()

    assert cuerpo["is_edit"] is True
    assert cuerpo["search"] is None
    assert cuerpo["mostrar_formulario"] is True
    assert cuerpo["selected"]["id"] == ciudadano.pk
    assert cuerpo["renaper"]["nino"]["bloque"] == "nino"
    assert cuerpo["renaper"]["nino"]["permite_cambiar"] is False
    assert _campos(cuerpo)["apellido"]["value"] == "Ramirez"
    assert cuerpo["urls"]["departamentos"]


# --- Save ---------------------------------------------------------------------


def test_post_creates_the_ficha_and_redirects_with_the_native_message(centro, admin):
    cliente = _cliente(admin)
    datos = datos_validos(centro, apellido="Torres", dni="45123456")

    respuesta = cliente.post(_crear(centro.pk), datos)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/{centro.pk}/nomina/",
    }
    nomina = NominaCentroInfancia.objects.get()
    assert (nomina.centro, nomina.apellido, nomina.dni) == (centro, "Torres", 45123456)
    assert nomina.ciudadano.documento == 45123456
    siguiente = cliente.get(_crear(centro.pk)).json()
    assert {
        "message": "Ficha creada y agregada a la nómina.",
        "level": "success",
    } in siguiente["messages"]


def test_rejected_post_changes_nothing_and_returns_the_errors(centro, admin):
    cliente = _cliente(admin)
    antes = _estado()

    respuesta = cliente.post(_crear(centro.pk), datos_validos(centro, apellido=""))

    cuerpo = respuesta.json()
    assert respuesta.status_code == 400
    assert _estado() == antes
    assert cuerpo["mostrar_formulario"] is True
    assert _campos(cuerpo)["apellido"]["errors"][0]["message"] == (
        "Este campo es obligatorio."
    )
    assert _campos(cuerpo)["nombre"]["value"] == "Luca"
    assert {
        "message": "Hay errores en la ficha de la nómina.",
        "level": "warning",
    } in cuerpo["messages"]


def test_the_ficha_of_a_citizen_already_in_the_nomina_is_not_duplicated(
    centro, admin, ciudadano
):
    _nomina(centro, ciudadano)
    antes = _estado()

    respuesta = _cliente(admin).post(
        _crear(centro.pk),
        datos_validos(centro, dni=str(ciudadano.documento), apellido="Ramirez"),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True
    assert _estado() == antes


def test_post_edit_updates_the_ficha(centro, admin, ciudadano):
    nomina = _nomina(centro, ciudadano)

    respuesta = _cliente(admin).post(
        _editar(centro.pk, nomina.pk),
        datos_validos(
            centro,
            dni=str(ciudadano.documento),
            apellido="Ramirez",
            nombre="Sofia",
            observaciones="Seguimiento sin novedades.",
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == f"/centrodeinfancia/{centro.pk}/nomina/"
    nomina.refresh_from_db()
    assert nomina.observaciones == "Seguimiento sin novedades."
    assert NominaCentroInfancia.objects.count() == 1


def test_rejected_edit_leaves_the_ficha_unchanged(centro, admin, ciudadano):
    nomina = _nomina(centro, ciudadano)
    antes = _estado()

    respuesta = _cliente(admin).post(
        _editar(centro.pk, nomina.pk),
        datos_validos(
            centro, dni=str(ciudadano.documento), nombre="", observaciones="x"
        ),
    )

    assert respuesta.status_code == 400
    assert _estado() == antes
    assert _campos(respuesta.json())["nombre"]["errors"]


def test_the_ficha_of_another_centre_is_404(centro, admin, ciudadano):
    otro = CentroDeInfancia.objects.create(nombre="Otro CDI")
    nomina = _nomina(otro, ciudadano)

    assert _cliente(admin).get(_editar(centro.pk, nomina.pk)).status_code == 404
    assert _cliente(admin).get(_crear(centro.pk + 999)).status_code == 404


# --- Access -------------------------------------------------------------------


def test_each_screen_keeps_its_native_permission(centro, ciudadano):
    nomina = _nomina(centro, ciudadano)
    solo_alta = _usuario("c8-alta", perms=(ALTA,))
    solo_edicion = _usuario("c8-edicion", perms=(EDICION,))

    assert _cliente(solo_alta).get(_crear(centro.pk)).status_code == 200
    assert _cliente(solo_alta).get(_editar(centro.pk, nomina.pk)).status_code == 403
    assert _cliente(solo_edicion).get(_crear(centro.pk)).status_code == 403
    assert _cliente(solo_edicion).get(_editar(centro.pk, nomina.pk)).status_code == 200
    sin = _usuario("c8-sin", perms=())
    assert (
        _cliente(sin).post(_crear(centro.pk), datos_validos(centro)).status_code == 403
    )
    assert NominaCentroInfancia.objects.count() == 1


def test_the_auditor_reads_but_cannot_save(centro, ciudadano):
    nomina = _nomina(centro, ciudadano)
    auditor = _usuario("c8-auditor")
    auditor.groups.add(Group.objects.get_or_create(name=UserGroups.SIMEPI_AUDITORIA)[0])
    antes = _estado()
    cliente = _cliente(auditor)

    assert cliente.get(_crear(centro.pk)).status_code == 200
    crear = cliente.post(_crear(centro.pk), datos_validos(centro))
    editar = cliente.post(
        _editar(centro.pk, nomina.pk),
        datos_validos(centro, dni=str(ciudadano.documento), observaciones="x"),
    )

    for veto in (crear, editar):
        assert veto.status_code == 403
        assert veto.json() == {"detail": VETO}
    assert _estado() == antes


def test_anonymous_gets_401_json(centro):
    for respuesta in (
        Client().get(_crear(centro.pk)),
        Client().post(_crear(centro.pk), {}),
        Client().get(_editar(centro.pk, 1)),
    ):
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert NominaCentroInfancia.objects.count() == 0


def test_post_without_csrf_token_is_403(centro, admin):
    cliente = _cliente(admin, enforce_csrf_checks=True)

    respuesta = cliente.post(_crear(centro.pk), datos_validos(centro))

    assert respuesta.status_code == 403
    assert NominaCentroInfancia.objects.count() == 0


def test_other_methods_and_body_formats_are_refused(centro, admin):
    cliente = _cliente(admin)

    assert cliente.put(_crear(centro.pk)).status_code == 405
    respuesta = cliente.post(_crear(centro.pk), "{}", content_type="application/json")
    assert respuesta.status_code == 415
    assert NominaCentroInfancia.objects.count() == 0
