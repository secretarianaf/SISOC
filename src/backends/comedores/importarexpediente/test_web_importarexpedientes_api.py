"""Web API (G1 v1) of the payment-file imports (EX02.02 and EX02.01).

``/api/web/comedores/importarexpedientes/`` runs the native views of
``importarexpediente.views``. The tests pin today's access on purpose (list and
detail need the view code and no scope; upload, import and delete need only a
session; the accreditation dates need one of two change codes) and the native
effects: the period completion written on GET, the validation counters, the
physical delete that leaves the states untouched.
"""

from datetime import date
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from openpyxl import Workbook

from comedores.models import Comedor
from expedientespagos.models import ExpedientePago
from importarexpediente.models import (
    ArchivosImportados,
    ErroresImportacion,
    ExitoImportacion,
    RegistroImportado,
)

ROOT = "/api/web/comedores/importarexpedientes/"
NATIVO = "/importarexpedientes/"
VIEW = ("importarexpediente", "view_archivosimportados")
CHANGE = ("importarexpediente", "change_archivosimportados")
CABECERA = (
    "ID;COMEDOR;ORGANIZACION;EXPEDIENTE del CONVENIO;Expediente de Pago;"
    "Prestaciones Mensuales Desayuno;Prestaciones Mensuales Almuerzo;"
    "Prestaciones Mensuales Merienda;Prestaciones Mensuales Cena;"
    "Monto Mensuales Desayuno;Monto Mensuales Almuerzo;"
    "Monto Mensuales Merienda;Monto Mensuales Cena;Total Prestaciones;"
    "Gastos Accesorios 6%;TOTAL;Mes de Pago;Año"
)
VALORES = (
    "150;0;0;750;$ 57.450,00;$ 0,00;$ 0,00;$ 572.250,00;$ 594.000,00;"
    "$ 35.700,00;$ 629.700,00;septiembre;2025"
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True, name="media")
def media_fixture(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir()
    return settings.MEDIA_ROOT


def _usuario(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for app, codename in codes:
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_lotes", VIEW)


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


@pytest.fixture(name="sesion")
def sesion_fixture(lector):
    """The operator: the view code only lets it read back the queued messages."""
    return _client(lector)


@pytest.fixture(name="sin_codigos")
def sin_codigos_fixture():
    """A session without any permission: enough for upload and import."""
    return _client(_usuario("solo_sesion_lotes"))


@pytest.fixture(name="gestor")
def gestor_fixture():
    """The two codes of ``PERMISOS_GESTION_LOTE``: undo and delete a batch."""
    return _client(_usuario("gestor_lotes", VIEW, CHANGE))


def _csv(comedor, expediente="EX-PAGO-1", filas=1, extra=""):
    lineas = [
        f"{comedor.pk};Comedor;Org;EX-CONV-1;{expediente}-{n};{VALORES}{extra}"
        for n in range(filas)
    ]
    return "\n".join([CABECERA, *lineas]) + "\n"


def _archivo(nombre, contenido):
    return SimpleUploadedFile(nombre, contenido.encode("utf-8"), "text/csv")


def _subir(client, contenido, nombre="lote.csv", **extra):
    datos = {"file": _archivo(nombre, contenido), "delimiter": ";", "has_header": True}
    datos.update(extra)
    return client.post(f"{ROOT}subir/", datos)


def _lote(usuario, nombre="lote.csv", contenido="ID\n1\n", **extra):
    return ArchivosImportados.objects.create(
        archivo=SimpleUploadedFile(nombre, contenido.encode("utf-8")),
        usuario=usuario,
        **extra,
    )


def _xlsx_acreditacion(filas):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["ID", "Fecha de Acreditación"])
    for fila in filas:
        hoja.append(fila)
    salida = BytesIO()
    libro.save(salida)
    return SimpleUploadedFile("acreditaciones.xlsx", salida.getvalue())


def _niveles(data):
    return [(m["level"], m["message"]) for m in data["messages"]]


# --- EX02.02 list ------------------------------------------------------------


def test_list_projects_the_native_rows_and_options(web, lector):
    otro = _usuario("otro_lotes")
    lote = _lote(
        otro,
        numero_expediente_pago="EX-9",
        mes_pago="marzo",
        ano_pago="2026",
        count_exitos=3,
        count_errores=1,
    )
    sin_datos = _lote(lector, nombre="b.csv", importacion_completada=True)

    respuesta = web.get(ROOT)

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert [r["id"] for r in data["results"]] == [sin_datos.pk, lote.pk]
    fila = data["results"][1]
    assert fila["numero_expediente_pago"] == "EX-9"
    assert fila["archivo"] == lote.archivo.name
    assert fila["periodo_pago"] == "03/2026"
    assert fila["usuario"] == "otro_lotes"
    assert (fila["count_exitos"], fila["count_errores"]) == ("3", "1")
    assert fila["importacion_completada"] == "No"
    assert fila["detail_url"] == f"{NATIVO}{lote.pk}/"
    assert fila["download_url"] == f"{NATIVO}{lote.pk}/descargar/"
    assert data["results"][0]["importacion_completada"] == "Si"
    assert data["results"][0]["numero_expediente_pago"] == "Sin informacion"
    assert data["urls"] == {
        "list": f"{NATIVO}listar",
        "upload": f"{NATIVO}upload",
    }
    assert [f["name"] for f in data["filters_config"]["fields"]][:3] == [
        "archivo",
        "usuario",
        "numero_expediente_pago",
    ]
    assert data["page"]["count"] == 2
    assert data["messages"] == []


def test_list_access_is_the_view_code_without_scope(client, sin_codigos, web):
    otro = _usuario("dueno_lotes")
    _lote(otro)
    assert client.get(ROOT).status_code == 401
    assert sin_codigos.get(ROOT).status_code == 403
    assert sin_codigos.get(f"{NATIVO}listar").status_code == 403
    assert len(web.get(ROOT).json()["results"]) == 1
    assert web.get(f"{NATIVO}listar").status_code == 200


def test_list_filters_and_search_use_the_native_engine(web, lector):
    ana = _usuario("ana_lotes")
    uno = _lote(ana, nombre="uno.csv", numero_expediente_pago="EX-A", count_errores=5)
    dos = _lote(
        lector, nombre="dos.csv", numero_expediente_pago="EX-B", count_errores=0
    )

    def ids(**params):
        return [r["id"] for r in web.get(ROOT, params).json()["results"]]

    assert ids(busqueda="ana_lotes") == [uno.pk]
    assert ids(busqueda="dos.csv") == [dos.pk]
    filtro = '{"logic": "AND", "items": [{"field": "count_errores", "op": "gt", "value": "1"}]}'
    assert ids(filters=filtro) == [uno.pk]
    filtro = '{"logic": "AND", "items": [{"field": "numero_expediente_pago", "op": "eq", "value": "EX-B"}]}'
    assert ids(filters=filtro) == [dos.pk]
    assert ids(filters=filtro, busqueda="uno") == []


def test_list_pages_by_ten_and_an_invalid_page_is_404(web, lector):
    for n in range(11):
        _lote(lector, nombre=f"l{n}.csv")

    primera = web.get(ROOT).json()
    segunda = web.get(ROOT, {"page": "2"}).json()

    assert len(primera["results"]) == 10 and len(segunda["results"]) == 1
    assert primera["page"]["next"] == 2 and segunda["page"]["previous"] == 1
    assert web.get(ROOT, {"page": "3"}).status_code == 404
    assert web.get(f"{NATIVO}listar", {"page": "3"}).status_code == 404


def test_list_completes_and_persists_the_missing_period(web, lector):
    lote = _lote(
        lector,
        nombre="periodo.csv",
        contenido=f"{CABECERA}\n1;C;Org;EC;EX-1;{VALORES}\n",
        delimiter=";",
    )
    assert lote.mes_pago is None

    fila = web.get(ROOT).json()["results"][0]

    lote.refresh_from_db()
    assert (lote.mes_pago, lote.ano_pago) == ("septiembre", "2025")
    assert fila["periodo_pago"] == "09/2025"


# --- EX02.02 detail ----------------------------------------------------------


def _con_errores(usuario, n=25, **extra):
    lote = _lote(usuario, count_errores=n, count_exitos=2, **extra)
    for fila in range(1, n + 1):
        ErroresImportacion.objects.create(
            archivo_importado=lote, fila=fila, mensaje=f"Fila {fila} mal"
        )
    ExitoImportacion.objects.create(archivo_importado=lote, fila=99)
    ExitoImportacion.objects.create(archivo_importado=lote, fila=100)
    return lote


def test_detail_projects_counters_and_the_error_page(web, lector):
    lote = _con_errores(lector)

    data = web.get(f"{ROOT}{lote.pk}/").json()

    assert data["batch"] == {
        "id": lote.pk,
        "label": str(lote),
        "importacion_completada": False,
    }
    assert data["counts"] == {"validos": 2, "errores": 25, "con_acreditacion": 0}
    assert [r["fila"] for r in data["results"]] == [str(n) for n in range(1, 21)]
    assert data["results"][0]["mensaje"] == "Fila 1 mal"
    assert data["results"][0]["archivo"] == str(lote)
    assert data["page"]["num_pages"] == 2
    assert data["urls"]["list"] == f"{NATIVO}listar"
    assert [
        r["fila"] for r in web.get(f"{ROOT}{lote.pk}/", {"page": 2}).json()["results"]
    ] == [str(n) for n in range(21, 26)]


def test_detail_search_by_row_or_text_and_invalid_page(web, lector):
    lote = _con_errores(lector, n=12)

    assert [
        r["fila"]
        for r in web.get(f"{ROOT}{lote.pk}/", {"busqueda": "7"}).json()["results"]
    ] == ["7"]
    assert (
        len(web.get(f"{ROOT}{lote.pk}/", {"busqueda": "mal"}).json()["results"]) == 12
    )
    assert web.get(f"{ROOT}{lote.pk}/", {"busqueda": "zzz"}).json()["results"] == []
    assert web.get(f"{ROOT}{lote.pk}/", {"page": 9}).status_code == 404
    assert web.get(f"{NATIVO}{lote.pk}/", {"page": 9}).status_code == 404


def test_detail_access_other_users_batch_and_missing_batch(client, sin_codigos, web):
    lote = _lote(_usuario("ajeno_lotes"))

    assert client.get(f"{ROOT}{lote.pk}/").status_code == 401
    assert sin_codigos.get(f"{ROOT}{lote.pk}/").status_code == 403
    assert web.get(f"{ROOT}{lote.pk}/").status_code == 200
    assert web.get(f"{ROOT}999999/").status_code == 404
    assert web.get(f"{NATIVO}999999/").status_code == 404


def test_can_update_acreditacion_needs_a_completed_batch_and_a_code(client, lector):
    pendiente = _lote(lector)
    completo = _lote(lector, nombre="c.csv", importacion_completada=True)
    cambia = _client(_usuario("cambia_lotes", VIEW, CHANGE))

    def puede(cliente, lote):
        return cliente.get(f"{ROOT}{lote.pk}/").json()["can_update_acreditacion"]

    assert puede(cambia, pendiente) is False
    assert puede(cambia, completo) is True
    assert puede(_client(lector), completo) is False


def test_detail_manage_flags_follow_the_native_buttons(lector):
    pendiente = _lote(lector)
    antiguo = _lote(lector, nombre="c.csv", importacion_completada=True)
    cambia = _client(_usuario("gestiona_lotes", VIEW, CHANGE))

    datos = cambia.get(f"{ROOT}{pendiente.pk}/").json()
    assert datos["can_manage"] is True
    assert datos["motivo_no_deshacer"] is None
    # Imported before the undo existed: the native page explains why.
    datos = cambia.get(f"{ROOT}{antiguo.pk}/").json()
    assert datos["motivo_no_deshacer"].startswith("Este lote se importó antes")
    assert _client(lector).get(f"{ROOT}{pendiente.pk}/").json()["can_manage"] is False


def test_download_stays_native(web, lector):
    lote = _lote(lector, contenido="a;b\n")

    respuesta = web.get(f"{NATIVO}{lote.pk}/descargar/")

    assert respuesta.status_code == 200
    assert b"".join(respuesta.streaming_content) == b"a;b\n"


# --- EX02.01 upload ----------------------------------------------------------


def test_upload_form_fields_and_access(client, sin_codigos):
    assert client.get(f"{ROOT}subir/").status_code == 401

    data = sin_codigos.get(f"{ROOT}subir/").json()

    assert [(f["name"], f["type"], f["label"]) for f in data["fields"]] == [
        ("file", "file", "Archivo CSV o XLSX"),
        ("delimiter", "select", "Delimitador"),
        ("has_header", "checkbox", "Incluye cabecera"),
    ]
    assert data["fields"][0]["accept"] == ".csv,.xlsx"
    assert data["fields"][1]["choices"] == [
        {"value": ",", "label": "Coma (,)"},
        {"value": ";", "label": "Punto y coma (;)"},
    ]
    assert data["fields"][1]["value"] == ","
    assert data["fields"][2]["value"] is True


def test_upload_validates_without_writing_expedientes(sesion):
    comedor = Comedor.objects.create(nombre="Comedor lote")

    respuesta = _subir(sesion, _csv(comedor, filas=2))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}listar"}
    lote = ArchivosImportados.objects.get()
    assert (lote.count_exitos, lote.count_errores) == (2, 0)
    assert lote.numero_expediente_pago == "EX-PAGO-1-0"
    assert not ExpedientePago.objects.exists()
    assert not RegistroImportado.objects.exists()
    # The message waits for the list, like after the native 302.
    assert _niveles(sesion.get(ROOT).json()) == [("success", "2 filas válidas.")]


