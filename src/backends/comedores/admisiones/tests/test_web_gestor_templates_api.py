"""Web API (G1 v1) of the template manager queries (AD01.01).

``/api/web/comedores/admisiones/plantillas-informe/`` runs the native views of
``views.templates_informe_tecnico``. The monolith tests go through
``config.settings_all`` (policy evaluated locally); the runtime tests switch to
``SISOC_BACKEND="comedores"`` with the real runtime URLconf, where only a request
the core signed reaches the view.
"""

from datetime import datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.utils import timezone

from admisiones.models.admisiones import (
    IncidenciaTemplateInformeTecnico,
    IncidenciaTemplateInformeTecnicoCaso,
    PlantillaInformeTecnico,
    PlantillaInformeTecnicoVersion,
    TipoConvenio,
    VariableTemplateInformeTecnico,
)
from admisiones.services.templates_informe_tecnico_service import (
    PlantillaInformeTecnicoService,
)
from core import web_gate

ROOT = "/api/web/comedores/admisiones/plantillas-informe/"
NATIVO = "/comedores/configuracion/templates/"
CODE = "gestionar_templates_informe_tecnico"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor")
def gestor_fixture():
    usuario = _ready(get_user_model().objects.create_user("gestor_templates_web"))
    usuario.user_permissions.add(
        Permission.objects.get(content_type__app_label="admisiones", codename=CODE)
    )
    return usuario


@pytest.fixture(name="web")
def web_fixture(gestor):
    client = Client()
    client.force_login(gestor)
    return client


@pytest.fixture(name="convenio")
def convenio_fixture():
    return TipoConvenio.objects.create(nombre="Organización Base")


def _incorporacion(convenio, nombre="Incorporación Ex PNUD", **extra):
    datos = {
        "nombre": nombre,
        "descripcion": "",
        "tipo_admision": "incorporacion",
        "tipo_convenio": convenio,
        "es_ex_pnud": "si",
        "estado_convenio_pnud": "vigente",
        "tipo_renovacion": None,
        "estado_financiamiento": None,
        **extra,
    }
    return PlantillaInformeTecnicoService.crear_plantilla(datos, None)


def _publicada(convenio, gestor, **extra):
    plantilla, version = _incorporacion(convenio, **extra)
    version.contenido_html = "<p>Contenido</p>"
    version.save()
    assert PlantillaInformeTecnicoService.publicar_version(version, gestor)[0]
    return plantilla, version


# --- Templates list ------------------------------------------------------------


def test_list_projects_the_native_page_and_defaults_to_active(web, gestor, convenio):
    publicada, _ = _publicada(
        convenio, gestor, descripcion="D" * 90, nombre="Con versión"
    )
    inactiva, _ = _incorporacion(
        convenio, nombre="Inactiva", es_ex_pnud="no", estado_convenio_pnud=None
    )
    PlantillaInformeTecnico.objects.filter(pk=inactiva.pk).update(estado="inactiva")
    renovacion = PlantillaInformeTecnico.objects.create(
        nombre="Renovación",
        tipo_admision="renovacion",
        tipo_convenio=convenio,
        tipo_renovacion="primera",
        estado_financiamiento="finalizado",
        informe_complementario_modifica_prestaciones="no",
    )

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["estado_filtro"] == "activa"
    assert [fila["id"] for fila in data["results"]] == [publicada.pk, renovacion.pk]
    assert data["results"][0] == {
        "id": publicada.pk,
        "codigo": publicada.codigo,
        "nombre": "Con versión",
        "descripcion": "D" * 84 + "…",
        "combinacion": "Incorporación · Organización Base · Ex PNUD: Sí · PNUD: Vigente",
        "version_vigente": 1,
        "estado": "activa",
        "estado_display": "Activa",
        "url": f"{NATIVO}{publicada.pk}/",
    }
    assert data["results"][1]["combinacion"] == (
        "Renovación · Organización Base · Primera renovación · "
        "Financiamiento finalizado · "
        "Informe complementario: No"
    )
    assert data["results"][1]["version_vigente"] is None
    assert data["urls"] == {
        "templates": NATIVO,
        "variables": f"{NATIVO}variables/",
        "incidencias": f"{NATIVO}incidencias/",
        "crear": f"{NATIVO}crear/",
    }
    assert data["opciones"]["tipos_convenio"] == [
        {"value": str(convenio.pk), "label": "Organización Base"}
    ]
    nativo = web.get(NATIVO).context["plantillas"]
    assert [p.pk for p in nativo] == [fila["id"] for fila in data["results"]]
    todas = web.get(ROOT, {"estado": "todas"}).json()
    assert {fila["id"] for fila in todas["results"]} == {
        publicada.pk,
        inactiva.pk,
        renovacion.pk,
    }
    assert todas["results"][1]["combinacion"].endswith("Ex PNUD: No")


