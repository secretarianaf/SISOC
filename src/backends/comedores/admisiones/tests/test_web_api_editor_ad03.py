"""Web API (G1 v1) of the technical admision editor (AD03.02).

The read endpoint projects the native context; each action runs the native view's
``post()``. The tests pin the persisted effect of every action, that a rejection leaves
the data unchanged, the access (kept gaps included) and the HTTP contract.
"""

import types
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import Client, override_settings
from django.utils import timezone

from admisiones.models.admisiones import (
    Admision,
    ArchivoAdmision,
    Documentacion,
    EstadoAdmision,
    InformeTecnico,
    TipoConvenio,
)
from admisiones.web_preview_seguimiento import seguimiento_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns
from organizaciones.models import Organizacion, TipoEntidad

API = "/api/web/comedores/admisiones/"
EXPEDIENTE = "EX-2026-000000001- -APN-DGD#MCH"

pytestmark = pytest.mark.django_db


def _usuario(nombre, permiso=None, superuser=False, grupo=None):
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
    if grupo:
        usuario.groups.add(Group.objects.get_or_create(name=grupo)[0])
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    return usuario


def _cliente(usuario, csrf=False):
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(usuario)
    return client


@pytest.fixture(name="root")
def root_fixture():
    return _cliente(_usuario("root_editor", superuser=True))


@pytest.fixture(name="convenio")
def convenio_fixture():
    return TipoConvenio.objects.create(pk=3, nombre="Personería Jurídica")


@pytest.fixture(name="admision")
def admision_fixture(convenio):
    # The native service writes ``estado_id`` 1 and 2 literally, so those rows must exist.
    estado = EstadoAdmision.objects.create(pk=1, nombre="Pendiente")
    EstadoAdmision.objects.create(pk=2, nombre="Rectificado")
    comedor = Comedor.objects.create(nombre="Comedor Editor AD03")
    return Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        tipo_convenio=convenio,
        estado=estado,
        estado_admision="convenio_seleccionado",
        convenio_numero=7,
        es_ex_pnud="no",
    )


def _lee(web, admision):
    return web.get(f"{API}{admision.pk}/")


def _accion(web, admision, accion, datos=None, **extra):
    return web.post(f"{API}{admision.pk}/acciones/{accion}/", datos or {}, **extra)


def _fresca(admision):
    admision.refresh_from_db()
    return admision


# --- read ------------------------------------------------------------------


def test_read_projects_the_native_context(admision, root):
    documentacion = Documentacion.objects.create(nombre="Estatuto", obligatorio=True)
    documentacion.convenios.add(admision.tipo_convenio)
    ArchivoAdmision.objects.create(
        admision=admision,
        documentacion=documentacion,
        archivo=SimpleUploadedFile("estatuto.pdf", b"%PDF"),
        estado="Documento adjunto",
    )

    respuesta = _lee(root, admision)

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == admision.pk
    assert datos["comedor"]["nombre"] == "Comedor Editor AD03"
    assert datos["comedor"]["tipocomedor"] == "Sin información"
    assert datos["admision"]["tipo_convenio"] == "Personería Jurídica"
    assert datos["admision"]["convenio_numero"] == 7
    assert datos["puede_editar_convenio_numero"] is True
    assert datos["seleccion_convenio"] is None
    assert datos["validaciones"]["editable"] is True
    assert [f["name"] for f in datos["validaciones"]["fields"]] == [
        "es_ex_pnud",
        "estado_convenio_pnud",
    ]
    assert datos["stats"]["obligatorios_total"] == 1
    documento = datos["documentos"][0]
    assert documento["nombre"] == "Estatuto"
    assert documento["estado_ui"]["kind"] == "select"
    assert documento["puede_eliminar"] is True
    assert (
        documento["archivo_url"].endswith("estatuto.pdf")
        or "estatuto" in documento["archivo_url"]
    )
    assert datos["puede_agregar_documento"] is True
    assert datos["messages"] == []


def test_read_without_agreement_type_asks_for_it(admision, root):
    admision.tipo_convenio = None
    admision.save()

    datos = _lee(root, admision).json()

    assert datos["seleccion_convenio"]["tipo"] == "incorporacion"
    assert datos["seleccion_convenio"]["precargado"] is False
    assert datos["validaciones"] is None


def test_read_buttons_follow_the_native_state(admision, root):
    admision.estado_admision = "documentacion_aprobada"
    admision.save()

    datos = _lee(root, admision).json()

    claves = [b["clave"] for b in datos["botones"]]
    assert "finalizar_carga_documentacion" in claves
    boton = next(
        b for b in datos["botones"] if b["clave"] == "finalizar_carga_documentacion"
    )
    assert boton["modal"] == "modalFinalizarCargaDocumentacion"


