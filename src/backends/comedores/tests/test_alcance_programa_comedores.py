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


# ------------------------------------- formulario: alcance del actor


def _datos_edicion(user, **extra):
    return {
        "username": user.username,
        "email": "",
        "tipo_usuario": "interno",
        "territorial_scopes": "[]",
        **extra,
    }


def _grupos(user):
    return set(
        user.profile.alcances_programa_comedor.values_list("programa", flat=True)
    )


def test_form_autoedicion_no_cambia_el_alcance_aunque_se_postee():
    user = _user("auto_prog", PNUD)
    form = CompositeUserChangeForm(
        instance=user,
        actor=user,
        data=_datos_edicion(user, programas_comedores=[ALIM]),
    )
    assert form.fields["programas_comedores"].disabled
    assert form.is_valid(), form.errors
    form.save()
    assert _grupos(user) == {PNUD}


def test_form_autoedicion_no_puede_quitarse_la_restriccion():
    user = _user("auto_prog2", PNUD)
    form = CompositeUserChangeForm(instance=user, actor=user, data=_datos_edicion(user))
    assert form.is_valid(), form.errors
    form.save()
    assert _grupos(user) == {PNUD}


def test_form_delegado_restringido_no_puede_dejar_vacio():
    actor = _user("deleg_pnud", PNUD)
    objetivo = _user("objetivo_1", PNUD)
    form = CompositeUserChangeForm(
        instance=objetivo, actor=actor, data=_datos_edicion(objetivo)
    )
    assert not form.is_valid()
    assert "programas_comedores" in form.errors


def test_form_delegado_restringido_no_puede_asignar_otro_programa():
    actor = _user("deleg_pnud2", PNUD)
    objetivo = _user("objetivo_2", PNUD)
    for elegidos in ([ALIM], [PNUD, ALIM]):
        form = CompositeUserChangeForm(
            instance=objetivo,
            actor=actor,
            data=_datos_edicion(objetivo, programas_comedores=elegidos),
        )
        assert not form.is_valid()
        assert "programas_comedores" in form.errors


def test_form_delegado_restringido_solo_ve_sus_opciones_y_puede_asignarlas():
    actor = _user("deleg_pnud3", PNUD)
    objetivo = _user("objetivo_3", PNUD)
    form = CompositeUserChangeForm(
        instance=objetivo,
        actor=actor,
        data=_datos_edicion(objetivo, programas_comedores=[PNUD]),
    )
    assert [c[0] for c in form.fields["programas_comedores"].choices] == [PNUD]
    assert form.is_valid(), form.errors
    form.save()
    assert _grupos(objetivo) == {PNUD}


@pytest.mark.parametrize("grupos_objetivo", [(), (ALIM,), (PNUD, ALIM)])
def test_form_delegado_restringido_no_toca_alcance_mayor_que_el_suyo(grupos_objetivo):
    actor = _user(f"deleg_mayor_{len(grupos_objetivo)}", PNUD)
    objetivo = _user(f"objetivo_mayor_{len(grupos_objetivo)}", *grupos_objetivo)
    form = CompositeUserChangeForm(
        instance=objetivo,
        actor=actor,
        data=_datos_edicion(objetivo, programas_comedores=[PNUD]),
    )
    assert form.fields["programas_comedores"].disabled
    assert form.is_valid(), form.errors
    form.save()
    assert _grupos(objetivo) == set(grupos_objetivo)


def test_form_delegado_sin_restriccion_asigna_cualquier_combinacion():
    actor = _user("deleg_libre")
    objetivo = _user("objetivo_4")

    def _guardar(**extra):
        form = CompositeUserChangeForm(
            instance=objetivo, actor=actor, data=_datos_edicion(objetivo, **extra)
        )
        assert form.is_valid(), form.errors
        form.save()
        return _grupos(objetivo)

    assert _guardar(programas_comedores=[ALIM]) == {ALIM}
    assert _guardar(programas_comedores=[PNUD, ALIM]) == {PNUD, ALIM}
    assert _guardar() == set()


def test_form_superuser_asigna_sin_limites_y_en_alta():
    actor = _user("su_form", PNUD, superuser=True)
    objetivo = _user("objetivo_5")
    form = CompositeUserChangeForm(
        instance=objetivo,
        actor=actor,
        data=_datos_edicion(objetivo, programas_comedores=[ALIM]),
    )
    assert form.is_valid(), form.errors
    form.save()
    assert _grupos(objetivo) == {ALIM}
    alta = CompositeUserCreationForm(
        actor=actor, data=_datos_alta("alta_su", programas_comedores=[ALIM])
    )
    assert alta.is_valid(), alta.errors


