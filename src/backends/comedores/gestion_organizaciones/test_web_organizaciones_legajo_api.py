"""Web API (G1 v1) of the Organizaciones legajo (O05.01).

``/api/web/comedores/organizaciones/<pk>/`` runs the native
``OrganizacionDetailView`` and returns the ``content`` block of
``organizacion_detail.html``. The tests compare that fragment with the native
HTML page ``/organizaciones/detalle/<pk>`` and pin today's access: any of
``ORGANIZACION_DOCUMENTACION_PERMS`` and the dupla scope (404 outside it).
"""

import json
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from comedores.models import Programas
from gestion_organizaciones.models import Firmante, ProgramaOrganizacion
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    SubtipoEntidad,
    TipoEntidad,
)

VIEW = "organizaciones.view_organizacion"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


def _organizacion():
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    sub = SubtipoEntidad.objects.create(nombre="Mutual", tipo_entidad=tipo)
    return Organizacion.objects.create(
        nombre="Legajo Sintético",
        cuit=20111111112,
        telefono=1140000000,
        email="legajo@ejemplo.org",
        tipo_entidad=tipo,
        subtipo_entidad=sub,
    )


@pytest.fixture(name="web_secos")
def web_secos_fixture():
    secos = Programas.objects.create(nombre="Abordaje comunitario - Línea Secos")
    alimentar = Programas.objects.create(nombre="Alimentar comunidad")
    organizacion = Organizacion.objects.create(nombre="Org Programas")
    for programa in (alimentar, secos):
        ProgramaOrganizacion.objects.create(
            organizacion=organizacion, programa=programa
        )
    return {
        "web": _client(_usuario("lector_prog", VIEW)),
        "org": organizacion,
        "secos": secos,
        "alimentar": alimentar,
    }


def _api(organizacion):
    return f"/api/web/comedores/organizaciones/{organizacion.pk}/"


