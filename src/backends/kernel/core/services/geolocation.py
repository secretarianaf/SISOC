"""Resolución pública de domicilios; sin acceso a legajos ni persistencia."""

import math

import requests

GEOREF_URL = "https://apis.datos.gob.ar/georef/api/direcciones"


def locate_address(
    *, address, province, locality="", municipality="", endpoint=GEOREF_URL
):
    # Georef no encuentra direcciones al repetir CABA como filtro de localidad.
    if (
        province.strip().casefold() == "ciudad autónoma de buenos aires"
        and locality.strip().casefold() == province.strip().casefold()
    ):
        locality = ""
    territories = [("localidad", locality or municipality)]
    if municipality:
        territories.append(("departamento", municipality))
    try:
        for territory, name in territories:
            params = {"direccion": address, "provincia": province, "max": 2}
            if name:
                params[territory] = name
            response = requests.get(
                endpoint,
                params=params,
                timeout=8,
                headers={"User-Agent": "SISOC-Dispositivos/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
            total = int(payload["total"])
            if total == 0:
                continue
            matches = payload["direcciones"]
            if total != 1 or len(matches) != 1:
                return _ambiguous_result(matches)
            lat = float(matches[0]["ubicacion"]["lat"])
            lon = float(matches[0]["ubicacion"]["lon"])
            if not (
                math.isfinite(lat)
                and math.isfinite(lon)
                and -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                raise ValueError("Coordenadas inválidas")
            return {"status": "located", "lat": lat, "lon": lon}
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        return {"status": "unavailable"}
    return {"status": "not_found"}


def _ambiguous_result(matches):
    result = {"status": "ambiguous"}
    if matches:
        point = matches[0].get("ubicacion", {})
        lat, lon = point.get("lat"), point.get("lon")
        if (
            all(isinstance(value, (int, float)) for value in (lat, lon))
            and math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            result["suggestion"] = {"lat": lat, "lon": lon}
    return result
