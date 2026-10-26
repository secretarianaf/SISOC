"""Geocodificación sin llamadas externas en los tests."""

from unittest.mock import Mock

import pytest
import requests
from django.core.cache import cache

from core.models import Localidad, Municipio, Provincia
from dispositivos.models import Dispositivo
from dispositivos.services import geolocate_dispositivo, get_saved_dispositivo_location


@pytest.fixture
def device():
    cache.clear()
    provincia = Provincia(pk=1, nombre="Santa Fe")
    municipio = Municipio(pk=1, nombre="Rosario", provincia=provincia)
    return Dispositivo(
        calle="San Martín",
        altura="500",
        municipio=municipio,
        provincia=provincia,
        nombre_institucion="Prueba ubicación",
        tipo_gestion="estatal",
        cuit_institucion="30900000001",
        telefono_prefijo="341",
        telefono_numero="5550001",
        responsable_nombre_completo="Responsable",
        responsable_dni="90000001",
        tipo_dispositivo="refugio",
        modalidad_funcionamiento="permanente",
        capacidad_total_plazas="16_30",
    )


def response(payload):
    return Mock(json=Mock(return_value=payload), raise_for_status=Mock())


def test_georef_cache_y_cambio_direccion(device, monkeypatch):
    lookup = Mock(
        return_value=response(
            {"total": 1, "direcciones": [{"ubicacion": {"lat": -32.94, "lon": -60.63}}]}
        )
    )
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    assert geolocate_dispositivo(device) == {
        "status": "located",
        "lat": -32.94,
        "lon": -60.63,
    }
    geolocate_dispositivo(device)
    assert lookup.call_count == 1
    assert lookup.call_args.kwargs["params"]["localidad"] == "Rosario"
    device.altura = "900"
    geolocate_dispositivo(device)
    assert lookup.call_count == 2


def test_georef_no_elige_coincidencia_ambigua(device, monkeypatch):
    lookup = Mock(return_value=response({"total": 2, "direcciones": [{}, {}]}))
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    assert geolocate_dispositivo(device) == {"status": "ambiguous"}
    assert lookup.call_count == 1


def test_georef_fallback_departamento(device, monkeypatch):
    lookup = Mock(
        side_effect=[
            response({"total": 0, "direcciones": []}),
            response(
                {
                    "total": 1,
                    "direcciones": [{"ubicacion": {"lat": -32.94, "lon": -60.63}}],
                }
            ),
        ]
    )
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    assert geolocate_dispositivo(device)["status"] == "located"
    assert lookup.call_args.kwargs["params"]["departamento"] == "Rosario"


@pytest.mark.parametrize(
    "payload",
    [
        {"total": 0, "direcciones": []},
        {"total": 1, "direcciones": [{"ubicacion": {"lat": 500, "lon": 0}}]},
        {"error": "bad response"},
    ],
)
def test_georef_vacio_o_invalido(device, monkeypatch, payload):
    monkeypatch.setattr(
        "core.services.geolocation.requests.get", Mock(return_value=response(payload))
    )
    assert geolocate_dispositivo(device)["status"] in ("not_found", "unavailable")


def test_georef_timeout_no_cachea_error(device, monkeypatch):
    lookup = Mock(side_effect=requests.Timeout())
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    assert geolocate_dispositivo(device) == {"status": "unavailable"}
    assert geolocate_dispositivo(device) == {"status": "unavailable"}
    assert lookup.call_count == 2


@pytest.fixture
def persisted_device(db, device):
    provincia = Provincia.objects.create(nombre="Santa Fe")
    municipio = Municipio.objects.create(nombre="Rosario", provincia=provincia)
    device.provincia = provincia
    device.municipio = municipio
    device.save()
    return device


def mock_location(monkeypatch):
    lookup = Mock(
        return_value=response(
            {"total": 1, "direcciones": [{"ubicacion": {"lat": -32.94, "lon": -60.63}}]}
        )
    )
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    return lookup


def test_ubicacion_persistida_sobrevive_cache_y_edicion_contacto(
    persisted_device, monkeypatch
):
    lookup = mock_location(monkeypatch)
    expected = geolocate_dispositivo(persisted_device)
    cache.clear()
    persisted_device.refresh_from_db()
    assert get_saved_dispositivo_location(persisted_device) == expected
    persisted_device.responsable_nombre_completo = "Otro responsable"
    persisted_device.telefono_numero = "5559999"
    persisted_device.save()
    assert geolocate_dispositivo(persisted_device) == expected
    assert lookup.call_count == 1


