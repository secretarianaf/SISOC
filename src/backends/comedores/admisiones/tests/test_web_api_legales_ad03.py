"""Web API of the legal admision detail and its actions (AD03.03).

Every action runs the native ``LegalesService`` handler: each test pins the persisted effect,
that a rejection leaves the admision unchanged and the HTTP contract (400 bound form, 403,
404, 409) added by the API.
"""

import shutil
import subprocess
import types
from zipfile import ZipFile

from docx import Document

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from core.models import Localidad, Municipio, Provincia

from admisiones.models.admisiones import (
    Admision,
    AdmisionHistorial,
    FormularioProyectoDeConvenio,
    HistorialEstadosAdmision,
    InformeComplementario,
    InformeComplementarioCampos,
    EstadoAdmision,
    InformeTecnico,
    Providencia,
)
from admisiones.web_preview_legales import legales_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/admisiones/legales/"
PERMISOS = (
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
    "expedientespagos.view_expedientepago",
)
EXPEDIENTE = {
    "expediente_anio": "2026",
    "expediente_numero": "000000123",
    "expediente_reparticion": "dgd",
    "expediente_organismo": "mch",
}
EXPEDIENTE_FINAL = "EX-2026-000000123- -APN-DGD#MCH"
PV = {
    "pv_anio": "2026",
    "pv_numero": "77",
    "pv_reparticion": "dps",
    "pv_organismo": "mch",
}
PV_FINAL = "PV-2026-77-APN-DPS#MCH"

pytestmark = pytest.mark.django_db


def _usuario(nombre, permiso=None, superuser=False):
    usuario = get_user_model().objects.create_user(nombre)
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    if permiso:
        app, codigo = permiso.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codigo)
        )
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    return usuario


def _cliente(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="root")
def root_fixture():
    return _usuario("root_legal", superuser=True)


@pytest.fixture(name="web")
def web_fixture(root):
    return _cliente(root)


def _admision(**campos):
    comedor = Comedor.objects.create(nombre="Comedor Legal AD03")
    datos = {
        "comedor": comedor,
        "tipo": "incorporacion",
        "enviado_legales": True,
        "estado_legales": "Enviado a Legales",
    }
    datos.update(campos)
    return Admision.objects.create(**datos)


def _campos(admision, *nombres):
    admision.refresh_from_db()
    return tuple(getattr(admision, nombre) for nombre in nombres)


def _accion(web, admision, accion, datos=None, **extra):
    return web.post(f"{API}{admision.pk}/acciones/{accion}/", datos or {}, **extra)


def _niveles(respuesta):
    return [(m["level"], m["message"]) for m in respuesta.json()["messages"]]


def _flash(web, admision):
    """The messages the native redirect leaves queued for the detail page."""
    pagina = web.get(f"{API}{admision.pk}/").json()
    return [(m["level"], m["message"]) for m in pagina["messages"]]


# ---- read ----------------------------------------------------------------------------


def test_detail_projects_the_native_context(web):
    admision = _admision(estado_legales="Expediente Agregado", legales_num_if="EX-1")

    datos = web.get(f"{API}{admision.pk}/").json()

    assert datos["id"] == admision.pk
    assert datos["titulo"]["estado"] == "Expediente Agregado"
    assert datos["expediente"]["numero"] == "EX-1"
    assert [b["key"] for b in datos["botones"]] == ["formulario_convenio"]
    assert datos["botones"][0]["modal"] == "modalFormConvenio"
    assert datos["comedor"]["nombre"] == "Comedor Legal AD03"
    assert set(datos["forms"]) >= {"rectificar", "numero_expediente", "convenio"}
    nombres = [f["name"] for f in datos["forms"]["numero_expediente"]["fields"]]
    assert nombres == [
        "expediente_anio",
        "expediente_numero",
        "expediente_reparticion",
        "expediente_organismo",
    ]
    archivo = datos["forms"]["convenio"]["fields"][1]
    assert (archivo["name"], archivo["kind"]) == ("archivo_convenio", "file")


