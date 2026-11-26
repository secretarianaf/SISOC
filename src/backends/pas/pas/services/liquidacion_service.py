"""Motor de liquidación PAS (Eje 5): puntos de control, preliquidación y nómina BNA.

Un titular se acredita cuando está Activo, tiene una DDJJ presentada y
procesada, no tiene alertas de cruces pendientes y, si la fuente FCH está
integrada, cumple la condicionalidad formativa (semáforo verde). La descarga
de la nómina se bloquea mientras algún punto de control no esté OK.
"""

import csv
import io

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from openpyxl import Workbook

from core.services.csv_export import build_csv_response, neutralize_csv_formula
from pas.models import PasDeclaracionJurada, PasIncompatibilidad, PasPersona
from pas.services.cruces_service import (
    NOMBRE_ESTADO_ACTIVO,
    NOMBRE_ESTADO_BAJA,
    incompatibilidades_pendientes,
)
from pas.services.estructura_salida import (
    COLUMNAS_SALIDA,
    MONTO_ASIGNACION_MENSUAL,
    fila_salida,
    formato_moneda,
)
from pas.services import formacion_service

OK = "ok"
PENDIENTE = "pendiente"
SIN_INTEGRAR = "sin_integrar"
FILAS_PRELIQUIDACION = 100
TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
COLUMNAS_CSV_PRELIQUIDACION = (
    ("titular", "Titular"),
    ("cuil", "CUIL"),
    ("cbu", "CBU BNA"),
    ("monto", "Monto"),
    ("fch", "FCH"),
    ("cruces", "Cruces"),
    ("ddjj", "DDJJ"),
    ("estado_final", "Estado final"),
)


class NominaBloqueada(Exception):
    """La nómina no se puede descargar: hay puntos de control sin resolver."""

    def __init__(self, motivos):
        super().__init__(" ".join(motivos))
        self.motivos = motivos


def _punto(clave, titulo, estado, detalle):
    return {
        "clave": clave,
        "titulo": titulo,
        "estado": estado,
        "detalle": detalle,
        "bloquea": estado == PENDIENTE,
    }


def _punto_suspensiones(circuito):
    titulo = "PC 1 Consolidación de suspensiones"
    if not circuito.fecha_exportacion_sintys:
        return _punto(
            "suspensiones", titulo, PENDIENTE, "Falta exportar el padrón a SINTyS."
        )
    if not circuito.fecha_importacion_sintys:
        return _punto(
            "suspensiones",
            titulo,
            PENDIENTE,
            "Falta importar el retorno de SINTyS del período.",
        )
    pendientes = (
        incompatibilidades_pendientes()
        .filter(periodo_impacto__lte=circuito.periodo)
        .count()
    )
    if pendientes:
        return _punto(
            "suspensiones",
            titulo,
            PENDIENTE,
            f"Hay {pendientes} alertas de incompatibilidad sin gestionar.",
        )
    return _punto(
        "suspensiones", titulo, OK, "Cruces del período procesados y confirmados."
    )


def _punto_ddjj():
    titulo = "DDJJ procesadas"
    sin_procesar = PasDeclaracionJurada.objects.filter(finalizada__isnull=True).count()
    if sin_procesar:
        return _punto(
            "ddjj",
            titulo,
            PENDIENTE,
            f"Hay {sin_procesar} declaraciones juradas presentadas sin procesar.",
        )
    return _punto(
        "ddjj",
        titulo,
        OK,
        "Todas las DDJJ presentadas están procesadas. "
        "Quien no presentó su DDJJ queda bloqueado para el pago.",
    )


def _punto_formacion():
    titulo = "PC 3 Validación de condicionalidad FCH"
    if not formacion_service.FORMACION_INTEGRADA:
        return _punto(
            "formacion",
            titulo,
            SIN_INTEGRAR,
            "La fuente FCH no está integrada: no se valida ni bloquea.",
        )
    return _punto(
        "formacion",
        titulo,
        OK,
        "Validación aplicada por titular: rojo y amarillo quedan bloqueados.",
    )


