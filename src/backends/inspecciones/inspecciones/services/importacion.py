"""Importación masiva de asignaciones por jornada (``.xlsx`` o ``.csv``).

Columnas: ``fecha`` (AAAA-MM-DD o DD/MM/AAAA), ``cueanexo`` (o el código de
la escuela) e ``inspector`` (usuario, DNI o mail). Mismo flujo de tres pasos
que las escuelas: ``analizar_asignaciones`` no escribe y
``aplicar_asignaciones`` guarda; las dos clasifican igual.

Informa filas nuevas, repetidas (ya estaban), restauradas (se habían quitado)
y rechazadas con su causa; las filas válidas se guardan aunque otras fallen.
Nunca borra nada. Si la escuela ya tiene otro inspector asignado ese día, se
asigna igual (cuenta como otra visita) y queda como aviso.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from inspecciones.models import AsignacionEscuela, Escuela
from inspecciones.services.asignaciones import es_inspector
from inspecciones.services.formato import nombre_actor
from inspecciones.services.importacion_escuelas import normalizar_cueanexo
from inspecciones.services.planillas import leer_planilla

ALIAS_ASIGNACIONES = {
    "fecha": "fecha",
    "jornada": "fecha",
    "cueanexo": "escuela",
    "cue_anexo": "escuela",
    "escuela": "escuela",
    "codigo": "escuela",
    "cue": "escuela",
    "inspector": "inspector",
    "usuario": "inspector",
    "username": "inspector",
    "dni": "inspector",
    "correo": "inspector",
    "email": "inspector",
    "mail": "inspector",
}
REQUERIDAS = ("fecha", "escuela", "inspector")
ETIQUETAS_COLUMNA = {"fecha": "Fecha", "escuela": "Cueanexo", "inspector": "Inspector"}
FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
SERIAL_EXCEL = re.compile(r"^\d{5}$")
ORIGEN_EXCEL = date(1899, 12, 30)


def fecha_de_texto(valor):
    texto = str(valor or "").strip()
    if SERIAL_EXCEL.match(texto):
        # Una celda de fecha del .xlsx llega como número de serie de Excel.
        return ORIGEN_EXCEL + timedelta(days=int(texto))
    texto = texto[:10]
    for formato in FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


@dataclass
class _Clasificacion:
    total: int = 0
    nuevas: list = field(default_factory=list)
    restauradas: list = field(default_factory=list)
    repetidas: int = 0
    otra_visita: int = 0
    rechazadas: int = 0
    observaciones: list = field(default_factory=list)

    def observar(self, numero, fila, tipo, detalle):
        self.observaciones.append(
            {
                "fila": numero,
                "cueanexo": str(fila.get("escuela", "")),
                "nombre": str(fila.get("inspector", "")),
                "tipo": tipo,
                "motivo": "Rechazada" if tipo == "rechazada" else "Aviso",
                "detalle": detalle,
            }
        )


class _Resolutor:
    """Busca escuelas e inspectores una sola vez por valor del archivo."""

    def __init__(self):
        self._escuelas = {}
        self._inspectores = {}

    def escuela(self, clave):
        if clave not in self._escuelas:
            self._escuelas[clave] = (
                Escuela.objects.filter(Q(codigo=clave) | Q(cue=clave)).first()
                if clave
                else None
            )
        return clave, self._escuelas[clave]

    def inspector(self, identificador):
        identificador = str(identificador or "").strip()
        if identificador not in self._inspectores:
            self._inspectores[identificador] = _inspector(identificador)
        return self._inspectores[identificador]


def _inspector(identificador):
    if not identificador:
        return None, "Falta el inspector."
    filtro = Q(username__iexact=identificador) | Q(email__iexact=identificador)
    dni = identificador.replace(".", "")
    if dni.isdigit():
        filtro |= Q(profile__dni=dni)
    candidatos = list(get_user_model().objects.filter(filtro).distinct()[:2])
    if len(candidatos) != 1:
        return None, (
            f"No existe el inspector '{identificador}'."
            if not candidatos
            else f"El inspector '{identificador}' es ambiguo."
        )
    usuario = candidatos[0]
    if not es_inspector(usuario):
        return None, (
            f"'{identificador}' no tiene la sección Inspecciones escolares "
            "con rol Inspector."
        )
    return usuario, ""


def _otra_visita(resultado, numero, fila, visita):
    """Aviso si la escuela ya tiene otro inspector asignado esa jornada."""
    escuela, inspector, fecha = visita
    otros = list(
        AsignacionEscuela.objects.filter(escuela=escuela, fecha=fecha)
        .exclude(inspector=inspector)
        .select_related("inspector")
    )
    if otros:
        resultado.otra_visita += 1
        nombres = ", ".join(nombre_actor(a.inspector) for a in otros)
        resultado.observar(
            numero,
            fila,
            "aviso",
            f"{escuela.nombre} ya está asignada ese día a {nombres}: "
            "cuenta como otra visita.",
        )


def _clasificar(filas):
    resultado = _Clasificacion()
    resolutor = _Resolutor()
    vistos = set()
    for numero, fila in filas:
        resultado.total += 1
        fecha = date.fromisoformat(fila["fecha"]) if fila["fecha"] else None
        clave, escuela = resolutor.escuela(fila["escuela"])
        inspector, causa = resolutor.inspector(fila.get("inspector"))
        if fecha is None:
            causa = "Fecha inválida (AAAA-MM-DD o DD/MM/AAAA)."
        elif escuela is None:
            causa = f"No existe la escuela '{clave}'."
        if fecha is None or escuela is None or inspector is None:
            resultado.rechazadas += 1
            resultado.observar(numero, fila, "rechazada", causa)
            continue
        clave_visita = (escuela.pk, inspector.pk, fecha)
        existente = AsignacionEscuela.all_objects.filter(
            escuela=escuela, inspector=inspector, fecha=fecha
        ).first()
        if clave_visita in vistos or (existente and existente.deleted_at is None):
            resultado.repetidas += 1
            continue
        vistos.add(clave_visita)
        _otra_visita(resultado, numero, fila, (escuela, inspector, fecha))
        if existente is not None:
            resultado.restauradas.append(existente)
        else:
            resultado.nuevas.append((escuela, inspector, fecha))
    return resultado


def _leer(archivo):
    """``(meta, filas)`` normalizadas y en JSON, para guardar con la subida."""
    planilla = leer_planilla(archivo, archivo.name, ALIAS_ASIGNACIONES, REQUERIDAS)
    filas = []
    for numero, fila in planilla.filas:
        fecha = fecha_de_texto(fila.get("fecha"))
        escuela = fila.get("escuela")
        filas.append(
            (
                numero,
                {
                    "fecha": fecha.isoformat() if fecha else "",
                    "escuela": normalizar_cueanexo(escuela)
                    or "".join(str(escuela or "").split()),
                    "inspector": str(fila.get("inspector") or "").strip(),
                },
            )
        )
    meta = {"fila_encabezado": planilla.fila_encabezado, "columnas": planilla.columnas}
    return meta, filas


def _resumen(meta, clasificacion):
    return {
        "total": clasificacion.total,
        "fila_encabezado": meta["fila_encabezado"],
        "columnas": [
            {
                "original": c["original"],
                "campo": ETIQUETAS_COLUMNA[c["campo"]],
                "renombrada": False,
            }
            for c in meta["columnas"]
        ],
        "nuevas": len(clasificacion.nuevas),
        "restauradas": len(clasificacion.restauradas),
        "repetidas": clasificacion.repetidas,
        "otra_visita": clasificacion.otra_visita,
        "rechazadas": clasificacion.rechazadas,
        "a_importar": len(clasificacion.nuevas) + len(clasificacion.restauradas),
    }


def analizar_asignaciones(archivo):
    """Revisión, sin escribir: ``{"resumen", "observaciones", "datos"}``."""
    meta, filas = _leer(archivo)
    clasificacion = _clasificar(filas)
    return {
        "resumen": _resumen(meta, clasificacion),
        "observaciones": clasificacion.observaciones,
        "datos": {"meta": meta, "filas": filas},
    }


def aplicar_asignaciones(datos, *, actor=None):
    """Confirmación: vuelve a clasificar contra la base actual y guarda."""
    clasificacion = _clasificar(datos["filas"])
    with transaction.atomic():
        AsignacionEscuela.objects.bulk_create(
            [
                AsignacionEscuela(
                    escuela=escuela, inspector=inspector, fecha=fecha, creada_por=actor
                )
                for escuela, inspector, fecha in clasificacion.nuevas
            ],
            batch_size=1000,
        )
        for asignacion in clasificacion.restauradas:
            asignacion.restore(user=actor, cascade=False)
    return _resumen(datos["meta"], clasificacion), clasificacion.observaciones
