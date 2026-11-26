"""Web API (G1 v1) of the PAS back office: ``/api/web/pas/`` (PAS05.01, PAS06.01).

Monolith tests go through ``config.settings_all`` (policy evaluated locally);
the runtime tests switch to ``SISOC_BACKEND="pas"`` with the real runtime
URLconf, where only a request the core signed reaches the view.
"""

import json
from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core import web_gate
from core.models import Municipio, Provincia
from pas.models import (
    PasAviso,
    PasDeclaracionJurada,
    PasEstado,
    PasHistorialEstado,
    PasInvitacionDDJJ,
    PasPersona,
)

ROOT = "/api/web/pas/"
READS = (
    "areas/formacion/",
    "areas/mesa-ayuda/",
    "areas/liquidacion/",
    "formacion/personas/",
    "personas/",
    "panel/",
)

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _user(username, *codenames):
    user = _ready(get_user_model().objects.create_user(username))
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="admin")
def admin_fixture():
    return _ready(get_user_model().objects.create_superuser("super_pas", password="x"))


@pytest.fixture(name="web")
def web_fixture(admin):
    return _client(admin)


@pytest.fixture(name="lugar")
def lugar_fixture():
    provincia = Provincia.objects.create(nombre="Provincia PAS")
    return provincia, Municipio.objects.create(
        nombre="Municipio PAS", provincia=provincia
    )


@pytest.fixture(name="activo")
def activo_fixture():
    return PasEstado.objects.get_or_create(nombre="Activo")[0]


@pytest.mark.parametrize("ruta", ["/pas/cursos", f"{ROOT}cursos/"])
def test_cursos_pas_ya_no_esta_disponible(web, ruta):
    assert web.get(ruta).status_code == 404


def _persona(lugar, estado, n, **extra):
    provincia, municipio = lugar
    datos = {
        "id_persona": 5000 + n,
        "apellidos": f"Apellido{n:03d}",
        "nombres": f"Nombre{n:03d}",
        "dni": 30000000 + n,
        "provincia": provincia,
        "municipio": municipio,
        "estado": estado,
    }
    datos.update(extra)
    return PasPersona.objects.create(**datos)


def _ddjj(persona, version, **extra):
    invitacion = PasInvitacionDDJJ.objects.create(persona=persona)
    datos = {
        "persona": persona,
        "invitacion": invitacion,
        "version": version,
        "provincia": persona.provincia,
        "municipio": persona.municipio,
        "domicilio": "Calle 123",
        "correo_electronico": "persona@example.test",
        "telefono_celular": "1100000000",
        "datos_mi_argentina_confirmados": False,
        "embarazada": False,
        "hijos_menores_a_cargo": False,
        "gastos_bajo_limite_smvm": True,
        "no_accedio_mercado_cambios": True,
        "acepto_declaracion": True,
        "respuestas": {
            "domicilio": {"etiqueta": "Domicilio", "respuesta": "Calle 123"},
            "embarazada": {"etiqueta": "¿Está embarazada?", "respuesta": False},
            "firma_nombre_completo": {
                "etiqueta": "Firma con nombre completo",
                "respuesta": "Persona Ejemplo",
            },
        },
        "texto_legal": "Texto legal sintético",
        "archivo_pdf": f"pas/ddjj/{persona.dni}/2026/ddjj_v{version}.pdf",
        "finalizada": timezone.now(),
    }
    datos.update(extra)
    return PasDeclaracionJurada.objects.create(**datos)


# --- Access: G1 first, then the native route rule ---------------------------