def test_upload_rejections_answer_400_with_native_messages_and_store_nothing(
    sesion, media
):
    comedor = Comedor.objects.create(nombre="Comedor rechazo")
    casos = {
        "mal.txt": (_csv(comedor), "La extensión de archivo"),
        "vacio.csv": ("", "El archivo enviado está vació."),
    }
    for nombre, (contenido, texto) in casos.items():
        respuesta = _subir(sesion, contenido, nombre=nombre)
        assert respuesta.status_code == 400, nombre
        mensajes = [m["message"] for m in respuesta.json()["messages"]]
        assert any(texto in m for m in mensajes), (nombre, mensajes)
        assert respuesta.json()["ok"] is False
    assert not ArchivosImportados.objects.exists()
    assert not list(media.glob("importados/*"))
    assert sesion.get(ROOT).json()["messages"] == []


def test_upload_without_header_is_rejected(sesion):
    respuesta = sesion.post(
        f"{ROOT}subir/",
        {"file": _archivo("x.csv", "1;2\n"), "delimiter": ";"},
    )

    assert respuesta.status_code == 400
    assert _niveles(respuesta.json()) == [
        ("error", "Archivo sin cabecera no soportado por defecto.")
    ]
    assert not ArchivosImportados.objects.exists()


def test_upload_duplicate_expediente_is_409_and_saves_no_file(sesion, media):
    comedor = Comedor.objects.create(nombre="Comedor dup")
    assert _subir(sesion, _csv(comedor)).status_code == 200
    sesion.get(ROOT)  # consume the success message
    antes = len(list(media.glob("importados/*")))

    respuesta = _subir(sesion, _csv(comedor), nombre="otra.csv")

    assert respuesta.status_code == 409
    assert _niveles(respuesta.json()) == [
        (
            "error",
            "No se puede adjuntar el archivo ya que el expediente de pago se "
            "encuentra cargado anteriormente",
        )
    ]
    assert ArchivosImportados.objects.count() == 1
    assert len(list(media.glob("importados/*"))) == antes


