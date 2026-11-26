"""Web API (G1 v1) of the monthly rendición detail (RM01.01).

``/api/web/comedores/rendicioncuentasmensual/<pk>/`` runs the native
``RendicionCuentaMensualDetailView``. The tests compare every projected value
with the native HTML page and pin today's access: any of the five codes of
``rendicioncuentasmensual/urls.py`` and no object scope. Writes stay the native
POST of the detail URL; the API is read-only.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import Client

from comedores.models import Comedor
from core import web_gate
from organizaciones.models import Organizacion
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
    SolicitudDocumentoFaltante,
)

NATIVO = "/rendicioncuentasmensual/rendicioncuentasmensual/detalle/{}/"
CODES = [
    "rendicioncuentasmensual.view_rendicioncuentamensual",
    "rendicioncuentasmensual.manage_territorial_stage",
    "rendicioncuentasmensual.manage_auditoria_review_stage",
    "rendicioncuentasmensual.manage_auditoria_stage",
    "rendicioncuentasmensual.manage_regularizacion_stage",
]
R = RendicionCuentaMensual
D = DocumentacionAdjunta

pytestmark = pytest.mark.django_db


def _api(pk):
    return f"/api/web/comedores/rendicioncuentasmensual/{pk}/"


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _permiso(code):
    app, codename = code.split(".")
    return Permission.objects.get(content_type__app_label=app, codename=codename)


def _usuario(nombre, *codes, **extra):
    usuario = _ready(get_user_model().objects.create_user(nombre, **extra))
    for code in codes:
        usuario.user_permissions.add(_permiso(code))
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


def _rendicion(**extra):
    organizacion = Organizacion.objects.create(nombre="Org <Norte>")
    comedor = Comedor.objects.create(
        nombre="Comedor RM", organizacion=organizacion, codigo_de_proyecto="P-77"
    )
    otro = Comedor.objects.create(
        nombre="Comedor Hermano", organizacion=organizacion, codigo_de_proyecto="P-77"
    )
    creador = get_user_model().objects.create_user(
        "creador_rm", first_name="Ana", last_name="Pérez"
    )
    datos = {
        "comedor": comedor,
        "mes": 3,
        "anio": 2026,
        "convenio": "P01",
        "numero_rendicion": 2,
        "nombre": "Rendición marzo",
        "observaciones": "Obs <b>generales</b>",
        "periodo_inicio": date(2026, 3, 1),
        "periodo_fin": date(2026, 3, 31),
        "etapa_proceso": R.ETAPA_REVISION_DOCUMENTACION,
        "subestado_proceso": R.SUBESTADO_EN_CURSO,
        "usuario_creador": creador,
    }
    datos.update(extra)
    rendicion = R.objects.create(**datos)
    assert otro.pk
    return rendicion


def _documento(rendicion, categoria, nombre, **extra):
    documento = D(
        rendicion_cuenta_mensual=rendicion,
        categoria=categoria,
        nombre=nombre,
        **extra,
    )
    documento.archivo.save(f"{nombre}.pdf", ContentFile(b"%PDF-1.4"), save=False)
    documento.save()
    return documento


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_det_rm", CODES[0])


@pytest.fixture(name="territorial")
def territorial_fixture():
    return _usuario("territorial_det_rm", CODES[1])


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


def _nativa(client, pk):
    respuesta = client.get(NATIVO.format(pk))
    assert respuesta.status_code == 200
    return respuesta


# --- Access ----------------------------------------------------------------------


def test_anonymous_is_401_and_no_permission_is_403():
    rendicion = _rendicion()

    assert Client().get(_api(rendicion.pk)).status_code == 401
    assert _client(_usuario("sin_det_rm")).get(_api(rendicion.pk)).status_code == 403


@pytest.mark.parametrize("code", CODES)
def test_each_of_the_five_codes_reads_any_rendicion(code):
    rendicion = _rendicion()

    respuesta = _client(_usuario(f"u_{code.split('.')[1]}", code)).get(
        _api(rendicion.pk)
    )

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert respuesta.json()["rendicion"]["id"] == rendicion.pk


def test_pending_web_prerequisite_is_403_with_state(lector):
    rendicion = _rendicion()
    profile = lector.profile
    profile.must_change_password = True
    profile.save()

    respuesta = _client(lector).get(_api(rendicion.pk))

    assert respuesta.status_code == 403
    assert "state" in respuesta.json()
    assert web_gate  # the gate module stays the one the other endpoints use


def test_missing_or_deleted_rendicion_is_404(web):
    rendicion = _rendicion()
    rendicion.delete()

    assert web.get(_api(rendicion.pk)).status_code == 404
    assert web.get(_api(rendicion.pk + 999)).status_code == 404
    assert web.get(NATIVO.format(rendicion.pk)).status_code == 404


def test_api_is_read_only(web):
    rendicion = _rendicion()

    assert web.post(_api(rendicion.pk)).status_code == 405


# --- Projection ------------------------------------------------------------------


def test_header_and_data_match_the_native_page(web):
    rendicion = _rendicion()

    datos = web.get(_api(rendicion.pk)).json()["rendicion"]
    html = _nativa(web, rendicion.pk).content.decode()

    assert datos["numero"] == "2"
    assert datos["nombre"] == "Rendición marzo"
    assert datos["proyecto"] == "P-77"
    assert datos["organizacion"] == "Org <Norte>"
    assert datos["convenio"] == "P01"
    assert datos["linea_programatica"] == "Abordaje Comunitario - Linea Tradicional"
    assert datos["mes_anio"] == "3 / 2026"
    assert datos["periodo"] == "01/03/2026 - 31/03/2026"
    assert datos["comedores_relacionados"] == ["Comedor Hermano", "Comedor RM"]
    assert datos["usuario_creador"] == "Ana Pérez"
    assert datos["usuario_ultima_modificacion"] == "Sin dato"
    assert datos["observaciones"] == "Obs <b>generales</b>"
    assert datos["estado_proceso_display"] == rendicion.estado_proceso_display
    assert f"<h2 class=\"mb-0 fw-bold\">Rendicion {datos['numero']}</h2>" in html
    assert "Org &lt;Norte&gt;" in html
    assert "3 / 2026" in html
    assert "01/03/2026 - 31/03/2026" in html
    assert datos["fecha_creacion"] in html
    assert datos["ultima_modificacion"] in html


def test_empty_values_use_the_native_fallbacks(web):
    rendicion = R.objects.create(
        mes=5,
        anio=2025,
        etapa_proceso=R.ETAPA_REVISION_AUDITORIA,
        subestado_proceso=R.SUBESTADO_PENDIENTE_CORRECCIONES,
    )

    datos = web.get(_api(rendicion.pk)).json()["rendicion"]

    assert datos["numero"] == str(rendicion.pk)
    assert datos["nombre"] == "Sin dato"
    assert datos["proyecto"] == "Sin proyecto"
    assert datos["organizacion"] == "Sin organizacion"
    assert datos["convenio"] == "Sin dato"
    assert datos["periodo"] == "Sin dato"
    assert datos["comedores_relacionados"] == []
    assert datos["usuario_creador"] == "Sin dato"
    assert datos["observaciones"] == ""
    assert datos["validada"] == "No"
    assert datos["genera_acta_text"] == "Sin definir"


def test_documents_by_category_match_the_native_table(web):
    rendicion = _rendicion()
    original = _documento(
        rendicion, D.CATEGORIA_OTROS, "adicional", estado=D.ESTADO_SUBSANAR
    )
    original.observaciones = "Falta firma"
    original.save()
    hijo = _documento(
        rendicion,
        D.CATEGORIA_OTROS,
        "adicional-corregido",
        documento_subsanado=original,
    )
    validado = _documento(
        rendicion, D.CATEGORIA_FORMULARIO_II, "resumen", estado=D.ESTADO_VALIDADO
    )
    SolicitudDocumentoFaltante.objects.create(
        rendicion=rendicion,
        categoria=D.CATEGORIA_EXTRACTO_BANCARIO,
        observaciones="Subir extracto",
        activa=True,
    )

    datos = web.get(_api(rendicion.pk)).json()
    html = _nativa(web, rendicion.pk).content.decode()

    categorias = {c["codigo"]: c for c in datos["documentacion"]}
    assert categorias["formulario_ii"]["required"] is True
    assert categorias["formulario_ii"]["archivos"][0]["badge"] == "validado"
    assert categorias["formulario_ii"]["archivos"][0]["estado_text"] == "Validado"
    otros = categorias["otros"]
    assert otros["historial_plano"] is True
    # The newest document of the chain is the principal; the older one is history.
    assert otros["archivos"][0]["id"] == hijo.pk
    assert otros["archivos"][0]["badge"] == "pendiente"
    historial = otros["archivos"][0]["subsanaciones"]
    assert [s["id"] for s in historial] == [original.pk]
    assert historial[0]["estado_text"] == "Subsanado"
    assert historial[0]["observaciones"] == "Falta firma"
    assert categorias["extracto_bancario"]["solicitud_faltante"] == {
        "observaciones": "Subir extracto"
    }
    assert categorias["extracto_bancario"]["archivos"] == []
    for documento in (original, hijo, validado):
        ver = f"/rendicioncuentasmensual/rendicioncuentasmensual/documento/{documento.pk}/ver/"
        assert ver in html
    assert "No hay archivos cargados en esta categoria." in html
    assert "Documento faltante solicitado" in html


def test_viewed_document_carries_the_native_tooltip(web, lector):
    rendicion = _rendicion()
    documento = _documento(rendicion, D.CATEGORIA_FORMULARIO_II, "resumen")
    documento.visualizacion_etapa = rendicion.etapa_proceso
    documento.visualizacion_usuario = lector
    documento.visualizacion_fecha = rendicion.fecha_creacion
    documento.save()

    archivo = web.get(_api(rendicion.pk)).json()["documentacion"][0]["archivos"][0]
    html = _nativa(web, rendicion.pk).content.decode()

    assert archivo["visualizado"] is True
    assert f'title="{archivo["visualizacion_title"]}"' in html


def test_capabilities_equal_the_native_context(territorial):
    rendicion = _rendicion()
    cliente = _client(territorial)

    capabilities = cliente.get(_api(rendicion.pk)).json()["capabilities"]
    contexto = cliente.get(NATIVO.format(rendicion.pk)).context

    assert capabilities["puede_revisar_documentos"] is True
    assert capabilities["puede_solicitar_faltantes"] is True
    assert capabilities["mostrar_acciones_proceso"] is True
    for nombre, valor in capabilities.items():
        assert valor == bool(contexto[nombre]), nombre


def test_reader_without_stage_permission_has_no_actions(web):
    rendicion = _rendicion()

    capabilities = web.get(_api(rendicion.pk)).json()["capabilities"]

    assert not any(
        capabilities[nombre]
        for nombre in (
            "puede_revisar_documentos",
            "puede_solicitar_faltantes",
            "mostrar_acciones_proceso",
            "puede_editar_datos",
        )
    )


def test_superuser_gets_every_stage_capability():
    rendicion = _rendicion(
        etapa_proceso=R.ETAPA_AUDITORIA,
        subestado_proceso=R.SUBESTADO_PENDIENTE,
    )
    admin = _ready(
        get_user_model().objects.create_superuser("admin_det_rm", password="x")
    )

    datos = _client(admin).get(_api(rendicion.pk)).json()

    assert datos["capabilities"]["puede_gestionar_auditoria"] is True
    assert datos["capabilities"]["puede_editar_datos"] is True
    assert datos["urls"]["auditoria"].endswith(f"/auditoria/{rendicion.pk}/")
    assert datos["urls"]["update"].endswith(f"/editar/{rendicion.pk}/")


def test_audit_card_and_summaries_follow_the_native_context(web):
    rendicion = _rendicion(
        etapa_proceso=R.ETAPA_AUDITORIA,
        subestado_proceso=R.SUBESTADO_FINALIZADA_CON_OBSERVACIONES,
        validada=True,
        genera_acta_auditoria=True,
    )
    rendicion.acta_auditoria.save("acta.pdf", ContentFile(b"%PDF-1.4"), save=True)
    _documento(rendicion, D.CATEGORIA_FORMULARIO_II, "resumen")

    datos = web.get(_api(rendicion.pk)).json()
    html = _nativa(web, rendicion.pk).content.decode()

    assert datos["rendicion"]["validada"] == "Sí"
    assert datos["rendicion"]["genera_acta_text"] == "Sí"
    assert (
        datos["rendicion"]["resultado_auditoria"]
        == "Auditoría finalizada con observaciones"
    )
    assert datos["rendicion"]["acta_auditoria_url"] in html
    assert datos["capabilities"]["mostrar_documentacion_auditoria"] is True
    resumen = datos["resumenes"][0]
    assert resumen["actual"] is True
    assert resumen["titulo"] in " ".join(html.split())
    assert resumen["documentos"][0]["nombre"] == "resumen"


def test_pending_messages_are_consumed_like_the_page(territorial):
    rendicion = _rendicion(subestado_proceso=R.SUBESTADO_PENDIENTE)
    cliente = _client(territorial)
    cliente.post(
        NATIVO.format(rendicion.pk),
        {"accion_proceso": "iniciar_revision_territorial"},
    )

    primero = cliente.get(_api(rendicion.pk)).json()["messages"]
    segundo = cliente.get(_api(rendicion.pk)).json()["messages"]

    assert primero == [
        {"message": "Estado de la rendición actualizado.", "level": "success"}
    ]
    assert segundo == []