def test_detail_pages_the_state_history_like_the_native_page(web):
    admision = _admision()
    for numero in range(12):
        HistorialEstadosAdmision.objects.create(
            admision=admision,
            estado_anterior="iniciada",
            estado_nuevo=f"estado_{numero}",
        )

    datos = web.get(f"{API}{admision.pk}/?historial_estados_page=2").json()

    historial = datos["historial_estados"]
    assert [h["title"] for h in historial["headers"]] == [
        "Fecha",
        "Estado anterior",
        "Estado nuevo",
        "Usuario",
    ]
    assert historial["page"]["number"] == 2
    assert historial["page"]["param"] == "historial_estados_page"
    assert len(historial["rows"]) == historial["page"]["count"] - 10 > 0


def test_detail_access_matches_the_native_guard():
    admision = _admision()
    url = f"{API}{admision.pk}/"

    assert Client().get(url).status_code == 401
    sin_permiso = _cliente(_usuario("sin_permiso_legal"))
    assert sin_permiso.get(url).status_code == 403
    for permiso in PERMISOS:
        # Kept gap: any read permission sees any admision (global primary key).
        cliente = _cliente(_usuario(f"u_{permiso.split('.')[1]}", permiso))
        assert cliente.get(url).status_code == 200
    assert (
        _cliente(_usuario("root_404", superuser=True)).get(f"{API}999999/").status_code
        == 404
    )


def test_review_page_is_served_with_its_pending_report(web):
    admision = _admision(estado_legales="Informe Complementario Enviado")
    informe = _informe_complementario(admision)
    InformeComplementarioCampos.objects.create(
        campo="plazo", value="12", informe_complementario=informe
    )

    datos = web.get(f"{API}{admision.pk}/complementario/revision/").json()

    assert datos["informe"]["campos"] == [{"campo": "plazo", "value": "12"}]
    assert datos["informe"]["estado"] == "Enviado a Validación"
    sin_informe = _admision()
    assert (
        web.get(f"{API}{sin_informe.pk}/complementario/revision/").json()["informe"]
        is None
    )


# ---- contract of the action endpoint ------------------------------------------------------


def test_actions_need_session_csrf_permission_and_a_known_target(root):
    admision = _admision()
    url = f"{API}{admision.pk}/acciones/rectificar/"

    assert Client().post(url, {}).status_code == 401
    assert _cliente(_usuario("sin_perm_post")).post(url, {}).status_code == 403
    csrf = _cliente(root, enforce_csrf_checks=True)
    assert csrf.post(url, {"observaciones": "x"}).status_code == 403
    web = _cliente(root)
    assert _accion(web, admision, "inexistente").status_code == 404
    assert web.post(f"{API}999999/acciones/rectificar/", {}).status_code == 404
    assert web.get(url).status_code == 405
    assert _campos(admision, "estado_legales", "observaciones") == (
        "Enviado a Legales",
        None,
    )


def test_an_action_never_runs_another_one_named_in_the_body(web):
    admision = _admision(
        estado_legales="Juridicos: Rechazado", rechazo_juridicos_motivo="providencia"
    )

    respuesta = _accion(
        web,
        admision,
        "reinicio-expediente",
        {
            "observaciones_reinicio_expediente": "Reinicio total",
            "btnLegalesNumIF": "1",
            **EXPEDIENTE,
        },
    )

    assert respuesta.status_code == 200
    assert _campos(
        admision, "legales_num_if", "enviada_a_archivo", "estado_legales"
    ) == (
        None,
        True,
        "Archivado",
    )


# ---- AD03.03 actions ---------------------------------------------------------------------


def test_rectificar_persists_and_rejection_changes_nothing(web):
    # The native handler moves the admision to the state registered with this key.
    estado = EstadoAdmision.objects.create(id=3, nombre="Rectificar")
    admision = _admision()

    rechazo = _accion(web, admision, "rectificar", {"observaciones": ""})

    assert rechazo.status_code == 200
    assert ("error", "Error al enviar a rectificar.") in _niveles(rechazo)
    assert _campos(admision, "estado_legales", "observaciones", "estado_id") == (
        "Enviado a Legales",
        None,
        admision.estado_id,
    )
    ok = _accion(web, admision, "rectificar", {"observaciones": "Falta nota"})
    assert ("success", "Enviado a rectificar con éxito.") in _niveles(ok)
    assert ok.json()["estado_legales"] == "A Rectificar"
    assert _campos(admision, "estado_legales", "observaciones", "estado_id") == (
        "A Rectificar",
        "Falta nota",
        estado.pk,
    )


