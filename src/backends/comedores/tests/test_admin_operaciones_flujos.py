"""Issue #2789: operaciones de soporte del admin en los flujos de comedores.

Admisiones, rendición de cuentas mensual y relevamientos: cada operación llama
al service existente y deja un LogEntry de auditlog con la operación.
"""

from auditlog.models import LogEntry
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from admisiones import admin as admisiones_admin
from admisiones.models.admisiones import Admision
from comedores.models import Comedor
from core.admin_operaciones import ejecutar_operacion
from relevamientos import admin as relevamientos_admin
from relevamientos.models import PrimerSeguimiento, Relevamiento
from rendicioncuentasmensual import admin as rendicion_admin
from rendicioncuentasmensual.models import DocumentacionAdjunta, RendicionCuentaMensual

pytestmark = pytest.mark.django_db


def _operacion(model, slug):
    model_admin = admin.site.get_model_admin(model)
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _log_de(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    )


def _ejecutar(model, slug, obj, usuario, motivo=""):
    return ejecutar_operacion(
        operacion=_operacion(model, slug),
        objetos=[obj],
        usuario=usuario,
        datos={"motivo": motivo},
    )


def _comedor(nombre="Comedor admin 2789"):
    return Comedor.objects.create(nombre=nombre)


def _admision(**campos):
    return Admision.objects.create(comedor=_comedor(), **campos)


# --- Admisiones -------------------------------------------------------------


def test_enviar_a_legales_llama_al_service_y_audita(mocker, superuser):
    admision = _admision(estado_admision="if_informe_tecnico_cargado")
    marcar = mocker.patch.object(
        admisiones_admin.AdmisionService,
        "marcar_como_enviado_a_legales",
        return_value=True,
    )
    actualizar = mocker.patch.object(
        admisiones_admin.AdmisionService, "actualizar_estado_admision"
    )

    ok, errores = _ejecutar(Admision, "enviar_legales", admision, superuser)

    assert ok == [admision] and errores == []
    marcar.assert_called_once_with(admision, superuser)
    actualizar.assert_called_once_with(admision, "enviar_a_legales")
    assert _log_de(admision, "enviar_legales").exists()


def test_enviar_a_legales_sin_if_cargado_no_llama_al_service(mocker, superuser):
    admision = _admision(estado_admision="expediente_cargado")
    marcar = mocker.patch.object(
        admisiones_admin.AdmisionService, "marcar_como_enviado_a_legales"
    )

    ok, errores = _ejecutar(Admision, "enviar_legales", admision, superuser)

    assert not ok and len(errores) == 1
    marcar.assert_not_called()
    assert not _log_de(admision, "enviar_legales").exists()


def test_enviar_a_acompaniamiento_repite_la_secuencia_de_la_vista(mocker, superuser):
    admision = _admision(numero_convenio="CONV-1")
    importar = mocker.patch.object(
        admisiones_admin.AcompanamientoService, "importar_datos_desde_admision"
    )
    marcar = mocker.patch.object(
        admisiones_admin.AdmisionService,
        "marcar_como_enviado_a_acompaniamiento",
        return_value=True,
    )
    actualizar = mocker.patch.object(
        admisiones_admin.AdmisionService,
        "actualizar_estado_admision",
        return_value=True,
    )

    ok, _errores = _ejecutar(Admision, "enviar_acompaniamiento", admision, superuser)

    assert ok == [admision]
    importar.assert_called_once_with(admision)
    marcar.assert_called_once_with(admision, superuser)
    actualizar.assert_called_once_with(admision, "enviar_a_acompaniamiento")
    assert _log_de(admision, "enviar_acompaniamiento").exists()


def test_enviar_a_acompaniamiento_sin_convenio_es_error(mocker, superuser):
    admision = _admision()
    importar = mocker.patch.object(
        admisiones_admin.AcompanamientoService, "importar_datos_desde_admision"
    )

    ok, errores = _ejecutar(Admision, "enviar_acompaniamiento", admision, superuser)

    assert not ok and len(errores) == 1
    importar.assert_not_called()