def _todas(valor):
    """Every JSON object with a ``kind`` in the page, in document order."""
    if isinstance(valor, dict):
        if "kind" in valor:
            yield valor
        for hijo in valor.values():
            yield from _todas(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from _todas(hijo)


def _tipos(data):
    return [b["kind"] for b in data["blocks"]]


def test_page_is_data_with_header_data_card_and_no_html():
    organizacion = _organizacion()
    web = _client(_usuario("lector_leg", VIEW))

    data = web.get(_api(organizacion)).json()

    assert data["title"] == "Organización: Legajo Sintético"
    assert "html" not in data and "sections" not in data and "scripts" not in data
    assert ".legajo-header" in data["css"] and "<style" not in data["css"]
    assert data["header"] == {
        "name": "Legajo Sintético",
        "cuit": "20111111112",
        "tipo": "Asociación civil",
        "subtipo": "Mutual",
        "history_url": None,
        "edit_url": f"/organizaciones/editar/{organizacion.pk}",
        "delete_url": f"/organizaciones/eliminar/{organizacion.pk}",
    }
    assert data["selector"] == {"kind": "none"}
    datos = data["datos"]
    assert (datos["phone"], datos["email"], datos["programs"]) == (
        "1140000000",
        "legajo@ejemplo.org",
        [],
    )
    assert (datos["provincia"], datos["partido"], datos["comedores_count"]) == (
        "-",
        "-",
        0,
    )
    assert datos["expiry"] == {"text": "-", "state": None}
    assert datos["created"] != "-"
    assert _tipos(data) == [
        "sin_programas",
        "rendiciones_generales",
        "documentos",
        "sin_programa",
    ]
    assert data["messages"] == []


def test_header_without_type_and_cuit_uses_the_native_defaults():
    organizacion = Organizacion.objects.create(nombre="Mínima")
    web = _client(_usuario("lector_min", VIEW))

    header = web.get(_api(organizacion)).json()["header"]

    assert (header["cuit"], header["tipo"], header["subtipo"]) == (
        "Sin información",
        "Sin tipo de entidad",
        None,
    )


def test_history_link_needs_the_auditlog_permission():
    organizacion = _organizacion()
    admin = _client(_usuario("auditor_leg", VIEW, "auditlog.view_logentry"))

    header = admin.get(_api(organizacion)).json()["header"]

    assert header["history_url"].endswith(f"/organizacion/{organizacion.pk}/")


def test_expiry_state_vigente_vencido_and_sin_vencimiento():
    web = _client(_usuario("lector_venc", VIEW))
    futura = Organizacion.objects.create(
        nombre="F", fecha_vencimiento=date(2999, 1, 31)
    )
    vencida = Organizacion.objects.create(
        nombre="V", fecha_vencimiento=date(2000, 2, 1)
    )
    sin = Organizacion.objects.create(
        nombre="S", sin_vencimiento=True, fecha_vencimiento=date(2000, 2, 1)
    )

    def vencimiento(org):
        return web.get(_api(org)).json()["datos"]["expiry"]

    assert vencimiento(futura) == {"text": "31/01/2999", "state": "vigente"}
    assert vencimiento(vencida) == {"text": "01/02/2000", "state": "vencido"}
    assert vencimiento(sin) == {"text": "Sin Vencimiento", "state": "vencido"}


def test_program_selector_and_program_flow(web_secos):
    organizacion, secos = web_secos["org"], web_secos["secos"]
    alimentar, web = web_secos["alimentar"], web_secos["web"]

    info = web.get(_api(organizacion) + f"?programa={secos.pk}").json()
    rend = web.get(
        _api(organizacion) + f"?programa={secos.pk}&seccion=rendiciones"
    ).json()
    alco = web.get(_api(organizacion) + f"?programa={alimentar.pk}").json()

    assert info["selector"]["kind"] == "switch"
    assert [(i["name"], i["active"], i["url"]) for i in info["selector"]["items"]] == [
        (alimentar.nombre, False, f"?programa={alimentar.pk}"),
        (secos.nombre, True, f"?programa={secos.pk}"),
    ]
    assert _tipos(info) == [
        "franja",
        "tabs",
        "region",
        "proyectos",
        "convenios",
        "firmantes",
        "comedores",
    ]
    franja = info["blocks"][0]
    assert (franja["label"], franja["name"], franja["summary"]) == (
        "Abordaje Comunitario",
        secos.nombre,
        "0 espacios · 0 proyectos",
    )
    tabs = info["blocks"][1]["items"]
    assert [(t["label"], t["active"]) for t in tabs] == [
        ("Información del programa", True),
        ("Rendiciones Presentadas (0)", False),
    ]
    assert tabs[1]["url"] == f"?programa={secos.pk}&seccion=rendiciones"
    assert _tipos(rend)[:3] == ["franja", "tabs", "rendiciones_programa"]
    assert rend["blocks"][2]["title"] == f"Rendiciones Presentadas · {secos.nombre}"
    assert rend["blocks"][2]["table"] is None
    assert _tipos(alco)[:2] == ["franja", "firmantes"]
    assert alco["blocks"][0]["summary"] == "0 comedores · 0 firmantes"
    assert alco["blocks"][0]["label"] == "Programa"


def test_program_chip_with_a_single_program(web_secos):
    web, secos = web_secos["web"], web_secos["secos"]
    unica = Organizacion.objects.create(nombre="Un programa")
    ProgramaOrganizacion.objects.create(organizacion=unica, programa=secos)

    data = web.get(_api(unica)).json()

    assert data["selector"]["kind"] == "chip"
    assert data["selector"]["name"] == secos.nombre


def test_projects_without_line_show_the_notice(web_secos):
    web, organizacion = web_secos["web"], web_secos["org"]
    secos = web_secos["secos"]
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="SIN-1")
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="SIN-2")

    data = web.get(_api(organizacion) + f"?programa={secos.pk}").json()

    aviso = [b for b in data["blocks"] if b["kind"] == "aviso_sin_linea"][0]
    assert (aviso["count"], aviso["plural"], aviso["plural_n"], aviso["plural_s"]) == (
        2,
        "s",
        "n",
        "s",
    )
    assert aviso["codes"] == ["SIN-1", "SIN-2"]
    assert aviso["edit_url"] == (
        f"/organizaciones/editar/{organizacion.pk}#abordaje-card"
    )