def test_numero_expediente_saves_and_an_invalid_form_answers_400(web):
    admision = _admision()
    otra = _admision(num_expediente=EXPEDIENTE_FINAL)

    duplicado = _accion(web, admision, "numero-expediente", EXPEDIENTE)
    assert duplicado.status_code == 400
    cuerpo = duplicado.json()
    assert cuerpo["modal"] == "modalLegalesNumIF"
    assert cuerpo["non_field_errors"][0].startswith("El expediente ya pertenece")
    corto = _accion(
        web, admision, "numero-expediente", {**EXPEDIENTE, "expediente_anio": "20"}
    )
    assert corto.status_code == 400
    anio = next(f for f in corto.json()["fields"] if f["name"] == "expediente_anio")
    assert anio["errors"]
    assert _campos(admision, "legales_num_if", "estado_legales") == (
        None,
        "Enviado a Legales",
    )

    otra.delete()
    ok = _accion(web, admision, "numero-expediente", EXPEDIENTE)

    assert ok.status_code == 200
    assert ("success", "Número de IF guardado correctamente.") in _niveles(ok)
    assert _campos(admision, "legales_num_if", "num_expediente", "estado_legales") == (
        EXPEDIENTE_FINAL,
        EXPEDIENTE_FINAL,
        "Expediente Agregado",
    )


def test_actions_record_the_history_with_the_acting_user(root, web):
    admision = _admision()

    _accion(web, admision, "numero-expediente", EXPEDIENTE)

    assert AdmisionHistorial.objects.filter(admision=admision, usuario=root).exists()


def test_if_proyecto_convenio_saves_the_number(web):
    admision = _admision(estado_legales="Formulario Convenio Creado")
    formulario = FormularioProyectoDeConvenio.objects.create(admision=admision)

    vacio = _accion(web, admision, "if-proyecto-convenio", {"numero_if": ""})
    assert (
        "error",
        "Error al guardar el número IF de Proyecto de Convenio.",
    ) in _niveles(vacio)
    formulario.refresh_from_db()
    assert formulario.numero_if is None

    ok = _accion(web, admision, "if-proyecto-convenio", {"numero_if": "IF-2026-1"})

    assert (
        "success",
        "Número IF de Proyecto de Convenio guardado correctamente.",
    ) in _niveles(ok)
    formulario.refresh_from_db()
    assert formulario.numero_if == "IF-2026-1"
    assert _campos(admision, "estado_legales") == ("IF Convenio Asignado",)


@pytest.fixture
def proyecto_datos():
    provincia = Provincia.objects.create(nombre="Provincia firmante")
    municipio = Municipio.objects.create(
        nombre="Municipio firmante", provincia=provincia
    )
    localidad = Localidad.objects.create(
        nombre="Localidad firmante", municipio=municipio
    )
    return {
        "cantidad_espacios": "hasta_5",
        "autoridad_nombre": "Autoridad & Asociación",
        "autoridad_cargo": "Secretaria",
        "autoridad_dni": "12345678",
        "autoridad_domicilio": "Calle Ficticia 123",
        "autoridad_provincia": provincia.pk,
        "autoridad_localidad": localidad.pk,
    }


def _informe_proyecto(admision, estado="Validado"):
    return InformeTecnico.objects.create(
        admision=admision,
        tipo="base",
        estado=estado,
        expediente_nro="EX-1",
        representante_nombre="Autoridad del informe",
        representante_cargo="Presidente",
        representante_dni="87654321",
        aprobadas_almuerzo_lunes=42,
    )