def test_documentacion_rectificada_llama_al_service_y_audita(mocker, superuser):
    admision = _admision(estado_legales="A Rectificar")
    marcar = mocker.patch.object(
        admisiones_admin.AdmisionService,
        "marcar_como_documentacion_rectificada",
        return_value=True,
    )

    ok, _errores = _ejecutar(
        Admision, "documentacion_rectificada", admision, superuser, "Ticket 7"
    )

    assert ok == [admision]
    marcar.assert_called_once_with(admision, superuser)
    entrada = _log_de(admision, "documentacion_rectificada").get()
    assert entrada.additional_data["motivo"] == "Ticket 7"


def test_documentacion_rectificada_fuera_de_a_rectificar_es_error(mocker, superuser):
    admision = _admision(estado_legales="Enviado a Legales")
    marcar = mocker.patch.object(
        admisiones_admin.AdmisionService, "marcar_como_documentacion_rectificada"
    )

    ok, errores = _ejecutar(Admision, "documentacion_rectificada", admision, superuser)

    assert not ok and len(errores) == 1
    marcar.assert_not_called()


def test_enviar_a_legales_por_url_con_el_service_real(auth_client):
    admision = _admision(estado_admision="if_informe_tecnico_cargado")

    response = auth_client.post(
        reverse(
            "admin:admisiones_admision_operacion_enviar_legales", args=[admision.pk]
        ),
        {"confirmar_operacion": "1", "motivo": "Pedido de soporte"},
    )

    assert response.status_code == 302
    admision.refresh_from_db()
    assert admision.enviado_legales is True
    assert admision.estado_legales == "Enviado a Legales"
    assert admision.estado_admision == "enviado_a_legales"
    entrada = _log_de(admision, "enviar_legales").get()
    assert entrada.changes_dict == {
        "estado_admision": ["if_informe_tecnico_cargado", "enviado_a_legales"]
    }


# --- Rendición de cuentas mensual -------------------------------------------


def _documento_en_revision(estado=RendicionCuentaMensual.ESTADO_REVISION):
    rendicion = RendicionCuentaMensual.objects.create(
        comedor=_comedor(),
        mes=1,
        anio=2026,
        estado=estado,
    )
    return DocumentacionAdjunta.objects.create(
        nombre="Formulario I",
        archivo="rendicion/form_i.pdf",
        rendicion_cuenta_mensual=rendicion,
    )


def test_validar_documento_llama_al_service_y_audita(mocker, superuser):
    documento = _documento_en_revision()
    servicio = mocker.patch.object(
        rendicion_admin.RendicionCuentaMensualService,
        "actualizar_estado_documento_revision",
        return_value=documento,
    )

    ok, _errores = _ejecutar(
        DocumentacionAdjunta, "validar_documento", documento, superuser
    )

    assert ok == [documento]
    servicio.assert_called_once_with(
        documento=documento,
        estado=DocumentacionAdjunta.ESTADO_VALIDADO,
        actor=superuser,
    )
    assert _log_de(documento, "validar_documento").exists()


def test_subsanar_documento_pasa_el_motivo_como_observaciones(mocker, superuser):
    documento = _documento_en_revision()
    servicio = mocker.patch.object(
        rendicion_admin.RendicionCuentaMensualService,
        "actualizar_estado_documento_revision",
        return_value=documento,
    )

    _ejecutar(
        DocumentacionAdjunta,
        "subsanar_documento",
        documento,
        superuser,
        "Falta la firma",
    )

    servicio.assert_called_once_with(
        documento=documento,
        estado=DocumentacionAdjunta.ESTADO_SUBSANAR,
        observaciones="Falta la firma",
        actor=superuser,
    )
    assert _log_de(documento, "subsanar_documento").exists()