def test_form_alta_de_delegado_restringido_exige_su_programa():
    actor = _user("deleg_alta", ALIM)
    vacio = CompositeUserCreationForm(actor=actor, data=_datos_alta("alta_vacia"))
    assert not vacio.is_valid()
    assert "programas_comedores" in vacio.errors
    ok = CompositeUserCreationForm(
        actor=actor, data=_datos_alta("alta_ok", programas_comedores=[ALIM])
    )
    assert ok.is_valid(), ok.errors


# ------------------------------------------------------------ comunicados


def _usuario_comunicados(monkeypatch, username, *grupos):
    from comunicados import permissions as perms

    monkeypatch.setattr(perms, "tiene_alcance_total_destinatarios", lambda u: True)
    return _user(username, *grupos)


def test_comunicados_ids_y_form_acotados_por_programa(monkeypatch, escenario):
    from django.core.exceptions import ValidationError

    from comunicados.forms import ComunicadoForm
    from comunicados.permissions import get_ids_comedores_del_usuario

    _, comedores = escenario
    user = _usuario_comunicados(monkeypatch, "com_pnud", PNUD)
    ids = set(get_ids_comedores_del_usuario(user))
    assert _ids(comedores, "secos", "tradicional") <= ids
    assert not (_ids(comedores, "alimentar", "otro", "nulo") & ids)

    form = ComunicadoForm(user=user)
    queryset_ids = set(form.fields["comedores"].queryset.values_list("pk", flat=True))
    assert queryset_ids == ids
    # POST manual con un comedor de otro programa: no es una opcion valida.
    with pytest.raises(ValidationError):
        form.fields["comedores"].clean([comedores["alimentar"].pk])
    assert form.fields["comedores"].clean([comedores["secos"].pk])


def test_comunicados_sin_restriccion_ve_todos(monkeypatch, escenario):
    from comunicados.permissions import get_ids_comedores_del_usuario

    _, comedores = escenario
    user = _usuario_comunicados(monkeypatch, "com_libre")
    ids = set(get_ids_comedores_del_usuario(user))
    assert _ids(comedores, "alimentar", "secos", "otro", "nulo") <= ids


def test_comunicados_para_todos_solo_asigna_los_del_programa(monkeypatch, escenario):
    from types import SimpleNamespace

    from comunicados.models import Comunicado, SubtipoComunicado, TipoComunicado
    from comunicados.views import ComunicadoPersistMixin

    _, comedores = escenario
    user = _usuario_comunicados(monkeypatch, "com_todos", ALIM)
    comunicado = Comunicado.objects.create(
        titulo="T",
        cuerpo="C",
        tipo=TipoComunicado.EXTERNO,
        subtipo=SubtipoComunicado.COMEDORES,
        usuario_creador=user,
    )
    vista = ComunicadoPersistMixin()
    vista.request = SimpleNamespace(user=user)
    vista.object = comunicado
    vista._handle_comedores(
        SimpleNamespace(cleaned_data={"para_todos_comedores": True})
    )
    asignados = set(comunicado.comedores.values_list("pk", flat=True))
    assert comedores["alimentar"].pk in asignados
    assert not (_ids(comedores, "secos", "tradicional", "otro", "nulo") & asignados)


# -------------------------------------------------------------- admisiones


