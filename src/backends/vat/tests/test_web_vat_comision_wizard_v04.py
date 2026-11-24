"""V04.02 (U5): web API y entrada de vista previa del asistente de alta de comisión de curso. Datos sintéticos."""

import itertools
import types
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from config.urls_all import urlpatterns as monolith_patterns
from core.models import Dia, Localidad, Municipio, Provincia
from VAT.models import (
    Centro,
    ComisionCurso,
    ComisionHorario,
    Curso,
    InstitucionUbicacion,
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
    SesionComision,
)
from VAT.web_preview_vat_comision_wizard import comision_wizard_preview_patterns

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
PREFIJO = "comision_curso_asistente_json"


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"u{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_vat_sse",
            defaults={"name": "role_vat_sse"},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    centro = Centro.objects.create(
        nombre="CFP 401", codigo="060144900", provincia=provincia
    )
    modalidad = ModalidadCursada.objects.create(nombre="Presencial")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=modalidad,
        horas_reloj=100,
    )
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=localidad,
        rol_ubicacion="sede_principal",
        domicilio="7 123",
    )
    return {
        "centro": centro,
        "ubicacion": ubicacion,
        "modalidad": modalidad,
        "plan": plan,
        "dia": Dia.objects.create(nombre="Lunes"),
    }


@pytest.fixture(name="curso")
def curso_fixture(base):
    return Curso.objects.create(
        nombre="Electricidad básica",
        centro=base["centro"],
        plan_estudio=base["plan"],
        modalidad=base["modalidad"],
        inscripcion_libre=True,
    )


def _url(curso):
    return f"/api/web/vat/comisiones-asistente/cursos/{curso.pk}/"


def _info(base, **cambios):
    hoy = timezone.localdate()
    datos = {
        f"{PREFIJO}-current_step": "info",
        "info-ubicacion": base["ubicacion"].pk,
        "info-cupo_total": 20,
        "info-estado": "planificada",
        "info-fecha_inicio": (hoy + timedelta(days=1)).isoformat(),
        "info-fecha_fin": (hoy + timedelta(days=40)).isoformat(),
        "info-observaciones": "Notas",
    }
    datos.update(cambios)
    return datos


def _horarios(base, filas=None, **cambios):
    filas = filas or [(base["dia"].pk, "18:00", "20:00")]
    datos = {
        f"{PREFIJO}-current_step": "horarios",
        "horarios-TOTAL_FORMS": len(filas),
        "horarios-INITIAL_FORMS": 0,
        "horarios-MIN_NUM_FORMS": 1,
        "horarios-MAX_NUM_FORMS": 1000,
    }
    for indice, (dia, desde, hasta) in enumerate(filas):
        datos[f"horarios-{indice}-dia_semana"] = dia
        datos[f"horarios-{indice}-hora_desde"] = desde
        datos[f"horarios-{indice}-hora_hasta"] = hasta
        datos[f"horarios-{indice}-vigente"] = "1"
    datos.update(cambios)
    return datos


def _hasta_confirmacion(cliente, base, curso):
    url = _url(curso)
    assert cliente.get(url).status_code == 200
    assert cliente.post(url, _info(base)).json()["step"] == "horarios"
    respuesta = cliente.post(url, _horarios(base))
    assert respuesta.json()["step"] == "confirmacion"
    return respuesta


def test_access_follows_the_native_route_rule_and_the_center_scope(base, curso):
    url = _url(curso)
    assert APIClient().get(url).status_code == 401
    assert _client("change_comisioncurso", sse=True).get(url).status_code == 403
    assert _client("add_comisioncurso").get(url).status_code == 403
    assert _client("add_comisioncurso", sse=True).get(url).status_code == 200
    faltante = "/api/web/vat/comisiones-asistente/cursos/999999/"
    assert _client("add_comisioncurso", sse=True).get(faltante).status_code == 404
    assert base["centro"].pk == curso.centro_id


