"""Alcance por programa de comedores (PNUD / Alimentar comunidad) por usuario."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import AlcanceProgramaComedor, Comedor, Programas
from comedores.services import alcance_programa as alcance
from comedores.services.comedor_service import ComedorService
from core.constants import UserGroups
from core.models import Provincia
from pwa.user_forms import (
    CustomUserChangeForm as CompositeUserChangeForm,
    UserCreationForm as CompositeUserCreationForm,
)
from relevamientos.models import (
    ActaComplementaria,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

ALIMENTAR = "Alimentar comunidad"
SECOS = "Abordaje comunitario - Línea Secos"
TRADICIONAL = "Abordaje comunitario - Línea Tradicional"
PNUD = AlcanceProgramaComedor.PNUD
ALIM = AlcanceProgramaComedor.ALIMENTAR_COMUNIDAD


def _user(username, *grupos_negocio, superuser=False):
    user = get_user_model().objects.create_user(
        username=username, password="x", is_superuser=superuser
    )
    for grupo in grupos_negocio:
        AlcanceProgramaComedor.objects.create(profile=user.profile, programa=grupo)
    return get_user_model().objects.get(pk=user.pk)


@pytest.fixture
def escenario():
    provincia = Provincia.objects.create(nombre="Prov Alcance Programa")
    alimentar, _ = Programas.objects.get_or_create(nombre=ALIMENTAR)
    secos, _ = Programas.objects.get_or_create(nombre=SECOS)
    tradicional, _ = Programas.objects.get_or_create(nombre=TRADICIONAL)
    otro = Programas.objects.create(nombre="Otro programa cualquiera")
    comedores = {
        "alimentar": Comedor.objects.create(
            nombre="C Alimentar", provincia=provincia, programa=alimentar
        ),
        "secos": Comedor.objects.create(
            nombre="C Secos", provincia=provincia, programa=secos
        ),
        "tradicional": Comedor.objects.create(
            nombre="C Tradicional", provincia=provincia, programa=tradicional
        ),
        "otro": Comedor.objects.create(
            nombre="C Otro", provincia=provincia, programa=otro
        ),
        "nulo": Comedor.objects.create(nombre="C Nulo", provincia=provincia),
    }
    return provincia, comedores


def _ids(comedores, *claves):
    return {comedores[clave].id for clave in claves}


# ------------------------------------------------------------------ helper


def test_programas_visibles_sin_nada_o_ambos_es_sin_restriccion():
    assert alcance.programas_visibles(_user("sin_nada")) is None
    assert alcance.programas_visibles(_user("ambos", PNUD, ALIM)) is None
    assert alcance.programas_visibles(None) is None


def test_programas_visibles_un_grupo_y_superuser():
    assert alcance.programas_visibles(_user("solo_pnud", PNUD)) == {PNUD}
    assert alcance.programas_visibles(_user("solo_alim", ALIM)) == {ALIM}
    assert alcance.programas_visibles(_user("su", PNUD, superuser=True)) is None


def test_apply_programa_scope_traduce_grupos_por_nombre(escenario):
    _, comedores = escenario
    todos = Comedor.objects.all()

    pnud = alcance.apply_programa_scope(todos, _user("u_pnud", PNUD))
    alim = alcance.apply_programa_scope(todos, _user("u_alim", ALIM))
    libre = alcance.apply_programa_scope(todos, _user("u_libre"))

    assert set(pnud.values_list("id", flat=True)) == _ids(
        comedores, "secos", "tradicional"
    )
    assert set(alim.values_list("id", flat=True)) == _ids(comedores, "alimentar")
    assert libre.count() == 5


def test_programas_visibles_se_cachea_en_la_instancia():
    user = _user("cache_user", PNUD)
    alcance.programas_visibles(user)
    AlcanceProgramaComedor.objects.filter(profile=user.profile).delete()
    assert alcance.programas_visibles(user) == {PNUD}
    alcance.invalidar_cache_alcance_programa(user)
    assert alcance.programas_visibles(user) is None


# ------------------------------------------------------- backoffice service


def test_listado_y_detalle_restringido_a_pnud(escenario):
    _, comedores = escenario
    user = _user("bo_pnud", PNUD)

    rows = ComedorService.get_filtered_comedores({}, user=user)
    assert {row["id"] for row in rows} == _ids(comedores, "secos", "tradicional")

    scoped = ComedorService.get_scoped_comedor_or_404(comedores["secos"].id, user)
    assert scoped.id == comedores["secos"].id
    for clave in ("alimentar", "otro", "nulo"):
        with pytest.raises(Http404):
            ComedorService.get_scoped_comedor_or_404(comedores[clave].id, user)
    with pytest.raises(Http404):
        ComedorService.get_comedor_detail_object(comedores["nulo"].id, user)


def test_listado_sin_restriccion_y_superuser_ven_todo(escenario):
    _, comedores = escenario
    for user in (_user("bo_libre"), _user("bo_ambos", PNUD, ALIM)):
        rows = ComedorService.get_filtered_comedores({}, user=user)
        assert len(list(rows)) == 5
    superuser = _user("bo_su", PNUD, superuser=True)
    assert len(list(ComedorService.get_filtered_comedores({}, user=superuser))) == 5
    assert (
        ComedorService.get_scoped_comedor_or_404(comedores["nulo"].id, superuser).pk
        == comedores["nulo"].pk
    )


def test_coordinador_general_restringido_queda_filtrado_por_programa(escenario):
    _, comedores = escenario
    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_coordinador_general",
        defaults={"name": "Rol coordinador general"},
    )
    grupo, _ = Group.objects.get_or_create(name=UserGroups.COORDINADOR_GENERAL)
    grupo.permissions.add(permiso)

    libre = _user("cg_libre")
    restringido = _user("cg_alim", ALIM)
    for user in (libre, restringido):
        user.groups.add(grupo)
        user.user_permissions.add(permiso)

    libre = get_user_model().objects.get(pk=libre.pk)
    restringido = get_user_model().objects.get(pk=restringido.pk)
    assert len(list(ComedorService.get_filtered_comedores({}, user=libre))) == 5
    rows = ComedorService.get_filtered_comedores({}, user=restringido)
    assert {row["id"] for row in rows} == _ids(comedores, "alimentar")


def test_vista_detalle_backoffice_404_fuera_de_programa(client, escenario):
    _, comedores = escenario
    user = _user("web_alim", ALIM)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="comedores", codename="view_comedor"
        )
    )
    client.force_login(user)

    fuera = client.get(reverse("comedor_detalle", kwargs={"pk": comedores["secos"].pk}))
    assert fuera.status_code == 404


# ----------------------------------------------- vistas web de registros


@pytest.fixture
def registros(escenario):
    _, comedores = escenario
    relevados = {}
    for clave in ("alimentar", "secos"):
        comedor = comedores[clave]
        relevamiento = Relevamiento.objects.create(
            comedor=comedor, estado="Visita pendiente"
        )
        seguimiento = PrimerSeguimiento.objects.create(
            id_relevamiento=relevamiento, numero_orden=1
        )
        pnud = SeguimientoPnud.objects.create(
            comedor=comedor, formulario=SeguimientoPnud.FORMULARIO_SECOS
        )
        acta = ActaComplementaria.objects.create(comedor=comedor)
        relevados[clave] = (comedor, relevamiento, seguimiento, pnud, acta)
    return relevados


def _urls_de(comedor, relevamiento, seguimiento, pnud, acta):
    cpk = comedor.pk
    return [
        reverse("relevamientos", kwargs={"comedor_pk": cpk}),
        reverse(
            "relevamiento_detalle", kwargs={"comedor_pk": cpk, "pk": relevamiento.pk}
        ),
        reverse(
            "seguimiento_detalle",
            kwargs={
                "comedor_pk": cpk,
                "relevamiento_pk": relevamiento.pk,
                "pk": seguimiento.pk,
            },
        ),
        reverse("seguimiento_pnud_detalle", kwargs={"comedor_pk": cpk, "pk": pnud.pk}),
        reverse(
            "acta_complementaria_detalle", kwargs={"comedor_pk": cpk, "pk": acta.pk}
        ),
        reverse("acta_complementaria_crear", kwargs={"comedor_pk": cpk}),
    ]


def _cliente_web(client, user):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=[
                "view_relevamiento",
                "add_actacomplementaria",
                "change_actacomplementaria",
            ],
        )
    )
    client.force_login(user)
    return client


def test_vistas_de_registros_404_fuera_de_programa(client, registros):
    cliente = _cliente_web(client, _user("reg_alim", ALIM))

    for url in _urls_de(*registros["secos"]):
        assert cliente.get(url).status_code == 404, url
    inexistente = cliente.get(reverse("relevamientos", kwargs={"comedor_pk": 0}))
    assert inexistente.status_code == 404


def test_vistas_de_registros_responden_dentro_de_programa(client, registros):
    cliente = _cliente_web(client, _user("reg_alim_ok", ALIM))

    comedor, relevamiento, *_ = registros["alimentar"]
    listado = cliente.get(reverse("relevamientos", kwargs={"comedor_pk": comedor.pk}))
    assert listado.status_code == 200
    detalle = cliente.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor.pk, "pk": relevamiento.pk},
        )
    )
    assert detalle.status_code == 200


def test_detalle_de_relevamiento_exige_que_sea_del_comedor_de_la_url(client, registros):
    cliente = _cliente_web(client, _user("reg_cruzado", ALIM))
    comedor_propio = registros["alimentar"][0]
    relevamiento_ajeno = registros["secos"][1]

    response = cliente.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor_propio.pk, "pk": relevamiento_ajeno.pk},
        )
    )
    assert response.status_code == 404


@pytest.mark.parametrize("nombre", ["relevamiento_editar", "relevamiento_eliminar"])
def test_editar_y_eliminar_relevamiento_exigen_que_sea_del_comedor_de_la_url(
    client, registros, nombre
):
    user = _user(f"reg_cruzado_{nombre}", ALIM)
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename="change_relevamiento",
        )
    )
    cliente = _cliente_web(client, user)
    comedor_propio = registros["alimentar"][0]
    relevamiento_ajeno = registros["secos"][1]
    url = reverse(
        nombre, kwargs={"comedor_pk": comedor_propio.pk, "pk": relevamiento_ajeno.pk}
    )

    assert cliente.get(url).status_code == 404
    assert cliente.post(url).status_code == 404
    relevamiento_ajeno.refresh_from_db()
    assert relevamiento_ajeno.comedor_id == registros["secos"][0].pk


def test_vistas_de_registros_sin_restriccion_ven_todo(client, registros):
    cliente = _cliente_web(client, _user("reg_libre"))
    comedor, relevamiento, *_ = registros["secos"]
    response = cliente.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor.pk, "pk": relevamiento.pk},
        )
    )
    assert response.status_code == 200


# ------------------------------------------------------- API territorial


def _territorial(username, provincia, *grupos_negocio):
    user = _user(username, *grupos_negocio)
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    return get_user_model().objects.get(pk=user.pk)


def _api(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def test_api_territorial_listado_y_zona_filtrados_por_programa(escenario):
    provincia, comedores = escenario
    user = _territorial("terr_pnud", provincia, PNUD)
    for clave in ("alimentar", "secos", "nulo"):
        Relevamiento.objects.create(
            comedor=comedores[clave],
            estado="Visita pendiente",
            territorial_user=user,
        )
    # Asignado desde SISOC: también queda filtrado por programa.
    SeguimientoPnud.objects.create(
        comedor=comedores["alimentar"],
        formulario=SeguimientoPnud.FORMULARIO_SECOS,
        tecnico=user,
        asignado_desde_sisoc=True,
    )
    api = _api(user)

    listado = api.get("/api/territorial/comedores/")
    zona = api.get("/api/territorial/comedores-zona/")

    assert listado.status_code == 200
    assert {row["id"] for row in listado.data["results"]} == _ids(comedores, "secos")
    assert zona.status_code == 200
    assert {row["id"] for row in zona.data["results"]} == _ids(
        comedores, "secos", "tradicional"
    )


def test_api_territorial_detalle_y_altas_filtrados_por_programa(escenario):
    provincia, comedores = escenario
    user = _territorial("terr_alim", provincia, ALIM)
    Relevamiento.objects.create(
        comedor=comedores["secos"], estado="Visita pendiente", territorial_user=user
    )
    api = _api(user)

    ok = api.get(f"/api/territorial/comedores/{comedores['alimentar'].id}/")
    asignado_otro_programa = api.get(
        f"/api/territorial/comedores/{comedores['secos'].id}/"
    )
    zona_otro_programa = api.get(
        f"/api/territorial/comedores/{comedores['tradicional'].id}/"
    )

    assert ok.status_code == 200
    assert asignado_otro_programa.status_code == 404
    assert zona_otro_programa.status_code == 404


def test_api_territorial_sin_restriccion_ve_todo_lo_de_su_zona(escenario):
    provincia, comedores = escenario
    user = _territorial("terr_libre", provincia)
    zona = _api(user).get("/api/territorial/comedores-zona/")
    assert {row["id"] for row in zona.data["results"]} == {
        comedor.id for comedor in comedores.values()
    }


# ------------------------------------------------------------- formulario


def _datos_alta(username, **extra):
    data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "pass12345",
        "tipo_usuario": "interno",
        "territorial_scopes": "[]",
    }
    data.update(extra)
    return data


def test_form_alta_guarda_programas_tildados():
    form = CompositeUserCreationForm(
        data=_datos_alta("alta_prog", programas_comedores=[PNUD])
    )
    assert form.is_valid(), form.errors
    user = form.save()
    assert set(
        user.profile.alcances_programa_comedor.values_list("programa", flat=True)
    ) == {PNUD}


def test_form_alta_sin_tildar_no_crea_restriccion():
    form = CompositeUserCreationForm(data=_datos_alta("alta_sin_prog"))
    assert form.is_valid(), form.errors
    user = form.save()
    assert not user.profile.alcances_programa_comedor.exists()


def test_form_edicion_tilda_y_destilda():
    user = _user("edit_prog")

    def _guardar(**extra):
        form = CompositeUserChangeForm(
            instance=user,
            data={
                "username": user.username,
                "email": "",
                "tipo_usuario": "interno",
                "territorial_scopes": "[]",
                **extra,
            },
        )
        assert form.is_valid(), form.errors
        form.save()
        return set(
            user.profile.alcances_programa_comedor.values_list("programa", flat=True)
        )

    assert _guardar(programas_comedores=[PNUD, ALIM]) == {PNUD, ALIM}
    assert _guardar(programas_comedores=[ALIM]) == {ALIM}
    assert alcance.programas_visibles(user) == {ALIM}
    assert _guardar() == set()
    assert alcance.programas_visibles(user) is None


def test_form_edicion_precarga_programas():
    user = _user("precarga_prog", ALIM)
    form = CompositeUserChangeForm(instance=user)
    assert form.fields["programas_comedores"].initial == [ALIM]
