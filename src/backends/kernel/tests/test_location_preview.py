"""Geocodificación de borradores: autenticación, validación y sin escrituras."""

from unittest.mock import Mock

import pytest
import requests
from django.test import Client
from django.urls import reverse

from core.location_views import AddressPreviewForm
from core.services.geolocation import locate_address


def test_form_domicilio_y_componentes():
    for data, expected in [
        ({"domicilio": "Av. de Mayo 525"}, "Av. de Mayo 525"),
        ({"calle": "Calle", "altura": "123"}, "Calle 123"),
        ({"calle": "Calle", "numero": "123"}, "Calle 123"),
    ]:
        form = AddressPreviewForm({"provincia": "Buenos Aires", **data})
        assert form.is_valid(), form.errors
        assert form.cleaned_data["address"] == expected
    for data in [{}, {"calle": "Calle"}, {"domicilio": "x" * 501}]:
        assert not AddressPreviewForm({"provincia": "Buenos Aires", **data}).is_valid()


@pytest.mark.django_db
def test_preview_autenticado_sin_acceso_a_legajos(
    client, django_user_model, monkeypatch
):
    user = django_user_model.objects.create_user(username="preview-publica")
    url = reverse("address_preview")
    assert client.post(url).status_code == 302
    client.force_login(user)
    lookup = Mock(return_value={"status": "located", "lat": -34.9, "lon": -57.9})
    monkeypatch.setattr("core.location_views.locate_address", lookup)
    response = client.post(
        url, {"provincia": "Buenos Aires", "calle": "Calle", "numero": "123"}
    )
    assert response.status_code == 200
    assert response.json()["lat"] == -34.9
    assert response["Cache-Control"] == "private, no-store"
    lookup.assert_called_once_with(
        address="Calle 123", province="Buenos Aires", locality="", municipality=""
    )
    assert client.get(url).status_code == 405
    protected = Client(enforce_csrf_checks=True)
    protected.force_login(user)
    assert protected.post(url).status_code == 403


@pytest.mark.django_db
def test_preview_invalido_y_caida(client, django_user_model, monkeypatch):
    client.force_login(django_user_model.objects.create_user(username="preview-errors"))
    lookup = Mock(return_value={"status": "unavailable"})
    monkeypatch.setattr("core.location_views.locate_address", lookup)
    url = reverse("address_preview")
    response = client.post(url, {})
    assert response.status_code == 400
    lookup.assert_not_called()
    response = client.post(url, {"provincia": "Buenos Aires", "domicilio": "Calle 123"})
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            {"total": 1, "direcciones": [{"ubicacion": {"lat": -34, "lon": -58}}]},
            "located",
        ),
        ({"total": 2, "direcciones": [{}, {}]}, "ambiguous"),
        ({"total": 0, "direcciones": []}, "not_found"),
        (
            {
                "total": 1,
                "direcciones": [{"ubicacion": {"lat": float("nan"), "lon": 0}}],
            },
            "unavailable",
        ),
        (
            {"total": 1, "direcciones": [{"ubicacion": {"lat": 91, "lon": 0}}]},
            "unavailable",
        ),
        ({"error": "invalid"}, "unavailable"),
    ],
)
def test_locate_address_valida_respuesta(monkeypatch, payload, expected):
    response = Mock(json=Mock(return_value=payload), raise_for_status=Mock())
    lookup = Mock(return_value=response)
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    result = locate_address(
        address="Calle 123", province="Buenos Aires", locality="La Plata"
    )
    assert result["status"] == expected
    if expected == "located":
        assert result == {"status": "located", "lat": -34.0, "lon": -58.0}
    assert lookup.call_args.kwargs["params"]["localidad"] == "La Plata"


def test_locate_address_timeout(monkeypatch):
    monkeypatch.setattr(
        "core.services.geolocation.requests.get", Mock(side_effect=requests.Timeout)
    )
    assert locate_address(address="Calle 123", province="Buenos Aires") == {
        "status": "unavailable"
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    ["comedor_crear", "centrodeinfancia_crear", "centro_create", "ciudadanos_crear"],
)
def test_formularios_incluyen_editor_y_busqueda_compartida(
    client, django_user_model, route
):
    user = django_user_model.objects.create_superuser(
        username=f"pin-{route}", password="test"
    )
    client.force_login(user)
    response = client.get(reverse(route))
    assert response.status_code == 200
    assert b"data-pin-editor" in response.content
    assert b'data-latitude-field="id_latitud"' in response.content
    assert b'data-longitude-field="id_longitud"' in response.content
    assert b'data-generic-search="true"' in response.content
    assert b'data-always-visible="true"' in response.content
    assert reverse("address_preview").encode() in response.content
    if route == "centro_create":
        assert b"centro_form.js?v=2778-2" in response.content
