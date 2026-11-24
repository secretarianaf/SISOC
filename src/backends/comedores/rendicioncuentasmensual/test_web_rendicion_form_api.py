"""Web API (G1 v1) of the monthly rendición form screens (RM01.02).

``/api/web/comedores/rendicioncuentasmensual/{nuevo,editar,eliminar}/<id>/`` runs
the native create, update and delete views. The tests pin today's access (each
native URL's code, plus ``edit_rendicion_data`` on the update), every projected
value against the native HTML page and the persisted effects of each POST.
"""

import re
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from comedores.models import Comedor
from organizaciones.models import Organizacion
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
)

PREFIJO = "/rendicioncuentasmensual/rendicioncuentasmensual"
VER = "rendicioncuentasmensual.view_rendicioncuentamensual"
EDITAR = "rendicioncuentasmensual.edit_rendicion_data"
R = RendicionCuentaMensual

pytestmark = pytest.mark.django_db


def _api(ruta, pk):
    return f"/api/web/comedores/rendicioncuentasmensual/{ruta}/{pk}/"


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _usuario(nombre, *codes):
    usuario = _ready(get_user_model().objects.create_user(nombre))
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


def _comedor():
    organizacion = Organizacion.objects.create(nombre="Org Form")
    return Comedor.objects.create(
        nombre="Comedor Form", organizacion=organizacion, codigo_de_proyecto="P-88"
    )


def _rendicion(comedor=None, **extra):
    datos = {
        "comedor": comedor or _comedor(),
        "mes": 3,
        "anio": 2026,
        "convenio": "P01",
        "numero_rendicion": 2,
        "nombre": "Rendición marzo",
        "periodo_inicio": date(2026, 3, 1),
        "periodo_fin": date(2026, 3, 31),
    }
    datos.update(extra)
    return R.objects.create(**datos)


@pytest.fixture(name="web")
def web_fixture():
    return _client(_usuario("lector_form_rm", VER))


@pytest.fixture(name="editor")
def editor_fixture():
    return _client(_usuario("editor_form_rm", VER, EDITAR))


def _html(respuesta):
    assert respuesta.status_code == 200
    return respuesta.content.decode()


def _opciones(html, nombre):
    bloque = re.search(rf'<select name="{nombre}".*?</select>', html, re.S).group(0)
    return re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', bloque)


# --- Access ----------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["nuevo", "editar", "eliminar"])
def test_anonymous_is_401_and_no_permission_is_403(ruta):
    rendicion = _rendicion()
    pk = rendicion.comedor_id if ruta == "nuevo" else rendicion.pk

    assert Client().get(_api(ruta, pk)).status_code == 401
    assert _client(_usuario(f"sin_{ruta}")).get(_api(ruta, pk)).status_code == 403
    assert Client().post(_api(ruta, pk)).status_code == 401


def test_the_native_codes_decide_each_screen(web, editor):
    rendicion = _rendicion()
    etapa = _client(
        _usuario("etapa_form_rm", "rendicioncuentasmensual.manage_territorial_stage")
    )

    assert web.get(_api("nuevo", rendicion.comedor_id)).status_code == 200
    assert web.get(_api("eliminar", rendicion.pk)).status_code == 200
    # A stage code is not the form code; the update also needs its own code.
    assert etapa.get(_api("eliminar", rendicion.pk)).status_code == 403
    assert etapa.get(f"{PREFIJO}/eliminar/{rendicion.pk}/").status_code == 403
    assert web.get(_api("editar", rendicion.pk)).status_code == 403
    assert web.get(f"{PREFIJO}/editar/{rendicion.pk}/").status_code == 403
    assert editor.get(_api("editar", rendicion.pk)).status_code == 200
    superuser = get_user_model().objects.create_superuser("su_form_rm")
    assert (
        _client(_ready(superuser)).get(_api("editar", rendicion.pk)).status_code == 200
    )


def test_pending_web_prerequisite_is_403_with_state():
    usuario = _usuario("pend_form_rm", VER)
    usuario.profile.must_change_password = True
    usuario.profile.save()

    respuesta = _client(usuario).get(_api("eliminar", _rendicion().pk))

    assert respuesta.status_code == 403
    assert "state" in respuesta.json()


def test_post_needs_csrf_and_a_known_content_type(web):
    rendicion = _rendicion()
    sin_csrf = _client(_usuario("csrf_form_rm", VER), enforce_csrf_checks=True)

    assert sin_csrf.post(_api("eliminar", rendicion.pk)).status_code == 403
    editor = _client(_usuario("ct_form_rm", VER, EDITAR))
    assert (
        editor.post(
            _api("editar", rendicion.pk), data="{}", content_type="application/json"
        ).status_code
        == 415
    )
    assert R.objects.get(pk=rendicion.pk).deleted_at is None


# --- Create ----------------------------------------------------------------------


