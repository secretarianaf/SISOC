"""Web API (G1 v1) of the PAS crossings: ``/api/web/pas/cruces/`` (PAS03.01, PAS03.02).

Neither SINTyS nor RENAPER is ever called: the RENAPER client is replaced by a
function that fails the test when invoked.
"""

import io
from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone
from openpyxl import load_workbook

from core import web_gate
from core.models import Municipio, Provincia
from pas.models import (
    PasAviso,
    PasCircuitoMensual,
    PasControlRenaper,
    PasEstado,
    PasIncompatibilidad,
    PasPersona,
    PasSupervivenciaRun,
)
from pas.services.cruces_service import COLUMNAS_ENVIO_SINTYS

ROOT = "/api/web/pas/cruces/"
EXPORTAR = f"{ROOT}exportar-sintys/"
IMPORTAR = f"{ROOT}importar-sintys/"
RENAPER = f"{ROOT}actualizar-renaper/"
ACCIONES = (EXPORTAR, IMPORTAR, RENAPER)

pytestmark = pytest.mark.django_db


def _user(username, *codenames):
    user = get_user_model().objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    return user


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(name="viewer")
def viewer_fixture():
    return _client(_user("cruces_ve", "view_paspersona"))


@pytest.fixture(name="editor")
def editor_fixture():
    return _client(_user("cruces_edita", "view_paspersona", "change_paspersona"))


@pytest.fixture(name="persona")
def persona_fixture():
    provincia = Provincia.objects.create(nombre="Provincia cruces web")
    municipio = Municipio.objects.create(nombre="Municipio cruces", provincia=provincia)
    estado = PasEstado.objects.get_or_create(nombre="Activo")[0]
    return PasPersona.objects.create(
        id_persona=881001,
        apellidos="García",
        nombres="María",
        dni=30111222,
        cuit="27301112224",
        provincia=provincia,
        municipio=municipio,
        estado=estado,
    )


@pytest.fixture(autouse=True)
def _never_call_renaper():
    def fail(*args, **kwargs):
        raise AssertionError("RENAPER must not be called by the web")

    with patch("pas.services.supervivencia_service.consultar_datos_renaper", fail):
        yield


def _incompatibilidad(persona, detalle="RENAPER informó fallecimiento.", mes=8):
    return PasIncompatibilidad.objects.create(
        persona=persona,
        categoria=PasIncompatibilidad.Categoria.SUPERVIVENCIA,
        periodo_impacto=date(2026, mes, 1),
        detalle=detalle,
    )


# --- Access ---------------------------------------------------------------------


def test_anonymous_gets_401_json_on_the_read_and_the_actions(client):
    assert client.get(ROOT).status_code == 401
    assert client.get(ROOT).json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    for url in ACCIONES:
        assert client.post(url).status_code == 401, url


def test_read_needs_view_paspersona_like_the_native_route():
    client = _client(_user("cruces_sin_ver", "change_paspersona"))

    assert client.get(ROOT).status_code == 403
    assert client.get("/pas/cruces").status_code == 403


def test_actions_need_change_paspersona_and_do_nothing_without_it(viewer, persona):
    for url in ACCIONES:
        assert viewer.post(url).status_code == 403, url
    assert not PasCircuitoMensual.objects.exists()
    assert not PasSupervivenciaRun.objects.exists()


def test_actions_without_csrf_are_403_and_reads_do_not_accept_post(editor):
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(_user("cruces_csrf", "view_paspersona", "change_paspersona"))
    for url in ACCIONES:
        assert csrf.post(url).status_code == 403, url
    assert editor.post(ROOT).status_code == 405
    for url in ACCIONES:
        assert editor.get(url).status_code == 405, url
    assert not PasCircuitoMensual.objects.exists()


# --- PAS03.02: projection --------------------------------------------------------