def test_upload_persists_every_row_error_and_shows_twenty(sesion):
    # A non numeric amount in each row is a specific error of the native parser.
    filas = "\n".join(
        f"x{n};Comedor;Org;EX-CONV;EX-ERR-{n};{VALORES}" for n in range(25)
    )

    respuesta = _subir(sesion, f"{CABECERA}\n{filas}\n")

    assert respuesta.status_code == 200
    lote = ArchivosImportados.objects.get()
    assert (
        lote.count_errores
        == ErroresImportacion.objects.filter(archivo_importado=lote).count()
    )
    assert lote.count_errores >= 25
    mensajes = sesion.get(ROOT).json()["messages"]
    errores = [m for m in mensajes if m["level"] == "error"]
    assert len(errores) == 20
    assert mensajes[-1]["level"] == "warning"
    assert mensajes[-1]["message"].startswith("Validación parcial: 0 filas válidas")


def test_upload_warns_when_the_delimiter_differs(sesion):
    comedor = Comedor.objects.create(nombre="Comedor delim")

    respuesta = _subir(sesion, _csv(comedor), delimiter=",")

    assert respuesta.status_code == 200
    textos = [m["message"] for m in sesion.get(ROOT).json()["messages"]]
    assert (
        "El delimitador seleccionado fue ',', pero el archivo parece usar ';'. "
        "Se usará ';'." in textos
    )
    assert ArchivosImportados.objects.get().delimiter == ";"


