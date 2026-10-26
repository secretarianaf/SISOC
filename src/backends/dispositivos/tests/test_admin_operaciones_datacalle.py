"""Issue #2789: operaciones de soporte y listados del admin de DataCalle."""

import datetime

from auditlog.models import LogEntry
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from core.admin_operaciones import ejecutar_operacion
from core.models import Municipio, Provincia
from datacalle import admin as datacalle_admin
from datacalle.models import Encuesta, Relevamiento

pytestmark = pytest.mark.django_db


@pytest.fixture(name="provincia")
def provincia_fixture():
    return Provincia.objects.create(nombre="Córdoba")


def _relevamiento(provincia, denominacion="Operativo invierno", **extra):
    return Relevamiento.objects.create(
        denominacion=denominacion,
        provincia=provincia,
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 9, 15),
        fecha_fin=datetime.date(2026, 9, 19),
        **extra,
    )


def _operacion(slug):
    model_admin = admin.site._registry[Relevamiento]  # pylint: disable=protected-access
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(slug, relevamiento, usuario):
    return ejecutar_operacion(
        operacion=_operacion(slug),
        objetos=[relevamiento],
        usuario=usuario,
        datos={"motivo": "Pedido de la coordinación"},
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


def test_marcar_en_curso_llama_al_service(mocker, provincia, superuser):
    relevamiento = _relevamiento(provincia)
    servicio = mocker.patch.object(datacalle_admin, "marcar_en_curso")

    ok, _ = _ejecutar("marcar_en_curso", relevamiento, superuser)

    assert ok == [relevamiento]
    servicio.assert_called_once_with(relevamiento)
    assert _auditado(relevamiento, "marcar_en_curso")


def test_marcar_en_curso_fuera_de_planificado_es_error(provincia, superuser):
    relevamiento = _relevamiento(provincia, estado=Relevamiento.Estado.FINALIZADO)

    ok, errores = _ejecutar("marcar_en_curso", relevamiento, superuser)

    assert not ok
    assert errores == [
        (relevamiento, "Solo se marca en curso un relevamiento planificado.")
    ]
    relevamiento.refresh_from_db()
    assert relevamiento.estado == Relevamiento.Estado.FINALIZADO


def test_cerrar_llama_al_service(mocker, provincia, superuser):
    relevamiento = _relevamiento(provincia)
    servicio = mocker.patch.object(
        datacalle_admin, "cerrar_relevamiento", return_value=(relevamiento, True)
    )

    ok, _ = _ejecutar("cerrar", relevamiento, superuser)

    assert ok == [relevamiento]
    servicio.assert_called_once_with(relevamiento=relevamiento, user=superuser)
    assert _auditado(relevamiento, "cerrar")


def test_cerrar_ya_cerrado_es_error_y_no_audita(provincia, superuser):
    relevamiento = _relevamiento(provincia, estado=Relevamiento.Estado.FINALIZADO)

    ok, errores = _ejecutar("cerrar", relevamiento, superuser)

    assert not ok
    assert errores == [(relevamiento, "El relevamiento ya estaba cerrado.")]
    assert not _auditado(relevamiento, "cerrar")


def test_cerrar_por_url_del_admin(auth_client, provincia, superuser):
    relevamiento = _relevamiento(provincia, estado=Relevamiento.Estado.EN_CURSO)
    url = reverse(
        "admin:datacalle_relevamiento_operacion_cerrar", args=[relevamiento.pk]
    )

    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "La app no pudo cerrarlo"}
    )

    assert respuesta.status_code == 302
    relevamiento.refresh_from_db()
    assert relevamiento.estado == Relevamiento.Estado.FINALIZADO
    assert relevamiento.cerrado_por == superuser
    assert relevamiento.fecha_cierre is not None
    entrada = LogEntry.objects.get(
        object_pk=str(relevamiento.pk), additional_data__operacion="cerrar"
    )
    assert entrada.changes_dict == {"estado": ["en_curso", "finalizado"]}


def test_casos_son_de_solo_lectura(rf, superuser):
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site._registry[Encuesta]  # pylint: disable=protected-access

    assert not model_admin.has_add_permission(request)
    assert not model_admin.has_change_permission(request)
    assert not model_admin.has_delete_permission(request)
    assert model_admin.has_view_permission(request)


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize("modelo", [Relevamiento, Encuesta])
def test_listados_sin_n_mas_1(
    auth_client, provincia, superuser, modelo, django_assert_max_num_queries
):
    url = reverse(
        f"admin:datacalle_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )
    municipio = Municipio.objects.create(nombre="Capital", provincia=provincia)

    def _cargar(desde):
        for numero in range(desde, desde + 5):
            relevamiento = _relevamiento(
                provincia, denominacion=f"Operativo {numero}", municipio=municipio
            )
            Encuesta.objects.create(
                relevamiento=relevamiento,
                relevador=superuser,
                estado=Encuesta.Estado.COMPLETA,
            )

    _cargar(100)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(200)

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize("modelo", ["relevamiento", "encuesta"])
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:datacalle_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_listado_de_dispositivos_carga_con_busqueda(auth_client):
    url = reverse("admin:dispositivos_dispositivo_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_detalles_cargan(auth_client, provincia, superuser):
    relevamiento = _relevamiento(provincia)
    encuesta = Encuesta.objects.create(
        relevamiento=relevamiento, relevador=superuser, estado=Encuesta.Estado.COMPLETA
    )

    for nombre, obj in (("relevamiento", relevamiento), ("encuesta", encuesta)):
        url = reverse(f"admin:datacalle_{nombre}_change", args=[obj.pk])
        assert auth_client.get(url).status_code == 200
