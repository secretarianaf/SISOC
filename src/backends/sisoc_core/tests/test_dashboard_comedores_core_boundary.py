"""Métricas autorizadas en el dueño y última muestra completa en el portal."""

from datetime import date
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from comedores.models import Comedor, ValorComida
from core.internal_services import RespuestaInterna
from dashboard.comedores_metrics import METRIC_KEYS, actualizar_metricas_comedores
from dashboard.models import Dashboard

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_metrics():
    user = get_user_model().objects.create_user(username="metricas")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="dashboard", codename="view_dashboard"
        )
    )
    request = RequestFactory().get("/dashboard/")
    request.user = user
    return request


def test_calculo_preserva_semantica_y_normalizacion(request_metrics):
    Comedor.objects.create(nombre="Espacio de prueba")
    ValorComida.objects.create(
        tipo="desayuno", valor=Decimal("12.50"), fecha=date.today()
    )
    assert actualizar_metricas_comedores(request_metrics)
    data = dict(Dashboard.objects.values_list("llave", "cantidad"))
    assert data == dict(zip(METRIC_KEYS, (1, 0, 12, 0, 0)))


@pytest.mark.parametrize(
    "response",
    [
        RespuestaInterna(503, None),
        RespuestaInterna(403, {}),
        RespuestaInterna(200, {"cantidad_comedores_activos": 999}),
        RespuestaInterna(200, {key: True for key in METRIC_KEYS}),
        RespuestaInterna(200, {key: "9" for key in METRIC_KEYS}),
        RespuestaInterna(200, {key: 2**63 for key in METRIC_KEYS}),
        RespuestaInterna(200, []),
    ],
)
def test_falla_no_reemplaza_ni_mezcla_muestra(request_metrics, mocker, response):
    previous = {key: index + 10 for index, key in enumerate(METRIC_KEYS)}
    previous["otra_metrica"] = 42
    for key, value in previous.items():
        Dashboard.objects.create(llave=key, cantidad=value)
    mocker.patch(
        "dashboard.comedores_metrics.pedir_json_interno", return_value=response
    )
    assert not actualizar_metricas_comedores(request_metrics)
    assert dict(Dashboard.objects.values_list("llave", "cantidad")) == previous


def test_reemplazo_completo_es_atomico(request_metrics, mocker):
    for key in METRIC_KEYS:
        Dashboard.objects.create(llave=key, cantidad=7)
    mocker.patch(
        "dashboard.comedores_metrics.pedir_json_interno",
        return_value=RespuestaInterna(200, {key: 99 for key in METRIC_KEYS}),
    )
    original = Dashboard.objects.update_or_create

    def fail_after_first(*args, **kwargs):
        if kwargs["llave"] == METRIC_KEYS[1]:
            raise RuntimeError("fallo antes del commit")
        return original(*args, **kwargs)

    mocker.patch.object(
        Dashboard.objects, "update_or_create", side_effect=fail_after_first
    )
    with pytest.raises(RuntimeError):
        actualizar_metricas_comedores(request_metrics)
    assert set(Dashboard.objects.values_list("cantidad", flat=True)) == {7}


def test_endpoint_revalida_permiso_y_no_confia_en_id_cliente(request_metrics):
    user = get_user_model().objects.create_user(username="sin_permiso_metricas")
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.get(
        "/api/comedores/metricas-dashboard/",
        HTTP_X_USER_ID=str(request_metrics.user.pk),
    )
    assert response.status_code == 403
    client.credentials()
    assert client.get("/api/comedores/metricas-dashboard/").status_code in (401, 403)


def test_sin_muestra_no_inventa_ceros(request_metrics, mocker):
    mocker.patch(
        "dashboard.comedores_metrics.pedir_json_interno",
        return_value=RespuestaInterna(503, None),
    )
    assert not actualizar_metricas_comedores(request_metrics)
    assert not Dashboard.objects.exists()


def test_pantalla_muestra_muestra_anterior_y_aviso(client, request_metrics, mocker):
    for key in METRIC_KEYS:
        Dashboard.objects.create(llave=key, cantidad=123)
    mocker.patch(
        "dashboard.comedores_metrics.pedir_json_interno",
        return_value=RespuestaInterna(503, None),
    )
    client.force_login(request_metrics.user)
    response = client.get("/dashboard/centro-de-familia")
    assert response.status_code == 200
    assert response.context["cantidad_comedores_activos"] == 123
    assert response.context["metricas_comedores_desactualizadas"] is True
    assert "últimos valores disponibles" in response.content.decode()
    assert '<div class="card-amount">123</div>' in response.content.decode()


def test_pantalla_sin_muestra_informa_ausencia(client, request_metrics, mocker):
    mocker.patch(
        "dashboard.comedores_metrics.pedir_json_interno",
        return_value=RespuestaInterna(503, None),
    )
    client.force_login(request_metrics.user)
    response = client.get("/dashboard/centro-de-familia")
    assert response.context["cantidad_comedores_activos"] is None
    assert "Todavía no hay información disponible" in response.content.decode()
    assert "Sin información" in response.content.decode()