def test_read_marks_the_embedded_report_form_for_the_technician(admision, root):
    datos = _lee(root, admision).json()

    assert datos["informe_embebido"] is True
    admision.estado_admision = "enviado_a_legales"
    admision.save()
    assert _lee(root, admision).json()["informe_embebido"] is False


def test_access_and_lookups_are_the_native_ones(admision):
    assert Client().get(f"{API}{admision.pk}/").status_code in (401, 403)
    sin_permiso = _cliente(_usuario("sin_permiso_ed"))
    assert _lee(sin_permiso, admision).status_code == 403
    lector = _cliente(_usuario("lector_ed", "comedores.view_comedor"))
    assert _lee(lector, admision).status_code == 200
    # No per-object scope: a reader that is nobody's technician reads any admision.
    assert _lee(lector, admision).json()["puede_editar_convenio_numero"] is False
    assert lector.get(f"{API}999999/").status_code == 404


# --- actions -----------------------------------------------------------------


def test_actions_need_access_a_known_action_and_csrf(admision):
    lector = _cliente(_usuario("lector_post", "comedores.view_comedor"))
    assert Client().post(
        f"{API}{admision.pk}/acciones/derivar-legales/"
    ).status_code in (
        401,
        403,
    )
    sin = _cliente(_usuario("sin_post"))
    assert _accion(sin, admision, "derivar-legales").status_code == 403
    assert _accion(lector, admision, "no-existe").status_code == 404
    assert _accion(lector, admision, "derivar-legales").status_code == 200
    csrf = _cliente(_usuario("csrf_post", "comedores.view_comedor"), csrf=True)
    assert _accion(csrf, admision, "rectificar-documentacion").status_code == 403
    assert lector.post(f"{API}999999/acciones/derivar-legales/").status_code == 404


def test_derive_to_legal_persists_and_a_repeat_is_rejected(admision, root):
    respuesta = _accion(root, admision, "derivar-legales")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["message"] == "La admisión fue enviada a legales correctamente."
    assert cuerpo["redirect"] == f"/comedores/admisiones/tecnicos/editar/{admision.pk}"
    admision = _fresca(admision)
    assert admision.enviado_legales is True
    assert admision.estado_legales == "Enviado a Legales"
    assert admision.estado_admision == "enviado_a_legales"

    repetida = _accion(root, admision, "derivar-legales")

    assert repetida.status_code == 400
    assert (
        repetida.json()["message"]
        == "La admisión ya estaba marcada como enviada a legales."
    )
    assert _fresca(admision).estado_admision == "enviado_a_legales"


def test_technical_report_number_is_saved_or_rejected_untouched(admision, root):
    sin_archivo = _accion(
        root, admision, "if-informe-tecnico", {"numero_if_tecnico": "IF-1"}
    )

    assert sin_archivo.status_code == 400
    assert (
        sin_archivo.json()["message"] == "Error en el formulario. Verifique los datos."
    )
    assert _fresca(admision).numero_if_tecnico is None

    guardada = _accion(
        root,
        admision,
        "if-informe-tecnico",
        {
            "numero_if_tecnico": "IF-2026-1",
            "archivo_informe_tecnico_GDE": SimpleUploadedFile("if.pdf", b"%PDF-1"),
        },
    )

    assert guardada.status_code == 200
    assert (
        guardada.json()["message"]
        == "Número IF del Informe Técnico guardado correctamente."
    )
    admision = _fresca(admision)
    assert admision.numero_if_tecnico == "IF-2026-1"
    assert admision.archivo_informe_tecnico_GDE
    assert admision.estado_admision == "if_informe_tecnico_cargado"


def test_accompaniment_start_persists_in_one_transaction(admision, root):
    with mock.patch(
        "admisiones.services.admisiones_service.impl.AcompanamientoService."
        "importar_datos_desde_admision"
    ) as importar:
        respuesta = _accion(root, admision, "comenzar-acompanamiento")

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Se envió a Acompañamiento correctamente."
    importar.assert_called_once()
    admision = _fresca(admision)
    assert admision.enviado_acompaniamiento is True
    assert admision.estado_legales == "Acompañamiento Iniciado"
    assert admision.estado_admision == "enviado_a_acompaniamiento"


def test_accompaniment_failure_rolls_back_and_reports(admision, root):
    with mock.patch(
        "admisiones.services.admisiones_service.impl.AcompanamientoService."
        "importar_datos_desde_admision",
        side_effect=RuntimeError("fallo"),
    ):
        respuesta = _accion(root, admision, "comenzar-acompanamiento")

    assert respuesta.status_code == 400
    assert respuesta.json()["message"] == "Error inesperado."
    admision = _fresca(admision)
    assert admision.enviado_acompaniamiento is False
    assert admision.estado_admision == "convenio_seleccionado"