def test_get_projects_the_pending_circuit_without_creating_it(viewer, persona):
    respuesta = viewer.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    datos = respuesta.json()
    hoy = timezone.localdate()
    assert datos["can_change"] is False
    assert datos["total_padron"] == 1
    assert datos["circuito"] == {
        "periodo": date(hoy.year, hoy.month, 1).isoformat(),
        "periodo_texto": f"{hoy.month:02d}/{hoy.year}",
        "existe": False,
    }
    assert [e["nombre"] for e in datos["etapas"]] == [
        "Exportación a SINTyS (VIAS)",
        "Importación retorno SINTyS",
        "Cruce FTP Justicia",
        "Cruce Migraciones",
        "Procesamiento de alertas",
        "Cierre del circuito mensual",
    ]
    assert [e["integracion_pendiente"] for e in datos["etapas"]] == [
        False,
        False,
        True,
        True,
        False,
        False,
    ]
    assert all(e["completada"] is False and e["fecha"] is None for e in datos["etapas"])
    assert datos["renaper"] == {
        "fecha": None,
        "total": 0,
        "fallecidas": 0,
        "errores": 0,
    }
    assert datos["incompatibilidades"] == []
    assert "corrida" not in datos
    assert [a["key"] for a in datos["areas"]] == [
        "panel",
        "formacion",
        "cruces",
        "mesa-ayuda",
        "liquidacion",
    ]
    assert [a["active"] for a in datos["areas"]] == [False, False, True, False, False]
    assert not PasCircuitoMensual.objects.exists()


def test_can_change_follows_the_permission(editor):
    assert editor.get(ROOT).json()["can_change"] is True


def test_get_shows_renaper_state_and_pending_incompatibility(viewer, persona):
    PasControlRenaper.objects.create(
        persona=persona,
        fecha_consulta=date(2026, 7, 29),
        resultado=PasControlRenaper.Resultado.FALLECIDA,
        sexo_consulta="F",
        error_tipo="fallecido",
    )
    _incompatibilidad(persona)

    datos = viewer.get(ROOT).json()

    assert datos["renaper"] == {
        "fecha": "29/07/2026",
        "total": 1,
        "fallecidas": 1,
        "errores": 0,
    }
    (fila,) = datos["incompatibilidades"]
    assert fila["titular"] == "García, María"
    assert fila["dni"] == 30111222
    assert fila["categoria"] == "Supervivencia"
    assert fila["detalle"] == "RENAPER informó fallecimiento."
    assert fila["periodo_impacto"] == "08/2026"
    assert fila["estado"] == "Pendiente"
    assert len(fila["fecha_deteccion"]) == len("29/07/2026 10:30")


def test_get_completed_stage_carries_its_date(editor, persona):
    circuito = PasCircuitoMensual.objects.create(
        periodo=date(timezone.localdate().year, timezone.localdate().month, 1),
        fecha_exportacion_sintys=timezone.now(),
    )

    datos = editor.get(ROOT).json()

    assert datos["circuito"]["existe"] is True
    primera = datos["etapas"][0]
    assert primera["completada"] is True
    assert primera["fecha"].startswith(
        timezone.localtime(circuito.fecha_exportacion_sintys).strftime("%Y-%m-%dT")
    )
    assert primera["fecha_texto"] == timezone.localtime(
        circuito.fecha_exportacion_sintys
    ).strftime("%d/%m/%Y %H:%M")
    assert datos["etapas"][1]["completada"] is False


@pytest.mark.parametrize(
    ("estado_nombre", "codigo_aviso", "visible"),
    [("Baja", 40, False), ("Baja", 39, True), ("Activo", 40, True)],
)
def test_only_the_baja_by_death_leaves_the_tray(
    viewer, persona, estado_nombre, codigo_aviso, visible
):
    estado = PasEstado.objects.get_or_create(nombre=estado_nombre)[0]
    aviso = PasAviso.objects.create(codigo=codigo_aviso, descripcion="AVISO")
    aviso.estados.add(estado)
    persona.estado = estado
    persona.save(update_fields=["estado"])
    persona.avisos.set([aviso])
    _incompatibilidad(persona, "Marca de prueba.")

    detalles = [i["detalle"] for i in viewer.get(ROOT).json()["incompatibilidades"]]

    assert ("Marca de prueba." in detalles) is visible


