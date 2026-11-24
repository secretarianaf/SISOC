"""Web API (G1 v1) of the report detail actions and the complementary report (AD02.02).

Every test asserts the exact persisted effects, and that a rejected request leaves the
stored data untouched.
"""

import types

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from admisiones.models.admisiones import (
    Admision,
    CampoASubsanar,
    InformeComplementario,
    InformeComplementarioCampos,
    InformeTecnico,
    InformeTecnicoPDF,
    ObservacionGeneralInforme,
)
from admisiones.tests.test_web_api_informe_detalle_ad02 import (
    INDEX,
    _cliente,
    _informe,
    _ready,
    _usuario,
)
from admisiones.web_preview_informe_complementario import (
    complementario_preview_patterns,
)
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/admisiones/informes/"
NATIVO = "/comedores/admision/informe_complementario/"
GENERADO = "informe_tecnico_finalizado"

pytestmark = pytest.mark.django_db


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Acciones")
    return Admision.objects.create(
        comedor=comedor, tipo="incorporacion", estado_admision=GENERADO
    )


@pytest.fixture(name="superusuario")
def superusuario_fixture():
    return _ready(get_user_model().objects.create_superuser("super_acciones"))


def _docx(nombre="editado.docx"):
    return SimpleUploadedFile(nombre, b"PK-synthetic-docx")


def _estado(informe):
    informe.refresh_from_db()
    return informe.estado


def _generado(admision):
    return _informe(admision, estado="Docx generado", estado_formulario="finalizado")


def _editor(admision):
    return reverse("admisiones_tecnicos_editar", args=[admision.pk])


# --- AD02.02: upload of the edited DOCX ---------------------------------------


def test_upload_stores_the_docx_and_moves_the_report_to_review(admision, superusuario):
    informe = _generado(admision)
    web = _cliente(superusuario)

    respuesta = web.post(
        f"{API}base/{informe.pk}/docx-editado/", {"docx_editado": _docx()}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "success": True,
        "messages": [
            {"message": "DOCX enviado a validar correctamente.", "level": "success"}
        ],
        "redirect": f"/comedores/admision/informe_tecnico/base/{informe.pk}/ver/",
    }
    assert _estado(informe) == "Docx editado"
    admision.refresh_from_db()
    assert admision.estado_admision == "informe_tecnico_docx_editado"
    contenedor = InformeTecnicoPDF.objects.get(admision=admision)
    assert contenedor.archivo_docx_editado.name.endswith(".docx")
    assert (contenedor.tipo, contenedor.informe_id) == ("base", informe.pk)
    # The flash message reaches the page that the redirect opens, once.
    detalle = web.get(f"{API}base/{informe.pk}/").json()
    assert detalle["messages"] == [
        {"message": "DOCX enviado a validar correctamente.", "level": "success"}
    ]
    assert web.get(f"{API}base/{informe.pk}/").json()["messages"] == []


def test_upload_without_file_is_rejected_and_changes_nothing(admision, superusuario):
    informe = _generado(admision)

    respuesta = _cliente(superusuario).post(f"{API}base/{informe.pk}/docx-editado/", {})

    assert respuesta.status_code == 400
    assert respuesta.json()["messages"] == [
        {"message": "Debe seleccionar un archivo DOCX.", "level": "error"}
    ]
    assert _estado(informe) == "Docx generado"
    assert not InformeTecnicoPDF.objects.exists()


