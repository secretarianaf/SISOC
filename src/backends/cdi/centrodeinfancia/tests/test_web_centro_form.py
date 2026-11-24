"""CDI centre create and edit: web API (G1 v1) over the native views.

The API inherits ``CentroDeInfanciaCreateView`` / ``CentroDeInfanciaUpdateView``,
so the form, the scope, the signed RENAPER token of the referente, the save, the
referente provisioning, the messages and the CDI-A3 auditor veto are the native
ones. RENAPER and the provisioning are always stubbed.
"""

from datetime import time
from unittest import mock
from urllib.parse import urlencode

import pytest
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.test import Client
from django.test.client import MULTIPART_CONTENT as MULTIPART

from centrodeinfancia.models import (
    CentroDeInfancia,
    CentroDeInfanciaHorarioFuncionamiento,
    DepartamentoIpi,
    OfertaServicio,
)
from centrodeinfancia.services_renaper_bloques import BLOQUE_REFERENTE, crear_token
from centrodeinfancia.tests.test_centrodeinfancia_form import (
    CUIT_VALIDO,
    datos_validos,
)
from centrodeinfancia.web_api_centro_form import CAMPOS, MULTIPLES
from core import web_gate
from core.constants import UserGroups
from core.models import Localidad, Municipio, Provincia
from users.models import Profile, ProfileTerritorialScope

API = "/api/web/cdi/"
PROVISION = "centrodeinfancia.views.actualizar_referente_cdi"
RENAPER = "centrodeinfancia.views.consultar_bloque"
VETO = "El rol Auditoría tiene acceso de solo lectura."
ALTA = "centrodeinfancia.add_centrodeinfancia"
EDICION = "centrodeinfancia.change_centrodeinfancia"

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
    return _listo(user)


def _listo(user):
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


@pytest.fixture(name="admin")
def admin_fixture():
    return _listo(User.objects.create_superuser("c9-admin", "", "test1234"))