def test_list_filters_like_the_native_view_and_ignores_invalid_values(
    web, gestor, convenio
):
    plantilla, _ = _incorporacion(convenio, nombre="Buscada")
    _incorporacion(convenio, nombre="Otra", es_ex_pnud="no", estado_convenio_pnud=None)

    assert [
        fila["id"]
        for fila in web.get(ROOT, {"q": "busc", "es_ex_pnud": "si"}).json()["results"]
    ] == [plantilla.pk]
    ignorados = web.get(ROOT, {"tipo_convenio": "abc", "tipo_admision": "x"}).json()
    assert len(ignorados["results"]) == 2
    assert ignorados["filtros"]["tipo_convenio"] == "abc"
    assert web.get(ROOT, {"estado": "eliminada"}).json()["results"] == []


def test_list_pages_of_fifty_and_an_invalid_page_is_404(web, convenio):
    for numero in range(51):
        PlantillaInformeTecnico.objects.create(
            nombre=f"P{numero}",
            tipo_admision="renovacion",
            tipo_convenio=convenio,
            tipo_renovacion="primera",
            estado_financiamiento="finalizado",
        )

    data = web.get(ROOT, {"q": "P", "page": "2"}).json()

    assert len(data["results"]) == 1
    assert data["page"] == {
        "is_paginated": True,
        "number": 2,
        "count": 51,
        "has_rows": True,
        "previous": 1,
        "next": None,
        "range": [1, 2],
        "query_without_page": "q=P&",
    }
    assert web.get(ROOT, {"page": "9"}).status_code == 404
    assert web.get(NATIVO, {"page": "9"}).status_code == 404


def test_empty_list_has_no_rows_nor_count(web):
    data = web.get(ROOT).json()

    assert data["results"] == []
    assert data["page"]["has_rows"] is False


# --- Template detail -----------------------------------------------------------


def test_detail_has_the_working_version_and_the_history(web, gestor, convenio):
    plantilla, version = _publicada(convenio, gestor)
    borrador, _ = PlantillaInformeTecnicoService.crear_version_borrador(
        plantilla, gestor
    )
    momento = timezone.make_aware(datetime(2026, 11, 9, 12, 30))
    PlantillaInformeTecnicoVersion.objects.filter(pk=version.pk).update(
        creado=momento, publicado=momento
    )
    PlantillaInformeTecnicoVersion.objects.filter(pk=borrador.pk).update(
        modificado=momento
    )

    respuesta = web.get(f"{ROOT}{plantilla.pk}/")

    assert respuesta.status_code == 200
    data = respuesta.json()
    hora = timezone.localtime(momento).strftime("%d/%m/%Y %H:%M")
    assert data["condiciones"] == [
        {"term": "Tipo de admisión", "value": "Incorporación"},
        {"term": "Tipo de convenio", "value": "Organización Base"},
        {"term": "Ex PNUD", "value": "Sí"},
        {"term": "Convenio PNUD", "value": "Vigente"},
    ]
    base = f"{NATIVO}{plantilla.pk}/versiones/{borrador.pk}/"
    assert data["borrador"] == {
        "id": borrador.pk,
        "numero": 2,
        "modificado": hora,
        "urls": {
            "editar": f"{base}editar/",
            "publicar": f"{base}publicar/",
            "descartar": f"{base}descartar/",
        },
    }
    assert data["historial"] == [
        {
            "id": version.pk,
            "numero": 1,
            "estado": "publicada",
            "estado_display": "Publicada",
            "creado": hora,
            "publicado": hora,
        }
    ]
    assert data["urls"]["version_crear"] == f"{NATIVO}{plantilla.pk}/versiones/crear/"
    assert data["urls"]["inactivar"] == f"{NATIVO}{plantilla.pk}/inactivar/"
    assert data["estado"] == "activa"


def test_detail_of_a_renewal_without_draft_and_a_missing_one(web, convenio):
    plantilla = PlantillaInformeTecnico.objects.create(
        nombre="Renovación",
        tipo_admision="renovacion",
        tipo_convenio=convenio,
        tipo_renovacion="primera",
        estado_financiamiento="finalizado",
        informe_complementario_modifica_prestaciones="si",
        estado="inactiva",
    )

    data = web.get(f"{ROOT}{plantilla.pk}/").json()

    assert data["borrador"] is None
    assert data["historial"] == []
    assert data["condiciones"][2:] == [
        {"term": "Renovación", "value": "Primera renovación"},
        {"term": "Financiamiento", "value": "Financiamiento finalizado · Sí"},
    ]
    assert web.get(f"{ROOT}999999/").status_code == 404


