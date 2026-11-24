"""Save (draft and submit) of the report editor through G1 (AD02.01, U3a).

Every test asserts the exact persisted effects, and that a rejected save leaves
the stored data untouched.
"""

from unittest import mock

import pytest
from django.test import Client

from admisiones.models.admisiones import (
    Admision,
    CampoASubsanar,
    InformeTecnico,
    ObservacionGeneralInforme,
)
from admisiones.tests.test_web_api_informe_detalle_ad02 import (
    _cliente,
    _informe,
    _usuario,
)
from comedores.models import Comedor
from core.models import Localidad, Municipio, Provincia

API = "/api/web/comedores/admisiones/informes/"
SERVICE = "admisiones.services.informes_service.impl.InformeService"
ADMISION = "admisiones.services.admisiones_service.AdmisionService"
PLANTILLAS = (
    "admisiones.services.templates_informe_tecnico_service."
    "PlantillaInformeTecnicoService.resolver_publicacion_para_admision"
)

pytestmark = pytest.mark.django_db


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Guardar")
    return Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        es_ex_pnud="no",
        estado_admision="documentacion_aprobada",
    )


@pytest.fixture(name="usuario")
def usuario_fixture():
    return _usuario("editor_guardar", "comedores.view_comedor")


@pytest.fixture(name="web")
def web_fixture(usuario):
    return _cliente(usuario)


def _crear(admision, tipo="base"):
    return f"{API}{tipo}/admision/{admision.pk}/guardar/"


def _valores_completos(web, url_formulario):
    """A value for every field the native form exposes (what a user would type)."""
    valores = {}
    provincia = Provincia.objects.get_or_create(nombre="Provincia Guardar")[0]
    municipio = Municipio.objects.get_or_create(
        nombre="Municipio G", provincia=provincia
    )[0]
    localidad = Localidad.objects.get_or_create(
        nombre="Localidad G", municipio=municipio
    )[0]
    for campo in web.get(url_formulario).json()["fields"]:
        if campo["kind"] == "select" and "provincia" in campo["name"]:
            valores[campo["name"]] = str(provincia.pk)
        elif campo["kind"] == "select" and "localidad" in campo["name"]:
            valores[campo["name"]] = str(localidad.pk)
        elif campo["kind"] == "checkbox":
            valores[campo["name"]] = campo["value"]
        elif campo["kind"] == "select":
            opciones = [c["value"] for c in campo["choices"] if c["value"]]
            valores[campo["name"]] = campo["value"] or (opciones[0] if opciones else "")
        elif campo["kind"] == "date":
            valores[campo["name"]] = campo["value"] or "2026-03-04"
        elif campo["kind"] == "number":
            valores[campo["name"]] = campo["value"] or "1"
        elif "mail" in campo["name"] or "electronico" in campo["name"]:
            valores[campo["name"]] = campo["value"] or "a@b.ar"
        else:
            valores[campo["name"]] = campo["value"] or "12345678"
    return valores


def _estado(admision):
    admision.refresh_from_db()
    return admision.estado_admision


def _publicacion():
    return mock.Mock(version=mock.Mock(numero=1))