@pytest.fixture(name="ubicacion")
def ubicacion_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    departamento = DepartamentoIpi.objects.create(
        codigo_departamento="06515", provincia=provincia, nombre="Moreno", decil_ipi=3
    )
    municipio = Municipio.objects.create(nombre="Moreno", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Paso del Rey", municipio=municipio)
    return {
        "provincia": provincia,
        "departamento": departamento,
        "municipio": municipio,
        "localidad": localidad,
    }


@pytest.fixture(name="servicio")
def servicio_fixture():
    return OfertaServicio.objects.get_or_create(
        codigo="multiedad", defaults={"orden": 5}
    )[0]


def _crear():
    return f"{API}centros/crear/"


def _editar(pk):
    return f"{API}centros/{pk}/editar/"


def _campos(cuerpo):
    return {campo["name"]: campo for campo in cuerpo["fields"]}


def _datos(ubicacion, servicio, **cambios):
    return datos_validos(ubicacion, servicio, **cambios)


def _centro(ubicacion, servicio, **cambios):
    """A saved centre, through the native form (the way the page creates it)."""
    admin = User.objects.filter(username="c9-admin").first() or _listo(
        User.objects.create_superuser("c9-admin", "", "test1234")
    )
    with mock.patch(PROVISION):
        _cliente(admin).post(_crear(), _datos(ubicacion, servicio, **cambios))
    return CentroDeInfancia.objects.order_by("-pk").first()


def _estado():
    return (
        list(
            CentroDeInfancia.objects.order_by("pk").values_list(
                "pk", "nombre", "organizacion", "cuil_referente", "latitud"
            )
        ),
        CentroDeInfanciaHorarioFuncionamiento.objects.count(),
    )


# --- Form ---------------------------------------------------------------------


def test_create_projects_the_fields_the_template_draws(admin, ubicacion, servicio):
    respuesta = _cliente(admin).get(_crear())
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert cuerpo["is_edit"] is False
    assert [campo["name"] for campo in cuerpo["fields"]] == list(CAMPOS)
    assert set(cuerpo["multiples"]) == set(MULTIPLES)
    assert [dia["dia"] for dia in cuerpo["dias"]][:2] == ["lunes", "martes"]
    campos = _campos(cuerpo)
    assert campos["nombre"]["required"] is True
    assert campos["ambito"]["widget"] == "select"
    assert [c["value"] for c in campos["ambito"]["choices"]] == ["", "rural", "urbano"]
    assert campos["decil_ipi"]["disabled"] is True
    assert campos["fecha_inicio"]["widget"] == "number"
    assert campos["horario_lunes_apertura"]["widget"] == "time"
    assert [o["label"] for o in cuerpo["multiples"]["oferta_servicios"]["options"]] == [
        str(servicio)
    ]
    assert cuerpo["renaper"]["bloque"] == "referente"
    assert cuerpo["renaper"]["modo"] == "dni"
    assert cuerpo["renaper"]["token"] == ""
    assert cuerpo["renaper"]["campos"] == [
        "dni_referente",
        "apellido_referente",
        "nombre_referente",
        "cuil_referente",
    ]
    assert cuerpo["urls"]["cancelar"] == "/centrodeinfancia/listar"
    assert cuerpo["urls"]["address_preview"] == "/ajax/ubicacion/previsualizar/"


def test_edit_projects_the_saved_centre(admin, ubicacion, servicio):
    centro = _centro(
        ubicacion,
        servicio,
        latitud="-34.5",
        horario_lunes_apertura="08:00",
        horario_lunes_cierre="17:30",
    )

    cuerpo = _cliente(admin).get(_editar(centro.pk)).json()

    campos = _campos(cuerpo)
    assert cuerpo["is_edit"] is True
    assert campos["nombre"]["value"] == "PULGARCITO"
    assert campos["fecha_inicio"]["value"] == "1995"
    assert campos["provincia"]["value"] == str(ubicacion["provincia"].pk)
    assert campos["departamento"]["value"] == str(ubicacion["departamento"].pk)
    assert campos["decil_ipi"]["value"] == "3"
    assert campos["horario_lunes_apertura"]["value"] == "08:00:00"
    assert campos["horario_lunes_cierre"]["value"] == "17:30:00"
    assert campos["latitud"]["value"] == "-34.500000"
    checked = [
        o["value"]
        for o in cuerpo["multiples"]["dias_funcionamiento"]["options"]
        if o["checked"]
    ]
    assert checked == ["lunes", "martes"]
    assert [
        o["checked"] for o in cuerpo["multiples"]["oferta_servicios"]["options"]
    ] == [True]
    assert cuerpo["urls"]["cancelar"] == f"/centrodeinfancia/detalle/{centro.pk}"


# --- Save ---------------------------------------------------------------------


def test_post_creates_the_centre_and_redirects_with_the_native_message(
    admin, ubicacion, servicio
):
    cliente = _cliente(admin)

    with mock.patch(
        PROVISION,
        side_effect=lambda request, centro, anterior: messages.success(
            request, "Usuario referente creado."
        ),
    ) as provision:
        respuesta = cliente.post(
            _crear(),
            _datos(
                ubicacion,
                servicio,
                horario_lunes_apertura="08:00",
                horario_lunes_cierre="12:30",
                latitud="-34.6",
                longitud="-58.4",
            ),
        )

    centro = CentroDeInfancia.objects.get()
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/detalle/{centro.pk}",
    }
    assert (centro.nombre, centro.cuit_organizacion_gestiona) == (
        "PULGARCITO",
        "20445350304",
    )
    assert centro.provincia == ubicacion["provincia"]
    assert centro.dias_funcionamiento == ["lunes", "martes"]
    assert list(centro.oferta_servicios.all()) == [servicio]
    horario = centro.horarios_funcionamiento.get(dia="lunes")
    assert (horario.hora_apertura, horario.hora_cierre) == (time(8), time(12, 30))
    provision.assert_called_once()
    assert provision.call_args.args[1] == centro
    siguiente = cliente.get(_crear()).json()
    assert siguiente["messages"] == [
        {"message": "Usuario referente creado.", "level": "success"}
    ]


def test_rejected_post_changes_nothing_and_returns_the_errors(
    admin, ubicacion, servicio
):
    antes = _estado()

    with mock.patch(PROVISION) as provision:
        respuesta = _cliente(admin).post(
            _crear(), _datos(ubicacion, servicio, nombre="", organizacion="Mi org")
        )

    cuerpo = respuesta.json()
    campos = _campos(cuerpo)
    assert respuesta.status_code == 400
    assert _estado() == antes
    provision.assert_not_called()
    assert campos["nombre"]["errors"][0]["message"] == "Este campo es obligatorio."
    assert campos["organizacion"]["value"] == "Mi org"
    assert campos["provincia"]["value"] == str(ubicacion["provincia"].pk)
    assert [
        o["value"]
        for o in cuerpo["multiples"]["dias_funcionamiento"]["options"]
        if o["checked"]
    ] == ["lunes", "martes"]


