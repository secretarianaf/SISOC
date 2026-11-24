"""Web API (G1 v1) of the monthly rendición audit screens (RM01.03).

``/api/web/comedores/rendicioncuentasmensual/auditoria/`` runs the native
``RendicionAuditoriaView``. The tests pin today's access (``manage_auditoria_stage``),
compare the projection with the native HTML page and check the persisted effects.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone

from comedores.models import Comedor
from organizaciones.models import Organizacion
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
)

PREFIJO = "/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/"
API = "/api/web/comedores/rendicioncuentasmensual/auditoria/"
CODE = "rendicioncuentasmensual.manage_auditoria_stage"
R = RendicionCuentaMensual

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
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="web")
def web_fixture():
    return _client(_usuario("auditor_api_rm", CODE))


def _comedor():
    organizacion = Organizacion.objects.create(nombre="Org Norte")
    return Comedor.objects.create(
        nombre="Comedor Aud", organizacion=organizacion, codigo_de_proyecto="P-77"
    )


def _rendicion(comedor=None, **extra):
    datos = {
        "comedor": comedor or _comedor(),
        "mes": 3,
        "anio": 2026,
        "convenio": "P01",
        "numero_rendicion": 2,
        "periodo_inicio": date(2026, 3, 1),
        "periodo_fin": date(2026, 3, 31),
        "etapa_proceso": R.ETAPA_AUDITORIA,
        "subestado_proceso": R.SUBESTADO_PENDIENTE,
    }
    datos.update(extra)
    return R.objects.create(**datos)


def _elegible(comedor):
    return _rendicion(
        comedor,
        mes=2,
        numero_rendicion=1,
        periodo_inicio=date(2026, 2, 1),
        periodo_fin=date(2026, 2, 28),
        validada=True,
        genera_acta_auditoria=False,
        fecha_gestion_auditoria=timezone.now(),
    )


# --- Access ----------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["", "{pk}/"])
def test_anonymous_is_401_and_no_permission_is_403(ruta):
    rendicion = _rendicion()
    url = API + ruta.format(pk=rendicion.pk)

    assert Client().get(url).status_code == 401
    assert Client().post(url).status_code == 401
    assert _client(_usuario("sin_aud_rm")).get(url).status_code == 403
    # Another stage code is not the audit code, like the native URL.
    otra = _usuario("otra_aud_rm", "rendicioncuentasmensual.manage_territorial_stage")
    assert _client(otra).get(url).status_code == 403
    assert _client(otra).get(PREFIJO + ruta.format(pk=rendicion.pk)).status_code == 403


def test_pending_prerequisite_is_403_with_state():
    usuario = _usuario("pend_aud_rm", CODE)
    usuario.profile.must_change_password = True
    usuario.profile.save()

    respuesta = _client(usuario).get(API)

    assert respuesta.status_code == 403
    assert "state" in respuesta.json()


def test_post_needs_csrf_and_a_known_content_type(web):
    rendicion = _rendicion()
    url = f"{API}{rendicion.pk}/"
    sin_csrf = _client(_usuario("csrf_aud_rm", CODE), enforce_csrf_checks=True)

    assert sin_csrf.post(url, {"validada": "on"}).status_code == 403
    assert web.post(url, data="{}", content_type="application/json").status_code == 415
    assert R.objects.get(pk=rendicion.pk).validada is not True


def test_search_page_is_get_only(web):
    assert web.post(API).status_code == 405


# --- Search ----------------------------------------------------------------------


def test_search_without_text_matches_the_native_page(web):
    datos = web.get(API).json()
    html = web.get(PREFIJO).content.decode()

    assert datos["busqueda_realizada"] is False
    assert datos["busqueda_valida"] is False
    assert datos["filas"] == []
    assert datos["filtro"]["value"] == "proyecto"
    assert [c["value"] for c in datos["filtro"]["choices"]] == [
        "proyecto",
        "organizacion",
        "periodo",
    ]
    assert datos["urls"]["limpiar"] == PREFIJO
    assert "Seleccioná un filtro e ingresá un texto" in html


def test_search_results_match_the_native_table(web):
    rendicion = _rendicion()
    consulta = "?filtro=proyecto&busqueda=P-77"

    datos = web.get(API + consulta).json()
    html = web.get(PREFIJO + consulta).content.decode()

    assert datos["busqueda_valida"] is True
    assert len(datos["filas"]) == 1
    fila = datos["filas"][0]
    assert fila["id"] == rendicion.pk
    assert (fila["proyecto"], fila["organizacion"]) == ("P-77", "Org Norte")
    assert fila["convenio_numero"] == "P01 · 2"
    assert fila["periodo"] == "01/03/2026 al 31/03/2026"
    assert fila["validada"] == "No"
    assert fila["gestionar_url"] == f"{PREFIJO}{rendicion.pk}/?origen=busqueda"
    assert fila["aria_label"] in html
    assert fila["gestionar_url"] in html
    assert datos["page"]["count"] == 1
    assert "Se encontraron 1 resultados" in html


def test_search_without_results_and_with_an_invalid_period(web):
    _rendicion()

    vacia = web.get(API + "?filtro=proyecto&busqueda=zzz").json()
    invalida = web.get(API + "?filtro=periodo&busqueda=xx").json()

    assert vacia["busqueda_valida"] is True
    assert vacia["filas"] == []
    assert invalida["busqueda_valida"] is False
    assert invalida["busqueda"]["errors"] == [
        "Ingresá un período como MM/AAAA, DD/MM/AAAA o AAAA."
    ]
    assert invalida["busqueda"]["value"] == "xx"


def test_search_paginates_with_the_native_links(web):
    comedor = _comedor()
    for numero in range(21):
        _rendicion(comedor, mes=1, numero_rendicion=1, anio=2000 + numero)

    datos = web.get(API + "?filtro=proyecto&busqueda=P-77&x=1").json()

    assert datos["page"]["is_paginated"] is True
    assert datos["page"]["next"] == 2
    assert datos["page"]["query_prefix"] == "busqueda=P-77&filtro=proyecto&x=1&"
    assert len(datos["filas"]) == 20


# --- Audit form ------------------------------------------------------------------


def test_missing_or_unavailable_rendicion_is_404(web):
    ya_auditada = _rendicion(fecha_auditada=timezone.now())
    borrada = _rendicion()
    borrada.delete()

    for pk in (ya_auditada.pk, borrada.pk, borrada.pk + 999):
        assert web.get(f"{API}{pk}/").status_code == 404
        assert web.get(f"{PREFIJO}{pk}/").status_code == 404
        assert web.post(f"{API}{pk}/", {"validada": "on"}).status_code == 404


def test_the_audit_form_matches_the_native_page(web):
    comedor = _comedor()
    rendicion = _rendicion(comedor)
    elegible = _elegible(comedor)
    DocumentacionAdjunta.objects.create(
        rendicion_cuenta_mensual=rendicion,
        categoria="formulario_ii",
        nombre="doc1",
        archivo="x/doc1.pdf",
    )

    datos = web.get(f"{API}{rendicion.pk}/?origen=busqueda").json()
    html = web.get(f"{PREFIJO}{rendicion.pk}/?origen=busqueda").content.decode()

    assert datos["rendicion"]["numero"] == "2"
    assert datos["rendicion"]["organizacion"] == "Org Norte"
    assert datos["rendicion"]["proyecto"] == "P-77"
    assert datos["rendicion"]["linea_programatica"] in html
    assert datos["volver_a_busqueda"] is True
    assert datos["urls"]["volver"] == PREFIJO
    assert "Volver a resultados" in html
    form = datos["form"]
    assert form["ya_validada"] is False
    assert form["genera_acta_auditoria"]["value"] == "False"
    assert [c["value"] for c in form["genera_acta_auditoria"]["choices"]] == [
        "False",
        "True",
    ]
    opcion = form["rendiciones_incluidas"]["opciones"][0]
    assert opcion["value"] == str(elegible.pk)
    assert opcion["periodo"] == "01/02/2026 al 28/02/2026"
    assert opcion["id"] == "id_rendiciones_incluidas_0"
    assert [r["id"] for r in datos["resumenes"]] == [rendicion.pk, elegible.pk]
    assert datos["resumenes"][0]["documentos"][0]["nombre"] == "doc1"
    assert datos["resumenes"][0]["titulo"] in " ".join(html.split())


def test_an_already_validated_rendicion_shows_it_fixed(web):
    rendicion = _rendicion(validada=True)

    datos = web.get(f"{API}{rendicion.pk}/").json()

    assert datos["form"]["ya_validada"] is True
    assert datos["volver_a_busqueda"] is False
    assert datos["urls"]["volver"].endswith(f"/detalle/{rendicion.pk}/")


def test_a_rejected_audit_returns_the_native_errors_and_the_typed_values(web):
    comedor = _comedor()
    rendicion = _rendicion(comedor)
    elegible = _elegible(comedor)
    enviados = {
        "genera_acta_auditoria": "True",
        "resultado": "finalizada_con_observaciones",
        "rendiciones_incluidas": [str(elegible.pk)],
    }

    respuesta = web.post(f"{API}{rendicion.pk}/", enviados)

    assert respuesta.status_code == 400
    form = respuesta.json()["form"]
    assert form["validada"]["errors"] == [
        "Marcá Validada para poder guardar la auditoría."
    ]
    assert form["errors"]["observaciones"][0]["message"] == (
        "Ingresá las observaciones de auditoría."
    )
    assert form["genera_acta_auditoria"]["value"] == "True"
    assert form["resultado"]["value"] == "finalizada_con_observaciones"
    assert form["rendiciones_incluidas"]["opciones"][0]["checked"] is True
    assert R.objects.get(pk=rendicion.pk).validada is not True


def test_validating_without_an_act_saves_and_redirects_to_the_detail(web):
    rendicion = _rendicion()

    respuesta = web.post(
        f"{API}{rendicion.pk}/", {"validada": "on", "genera_acta_auditoria": "False"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"{PREFIJO.replace('auditoria/', '')}detalle/{rendicion.pk}/",
    }
    rendicion.refresh_from_db()
    assert rendicion.validada is True
    assert rendicion.genera_acta_auditoria is False
    assert rendicion.fecha_gestion_auditoria is not None
    assert rendicion.usuario_ultima_modificacion.username == "auditor_api_rm"
    # Its management is closed now: it is no longer available.
    assert web.get(f"{API}{rendicion.pk}/").status_code == 404


def test_an_act_with_a_result_closes_the_group(web, tmp_path):
    comedor = _comedor()
    rendicion = _rendicion(comedor)
    elegible = _elegible(comedor)

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        respuesta = web.post(
            f"{API}{rendicion.pk}/",
            {
                "validada": "on",
                "genera_acta_auditoria": "True",
                "resultado": "finalizada",
                "rendiciones_incluidas": [str(elegible.pk)],
                "acta_auditoria": SimpleUploadedFile(
                    "acta.pdf", b"%PDF-1.4", content_type="application/pdf"
                ),
            },
        )

    assert respuesta.status_code == 200
    rendicion.refresh_from_db()
    elegible.refresh_from_db()
    assert rendicion.subestado_proceso == "finalizada"
    assert rendicion.genera_acta_auditoria is True
    assert elegible.genera_acta_auditoria is True
    assert elegible.rendicion_origen_acta_id == rendicion.pk
