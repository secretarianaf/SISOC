"""Issue #2789: operaciones de soporte y listados del admin de Inspecciones."""

from auditlog.models import LogEntry
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from core.admin_operaciones import ejecutar_operacion
from inspecciones import admin as inspecciones_admin
from inspecciones.models import Acta, AsignacionEscuela, Escuela

pytestmark = pytest.mark.django_db

MOTIVO = "Acta cargada sobre la escuela equivocada"


def _acta(client, cerrar, escuela_obj=None):
    _, respuesta = cerrar(client, escuela_obj)
    assert respuesta.status_code == 200, respuesta.json()
    return Acta.objects.get(numero=respuesta.json()["numero"])


def _operacion(model, slug):
    model_admin = admin.site.get_model_admin(model)
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(model, slug, obj, usuario, **datos):
    return ejecutar_operacion(
        operacion=_operacion(model, slug),
        objetos=[obj],
        usuario=usuario,
        datos={"motivo": MOTIVO, **datos},
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


def test_anular_llama_al_service(mocker, api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)
    servicio = mocker.patch.object(inspecciones_admin, "anular_acta")

    ok, _ = _ejecutar(Acta, "anular", acta, superuser)

    assert ok == [acta]
    servicio.assert_called_once_with(acta, MOTIVO, superuser)
    assert _auditado(acta, "anular")


@pytest.mark.parametrize("valor, esperado", [("1", True), ("0", False)])
def test_marcar_prueba_llama_al_service(
    mocker, api_a, cerrar, superuser, valor, esperado
):
    acta = _acta(api_a, cerrar)
    # Parte de la marca contraria: sin cambio, la operación es un error.
    Acta.objects.filter(pk=acta.pk).update(es_prueba=not esperado)
    acta.refresh_from_db()
    servicio = mocker.patch.object(inspecciones_admin, "marcar_prueba")

    ok, _ = _ejecutar(Acta, "marcar_prueba", acta, superuser, es_prueba=valor)

    assert ok == [acta]
    servicio.assert_called_once_with(acta, esperado, superuser)
    assert _auditado(acta, "marcar_prueba")


def test_marcar_prueba_real_cambia_la_marca(api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)

    ok, errores = _ejecutar(Acta, "marcar_prueba", acta, superuser, es_prueba="1")

    assert ok == [acta] and errores == []
    acta.refresh_from_db()
    assert acta.es_prueba
    entrada = LogEntry.objects.get(
        object_pk=str(acta.pk), additional_data__operacion="marcar_prueba"
    )
    assert entrada.changes_dict == {"es_prueba": ["False", "True"]}


def test_anular_dos_veces_es_error(api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)
    _ejecutar(Acta, "anular", acta, superuser)

    ok, errores = _ejecutar(Acta, "anular", acta, superuser)

    assert not ok
    assert errores == [(acta, f"El acta {acta.numero} ya está anulada.")]


def test_anular_por_url_del_admin(auth_client, api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)
    url = reverse("admin:inspecciones_acta_operacion_anular", args=[acta.pk])

    corto = auth_client.post(url, {"confirmar_operacion": "1", "motivo": "corto"})
    respuesta = auth_client.post(url, {"confirmar_operacion": "1", "motivo": MOTIVO})

    # El form pide el mismo mínimo de caracteres que el service.
    assert corto.status_code == 200
    assert respuesta.status_code == 302
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA
    assert acta.anulada_por == superuser
    assert acta.motivo_anulacion == MOTIVO
    entrada = LogEntry.objects.get(
        object_pk=str(acta.pk), additional_data__operacion="anular"
    )
    assert entrada.changes_dict == {"estado": ["finalizada", "anulada"]}


def test_quitar_asignacion_llama_al_service(mocker, asignada_a, superuser):
    servicio = mocker.patch.object(inspecciones_admin, "quitar_asignacion")

    ok, _ = _ejecutar(AsignacionEscuela, "quitar", asignada_a, superuser)

    assert ok == [asignada_a]
    servicio.assert_called_once_with(asignada_a, actor=superuser)
    assert _auditado(asignada_a, "quitar")


def test_quitar_asignacion_real_es_baja_logica(asignada_a, superuser):
    ok, errores = _ejecutar(AsignacionEscuela, "quitar", asignada_a, superuser)

    assert ok == [asignada_a] and errores == []
    assert not AsignacionEscuela.objects.filter(pk=asignada_a.pk).exists()
    borrada = AsignacionEscuela.all_objects.get(pk=asignada_a.pk)
    assert borrada.deleted_by == superuser
    assert _auditado(asignada_a, "quitar")


def test_quitar_asignacion_con_acta_es_error(
    api_a, cerrar, asignada_a, escuela, superuser
):
    _acta(api_a, cerrar, escuela)

    ok, errores = _ejecutar(AsignacionEscuela, "quitar", asignada_a, superuser)

    assert not ok
    assert "ya tiene un acta" in errores[0][1]
    assert AsignacionEscuela.objects.filter(pk=asignada_a.pk).exists()


def test_acta_sigue_de_solo_lectura_en_el_detalle(rf, api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site.get_model_admin(Acta)

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_delete_permission(request, acta)
    assert not model_admin.has_change_permission(request, acta)
    # Sin objeto: habilita las acciones de soporte del listado.
    assert model_admin.has_change_permission(request)
    assert "operacion_anular_lote" in model_admin.get_actions(request)


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


def test_listado_de_actas_sin_n_mas_1(
    auth_client, api_a, cerrar, django_assert_max_num_queries
):
    url = reverse("admin:inspecciones_acta_changelist")

    def _cargar(desde):
        for numero in range(desde, desde + 5):
            escuela = Escuela.objects.create(
                codigo=f"0601{numero:05d}",
                nombre=f"Escuela {numero}",
                cue=f"0601{numero:05d}",
            )
            _acta(api_a, cerrar, escuela)

    _cargar(100)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(200)

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize(
    "modelo", ["acta", "asignacionescuela", "inspeccion", "eventoinspeccion"]
)
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:inspecciones_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_detalles_con_operaciones_cargan(auth_client, api_a, cerrar, asignada_a):
    acta = _acta(api_a, cerrar)

    for nombre, obj in (("acta", acta), ("asignacionescuela", asignada_a)):
        url = reverse(f"admin:inspecciones_{nombre}_change", args=[obj.pk])
        assert auth_client.get(url).status_code == 200


def test_marcar_prueba_sin_cambio_es_error(mocker, api_a, cerrar, superuser):
    acta = _acta(api_a, cerrar)
    servicio = mocker.patch.object(inspecciones_admin, "marcar_prueba")

    ok, errores = _ejecutar(Acta, "marcar_prueba", acta, superuser, es_prueba="0")

    assert not ok
    assert errores == [(acta, "El acta ya tiene esa marca.")]
    servicio.assert_not_called()