def puntos_de_control(circuito):
    return [
        _punto_suspensiones(circuito),
        _punto(
            "reclamos",
            "PC 2 Novedades y reclamos",
            SIN_INTEGRAR,
            "La Mesa de Ayuda no está integrada: no bloquea.",
        ),
        _punto_formacion(),
        _punto_ddjj(),
    ]


def descarga_habilitada(puntos):
    return not any(punto["bloquea"] for punto in puntos)


def _queryset(circuito):
    ddjj = PasDeclaracionJurada.objects.filter(
        persona_id=OuterRef("pk"), finalizada__isnull=False
    )
    alertas = PasIncompatibilidad.objects.filter(
        persona_id=OuterRef("pk"),
        estado=PasIncompatibilidad.Estado.PENDIENTE,
        periodo_impacto__lte=circuito.periodo,
    )
    return (
        PasPersona.objects.select_related("provincia", "municipio", "estado")
        .exclude(estado__nombre__iexact=NOMBRE_ESTADO_BAJA)
        .annotate(tiene_ddjj=Exists(ddjj), alerta_pendiente=Exists(alertas))
        .order_by("apellidos", "nombres", "id_persona")
    )


def _filtro_habilitado():
    return Q(
        estado__nombre__iexact=NOMBRE_ESTADO_ACTIVO,
        tiene_ddjj=True,
        alerta_pendiente=False,
    )


def _evaluar(persona):
    """Validaciones del titular; ``fch`` es None cuando la fuente no está integrada."""

    resumen_fch = formacion_service.estado_formacion_pago(persona)
    activo = persona.estado.nombre.casefold() == NOMBRE_ESTADO_ACTIVO.casefold()
    motivos = []
    if not activo:
        motivos.append(persona.estado.nombre)
    if not persona.tiene_ddjj:
        motivos.append("Sin DDJJ")
    if persona.alerta_pendiente:
        motivos.append("Alerta de cruce pendiente")
    if resumen_fch and resumen_fch["bloquea_pago"]:
        motivos.append(f"FCH {resumen_fch['semaforo']}")
    return {
        "habilitado": not motivos,
        "motivos": motivos,
        "fch": resumen_fch["semaforo"] if resumen_fch else None,
    }


def _fila(persona, evaluacion):
    return {
        "id": persona.pk,
        "titular": f"{persona.apellidos}, {persona.nombres}",
        "cuil": persona.cuit or "",
        "cbu": "",
        "monto": formato_moneda(
            MONTO_ASIGNACION_MENSUAL if evaluacion["habilitado"] else 0
        ),
        "fch": evaluacion["fch"],
        "cruces_ok": not persona.alerta_pendiente,
        "ddjj_ok": persona.tiene_ddjj,
        "habilitado": evaluacion["habilitado"],
        "estado_final": (
            "Habilitado"
            if evaluacion["habilitado"]
            else "Bloqueado: " + ", ".join(evaluacion["motivos"])
        ),
    }


def _contar(queryset):
    if not formacion_service.FORMACION_INTEGRADA:
        habilitados = queryset.filter(_filtro_habilitado()).count()
        return habilitados, queryset.count() - habilitados
    habilitados = bloqueados = 0
    for persona in queryset.iterator(chunk_size=2000):
        if _evaluar(persona)["habilitado"]:
            habilitados += 1
        else:
            bloqueados += 1
    return habilitados, bloqueados


def resumen_liquidacion(circuito, limite=FILAS_PRELIQUIDACION):
    """Datos de la pantalla de liquidación del período del circuito."""

    queryset = _queryset(circuito)
    habilitados, bloqueados = _contar(queryset)
    puntos = puntos_de_control(circuito)
    filas = [_fila(persona, _evaluar(persona)) for persona in queryset[:limite]]
    return {
        "periodo": circuito.periodo,
        "puntos_control": puntos,
        "descarga_habilitada": descarga_habilitada(puntos),
        "nomina_generada": bool(circuito.archivo_nomina_pago),
        "fecha_cierre": circuito.fecha_cierre,
        "titulares_a_acreditar": habilitados,
        "titulares_bloqueados": bloqueados,
        "total_a_liquidar": formato_moneda(MONTO_ASIGNACION_MENSUAL * habilitados),
        "monto_mensual": formato_moneda(MONTO_ASIGNACION_MENSUAL),
        "filas": filas,
        "total_filas": habilitados + bloqueados,
    }


