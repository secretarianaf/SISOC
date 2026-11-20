"""Ciclo de vida de un lote: subida, edición, revalidación y confirmación (secciones 5, 8 y 9)."""

import logging
from collections import Counter
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from centrodefamilia.models import (
    Beneficiario,
    BeneficiarioResponsable,
    CargaMasivaPreinscriptos,
    EdicionCargaMasivaPreinscriptos,
    FilaCargaMasivaPreinscriptos,
    Responsable,
)
from centrodefamilia.services.carga_masiva.columnas import (
    CAMPOS_CONTACTO_TITULAR,
    CAMPOS_IDENTIDAD_TITULAR,
    COLUMNAS,
    COLUMNAS_POR_CLAVE,
)
from centrodefamilia.services.carga_masiva.excel import leer_archivo
from centrodefamilia.services.carga_masiva.validacion import (
    AccionPreinscripto,
    AccionTitular,
    CAMPOS_UBICACION,
    Estado,
    validar_filas,
)

logger = logging.getLogger("django")

MAX_LARGO_CELDA = 500
FILA_QUITADA = "fila quitada"
CAMPOS_RESULTADO_FILA = [
    "estado",
    "errores",
    "advertencias",
    "accion_preinscripto",
    "accion_titular",
    "fila_titular",
]
# Columnas del preinscripto que van directo al modelo (el resto se arma aparte).
CAMPOS_PREINSCRIPTO = tuple(
    columna.clave
    for columna in COLUMNAS
    if not columna.es_titular
    and columna.clave not in ("vinculo_parental", "actividades_detalle")
)


class CargaNoPendiente(Exception):
    """El lote ya fue confirmado: no admite cambios ni otra confirmación (RN-08)."""


# ——— Subida y revalidación ———


def crear_carga(archivo, usuario):
    """Crea el lote pendiente con todas sus filas validadas (RN-03).

    No crea ni modifica preinscriptos ni titulares. Lanza ValidationError si el
    archivo se rechaza completo; en ese caso no se crea lote.
    """
    filas = leer_archivo(archivo)
    with transaction.atomic():
        carga = CargaMasivaPreinscriptos.objects.create(
            archivo=archivo,
            nombre_archivo=Path(archivo.name).name[:255],
            subido_por=usuario,
        )
        FilaCargaMasivaPreinscriptos.objects.bulk_create(
            FilaCargaMasivaPreinscriptos(carga=carga, numero_fila=numero, datos=datos)
            for numero, datos in filas
        )
        revalidar_carga(carga)
    return carga


def revalidar_carga(carga):
    """Revalida todas las filas no quitadas y actualiza los totales del lote."""
    activas = list(carga.filas.filter(quitada=False))
    resultados = validar_filas([(fila.numero_fila, fila.datos) for fila in activas])
    for fila in activas:
        resultado = resultados[fila.numero_fila]
        fila.estado = resultado.estado
        fila.errores = resultado.errores
        fila.advertencias = resultado.advertencias
        fila.accion_preinscripto = resultado.accion_preinscripto
        fila.accion_titular = resultado.accion_titular
        fila.fila_titular = resultado.fila_titular
    FilaCargaMasivaPreinscriptos.objects.bulk_update(activas, CAMPOS_RESULTADO_FILA)

    por_estado = Counter(fila.estado for fila in activas)
    carga.total_filas = len(activas)
    carga.total_validas = por_estado[Estado.VALIDA]
    carga.total_advertencias = por_estado[Estado.ADVERTENCIA]
    carga.total_errores = por_estado[Estado.ERROR]
    carga.save(
        update_fields=[
            "total_filas",
            "total_validas",
            "total_advertencias",
            "total_errores",
        ]
    )
    return resultados


def _bloquear_pendiente(carga_id):
    carga = CargaMasivaPreinscriptos.objects.select_for_update().get(pk=carga_id)
    if not carga.esta_pendiente:
        raise CargaNoPendiente
    return carga


def eliminar_carga(carga_id, usuario):
    """Elimina un lote pendiente con sus filas, ediciones y archivo original.

    Un lote confirmado no se elimina: sus preinscriptos ya están cargados y la
    carga no se puede deshacer (RN-09).
    """
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        archivo = carga.archivo
        carga.delete()
        transaction.on_commit(lambda: archivo.delete(save=False))
    logger.info(
        "Carga masiva de preinscriptos %s eliminada por el usuario %s.",
        carga_id,
        usuario.pk,
    )


# ——— Edición en la vista previa ———


def editar_fila(carga_id, fila_id, cambios, usuario):
    """Guarda las celdas cambiadas, registra cada cambio y revalida el lote (RF-04, RF-08).

    Devuelve la cantidad de celdas modificadas. Ignora claves que no son columnas
    de la plantilla.
    """
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        fila = carga.filas.get(pk=fila_id, quitada=False)
        ediciones = []
        for clave, valor in cambios.items():
            columna = COLUMNAS_POR_CLAVE.get(clave)
            if columna is None:
                continue
            nuevo = str(valor or "").strip()[:MAX_LARGO_CELDA]
            anterior = str(fila.datos.get(clave) or "")
            if nuevo == anterior:
                continue
            fila.datos[clave] = nuevo
            ediciones.append(
                EdicionCargaMasivaPreinscriptos(
                    carga=carga,
                    fila=fila,
                    usuario=usuario,
                    columna=columna.encabezado,
                    valor_anterior=anterior,
                    valor_nuevo=nuevo,
                )
            )
        if ediciones:
            fila.save(update_fields=["datos"])
            EdicionCargaMasivaPreinscriptos.objects.bulk_create(ediciones)
            revalidar_carga(carga)
        return len(ediciones)


