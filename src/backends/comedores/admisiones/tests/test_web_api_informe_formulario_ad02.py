"""Effective-form schema of the report editor (AD02.01, gates 1 and 2).

The API schema must equal what the native ``Form`` computes for each admission
variant, and the native whitelist rules (exclusions, conditional fields) are
pinned here so a React editor cannot drift from them. With ``AD02_SNAPSHOT_DIR``
set, the native effective fields are also dumped as JSON snapshots.
"""

import json
import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from admisiones.forms.admisiones_forms import (
    InformeTecnicoBaseForm,
    InformeTecnicoJuridicoForm,
)
from admisiones.tests.test_web_api_informe_detalle_ad02 import _informe
from admisiones.models.admisiones import Admision, InformeTecnico
from comedores.models import Comedor

API = "/api/web/comedores/admisiones/informes/"
FORMS = {"base": InformeTecnicoBaseForm, "juridico": InformeTecnicoJuridicoForm}
VARIANTES = {
    "incorporacion": {"tipo": "incorporacion", "es_ex_pnud": "no"},
    "incorporacion_pnud_vigente": {
        "tipo": "incorporacion",
        "es_ex_pnud": "si",
        "estado_convenio_pnud": "vigente",
    },
    "renovacion_primera": {"tipo": "renovacion", "tipo_renovacion": "primera"},
    "renovacion_segunda": {
        "tipo": "renovacion",
        "tipo_renovacion": "segunda_o_posterior",
    },
    "renovacion_complementario": {
        "tipo": "renovacion",
        "tipo_renovacion": "primera",
        "informe_complementario_modifica_prestaciones": "si",
    },
}
RESOLUCIONES = {f"resolucion_de_pago_{n}" for n in range(1, 7)} | {
    f"monto_{n}" for n in range(1, 7)
}

pytestmark = pytest.mark.django_db


def _admision(comedor, **datos):
    return Admision.objects.create(comedor=comedor, **datos)


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor Formulario")


@pytest.fixture(name="web")
def web_fixture():
    usuario = get_user_model().objects.create_user("editor_informe")
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="comedores", codename="view_comedor"
        )
    )
    client = Client()
    client.force_login(usuario)
    return client


def _native(tipo, admision, require_full=False):
    return FORMS[tipo](admision=admision, require_full=require_full)


@pytest.mark.parametrize("tipo", ["base", "juridico"])
@pytest.mark.parametrize("variante", sorted(VARIANTES))
def test_api_schema_equals_the_native_effective_form(web, comedor, tipo, variante):
    admision = _admision(comedor, **VARIANTES[variante])

    respuesta = web.get(f"{API}{tipo}/admision/{admision.pk}/formulario/")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    nativo = _native(tipo, admision)
    assert [f["name"] for f in datos["fields"]] == list(nativo.fields)
    assert {f["name"]: f["required"] for f in datos["fields"]} == {
        n: f.required for n, f in nativo.fields.items()
    }
    assert (
        datos["permite_no_corresponde"]
        == nativo.permite_no_corresponde_fecha_vencimiento
    )
    assert datos["require_full"] is False
    assert (datos["admision_id"], datos["informe_id"], datos["estado"]) == (
        admision.pk,
        None,
        "",
    )

    nombres = set(nativo.fields)
    assert not nombres & RESOLUCIONES
    assert "conclusiones" not in nombres and "antecedentes_renovaciones" not in nombres
    renovacion = VARIANTES[variante]["tipo"] == "renovacion"
    assert ("expediente_incorporacion" in nombres) is renovacion
    assert ("convenio_incorporacion" in nombres) is renovacion
    assert ("finalizacion_convenio_pnud_vigente" in nombres) is (
        variante == "incorporacion_pnud_vigente"
    )
    assert ("presentacion_avales" in nombres) is (renovacion and tipo == "base")
    complementario = variante == "renovacion_complementario"
    assert ("if_it_complementario" in nombres) is complementario
    assert (
        any(n.startswith("aprobadas_ultimo_convenio_") for n in nombres) is renovacion
    )
    if tipo == "base":
        assert (
            not {"validacion_registro_nacional", "IF_relevamiento_territorial"}
            & nombres
        )
    else:
        assert "declaracion_jurada_recepcion_subsidios" not in nombres
        assert "organizacion_avalista_1" not in nombres


def test_submit_requires_what_draft_does_not(comedor):
    admision = _admision(comedor, tipo="renovacion", tipo_renovacion="primera")
    borrador = _native("base", admision)
    completo = _native("base", admision, require_full=True)

    assert not any(f.required for f in borrador.fields.values())
    obligatorios = {n for n, f in completo.fields.items() if f.required}
    assert "expediente_incorporacion" in obligatorios
    assert "aprobadas_ultimo_convenio_desayuno_lunes" in obligatorios