def test_first_step_projects_the_native_form(base, curso):
    cuerpo = _client("add_comisioncurso", sse=True).get(_url(curso)).json()
    assert cuerpo["step"] == "info"
    assert cuerpo["steps"] == ["info", "horarios", "confirmacion"]
    assert cuerpo["management"] == {"name": f"{PREFIJO}-current_step", "value": "info"}
    assert cuerpo["estado_label"] == "Planificada"
    assert cuerpo["curso"] == {
        "nombre": "Electricidad básica",
        "plan": str(base["plan"]),
        "codigo": f"{curso.pk:011d}",
    }
    assert [f["name"] for f in cuerpo["fields"]] == [
        f"info-{n}"
        for n in (
            "ubicacion",
            "cupo_total",
            "estado",
            "fecha_inicio",
            "fecha_fin",
            "acepta_lista_espera",
            "cupo_lista_espera",
            "observaciones",
        )
    ]
    ubicacion = cuerpo["fields"][0]
    assert [c["value"] for c in ubicacion["choices"]] == [
        "",
        str(base["ubicacion"].pk),
    ]
    assert ubicacion["attrs"]["class"] == "form-select sisoc-wizard-input"
    assert cuerpo["urls"]["cancel"] == f"/vat/centros/{curso.centro_id}/#cursos"
    assert cuerpo["messages"] == []


def test_invalid_first_step_is_400_with_the_native_errors_and_writes_nothing(
    base, curso
):
    cliente = _client("add_comisioncurso", sse=True)
    cliente.get(_url(curso))
    ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
    respuesta = cliente.post(
        _url(curso), _info(base, **{"info-cupo_total": 3, "info-fecha_inicio": ayer})
    )
    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["step"] == "info"
    errores = {f["name"]: f["errors"] for f in cuerpo["fields"] if f["errors"]}
    assert errores["info-fecha_inicio"] == [
        "La fecha de inicio debe ser igual o posterior a hoy."
    ]
    assert errores["info-cupo_total"] == [
        "Asegúrese de que este valor sea mayor o igual a 5."
    ]
    assert not ComisionCurso.objects.filter(curso=curso).exists()


def test_waiting_list_without_capacity_is_rejected_by_the_native_rule(base, curso):
    cliente = _client("add_comisioncurso", sse=True)
    cliente.get(_url(curso))
    respuesta = cliente.post(
        _url(curso), _info(base, **{"info-acepta_lista_espera": "on"})
    )
    assert respuesta.status_code == 400
    campo = next(
        f for f in respuesta.json()["fields"] if f["name"] == "info-cupo_lista_espera"
    )
    assert campo["errors"] == [
        "Definí un cupo para la lista de espera cuando está habilitada."
    ]
    ok = cliente.post(_url(curso), _info(base, **{"info-cupo_lista_espera": "7"}))
    assert ok.status_code == 200 and ok.json()["step"] == "horarios"


def test_schedule_step_projects_the_formset_and_validates_the_native_rules(base, curso):
    cliente = _client("add_comisioncurso", sse=True)
    cliente.get(_url(curso))
    cuerpo = cliente.post(_url(curso), _info(base)).json()
    formset = cuerpo["formset"]
    assert cuerpo["step"] == "horarios"
    assert formset["prefix"] == "horarios"
    valores = {m["name"]: m["value"] for m in formset["management"]}
    assert valores["horarios-TOTAL_FORMS"] == "1"
    assert [f["name"] for f in formset["forms"][0]["fields"]] == [
        f"horarios-0-{n}"
        for n in ("dia_semana", "hora_desde", "hora_hasta", "vigente", "DELETE")
    ]
    assert formset["empty"]["fields"][0]["name"] == "horarios-__prefix__-dia_semana"
    # Como la página nativa: el paso 1 dibuja ``required`` y los formularios del formset no.
    assert all(
        "required" not in f["attrs"]
        for h in (*formset["forms"], formset["empty"])
        for f in h["fields"]
    )
    primero = _client("add_comisioncurso", sse=True)
    primero.get(_url(curso))
    assert "required" in primero.get(_url(curso)).json()["fields"][0]["attrs"]
    corto = cliente.post(
        _url(curso), _horarios(base, [(base["dia"].pk, "18:00", "19:00")])
    )
    assert corto.status_code == 400
    assert corto.json()["formset"]["non_form_errors"] == [
        "El total semanal debe ser de al menos 2 horas."
    ]
    repetido = cliente.post(
        _url(curso),
        _horarios(
            base,
            [(base["dia"].pk, "18:00", "20:00"), (base["dia"].pk, "10:00", "12:00")],
        ),
    )
    assert repetido.json()["formset"]["non_form_errors"] == [
        "No puede haber dos horarios para el mismo día de la semana."
    ]
    breve = cliente.post(
        _url(curso), _horarios(base, [(base["dia"].pk, "18:00", "18:30")])
    )
    assert breve.json()["formset"]["forms"][0]["fields"][2]["errors"] == [
        "Cada clase debe durar al menos 45 minutos."
    ]
    assert not ComisionCurso.objects.filter(curso=curso).exists()


