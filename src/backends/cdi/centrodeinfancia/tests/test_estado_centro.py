"""Estado del CDI: Activo, Pendiente o Baja (#2945).

Botón "Estado" del legajo (vista nativa y su par de la API web), permisos por
grupo según la semilla, alcance territorial de EGP y trazabilidad. La exclusión
del PDF y la columna del Excel se prueban en test_nomina_ninos_pdf.py y
test_reportes.py.
"""

import re
from urllib.parse import urlencode

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Group, Permission, User
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from centrodeinfancia.models import CentroDeInfancia
from core.constants import UserGroups
from core.models import Provincia
from users.bootstrap.groups_seed import permission_codes_for_bootstrap_group
from users.models import Profile, ProfileTerritorialScope

pytestmark = pytest.mark.django_db

PERMISO = "centrodeinfancia.cambiar_estado_centrodeinfancia"
EDITAN = (
    UserGroups.SIMEPI_ADMINISTRADOR,
    UserGroups.SIMEPI_EQUIPO_NACIONAL,
    UserGroups.SIMEPI_EGP,
)
SOLO_VEN = (
    UserGroups.SIMEPI_ANALISTA_DATOS,
    UserGroups.SIMEPI_AUDITORIA,
    "CDI - Referente centro",
)


def _grupo_sembrado(nombre):
    """El grupo con los permisos de users/bootstrap/groups_seed.py."""
    grupo, _ = Group.objects.get_or_create(name=nombre)
    for code in permission_codes_for_bootstrap_group(nombre):
        app, codename = code.split(".", 1)
        permiso = Permission.objects.filter(
            content_type__app_label=app, codename=codename
        ).first()
        if permiso:
            grupo.permissions.add(permiso)
    return grupo


def _usuario(username, *, grupo=None, superuser=False, provincia=None):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    if grupo:
        user.groups.add(_grupo_sembrado(grupo))
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    if provincia is not None:
        profile.es_usuario_provincial = True
        profile.provincia = provincia
        ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    profile.save()
    return User.objects.get(pk=user.pk)


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


def _nativo(centro):
    return reverse("centrodeinfancia_estado", args=[centro.pk])


def _web(centro):
    return f"/api/web/cdi/centros/{centro.pk}/estado/"


def _post_web(client, centro, estado):
    return client.post(
        _web(centro),
        urlencode({"estado": estado}),
        content_type="application/x-www-form-urlencoded",
    )


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Estados", provincia=Provincia.objects.create(nombre="Salta")
    )


def test_un_cdi_nuevo_queda_activo(centro):
    assert centro.estado == CentroDeInfancia.Estado.ACTIVO


def test_la_semilla_da_el_permiso_solo_a_los_grupos_del_pedido():
    for nombre in EDITAN:
        assert PERMISO in permission_codes_for_bootstrap_group(nombre), nombre
    for nombre in SOLO_VEN:
        assert PERMISO not in permission_codes_for_bootstrap_group(nombre), nombre


def test_superusuario_cambia_el_estado_y_queda_en_el_historial(centro):
    client = _cliente(_usuario("estado-super", superuser=True))

    respuesta = client.post(_nativo(centro), {"estado": "pendiente"})

    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse(
        "centrodeinfancia_detalle", args=[centro.pk]
    )
    centro.refresh_from_db()
    assert centro.estado == "pendiente"
    assert [str(m) for m in get_messages(respuesta.wsgi_request)] == [
        "Estado del CDI actualizado a «Pendiente»."
    ]
    cambio = LogEntry.objects.get_for_object(centro).latest("timestamp")
    assert cambio.changes_dict["estado"] == ["activo", "pendiente"]
    assert cambio.actor.username == "estado-super"


@pytest.mark.parametrize("grupo", EDITAN)
def test_los_grupos_del_pedido_pueden_cambiarlo(centro, grupo):
    provincia = centro.provincia if grupo == UserGroups.SIMEPI_EGP else None
    client = _cliente(_usuario(f"estado-{grupo}", grupo=grupo, provincia=provincia))

    assert client.post(_nativo(centro), {"estado": "baja"}).status_code == 302
    centro.refresh_from_db()
    assert centro.estado == "baja"