def test_upload_in_another_state_is_rejected_and_changes_nothing(
    admision, superusuario
):
    informe = _informe(admision, estado="Iniciado", estado_formulario="borrador")

    respuesta = _cliente(superusuario).post(
        f"{API}base/{informe.pk}/docx-editado/", {"docx_editado": _docx()}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["messages"] == [
        {
            "message": "Estado inválido para subir el DOCX editado del informe técnico.",
            "level": "error",
        }
    ]
    assert _estado(informe) == "Iniciado"
    assert not InformeTecnicoPDF.objects.exists()


def test_upload_by_a_reader_who_is_not_the_dupla_technician_is_forbidden(admision):
    informe = _generado(admision)
    lector = _cliente(_usuario("lector_docx", "comedores.view_comedor"))

    respuesta = lector.post(
        f"{API}base/{informe.pk}/docx-editado/", {"docx_editado": _docx()}
    )

    assert respuesta.status_code == 403
    assert _estado(informe) == "Docx generado"
    assert not InformeTecnicoPDF.objects.exists()


def test_actions_keep_the_native_guards_and_the_csrf_check(admision, superusuario):
    informe = _generado(admision)
    destinos = (
        f"{API}base/{informe.pk}/docx-editado/",
        f"{API}base/{informe.pk}/revision/",
    )
    sin_permiso = _cliente(_usuario("sin_permiso_acc"))
    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(superusuario)
    for url in destinos:
        assert Client().post(url, {}).status_code in (401, 403)
        assert sin_permiso.post(url, {}).status_code == 403
        assert con_csrf.post(url, {}).status_code == 403
    web = _cliente(superusuario)
    assert (
        web.post(
            f"{API}base/999999/docx-editado/", {"docx_editado": _docx()}
        ).status_code
        == 404
    )
    assert (
        web.post(
            f"{API}base/999999/revision/",
            {"estado": "Validado"},
            content_type="application/json",
        ).status_code
        == 404
    )
    assert _estado(informe) == "Docx generado"


# --- AD02.02: review of the report --------------------------------------------


def _revision(web, informe, **cuerpo):
    return web.post(
        f"{API}base/{informe.pk}/revision/", cuerpo, content_type="application/json"
    )


def test_review_validates_and_clears_the_pending_fixes(admision, superusuario):
    informe = _informe(
        admision,
        estado="Docx editado",
        estado_formulario="finalizado",
        observaciones_subsanacion="Revisar",
    )
    CampoASubsanar.objects.create(informe=informe, campo="expediente_nro")
    ObservacionGeneralInforme.objects.create(informe=informe, texto="Revisar")

    respuesta = _revision(_cliente(superusuario), informe, estado="Validado")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "success": True,
        "messages": [],
        "redirect": _editor(admision),
    }
    informe.refresh_from_db()
    assert informe.estado == "Validado"
    assert informe.observaciones_subsanacion is None
    assert not CampoASubsanar.objects.filter(informe=informe).exists()
    assert not ObservacionGeneralInforme.objects.filter(informe=informe).exists()
    admision.refresh_from_db()
    assert admision.estado_admision == "informe_tecnico_aprobado"


def test_review_asks_for_fixes_and_replaces_the_previous_ones(admision, superusuario):
    informe = _informe(admision, estado="Docx editado", estado_formulario="finalizado")
    CampoASubsanar.objects.create(informe=informe, campo="localidad_espacio")
    verbose = InformeTecnico._meta.get_field("expediente_nro").verbose_name

    respuesta = _revision(
        _cliente(superusuario),
        informe,
        estado="A subsanar",
        observacion="  Falta el número  ",
        campos_a_subsanar=[str(verbose)],
    )

    assert respuesta.status_code == 200
    informe.refresh_from_db()
    assert informe.estado == "A subsanar"
    assert informe.observaciones_subsanacion == "Falta el número"
    assert list(
        CampoASubsanar.objects.filter(informe=informe).values_list("campo", flat=True)
    ) == ["expediente_nro"]
    assert ObservacionGeneralInforme.objects.get(informe=informe).texto == (
        "Falta el número"
    )
    admision.refresh_from_db()
    assert admision.estado_admision == "informe_tecnico_en_subsanacion"


def test_review_ignores_any_other_state_and_a_malformed_body_is_rejected(
    admision, superusuario
):
    informe = _informe(admision, estado="Docx editado", estado_formulario="finalizado")
    web = _cliente(superusuario)

    sin_efecto = _revision(web, informe, estado="Rechazado")
    assert sin_efecto.status_code == 200
    malformado = _revision(web, informe, estado="Validado", campos_a_subsanar="x")
    assert malformado.status_code == 400
    lista = web.post(
        f"{API}base/{informe.pk}/revision/", [], content_type="application/json"
    )
    assert lista.status_code == 400

    assert _estado(informe) == "Docx editado"
    admision.refresh_from_db()
    assert admision.estado_admision == GENERADO


# --- AD02.02: complementary report --------------------------------------------


def _complementario(admision, informe):
    return InformeComplementario.objects.create(
        admision=admision,
        informe_tecnico=informe,
        estado="rectificar",
        observaciones_legales="Corregir la dirección",
    )