def test_subsanar_documento_por_url_con_el_service_real(auth_client):
    documento = _documento_en_revision()

    response = auth_client.post(
        reverse(
            "admin:rendicioncuentasmensual_documentacionadjunta_operacion_subsanar_documento",
            args=[documento.pk],
        ),
        {"confirmar_operacion": "1", "motivo": "Falta la firma"},
    )

    assert response.status_code == 302
    documento.refresh_from_db()
    assert documento.estado == DocumentacionAdjunta.ESTADO_SUBSANAR
    assert documento.observaciones == "Falta la firma"
    entrada = _log_de(documento, "subsanar_documento").get()
    assert entrada.changes_dict == {"estado": ["presentado", "subsanar"]}


def test_revision_fuera_de_etapa_la_rechaza_el_service(superuser):
    documento = _documento_en_revision(estado=RendicionCuentaMensual.ESTADO_ELABORACION)

    ok, errores = _ejecutar(
        DocumentacionAdjunta, "validar_documento", documento, superuser
    )

    assert not ok and len(errores) == 1
    documento.refresh_from_db()
    assert documento.estado == DocumentacionAdjunta.ESTADO_PRESENTADO


# --- Relevamientos ----------------------------------------------------------


def _relevamiento(nombre="Comedor relevamiento 2789", **campos):
    return Relevamiento.objects.create(
        comedor=_comedor(nombre), estado="Finalizado", **campos
    )


def test_reintentar_sync_relevamiento_encola_la_tarea_al_confirmar(
    mocker, settings, superuser, django_capture_on_commit_callbacks
):
    relevamiento = _relevamiento()
    settings.GESTIONAR_INTEGRATION_ENABLED = True
    tarea = mocker.patch.object(relevamientos_admin, "AsyncSendRelevamientoToGestionar")

    with django_capture_on_commit_callbacks(execute=True):
        ok, _errores = _ejecutar(
            Relevamiento, "reintentar_sync_gestionar", relevamiento, superuser
        )

    assert ok == [relevamiento]
    tarea.assert_called_once_with(relevamiento.pk)
    tarea.return_value.start.assert_called_once_with()
    assert _log_de(relevamiento, "reintentar_sync_gestionar").exists()


def test_reintentar_sync_ya_sincronizado_o_sin_integracion_es_error(
    mocker, settings, superuser
):
    sincronizado = _relevamiento(sincronizado_gestionar=True)
    pendiente = _relevamiento(nombre="Otro comedor 2789")
    tarea = mocker.patch.object(relevamientos_admin, "AsyncSendRelevamientoToGestionar")

    settings.GESTIONAR_INTEGRATION_ENABLED = False
    _ok, sin_integracion = _ejecutar(
        Relevamiento, "reintentar_sync_gestionar", pendiente, superuser
    )
    settings.GESTIONAR_INTEGRATION_ENABLED = True
    _ok, ya_sincronizado = _ejecutar(
        Relevamiento, "reintentar_sync_gestionar", sincronizado, superuser
    )

    assert len(sin_integracion) == 1 and len(ya_sincronizado) == 1
    tarea.assert_not_called()


def test_reintentar_sync_primer_seguimiento_por_url(
    mocker, settings, auth_client, django_capture_on_commit_callbacks
):
    relevamiento = _relevamiento()
    relevamiento.sincronizado_gestionar = True
    relevamiento.save(update_fields=["sincronizado_gestionar"])
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, estado=PrimerSeguimiento.ESTADO_COMPLETO
    )
    settings.GESTIONAR_INTEGRATION_ENABLED = True
    tarea = mocker.patch.object(
        relevamientos_admin, "AsyncSendPrimerSeguimientoToGestionar"
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse(
                "admin:relevamientos_primerseguimiento_operacion_reintentar_sync_gestionar",
                args=[seguimiento.pk],
            ),
            {"confirmar_operacion": "1", "motivo": ""},
        )

    assert response.status_code == 302
    tarea.assert_called_once_with(seguimiento.pk)
    tarea.return_value.start.assert_called_once_with()
    assert _log_de(seguimiento, "reintentar_sync_gestionar").exists()