def test_upload_needs_multipart_csrf_and_a_session(client, sin_codigos):
    assert client.post(f"{ROOT}subir/").status_code == 401
    assert (
        sin_codigos.post(
            f"{ROOT}subir/", {"file": "x"}, content_type="application/json"
        ).status_code
        == 415
    )
    estricto = _client(_usuario("csrf_lotes"), enforce_csrf_checks=True)
    assert estricto.post(f"{ROOT}subir/", {"delimiter": ";"}).status_code == 403
    assert not ArchivosImportados.objects.exists()


# --- EX02.01 import and delete -----------------------------------------------


def _lote_subido(client, comedor, **kwargs):
    assert _subir(client, _csv(comedor, **kwargs)).status_code == 200
    client.get(ROOT)  # consume the validation message
    return ArchivosImportados.objects.latest("id")


def test_import_creates_the_expedientes_the_records_and_the_flag(sesion):
    comedor = Comedor.objects.create(nombre="Comedor import")
    lote = _lote_subido(sesion, comedor, filas=2)

    respuesta = sesion.post(f"{ROOT}{lote.pk}/importar/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}listar"}
    lote.refresh_from_db()
    assert lote.importacion_completada is True
    assert ExpedientePago.objects.count() == 2
    assert RegistroImportado.objects.count() == 2
    assert _niveles(sesion.get(ROOT).json()) == [
        (
            "success",
            "Importación completada: 2 registros importados. Estados actualizados: 0.",
        )
    ]