def quitar_fila(carga_id, fila_id, usuario):
    """Quita la fila del lote: no se carga ni cuenta para confirmar (RF-05)."""
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        fila = carga.filas.get(pk=fila_id, quitada=False)
        fila.quitada = True
        fila.save(update_fields=["quitada"])
        EdicionCargaMasivaPreinscriptos.objects.create(
            carga=carga,
            fila=fila,
            usuario=usuario,
            valor_nuevo=FILA_QUITADA,
        )
        revalidar_carga(carga)


# ——— Confirmación ———


def resumen_confirmacion(carga):
    """Cantidades que se informan antes de confirmar (RF-10)."""
    filas = list(
        carga.filas.filter(quitada=False).values_list(
            "numero_fila", "accion_preinscripto", "accion_titular", "fila_titular"
        )
    )
    preinscriptos = Counter(accion for _, accion, _, _ in filas)
    titulares = Counter(
        accion for numero, _, accion, fila_titular in filas if numero == fila_titular
    )
    return {
        "preinscriptos_crear": preinscriptos[AccionPreinscripto.CREAR],
        "preinscriptos_reactivar": preinscriptos[AccionPreinscripto.REACTIVAR],
        "titulares_crear": titulares[AccionTitular.CREAR],
        "titulares_actualizar": titulares[AccionTitular.ACTUALIZAR],
        "titulares_reactivar": titulares[AccionTitular.REACTIVAR],
        "titulares_existentes": titulares[AccionTitular.EXISTENTE],
    }


def confirmar_carga(carga_id, usuario):
    """Revalida el lote y, si no hay errores, carga todas las filas o ninguna.

    Devuelve True si se confirmó; False si la revalidación encontró errores (los
    estados nuevos de las filas quedan guardados). Lanza CargaNoPendiente si el
    lote ya estaba confirmado. Cualquier otra falla deshace todo (RN-06).
    """
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        resultados = revalidar_carga(carga)
        if carga.total_errores or not carga.total_filas:
            return False
        _cargar_filas(carga, resultados, usuario)
        carga.estado = CargaMasivaPreinscriptos.Estado.CONFIRMADO
        carga.confirmado_por = usuario
        carga.fecha_confirmacion = timezone.now()
        carga.save(update_fields=["estado", "confirmado_por", "fecha_confirmacion"])
    return True


def _cargar_filas(carga, resultados, usuario):
    titulares = {}
    for fila in carga.filas.filter(quitada=False).order_by("numero_fila"):
        resultado = resultados[fila.numero_fila]
        titular = titulares.get(resultado.fila_titular)
        if titular is None:
            titular = _guardar_titular(resultados[resultado.fila_titular], usuario)
            titulares[resultado.fila_titular] = titular
        beneficiario = _guardar_preinscripto(resultado, titular, carga, usuario)
        _vincular(beneficiario, titular, resultado.valor("vinculo_parental"), usuario)
        fila.beneficiario = beneficiario
        fila.save(update_fields=["beneficiario"])


def _asignar(instancia, campo, valor):
    atributo = f"{campo}_id" if campo in CAMPOS_UBICACION else campo
    setattr(instancia, atributo, valor)


def _restaurar_si_baja(instancia, usuario):
    if instancia.is_deleted:
        instancia.restore(user=usuario, cascade=False)


def _guardar_titular(resultado, usuario):
    """Crea, actualiza (solo contacto y domicilio) o reactiva el titular (RN-26/27)."""
    if resultado.titular_existente:
        titular = Responsable.all_objects.get(pk=resultado.titular_existente)
        _restaurar_si_baja(titular, usuario)
    else:
        titular = Responsable(
            creado_por=usuario,
            vinculo_parental=resultado.valor("vinculo_parental"),
        )
        for campo in CAMPOS_IDENTIDAD_TITULAR:
            _asignar(titular, campo, resultado.valor(f"titular_{campo}"))
    for campo in CAMPOS_CONTACTO_TITULAR:
        _asignar(titular, campo, resultado.valor(f"titular_{campo}"))
    titular.save()
    return titular


def _guardar_preinscripto(resultado, titular, carga, usuario):
    """Crea el preinscripto o reactiva el dado de baja con los datos del Excel (RN-23)."""
    if resultado.beneficiario_existente:
        beneficiario = Beneficiario.all_objects.get(pk=resultado.beneficiario_existente)
        _restaurar_si_baja(beneficiario, usuario)
    else:
        beneficiario = Beneficiario(creado_por=usuario)
    for campo in CAMPOS_PREINSCRIPTO:
        _asignar(beneficiario, campo, resultado.valor(campo))
    beneficiario.observaciones = resultado.valor("observaciones") or ""
    beneficiario.provincia_tabla = resultado.valor("provincia_tabla") or ""
    beneficiario.municipio_tabla = resultado.valor("municipio_tabla") or ""
    beneficiario.responsable = titular
    beneficiario.carga_masiva_origen = carga
    beneficiario.save()
    beneficiario.actividades_detalle.set(resultado.valor("actividades_detalle") or [])
    return beneficiario


def _vincular(beneficiario, titular, vinculo_parental, usuario):
    """El vínculo es de cada par titular–preinscripto (RN-24, DT-04)."""
    vinculo = BeneficiarioResponsable.all_objects.filter(
        beneficiario=beneficiario, responsable=titular
    ).first()
    if vinculo is None:
        BeneficiarioResponsable.objects.create(
            beneficiario=beneficiario,
            responsable=titular,
            vinculo_parental=vinculo_parental,
        )
        return
    _restaurar_si_baja(vinculo, usuario)
    vinculo.vinculo_parental = vinculo_parental
    vinculo.save()