def test_documentation_rectified_and_finished_persist(admision, root):
    admision.estado_legales = "A Rectificar"
    admision.observaciones = "Falta algo"
    admision.save()

    respuesta = _accion(root, admision, "rectificar-documentacion")

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "Se rectificó la documentación."
    admision = _fresca(admision)
    assert admision.estado_legales == "Rectificado"
    assert admision.enviado_legales is True
    assert admision.observaciones is None

    finalizada = _accion(root, admision, "finalizar-carga-documentacion")

    assert finalizada.status_code == 200
    assert (
        finalizada.json()["message"]
        == "Carga de documentación finalizada correctamente."
    )
    assert _fresca(admision).estado_admision == "documentacion_carga_finalizada"


def test_cover_is_saved_or_rejected_with_the_form_errors(admision, root):
    invalida = _accion(root, admision, "caratular", {"expediente_anio": "20"})

    assert invalida.status_code == 400
    cuerpo = invalida.json()
    assert cuerpo["success"] is False
    campos = {f["name"]: f for f in cuerpo["fields"]}
    assert campos["expediente_anio"]["errors"]
    assert campos["expediente_numero"]["errors"]
    assert _fresca(admision).num_expediente in (None, "")

    valida = _accion(
        root,
        admision,
        "caratular",
        {
            "expediente_anio": "2026",
            "expediente_numero": "123456789",
            "expediente_reparticion": "DGD",
            "expediente_organismo": "MCH",
        },
    )

    assert valida.status_code == 200
    assert (
        valida.json()["message"]
        == "Caratulación del expediente guardado correctamente."
    )
    assert _fresca(admision).num_expediente == "EX-2026-123456789- -APN-DGD#MCH"


def test_confirm_agreement_type_is_resolved_from_the_organization(
    admision, convenio, root
):
    sin_organizacion = Admision.objects.create(
        comedor=Comedor.objects.create(nombre="Sin org"), tipo="incorporacion"
    )

    rechazada = _accion(root, sin_organizacion, "confirmar-tipo-convenio")

    assert rechazada.status_code == 400
    assert rechazada.json()["message"] == (
        "No se pudo resolver el Tipo de Convenio desde el Tipo de Entidad de la organización."
    )
    assert _fresca(sin_organizacion).tipo_convenio is None

    entidad = TipoEntidad.objects.create(nombre="Personería Jurídica")
    organizacion = Organizacion.objects.create(nombre="Org Ed", tipo_entidad=entidad)
    admision.comedor.organizacion = organizacion
    admision.comedor.save()
    admision.tipo_convenio = None
    admision.save()

    sin_validaciones = _accion(root, admision, "confirmar-tipo-convenio")

    assert sin_validaciones.status_code == 400
    assert _fresca(admision).tipo_convenio is None

    confirmada = _accion(
        root, admision, "confirmar-tipo-convenio", {"es_ex_pnud": "no"}
    )

    assert confirmada.status_code == 200
    assert (
        confirmada.json()["message"]
        == "Tipo de convenio precargado desde la organización."
    )
    admision = _fresca(admision)
    assert admision.tipo_convenio_id == convenio.pk
    assert admision.estado_admision == "convenio_seleccionado"
    assert admision.es_ex_pnud == "no"


def test_template_validations_are_saved_or_rejected_untouched(admision, root):
    invalida = _accion(root, admision, "validaciones-template", {"es_ex_pnud": "si"})

    assert invalida.status_code == 400
    assert "Debe indicar el estado del convenio PNUD." in invalida.json()["message"]
    assert _fresca(admision).es_ex_pnud == "no"

    guardada = _accion(
        root,
        admision,
        "validaciones-template",
        {"es_ex_pnud": "si", "estado_convenio_pnud": "vigente"},
    )

    assert guardada.status_code == 200
    assert (
        guardada.json()["message"]
        == "Validaciones de templates guardadas correctamente."
    )
    admision = _fresca(admision)
    assert (admision.es_ex_pnud, admision.estado_convenio_pnud) == ("si", "vigente")


def test_template_validations_keep_the_native_permission_text(admision):
    lector = _cliente(_usuario("lector_val", "comedores.view_comedor"))

    respuesta = _accion(lector, admision, "validaciones-template", {"es_ex_pnud": "si"})

    assert respuesta.status_code == 400
    assert (
        respuesta.json()["message"]
        == "No tiene permisos para modificar estas validaciones."
    )
    assert _fresca(admision).es_ex_pnud == "no"