@pytest.mark.parametrize("grupo", SOLO_VEN)
def test_el_resto_recibe_403_y_no_cambia_nada(centro, grupo):
    client = _cliente(_usuario(f"estado-no-{grupo}", grupo=grupo))

    assert client.post(_nativo(centro), {"estado": "baja"}).status_code == 403
    assert _post_web(client, centro, "baja").status_code == 403
    centro.refresh_from_db()
    assert centro.estado == "activo"


def test_egp_no_cambia_un_cdi_fuera_de_su_alcance(centro):
    otra = Provincia.objects.create(nombre="Jujuy")
    client = _cliente(
        _usuario("estado-egp-ajeno", grupo=UserGroups.SIMEPI_EGP, provincia=otra)
    )

    assert client.post(_nativo(centro), {"estado": "baja"}).status_code == 404
    centro.refresh_from_db()
    assert centro.estado == "activo"


@pytest.mark.parametrize("valor", ["", "eliminado", "ACTIVO"])
def test_un_estado_invalido_no_se_guarda(centro, valor):
    client = _cliente(_usuario(f"estado-invalido-{valor}", superuser=True))

    respuesta = client.post(_nativo(centro), {"estado": valor})

    assert respuesta.status_code == 302
    centro.refresh_from_db()
    assert centro.estado == "activo"
    assert [str(m) for m in get_messages(respuesta.wsgi_request)] == [
        "El estado elegido no es válido."
    ]


def test_solo_acepta_post(centro):
    client = _cliente(_usuario("estado-get", superuser=True))

    assert client.get(_nativo(centro)).status_code == 405


def test_la_api_web_aplica_el_cambio_y_devuelve_la_redireccion_nativa(centro):
    client = _cliente(_usuario("estado-web", superuser=True))

    respuesta = _post_web(client, centro, "baja")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/detalle/{centro.pk}",
    }
    centro.refresh_from_db()
    assert centro.estado == "baja"


def test_el_legajo_muestra_el_estado_y_el_boton_solo_a_quien_edita(centro):
    centro.estado = CentroDeInfancia.Estado.PENDIENTE
    centro.save(update_fields=["estado"])
    url = reverse("centrodeinfancia_detalle", args=[centro.pk])

    editor = _cliente(_usuario("estado-ve-editor", superuser=True)).get(url)
    lector = _cliente(
        _usuario("estado-ve-lector", grupo=UserGroups.SIMEPI_ANALISTA_DATOS)
    ).get(url)

    for respuesta in (editor, lector):
        html = respuesta.content.decode()
        assert respuesta.status_code == 200
        assert re.search(
            r'class="cdf-pill cdf-pill--gold"\s+id="cdiEstadoPill">Pendiente</span>',
            html,
        )
    assert 'data-bs-target="#modalEstadoCentro"' in editor.content.decode()
    assert 'id="modalEstadoCentro"' in editor.content.decode()
    assert 'data-bs-target="#modalEstadoCentro"' not in lector.content.decode()
    assert 'id="modalEstadoCentro"' not in lector.content.decode()


def test_la_api_web_del_legajo_informa_estado_y_url_segun_permiso(centro):
    centro.estado = CentroDeInfancia.Estado.BAJA
    centro.save(update_fields=["estado"])
    url = f"/api/web/cdi/centros/{centro.pk}/"

    editor = _cliente(_usuario("estado-api-editor", superuser=True)).get(url).json()
    lector = (
        _cliente(_usuario("estado-api-lector", grupo=UserGroups.SIMEPI_ANALISTA_DATOS))
        .get(url)
        .json()
    )

    for data in (editor, lector):
        assert (data["centro"]["estado"], data["centro"]["estado_display"]) == (
            "baja",
            "Baja",
        )
    assert editor["header"]["estado_url"] == _web(centro)
    assert lector["header"]["estado_url"] is None
