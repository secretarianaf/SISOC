"""Archivo subido entre la revisión y la confirmación de una importación.

El archivo, su análisis (``analisis.json``: resumen y observaciones) y sus
filas normalizadas (``filas.json``, lo que usa la confirmación) quedan en el
almacenamiento privado del módulo (``MEDIA_ROOT/inspecciones/importaciones/``,
sin URL; el Nginx bloquea ``/media/inspecciones/``) bajo un token. Sólo el
usuario que lo subió puede usarlo. Se borran al confirmar o cancelar, y los
que quedaron abandonados más de 24 horas se limpian en cada subida nueva.
"""

import json
import re
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

from inspecciones.services.planillas import extension_de
from inspecciones.storage import PREFIJO, almacenamiento_privado

DIRECTORIO = f"{PREFIJO}/importaciones"
TIPOS = ("escuelas", "asignaciones")
TOKEN_VALIDO = re.compile(r"^[0-9a-f]{32}$")
VIGENCIA = timedelta(hours=24)


class SubidaInexistente(ValidationError):
    """El token no existe, venció o es de otro usuario."""


def _ruta(tipo, token, nombre):
    return f"{DIRECTORIO}/{tipo}/{token}/{nombre}"


def _validar(tipo, token):
    if tipo not in TIPOS or not TOKEN_VALIDO.match(token or ""):
        raise SubidaInexistente("La importación no existe o ya terminó.")


def _json(datos):
    return ContentFile(json.dumps(datos, ensure_ascii=False).encode("utf-8"))


def guardar_subida(tipo, archivo, *, user, analisis, filas):
    """Guarda el archivo, su análisis y sus filas normalizadas; devuelve el token.

    ``analisis`` (resumen y observaciones) es lo que muestra la revisión;
    ``filas`` es lo que usa la confirmación, para no volver a leer el archivo.
    """
    limpiar_vencidas(tipo)
    token = secrets.token_hex(16)
    almacenamiento = almacenamiento_privado()
    extension = extension_de(archivo.name)
    archivo.seek(0)
    almacenamiento.save(_ruta(tipo, token, f"archivo.{extension}"), archivo)
    almacenamiento.save(_ruta(tipo, token, "filas.json"), _json(filas))
    datos = {
        "usuario_id": user.pk,
        "nombre": archivo.name[:200],
        "extension": extension,
        "creada_at": timezone.now().isoformat(),
        "analisis": analisis,
    }
    almacenamiento.save(_ruta(tipo, token, "analisis.json"), _json(datos))
    return token


def cargar_subida(tipo, token, *, user):
    """Datos guardados de la subida (sin abrir el archivo)."""
    _validar(tipo, token)
    almacenamiento = almacenamiento_privado()
    ruta = _ruta(tipo, token, "analisis.json")
    if not almacenamiento.exists(ruta):
        raise SubidaInexistente("La importación no existe o ya terminó.")
    with almacenamiento.open(ruta, "rb") as archivo:
        datos = json.loads(archivo.read().decode("utf-8"))
    if datos.get("usuario_id") != user.pk:
        raise SubidaInexistente("La importación no existe o ya terminó.")
    return datos


def cargar_filas(tipo, token):
    """Filas normalizadas guardadas en la revisión (llamar después de ``cargar_subida``)."""
    _validar(tipo, token)
    with almacenamiento_privado().open(
        _ruta(tipo, token, "filas.json"), "rb"
    ) as archivo:
        return json.loads(archivo.read().decode("utf-8"))


def borrar_subida(tipo, token):
    _validar(tipo, token)
    almacenamiento = almacenamiento_privado()
    directorio = _ruta(tipo, token, "")
    if not almacenamiento.exists(directorio):
        return
    _directorios, archivos = almacenamiento.listdir(directorio)
    for nombre in archivos:
        almacenamiento.delete(directorio + nombre)
    try:
        almacenamiento.delete(directorio.rstrip("/"))
    except OSError:
        pass


def limpiar_vencidas(tipo):
    """Borra las subidas que no se confirmaron ni cancelaron en 24 horas."""
    almacenamiento = almacenamiento_privado()
    base = f"{DIRECTORIO}/{tipo}"
    if not almacenamiento.exists(base):
        return
    limite = timezone.now() - VIGENCIA
    tokens, _archivos = almacenamiento.listdir(base)
    for token in tokens:
        if not TOKEN_VALIDO.match(token):
            continue
        ruta = _ruta(tipo, token, "analisis.json")
        try:
            vencida = almacenamiento.get_modified_time(ruta) < limite
        except (OSError, FileNotFoundError):
            vencida = True
        if vencida:
            borrar_subida(tipo, token)