@pytest.mark.parametrize("tipo", ["incorporacion", "renovacion"])
@pytest.mark.parametrize("judicializado", [False, True])
@pytest.mark.parametrize("espacios", ["hasta_5", "mas_de_5"])
def test_proyecto_convenio_genera_word_y_pdf(
    web, admision_media, proyecto_datos, mocker, tipo, judicializado, espacios
):
    admision = _admision(tipo=tipo, estado_legales="Expediente Agregado")
    admision.comedor.es_judicializado = judicializado
    admision.comedor.save(update_fields=["es_judicializado"])
    informe = _informe_proyecto(
        admision, estado="Para revision" if judicializado else "Validado"
    )
    detalle = web.get(f"{API}{admision.pk}/").json()
    campos = {
        campo["name"]: campo["value"]
        for campo in detalle["forms"]["proyecto"]["fields"]
    }
    assert campos["autoridad_nombre"] == informe.representante_nombre
    assert campos["autoridad_cargo"] == informe.representante_cargo
    assert campos["autoridad_dni"] == informe.representante_dni

    convertir = mocker.patch(
        "admisiones.services.legales_service.impl.convertir_convenio_a_pdf",
        return_value=b"%PDF-1.7",
    )
    datos = {
        **proyecto_datos,
        "cantidad_espacios": espacios,
        "caratula_causa": "Causa ficticia",
        "juzgado": "Juzgado ficticio",
        "memo": "Memo ficticio",
    }
    respuesta = _accion(web, admision, "proyecto-convenio", datos)
    assert respuesta.status_code == 200
    assert _campos(admision, "estado_legales") == ("Formulario Convenio Creado",)
    proyecto = admision.admisiones_proyecto_convenio.get()
    assert proyecto.es_judicializado is judicializado
    assert proyecto.caratula_causa == ("Causa ficticia" if judicializado else None)
    with proyecto.archivo.open("rb") as pdf:
        assert pdf.read() == b"%PDF-1.7"
    with proyecto.archivo_docx.open("rb") as docx:
        convertir.assert_called_once_with(docx.read())
        docx.seek(0)
        with ZipFile(docx) as zip_doc:
            assert all("comment" not in name for name in zip_doc.namelist())
        docx.seek(0)
        documento = Document(docx)
        texto = "\n".join(p.text for p in documento.paragraphs)
        assert "[PRESIDENTE" not in texto
        assert "[" not in "".join(documento.element.xpath("//w:t/text()"))
        assert "Autoridad & Asociación" in texto
        assert "Secretaria" in texto
        assert "BORRADOR" not in texto
        header = documento.sections[0].header
        assert (
            bool(
                header._element.xpath(
                    ".//wp:anchor[@behindDoc='1']/wp:docPr[@descr='BORRADOR']"
                )
            )
            is judicializado
        )
        assert (
            "Causa ficticia" in texto and "Juzgado ficticio" in texto
        ) is judicializado
        assert ("con el propósito de garantizar la continuidad" in texto) is (
            espacios == "mas_de_5"
        )
        assert len(documento.tables) == 3
        assert documento.tables[1].cell(2, 1).text == "42"
    informe.refresh_from_db()
    assert informe.representante_nombre == "Autoridad del informe"