def test_a_native_action_message_is_shown_by_the_next_api_page(web, gestor, convenio):
    plantilla, _ = _publicada(convenio, gestor)

    respuesta = web.post(f"{NATIVO}{plantilla.pk}/inactivar/")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == f"{NATIVO}{plantilla.pk}/"
    data = web.get(f"{ROOT}{plantilla.pk}/").json()
    assert data["messages"] == [
        {"message": "Plantilla inactivada correctamente.", "level": "success"}
    ]
    assert data["estado"] == "inactiva"
    assert web.get(f"{ROOT}{plantilla.pk}/").json()["messages"] == []


# --- Variables -----------------------------------------------------------------


def test_variables_default_to_active_and_keep_the_native_order(web):
    segunda = VariableTemplateInformeTecnico.objects.create(
        codigo="informe.b", nombre="B", categoria="Informe", orden=2
    )
    primera = VariableTemplateInformeTecnico.objects.create(
        codigo="informe.a", nombre="A", categoria="Informe", orden=1, descripcion="D"
    )
    inactiva = VariableTemplateInformeTecnico.objects.create(
        codigo="admision.c", nombre="C", categoria="Admisión", activo=False
    )

    data = web.get(f"{ROOT}variables/").json()

    assert data["estado_filtro"] == "activas"
    assert [fila["id"] for fila in data["results"]] == [primera.pk, segunda.pk]
    assert data["results"][0] == {
        "id": primera.pk,
        "categoria": "Informe",
        "nombre": "A",
        "descripcion": "D",
        "token": "{{ informe.a }}",
        "activo": True,
        "alternar_url": f"{NATIVO}variables/{primera.pk}/alternar/",
    }
    todas = web.get(f"{ROOT}variables/", {"estado": "todas"}).json()["results"]
    assert [fila["id"] for fila in todas] == [inactiva.pk, primera.pk, segunda.pk]
    buscadas = web.get(f"{ROOT}variables/", {"estado": "inactivas", "q": "admis"})
    assert [fila["id"] for fila in buscadas.json()["results"]] == [inactiva.pk]


def test_toggling_through_the_native_form_reports_its_message(web):
    variable = VariableTemplateInformeTecnico.objects.create(
        codigo="informe.a", nombre="A", categoria="Informe"
    )

    respuesta = web.post(
        f"{NATIVO}variables/{variable.pk}/alternar/",
        {"next": f"{NATIVO}variables/?estado=todas"},
    )

    assert respuesta["Location"] == f"{NATIVO}variables/?estado=todas"
    data = web.get(f"{ROOT}variables/", {"estado": "todas"}).json()
    assert data["messages"] == [
        {"message": "Variable inactivada correctamente.", "level": "success"}
    ]
    assert data["results"][0]["activo"] is False


# --- Incidents -----------------------------------------------------------------


def _incidencia(**extra):
    datos = {
        "clave_condiciones": "incorporacion|convenio:1|ex_pnud:si|estado_pnud:-",
        "condiciones": {
            "tipo_admision": {"valor": "incorporacion", "descripcion": "Incorporación"},
            "estado_pnud": {"valor": None, "descripcion": ""},
        },
        "cantidad_casos": 1,
        **extra,
    }
    return IncidenciaTemplateInformeTecnico.objects.create(**datos)


def test_incidents_default_to_pending(web):
    pendiente = _incidencia()
    _incidencia(estado="resuelta", clave_condiciones="otra")

    data = web.get(f"{ROOT}incidencias/").json()

    assert data["estado_filtro"] == "pendiente"
    assert data["estados"][0] == {"value": "pendiente", "label": "Pendiente"}
    assert data["results"] == [
        {
            "id": pendiente.pk,
            "codigo": f"INC-IT-{pendiente.pk:06d}",
            "clave_condiciones": pendiente.clave_condiciones,
            "cantidad_casos": 1,
            "ultima_fecha": timezone.localtime(
                IncidenciaTemplateInformeTecnico.objects.get(
                    pk=pendiente.pk
                ).ultima_fecha
            ).strftime("%d/%m/%Y %H:%M"),
            "estado": "pendiente",
            "estado_display": "Pendiente",
            "url": f"{NATIVO}incidencias/{pendiente.pk}/",
        }
    ]
    assert (
        len(web.get(f"{ROOT}incidencias/", {"estado": "todas"}).json()["results"]) == 2
    )
    assert web.get(f"{ROOT}incidencias/", {"page": "4"}).status_code == 404