def test_duplicate_centre_is_rejected_with_the_native_form_errors(
    admin, ubicacion, servicio
):
    _centro(ubicacion, servicio)
    antes = _estado()

    respuesta = _cliente(admin).post(
        _crear(), _datos(ubicacion, servicio, nombre="Otro nombre")
    )

    cuerpo = respuesta.json()
    assert respuesta.status_code == 400
    assert _estado() == antes
    assert cuerpo["non_field_errors"][0].startswith("Ya existe el CDI")
    assert _campos(cuerpo)["cuil_referente"]["errors"]


def test_post_edit_updates_the_centre_and_its_hours(admin, ubicacion, servicio):
    centro = _centro(
        ubicacion,
        servicio,
        horario_lunes_apertura="08:00",
        horario_lunes_cierre="12:00",
    )

    with mock.patch(PROVISION) as provision:
        respuesta = _cliente(admin).post(
            _editar(centro.pk),
            _datos(
                ubicacion,
                servicio,
                nombre="Pulgarcito II",
                horario_lunes_apertura="09:00",
                horario_lunes_cierre="13:00",
            ),
        )

    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == f"/centrodeinfancia/detalle/{centro.pk}"
    centro.refresh_from_db()
    assert centro.nombre == "Pulgarcito II"
    assert centro.horarios_funcionamiento.get(dia="lunes").hora_apertura == time(9)
    assert CentroDeInfancia.objects.count() == 1
    provision.assert_called_once()
    assert provision.call_args.kwargs["anterior"]["nombre_referente"] == "Ana"


def test_rejected_edit_leaves_the_centre_unchanged(admin, ubicacion, servicio):
    centro = _centro(ubicacion, servicio)
    antes = _estado()

    with mock.patch(PROVISION) as provision:
        respuesta = _cliente(admin).post(
            _editar(centro.pk),
            _datos(ubicacion, servicio, nombre="Cambio", codigo_postal="12"),
        )

    assert respuesta.status_code == 400
    assert _estado() == antes
    provision.assert_not_called()
    assert _campos(respuesta.json())["codigo_postal"]["errors"]


def test_hours_of_an_unchecked_day_are_rejected(admin, ubicacion, servicio):
    antes = _estado()

    respuesta = _cliente(admin).post(
        _crear(),
        _datos(
            ubicacion,
            servicio,
            horario_domingo_apertura="08:00",
            horario_domingo_cierre="09:00",
        ),
    )

    assert respuesta.status_code == 400
    assert _estado() == antes
    assert _campos(respuesta.json())["horario_domingo_cierre"]["errors"][0][
        "message"
    ] == ("El día debe estar seleccionado para cargar horarios.")


# --- RENAPER ------------------------------------------------------------------


def _token(user, **valores):
    base = {
        "dni_referente": "30111222",
        "apellido_referente": "Verificada",
        "nombre_referente": "Rita",
        "cuil_referente": CUIT_VALIDO,
    }
    base.update(valores)
    return crear_token(BLOQUE_REFERENTE, user, base)


def test_the_referente_lookup_goes_through_the_native_renaper_view(admin):
    respuesta_renaper = {
        "success": True,
        "message": "Datos obtenidos desde RENAPER.",
        "valores": {"dni_referente": "30111222", "nombre_referente": "Rita"},
    }

    with mock.patch(RENAPER, return_value=respuesta_renaper) as consulta:
        respuesta = _cliente(admin).get(f"{API}renaper/referente/?dni=30111222")

    assert respuesta.status_code == 200
    assert respuesta.json()["valores"]["nombre_referente"] == "Rita"
    assert respuesta.json()["token"]
    consulta.assert_called_once_with("referente", "30111222")


def test_the_signed_token_decides_the_locked_values_not_the_post(
    admin, ubicacion, servicio
):
    datos = _datos(
        ubicacion,
        servicio,
        dni_referente="99999999",
        nombre_referente="Adulterado",
        apellido_referente="Adulterado",
        cuil_referente="20-11111111-2",
        renaper_token_referente=_token(admin),
    )

    with mock.patch(PROVISION):
        respuesta = _cliente(admin).post(_crear(), datos)

    centro = CentroDeInfancia.objects.get()
    assert respuesta.status_code == 200
    assert (
        centro.dni_referente,
        centro.nombre_referente,
        centro.apellido_referente,
    ) == (
        "30111222",
        "Rita",
        "Verificada",
    )
    assert "dni_referente" in centro.campos_verificados_renaper


def test_a_verified_referente_comes_back_locked(admin, ubicacion, servicio):
    datos = _datos(ubicacion, servicio, renaper_token_referente=_token(admin))
    with mock.patch(PROVISION):
        _cliente(admin).post(_crear(), datos)
    centro = CentroDeInfancia.objects.get()

    cuerpo = _cliente(admin).get(_editar(centro.pk)).json()

    assert cuerpo["renaper"]["modo"] == "verificado"
    assert cuerpo["renaper"]["verificado"] is True
    campos = _campos(cuerpo)
    for nombre in cuerpo["renaper"]["campos"]:
        assert campos[nombre]["disabled"] is True
        assert campos[nombre]["renaper"] is True