def test_the_create_form_matches_the_native_page(web):
    comedor = _comedor()

    datos = web.get(_api("nuevo", comedor.pk)).json()
    html = _html(web.get(f"{PREFIJO}/nuevo/{comedor.pk}/"))

    assert datos["comedor_id"] == comedor.pk
    assert datos["titulo"] == "Crear"
    assert datos["urls"]["listado"] == f"{PREFIJO}/{comedor.pk}/"
    assert f'href="{datos["urls"]["listado"]}"' in html
    assert "Crear Seguimiento mensual" in html
    campos = datos["campos"]
    assert [
        campos[n]["label"]
        for n in ("mes", "anio", "observaciones", "nombre", "archivo")
    ] == [
        "Mes",
        "Año",
        "Observaciones",
        "Nombre del Documento",
        "Archivo",
    ]
    assert [
        campos[n]["required"]
        for n in ("mes", "anio", "observaciones", "nombre", "archivo")
    ] == [
        True,
        True,
        False,
        True,
        True,
    ]
    assert [(c["value"], c["label"]) for c in campos["mes"]["choices"]] == _opciones(
        html, "mes"
    )
    assert campos["observaciones"]["rows"] == 3
    assert campos["nombre"]["maxlength"] == 255
    assert datos["errors"] == {}
    assert datos["messages"] == []


def test_an_unknown_comedor_still_renders_the_form_like_the_native_page(web):
    assert web.get(f"{PREFIJO}/nuevo/999999/").status_code == 200
    assert web.get(_api("nuevo", 999999)).status_code == 200


def _archivo(nombre="comprobante.pdf"):
    return SimpleUploadedFile(nombre, b"%PDF-1.4", content_type="application/pdf")


def test_the_page_fields_never_save_a_rendicion_and_the_form_comes_back_blank(web):
    """The native form requires two fields the page does not render (kept quirk)."""
    comedor = _comedor()
    campos = {
        "mes": "4",
        "anio": "2026",
        "observaciones": "Texto",
        "nombre": "Planilla",
        "archivo": _archivo(),
    }

    nativa = web.post(f"{PREFIJO}/nuevo/{comedor.pk}/", campos)
    campos["archivo"] = _archivo()
    api = web.post(_api("nuevo", comedor.pk), campos)

    assert nativa.status_code == 200
    assert api.status_code == 400
    assert api.json()["errors"] == {}
    assert api.json()["campos"]["mes"]["value"] == ""
    assert api.json()["campos"]["observaciones"]["value"] == ""
    assert R.objects.count() == 0
    assert DocumentacionAdjunta.objects.count() == 0


def test_a_complete_post_creates_the_rendicion_with_its_files(web, tmp_path):
    comedor = _comedor()
    campos = {
        "mes": "4",
        "anio": "2026",
        "observaciones": "Texto",
        "linea_programatica": R.LINEA_TRADICIONAL,
        "estado": R.ESTADO_ELABORACION,
        "nombre": "Ignorado",
        "archivo": [_archivo("uno.pdf"), _archivo("dos.pdf")],
    }

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        respuesta = web.post(_api("nuevo", comedor.pk), campos)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{PREFIJO}/{comedor.pk}/"}
    rendicion = R.objects.get()
    assert (rendicion.comedor, rendicion.mes, rendicion.anio) == (comedor, 4, 2026)
    assert rendicion.observaciones == "Texto"
    assert rendicion.usuario_creador.username == "lector_form_rm"
    assert rendicion.usuario_ultima_modificacion.username == "lector_form_rm"
    # The native view names each document after its file; the typed name is ignored.
    assert sorted(a.nombre for a in rendicion.archivos_adjuntos.all()) == [
        "dos.pdf",
        "uno.pdf",
    ]


def test_a_complete_post_for_an_unknown_comedor_is_404(web, tmp_path):
    campos = {
        "mes": "4",
        "anio": "2026",
        "linea_programatica": R.LINEA_TRADICIONAL,
        "estado": R.ESTADO_ELABORACION,
    }

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        respuesta = web.post(_api("nuevo", 999999), campos)

    assert respuesta.status_code == 404
    assert R.objects.count() == 0


# --- Update ----------------------------------------------------------------------


def test_the_data_form_matches_the_native_page(editor):
    rendicion = _rendicion()

    datos = editor.get(_api("editar", rendicion.pk)).json()
    html = _html(editor.get(f"{PREFIJO}/editar/{rendicion.pk}/"))

    assert datos["id"] == rendicion.pk
    assert datos["numero"] == "2"
    assert datos["urls"]["detalle"] == f"{PREFIJO}/detalle/{rendicion.pk}/"
    assert "Rendición 2" in html
    campos = datos["campos"]
    assert [campos[n]["value"] for n in campos] == [
        "P01",
        "2",
        "2026-03-01",
        "2026-03-31",
        "Rendición marzo",
    ]
    assert 'value="2026-03-01"' in html
    assert [
        (c["value"], c["label"]) for c in campos["convenio"]["choices"]
    ] == _opciones(html, "convenio")
    assert [
        (c["value"], c["label"]) for c in campos["numero_rendicion"]["choices"]
    ] == _opciones(html, "numero_rendicion")
    assert [campos[n]["label"] for n in campos] == [
        "Convenio",
        "Numero rendicion",
        "Periodo inicio",
        "Periodo fin",
        "Nombre de Rendición",
    ]
    assert not any(campo["required"] for campo in campos.values())
    assert datos["errors"] == {}
    assert datos["non_field_errors"] == []