def test_actions_keep_the_native_gap_of_not_checking_the_origin_state(admision):
    # The native handlers do not repeat the role or the origin state (AD03 contract, gap 4).
    lector = _cliente(_usuario("lector_gap", "admisiones.view_admision"))
    admision.estado_admision = "documentacion_en_proceso"
    admision.save()

    respuesta = _accion(lector, admision, "finalizar-carga-documentacion")

    assert respuesta.status_code == 200
    assert _fresca(admision).estado_admision == "documentacion_carga_finalizada"


def test_json_body_is_accepted_like_the_form_body(admision, root):
    respuesta = root.post(
        f"{API}{admision.pk}/acciones/validaciones-template/",
        {"es_ex_pnud": "si", "estado_convenio_pnud": "finalizado"},
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert _fresca(admision).estado_convenio_pnud == "finalizado"


def _informe(admision, estado):
    """The report with the minimum its required columns need."""
    kinds = (
        (models.EmailField, "test@example.com"),
        (models.BooleanField, False),
        (models.DateTimeField, timezone.now()),
        (models.DateField, timezone.now().date()),
        (models.IntegerField, 1),
    )
    datos = {}
    for field in InformeTecnico._meta.fields:
        autogen = field.primary_key or field.auto_created
        if autogen or getattr(field, "auto_now", False) or field.has_default():
            continue
        if getattr(field, "auto_now_add", False) or field.null:
            continue
        if not isinstance(field, models.ForeignKey):
            datos[field.name] = (
                field.choices[0][0]
                if field.choices
                else next((v for k, v in kinds if isinstance(field, k)), "test")
            )
    datos.update(admision=admision, tipo="base", estado=estado)
    return InformeTecnico.objects.create(**datos)


def test_final_docx_upload_runs_the_native_check_and_service(admision, root):
    admision.estado_admision = "informe_tecnico_finalizado"
    admision.save()
    informe = _informe(admision, "Docx generado")
    docx = SimpleUploadedFile("final.docx", b"PK")

    with mock.patch(
        "admisiones.views.web_views.InformeService.subir_docx_editado",
        return_value=True,
    ) as subir:
        respuesta = _accion(
            root,
            admision,
            "subir-docx-final",
            {"docx_final": docx, "informe_id": informe.pk},
        )

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == (
        "DOCX final subido correctamente. El informe está ahora en revisión."
    )
    subir.assert_called_once()


def test_final_docx_upload_is_rejected_untouched_without_file_or_state(admision, root):
    sin_archivo = _accion(root, admision, "subir-docx-final", {})

    assert sin_archivo.status_code == 400
    assert sin_archivo.json()["message"] == "Debe seleccionar un archivo DOCX."

    informe = _informe(admision, "Iniciado")
    with mock.patch(
        "admisiones.views.web_views.InformeService.subir_docx_editado"
    ) as subir:
        estado = _accion(
            root,
            admision,
            "subir-docx-final",
            {
                "docx_final": SimpleUploadedFile("f.docx", b"PK"),
                "informe_id": informe.pk,
            },
        )

    assert estado.status_code == 400
    assert estado.json()["message"] == (
        "Estado inválido para subir el DOCX final del informe técnico."
    )
    subir.assert_not_called()
    assert _fresca(admision).estado_admision == "convenio_seleccionado"


def test_final_docx_upload_keeps_the_native_403_for_a_plain_reader(admision):
    lector = _cliente(_usuario("lector_docx", "comedores.view_comedor"))

    respuesta = _accion(
        lector,
        admision,
        "subir-docx-final",
        {"docx_final": SimpleUploadedFile("f.docx", b"PK")},
    )

    assert respuesta.status_code == 403


INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    module = types.ModuleType("editor_preview_test_urls")
    module.urlpatterns = seguimiento_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_serves_the_index_unless_the_native_page_embeds_the_report(admision):
    url = f"/comedores/admisiones/tecnicos/editar/{admision.pk}"
    lector = _cliente(_usuario("lector_prev_ed", "comedores.view_comedor"))

    # A plain reader cannot edit the report: React page.
    assert '/comedores/react/assets/app-1.js"' in lector.get(url).content.decode()
    assert Client().get(url).status_code in (302, 403)
    assert _cliente(_usuario("sin_prev_ed")).get(url).status_code == 403
    assert lector.get("/comedores/admisiones/tecnicos/editar/999999").status_code == 404
    # The technician that can edit it keeps the native page, so no control is inert.
    root = _cliente(_usuario("root_prev_ed", superuser=True))
    nativa = root.get(url).content.decode()
    assert "informe-tecnico-seccion" in nativa
    assert "/comedores/react/assets/app-1.js" not in nativa
    # The native POST stays for that page.
    assert root.post(url, {"mandarLegales": "1"}).status_code == 302
    assert _fresca(admision).estado_admision == "enviado_a_legales"
