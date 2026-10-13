import hashlib
import json
import logging
import math

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from users.territorial_scope import (
    get_effective_scopes,
    get_geography_scope_map,
    is_territorial_user,
)

from .models import Dispositivo


def get_dispositivos_queryset():
    return Dispositivo.objects.select_related("provincia", "municipio").order_by(
        "-created_at",
        "nombre_institucion",
    )


def apply_dispositivos_scope(queryset, user):
    """Acota el queryset de dispositivos al alcance territorial del usuario.

    - Sin usuario autenticado: queryset vacío.
    - Superusuario o usuario sin alcance provincial: sin restricción.
    - Usuario provincial: provincia y, si corresponde, municipio.

    El modelo ``Dispositivo`` no tiene localidad, por lo que un alcance a nivel
    localidad se respeta hasta su municipio (la granularidad más fina posible).
    Un usuario provincial sin alcances configurados no ve ningún registro.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return queryset.none()
    if getattr(user, "is_superuser", False):
        return queryset
    if not is_territorial_user(user):
        return queryset

    scopes = get_effective_scopes(user)
    if not scopes:
        return queryset.none()

    scope_q = Q()
    for scope in scopes:
        condiciones = {"provincia_id": scope.provincia_id}
        if scope.municipio_id:
            condiciones["municipio_id"] = scope.municipio_id
        scope_q |= Q(**condiciones)
    return queryset.filter(scope_q).distinct()


def get_dispositivos_geography_scope(user):
    """Mapa ``provincia_id -> set(municipio_id) | None`` para acotar el formulario.

    Devuelve ``None`` si el usuario no tiene restricción territorial.
    """
    return get_geography_scope_map(user)


def save_dispositivo_from_form(form, *, instance=None):
    dispositivo = form.save(commit=False)
    if instance is not None:
        dispositivo.pk = instance.pk
    dispositivo.save()
    return dispositivo


def delete_dispositivo(instance):
    instance.delete()


logger = logging.getLogger(__name__)


def _location_signature(device):
    address = [
        device.calle.strip(),
        device.altura.strip(),
        device.municipio_id,
        device.municipio.nombre,
        device.provincia_id,
        device.provincia.nombre,
    ]
    return hashlib.sha256(json.dumps(address, ensure_ascii=False).encode()).hexdigest()


# Resultados definitivos para una dirección: solo cambian si se edita la dirección.
# ``unavailable`` es transitorio y nunca se persiste.
_PERSISTED_STATUSES = ("located", "ambiguous", "not_found")


def get_saved_dispositivo_location(device):
    """Reutiliza el resultado guardado solo si corresponde a la dirección actual."""
    saved = device.ubicacion_georef
    if not isinstance(saved, dict) or saved.get("signature") != _location_signature(
        device
    ):
        return None
    result = saved.get("result")
    if not isinstance(result, dict) or result.get("status") not in _PERSISTED_STATUSES:
        return None
    if result["status"] != "located":
        return {"status": result["status"]}
    try:
        lat, lon = float(result["lat"]), float(result["lon"])
    except (KeyError, ValueError, TypeError):
        return None
    if not (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    ):
        return None
    return {"status": "located", "lat": lat, "lon": lon}


def _save_dispositivo_location(device, signature, result):
    if result["status"] not in _PERSISTED_STATUSES or device.pk is None:
        return
    saved = {"signature": signature, "result": result}
    updated = Dispositivo.objects.filter(
        pk=device.pk,
        calle=device.calle,
        altura=device.altura,
        municipio_id=device.municipio_id,
        provincia_id=device.provincia_id,
    ).update(ubicacion_georef=saved)
    if updated:
        device.ubicacion_georef = saved


def geolocate_dispositivo(device):
    """Reutiliza resultados persistidos; consulta Georef si cambió la dirección."""
    result = get_saved_dispositivo_location(device)
    if result is not None:
        return result
    if not device.calle.strip() or not device.altura.strip():
        return {"status": "not_found"}
    address = f"{device.calle} {device.altura}"
    signature = _location_signature(device)
    key = "dispositivos:georef:v2:" + signature
    result = cache.get(key)
    if result is not None:
        _save_dispositivo_location(device, signature, result)
        return result
    endpoint = getattr(
        settings,
        "DISPOSITIVOS_GEOREF_URL",
        "https://apis.datos.gob.ar/georef/api/direcciones",
    )
    try:
        for territory in ("localidad", "departamento"):
            response = requests.get(
                endpoint,
                params={
                    "direccion": address,
                    "provincia": device.provincia.nombre,
                    territory: device.municipio.nombre,
                    "max": 2,
                },
                timeout=8,
                headers={"User-Agent": "SISOC-Dispositivos/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
            matches = payload["direcciones"]
            total = int(payload["total"])
            if total == 0:
                continue
            result = {"status": "ambiguous"}
            if total == 1 and len(matches) == 1:
                location = matches[0]["ubicacion"]
                lat, lon = float(location["lat"]), float(location["lon"])
                if not (
                    math.isfinite(lat)
                    and math.isfinite(lon)
                    and -90 <= lat <= 90
                    and -180 <= lon <= 180
                ):
                    raise ValueError("Coordenadas inválidas")
                result = {"status": "located", "lat": lat, "lon": lon}
            break
        else:
            result = {"status": "not_found"}
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        logger.warning("Georef no disponible para dispositivo %s", device.pk)
        return {"status": "unavailable"}
    _save_dispositivo_location(device, signature, result)
    cache.set(key, result, timeout=86400 * (30 if result["status"] == "located" else 1))
    return result