def test_incident_detail_has_the_cases_and_the_native_form(web, gestor, convenio):
    anterior = _incidencia(estado="resuelta", clave_condiciones="vieja")
    incidencia = _incidencia(incidencia_anterior=anterior, observaciones="Nota")
    activa, _ = _incorporacion(convenio, nombre="Activa")
    inactiva, _ = _incorporacion(
        convenio, nombre="Inactiva", es_ex_pnud="no", estado_convenio_pnud=None
    )
    PlantillaInformeTecnico.objects.filter(pk=inactiva.pk).update(estado="inactiva")
    caso = IncidenciaTemplateInformeTecnicoCaso.objects.create(
        incidencia=incidencia,
        referencia_caso="admision:7",
        admision_id_reportada=7,
        comedor_nombre="Comedor sintético",
        reportado_por=gestor,
    )

    data = web.get(f"{ROOT}incidencias/{incidencia.pk}/").json()

    assert data["incidencia_anterior"] == anterior.codigo
    assert data["condiciones"] == [
        {"clave": "Tipo_Admision", "descripcion": "Incorporación"},
        {"clave": "Estado_Pnud", "descripcion": "-"},
    ]
    assert data["casos"] == [
        {
            "id": caso.pk,
            "admision": "7",
            "informe": "-",
            "comedor": "Comedor sintético",
            "organizacion": "-",
            "reportado_por": "gestor_templates_web",
            "creado": timezone.localtime(
                IncidenciaTemplateInformeTecnicoCaso.objects.get(pk=caso.pk).creado
            ).strftime("%d/%m/%Y %H:%M"),
        }
    ]
    estado, plantilla, observaciones = data["form"]
    assert estado["value"] == "pendiente" and estado["required"] is True
    assert [c["value"] for c in estado["choices"]] == [
        "pendiente",
        "en_analisis",
        "resuelta",
        "descartada",
    ]
    assert plantilla["required"] is False
    assert plantilla["choices"] == [
        {"value": "", "label": "---------"},
        {"value": str(activa.pk), "label": str(activa)},
    ]
    assert observaciones == {
        "name": "observaciones",
        "label": "Observaciones",
        "required": False,
        "value": "Nota",
    }
    assert data["urls"]["gestionar"] == f"{NATIVO}incidencias/{incidencia.pk}/"
    assert web.get(f"{ROOT}incidencias/999999/").status_code == 404


# --- Access, same rule as the native routes ------------------------------------


def _urls(convenio):
    plantilla, _ = _incorporacion(convenio)
    incidencia = _incidencia()
    return [
        ROOT,
        f"{ROOT}{plantilla.pk}/",
        f"{ROOT}variables/",
        f"{ROOT}incidencias/",
        f"{ROOT}incidencias/{incidencia.pk}/",
    ]


def test_anonymous_gets_401_json(client, convenio):
    for url in _urls(convenio):
        respuesta = client.get(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_without_the_permission_code_is_403_like_the_native_pages(client, convenio):
    usuario = _ready(get_user_model().objects.create_user("sin_permiso_templates"))
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="admisiones", codename="view_admision"
        )
    )
    client.force_login(usuario)

    for url in _urls(convenio):
        respuesta = client.get(url)
        assert respuesta.status_code == 403, url
        assert "state" not in respuesta.json()
    assert client.get(NATIVO).status_code == 403


def test_superuser_passes(client, convenio):
    client.force_login(
        _ready(get_user_model().objects.create_superuser("super_templates"))
    )

    for url in _urls(convenio):
        assert client.get(url).status_code == 200, url


def test_every_endpoint_is_read_only(web, convenio):
    for url in _urls(convenio):
        for metodo in ("post", "put", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(
    web, gestor
):
    gestor.profile.must_change_password = True
    gestor.profile.save()
    falso = web_gate.sign(
        audience="comedores",
        user_pk=gestor.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT,
    )

    respuesta = web.get(ROOT, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT)

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_admindocs_head_does_not_bypass_the_web_api(client, convenio):
    urls = _urls(convenio)
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_templates", is_staff=True))
    )

    for url in urls:
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- Split runtime -------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="comedores",
        ROOT_URLCONF="comedores_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target=ROOT, now=None):
    return web_gate.sign(
        audience="comedores",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_only_signed_requests(web, gestor):
    respuesta = web.get(ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(gestor, web))
    assert respuesta.status_code == 200

    for token in (None, _signed(gestor, web, now=timezone.now().timestamp() - 61)):
        extra = {"RAW_URI": ROOT}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.get(ROOT, **extra)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_rule(client):
    usuario = _ready(get_user_model().objects.create_user("runtime_sin_permiso"))
    client.force_login(usuario)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(usuario, client)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}