@pytest.fixture
def admision_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def test_proyecto_convenio_rechaza_campos_obligatorios_y_localidad_de_otra_provincia(
    web, proyecto_datos
):
    admision = _admision(estado_legales="Expediente Agregado")
    otra_provincia = Provincia.objects.create(nombre="Otra provincia firmante")
    respuesta = _accion(
        web,
        admision,
        "proyecto-convenio",
        {
            **proyecto_datos,
            "autoridad_nombre": "",
            "autoridad_provincia": otra_provincia.pk,
        },
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["form"] == "proyecto"
    errores = {campo["name"] for campo in respuesta.json()["fields"] if campo["errors"]}
    assert errores == {"autoridad_nombre", "autoridad_localidad"}
    assert not admision.admisiones_proyecto_convenio.exists()
    assert _campos(admision, "estado_legales") == ("Expediente Agregado",)


def test_proyecto_convenio_django_reabre_el_modal_con_errores(web):
    admision = _admision(estado_legales="Expediente Agregado")
    respuesta = web.post(
        reverse("admisiones_legales_ver", args=[admision.pk]),
        {"btnProyectoConvenio": "", "cantidad_espacios": "mas_de_5"},
    )

    assert respuesta.status_code == 200
    assert respuesta.context["abrir_modal"] == "modalFormConvenio"
    form = respuesta.context["proyecto_form"]
    assert form["cantidad_espacios"].value() == "mas_de_5"
    assert "autoridad_nombre" in form.errors
    assert not admision.admisiones_proyecto_convenio.exists()


@pytest.mark.parametrize("componente", ["word", "pdf"])
def test_proyecto_convenio_no_guarda_si_falla_un_documento(
    web, proyecto_datos, admision_media, mocker, componente
):
    admision = _admision(estado_legales="Expediente Agregado")
    _informe_proyecto(admision)
    modulo = "admisiones.services.legales_service.impl"
    funcion = (
        "DocumentTemplateService.generar_docx"
        if componente == "word"
        else "convertir_convenio_a_pdf"
    )
    mocker.patch(f"{modulo}.{funcion}", side_effect=RuntimeError("falló la generación"))
    respuesta = _accion(web, admision, "proyecto-convenio", proyecto_datos)
    assert (
        "error",
        "No se pudieron generar el Word y el PDF del Proyecto de Convenio.",
    ) in _niveles(respuesta)
    assert not list(admision_media.iterdir())
    assert not admision.admisiones_proyecto_convenio.exists()
    assert _campos(admision, "estado_legales") == ("Expediente Agregado",)


def test_primera_providencia_copia_datos_del_convenio_sin_admitir_cambios(web, mocker):
    admision = _admision(estado_legales="IF Convenio Asignado")
    FormularioProyectoDeConvenio.objects.create(
        admision=admision,
        numero_if="IF-1",
        es_judicializado=True,
        cantidad_espacios="mas_de_5",
        caratula_causa="Causa",
        juzgado="Juzgado",
        memo="Memo",
    )
    generar = mocker.patch(
        "admisiones.services.legales_service.impl.LegalesService._generar_archivos_providencia"
    )
    detalle = web.get(f"{API}{admision.pk}/").json()
    assert detalle["primera_es_judicializado"] is True
    assert all(
        campo["attrs"]["disabled"]
        for campo in detalle["forms"]["primera_providencia"]["fields"]
    )
    respuesta = _accion(
        web,
        admision,
        "primera-providencia",
        {
            "cantidad_espacios": "hasta_5",
            "caratula_causa": "Ignorar",
        },
    )
    assert respuesta.status_code == 200
    providencia = Providencia.objects.get(admision=admision, orden="primera")
    assert providencia.es_judicializado
    assert providencia.cantidad_espacios == "mas_de_5"
    assert (providencia.caratula_causa, providencia.juzgado, providencia.memo) == (
        "Causa",
        "Juzgado",
        "Memo",
    )
    generar.assert_called_once()


def test_regenerar_proyecto_conserva_datos_y_reinicia_documentos(web, proyecto_datos):
    from admisiones.services.legales_service import LegalesService

    admision = _admision(estado_legales="Expediente Agregado")
    proyecto = FormularioProyectoDeConvenio.objects.create(
        admision=admision,
        archivo="viejo.pdf",
        archivo_docx="viejo.docx",
        numero_if="IF-1",
        **{
            k: v
            for k, v in proyecto_datos.items()
            if k not in {"autoridad_provincia", "autoridad_localidad"}
        },
        autoridad_provincia_id=proyecto_datos["autoridad_provincia"],
        autoridad_localidad_id=proyecto_datos["autoridad_localidad"],
    )
    LegalesService._reiniciar_proyecto_convenio(admision)
    proyecto.refresh_from_db()
    detalle = web.get(f"{API}{admision.pk}/").json()
    assert detalle["expediente"]["proyecto"] is None
    campos = {
        campo["name"]: campo["value"]
        for campo in detalle["forms"]["proyecto"]["fields"]
    }
    assert campos["autoridad_nombre"] == proyecto_datos["autoridad_nombre"]
    assert campos["autoridad_localidad"] == str(proyecto_datos["autoridad_localidad"])
    assert not proyecto.numero_if


@pytest.mark.skipif(
    not (shutil.which("libreoffice") or shutil.which("soffice"))
    or not all(shutil.which(tool) for tool in ("pdftotext", "pdfimages")),
    reason="Requiere LibreOffice y las herramientas PDF de Poppler",
)
def test_proyecto_convenio_convierte_el_word_a_pdf_con_marca_borrador(
    web, admision_media, proyecto_datos
):
    admision = _admision(estado_legales="Expediente Agregado")
    _informe_proyecto(admision, estado="Para revision")
    respuesta = _accion(web, admision, "proyecto-convenio", proyecto_datos)
    assert respuesta.status_code == 200
    proyecto = admision.admisiones_proyecto_convenio.get()
    texto_pdf = subprocess.check_output(
        ["pdftotext", proyecto.archivo.path, "-"], text=True, timeout=30
    )
    assert "BORRADOR" not in texto_pdf
    imagenes_pdf = subprocess.check_output(
        ["pdfimages", "-list", proyecto.archivo.path], text=True, timeout=30
    )
    paginas_con_marca = {
        int(columnas[0])
        for linea in imagenes_pdf.splitlines()[2:]
        if (columnas := linea.split()) and columnas[2] == "image"
    }
    cantidad_paginas = len(texto_pdf.rstrip("\f").split("\f"))
    assert cantidad_paginas > 1
    assert paginas_con_marca == set(range(1, cantidad_paginas + 1))
    assert proyecto_datos["autoridad_nombre"] in texto_pdf.replace("\n", " ")
    assert "CLÁUSULA" in texto_pdf


def test_primera_providencia_creates_it_and_the_sequence_guard_answers_409(web, mocker):
    mocker.patch(
        "admisiones.services.legales_service.impl.LegalesService._generar_archivos_providencia"
    )
    admision = _admision(estado_legales="IF Convenio Asignado")

    ok = _accion(web, admision, "primera-providencia", {"cantidad_espacios": "hasta_5"})

    assert ok.status_code == 200
    assert ("success", "Primera Providencia generada correctamente.") in _niveles(ok)
    primera = Providencia.objects.get(admision=admision, orden="primera")
    assert primera.cantidad_espacios == "hasta_5"
    assert _campos(admision, "estado_legales") == (
        "Formulario Primera Providencia Creado",
    )
    fuera = _accion(
        web, admision, "primera-providencia", {"cantidad_espacios": "mas_de_5"}
    )
    assert fuera.status_code == 409
    assert (
        "error",
        "No se puede generar la Primera Providencia: el expediente está en estado "
        "'Formulario Primera Providencia Creado'.",
    ) in _niveles(fuera)
    primera.refresh_from_db()
    assert primera.cantidad_espacios == "hasta_5"


def test_primera_providencia_with_an_invalid_form_answers_400_and_changes_nothing(web):
    admision = _admision(estado_legales="IF Convenio Asignado")

    respuesta = _accion(web, admision, "primera-providencia", {"cantidad_espacios": ""})

    assert respuesta.status_code == 400
    assert respuesta.json()["modal"] == "modalPrimeraProvidencia"
    assert respuesta.json()["form"] == "primera_providencia"
    assert not Providencia.objects.filter(admision=admision).exists()
    assert _campos(admision, "estado_legales") == ("IF Convenio Asignado",)


def test_gde_pv_and_segunda_providencia_follow_the_sequence(web, mocker):
    mocker.patch(
        "admisiones.services.legales_service.impl.LegalesService._generar_archivos_providencia"
    )
    admision = _admision(estado_legales="Formulario Primera Providencia Creado")
    Providencia.objects.create(admision=admision, orden="primera", tipo="incorporacion")

    mal = _accion(web, admision, "gde-pv-primera", {**PV, "pv_anio": "20"})
    assert mal.status_code == 400
    assert mal.json()["modal"] == "modalGDEPVPrimera"
    assert Providencia.objects.get(admision=admision).numero_gde_pv in (None, "")

    ok = _accion(web, admision, "gde-pv-primera", PV)
    assert ok.status_code == 200
    assert (
        Providencia.objects.get(admision=admision, orden="primera").numero_gde_pv
        == PV_FINAL
    )
    assert _campos(admision, "estado_legales") == ("IF Primera Providencia Asignado",)

    segunda = _accion(web, admision, "segunda-providencia", PV)
    assert segunda.status_code == 200
    assert (
        Providencia.objects.get(admision=admision, orden="segunda").numero_pv_primera
        == PV_FINAL
    )
    fuera = _accion(web, admision, "gde-pv-primera", PV)
    assert fuera.status_code == 409


def test_intervencion_juridicos_validates_rejects_and_keeps_the_admision_on_error(web):
    admision = _admision(estado_legales="IF Segunda Providencia Asignado")

    sin_motivo = _accion(
        web, admision, "intervencion-juridicos", {"intervencion_juridicos": "rechazado"}
    )
    assert ("error", "Error al guardar Intervención Jurídicos.") in _niveles(sin_motivo)
    assert _campos(admision, "intervencion_juridicos", "estado_legales") == (
        None,
        "IF Segunda Providencia Asignado",
    )
    ok = _accion(
        web, admision, "intervencion-juridicos", {"intervencion_juridicos": "validado"}
    )
    assert ("success", "Intervención Jurídicos guardada correctamente.") in _niveles(ok)
    assert _campos(admision, "intervencion_juridicos", "estado_legales") == (
        "validado",
        "Juridicos: Validado",
    )
    assert "convenio" in [b["key"] for b in ok.json()["botones"]]


def test_convenio_saves_the_number_and_the_uploaded_file(web):
    admision = _admision(estado_legales="Juridicos: Validado")

    sin_archivo = _accion(web, admision, "convenio", {"numero_convenio": "55"})
    assert ("error", "Error al guardar el Convenio.") in _niveles(sin_archivo)
    assert _campos(admision, "numero_convenio", "estado_legales") == (
        None,
        "Juridicos: Validado",
    )
    archivo = SimpleUploadedFile(
        "convenio.pdf", b"%PDF-1.4 convenio", "application/pdf"
    )
    ok = _accion(
        web,
        admision,
        "convenio",
        {"numero_convenio": "55", "archivo_convenio": archivo},
    )

    assert ("success", "Convenio guardado correctamente.") in _niveles(ok)
    admision.refresh_from_db()
    assert admision.numero_convenio == "55"
    assert admision.archivo_convenio.name.endswith(".pdf")
    assert admision.estado_legales == "Acompañamiento Pendiente"


def test_reinicio_expediente_archives_the_admision(web):
    admision = _admision(
        estado_legales="Juridicos: Rechazado", rechazo_juridicos_motivo="providencia"
    )

    vacio = _accion(
        web, admision, "reinicio-expediente", {"observaciones_reinicio_expediente": ""}
    )
    assert _campos(admision, "enviada_a_archivo", "estado_legales") == (
        False,
        "Juridicos: Rechazado",
    )
    assert vacio.status_code == 200

    ok = _accion(
        web,
        admision,
        "reinicio-expediente",
        {"observaciones_reinicio_expediente": "Vuelve a empezar"},
    )

    assert (
        "success",
        "Reinicio de expediente guardado y enviado a archivo correctamente.",
    ) in _niveles(ok)
    assert _campos(
        admision,
        "enviada_a_archivo",
        "estado_legales",
        "observaciones_reinicio_expediente",
    ) == (True, "Archivado", "Vuelve a empezar")


def test_solicitar_complementario_marks_the_request(web):
    admision = _admision(
        estado_legales="Juridicos: Rechazado",
        rechazo_juridicos_motivo="dictamen",
        dictamen_motivo="observacion en informe técnico",
    )

    vacio = _accion(web, admision, "solicitar-complementario", {})
    assert _campos(admision, "complementario_solicitado") == (False,)
    assert vacio.status_code == 200
    ok = _accion(
        web,
        admision,
        "solicitar-complementario",
        {"observaciones_informe_tecnico_complementario": "Aclarar prestaciones"},
    )

    assert ("success", "Informe complementario solicitado.") in _niveles(ok)
    assert _campos(
        admision,
        "complementario_solicitado",
        "estado_legales",
        "observaciones_informe_tecnico_complementario",
    ) == (True, "Informe Complementario Solicitado", "Aclarar prestaciones")


def _informe_complementario(admision, estado="enviado_validacion"):
    informe = InformeTecnico.objects.create(
        admision=admision, tipo="base", expediente_nro="EX-1"
    )
    return InformeComplementario.objects.create(
        admision=admision, informe_tecnico=informe, estado=estado
    )


def test_review_rectificar_requires_observations_and_persists(web):
    admision = _admision(estado_legales="Informe Complementario Enviado")
    informe = _informe_complementario(admision)
    url = f"{API}{admision.pk}/complementario/revision/"

    web.post(url, {"accion_complementario": "rectificar"})
    assert (
        "error",
        "Las observaciones son obligatorias para rectificar.",
    ) in _flash(web, admision)
    informe.refresh_from_db()
    assert informe.estado == "enviado_validacion"
    web.post(url, {"accion_complementario": "otra"})
    assert ("error", "Acción no válida.") in _flash(web, admision)

    ok = web.post(
        url,
        {
            "accion_complementario": "rectificar",
            "observaciones_complementario": "Corregir",
        },
    )

    assert ok.json()["redirect"] == f"/comedores/admisiones/legales/ver/{admision.pk}"
    assert ("success", "Informe complementario enviado a rectificar.") in _flash(
        web, admision
    )
    informe.refresh_from_db()
    assert (informe.estado, informe.observaciones_legales) == ("rectificar", "Corregir")
    assert _campos(admision, "estado_legales") == ("Informe Complementario Solicitado",)


def test_review_without_a_pending_report_keeps_the_native_message(web):
    admision = _admision()

    respuesta = web.post(
        f"{API}{admision.pk}/complementario/revision/",
        {"accion_complementario": "validar"},
    )

    assert respuesta.status_code == 200
    assert (
        "error",
        "No se encontró informe complementario para revisar.",
    ) in _flash(web, admision)


def test_if_complementario_requires_the_number(web):
    admision = _admision(estado_legales="Informe Complementario: Validado")

    sin_pdf = _accion(
        web, admision, "if-complementario", {"numero_if_complementario": "IF-9"}
    )
    assert (
        "error",
        "No se encontró PDF de informe complementario validado.",
    ) in _niveles(sin_pdf)
    vacio = _accion(
        web, admision, "if-complementario", {"numero_if_complementario": " "}
    )
    assert ("error", "El número IF es obligatorio.") in _niveles(vacio)


def test_validar_juridicos_keeps_the_native_rejection(web):
    admision = _admision(estado_legales="IF Segunda Providencia Asignado")

    respuesta = _accion(web, admision, "validar-juridicos")

    assert respuesta.status_code == 200
    assert any(
        nivel == "error" and texto.startswith("No se puede validar")
        for nivel, texto in _niveles(respuesta)
    )
    assert _campos(admision, "estado_legales") == ("IF Segunda Providencia Asignado",)


# ---- preview entries ---------------------------------------------------------------


def test_preview_entries_keep_the_native_guard_and_lookup(tmp_path):
    (tmp_path / "index.html").write_text("<html>react</html>", encoding="utf-8")
    patrones = legales_preview_patterns(tmp_path)
    EstadoAdmision.objects.create(id=3, nombre="Rectificar")
    admision = _admision()
    urlconf = types.ModuleType("legales_preview_test_urls")
    urlconf.urlpatterns = patrones + list(monolith_patterns)

    with override_settings(ROOT_URLCONF=urlconf):
        sin_permiso = _cliente(_usuario("preview_sin"))
        assert (
            sin_permiso.get(
                f"/comedores/admisiones/legales/ver/{admision.pk}"
            ).status_code
            == 403
        )
        root = _cliente(_usuario("preview_root", superuser=True))
        assert root.get("/comedores/admisiones/legales/ver/999999").status_code == 404
        ok = root.get(f"/comedores/admisiones/legales/ver/{admision.pk}")
        assert ok.status_code == 200
        assert b"react" in ok.content
        revision = root.get(
            f"/comedores/admisiones/legales/revisar-complementario/{admision.pk}"
        )
        assert revision.status_code == 200
        # The native POST stays reachable on the same URL.
        post = root.post(
            f"/comedores/admisiones/legales/ver/{admision.pk}",
            {"btnObservaciones": "", "observaciones": "Nativo"},
        )
        assert post.status_code == 302
    assert _campos(admision, "estado_legales") == ("A Rectificar",)