# --- N+1 en los listados principales ----------------------------------------


def _crear_admisiones(cantidad, desde):
    for indice in range(desde, desde + cantidad):
        Admision.objects.create(comedor=_comedor(f"Comedor admision {indice}"))


def _crear_rendiciones(cantidad, desde):
    for indice in range(desde, desde + cantidad):
        RendicionCuentaMensual.objects.create(
            comedor=_comedor(f"Comedor rendicion {indice}"), mes=1, anio=2026
        )


def _crear_relevamientos(cantidad, desde):
    for indice in range(desde, desde + cantidad):
        _relevamiento(nombre=f"Comedor relevamiento {indice}")


def _crear_seguimientos(cantidad, desde):
    for indice in range(desde, desde + cantidad):
        PrimerSeguimiento.objects.create(
            id_relevamiento=_relevamiento(nombre=f"Comedor seguimiento {indice}")
        )


def _consultas_del_listado(auth_client, url):
    with CaptureQueriesContext(connection) as consultas:
        response = auth_client.get(url)
    assert response.status_code == 200
    return len(consultas)


@pytest.mark.parametrize(
    ("url_name", "crear"),
    [
        ("admin:admisiones_admision_changelist", _crear_admisiones),
        (
            "admin:rendicioncuentasmensual_rendicioncuentamensual_changelist",
            _crear_rendiciones,
        ),
        ("admin:relevamientos_relevamiento_changelist", _crear_relevamientos),
        ("admin:relevamientos_primerseguimiento_changelist", _crear_seguimientos),
    ],
)
def test_listados_sin_n_mas_1(
    auth_client, django_assert_max_num_queries, url_name, crear
):
    url = reverse(url_name)
    crear(5, 0)
    with django_assert_max_num_queries(10):
        auth_client.get(url)
    con_cinco = _consultas_del_listado(auth_client, url)
    crear(5, 5)

    assert _consultas_del_listado(auth_client, url) == con_cinco


APPS_DE_FLUJOS = (
    "admisiones",
    "rendicioncuentasmensual",
    "rendicioncuentasfinal",
    "relevamientos",
    "importarexpediente",
)


def test_listados_y_busquedas_de_los_flujos_cargan(auth_client):
    # Cubre search_fields y list_filter: un lookup inválido da 500 al buscar.
    _admision()
    modelos = [
        model
        for model in admin.site._registry  # pylint: disable=protected-access
        if model._meta.app_label in APPS_DE_FLUJOS
    ]
    fallas = []
    for model in modelos:
        opts = model._meta
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        for params in ({}, {"q": "1"}):
            status = auth_client.get(url, params).status_code
            if status != 200:
                fallas.append((url, params, status))

    assert len(modelos) > 40
    assert not fallas


@pytest.mark.django_db
def test_reintento_de_seguimiento_exige_relevamiento_sincronizado(
    mocker, settings, superuser
):
    # El alta del seguimiento referencia al relevamiento en GESTIONAR: si el
    # relevamiento no está sincronizado, se pide reintentarlo primero.
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=_relevamiento(), estado=PrimerSeguimiento.ESTADO_COMPLETO
    )
    settings.GESTIONAR_INTEGRATION_ENABLED = True
    tarea = mocker.patch.object(
        relevamientos_admin, "AsyncSendPrimerSeguimientoToGestionar"
    )
    operacion = next(
        op
        for op in admin.site.get_model_admin(PrimerSeguimiento).operaciones
        if op.slug == "reintentar_sync_gestionar"
    )

    ok, errores = ejecutar_operacion(
        operacion=operacion, objetos=[seguimiento], usuario=superuser, datos={}
    )

    assert not ok
    assert "reintentá primero el relevamiento" in errores[0][1]
    tarea.assert_not_called()