def test_second_import_is_409_and_changes_nothing(sesion):
    comedor = Comedor.objects.create(nombre="Comedor doble")
    lote = _lote_subido(sesion, comedor)
    assert sesion.post(f"{ROOT}{lote.pk}/importar/").status_code == 200
    sesion.get(ROOT)

    respuesta = sesion.post(f"{ROOT}{lote.pk}/importar/")

    assert respuesta.status_code == 409
    assert respuesta.json()["redirect"] == f"{NATIVO}listar"
    assert ExpedientePago.objects.count() == 1
    assert RegistroImportado.objects.count() == 1
    assert _niveles(sesion.get(ROOT).json()) == [
        (
            "warning",
            "Este archivo ya fue importado. Primero borre los datos importados "
            "para reintentar.",
        )
    ]


def test_import_of_a_missing_batch_is_404_and_get_is_not_allowed(sin_codigos, client):
    assert sin_codigos.post(f"{ROOT}999999/importar/").status_code == 404
    assert client.post(f"{ROOT}1/importar/").status_code == 401
    assert sin_codigos.get(f"{ROOT}1/importar/").status_code == 405
    assert sin_codigos.get(f"{NATIVO}1/importar_datos/").status_code == 405


def test_a_session_without_codes_can_upload_and_import_but_not_undo(sin_codigos):
    comedor = Comedor.objects.create(nombre="Comedor sin codigos")
    assert _subir(sin_codigos, _csv(comedor)).status_code == 200
    lote = ArchivosImportados.objects.get()

    assert sin_codigos.post(f"{ROOT}{lote.pk}/importar/").status_code == 200
    assert ExpedientePago.objects.count() == 1
    # Same codes as the native route (``PERMISOS_GESTION_LOTE``).
    assert sin_codigos.post(f"{ROOT}{lote.pk}/borrar-datos/").status_code == 403
    assert sin_codigos.post(f"{ROOT}{lote.pk}/eliminar/").status_code == 403
    assert (
        sin_codigos.post(f"{NATIVO}{lote.pk}/borrar_datos_importados/").status_code
        == 403
    )
    assert ExpedientePago.objects.count() == 1