def test_draft_creates_the_report_and_starts_the_technical_report(
    web, usuario, admision
):
    respuesta = web.post(
        _crear(admision),
        {"action": "draft", "values": {"expediente_nro": "EX-1"}},
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    informe = InformeTecnico.objects.get()
    assert datos == {
        "success": True,
        "informe_id": informe.pk,
        "estado": "Iniciado",
        "estado_formulario": "borrador",
        "redirect": datos["redirect"],
    }
    assert str(admision.pk) in datos["redirect"]
    assert (informe.tipo, informe.admision_id, informe.expediente_nro) == (
        "base",
        admision.pk,
        "EX-1",
    )
    assert informe.creado_por_id == usuario.pk
    assert informe.modificado_por_id == usuario.pk
    assert _estado(admision) == "informe_tecnico_en_proceso"


def test_second_draft_reuses_the_stored_report(web, admision):
    url = _crear(admision)
    web.post(
        url,
        {"action": "draft", "values": {"expediente_nro": "EX-1"}},
        content_type="application/json",
    )

    web.post(
        url,
        {"action": "draft", "values": {"expediente_nro": "EX-2"}},
        content_type="application/json",
    )

    assert InformeTecnico.objects.count() == 1
    assert InformeTecnico.objects.get().expediente_nro == "EX-2"


def test_edit_draft_updates_only_the_posted_fields_and_keeps_the_state(web, admision):
    informe = _informe(admision, expediente_nro="EX-VIEJO")

    respuesta = web.post(
        f"{API}base/{informe.pk}/guardar/",
        {"action": "draft", "values": {"expediente_nro": "EX-NUEVO"}},
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    informe.refresh_from_db()
    assert informe.expediente_nro == "EX-NUEVO"
    assert (informe.estado, informe.estado_formulario) == ("Iniciado", "borrador")


def test_validated_report_is_rejected_and_left_untouched(web, admision):
    informe = _informe(
        admision,
        estado="Validado",
        estado_formulario="finalizado",
        expediente_nro="EX-V",
    )

    respuesta = web.post(
        _crear(admision),
        {"action": "draft", "values": {"expediente_nro": "EX-OTRO"}},
        content_type="application/json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "success": False,
        "saved_as_draft": False,
        "error": "El informe técnico ya fue validado y no puede editarse.",
    }
    informe.refresh_from_db()
    assert (informe.expediente_nro, informe.estado) == ("EX-V", "Validado")
    assert InformeTecnico.objects.count() == 1
    assert _estado(admision) == "documentacion_aprobada"


def test_submit_without_required_documents_is_rejected_and_persists_nothing(
    web, admision
):
    with mock.patch(
        f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=False
    ):
        respuesta = web.post(
            _crear(admision),
            {"action": "submit", "values": {}},
            content_type="application/json",
        )

    # The native form rejects first when required fields are missing; send them all.
    assert respuesta.status_code == 400
    assert InformeTecnico.objects.count() == 0
    valores = _valores_completos(web, f"{API}base/admision/{admision.pk}/formulario/")
    with mock.patch(
        f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=False
    ):
        respuesta = web.post(
            _crear(admision),
            {"action": "submit", "values": valores},
            content_type="application/json",
        )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == (
        "No puede finalizar el informe técnico si faltan documentos obligatorios por cargar."
    )
    assert InformeTecnico.objects.count() == 0
    assert _estado(admision) == "documentacion_aprobada"


def test_submit_with_unaccepted_documents_is_rejected(web, admision):
    valores = _valores_completos(web, f"{API}base/admision/{admision.pk}/formulario/")
    with (
        mock.patch(
            f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=True
        ),
        mock.patch(f"{ADMISION}._todos_obligatorios_aceptados", return_value=False),
    ):
        respuesta = web.post(
            _crear(admision),
            {"action": "submit", "values": valores},
            content_type="application/json",
        )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == (
        "No puede finalizar el informe técnico si hay documentos obligatorios sin validar."
    )
    assert InformeTecnico.objects.count() == 0


def test_invalid_form_returns_every_error_and_persists_nothing(web, admision):
    informe = _informe(admision, expediente_nro="EX-ORIG")

    respuesta = web.post(
        f"{API}base/{informe.pk}/guardar/",
        {"action": "submit", "values": {"expediente_nro": "EX-CAMBIO"}},
        content_type="application/json",
    )

    assert respuesta.status_code == 400
    datos = respuesta.json()
    assert datos["success"] is False
    assert datos["message"].startswith(
        "No se pudo guardar el informe. Revisá los campos: "
    )
    campos = {c["name"]: c for c in datos["fields"]}
    assert campos["expediente_nro"]["value"] == "EX-CAMBIO"
    assert any(c["errors"] for c in campos.values())
    informe.refresh_from_db()
    assert informe.expediente_nro == "EX-ORIG"
    assert (informe.estado, informe.estado_formulario) == ("Iniciado", "borrador")
    assert _estado(admision) == "documentacion_aprobada"


def test_publication_error_keeps_the_report_as_a_draft(web, admision):
    valores = _valores_completos(web, f"{API}base/admision/{admision.pk}/formulario/")
    with (
        mock.patch(
            f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=True
        ),
        mock.patch(f"{ADMISION}._todos_obligatorios_aceptados", return_value=True),
    ):
        respuesta = web.post(
            _crear(admision),
            {"action": "submit", "values": valores},
            content_type="application/json",
        )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert (datos["success"], datos["saved_as_draft"]) == (False, True)
    assert datos["error"].endswith(
        "Se guardó el Informe Técnico como borrador; "
        "puede corregir sus validaciones e intentar nuevamente."
    )
    informe = InformeTecnico.objects.get()
    assert (informe.estado, informe.estado_formulario) == ("Iniciado", "borrador")
    assert _estado(admision) == "informe_tecnico_en_proceso"


def _submit(web, admision, valores, docx):
    with (
        mock.patch(
            f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=True
        ),
        mock.patch(f"{ADMISION}._todos_obligatorios_aceptados", return_value=True),
        mock.patch(PLANTILLAS, return_value=(_publicacion(), None)),
        mock.patch(f"{SERVICE}.generar_docx_borrador", return_value=docx),
    ):
        return web.post(
            _crear(admision),
            {"action": "submit", "values": valores},
            content_type="application/json",
        )


def test_submit_generates_the_docx_and_finalizes_everything(web, usuario, admision):
    valores = _valores_completos(web, f"{API}base/admision/{admision.pk}/formulario/")

    respuesta = _submit(web, admision, valores, docx=True)

    assert respuesta.status_code == 200, respuesta.json()
    assert respuesta.json()["estado"] == "Para revision"
    informe = InformeTecnico.objects.get()
    assert (informe.estado, informe.estado_formulario) == (
        "Para revision",
        "finalizado",
    )
    assert informe.creado_por_id == usuario.pk
    assert _estado(admision) == "informe_tecnico_finalizado"


@pytest.mark.django_db(transaction=True)
def test_generation_failure_matches_the_native_view(usuario):
    """Parity with the Django view, without the test wrapper transaction.

    ``guardar_informe`` is ``@transaction.atomic``: a generation failure rolls the
    whole save back, so no report is stored and the admission keeps its state, on
    the native page (re-rendered form, 200) and on the API (409) alike.
    """
    comedor = Comedor.objects.create(nombre="Comedor Paridad")
    por_api = Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        es_ex_pnud="no",
        estado_admision="documentacion_aprobada",
    )
    nativa = Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        es_ex_pnud="no",
        estado_admision="documentacion_aprobada",
    )
    web = _cliente(usuario)
    web.raise_request_exception = False
    valores = _valores_completos(web, f"{API}base/admision/{por_api.pk}/formulario/")

    with (
        mock.patch(
            f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=True
        ),
        mock.patch(f"{ADMISION}._todos_obligatorios_aceptados", return_value=True),
        mock.patch(PLANTILLAS, return_value=(_publicacion(), None)),
        mock.patch(f"{SERVICE}.generar_docx_borrador", return_value=None),
    ):
        api = web.post(
            _crear(por_api),
            {"action": "submit", "values": valores},
            content_type="application/json",
        )
        datos = {
            n: ("on" if v is True else v) for n, v in valores.items() if v is not False
        }
        native = web.post(
            f"/comedores/admision/informe_tecnico/base/{nativa.pk}/crear/",
            {**datos, "action": "submit"},
        )

    assert (api.status_code, native.status_code) == (409, 200)
    assert api.json()["error"] == (
        "No se pudo generar el DOCX borrador. El Informe Técnico permanece editable."
    )
    for admision in (por_api, nativa):
        admision.refresh_from_db()
        assert not InformeTecnico.objects.filter(admision=admision).exists()
        assert admision.estado_admision == "documentacion_aprobada"