def test_a_token_of_another_user_is_ignored(admin, ubicacion, servicio):
    otro = _usuario("c9-otro")
    datos = _datos(
        ubicacion,
        servicio,
        nombre_referente="Manual",
        renaper_token_referente=_token(otro),
    )

    with mock.patch(PROVISION):
        _cliente(admin).post(_crear(), datos)

    centro = CentroDeInfancia.objects.get()
    assert centro.nombre_referente == "Manual"
    assert not centro.campos_verificados_renaper


# --- Access -------------------------------------------------------------------


def test_each_screen_keeps_its_native_permission(ubicacion, servicio):
    centro = _centro(ubicacion, servicio)
    solo_alta = _usuario("c9-alta", perms=(ALTA,))
    solo_edicion = _usuario("c9-edicion", perms=(EDICION,))

    assert _cliente(solo_alta).get(_crear()).status_code == 200
    assert _cliente(solo_alta).get(_editar(centro.pk)).status_code == 403
    assert _cliente(solo_edicion).get(_crear()).status_code == 403
    assert _cliente(solo_edicion).get(_editar(centro.pk)).status_code == 200
    sin = _usuario("c9-sin", perms=())
    antes = _estado()
    assert _cliente(sin).post(_crear(), _datos(ubicacion, servicio)).status_code == 403
    assert _estado() == antes


def test_the_centre_outside_the_scope_is_404(ubicacion, servicio):
    centro = _centro(ubicacion, servicio)
    ajena = Provincia.objects.create(nombre="Otra provincia")
    usuario = _usuario("c9-scope", perms=(EDICION,))
    usuario.profile.es_usuario_provincial = True
    usuario.profile.save(update_fields=["es_usuario_provincial"])
    ProfileTerritorialScope.objects.create(profile=usuario.profile, provincia=ajena)

    assert _cliente(usuario).get(_editar(centro.pk)).status_code == 404
    assert _cliente(usuario).post(_editar(centro.pk), {}).status_code == 404
    assert _cliente(usuario).get(_editar(centro.pk + 999)).status_code == 404


def test_the_auditor_reads_but_cannot_save(ubicacion, servicio):
    centro = _centro(ubicacion, servicio)
    auditor = _usuario("c9-auditor")
    auditor.groups.add(Group.objects.get_or_create(name=UserGroups.SIMEPI_AUDITORIA)[0])
    antes = _estado()
    cliente = _cliente(auditor)

    assert cliente.get(_crear()).status_code == 200
    crear = cliente.post(_crear(), _datos(ubicacion, servicio, nombre="Nuevo"))
    editar = cliente.post(
        _editar(centro.pk), _datos(ubicacion, servicio, nombre="Cambio")
    )

    for veto in (crear, editar):
        assert veto.status_code == 403
        assert veto.json() == {"detail": VETO}
    assert _estado() == antes


def test_anonymous_gets_401_json():
    for respuesta in (
        Client().get(_crear()),
        Client().post(_crear(), {}),
        Client().get(_editar(1)),
    ):
        assert respuesta.status_code == 401
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert CentroDeInfancia.objects.count() == 0


def test_post_without_csrf_token_is_403(admin, ubicacion, servicio):
    cliente = _cliente(admin, enforce_csrf_checks=True)

    respuesta = cliente.post(_crear(), _datos(ubicacion, servicio))

    assert respuesta.status_code == 403
    assert CentroDeInfancia.objects.count() == 0


def test_other_methods_and_body_formats_are_refused(admin):
    cliente = _cliente(admin)

    assert cliente.put(_crear()).status_code == 405
    respuesta = cliente.post(_crear(), "{}", content_type="application/json")
    assert respuesta.status_code == 415
    assert CentroDeInfancia.objects.count() == 0


def test_a_province_locked_user_sees_the_province_disabled(ubicacion, servicio):
    usuario = _usuario("c9-provincial", perms=(ALTA,))
    usuario.profile.es_usuario_provincial = True
    usuario.profile.save(update_fields=["es_usuario_provincial"])
    ProfileTerritorialScope.objects.create(
        profile=usuario.profile, provincia=ubicacion["provincia"]
    )

    campos = _campos(_cliente(usuario).get(_crear()).json())

    assert campos["provincia"]["disabled"] is True
    assert campos["provincia"]["value"] == str(ubicacion["provincia"].pk)