def test_anonymous_gets_401_json_on_every_read(client):
    for url in READS:
        respuesta = client.get(ROOT + url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_without_view_paspersona_every_read_is_403_like_the_native_routes(
    lugar, activo
):
    persona = _persona(lugar, activo, 1)
    client = _client(_user("sin_pas", "change_paspersona", "add_paspersona"))

    for url in (*READS, f"panel/{persona.pk}/"):
        respuesta = client.get(ROOT + url)
        assert respuesta.status_code == 403, url
        assert "state" not in respuesta.json()
    assert client.get("/pas/listar").status_code == 403
    assert client.get("/pas/formacion").status_code == 403


def test_view_paspersona_or_superuser_reads(web, lugar, activo):
    persona = _persona(lugar, activo, 1)
    viewer = _client(_user("ve_pas", "view_paspersona"))

    for client in (web, viewer):
        for url in (*READS, f"panel/{persona.pk}/"):
            respuesta = client.get(ROOT + url)
            assert respuesta.status_code == 200, url
            assert respuesta["Cache-Control"] == "private, no-store"
            assert "Cookie" in respuesta["Vary"]


def test_reads_only_answer_get(web, lugar, activo):
    _persona(lugar, activo, 1)

    for url in READS:
        for metodo in ("post", "put", "delete"):
            assert getattr(web, metodo)(ROOT + url).status_code == 405, (url, metodo)


def test_pending_web_requirement_is_reported_and_a_forged_header_is_ignored(web, admin):
    admin.profile.must_change_password = True
    admin.profile.save()
    falso = web_gate.sign(
        audience="pas",
        user_pk=admin.pk,
        session_key=web.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=ROOT + "personas/",
    )

    respuesta = web.get(
        ROOT + "personas/", HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=ROOT + "personas/"
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["state"] == "password_change_required"


def test_admindocs_head_does_not_bypass_the_web_api(client, lugar, activo):
    persona = _persona(lugar, activo, 1)
    client.force_login(
        _ready(get_user_model().objects.create_user("staff_pas", is_staff=True))
    )

    for url in (*READS, f"panel/{persona.pk}/"):
        respuesta = client.head(ROOT + url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- PAS05.01 areas -----------------------------------------------------------


def test_workflow_cards_come_from_the_native_areas(web):
    data = web.get(ROOT + "areas/mesa-ayuda/").json()

    assert data["area"] == {
        "key": "mesa-ayuda",
        "number": "04",
        "title": "Mesa de Ayuda",
        "subtitle": "Reclamos y atención",
    }
    assert [(w["number"], w["title"], w["active"]) for w in data["workflow"]] == [
        ("01", "Panel de Control", False),
        ("02", "Formación FCH", False),
        ("03", "Cruces y Novedades", False),
        ("04", "Mesa de Ayuda", True),
        ("05", "Liquidación", False),
    ]
    assert [w["source_status"] for w in data["workflow"]] == [
        "disponible",
        "disponible",
        "disponible",
        "pendiente",
        "pendiente",
    ]
    assert data["workflow"][0]["url"] == "/pas/panel-control"
    assert data["total_padron"] == 0
    assert set(data) == {"area", "workflow", "total_padron"}


def test_liquidacion_counts_the_whole_padron(web, lugar, activo):
    for n in range(3):
        _persona(lugar, activo, n)

    data = web.get(ROOT + "areas/liquidacion/").json()

    assert data["area"]["title"] == "Liquidación"
    assert data["total_padron"] == 3


def test_other_area_keys_have_no_route(web):
    assert web.get(ROOT + "areas/cruces/").status_code == 404
    assert web.get(ROOT + "areas/panel/").status_code == 404


def test_formacion_requested_persona_goes_first_and_is_selected(web, lugar, activo):
    personas = [_persona(lugar, activo, n) for n in range(5)]
    pedida = personas[3]

    data = web.get(ROOT + "areas/formacion/", {"persona": pedida.pk}).json()

    assert [p["id"] for p in data["personas"]] == [
        pedida.pk,
        *[p.pk for p in personas if p != pedida],
    ]
    assert data["persona_seleccionada"] == {
        "id": pedida.pk,
        "apellidos": "Apellido003",
        "nombres": "Nombre003",
        "dni": 30000003,
    }
    assert data["persona_solicitada_id"] == pedida.pk
    assert data["personas"][0] == {
        "id": pedida.pk,
        "apellidos": "Apellido003",
        "nombres": "Nombre003",
        "puntos_formacion": 0,
        "estado_formacion": "sin-formacion",
    }
    areas = {w["key"]: w["url"] for w in data["workflow"]}
    assert areas["panel"] == f"/pas/panel-control/{pedida.pk}"
    assert areas["formacion"] == f"/pas/formacion?persona={pedida.pk}"
    assert data["formaciones"] == []
    resumen = data["resumen"]
    assert resumen["puntos"] == 0
    assert resumen["objetivo"] == 100
    assert resumen["estado"] == "sin-formacion"
    assert resumen["titulo"] == "Sin formación"
    assert resumen["detalle"] == (
        "La fuente de formación todavía no se encuentra integrada."
    )
    assert resumen["inicio_base"] == "01/01/2026"
    assert resumen["duracion_dias"] == 90


def test_formacion_non_numeric_persona_is_ignored(web, lugar, activo):
    primera = _persona(lugar, activo, 1)
    _persona(lugar, activo, 2)

    data = web.get(ROOT + "areas/formacion/", {"persona": "abc"}).json()

    assert data["persona_solicitada_id"] is None
    assert data["persona_seleccionada"]["id"] == primera.pk
    assert [w["url"] for w in data["workflow"]][1] == (
        f"/pas/formacion?persona={primera.pk}"
    )


def test_formacion_cumplido_and_en_curso_are_empty_without_a_source(web, lugar, activo):
    _persona(lugar, activo, 1)

    for estado in ("cumplido", "en-curso"):
        data = web.get(ROOT + "areas/formacion/", {"estado_formacion": estado}).json()
        assert data["personas"] == []
        assert data["persona_seleccionada"] is None
        assert data["estado_formacion"] == estado
        assert data["has_next"] is False
    data = web.get(ROOT + "areas/formacion/").json()
    assert data["estado_formacion"] == "todos"


def test_formacion_numeric_query_finds_dni_and_id_persona_and_keeps_raw_input(
    web, lugar, activo
):
    por_dni = _persona(lugar, activo, 1, dni=41000000)
    por_id = _persona(lugar, activo, 2, id_persona=41000000)
    _persona(lugar, activo, 3)

    data = web.get(ROOT + "areas/formacion/", {"q": "  41000000 "}).json()

    assert {p["id"] for p in data["personas"]} == {por_dni.pk, por_id.pk}
    assert data["query"] == "  41000000 "


def test_formacion_pages_of_thirty(web, lugar, activo):
    for n in range(31):
        _persona(lugar, activo, n)

    primera = web.get(ROOT + "areas/formacion/").json()
    segunda = web.get(ROOT + "formacion/personas/", {"page": "2"}).json()
    invalida = web.get(ROOT + "formacion/personas/", {"page": "xyz"}).json()

    assert len(primera["personas"]) == 30
    assert primera["has_next"] is True
    assert primera["next_page"] == 2
    assert len(segunda["personas"]) == 1
    assert segunda["has_next"] is False
    assert segunda["next_page"] is None
    assert len(invalida["personas"]) == 30
    assert invalida["personas"][0]["apellidos"] == "Apellido000"


def test_formacion_personas_page_repeats_the_link_values(web, lugar, activo):
    pedida = _persona(lugar, activo, 1)
    otra = _persona(lugar, activo, 2)

    data = web.get(
        ROOT + "formacion/personas/",
        {"q": " Apellido ", "estado_formacion": "", "persona": str(pedida.pk)},
    ).json()

    assert [p["id"] for p in data["personas"]] == [otra.pk]
    assert data["query"] == "Apellido"
    assert data["estado_formacion"] == "todos"
    assert data["persona_seleccionada_id"] == pedida.pk
    assert "html" not in data


# --- PAS06.01 buscador --------------------------------------------------------


def test_buscador_lists_ten_per_page_with_the_native_row_values(web, lugar, activo):
    aviso = PasAviso.objects.create(codigo=9101, descripcion="Aviso sintético")
    personas = [_persona(lugar, activo, n, cuit=f"20-{n}-1") for n in range(11)]
    personas[0].avisos.add(aviso)

    data = web.get(ROOT + "personas/").json()

    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["count"] is None
    assert data["has_next"] is True
    assert data["has_previous"] is False
    assert data["is_paginated"] is True
    # ``build_no_count_page_range``: the next page exists, more may follow.
    assert data["page_range"] == [1, 2, "…"]
    assert data["total_padron"] == 11
    assert len(data["results"]) == 10
    assert data["results"][0] == {
        "id": personas[0].pk,
        "apellidos": "Apellido000",
        "nombres": "Nombre000",
        "dni": 30000000,
        "id_persona": 5000,
        "cuit": "20-0-1",
        "provincia": "Provincia PAS",
        "municipio": "Municipio PAS",
        "estado": {"nombre": "Activo", "css_class": "pas-status-activo"},
        "avisos": [9101],
        "tag_ddjj": True,
        "tag_fch": True,
    }
    assert data["estados"] == [
        {"nombre": e.nombre} for e in PasEstado.objects.order_by("nombre")
    ]


def test_buscador_filters_like_the_native_list(web, lugar, activo):
    baja = PasEstado.objects.get_or_create(nombre="Baja")[0]
    uno = _persona(lugar, activo, 1, dni=42000000)
    dos = _persona(lugar, baja, 2)
    _persona(lugar, activo, 3, nombres="Otra")

    por_dni = web.get(ROOT + "personas/", {"q": " 42000000 "}).json()
    por_estado = web.get(ROOT + "personas/", {"estado": "bAjA"}).json()
    filtros = json.dumps(
        {"logic": "AND", "items": [{"field": "nombre", "op": "eq", "value": "Otra"}]}
    )
    avanzados = web.get(ROOT + "personas/", {"filters": filtros}).json()

    assert [p["id"] for p in por_dni["results"]] == [uno.pk]
    assert por_dni["query"] == " 42000000 "
    assert [p["id"] for p in por_estado["results"]] == [dos.pk]
    assert por_estado["estado_seleccionado"] == "bAjA"
    assert [p["nombres"] for p in avanzados["results"]] == ["Otra"]
    assert avanzados["total_padron"] == 3


def test_buscador_out_of_range_page_falls_back_to_the_last_non_empty(
    web, lugar, activo
):
    for n in range(12):
        _persona(lugar, activo, n)

    data = web.get(ROOT + "personas/", {"page": "999"}).json()
    invalida = web.get(ROOT + "personas/", {"page": "abc"}).json()

    assert data["page"] == 2
    assert len(data["results"]) == 2
    assert data["count"] is None
    assert invalida["page"] == 1


def test_buscador_pagination_prefix_repeats_busqueda_and_other_params(
    web, lugar, activo
):
    for n in range(12):
        _persona(lugar, activo, n)

    data = web.get(
        ROOT + "personas/", {"q": "Apellido", "estado": "Activo", "page": "2"}
    ).json()

    assert data["query_prefix"] == "busqueda=Apellido&q=Apellido&estado=Activo&"
    assert data["previous"] == 1
    assert web.get(ROOT + "personas/").json()["query_prefix"] == ""


def test_buscador_capabilities_follow_each_permission(lugar, activo):
    _persona(lugar, activo, 1)
    casos = [
        (("view_paspersona",), False, False),
        (("view_paspersona", "add_paspersona"), True, False),
        (("view_paspersona", "export_ddjj_tokens"), False, True),
    ]
    for n, (codigos, importar, exportar) in enumerate(casos):
        client = _client(_user(f"cap_{n}", *codigos))
        assert client.get(ROOT + "personas/").json()["capabilities"] == {
            "can_import": importar,
            "can_export_tokens": exportar,
        }


def test_buscador_empty_padron(web):
    data = web.get(ROOT + "personas/").json()

    assert data["results"] == []
    assert data["total_padron"] == 0
    assert data["is_paginated"] is False


# --- PAS06.01 panel de control ------------------------------------------------


def test_panel_without_pk_shows_the_first_titular_by_model_order(web, lugar, activo):
    segunda = _persona(lugar, activo, 2, apellidos="Bravo")
    primera = _persona(lugar, activo, 1, apellidos="Alfa")

    data = web.get(ROOT + "panel/").json()

    assert data["persona"]["id"] == primera.pk
    assert [p["id"] for p in data["personas_panel"]] == [primera.pk, segunda.pk]
    assert data["workflow"][0]["url"] == f"/pas/panel-control/{primera.pk}"
    assert data["workflow"][0]["active"] is True


def test_panel_unknown_pk_is_404_and_an_empty_padron_has_no_persona(web):
    assert web.get(ROOT + "panel/999999/").status_code == 404

    data = web.get(ROOT + "panel/").json()

    assert data["persona"] is None
    assert data["personas_panel"] == []
    assert data["ddjj"] == {
        "declaraciones": [],
        "seleccionada": None,
        "vigente_download_url": None,
    }
    assert data["eventos_historial"] == []


def test_panel_persona_projection(web, lugar, activo):
    aviso = PasAviso.objects.create(codigo=9201, descripcion="Aviso del titular")
    persona = _persona(
        lugar,
        activo,
        1,
        cuit="20-30000001-5",
        domicilio="Calle 1",
        correo_electronico="t@example.test",
        telefono_celular="11",
    )
    persona.avisos.add(aviso)
    momento = timezone.make_aware(datetime(2026, 11, 9, 12, 30))
    PasPersona.objects.filter(pk=persona.pk).update(
        fecha_creacion=momento, fecha_actualizacion=momento + timedelta(hours=1)
    )

    data = web.get(f"{ROOT}panel/{persona.pk}/").json()

    assert data["persona"] == {
        "id": persona.pk,
        "apellidos": "Apellido001",
        "nombres": "Nombre001",
        "dni": 30000001,
        "id_persona": 5001,
        "cuit": "20-30000001-5",
        "genero": "",
        "provincia": "Provincia PAS",
        "municipio": "Municipio PAS",
        "domicilio": "Calle 1",
        "correo_electronico": "t@example.test",
        "telefono_celular": "11",
        "estado": {
            "id": activo.pk,
            "nombre": "Activo",
            "css_class": "pas-status-activo",
        },
        "avisos": [{"codigo": 9201, "descripcion": "Aviso del titular"}],
        "fecha_creacion": timezone.localtime(momento).strftime("%d/%m/%Y %H:%M"),
        "fecha_actualizacion": timezone.localtime(
            momento + timedelta(hours=1)
        ).strftime("%d/%m/%Y %H:%M"),
        "ddjj_vigente": None,
    }
    assert data["capabilities"] == {"can_change": True, "can_delete": True}
    assert data["formaciones"] == []


def test_panel_delete_capability_follows_native_permission(lugar, activo):
    persona = _persona(lugar, activo, 1)
    url = f"{ROOT}panel/{persona.pk}/"
    lector = _client(_user("pas_lector_baja", "view_paspersona"))
    gestor = _client(_user("pas_gestor_baja", "view_paspersona", "delete_paspersona"))
    assert lector.get(url).json()["capabilities"]["can_delete"] is False
    assert gestor.get(url).json()["capabilities"]["can_delete"] is True


def test_panel_side_list_filters_tags_and_stops_at_one_hundred(web, lugar, activo):
    baja = PasEstado.objects.get_or_create(nombre="Baja")[0]
    personas = [_persona(lugar, activo, n) for n in range(101)]
    _ddjj(personas[0], 1)
    _persona(lugar, baja, 200, cuit="27-999-1")

    data = web.get(f"{ROOT}panel/{personas[0].pk}/").json()
    por_cuit = web.get(f"{ROOT}panel/{personas[0].pk}/", {"q": " 27-999 "}).json()
    por_estado = web.get(
        f"{ROOT}panel/{personas[0].pk}/", {"estado_actual": str(baja.pk)}
    ).json()
    por_dni = web.get(f"{ROOT}panel/{personas[0].pk}/", {"q": "30000005"}).json()

    assert len(data["personas_panel"]) == 100
    assert data["estado_actual"] == "todos"
    assert data["personas_panel"][0]["mostrar_tag_ddjj"] is False
    assert data["personas_panel"][1]["mostrar_tag_ddjj"] is True
    # Sin fuente FCH nadie llega a 100 puntos: el chip FCH se muestra.
    assert data["personas_panel"][1]["mostrar_tag_fch"] is True
    assert [p["cuit"] for p in por_cuit["personas_panel"]] == ["27-999-1"]
    assert por_cuit["query"] == "27-999"
    assert [p["estado"]["nombre"] for p in por_estado["personas_panel"]] == ["Baja"]
    assert por_estado["estado_actual"] == str(baja.pk)
    assert por_dni["personas_panel"] == []
    assert data["estados_panel"] == [
        {"id": e.pk, "nombre": e.nombre} for e in PasEstado.objects.order_by("nombre")
    ]


def test_panel_ddjj_versions_selection_and_private_fields(web, lugar, activo):
    persona = _persona(lugar, activo, 1)
    otra = _persona(lugar, activo, 2)
    versiones = [_ddjj(persona, v) for v in (1, 2, 3)]
    ajena = _ddjj(otra, 1)

    por_defecto = web.get(f"{ROOT}panel/{persona.pk}/").json()
    elegida = web.get(
        f"{ROOT}panel/{persona.pk}/", {"ddjj": str(versiones[0].pk)}
    ).json()
    con_ajena = web.get(f"{ROOT}panel/{persona.pk}/", {"ddjj": str(ajena.pk)}).json()
    no_numerica = web.get(f"{ROOT}panel/{persona.pk}/", {"ddjj": "x"}).json()

    ddjj = por_defecto["ddjj"]
    assert [(d["version"], d["es_ultima"]) for d in ddjj["declaraciones"]] == [
        (3, True),
        (2, False),
        (1, False),
    ]
    assert ddjj["seleccionada"]["id"] == versiones[2].pk
    assert ddjj["seleccionada"]["download_url"] == (
        f"/pas/ddjj/{versiones[2].pk}/descargar"
    )
    assert ddjj["seleccionada"]["respuestas"] == [
        {"clave": "domicilio", "etiqueta": "Domicilio", "respuesta": "Calle 123"},
        {
            "clave": "embarazada",
            "etiqueta": "¿Está embarazada?",
            "respuesta": "False",
        },
    ]
    assert ddjj["vigente_download_url"] == f"/pas/ddjj/{versiones[2].pk}/descargar"
    assert por_defecto["persona"]["ddjj_vigente"] == {
        "id": versiones[2].pk,
        "download_url": f"/pas/ddjj/{versiones[2].pk}/descargar",
    }
    assert elegida["ddjj"]["seleccionada"]["id"] == versiones[0].pk
    assert con_ajena["ddjj"]["seleccionada"]["id"] == versiones[2].pk
    assert no_numerica["ddjj"]["seleccionada"]["id"] == versiones[2].pk
    crudo = json.dumps(por_defecto, ensure_ascii=False)
    for privado in (
        "Texto legal sintético",
        "Persona Ejemplo",
        "firma_nombre_completo",
        str(versiones[0].invitacion.token),
        "media/pas",
        "ddjj_v3.pdf",
    ):
        assert privado not in crudo


def test_panel_history_mixes_states_and_ddjj_newest_first(web, lugar, activo):
    persona = _persona(lugar, activo, 1)
    aviso = PasAviso.objects.create(codigo=9301, descripcion="Nuevo aviso")
    operador = get_user_model().objects.create_user(
        "operador", first_name="Opera", last_name="Dora"
    )
    viejo = PasHistorialEstado.objects.create(
        persona=persona, estado_anterior=None, estado_nuevo=activo, usuario=None
    )
    nuevo = PasHistorialEstado.objects.create(
        persona=persona, estado_anterior=activo, estado_nuevo=activo, usuario=operador
    )
    nuevo.avisos_nuevos.add(aviso)
    declaracion = _ddjj(persona, 1)
    base = timezone.make_aware(datetime(2026, 11, 1, 10, 0))
    PasHistorialEstado.objects.filter(pk=viejo.pk).update(fecha_cambio=base)
    PasHistorialEstado.objects.filter(pk=nuevo.pk).update(
        fecha_cambio=base + timedelta(days=2)
    )
    PasDeclaracionJurada.objects.filter(pk=declaracion.pk).update(
        presentada=base + timedelta(days=1)
    )

    eventos = web.get(f"{ROOT}panel/{persona.pk}/").json()["eventos_historial"]

    assert [e["tipo"] for e in eventos] == ["estado", "ddjj", "estado"]
    assert eventos[0]["estado"] == "Activo"
    assert eventos[0]["avisos"] == [{"codigo": 9301, "descripcion": "Nuevo aviso"}]
    assert eventos[0]["usuario"] == "Opera Dora"
    assert eventos[1] == {
        "tipo": "ddjj",
        "fecha": timezone.localtime(base + timedelta(days=1)).strftime(
            "%d/%m/%Y %H:%M"
        ),
        "fecha_iso": timezone.localtime(base + timedelta(days=1)).isoformat(),
        "id": declaracion.pk,
        "version": 1,
    }
    assert eventos[2]["usuario"] is None
    assert eventos[2]["avisos"] == []


def test_panel_can_change_follows_change_paspersona(lugar, activo):
    persona = _persona(lugar, activo, 1)
    viewer = _client(_user("ve_panel", "view_paspersona"))
    editor = _client(_user("edita_panel", "view_paspersona", "change_paspersona"))

    assert viewer.get(f"{ROOT}panel/{persona.pk}/").json()["capabilities"] == {
        "can_change": False,
        "can_delete": False,
    }
    assert editor.get(f"{ROOT}panel/{persona.pk}/").json()["capabilities"] == {
        "can_change": True,
        "can_delete": False,
    }


def test_native_pages_are_unchanged(web, lugar, activo):
    persona = _persona(lugar, activo, 1)

    for url, plantilla in (
        ("/pas/listar", "pas/persona_list.html"),
        ("/pas/panel-control", "pas/persona_detail.html"),
        (f"/pas/{persona.pk}", "pas/persona_detail.html"),
        ("/pas/formacion", "pas/area.html"),
        ("/pas/mesa-ayuda", "pas/area.html"),
        ("/pas/liquidacion", "pas/area.html"),
    ):
        respuesta = web.get(url)
        assert respuesta.status_code == 200, url
        assert plantilla in [t.name for t in respuesta.templates], url
    fragmento = web.get("/pas/formacion/personas").json()
    assert "html" in fragmento
    assert Client().get("/pas/listar").status_code == 403


# --- Split runtime ------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="pas",
        ROOT_URLCONF="pas_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET", now=None):
    return web_gate.sign(
        audience="pas",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_reads(web, admin, lugar, activo):
    persona = _persona(lugar, activo, 1)
    target = f"{ROOT}panel/{persona.pk}/"

    respuesta = web.get(
        target, RAW_URI=target, HTTP_X_SISOC_WEB_GATE=_signed(admin, web, target=target)
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["persona"]["id"] == persona.pk


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_unsigned_stale_and_other_target_requests(web, admin):
    target = ROOT + "personas/"
    for token in (
        None,
        _signed(admin, web, target=ROOT + "panel/"),
        _signed(admin, web, target=target, now=timezone.now().timestamp() - 61),
    ):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.get(target, **extra)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_rule(client):
    usuario = _user("sin_ver_runtime", "change_paspersona")
    client.force_login(usuario)
    target = ROOT + "personas/"

    respuesta = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(usuario, client, target=target),
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_the_public_ddjj_routes(client):
    assert reverse("pas_ddjj_confirmacion") == "/pas/ddjj/confirmacion"
    assert client.get("/pas/ddjj/confirmacion").status_code == 200


def test_pas_publishes_its_web_api_prefix():
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    prefijos = load_backends_registry()["pas"]["url_prefixes"]

    assert web_gate.web_api_prefix("pas") in prefijos
    assert reverse("pas_web_personas") == ROOT + "personas/"