def _admisiones_escenario(escenario):
    from admisiones.models.admisiones import Admision
    from duplas.models import Dupla

    _, comedores = escenario
    tecnico = get_user_model().objects.create_user(username="tec_adm")
    abogado = get_user_model().objects.create_user(username="abo_adm")
    dupla = Dupla.objects.create(nombre="Dupla Adm", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    for comedor in comedores.values():
        comedor.dupla = dupla
        comedor.save()
    admisiones = {
        clave: Admision.objects.create(comedor=comedor)
        for clave, comedor in comedores.items()
    }
    return tecnico, comedores, admisiones


def test_admisiones_queryset_y_chequeo_acotados_por_programa(escenario):
    from admisiones.models.admisiones import Admision
    from admisiones.services.admisiones_service import AdmisionService

    tecnico, comedores, admisiones = _admisiones_escenario(escenario)
    AlcanceProgramaComedor.objects.create(profile=tecnico.profile, programa=PNUD)
    tecnico = get_user_model().objects.get(pk=tecnico.pk)

    ids = set(
        AdmisionService.get_admisiones_tecnicos_queryset(tecnico).values_list(
            "pk", flat=True
        )
    )
    assert ids == {admisiones["secos"].pk, admisiones["tradicional"].pk}
    assert not AdmisionService._verificar_permiso_dupla(tecnico, comedores["alimentar"])
    assert AdmisionService._verificar_permiso_dupla(tecnico, comedores["secos"])
    assert not AdmisionService.acotar_admisiones_por_programa(
        Admision.objects.filter(pk=admisiones["alimentar"].pk), tecnico
    ).exists()


def test_admisiones_tecnico_sin_restriccion_ve_todas(escenario):
    from admisiones.services.admisiones_service import AdmisionService

    tecnico, _comedores, admisiones = _admisiones_escenario(escenario)
    ids = set(
        AdmisionService.get_admisiones_tecnicos_queryset(tecnico).values_list(
            "pk", flat=True
        )
    )
    assert ids == {a.pk for a in admisiones.values()}


# ------------------------------------------- alta/edición con programa (API)


def _payload_alta(provincia, **extra):
    from comedores.models import TipoDeComedor

    TipoDeComedor.objects.get_or_create(nombre="Comedor")
    data = {
        "client_uuid": f"uuid-{extra.pop('uuid', 'a')}",
        "nombre": "Comedor nuevo",
        "tipo": "Comedor",
        "provincia": provincia.nombre,
    }
    data.update(extra)
    return data


def test_alta_pnud_sin_programa_exige_elegir(escenario):
    provincia, _ = escenario
    api = _api(_territorial("alta_pnud_sin", provincia, PNUD))
    response = api.post(
        "/api/territorial/comedores/", _payload_alta(provincia), format="json"
    )
    assert response.status_code == 400
    assert response.json()["programa"] == ["Seleccione el programa del comedor."] or (
        "Seleccione el programa del comedor." in str(response.json()["programa"])
    )


def test_alta_pnud_con_linea_tradicional_queda_visible(escenario):
    provincia, _ = escenario
    user = _territorial("alta_pnud_ok", provincia, PNUD)
    response = _api(user).post(
        "/api/territorial/comedores/",
        _payload_alta(provincia, programa=TRADICIONAL),
        format="json",
    )
    assert response.status_code == 201
    comedor = Comedor.objects.get(pk=response.json()["id"])
    assert comedor.programa.nombre == TRADICIONAL
    assert alcance.comedor_en_alcance_programa(user, comedor)


def test_alta_pnud_con_alimentar_fuera_de_alcance(escenario):
    provincia, _ = escenario
    response = _api(_territorial("alta_pnud_alim", provincia, PNUD)).post(
        "/api/territorial/comedores/",
        _payload_alta(provincia, programa=ALIMENTAR),
        format="json",
    )
    assert response.status_code == 400
    assert "El programa no está dentro de su alcance." in str(
        response.json()["programa"]
    )


def test_alta_alimentar_sin_programa_asigna_alimentar(escenario):
    provincia, _ = escenario
    response = _api(_territorial("alta_alim", provincia, ALIM)).post(
        "/api/territorial/comedores/", _payload_alta(provincia), format="json"
    )
    assert response.status_code == 201
    assert Comedor.objects.get(pk=response.json()["id"]).programa.nombre == ALIMENTAR


def test_alta_sin_restriccion_sin_programa_queda_nulo(escenario):
    provincia, _ = escenario
    response = _api(_territorial("alta_libre", provincia)).post(
        "/api/territorial/comedores/", _payload_alta(provincia), format="json"
    )
    assert response.status_code == 201
    assert Comedor.objects.get(pk=response.json()["id"]).programa is None


def test_alta_replay_idempotente_con_programa_asignado(escenario):
    provincia, _ = escenario
    api = _api(_territorial("alta_replay", provincia, ALIM))
    payload = _payload_alta(provincia)
    primero = api.post("/api/territorial/comedores/", payload, format="json")
    segundo = api.post("/api/territorial/comedores/", payload, format="json")
    assert primero.status_code == 201
    assert segundo.status_code == 200
    assert segundo.json()["id"] == primero.json()["id"]


def test_patch_programa_fuera_de_alcance_rechazado(escenario):
    provincia, comedores = escenario
    user = _territorial("patch_pnud", provincia, PNUD)
    comedor = comedores["secos"]
    from relevamientos.models import Relevamiento as Rel

    Rel.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=user
    )
    api = _api(user)
    url = f"/api/territorial/comedores/{comedor.id}/"
    fuera = api.patch(url, {"programa": ALIMENTAR}, format="json")
    assert fuera.status_code == 400
    assert "El programa no está dentro de su alcance." in str(fuera.json()["programa"])
    dentro = api.patch(url, {"programa": TRADICIONAL}, format="json")
    assert dentro.status_code == 200