def test_a_rendicion_without_number_shows_its_pk(editor):
    rendicion = _rendicion(numero_rendicion=None, convenio=None)

    assert editor.get(_api("editar", rendicion.pk)).json()["numero"] == str(
        rendicion.pk
    )


def test_a_deleted_or_missing_rendicion_is_404_on_update_and_delete(editor):
    rendicion = _rendicion()
    rendicion.delete()

    for ruta in ("editar", "eliminar"):
        assert editor.get(_api(ruta, rendicion.pk)).status_code == 404
        assert editor.get(_api(ruta, rendicion.pk + 999)).status_code == 404
        assert editor.get(f"{PREFIJO}/{ruta}/{rendicion.pk}/").status_code == 404


def test_an_invalid_update_returns_the_native_errors_and_the_typed_values(editor):
    rendicion = _rendicion()
    enviados = {
        "convenio": "ZZ",
        "numero_rendicion": "99",
        "periodo_inicio": "2026-03-10",
        "periodo_fin": "2026-03-01",
        "nombre": "Cambio",
    }

    nativa = _html(editor.post(f"{PREFIJO}/editar/{rendicion.pk}/", enviados))
    api = editor.post(_api("editar", rendicion.pk), enviados)

    assert api.status_code == 400
    datos = api.json()
    for campo, errores in datos["errors"].items():
        for error in errores:
            assert error["message"] in nativa.replace("&quot;", '"')
    assert set(datos["errors"]) == {"convenio", "numero_rendicion", "periodo_fin"}
    assert datos["errors"]["periodo_fin"][0]["message"] == (
        "La fecha de fin debe ser posterior o igual a la fecha de inicio."
    )
    assert datos["campos"]["periodo_inicio"]["value"] == "2026-03-10"
    assert datos["campos"]["nombre"]["value"] == "Cambio"
    assert R.objects.get(pk=rendicion.pk).nombre == "Rendición marzo"


def test_a_valid_update_saves_and_recalculates_the_period(editor):
    rendicion = _rendicion()

    respuesta = editor.post(
        _api("editar", rendicion.pk),
        {
            "convenio": "P02",
            "numero_rendicion": "1",
            "periodo_inicio": "2026-05-01",
            "periodo_fin": "2026-05-31",
            "nombre": "  Mayo  ",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"{PREFIJO}/detalle/{rendicion.pk}/",
    }
    rendicion.refresh_from_db()
    assert (rendicion.convenio, rendicion.numero_rendicion) == ("P02", 1)
    assert (rendicion.mes, rendicion.anio) == (5, 2026)
    assert rendicion.periodo_fin == date(2026, 5, 31)
    assert rendicion.nombre == "Mayo"
    assert rendicion.usuario_ultima_modificacion.username == "editor_form_rm"


def test_an_empty_update_keeps_the_stored_values_and_clears_the_name(editor):
    rendicion = _rendicion()

    respuesta = editor.post(_api("editar", rendicion.pk), {"nombre": ""})

    assert respuesta.status_code == 200
    rendicion.refresh_from_db()
    assert (rendicion.convenio, rendicion.numero_rendicion) == ("P01", 2)
    assert rendicion.periodo_inicio == date(2026, 3, 1)
    assert rendicion.nombre is None


# --- Delete ----------------------------------------------------------------------


def test_the_delete_confirmation_matches_the_native_page(web):
    rendicion = _rendicion()

    datos = web.get(_api("eliminar", rendicion.pk)).json()
    html = _html(web.get(f"{PREFIJO}/eliminar/{rendicion.pk}/"))

    assert datos["id"] == rendicion.pk
    assert datos["object_name"] == str(rendicion).upper()
    assert datos["confirm_text"] == "Dar de baja"
    assert datos["cancel_text"] == "Cancelar"
    assert datos["cancel_url"] == f"{PREFIJO}/detalle/{rendicion.pk}/"
    assert datos["cascade_preview"]["total_afectados"] == 1
    assert datos["cascade_preview"]["desglose_por_modelo"][0]["modo"] == "baja_logica"
    assert datos["messages"] == []
    assert datos["object_name"] in html.upper()
    assert f'href="{datos["cancel_url"]}"' in html
    assert "Total de registros afectados:" in html


def test_confirming_soft_deletes_the_rendicion_and_returns_to_the_list(web):
    rendicion = _rendicion()
    otra = _rendicion(comedor=rendicion.comedor, mes=4)

    respuesta = web.post(_api("eliminar", rendicion.pk))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"{PREFIJO}/{rendicion.comedor_id}/",
    }
    assert R.objects.filter(pk=rendicion.pk).count() == 0
    assert R.all_objects.get(pk=rendicion.pk).deleted_at is not None
    assert R.objects.filter(pk=otra.pk).count() == 1
    assert web.get(_api("eliminar", rendicion.pk)).status_code == 404
