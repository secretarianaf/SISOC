"""Chequeo de las URLs sin parámetros de todo SISOC (``/health/urls/``).

Recorre ``src/backends/config/url_registry.json`` (la composición completa,
incluidas las verticales), hace un GET a cada ruta sin parámetros con la sesión
del usuario técnico ``sisoc-health-urls`` y guarda el código de respuesta en
``LOG_DIR``. Las rutas de
las verticales pasan por el proxy del core (``core.backend_proxy``), igual que
el tráfico real. Lo corre ``python manage.py chequear_urls``.
"""

import json
import logging
import os
import re
import tempfile
import time
from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.url_registry import cargar
from users.models import Profile

logger = logging.getLogger("django")

ARCHIVO_RESULTADO = "health_urls.json"
USUARIO_TECNICO = "sisoc-health-urls"
PREFIJO_ADMIN = "admin/"
# Logout, borrados y exportaciones: un GET puede tener efectos o ser pesado.
EXCLUIDAS = re.compile(
    r"logout|delete|eliminar|borrar|export|excel|xlsx|csv|descarg", re.IGNORECASE
)
# Esta misma vista no aporta nada al chequeo.
NOMBRES_EXCLUIDOS = {"health_urls"}
# Un GET a un endpoint que solo acepta POST responde 405: se ignora.
STATUS_SOLO_POST = 405
METACARACTERES = re.compile(r"(?<!\\)[()\[\]{}?*+|.^$]")


def resultado_path():
    return Path(settings.LOG_DIR) / ARCHIVO_RESULTADO


def ruta_sin_parametros(regex):
    """``/ruta/`` del patrón, o ``None`` si tiene parámetros o comodines."""
    ruta = re.sub(r"(\\Z|\$)$", "", regex.removeprefix("^"))
    if METACARACTERES.search(ruta):
        return None
    return "/" + re.sub(r"\\(.)", r"\1", ruta)


def urls_a_chequear(registro):
    """``(urls, excluidas, con_parametros)``; ``urls`` es ``[(ruta, nombre)]``."""
    urls, vistas = [], set()
    excluidas = con_parametros = 0
    for entrada in registro:
        ruta = ruta_sin_parametros(entrada["regex"])
        if ruta is None:
            con_parametros += 1
            continue
        nombre = ":".join(n for n in (entrada["namespace"], entrada["name"]) if n)
        if (
            ruta.startswith("/" + PREFIJO_ADMIN)
            or entrada["name"] in NOMBRES_EXCLUIDOS
            or EXCLUIDAS.search(ruta)
            or EXCLUIDAS.search(nombre)
        ):
            excluidas += 1
            continue
        if ruta not in vistas:
            vistas.add(ruta)
            urls.append((ruta, nombre))
    return urls, excluidas, con_parametros


def host_por_defecto():
    """Primer host concreto de ``ALLOWED_HOSTS``: sin él, todo responde 400."""
    for host in settings.ALLOWED_HOSTS:
        if not host.startswith((".", "*")):
            return host
    return "localhost"


def usuario_tecnico():
    """Superusuario propio del chequeo; se crea la primera vez.

    No tiene contraseña utilizable: no sirve para entrar por el login. Su perfil
    se mantiene sin pendientes, porque los middlewares de contraseña, datos
    personales y acceso web redirigirían todas las URLs. Desactivarlo apaga el
    chequeo.
    """
    usuario, _ = get_user_model().objects.get_or_create(
        username=USUARIO_TECNICO,
        defaults={
            "is_superuser": True,
            "first_name": "Chequeo",
            "last_name": "de URLs",
        },
    )
    if not usuario.is_active:
        raise ValueError(
            f"El usuario '{USUARIO_TECNICO}' está desactivado: el chequeo está apagado."
        )
    if not usuario.is_superuser or usuario.has_usable_password():
        usuario.is_superuser = True
        usuario.set_unusable_password()
        usuario.save()
    Profile.objects.update_or_create(
        user=usuario,
        defaults={
            "acceso_web": True,
            "must_change_password": False,
            "needs_profile_confirmation": False,
        },
    )
    return usuario


def chequear(urls, usuario, host):
    """GET a cada ruta; devuelve ``(resultados, solo_post)``."""
    client = Client(
        raise_request_exception=False,
        HTTP_HOST=host,
        HTTP_X_FORWARDED_PROTO="https",
    )
    client.force_login(usuario)
    resultados, solo_post = [], 0
    try:
        _verificar_acceso(client)
        for ruta, nombre in urls:
            try:
                respuesta = client.get(ruta, secure=True)
                respuesta.close()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.exception("health/urls: fallo el GET a %s", ruta)
                resultados.append(
                    {"url": ruta, "nombre": nombre, "status": None, "error": str(exc)}
                )
                continue
            if respuesta.status_code == STATUS_SOLO_POST:
                solo_post += 1
                continue
            resultados.append(
                {"url": ruta, "nombre": nombre, "status": respuesta.status_code}
            )
    finally:
        # Borra la sesión creada para el chequeo.
        client.logout()
    return resultados, solo_post


def _verificar_acceso(client):
    """Sin ``inicio`` en 200, un middleware tapa todas las vistas: no seguir."""
    respuesta = client.get(reverse("inicio"), secure=True)
    respuesta.close()
    if respuesta.status_code != 200:
        destino = respuesta.headers.get("Location")
        raise ValueError(
            f"El usuario del chequeo no llega a inicio (status "
            f"{respuesta.status_code}{f', redirige a {destino}' if destino else ''})"
            ": no se recorrieron las URLs."
        )


def ejecutar(host=None):
    """Corre el chequeo completo, lo guarda y lo devuelve."""
    usuario = usuario_tecnico()
    urls, excluidas, con_parametros = urls_a_chequear(cargar())
    inicio = time.monotonic()
    resultados, solo_post = chequear(urls, usuario, host or host_por_defecto())
    por_status = Counter(str(r["status"]) for r in resultados)
    resultado = {
        "generado": timezone.localtime().isoformat(timespec="seconds"),
        "duracion_s": round(time.monotonic() - inicio, 1),
        "resumen": {
            "chequeadas": len(resultados),
            "por_status": dict(sorted(por_status.items())),
            "ignoradas_solo_post": solo_post,
            "excluidas": excluidas,
            "salteadas_con_parametros": con_parametros,
        },
        "urls": resultados,
    }
    guardar(resultado)
    return resultado


def guardar_error(mensaje):
    """Deja el fallo visible en ``/health/urls/`` en lugar del último resultado."""
    guardar(
        {
            "generado": timezone.localtime().isoformat(timespec="seconds"),
            "error": mensaje,
        }
    )


def guardar(resultado):
    destino = resultado_path()
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Escritura atómica: la vista nunca lee un JSON a medias.
    fd, temporal = tempfile.mkstemp(dir=destino.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, ensure_ascii=False, indent=1)
    os.replace(temporal, destino)


def leer_resultado():
    try:
        with open(resultado_path(), encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return None


def proximo_horario(ahora, horarios):
    """Próximo ``datetime`` posterior a ``ahora`` en alguno de los ``horarios``."""
    for horario in sorted(horarios):
        candidato = ahora.replace(
            hour=horario.hour, minute=horario.minute, second=0, microsecond=0
        )
        if candidato > ahora:
            return candidato
    primero = min(horarios)
    return (ahora + timedelta(days=1)).replace(
        hour=primero.hour, minute=primero.minute, second=0, microsecond=0
    )