def test_second_renewal_projects_the_antecedents(web, comedor):
    previa = _admision(comedor, tipo="renovacion", tipo_renovacion="primera")
    actual = _admision(
        comedor, tipo="renovacion", tipo_renovacion="segunda_o_posterior"
    )

    datos = web.get(f"{API}base/admision/{actual.pk}/formulario/").json()

    assert [a["admision_id"] for a in datos["antecedentes"]] == [previa.pk]
    nombres = {f["name"] for f in datos["fields"]}
    assert {
        datos["antecedentes"][0][k]
        for k in ("incluida", "resolucion", "convenio", "expediente")
    } <= nombres
    incluida = next(
        f for f in datos["fields"] if f["name"] == datos["antecedentes"][0]["incluida"]
    )
    assert (incluida["kind"], incluida["value"]) == ("checkbox", True)


def test_edit_schema_carries_state_remarks_and_the_publication_error(web, comedor):
    admision = _admision(comedor, tipo="incorporacion", es_ex_pnud="no")
    informe = _informe(admision, expediente_nro="EX-9")

    datos = web.get(f"{API}base/{informe.pk}/formulario/").json()

    assert (datos["informe_id"], datos["estado"]) == (informe.pk, "Iniciado")
    campo = next(f for f in datos["fields"] if f["name"] == "expediente_nro")
    assert campo["value"] == "EX-9"
    assert datos["publicacion"]["plantilla"] is None
    assert datos["publicacion"]["error"]
    assert isinstance(InformeTecnico.objects.get(pk=informe.pk), InformeTecnico)


def test_access_and_lookups_are_the_native_ones(web, comedor):
    admision = _admision(comedor, tipo="incorporacion", es_ex_pnud="no")
    url = f"{API}base/admision/{admision.pk}/formulario/"

    assert Client().get(url).status_code in (401, 403)
    sin_permiso = Client()
    sin_permiso.force_login(get_user_model().objects.create_user("sin_permiso_form"))
    assert sin_permiso.get(url).status_code in (403,)
    assert web.get(f"{API}base/admision/999999/formulario/").status_code == 404
    assert web.get(f"{API}base/999999/formulario/").status_code == 404
    otro = web.get(f"{API}otro/admision/{admision.pk}/formulario/")
    assert otro.status_code == 400
    assert otro.json()["detail"] == (
        "El tipo de informe seleccionado no está disponible para carga online."
    )
    assert web.post(url, {}).status_code == 405


def test_snapshots_of_the_native_effective_fields(comedor):
    destino = os.environ.get("AD02_SNAPSHOT_DIR")
    if not destino:
        pytest.skip("snapshot dump disabled")
    for tipo in FORMS:
        for variante, datos in VARIANTES.items():
            admision = _admision(comedor, **datos)
            for completo in (False, True):
                form = _native(tipo, admision, completo)
                (
                    Path(destino)
                    / f"{tipo}-{variante}-{'submit' if completo else 'draft'}.json"
                ).write_text(
                    json.dumps(
                        {n: f.required for n, f in form.fields.items()},
                        indent=1,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )


def test_schema_carries_what_the_editor_renders(web, comedor):
    admision = _admision(comedor, tipo="incorporacion", es_ex_pnud="no")

    datos = web.get(f"{API}base/admision/{admision.pk}/formulario/").json()

    nativo = _native("base", admision)
    assert {f["name"]: (f["id"], f["widget"]) for f in datos["fields"]} == {
        n: (nativo[n].id_for_label, type(f.widget).__name__)
        for n, f in nativo.fields.items()
    }
    provincia = next(
        f for f in datos["fields"] if f["name"] == "provincia_organizacion"
    )
    assert provincia["attrs"]["data-geografia-provincia"] == "id_localidad_organizacion"
    fecha = next(
        f for f in datos["fields"] if f["name"] == "fecha_vencimiento_mandatos"
    )
    assert (fecha["kind"], fecha["attrs"]["class"]) == ("date", "form-control")
    assert datos["urls"] == {
        "volver": reverse("admisiones_tecnicos_editar", args=[admision.pk]),
        "previsualizar": None,
        "reportar_faltante": reverse(
            "admisiones_reportar_configuracion_faltante_template", args=[admision.pk]
        ),
        "localidades": reverse("ajax_load_localidades"),
    }
    assert datos["estado_formulario"] == ""


def test_notification_message_keeps_its_native_tag_and_is_consumed_once(comedor):
    from unittest import mock

    admision = _admision(comedor, tipo="incorporacion", es_ex_pnud="no")
    informe = _informe(admision)
    root = get_user_model().objects.create_superuser("super_notifica")
    perfil = root.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    web = Client()
    web.force_login(root)

    with mock.patch(
        "admisiones.services.templates_informe_tecnico_service."
        "PlantillaInformeTecnicoService.reportar_configuracion_faltante",
        return_value=(object(), "Registrada para los referentes."),
    ):
        respuesta = web.post(
            f"/comedores/admisiones/{admision.pk}/templates/reportar-faltante/",
            {"informe_id": informe.pk},
        )
    assert respuesta.status_code == 302

    url = f"{API}base/{informe.pk}/formulario/"
    datos = web.get(url).json()
    assert [(m["message"], m["level"]) for m in datos["messages"]] == [
        ("Registrada para los referentes.", "success")
    ]
    assert "configuracion-template" in datos["messages"][0]["tags"]
    assert web.get(url).json()["messages"] == []
