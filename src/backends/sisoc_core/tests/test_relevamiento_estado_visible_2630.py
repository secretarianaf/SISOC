"""#2630: un relevamiento finalizado desde la app que espera la validación del
coordinador se muestra en SISOC como "Pendiente de validación".

Solo cambia lo que se muestra: ``estado`` sigue guardando "Finalizado" porque
de ese valor dependen la sincronización con GESTIONAR, el botón de PDF y los
servicios de comedores.
"""

import re
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import Relevamiento
from relevamientos.service import RelevamientoService
from relevamientos.views.web_views import RelevamientoDetailView, RelevamientoListView

PENDIENTE = Relevamiento.ESTADO_VALIDACION_PENDIENTE


@pytest.mark.parametrize("estado", ["Finalizado", "Finalizado/Excepciones"])
def test_finalizado_pendiente_de_validacion_se_muestra_pendiente(estado):
    assert (
        RelevamientoService.estado_para_mostrar(estado, PENDIENTE)
        == "Pendiente de validación"
    )


@pytest.mark.parametrize(
    "estado,estado_validacion",
    [
        # Históricos sin circuito de validación: no deben pasar a pendientes.
        ("Finalizado", None),
        ("Finalizado", ""),
        ("Finalizado", Relevamiento.ESTADO_VALIDACION_VALIDADO),
        ("Finalizado", Relevamiento.ESTADO_VALIDACION_A_SUBSANAR),
        ("Visita pendiente", PENDIENTE),
        ("En Proceso", PENDIENTE),
    ],
)
def test_otros_casos_muestran_el_estado_guardado(estado, estado_validacion):
    assert RelevamientoService.estado_para_mostrar(estado, estado_validacion) == estado


def test_estado_vacio_se_mantiene_vacio():
    assert RelevamientoService.estado_para_mostrar(None, PENDIENTE) is None


def _mock_list_view(mocker, relevamientos):
    mocker.patch("relevamientos.views.web_views.ActaComplementaria.objects")
    mocker.patch("relevamientos.views.web_views.SeguimientoPnud.objects")
    mocker.patch(
        "relevamientos.views.web_views._opciones_del_popup", return_value=([], [])
    )
    mocker.patch(
        "django.views.generic.list.MultipleObjectMixin.get_context_data",
        return_value={"relevamientos": relevamientos},
    )
    mocker.patch(
        "relevamientos.views.web_views.Comedor.objects.values",
        mocker.Mock(return_value=SimpleNamespace(get=lambda **_: {"id": 5})),
    )


def test_listado_del_comedor_muestra_pendiente_de_validacion(mocker):
    rel = SimpleNamespace(
        id=8867,
        fecha_visita="2026-10-01",
        estado="Finalizado",
        estado_validacion=PENDIENTE,
        numero_if=None,
        sincronizado_gestionar=True,
        seguimientos=SimpleNamespace(all=list),
        origen="app",
    )
    _mock_list_view(mocker, [rel])
    view = RelevamientoListView()
    view.kwargs = {"comedor_pk": 5}

    context = view.get_context_data()

    assert context["relevamientos_items"][0]["estado"] == "Pendiente de validación"


def _mock_detail_view(mocker, timeline):
    mocker.patch(
        "django.views.generic.detail.SingleObjectMixin.get_context_data",
        return_value={},
    )
    mocker.patch(
        "relevamientos.views.web_views.Relevamiento.objects.filter",
        return_value=SimpleNamespace(
            only=lambda *a, **k: SimpleNamespace(order_by=lambda *x, **y: timeline)
        ),
    )


def test_detalle_muestra_pendiente_de_validacion_en_titulo_y_timeline(mocker):
    relevamiento = SimpleNamespace(
        seguimientos=SimpleNamespace(all=list),
        id=8868,
        comedor=SimpleNamespace(id=205577),
        estado="Finalizado/Excepciones",
        estado_validacion=PENDIENTE,
        prestacion=None,
        espacio=None,
        recursos=None,
        punto_entregas=None,
    )
    timeline = [
        SimpleNamespace(
            id=8867,
            fecha_visita="2026-10-01",
            estado="Finalizado",
            estado_validacion=Relevamiento.ESTADO_VALIDACION_VALIDADO,
        ),
        SimpleNamespace(
            id=8868,
            fecha_visita="2026-09-29",
            estado="Finalizado/Excepciones",
            estado_validacion=PENDIENTE,
        ),
    ]
    _mock_detail_view(mocker, timeline)
    view = RelevamientoDetailView()
    view.object = relevamiento

    context = view.get_context_data()

    assert context["estado_visible"] == "Pendiente de validación"
    estados = {item["id"]: item for item in context["relevamientos_timeline"]}
    assert estados[8867]["estado"] == "Finalizado"
    assert estados[8867]["status_class"] == "finalizado"
    assert estados[8868]["estado"] == "Pendiente de validación"
    # Mientras espera al coordinador no se pinta como finalizado.
    assert estados[8868]["status_class"] == "pendiente"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado_validacion,esperado",
    [(PENDIENTE, "Pendiente de validación"), (None, "Finalizado")],
)
def test_pantallas_renderizan_el_estado_visible(client, estado_validacion, esperado):
    user = get_user_model().objects.create_user(
        username="coord_2630", password="testpass123"
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    client.force_login(user)
    provincia = Provincia.objects.create(nombre="Prov 2630")
    comedor = Comedor.objects.create(nombre="Comedor 2630", provincia=provincia)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor,
        estado="Finalizado",
        estado_validacion=estado_validacion,
    )

    detalle = client.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": relevamiento.id},
        )
    )
    listado = client.get(reverse("relevamientos", kwargs={"comedor_pk": comedor.id}))

    assert detalle.status_code == 200
    assert listado.status_code == 200
    # El título de la página, no la línea de tiempo (que también lo muestra).
    titulo = re.compile(r'<span class="ml-2 h5"[^>]*>\s*' + re.escape(esperado))
    assert titulo.search(detalle.content.decode())
    assert esperado in listado.content.decode()
    if estado_validacion == PENDIENTE:
        assert "Finalizado" not in listado.content.decode()