@pytest.mark.parametrize(
    "field",
    [
        "calle",
        "altura",
        "municipio",
        "provincia",
        "municipio_nombre",
        "provincia_nombre",
    ],
)
def test_cambio_direccion_invalida_ubicacion_guardada(
    persisted_device, monkeypatch, field
):
    lookup = mock_location(monkeypatch)
    geolocate_dispositivo(persisted_device)
    cache.clear()
    if field == "calle":
        persisted_device.calle = "Otra calle"
    elif field == "altura":
        persisted_device.altura = "900"
    elif field == "municipio":
        persisted_device.municipio = Municipio.objects.create(
            nombre="Santa Fe", provincia=persisted_device.provincia
        )
    elif field == "provincia":
        persisted_device.provincia = Provincia.objects.create(nombre="Buenos Aires")
    elif field == "municipio_nombre":
        persisted_device.municipio.nombre = "Otra ciudad"
        persisted_device.municipio.save()
    else:
        persisted_device.provincia.nombre = "Otra provincia"
        persisted_device.provincia.save()
    persisted_device.save()
    persisted_device.refresh_from_db()
    assert get_saved_dispositivo_location(persisted_device) is None
    geolocate_dispositivo(persisted_device)
    assert lookup.call_count == 2


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"total": 2, "direcciones": [{}, {}]}, "ambiguous"),
        ({"total": 0, "direcciones": []}, "not_found"),
    ],
)
def test_persiste_resultados_sin_punto_hasta_cambiar_direccion(
    persisted_device, monkeypatch, payload, status
):
    lookup = Mock(return_value=response(payload))
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    assert geolocate_dispositivo(persisted_device) == {"status": status}
    calls = lookup.call_count
    cache.clear()
    persisted_device.refresh_from_db()
    assert get_saved_dispositivo_location(persisted_device) == {"status": status}
    assert geolocate_dispositivo(persisted_device) == {"status": status}
    assert lookup.call_count == calls
    persisted_device.altura = "900"
    persisted_device.save()
    assert get_saved_dispositivo_location(persisted_device) is None
    geolocate_dispositivo(persisted_device)
    assert lookup.call_count > calls


def test_no_persiste_servicio_no_disponible(persisted_device, monkeypatch):
    monkeypatch.setattr(
        "core.services.geolocation.requests.get",
        Mock(side_effect=requests.Timeout),
    )
    assert geolocate_dispositivo(persisted_device) == {"status": "unavailable"}
    persisted_device.refresh_from_db()
    assert persisted_device.ubicacion_georef == {}


def test_no_sobrescribe_direccion_editada_durante_consulta(
    persisted_device, monkeypatch
):
    def lookup(*_args, **_kwargs):
        Dispositivo.objects.filter(pk=persisted_device.pk).update(calle="Calle nueva")
        return response(
            {"total": 1, "direcciones": [{"ubicacion": {"lat": -32.94, "lon": -60.63}}]}
        )

    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    geolocate_dispositivo(persisted_device)
    persisted_device.refresh_from_db()
    assert persisted_device.calle == "Calle nueva"
    assert persisted_device.ubicacion_georef == {}


@pytest.mark.parametrize("coordinates", [(0, 0), (-34.9, -57.9)])
def test_coordenadas_manuales_prioritarias_sin_consulta(
    device, monkeypatch, coordinates
):
    lookup = Mock(side_effect=AssertionError("No debe consultar Georef"))
    monkeypatch.setattr("core.services.geolocation.requests.get", lookup)
    device.latitud, device.longitud = coordinates
    expected = {"status": "located", "lat": coordinates[0], "lon": coordinates[1]}
    assert geolocate_dispositivo(device) == expected
    device.calle = "Otra calle"
    assert get_saved_dispositivo_location(device) == expected
    lookup.assert_not_called()


def test_georef_usa_localidad_y_su_cambio_invalida_cache(device, monkeypatch):
    lookup = mock_location(monkeypatch)
    device.localidad = Localidad(pk=1, nombre="Localidad A", municipio=device.municipio)
    geolocate_dispositivo(device)
    assert lookup.call_args.kwargs["params"]["localidad"] == "Localidad A"
    device.localidad = Localidad(pk=2, nombre="Localidad B", municipio=device.municipio)
    geolocate_dispositivo(device)
    assert lookup.call_count == 2
    assert lookup.call_args.kwargs["params"]["localidad"] == "Localidad B"


def test_query_mapa_prioriza_coordenadas_y_fallback_domicilio(device):
    from urllib.parse import unquote
    from dispositivos.services import get_dispositivo_map_query

    assert (
        unquote(get_dispositivo_map_query(device))
        == "San Martín 500, Rosario, Santa Fe, Argentina"
    )
    device.localidad = Localidad(pk=1, nombre="Centro", municipio=device.municipio)
    assert "Centro, Rosario" in unquote(get_dispositivo_map_query(device))
    device.latitud, device.longitud = 0, 0
    assert unquote(get_dispositivo_map_query(device)) == "0,0"
