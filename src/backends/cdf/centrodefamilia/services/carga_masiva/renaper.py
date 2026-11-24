"""Consultas a RENAPER de las personas de un lote, por tandas.

La vista previa pide una tanda por vez hasta verificar a todas las personas, así
ningún pedido web tarda más que unas pocas consultas. Cada persona (DNI y sexo)
se consulta una sola vez por lote aunque aparezca en varias filas.
"""

from datetime import datetime

from django.utils import timezone

from centrodefamilia.models import ConsultaRenaperCargaMasiva
from centrodefamilia.services.carga_masiva.validacion import claves_renaper
from core.services.renaper import consultar_datos_renaper

Estado = ConsultaRenaperCargaMasiva.Estado

TAMANIO_TANDA = 8
_FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")


def _fecha(valor):
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(str(valor or "").strip()[:10], formato).date()
        except ValueError:
            continue
    return None


def consultas_del_lote(carga):
    """Respuestas de RENAPER del lote por (DNI, sexo)."""
    return {
        (consulta.dni, consulta.sexo): consulta
        for consulta in carga.consultas_renaper.all()
    }


def personas_por_consultar(carga):
    """(DNI, sexo) del lote sin respuesta de RENAPER o cuya consulta falló."""
    resueltas = set(
        carga.consultas_renaper.exclude(estado=Estado.FALLA).values_list("dni", "sexo")
    )
    pendientes = []
    filas = carga.filas.filter(quitada=False).order_by("numero_fila")
    for datos in filas.values_list("datos", flat=True):
        for clave in claves_renaper(datos):
            if clave not in resueltas and clave not in pendientes:
                pendientes.append(clave)
    return pendientes


def consultar_persona(carga, dni, sexo):
    """Consulta RENAPER, guarda la respuesta en el lote y devuelve su estado."""
    resultado = consultar_datos_renaper(str(dni), sexo)
    valores = {"datos_api": {}, "apellido": "", "nombre": "", "fecha_nacimiento": None}
    if resultado.get("success"):
        datos = resultado.get("data") or {}
        valores.update(
            estado=Estado.ENCONTRADO,
            apellido=str(datos.get("apellido") or "")[:200],
            nombre=str(datos.get("nombre") or "")[:200],
            fecha_nacimiento=_fecha(datos.get("fecha_nacimiento")),
            datos_api=resultado.get("datos_api") or {},
        )
    elif resultado.get("error_type") == "no_match":
        valores["estado"] = Estado.NO_ENCONTRADO
    elif resultado.get("error_type") == "fallecido" or resultado.get("fallecido"):
        valores["estado"] = Estado.FALLECIDO
    else:
        # Falla técnica: queda pendiente y se vuelve a consultar en otra tanda.
        valores["estado"] = Estado.FALLA
    valores["fecha_consulta"] = timezone.now()
    ConsultaRenaperCargaMasiva.objects.update_or_create(
        carga=carga, dni=dni, sexo=sexo, defaults=valores
    )
    return valores["estado"]
