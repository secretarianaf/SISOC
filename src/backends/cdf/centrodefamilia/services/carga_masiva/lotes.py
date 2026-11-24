"""Ciclo de vida de un lote: subida, edición, revalidación y confirmación (secciones 5, 8 y 9)."""

import logging
from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from centrodefamilia.models import (
    Beneficiario,
    BeneficiarioResponsable,
    BeneficiariosResponsablesRenaper,
    CargaMasivaPreinscriptos,
    ConsultaRenaperCargaMasiva,
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
from centrodefamilia.services.carga_masiva.renaper import (
    TAMANIO_TANDA,
    consultar_persona,
    consultas_del_lote,
    personas_por_consultar,
)
from centrodefamilia.services.carga_masiva.validacion import (
    AccionPreinscripto,
    AccionTitular,
    CAMPOS_UBICACION,
    Estado,
    validar_filas,
)

logger = logging.getLogger("django")

EstadoRenaper = ConsultaRenaperCargaMasiva.Estado
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


class VerificacionRenaperPendiente(Exception):
    """Todavía hay personas del lote sin verificar contra RENAPER."""


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
    resultados = validar_filas(
        [(fila.numero_fila, fila.datos) for fila in activas],
        consultas_del_lote(carga),
    )
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
    carga.renaper_pendientes = len(
        set().union(*(r.renaper_pendientes for r in resultados.values()))
    )
    carga.save(
        update_fields=[
            "total_filas",
            "total_validas",
            "total_advertencias",
            "total_errores",
            "renaper_pendientes",
        ]
    )
    return resultados


def verificar_renaper(carga_id, tamanio=TAMANIO_TANDA):
    """Consulta RENAPER para la próxima tanda de personas y revalida el lote.

    Las consultas se hacen fuera de la transacción para no bloquear el lote
    mientras RENAPER responde. Devuelve cuántas personas se consultaron, cuántas
    fallaron por un problema técnico y cuántas quedan pendientes.
    """
    carga = CargaMasivaPreinscriptos.objects.get(pk=carga_id)
    if not carga.esta_pendiente:
        raise CargaNoPendiente
    personas = personas_por_consultar(carga)[:tamanio]
    fallas = sum(
        consultar_persona(carga, dni, sexo) == EstadoRenaper.FALLA
        for dni, sexo in personas
    )
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        revalidar_carga(carga)
    return {
        "consultadas": len(personas),
        "fallas": fallas,
        "pendientes": carga.renaper_pendientes,
    }


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


# Los lotes pendientes (con datos de menores sin cargar) se eliminan a los 90 días.
DIAS_RETENCION_PENDIENTES = 90


def purgar_lotes_pendientes_vencidos(dias=DIAS_RETENCION_PENDIENTES):
    """Elimina los lotes pendientes subidos hace más de `dias` días.

    Borra el lote con sus filas, ediciones, consultas a RENAPER y archivo
    original. Los lotes confirmados o deshechos se conservan. Devuelve cuántos
    lotes eliminó.
    """
    limite = timezone.now() - timedelta(days=dias)
    vencidos = list(
        CargaMasivaPreinscriptos.objects.filter(
            estado=CargaMasivaPreinscriptos.Estado.PENDIENTE,
            fecha_subida__lt=limite,
        ).values_list("pk", flat=True)
    )
    eliminados = 0
    for carga_id in vencidos:
        with transaction.atomic():
            carga = (
                CargaMasivaPreinscriptos.objects.select_for_update()
                .filter(pk=carga_id, estado=CargaMasivaPreinscriptos.Estado.PENDIENTE)
                .first()
            )
            if carga is None:
                continue
            archivo = carga.archivo
            carga.delete()
            transaction.on_commit(lambda archivo=archivo: archivo.delete(save=False))
            eliminados += 1
    if eliminados:
        logger.info(
            "Carga masiva de preinscriptos: %s lotes pendientes eliminados por "
            "superar %s días.",
            eliminados,
            dias,
        )
    return eliminados


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


def _filas_a_cargar(carga):
    return carga.filas.filter(quitada=False).exclude(estado=Estado.ERROR)


def resumen_confirmacion(carga):
    """Cantidades que se informan antes de confirmar (RF-10)."""
    filas = list(
        _filas_a_cargar(carga).values_list(
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
        "rechazadas": carga.total_errores,
    }


def confirmar_carga(carga_id, usuario):
    """Revalida el lote y carga las filas sin error; las filas con error se rechazan.

    Devuelve True si se confirmó; False si después de revalidar no queda ninguna
    fila para cargar (los estados nuevos quedan guardados). Lanza CargaNoPendiente
    si el lote ya estaba confirmado. Si falla la carga de una fila no se carga
    ninguna (RN-06).
    """
    with transaction.atomic():
        carga = _bloquear_pendiente(carga_id)
        resultados = revalidar_carga(carga)
        if carga.renaper_pendientes:
            raise VerificacionRenaperPendiente
        if not carga.total_validas + carga.total_advertencias:
            return False
        _cargar_filas(carga, resultados, usuario)
        _guardar_datos_renaper(carga)
        carga.estado = CargaMasivaPreinscriptos.Estado.CONFIRMADO
        carga.confirmado_por = usuario
        carga.fecha_confirmacion = timezone.now()
        carga.save(update_fields=["estado", "confirmado_por", "fecha_confirmacion"])
    return True


def _cargar_filas(carga, resultados, usuario):
    titulares = {}
    for fila in _filas_a_cargar(carga).order_by("numero_fila"):
        resultado = resultados[fila.numero_fila]
        deshacer = {}
        titular = titulares.get(resultado.fila_titular)
        if titular is None:
            titular, deshacer["titular"] = _guardar_titular(
                resultados[resultado.fila_titular], usuario
            )
            titulares[resultado.fila_titular] = titular
        beneficiario, deshacer["preinscripto"] = _guardar_preinscripto(
            resultado, titular, carga, usuario
        )
        deshacer["vinculo"] = _vincular(
            beneficiario, titular, resultado.valor("vinculo_parental"), usuario
        )
        fila.beneficiario = beneficiario
        fila.titular = titular
        fila.deshacer = deshacer
        fila.save(update_fields=["beneficiario", "titular", "deshacer"])


def _asignar(instancia, campo, valor):
    atributo = f"{campo}_id" if campo in CAMPOS_UBICACION else campo
    if valor is None and not instancia._meta.get_field(campo).null:
        valor = ""  # Texto opcional sin dato, por ejemplo la calle.
    setattr(instancia, atributo, valor)


def _restaurar_si_baja(instancia, usuario):
    if instancia.is_deleted:
        instancia.restore(user=usuario, cascade=False)


def _foto(instancia):
    """Valores de la instancia antes de modificarla, para poder deshacer."""
    foto = {
        campo.attname: getattr(instancia, campo.attname)
        for campo in instancia._meta.concrete_fields
    }
    if isinstance(instancia, Beneficiario):
        foto["actividades_detalle"] = list(
            instancia.actividades_detalle.values_list("pk", flat=True)
        )
    return foto


def _guardar_titular(resultado, usuario):
    """Crea el titular, o reactiva y actualiza con todos los datos del Excel el existente.

    Devuelve (titular, cómo deshacerlo).
    """
    if resultado.titular_existente:
        titular = Responsable.all_objects.get(pk=resultado.titular_existente)
        deshacer = {"creado": False, "foto": _foto(titular)}
        _restaurar_si_baja(titular, usuario)
    else:
        titular = Responsable(
            creado_por=usuario,
            vinculo_parental=resultado.valor("vinculo_parental"),
        )
        deshacer = {"creado": True}
    for campo in CAMPOS_IDENTIDAD_TITULAR + CAMPOS_CONTACTO_TITULAR:
        _asignar(titular, campo, resultado.valor(f"titular_{campo}"))
    titular.save()
    return titular, deshacer


def _guardar_preinscripto(resultado, titular, carga, usuario):
    """Crea el preinscripto o reactiva el dado de baja con los datos del Excel.

    Devuelve (preinscripto, cómo deshacerlo).
    """
    if resultado.beneficiario_existente:
        beneficiario = Beneficiario.all_objects.get(pk=resultado.beneficiario_existente)
        deshacer = {"creado": False, "foto": _foto(beneficiario)}
        _restaurar_si_baja(beneficiario, usuario)
    else:
        beneficiario = Beneficiario(creado_por=usuario)
        deshacer = {"creado": True}
    for campo in CAMPOS_PREINSCRIPTO:
        _asignar(beneficiario, campo, resultado.valor(campo))
    beneficiario.provincia_tabla = resultado.valor("provincia_tabla") or ""
    beneficiario.municipio_tabla = resultado.valor("municipio_tabla") or ""
    beneficiario.responsable = titular
    beneficiario.carga_masiva_origen = carga
    beneficiario.save()
    beneficiario.actividades_detalle.set(resultado.valor("actividades_detalle") or [])
    return beneficiario, deshacer


def _vincular(beneficiario, titular, vinculo_parental, usuario):
    """El vínculo es de cada par titular–preinscripto (RN-24, DT-04).

    Devuelve cómo deshacerlo.
    """
    vinculo = BeneficiarioResponsable.all_objects.filter(
        beneficiario=beneficiario, responsable=titular
    ).first()
    if vinculo is None:
        vinculo = BeneficiarioResponsable.objects.create(
            beneficiario=beneficiario,
            responsable=titular,
            vinculo_parental=vinculo_parental,
        )
        return {"creado": True, "id": vinculo.pk}
    deshacer = {"creado": False, "foto": _foto(vinculo)}
    _restaurar_si_baja(vinculo, usuario)
    vinculo.vinculo_parental = vinculo_parental
    vinculo.save()
    return deshacer


# Campos de la respuesta de RENAPER que se guardan, igual que en el formulario.
CAMPOS_RESPUESTA_RENAPER = tuple(
    campo.name
    for campo in BeneficiariosResponsablesRenaper._meta.concrete_fields
    if campo.name not in ("id", "dni", "genero", "tipo", "fecha_creado")
)


def _guardar_datos_renaper(carga):
    """Guarda la respuesta de RENAPER de las personas cargadas y descarta las del lote.

    Como el formulario, deja un registro por persona y tipo (Beneficiario o
    Responsable). Las consultas del lote se borran: tienen datos de menores y ya
    no hacen falta.
    """
    consultas = consultas_del_lote(carga)
    personas = set()
    for fila in _filas_cargadas(carga):
        personas.add((fila.beneficiario.dni, fila.beneficiario.genero, "Beneficiario"))
        personas.add((fila.titular.dni, fila.titular.genero, "Responsable"))
    for dni, sexo, tipo in personas:
        consulta = consultas.get((dni, sexo))
        if consulta is None or not consulta.datos_api:
            continue
        BeneficiariosResponsablesRenaper.objects.update_or_create(
            dni=str(dni),
            genero=sexo,
            tipo=tipo,
            defaults={
                campo: consulta.datos_api.get(campo)
                for campo in CAMPOS_RESPUESTA_RENAPER
            },
        )
    carga.consultas_renaper.all().delete()


# ——— Deshacer ———


class CargaNoDeshacible(Exception):
    """El lote no cumple las condiciones para deshacerse."""


def motivo_no_deshacer(carga):
    """Por qué el lote no se puede deshacer, o "" si se puede.

    Solo se deshace el último lote confirmado y solo si nadie modificó después
    los preinscriptos que cargó.
    """
    if not carga.esta_confirmado:
        return "Solo se puede deshacer un lote confirmado."
    posterior = CargaMasivaPreinscriptos.objects.filter(
        fecha_confirmacion__gt=carga.fecha_confirmacion
    ).exclude(pk=carga.pk)
    if posterior.exists():
        return "Solo se puede deshacer el último lote cargado."
    modificadas = [
        fila.numero_fila
        for fila in _filas_cargadas(carga)
        if _modificado_despues(fila.beneficiario, carga.fecha_confirmacion)
    ]
    if modificadas:
        return (
            "No se puede deshacer: hay preinscriptos de este lote modificados "
            "después de la carga (filas "
            + ", ".join(str(numero) for numero in modificadas)
            + ")."
        )
    return ""


def _filas_cargadas(carga):
    return (
        carga.filas.filter(quitada=False)
        .exclude(deshacer={})
        .select_related("beneficiario", "titular")
    )


def _modificado_despues(instancia, fecha):
    if instancia is None:
        return True  # Lo borraron definitivamente.
    if instancia.fecha_modificado > fecha:
        return True
    return bool(instancia.deleted_at and instancia.deleted_at > fecha)


def deshacer_carga(carga_id, usuario):
    """Vuelve SISOC al estado previo a la confirmación del lote.

    Borra lo que el lote creó y restaura lo que reactivó o actualizó. Un titular
    creado por el lote se conserva si mientras tanto le asociaron otros
    preinscriptos, y un titular modificado después de la carga no se restaura.
    """
    with transaction.atomic():
        carga = CargaMasivaPreinscriptos.objects.select_for_update().get(pk=carga_id)
        motivo = motivo_no_deshacer(carga)
        if motivo:
            raise CargaNoDeshacible(motivo)
        filas = list(_filas_cargadas(carga).order_by("-numero_fila"))
        for fila in filas:
            _deshacer_vinculo(fila.deshacer["vinculo"])
            _deshacer_preinscripto(fila.beneficiario, fila.deshacer["preinscripto"])
        for fila in filas:
            if "titular" in fila.deshacer and fila.titular_id:
                _deshacer_titular(
                    fila.titular, fila.deshacer["titular"], carga.fecha_confirmacion
                )
        carga.estado = CargaMasivaPreinscriptos.Estado.DESHECHO
        carga.deshecho_por = usuario
        carga.fecha_deshecho = timezone.now()
        carga.save(update_fields=["estado", "deshecho_por", "fecha_deshecho"])
    logger.info(
        "Carga masiva de preinscriptos %s deshecha por el usuario %s.",
        carga_id,
        usuario.pk,
    )


def _restaurar_foto(modelo, foto):
    foto = dict(foto)
    actividades = foto.pop("actividades_detalle", None)
    instancia = modelo.all_objects.get(pk=foto["id"])
    for atributo, valor in foto.items():
        setattr(instancia, atributo, valor)
    instancia.save()
    if actividades is not None:
        instancia.actividades_detalle.set(actividades)


def _deshacer_vinculo(deshacer):
    if deshacer["creado"]:
        BeneficiarioResponsable.all_objects.filter(pk=deshacer["id"]).delete()
    else:
        _restaurar_foto(BeneficiarioResponsable, deshacer["foto"])


def _deshacer_preinscripto(beneficiario, deshacer):
    if deshacer["creado"]:
        beneficiario.hard_delete()
    else:
        _restaurar_foto(Beneficiario, deshacer["foto"])


def _deshacer_titular(titular, deshacer, fecha_confirmacion):
    if deshacer["creado"]:
        en_uso = (
            Beneficiario.all_objects.filter(responsable=titular).exists()
            or BeneficiarioResponsable.all_objects.filter(responsable=titular).exists()
        )
        if not en_uso:
            titular.hard_delete()
    elif titular.fecha_modificado <= fecha_confirmacion:
        _restaurar_foto(Responsable, deshacer["foto"])