def _texto_excel(valor):
    texto = str(valor or "")
    return f"'{texto}" if texto.startswith(("=", "+", "-", "@")) else texto


def generar_nomina_bna(circuito):
    """Excel nominal para BNA con la estructura de datos de salida.

    ``idPersona`` y ``DNI`` van como números y ``MES CURSO`` como importe con
    dos decimales; los textos se neutralizan contra fórmulas.
    """

    queryset = _queryset(circuito)
    if not formacion_service.FORMACION_INTEGRADA:
        queryset = queryset.filter(_filtro_habilitado())
    workbook = Workbook()
    hoja = workbook.active
    hoja.title = "nomina"
    hoja.append(COLUMNAS_SALIDA)
    for persona in queryset.iterator(chunk_size=2000):
        if (
            formacion_service.FORMACION_INTEGRADA
            and not _evaluar(persona)["habilitado"]
        ):
            continue
        fila = fila_salida(persona)
        hoja.append(
            [
                fila[0],
                *(_texto_excel(valor) for valor in fila[1:4]),
                fila[4],
                *(_texto_excel(valor) for valor in fila[5:8]),
                MONTO_ASIGNACION_MENSUAL,
                *(None for _ in fila[9:]),
            ]
        )
    for celda in hoja["I"][1:]:
        celda.number_format = "0.00"
    salida = io.BytesIO()
    workbook.save(salida)
    return salida.getvalue()


def _fila_csv(persona, evaluacion):
    fila = _fila(persona, evaluacion)
    return {
        **fila,
        "fch": fila["fch"] or "Sin integrar",
        "cruces": "OK" if fila["cruces_ok"] else "No",
        "ddjj": "OK" if fila["ddjj_ok"] else "No",
    }


def csv_preliquidacion(circuito):
    """CSV de la preliquidación completa del período (todas las filas, no solo 100).

    Usa la política central de CSV (UTF-8 con BOM y fórmulas neutralizadas).
    """

    response = build_csv_response(f"preliquidacion_pas_{circuito.periodo:%Y%m}.csv")
    writer = csv.writer(response)
    writer.writerow([etiqueta for _, etiqueta in COLUMNAS_CSV_PRELIQUIDACION])
    for persona in _queryset(circuito).iterator(chunk_size=2000):
        fila = _fila_csv(persona, _evaluar(persona))
        writer.writerow(
            [
                neutralize_csv_formula(fila[clave])
                for clave, _ in COLUMNAS_CSV_PRELIQUIDACION
            ]
        )
    return response


@transaction.atomic
def descargar_nomina(circuito, usuario):
    """Genera (una sola vez por período) la nómina final y cierra el circuito.

    Levanta ``NominaBloqueada`` si algún punto de control no está OK. Si el
    período ya fue cerrado devuelve el mismo archivo.
    """

    if circuito.pk:
        circuito = type(circuito).objects.select_for_update().get(pk=circuito.pk)
    nombre = f"nomina_pago_pas_bna_{circuito.periodo:%Y%m}.xlsx"
    if circuito.archivo_nomina_pago:
        circuito.archivo_nomina_pago.open("rb")
        try:
            contenido = circuito.archivo_nomina_pago.read()
        finally:
            circuito.archivo_nomina_pago.close()
        return contenido, nombre
    puntos = puntos_de_control(circuito)
    if not descarga_habilitada(puntos):
        raise NominaBloqueada(
            [punto["detalle"] for punto in puntos if punto["bloquea"]]
        )
    contenido = generar_nomina_bna(circuito)
    circuito.archivo_nomina_pago.save(nombre, ContentFile(contenido), save=False)
    circuito.nomina_descargada_por = usuario
    circuito.fecha_cierre = timezone.now()
    circuito.save(
        update_fields=["archivo_nomina_pago", "nomina_descargada_por", "fecha_cierre"]
    )
    return contenido, nombre
