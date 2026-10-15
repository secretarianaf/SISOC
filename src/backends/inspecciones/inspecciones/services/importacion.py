"""Importación por CSV del catálogo de escuelas y de las asignaciones.

Informa filas creadas, actualizadas, repetidas y rechazadas con su causa; las
filas válidas se guardan aunque otras fallen. Nunca borra nada: una escuela o
asignación que no viene en el archivo queda como estaba.
"""

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from inspecciones.models import AsignacionEscuela, Escuela
from users.services_inspecciones import tiene_acceso_inspecciones

MAX_BYTES_CSV = 10 * 1024 * 1024
SOLO_DIGITOS = re.compile(r"^\d+$")

ALIAS_ESCUELAS = {
    "codigo": "codigo",
    "id": "codigo",
    "clave": "codigo",
    "cue": "cue",
    "nombre": "nombre",
    "escuela": "nombre",
    "establecimiento": "nombre",
    "distrito": "distrito",
    "localidad": "localidad",
    "domicilio": "domicilio",
    "direccion": "domicilio",
    "nivel": "nivel",
}
ALIAS_ASIGNACIONES = {
    "fecha": "fecha",
    "jornada": "fecha",
    "escuela": "escuela",
    "codigo": "escuela",
    "cue": "escuela",
    "inspector": "inspector",
    "usuario": "inspector",
    "username": "inspector",
    "dni": "inspector",
    "correo": "inspector",
    "email": "inspector",
}


@dataclass
class ResultadoImportacion:
    total: int = 0
    creadas: int = 0
    actualizadas: int = 0
    sin_cambios: int = 0
    rechazadas: list = field(default_factory=list)

    def rechazar(self, fila, causa):
        self.rechazadas.append({"fila": fila, "causa": causa})


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def _decodificar(archivo):
    if archivo.size > MAX_BYTES_CSV:
        raise ValidationError("El archivo CSV no puede superar los 10 MB.")
    archivo.seek(0)
    crudo = archivo.read()
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ValidationError("No se pudo leer el archivo: guardalo como CSV UTF-8.")


def leer_csv(archivo, alias, requeridas):
    """Filas como ``(numero_de_fila, {columna: valor})`` con encabezados normalizados."""
    texto = _decodificar(archivo)
    try:
        dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;|\t")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.reader(io.StringIO(texto), dialect=dialecto)
    try:
        encabezados = next(lector)
    except StopIteration as exc:
        raise ValidationError("El archivo CSV está vacío.") from exc
    columnas = [alias.get(_normalizar(nombre)) for nombre in encabezados]
    faltantes = [c for c in requeridas if c not in columnas]
    if faltantes:
        raise ValidationError(
            "Faltan columnas obligatorias: " + ", ".join(faltantes) + "."
        )
    filas = []
    for numero, valores in enumerate(lector, start=2):
        if not any(str(v).strip() for v in valores):
            continue
        fila = {}
        for columna, valor in zip(columnas, valores):
            if columna and not fila.get(columna):
                fila[columna] = str(valor).strip()
        filas.append((numero, fila))
    return filas


CAMPOS_ESCUELA = ("nombre", "cue", "distrito", "localidad", "domicilio", "nivel")


def importar_escuelas(archivo):  # pylint: disable=too-many-locals
    """Alta o actualización por ``codigo`` (si falta, el CUE es la clave)."""
    resultado = ResultadoImportacion()
    vistos = set()
    for numero, fila in leer_csv(archivo, ALIAS_ESCUELAS, ("nombre", "cue")):
        resultado.total += 1
        cue = re.sub(r"\s+", "", fila.get("cue", ""))
        codigo = fila.get("codigo") or cue
        if not fila.get("nombre"):
            resultado.rechazar(numero, "Falta el nombre de la escuela.")
            continue
        if cue and not SOLO_DIGITOS.match(cue):
            resultado.rechazar(numero, f"El CUE '{cue}' lleva solo números.")
            continue
        if not codigo:
            resultado.rechazar(numero, "Falta el CUE o el código de la escuela.")
            continue
        if codigo in vistos:
            resultado.rechazar(numero, f"Código '{codigo}' repetido en el archivo.")
            continue
        vistos.add(codigo)
        datos = {campo: fila.get(campo, "") for campo in CAMPOS_ESCUELA}
        datos["cue"] = cue
        with transaction.atomic():
            escuela = Escuela.all_objects.filter(codigo=codigo).first()
            if escuela is None:
                Escuela.objects.create(codigo=codigo[:40], **datos)
                resultado.creadas += 1
                continue
            cambios = {k: v for k, v in datos.items() if getattr(escuela, k) != v}
            if escuela.deleted_at is not None:
                cambios.update(deleted_at=None, deleted_by=None)
            if not cambios:
                resultado.sin_cambios += 1
                continue
            for clave, valor in cambios.items():
                setattr(escuela, clave, valor)
            escuela.save()
            resultado.actualizadas += 1
    return resultado


def _fecha(valor):
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(valor.strip(), formato).date()
        except (ValueError, AttributeError):
            continue
    return None


def _inspector(identificador):
    identificador = (identificador or "").strip()
    if not identificador:
        return None, "Falta el inspector."
    user_model = get_user_model()
    filtro = Q(username__iexact=identificador) | Q(email__iexact=identificador)
    if identificador.isdigit():
        filtro |= Q(profile__dni=identificador)
    candidatos = list(user_model.objects.filter(filtro).distinct()[:2])
    if len(candidatos) != 1:
        return None, (
            "No existe el inspector." if not candidatos else "Inspector ambiguo."
        )
    usuario = candidatos[0]
    if not tiene_acceso_inspecciones(usuario):
        return None, "El usuario no pertenece a Inspecciones escolares."
    return usuario, ""


def importar_asignaciones(archivo, *, actor=None):
    resultado = ResultadoImportacion()
    for numero, fila in leer_csv(
        archivo, ALIAS_ASIGNACIONES, ("fecha", "escuela", "inspector")
    ):
        resultado.total += 1
        fecha = _fecha(fila.get("fecha", ""))
        if fecha is None:
            resultado.rechazar(numero, "Fecha inválida (AAAA-MM-DD o DD/MM/AAAA).")
            continue
        clave = re.sub(r"\s+", "", fila.get("escuela", ""))
        escuela = Escuela.objects.filter(Q(codigo=clave) | Q(cue=clave)).first()
        if not clave or escuela is None:
            resultado.rechazar(numero, f"No existe la escuela '{clave}'.")
            continue
        inspector, causa = _inspector(fila.get("inspector", ""))
        if inspector is None:
            resultado.rechazar(numero, causa)
            continue
        with transaction.atomic():
            existente = AsignacionEscuela.all_objects.filter(
                escuela=escuela, inspector=inspector, fecha=fecha
            ).first()
            if existente is None:
                AsignacionEscuela.objects.create(
                    escuela=escuela, inspector=inspector, fecha=fecha, creada_por=actor
                )
                resultado.creadas += 1
            elif existente.deleted_at is not None:
                existente.deleted_at = None
                existente.deleted_by = None
                existente.save(update_fields=["deleted_at", "deleted_by"])
                resultado.actualizadas += 1
            else:
                resultado.sin_cambios += 1
    return resultado