def test_back_keeps_the_stored_step_and_confirmation_projects_the_summary(base, curso):
    cliente = _client("add_comisioncurso", sse=True)
    respuesta = _hasta_confirmacion(cliente, base, curso)
    resumen = respuesta.json()["resumen"]
    assert resumen["ubicacion"] == str(base["ubicacion"])
    assert resumen["cupo"] == "20"
    assert resumen["horarios"] == [
        {
            "dia": "Lunes",
            "horas": "18:00 a 20:00",
            "duracion": "2 hs 0 minutos",
            "estado": "Activo",
        }
    ]
    assert resumen["total"] == "2 hs 0 minutos"
    atras = cliente.post(_url(curso), {"wizard_goto_step": "info"}).json()
    assert atras["step"] == "info"
    cupo = next(f for f in atras["fields"] if f["name"] == "info-cupo_total")
    assert cupo["value"] == "20"
    assert not ComisionCurso.objects.filter(curso=curso).exists()


def test_confirmation_persists_the_commission_hours_sessions_and_queues_the_message(
    base, curso
):
    cliente = _client("add_comisioncurso", sse=True)
    _hasta_confirmacion(cliente, base, curso)
    respuesta = cliente.post(_url(curso), {f"{PREFIJO}-current_step": "confirmacion"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/vat/centros/{curso.centro_id}/?refresh=1#cursos",
    }
    comision = ComisionCurso.objects.get(curso=curso)
    assert (comision.cupo_total, comision.estado) == (20, "planificada")
    assert comision.ubicacion == base["ubicacion"]
    horario = ComisionHorario.objects.get(comision_curso=comision)
    assert (horario.hora_desde.hour, horario.hora_hasta.hour, horario.vigente) == (
        18,
        20,
        True,
    )
    sesiones = SesionComision.objects.filter(comision_curso=comision).count()
    assert sesiones >= 1
    siguiente = cliente.get(_url(curso)).json()
    assert siguiente["messages"] == [
        {
            "message": f"Comisión creada con 1 horario(s) y {sesiones} sesión(es).",
            "level": "success",
        }
    ]


def test_get_restarts_the_wizard_and_confirming_without_the_steps_creates_nothing(
    base, curso
):
    cliente = _client("add_comisioncurso", sse=True)
    _hasta_confirmacion(cliente, base, curso)
    assert cliente.get(_url(curso)).json()["step"] == "info"
    cliente.post(_url(curso), {f"{PREFIJO}-current_step": "confirmacion"})
    assert not ComisionCurso.objects.filter(curso=curso).exists()


def test_writes_without_csrf_or_scope_change_nothing(base, curso):
    cliente = _client("add_comisioncurso", sse=True, csrf=True)
    assert cliente.post(_url(curso), _info(base)).status_code == 403
    sin_alcance = _client("add_comisioncurso")
    assert sin_alcance.post(_url(curso), _info(base)).status_code == 403
    assert not ComisionCurso.objects.filter(curso=curso).exists()


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("vat_comision_wizard_preview_test_urls")
    module.urlpatterns = comision_wizard_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_frozen_index_behind_the_native_guards(base, curso):
    del base
    url = f"/vat/cursos/{curso.pk}/comision/nueva/"
    respuesta = _client("add_comisioncurso", sse=True).get(url)
    assert respuesta.status_code == 200
    cuerpo = respuesta.content.decode()
    assert '/vat/react/assets/app-1.js"' in cuerpo
    assert "/v2/sisoc/assets/" not in cuerpo
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert _client("view_comisioncurso", sse=True).get(url).status_code == 403
    assert Client().get(url).status_code == 403
    assert _client("add_comisioncurso").get(url).status_code == 403
    faltante = "/vat/cursos/999999/comision/nueva/"
    assert _client("add_comisioncurso", sse=True).get(faltante).status_code == 404