def test_complementary_detail_projects_the_native_context(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    complementario = _complementario(admision, informe)
    InformeComplementarioCampos.objects.create(
        informe_complementario=complementario, campo="Fecha", value="01/11/2026"
    )
    web = _cliente(_usuario("lector_comp", "comedores.view_comedor"))

    respuesta = web.get(f"{API}complementario/base/{informe.pk}/")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == informe.pk
    assert datos["comedor"] == "Comedor Acciones"
    assert datos["origen_acompanamiento"] is False
    assert datos["observaciones_legales"] == "Corregir la dirección"
    assert datos["campos_modificados"] == {"Fecha": "01/11/2026"}
    assert datos["urls"] == {
        "volver": _editor(admision),
        "pagina": f"{NATIVO}base/{informe.pk}/ver/",
        "accion": f"{NATIVO}base/{informe.pk}/ver/",
    }
    grupos = datos["grupos"]
    assert grupos and all(g["tipo"] in ("campos", "matriz") for g in grupos)
    primero = next(g for g in grupos if g["tipo"] == "campos")
    assert {"identificador", "nombre", "valor"} <= set(primero["campos"][0])
    assert datos["messages"] == []
    acompanamiento = web.get(
        f"{API}complementario/base/{informe.pk}/?origen=acompanamiento"
    ).json()
    assert acompanamiento["origen_acompanamiento"] is True
    assert acompanamiento["urls"]["volver"].endswith(f"?admision_id={admision.pk}")
    assert acompanamiento["urls"]["pagina"].endswith("?origen=acompanamiento")


def test_complementary_detail_keeps_the_native_guards(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    url = f"{API}complementario/base/{informe.pk}/"

    assert Client().get(url).status_code in (401, 403)
    assert _cliente(_usuario("sin_permiso_comp")).get(url).status_code == 403
    lector = _cliente(_usuario("lector_comp2", "comedores.view_comedor"))
    assert lector.get(f"{API}complementario/base/999999/").status_code == 404
    assert lector.get(f"{API}complementario/juridico/{informe.pk}/").status_code == 404


def test_complementary_post_stores_the_changes_and_sends_them_to_validation(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    web = _cliente(_usuario("editor_comp", "comedores.view_comedor"))

    respuesta = web.post(
        f"{API}complementario/base/{informe.pk}/",
        {"values": {"Fecha": " 02/11/2026 ", "Vacío": "   "}},
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "success": True,
        "messages": [
            {
                "message": "Informe complementario enviado para validación.",
                "level": "success",
            }
        ],
        "redirect": _editor(admision),
    }
    complementario = InformeComplementario.objects.get(admision=admision)
    assert complementario.estado == "enviado_validacion"
    assert complementario.informe_tecnico_id == informe.pk
    assert complementario.creado_por.username == "editor_comp"
    assert dict(
        InformeComplementarioCampos.objects.filter(
            informe_complementario=complementario
        ).values_list("campo", "value")
    ) == {"Fecha": "02/11/2026"}
    admision.refresh_from_db()
    assert admision.estado_legales == "Informe Complementario Enviado"


def test_complementary_post_replaces_the_fields_of_the_open_draft(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    complementario = _complementario(admision, informe)
    InformeComplementarioCampos.objects.create(
        informe_complementario=complementario, campo="Viejo", value="x"
    )
    web = _cliente(_usuario("editor_comp2", "comedores.view_comedor"))

    respuesta = web.post(
        f"{API}complementario/base/{informe.pk}/?origen=acompanamiento",
        {"values": {"Nuevo": "y"}},
        content_type="application/json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"].endswith(f"?admision_id={admision.pk}")
    assert InformeComplementario.objects.count() == 1
    complementario.refresh_from_db()
    assert complementario.estado == "enviado_validacion"
    assert dict(InformeComplementarioCampos.objects.values_list("campo", "value")) == {
        "Nuevo": "y"
    }


def test_complementary_post_without_changes_is_rejected_and_stores_nothing(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    web = _cliente(_usuario("editor_comp3", "comedores.view_comedor"))
    url = f"{API}complementario/base/{informe.pk}/"

    vacio = web.post(url, {"values": {"Fecha": "  "}}, content_type="application/json")
    assert vacio.status_code == 400
    assert vacio.json()["messages"] == [
        {"message": "No se han realizado cambios en el informe.", "level": "error"}
    ]
    assert vacio.json()["redirect"] == f"{NATIVO}base/{informe.pk}/ver/"
    for malformado in ({}, {"values": []}, {"values": {"Fecha": 1}}):
        assert (
            web.post(url, malformado, content_type="application/json").status_code
            == 400
        )
    assert not InformeComplementario.objects.exists()
    assert not InformeComplementarioCampos.objects.exists()
    admision.refresh_from_db()
    assert admision.estado_legales != "Informe Complementario Enviado"
    # The rejection message shows once on the reloaded page.
    assert web.get(url).json()["messages"][0]["level"] == "error"


# --- AD02.02: local preview of the complementary page -------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("informe_complementario_preview_test_urls")
    module.urlpatterns = complementario_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_the_preview_gets_the_frozen_index_after_the_native_guards(admision):
    informe = _informe(admision, estado="Validado", estado_formulario="finalizado")
    url = f"{NATIVO}base/{informe.pk}/ver/"
    web = _cliente(_usuario("lector_prev_comp", "comedores.view_comedor"))

    respuesta = web.get(url)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "csrftoken" in respuesta.cookies
    assert Client().get(url).status_code in (302, 403)
    assert _cliente(_usuario("sin_permiso_prev")).get(url).status_code == 403
    assert web.get(f"{NATIVO}base/999999/ver/").status_code == 404
    # The native POST stays native.
    enviado = web.post(url, {"campo_Fecha": "03/11/2026"})
    assert enviado.status_code == 302
    assert InformeComplementario.objects.get().estado == "enviado_validacion"