def test_submit_of_a_remediated_report_clears_the_remarks(web, admision):
    informe = _informe(
        admision,
        estado="A subsanar",
        estado_formulario="finalizado",
        observaciones_subsanacion="Corregir",
    )
    CampoASubsanar.objects.create(informe=informe, campo="expediente_nro")
    ObservacionGeneralInforme.objects.create(informe=informe, texto="Corregir")
    valores = _valores_completos(web, f"{API}base/{informe.pk}/formulario/")

    with (
        mock.patch(
            f"{ADMISION}._todos_obligatorios_tienen_archivos", return_value=True
        ),
        mock.patch(f"{ADMISION}._todos_obligatorios_aceptados", return_value=True),
        mock.patch(PLANTILLAS, return_value=(_publicacion(), None)),
        mock.patch(f"{SERVICE}.generar_docx_borrador", return_value=True),
    ):
        respuesta = web.post(
            f"{API}base/{informe.pk}/guardar/",
            {"action": "submit", "values": valores},
            content_type="application/json",
        )

    assert respuesta.status_code == 200, respuesta.json()
    informe.refresh_from_db()
    assert (informe.estado, informe.estado_formulario) == (
        "Para revision",
        "finalizado",
    )
    assert informe.observaciones_subsanacion is None
    assert not CampoASubsanar.objects.filter(informe=informe).exists()
    assert not ObservacionGeneralInforme.objects.filter(informe=informe).exists()


def test_request_shape_access_and_csrf(web, admision):
    url = _crear(admision)
    assert web.get(url).status_code == 405
    for cuerpo in (
        {"action": "otra", "values": {}},
        {"values": {}},
        {"action": "draft", "values": []},
        {"action": "draft", "values": {"expediente_nro": {"x": 1}}},
    ):
        assert (
            web.post(url, cuerpo, content_type="application/json").status_code == 400
        ), cuerpo
    assert InformeTecnico.objects.count() == 0
    otro = web.post(
        _crear(admision, "otro"),
        {"action": "draft", "values": {}},
        content_type="application/json",
    )
    assert otro.status_code == 400
    assert (
        web.post(
            f"{API}base/admision/999999/guardar/",
            {"action": "draft", "values": {}},
            content_type="application/json",
        ).status_code
        == 404
    )
    assert (
        web.post(
            f"{API}base/999999/guardar/",
            {"action": "draft", "values": {}},
            content_type="application/json",
        ).status_code
        == 404
    )
    anonimo = Client()
    assert anonimo.post(url, {}, content_type="application/json").status_code in (
        401,
        403,
    )
    sin_permiso = _cliente(_usuario("sin_permiso_guardar"))
    assert (
        sin_permiso.post(
            url, {"action": "draft", "values": {}}, content_type="application/json"
        ).status_code
        == 403
    )
    assert InformeTecnico.objects.count() == 0

    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(_usuario("csrf_guardar", "comedores.view_comedor"))
    rechazado = con_csrf.post(
        url, {"action": "draft", "values": {}}, content_type="application/json"
    )
    assert rechazado.status_code == 403
    assert InformeTecnico.objects.count() == 0