def test_abordaje_data_without_a_line_shows_the_notice_and_the_sections():
    organizacion = Organizacion.objects.create(nombre="Datos sin línea")
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="X-1")
    web = _client(_usuario("lector_avi", VIEW))

    data = web.get(_api(organizacion)).json()

    assert _tipos(data)[:5] == [
        "sin_programas",
        "aviso_abordaje",
        "region",
        "proyectos",
        "rendiciones_generales",
    ]
    assert data["blocks"][3]["title"] == "Proyectos"
    assert data["blocks"][3]["color"] == "otro"


def test_sin_programa_block_groups_what_is_outside_the_loaded_programs(web_secos):
    web, organizacion = web_secos["web"], web_secos["org"]
    secos = web_secos["secos"]
    Firmante.objects.create(organizacion=organizacion, nombre="Suelto")
    Comedor.objects.create(nombre="Espacio suelto", organizacion=organizacion)

    data = web.get(_api(organizacion) + f"?programa={secos.pk}").json()

    bloque = data["blocks"][-1]
    assert bloque["kind"] == "sin_programa"
    firmantes, comedores = bloque["sections"]
    assert (firmantes["title"], firmantes["add_url"], firmantes["show_program"]) == (
        "Firmantes",
        None,
        True,
    )
    assert (comedores["title"], comedores["show_code"], comedores["show_program"]) == (
        "Comedores",
        True,
        True,
    )


def test_invalid_program_and_section_parameters_fall_back_like_the_native_view():
    organizacion = _organizacion()
    web = _client(_usuario("lector_par", VIEW))

    data = web.get(_api(organizacion) + "?programa=999&seccion=otra&proyecto=X").json()

    assert data["selector"] == {"kind": "none"}
    assert "sin_programas" in _tipos(data)


def test_technicians_see_only_their_dupla_and_no_manage_buttons():
    propia, ajena = _organizacion(), Organizacion.objects.create(nombre="Ajena")
    tecnico = _usuario("tecnico_leg", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("abogado_leg")
    )
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=propia, dupla=dupla)
    web = _client(tecnico)

    respuesta = web.get(_api(propia))

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["header"]["edit_url"] is None
    assert data["header"]["delete_url"] is None
    assert data["datos"]["edit_url"] is None
    assert "/organizaciones/editar/" not in json.dumps(data)
    assert web.get(_api(ajena)).status_code == 404
    assert web.get("/api/web/comedores/organizaciones/999999/").status_code == 404


def test_without_the_codes_the_answer_is_403_and_anonymous_401():
    organizacion = _organizacion()

    assert _client(_usuario("sin_leg")).get(_api(organizacion)).status_code == 403
    anonimo = Client().get(_api(organizacion))
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_pending_messages_are_consumed_like_the_native_page():
    organizacion = _organizacion()
    web = _client(_usuario("lector_msg", VIEW))
    # The native delete of another organization queues a message for this session.
    web.post(f"/organizaciones/eliminar/{Organizacion.objects.create(nombre='B').pk}")

    mensajes = web.get(_api(organizacion)).json()["messages"]

    assert mensajes == [
        {
            "message": "La organización B fue dada de baja correctamente.",
            "level": "success",
        }
    ]
    assert web.get(_api(organizacion)).json()["messages"] == []


def test_read_only_get_without_writes():
    organizacion = _organizacion()
    web = _client(_usuario("lector_ro", VIEW))
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(_api(organizacion)).status_code == 405, metodo
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(_api(organizacion)).status_code == 200
    assert not [
        q["sql"]
        for q in consultas.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
