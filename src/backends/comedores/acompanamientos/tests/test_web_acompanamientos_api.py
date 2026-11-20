"""Web API (G1 v1) of the acompañamiento follow-up and milestones (AC01).

``/api/web/comedores/acompanamientos/`` runs the native views of
``acompanamientos.views``; restoring a milestone repeats ``restaurar_hito`` with
an explicit ``admision_id`` and a whitelist of the 23 boolean milestones.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from acompanamientos.models.acompanamiento import Acompanamiento
from acompanamientos.models.hitos import Hitos
from admisiones.models.admisiones import Admision, InformeTecnico
from comedores.models import Comedor
from core import web_gate
from users.services import UserPermissionService

ROOT = "/api/web/comedores/acompanamientos/"
NATIVO = "/acompanamientos/acompanamiento/"
HITOS = [
    "retiro_tarjeta",
    "habilitacion_tarjeta",
    "alta_usuario_plataforma",
    "capacitacion_realizada",
    "capacitacion_fch_realizada",
    *(f"notificacion_acreditacion_{n}" for n in range(1, 7)),
    "nomina_entregada_inicial",
    *(f"nomina_alta_baja_{n}" for n in range(2, 7)),
    *(f"certificado_prestaciones_{n}" for n in range(1, 7)),
]

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _sin_alcance_de_duplas(monkeypatch):
    """The technician is in no dupla: scope as a user with the permission only."""
    monkeypatch.setattr(
        UserPermissionService,
        "es_tecnico_o_abogado",
        staticmethod(lambda _user: False),
    )
    monkeypatch.setattr(
        UserPermissionService,
        "get_coordinador_duplas",
        staticmethod(lambda _user: (False, [])),
    )


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _perm(code):
    app, codename = code.split(".")
    if app == "auth":
        # ``auth.role_*`` codes live on the Group content type (seeded by bootstrap).
        return Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": codename},
        )[0]
    return Permission.objects.get(content_type__app_label=app, codename=codename)


def _usuario(nombre, *codes):
    usuario = _ready(get_user_model().objects.create_user(nombre))
    usuario.user_permissions.add(*(_perm(code) for code in codes))
    return usuario


@pytest.fixture(name="tecnico")
def tecnico_fixture():
    return _usuario(
        "tecnico_acomp",
        "acompanamientos.view_informacionrelevante",
        "acompanamientos.change_hitos",
        "auth.role_tecnico_comedor",
    )


@pytest.fixture(name="web")
def web_fixture(tecnico):
    client = Client()
    client.force_login(tecnico)
    return client


def _acompanamiento(comedor, nro="", activa=True, **hitos):
    admision = Admision.objects.create(
        comedor=comedor,
        activa=activa,
        enviado_acompaniamiento=True,
        estado_admision="iniciada",
        num_expediente="EXP-1",
    )
    acompanamiento = Acompanamiento.objects.create(admision=admision, nro_convenio=nro)
    Hitos.objects.create(acompanamiento=acompanamiento, **hitos)
    return admision


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Sintético", codigo_de_proyecto="")


def _hito(admision):
    return Hitos.objects.get(acompanamiento__admision=admision)


# --- List ----------------------------------------------------------------------


def test_list_projects_the_native_page(web, comedor):
    admision = _acompanamiento(comedor)
    Comedor.objects.create(nombre="Sin acompañamiento")

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    fila = data["results"][0]
    assert len(data["results"]) == 1
    assert [c["content"] for c in fila["cells"]] == [
        str(comedor.pk),
        "Comedor Sintético",
        "-",
        "EXP-1",
        "-",
        "-",
        "Iniciada",
        admision.modificado.strftime("%d/%m/%Y"),
    ]
    assert fila["cells"][1]["data_attr"] == "nombre"
    assert fila["actions"] == [
        {
            "label": "Ver Acompañamiento",
            "url": f"{NATIVO}{comedor.pk}/detalle/?admision_id={admision.pk}",
            "type": "primary",
        }
    ]
    assert [h["title"] for h in data["headers"]] == [
        "ID",
        "Nombre",
        "Organización",
        "N° Expediente",
        "Provincia",
        "Dupla",
        "Estado",
        "Última Modificación",
    ]
    assert data["headers"][1] == {
        "title": "Nombre",
        "sort_url": "?ordering=nombre",
        "sort_direction": None,
    }
    assert data["urls"] == {
        "list": NATIVO,
        "reset": NATIVO,
        "export": f"{NATIVO}exportar/",
    }
    assert data["can_export"] is False
    assert data["favorites"]["section"] == "acompanamientos"
    assert data["page"]["has_rows"] is True


def test_list_keeps_the_native_order_search_and_pages(web):
    for numero in range(11):
        _acompanamiento(Comedor.objects.create(nombre=f"Comedor {numero:02d}"))

    data = web.get(ROOT, {"ordering": "-nombre", "busqueda": "comedor"}).json()

    assert [r["cells"][1]["content"] for r in data["results"]][:2] == [
        "Comedor 10",
        "Comedor 09",
    ]
    assert data["headers"][1]["sort_direction"] == "desc"
    assert data["headers"][1]["sort_url"] == "?ordering=nombre&busqueda=comedor"
    assert data["page"]["query_without_page"] == ("busqueda=comedor&ordering=-nombre&")
    segunda = web.get(ROOT, {"ordering": "-nombre", "page": "2"}).json()
    assert [r["cells"][1]["content"] for r in segunda["results"]] == ["Comedor 00"]
    assert web.get(ROOT, {"page": "7"}).status_code == 404
    assert web.get(NATIVO, {"page": "7"}).status_code == 404


# --- Detail --------------------------------------------------------------------


def test_detail_resolves_the_agreement_like_the_native_view(web, comedor):
    cerrada = _acompanamiento(comedor, nro="CONV-1", activa=False, retiro_tarjeta=True)
    activa = _acompanamiento(comedor, nro="", habilitacion_tarjeta=True)

    data = web.get(f"{ROOT}{comedor.pk}/").json()

    assert data["admision_id"] == activa.pk
    assert data["convenios"] == [
        {
            "id": activa.pk,
            "label": f"Admisión #{activa.pk}",
            "activa": True,
            "seleccionada": True,
        },
        {"id": cerrada.pk, "label": "CONV-1", "activa": False, "seleccionada": False},
    ]
    assert data["multiples_activos"] is False
    assert [h["campo"] for h in data["hitos"]] == HITOS
    assert data["hitos"][1] == {
        "campo": "habilitacion_tarjeta",
        "descripcion": "Habilitación de Tarjeta",
        "completado": True,
        "fecha": "—",
    }
    assert data["hitos"][0]["completado"] is False
    assert data["puede_restaurar"] is True
    assert data["informacion"] is None
    assert data["prestaciones"] == {"dias": [], "por_dia": [], "semanal": []}
    assert data["urls"]["intervenciones"].endswith(f"?admision_id={activa.pk}")
    assert data["urls"]["informe_complementario"] is None

    otra = web.get(f"{ROOT}{comedor.pk}/", {"admision_id": cerrada.pk}).json()
    assert otra["admision_id"] == cerrada.pk
    assert otra["hitos"][0]["completado"] is True
    ajeno = _acompanamiento(Comedor.objects.create(nombre="Otro"))
    no_numerico = web.get(f"{ROOT}{comedor.pk}/", {"admision_id": "x"}).json()
    assert no_numerico["admision_id"] == activa.pk
    de_otro = web.get(f"{ROOT}{comedor.pk}/", {"admision_id": ajeno.pk}).json()
    assert de_otro["admision_id"] is None
    assert de_otro["hitos"] is None


def test_detail_shows_the_finalized_report_data(web, comedor):
    admision = _acompanamiento(comedor, nro="CONV-9")
    InformeTecnico.objects.create(
        admision=admision,
        tipo="base",
        estado_formulario="finalizado",
        expediente_nro="EX-2026-1",
        if_relevamiento="",
        aprobadas_desayuno_lunes=10,
    )

    data = web.get(f"{ROOT}{comedor.pk}/").json()

    assert data["informacion"] == {
        "nro_convenio": "CONV-9",
        "expediente": "EX-2026-1",
        "disposicion": "-",
        "if_relevamiento": "-",
        # Native quirk: ``None|date`` is "" so ``default_if_none`` never applies.
        "vencimiento": "",
        "codigo_proyecto": "-",
    }
    assert data["prestaciones"]["dias"][0] == "Lunes"
    assert data["prestaciones"]["por_dia"][0]["tipo"] == "DESAYUNO"
    assert data["prestaciones"]["por_dia"][0]["valores"][0] == "10"
    assert data["prestaciones"]["semanal"][0] == {"tipo": "DESAYUNO", "cantidad": "10"}
    assert data["urls"]["informe_complementario"].endswith("?origen=acompanamiento")


def test_reader_without_the_technician_role_cannot_restore(client, comedor):
    _acompanamiento(comedor)
    client.force_login(
        _usuario("lector_acomp", "acompanamientos.view_informacionrelevante")
    )

    assert client.get(f"{ROOT}{comedor.pk}/").json()["puede_restaurar"] is False


def test_detail_outside_scope_is_404(web, tecnico, comedor, monkeypatch):
    _acompanamiento(comedor)
    from comedores.services.comedor_service import (  # pylint: disable=import-outside-toplevel
        ComedorService,
    )

    monkeypatch.setattr(
        ComedorService,
        "get_scoped_comedor_queryset",
        staticmethod(lambda _user: Comedor.objects.none()),
    )

    assert web.get(f"{ROOT}{comedor.pk}/").status_code == 404
    assert web.get(f"{NATIVO}{comedor.pk}/detalle/").status_code == 404
    respuesta = web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/", {"campo": "retiro_tarjeta"}
    )
    assert respuesta.status_code == 404


# --- Restore a milestone -------------------------------------------------------


def test_restore_sets_false_for_the_explicit_agreement_only(web, comedor):
    vieja = _acompanamiento(comedor, activa=False, retiro_tarjeta=True)
    actual = _acompanamiento(comedor, retiro_tarjeta=True)

    respuesta = web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/",
        {"campo": "retiro_tarjeta", "admision_id": vieja.pk},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": {
            "level": "success",
            "text": "El campo 'retiro_tarjeta' ha sido restaurado correctamente.",
        },
        "redirect": f"{NATIVO}{comedor.pk}/detalle/?admision_id={vieja.pk}",
    }
    assert _hito(vieja).retiro_tarjeta is False
    assert _hito(actual).retiro_tarjeta is True
    siguiente = web.get(f"{ROOT}{comedor.pk}/", {"admision_id": vieja.pk}).json()
    assert siguiente["messages"] == [
        {
            "message": "El campo 'retiro_tarjeta' ha sido restaurado correctamente.",
            "level": "success",
        }
    ]
    repetido = web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/",
        {"campo": "retiro_tarjeta", "admision_id": vieja.pk},
    )
    assert repetido.status_code == 200


@pytest.mark.parametrize(
    "campo", ["pk", "id", "acompanamiento_id", "fecha", "", "save"]
)
def test_restore_rejects_fields_outside_the_milestones(web, comedor, campo):
    admision = _acompanamiento(comedor, retiro_tarjeta=True)
    antes = Hitos.objects.values().get(acompanamiento__admision=admision)

    respuesta = web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/",
        {"campo": campo, "admision_id": admision.pk},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["message"] == {
        "level": "error",
        "text": f"El campo '{campo}' no existe en el modelo Hitos.",
    }
    assert Hitos.objects.values().get(acompanamiento__admision=admision) == antes


def test_restore_without_milestones_is_409(web, comedor):
    respuesta = web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/", {"campo": "retiro_tarjeta"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["message"]["text"] == (
        "No se encontraron hitos para el convenio seleccionado."
    )


def test_restore_requires_both_native_permissions(client, comedor):
    admision = _acompanamiento(comedor, retiro_tarjeta=True)
    for codes in (
        ("acompanamientos.view_informacionrelevante", "auth.role_tecnico_comedor"),
        ("acompanamientos.view_informacionrelevante", "acompanamientos.change_hitos"),
    ):
        client.force_login(_usuario("_".join(c[-6:] for c in codes), *codes))
        respuesta = client.post(
            f"{ROOT}{comedor.pk}/hitos/restaurar/",
            {"campo": "retiro_tarjeta", "admision_id": admision.pk},
        )
        assert respuesta.status_code == 403
    assert _hito(admision).retiro_tarjeta is True


def test_api_and_native_restore_leave_the_same_state(web, comedor):
    api = _acompanamiento(comedor, nomina_entregada_inicial=True)
    nativo_comedor = Comedor.objects.create(nombre="Nativo")
    nativo = _acompanamiento(nativo_comedor, nomina_entregada_inicial=True)

    web.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/",
        {"campo": "nomina_entregada_inicial", "admision_id": api.pk},
    )
    web.post(
        f"/acompanamientos/comedor/{nativo_comedor.pk}/restaurar-hito/",
        {"campo": "nomina_entregada_inicial", "admision_id": nativo.pk},
    )

    campos = lambda a: {c: getattr(_hito(a), c) for c in HITOS}  # noqa: E731
    assert campos(api) == campos(nativo)


def test_restore_requires_the_csrf_token(tecnico, comedor):
    admision = _acompanamiento(comedor, retiro_tarjeta=True)
    client = Client(enforce_csrf_checks=True)
    client.force_login(tecnico)

    respuesta = client.post(
        f"{ROOT}{comedor.pk}/hitos/restaurar/",
        {"campo": "retiro_tarjeta", "admision_id": admision.pk},
    )

    assert respuesta.status_code == 403
    assert _hito(admision).retiro_tarjeta is True


# --- Access --------------------------------------------------------------------


def test_anonymous_gets_401_and_without_permission_403(client, comedor):
    _acompanamiento(comedor)
    for url in (ROOT, f"{ROOT}{comedor.pk}/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    client.force_login(_usuario("sin_permiso_acomp", "comedores.view_comedor"))
    for url in (ROOT, f"{ROOT}{comedor.pk}/"):
        assert client.get(url).status_code == 403, url
    assert client.get(NATIVO).status_code == 403


def test_read_endpoints_only_answer_get_and_restore_only_post(web, comedor):
    _acompanamiento(comedor)
    for url in (ROOT, f"{ROOT}{comedor.pk}/"):
        for metodo in ("post", "put", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)
    assert web.get(f"{ROOT}{comedor.pk}/hitos/restaurar/").status_code == 405


def test_admindocs_head_does_not_bypass_the_web_api(client, comedor):
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_acomp", is_staff=True))
    )

    for url in (ROOT, f"{ROOT}{comedor.pk}/"):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET"):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_reads_and_writes_only(web, tecnico, comedor):
    admision = _acompanamiento(comedor, retiro_tarjeta=True)
    assert (
        web.get(
            ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=ROOT)
        ).status_code
        == 200
    )
    target = f"{ROOT}{comedor.pk}/hitos/restaurar/"
    datos = {"campo": "retiro_tarjeta", "admision_id": admision.pk}

    sin_firma = web.post(target, datos, RAW_URI=target)
    firmado_get = web.post(
        target,
        datos,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=target),
    )
    assert sin_firma.status_code == firmado_get.status_code == 403
    assert _hito(admision).retiro_tarjeta is True
    firmado = web.post(
        target,
        datos,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(tecnico, web, target=target, method="POST"),
    )
    assert firmado.status_code == 200
    assert _hito(admision).retiro_tarjeta is False