def test_undo_removes_records_and_expedientes_physically(gestor):
    comedor = Comedor.objects.create(nombre="Comedor borrar")
    lote = _lote_subido(gestor, comedor, filas=2)
    gestor.post(f"{ROOT}{lote.pk}/importar/")
    gestor.get(ROOT)
    ExpedientePago.objects.first().delete()  # logical delete: still removed

    respuesta = gestor.post(f"{ROOT}{lote.pk}/borrar-datos/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}{lote.pk}/"}
    lote.refresh_from_db()
    assert lote.importacion_completada is False
    assert not RegistroImportado.objects.exists()
    assert not ExpedientePago.all_objects.exists()
    # The batch, its file and its validation rows stay.
    assert ExitoImportacion.objects.filter(archivo_importado=lote).count() == 2
    assert _niveles(gestor.get(ROOT).json()) == [
        (
            "success",
            "Importación deshecha: 2 expedientes eliminados y 0 comedores "
            "volvieron a su estado anterior.",
        )
    ]


def test_repeated_undo_is_rejected(gestor):
    comedor = Comedor.objects.create(nombre="Comedor repetido")
    lote = _lote_subido(gestor, comedor)
    gestor.post(f"{ROOT}{lote.pk}/importar/")
    gestor.post(f"{ROOT}{lote.pk}/borrar-datos/")
    gestor.get(ROOT)

    assert gestor.post(f"{ROOT}{lote.pk}/borrar-datos/").status_code == 409

    assert _niveles(gestor.get(ROOT).json()) == [
        ("error", "Este lote todavía no fue importado.")
    ]
    assert gestor.post(f"{ROOT}999999/borrar-datos/").status_code == 404
    assert gestor.get(f"{ROOT}1/borrar-datos/").status_code == 405


def test_delete_of_a_pending_batch_and_rejection_of_an_imported_one(gestor):
    comedor = Comedor.objects.create(nombre="Comedor eliminar")
    importado = _lote_subido(gestor, comedor)
    gestor.post(f"{ROOT}{importado.pk}/importar/")
    gestor.get(ROOT)

    assert gestor.post(f"{ROOT}{importado.pk}/eliminar/").status_code == 409
    assert _niveles(gestor.get(ROOT).json())[0][0] == "error"
    assert ArchivosImportados.objects.filter(pk=importado.pk).exists()

    pendiente = _lote_subido(gestor, comedor, expediente="EX-PAGO-2")
    gestor.get(ROOT)
    respuesta = gestor.post(f"{ROOT}{pendiente.pk}/eliminar/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}listar"}
    assert not ArchivosImportados.objects.filter(pk=pendiente.pk).exists()
    assert _niveles(gestor.get(ROOT).json())[0][0] == "success"
    assert gestor.post(f"{ROOT}999999/eliminar/").status_code == 404
    assert gestor.get(f"{ROOT}1/eliminar/").status_code == 405


def test_mutations_need_csrf(sesion):
    comedor = Comedor.objects.create(nombre="Comedor csrf")
    lote = _lote_subido(sesion, comedor)
    estricto = _client(_usuario("csrf_import"), enforce_csrf_checks=True)

    assert estricto.post(f"{ROOT}{lote.pk}/importar/").status_code == 403
    assert estricto.post(f"{ROOT}{lote.pk}/borrar-datos/").status_code == 403
    lote.refresh_from_db()
    assert lote.importacion_completada is False
    assert not ExpedientePago.objects.exists()


# --- EX02.01 accreditation dates ---------------------------------------------


@pytest.fixture(name="cambia")
def cambia_fixture():
    return _client(_usuario("cambia_fechas", VIEW, CHANGE))


def _lote_importado(client, comedor):
    lote = _lote_subido(client, comedor)
    client.post(f"{ROOT}{lote.pk}/importar/")
    client.get(ROOT)
    return lote