def test_tray_is_capped_at_100_pending_only(viewer, persona):
    ayer = date(2026, 1, 1)
    for n in range(102):
        PasIncompatibilidad.objects.create(
            persona=persona,
            categoria=PasIncompatibilidad.Categoria.SUPERVIVENCIA,
            periodo_impacto=date(2030 + n // 12, n % 12 + 1, 1),
            detalle=f"pendiente {n}",
        )
    PasIncompatibilidad.objects.create(
        persona=persona,
        categoria=PasIncompatibilidad.Categoria.SUPERVIVENCIA,
        periodo_impacto=ayer,
        detalle="resuelta",
        estado=next(
            valor
            for valor, _ in PasIncompatibilidad.Estado.choices
            if valor != PasIncompatibilidad.Estado.PENDIENTE
        ),
    )

    filas = viewer.get(ROOT).json()["incompatibilidades"]

    assert len(filas) == 100
    assert "resuelta" not in [f["detalle"] for f in filas]


# --- PAS03.01: actions --------------------------------------------------------------


def test_export_answers_the_native_file_and_completes_stage_one_once(
    editor, persona, tmp_path
):
    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = editor.post(EXPORTAR)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].endswith("spreadsheetml.sheet")
    assert respuesta["Content-Disposition"].startswith(
        'attachment; filename="nomina_pas_sintys_vias_'
    )
    assert respuesta["Content-Disposition"].endswith('.xlsx"')
    assert respuesta["Cache-Control"] == "private, no-store"
    filas = list(
        load_workbook(io.BytesIO(respuesta.content), read_only=True)[
            "nomina"
        ].iter_rows(values_only=True)
    )
    assert filas[0] == COLUMNAS_ENVIO_SINTYS
    fila = dict(zip(COLUMNAS_ENVIO_SINTYS, filas[1]))
    assert fila["ID_ORIG"] == "881001"
    assert fila["APELLIDO_ORIG"] == "García"
    assert fila["CUIT_ORIG"] == 27301112224
    assert fila["MONTO_ORIG"] == "78000.00"
    assert fila["LOCALIDAD"] == persona.municipio.nombre
    assert fila["PROV_ORIG"] == persona.provincia.nombre
    circuito = PasCircuitoMensual.objects.get()
    assert circuito.fecha_exportacion_sintys is not None
    assert circuito.exportado_por.username == "cruces_edita"
    assert circuito.archivo_exportacion_sintys.name.endswith(".xlsx")
    assert PasCircuitoMensual.objects.count() == 1
    assert editor.get(ROOT).json()["etapas"][0]["completada"] is True


def test_import_stores_the_file_and_completes_stage_two(editor, tmp_path):
    archivo = SimpleUploadedFile(
        "retorno-sintys.txt",
        b"ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO\n"
        b"1|GARCIA|MARIA|30111222|27301112224|COMPATIBLE|\n",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = editor.post(IMPORTAR, {"archivo": archivo})

    assert respuesta.status_code == 200
    assert respuesta.json()["message"].startswith(
        "Retorno SINTyS procesado: 1 registros"
    )
    assert respuesta.json()["resumen"]["compatibles"] == 1
    circuito = PasCircuitoMensual.objects.get()
    assert circuito.fecha_importacion_sintys is not None
    assert circuito.importado_por.username == "cruces_edita"
    assert circuito.archivo_retorno_sintys.name.endswith(".txt")
    assert circuito.fecha_exportacion_sintys is None
    assert editor.get(ROOT).json()["etapas"][1]["completada"] is True


@pytest.mark.parametrize(
    ("nombre", "contenido", "texto"),
    [
        ("retorno.pdf", b"%PDF", "El retorno debe ser un archivo TXT, CSV o XLSX."),
        (
            "retorno.csv",
            b"0" * (10 * 1024 * 1024 + 1),
            "El archivo no puede superar los 10 MB.",
        ),
    ],
)
def test_import_rejects_with_the_exact_native_text_and_changes_nothing(
    editor, nombre, contenido, texto
):
    respuesta = editor.post(
        IMPORTAR, {"archivo": SimpleUploadedFile(nombre, contenido)}
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {
        "message": f"No se pudo importar el retorno: {texto}",
        "errors": {"archivo": [texto]},
    }
    assert not PasCircuitoMensual.objects.exists()


def test_import_without_file_is_the_native_required_error(editor):
    respuesta = editor.post(IMPORTAR, {})

    assert respuesta.status_code == 400
    assert respuesta.json()["message"].startswith("No se pudo importar el retorno: ")
    assert list(respuesta.json()["errors"]) == ["archivo"]
    assert not PasCircuitoMensual.objects.exists()


def test_renaper_update_registers_the_run_once_per_period(editor):
    primero = editor.post(RENAPER)
    segundo = editor.post(RENAPER)

    assert primero.status_code == segundo.status_code == 200
    run = PasSupervivenciaRun.objects.get()
    assert (
        primero.json()
        == segundo.json()
        == {
            "run_id": run.pk,
            "message": (
                f"Control mensual #{run.pk} registrado. "
                "Consulte el avance en esta pantalla."
            ),
        }
    )
    assert run.requested_by.username == "cruces_edita"
    assert not PasControlRenaper.objects.exists()