def test_dates_access_needs_one_change_code(client, sin_codigos, cambia, web):
    lote = _lote(_usuario("duenio_fechas"))
    url = f"{ROOT}{lote.pk}/fechas-acreditacion/"

    assert client.get(url).status_code == 401
    assert sin_codigos.get(url).status_code == 403
    assert web.get(url).status_code == 403
    assert sin_codigos.post(url, {"file": _xlsx_acreditacion([])}).status_code == 403
    assert cambia.get(url).status_code == 200
    assert cambia.get(f"{ROOT}999999/fechas-acreditacion/").status_code == 404
    assert sin_codigos.get(f"{NATIVO}{lote.pk}/fechas-acreditacion/").status_code == 403
    assert (
        _client(_usuario("exp_fechas", ("expedientespagos", "change_expedientepago")))
        .get(url)
        .status_code
        == 200
    )


def test_dates_form_describes_the_native_form(cambia):
    lote = _lote(_usuario("duenio_form"))

    data = cambia.get(f"{ROOT}{lote.pk}/fechas-acreditacion/").json()

    assert data["batch"] == {"id": lote.pk, "label": str(lote)}
    assert [(f["name"], f["type"], f["label"]) for f in data["fields"]] == [
        ("file", "file", "Archivo CSV o XLSX")
    ]


def test_dates_update_only_the_expedientes_of_the_batch(sesion, cambia):
    comedor = Comedor.objects.create(nombre="Comedor fechas")
    otro = Comedor.objects.create(nombre="Comedor fuera")
    lote = _lote_importado(sesion, comedor)
    ajeno = ExpedientePago.objects.create(
        comedor=otro,
        expediente_convenio="X",
        **{
            f"prestaciones_mensuales_{c}": 1
            for c in ("desayuno", "almuerzo", "merienda", "cena")
        },
        **{
            f"monto_mensual_{c}": 1
            for c in ("desayuno", "almuerzo", "merienda", "cena")
        },
    )

    respuesta = cambia.post(
        f"{ROOT}{lote.pk}/fechas-acreditacion/",
        {"file": _xlsx_acreditacion([[comedor.pk, "20/02/2025"]])},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"{NATIVO}listar"}
    assert ExpedientePago.objects.get(comedor=comedor).fecha_acreditacion == date(
        2025, 2, 20
    )
    ajeno.refresh_from_db()
    assert ajeno.fecha_acreditacion is None
    assert _niveles(cambia.get(ROOT).json()) == [
        (
            "success",
            "Fechas de acreditación actualizadas: 1 expedientes de 1 comedores.",
        )
    ]


def test_dates_rejections_return_the_messages_and_change_nothing(sesion, cambia):
    comedor = Comedor.objects.create(nombre="Comedor fechas malas")
    lote = _lote_importado(sesion, comedor)
    url = f"{ROOT}{lote.pk}/fechas-acreditacion/"
    casos = {
        "Fila 2: Fecha de acreditación debe tener formato DD/MM/AAAA.": [
            [comedor.pk, "hola"]
        ],
        "Fila 2: ID debe ser numérico.": [["abc", "20/02/2025"]],
        "No se encontraron fechas de acreditación para procesar.": [],
        "El archivo debe informar una única fecha de acreditación para el lote.": [
            [comedor.pk, "20/02/2025"],
            [comedor.pk + 1, "21/02/2025"],
        ],
    }
    for texto, filas in casos.items():
        respuesta = cambia.post(url, {"file": _xlsx_acreditacion(filas)})
        assert respuesta.status_code == 400, texto
        assert respuesta.json()["ok"] is False
        assert texto in [m["message"] for m in respuesta.json()["messages"]], texto
    assert ExpedientePago.objects.get(comedor=comedor).fecha_acreditacion is None
    assert cambia.get(ROOT).json()["messages"] == []


def test_dates_need_a_completed_batch_and_multipart(sesion, cambia):
    pendiente = _lote_subido(sesion, Comedor.objects.create(nombre="Comedor pend"))
    url = f"{ROOT}{pendiente.pk}/fechas-acreditacion/"

    respuesta = cambia.post(url, {"file": _xlsx_acreditacion([[1, "20/02/2025"]])})

    assert respuesta.status_code == 400
    assert "Primero se debe completar la importación del lote." in [
        m["message"] for m in respuesta.json()["messages"]
    ]
    assert (
        cambia.post(url, {"file": "x"}, content_type="application/json").status_code
        == 415
    )
