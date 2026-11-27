import csv
import io
import re
from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from pas.models import (
    PasAviso,
    PasCircuitoMensual,
    PasEstado,
    PasIncompatibilidad,
    PasPersona,
)
from pas.services.estructura_salida import (
    MONTO_ASIGNACION_MENSUAL,
    PROGRAMA,
    formato_moneda,
)
from pas.services.persona_service import aplicar_cambio_estado, cambiar_estado

NOMBRE_ESTADO_ACTIVO = "Activo"
NOMBRE_ESTADO_SUSPENDIDO = "Suspendido"
NOMBRE_ESTADO_BAJA = "Baja"
CODIGO_AVISO_INCOMPATIBLE = 10
CODIGO_AVISO_RENUNCIA = 39
CODIGO_AVISO_FALLECIDO = 40

# Formato de envío de titulares a SINTyS (VIAS), en el orden del layout.
COLUMNAS_ENVIO_SINTYS = (
    "PROG",
    "ID_ORIG",
    "NOMBRE_ORIG",
    "APELLIDO_ORIG",
    "NDOC_ORIG",
    "CUIT_ORIG",
    "SEXO_ORIG",
    "FNAC_ORIG",
    "ESTADO",
    "MONTO_ORIG",
    "TIPOCALLE",
    "CALLE",
    "NUMERO",
    "PISO",
    "DEPTO",
    "MANZANA",
    "LOTE",
    "CALLELATERALA",
    "CALLELATERALB",
    "BARRIO",
    "PARAJE",
    "LOCALIDAD",
    "DEPARTAMENTO",
    "PROV_ORIG",
    "CODIGOPOSTAL",
    "ACLARACIONES",
    "TELFIJOCODAREA",
    "TELFIJO",
    "TELCELULARCODAREA",
    "TELCELULAR",
    "EMAIL",
    "FUENTEDOMICILIO",
    "EVALUACION",
    "MOTIVO",
    "TIPO_PRESTACION_SINTYS",
    "ESTADO_SINTYS",
    "TIPO_BEN_SINTYS",
    "CANAL_FINANCIACION_SINTYS",
    "SUBPROGRAMA_SINTYS",
    "TELEFONO_SINTYS",
    "DOMICILIO_COMPLETO_SINTYS",
)

COLUMNAS_RETORNO_SINTYS = (
    "ID",
    "APELLIDO",
    "NOMBRE",
    "NDOC",
    "CUIT_TXT",
    "EVALUACION",
    "MOTIVO",
)
EVALUACION_COMPATIBLE = "COMPATIBLE"
# Evaluación SINTyS → (categoría de la alerta, estado propuesto, aviso propuesto).
CAMBIOS_POR_EVALUACION = {
    "INCOMPATIBLE": (None, NOMBRE_ESTADO_SUSPENDIDO, CODIGO_AVISO_INCOMPATIBLE),
    "RENUNCIA": (
        PasIncompatibilidad.Categoria.RENUNCIA,
        NOMBRE_ESTADO_BAJA,
        CODIGO_AVISO_RENUNCIA,
    ),
    "FALLECIDO": (
        PasIncompatibilidad.Categoria.SUPERVIVENCIA,
        NOMBRE_ESTADO_BAJA,
        CODIGO_AVISO_FALLECIDO,
    ),
}
PALABRAS_PATRIMONIO = (
    "AUTOMOTOR",
    "VEHICULO",
    "INMUEBLE",
    "EMBARCACION",
    "AERONAVE",
    "PATRIMONIO",
)
DELIMITADORES_RETORNO = "|;,\t"


def obtener_circuito_actual(*, crear=False):
    hoy = timezone.localdate()
    periodo = date(hoy.year, hoy.month, 1)
    circuito = PasCircuitoMensual.objects.filter(periodo=periodo).first()
    if circuito:
        return circuito
    if crear:
        return PasCircuitoMensual.objects.create(periodo=periodo)
    return PasCircuitoMensual(periodo=periodo)


def _texto_excel_seguro(value):
    texto = str(value or "")
    if texto.startswith(("=", "+", "-", "@")):
        return f"'{texto}"
    return texto


def _numero(valor):
    """Columnas NUMERICO del formato de envío: el número, o vacío si no hay."""

    texto = re.sub(r"\D", "", str(valor or ""))
    return int(texto) if texto else None


def _fila_envio_sintys(persona):
    """Valores que PAS registra; el resto de las columnas del envío va vacío."""

    activo = persona.estado.nombre.casefold() == NOMBRE_ESTADO_ACTIVO.casefold()
    datos = {
        "PROG": PROGRAMA,
        "ID_ORIG": str(persona.id_persona),
        "NOMBRE_ORIG": persona.nombres,
        "APELLIDO_ORIG": persona.apellidos,
        "NDOC_ORIG": persona.dni,
        "CUIT_ORIG": _numero(persona.cuit),
        "SEXO_ORIG": persona.genero,
        "ESTADO": persona.estado.nombre,
        "MONTO_ORIG": formato_moneda(MONTO_ASIGNACION_MENSUAL) if activo else "",
        "CALLE": persona.calle or persona.domicilio,
        "NUMERO": persona.altura,
        "LOCALIDAD": persona.municipio.nombre if persona.municipio_id else "",
        "PROV_ORIG": persona.provincia.nombre if persona.provincia_id else "",
        "TELCELULAR": persona.telefono_celular,
        "EMAIL": persona.correo_electronico,
    }
    fila = []
    for columna in COLUMNAS_ENVIO_SINTYS:
        valor = datos.get(columna)
        if valor in (None, ""):
            fila.append(None)
        elif isinstance(valor, int):
            fila.append(valor)
        else:
            fila.append(_texto_excel_seguro(valor))
    return fila


def generar_nomina_sintys_pas():
    """Padrón a cruzar en SINTyS (formato de envío de titulares).

    Incluye a los titulares que no están de baja. ``MONTO_ORIG`` lleva la
    asignación solo para los activos.
    """

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "nomina"
    sheet.append(COLUMNAS_ENVIO_SINTYS)

    personas = (
        PasPersona.objects.select_related("provincia", "municipio", "estado")
        .exclude(estado__nombre__iexact=NOMBRE_ESTADO_BAJA)
        .order_by("apellidos", "nombres", "id_persona")
    )
    for persona in personas.iterator(chunk_size=2000):
        sheet.append(_fila_envio_sintys(persona))

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


@transaction.atomic
def registrar_exportacion_sintys(circuito, usuario):
    contenido = generar_nomina_sintys_pas()
    marca = timezone.localtime().strftime("%Y%m%d_%H%M")
    nombre = f"nomina_pas_sintys_vias_{marca}.xlsx"
    circuito.fecha_exportacion_sintys = timezone.now()
    circuito.exportado_por = usuario
    circuito.archivo_exportacion_sintys.save(
        nombre,
        ContentFile(contenido),
        save=False,
    )
    circuito.save(
        update_fields=[
            "fecha_exportacion_sintys",
            "exportado_por",
            "archivo_exportacion_sintys",
        ]
    )
    return contenido, nombre


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _entero(valor):
    texto = _texto(valor)
    if texto.endswith(".0"):
        texto = texto[:-2]
    return int(texto) if texto.isdigit() else None


def _filas_texto(contenido):
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("cp1252", errors="replace")
    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    if not lineas:
        return []
    delimitador = max(DELIMITADORES_RETORNO, key=lineas[0].count)
    return list(csv.reader(lineas, delimiter=delimitador))


def _filas_xlsx(contenido):
    try:
        workbook = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    # openpyxl levanta errores variados ante archivos rotos.
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise ValidationError("No se pudo leer el archivo XLSX de retorno.") from exc
    try:
        return [list(fila) for fila in workbook.active.iter_rows(values_only=True)]
    finally:
        workbook.close()


def leer_retorno_sintys(archivo):
    """Lee el retorno SINTyS (TXT/CSV delimitado o XLSX) y devuelve filas normalizadas.

    Exige el encabezado del formato de retorno; cada fila es un ``dict`` con
    las columnas de ``COLUMNAS_RETORNO_SINTYS`` y su número de línea.
    """

    archivo.seek(0)
    contenido = archivo.read()
    nombre = (archivo.name or "").lower()
    crudas = (
        _filas_xlsx(contenido) if nombre.endswith(".xlsx") else _filas_texto(contenido)
    )
    if not crudas:
        raise ValidationError("El archivo de retorno está vacío.")
    encabezado = [_texto(valor).upper() for valor in crudas[0]]
    faltantes = [
        columna for columna in COLUMNAS_RETORNO_SINTYS if columna not in encabezado
    ]
    if faltantes:
        raise ValidationError(
            "El retorno no tiene el formato SINTyS esperado. Faltan las columnas: "
            + ", ".join(faltantes)
            + "."
        )
    indices = {
        columna: encabezado.index(columna) for columna in COLUMNAS_RETORNO_SINTYS
    }
    filas = []
    for numero, cruda in enumerate(crudas[1:], start=2):
        if not any(_texto(valor) for valor in cruda):
            continue
        filas.append(
            {
                "linea": numero,
                **{
                    columna: _texto(cruda[indice]) if indice < len(cruda) else ""
                    for columna, indice in indices.items()
                },
            }
        )
    return filas


def _categoria_incompatible(motivo):
    motivo = motivo.upper()
    if any(palabra in motivo for palabra in PALABRAS_PATRIMONIO):
        return PasIncompatibilidad.Categoria.PATRIMONIO
    return PasIncompatibilidad.Categoria.INGRESOS


def _catalogo_cambios():
    estados = {
        estado.nombre.casefold(): estado
        for estado in PasEstado.objects.filter(
            nombre__in=[NOMBRE_ESTADO_SUSPENDIDO, NOMBRE_ESTADO_BAJA]
        )
    }
    avisos = {
        aviso.codigo: aviso
        for aviso in PasAviso.objects.filter(
            codigo__in=[cambio[2] for cambio in CAMBIOS_POR_EVALUACION.values()]
        )
    }
    faltantes = [
        nombre
        for nombre in (NOMBRE_ESTADO_SUSPENDIDO, NOMBRE_ESTADO_BAJA)
        if nombre.casefold() not in estados
    ] + [
        str(codigo)
        for codigo in {cambio[2] for cambio in CAMBIOS_POR_EVALUACION.values()}
        if codigo not in avisos
    ]
    if faltantes:
        raise ValidationError(
            "Falta configurar el catálogo PAS para procesar el retorno: "
            + ", ".join(sorted(faltantes))
            + "."
        )
    return estados, avisos


def _buscar_personas(filas):
    ids = {_entero(fila["ID"]) for fila in filas} - {None}
    dnis = {_entero(fila["NDOC"]) for fila in filas} - {None}
    personas = PasPersona.objects.select_related("estado").prefetch_related("avisos")
    por_id = {p.id_persona: p for p in personas.filter(id_persona__in=ids)}
    por_dni = {p.dni: p for p in personas.filter(dni__in=dnis)}
    return por_id, por_dni


def _persona_de(fila, personas):
    """Titular de la fila: por ID si coincide su DNI, si no por DNI."""

    por_id, por_dni = personas
    dni = _entero(fila["NDOC"])
    persona = por_id.get(_entero(fila["ID"]))
    if persona is not None and (dni is None or persona.dni == dni):
        return persona
    return por_dni.get(dni)


def _cambio_propuesto(fila, catalogo):
    """(categoría, estado, aviso) que propone una fila no compatible."""

    estados, avisos = catalogo
    categoria, nombre_estado, codigo_aviso = CAMBIOS_POR_EVALUACION[
        fila["EVALUACION"].upper()
    ]
    return (
        categoria or _categoria_incompatible(fila["MOTIVO"]),
        estados[nombre_estado.casefold()],
        avisos[codigo_aviso],
    )


def _sin_cambio(persona, estado, aviso):
    """El titular ya está de baja o ya tiene el estado y aviso propuestos."""

    if persona.estado.nombre.casefold() == NOMBRE_ESTADO_BAJA.casefold():
        return True
    return persona.estado_id == estado.pk and any(
        item.pk == aviso.pk for item in persona.avisos.all()
    )


def procesar_retorno_sintys(circuito, filas):
    """Convierte el retorno en alertas pendientes para los titulares que cambian.

    Una nueva importación del mismo período reemplaza las alertas SINTyS que
    seguían pendientes; las ya confirmadas no se vuelven a abrir.
    """

    requiere_catalogo = any(
        fila["EVALUACION"].upper() in CAMBIOS_POR_EVALUACION for fila in filas
    )
    catalogo = _catalogo_cambios() if requiere_catalogo else ({}, {})
    personas = _buscar_personas(filas)
    PasIncompatibilidad.objects.filter(
        origen=PasIncompatibilidad.Origen.SINTYS,
        periodo_impacto=circuito.periodo,
        estado=PasIncompatibilidad.Estado.PENDIENTE,
    ).delete()
    ya_gestionadas = set(
        PasIncompatibilidad.objects.filter(
            origen=PasIncompatibilidad.Origen.SINTYS,
            periodo_impacto=circuito.periodo,
        ).values_list("persona_id", "categoria")
    )
    resumen = {
        "total": len(filas),
        "compatibles": 0,
        "alertas": 0,
        "sin_cambios": 0,
        "ya_gestionadas": 0,
        "errores": [],
    }
    nuevas = []
    for fila in filas:
        evaluacion = fila["EVALUACION"].upper()
        if evaluacion == EVALUACION_COMPATIBLE:
            resumen["compatibles"] += 1
            continue
        if evaluacion not in CAMBIOS_POR_EVALUACION:
            resumen["errores"].append(
                f"Línea {fila['linea']}: evaluación desconocida «{fila['EVALUACION']}»."
            )
            continue
        persona = _persona_de(fila, personas)
        if persona is None:
            resumen["errores"].append(
                f"Línea {fila['linea']}: titular no encontrado "
                f"(ID {fila['ID'] or '—'}, DNI {fila['NDOC'] or '—'})."
            )
            continue
        categoria, estado, aviso = _cambio_propuesto(fila, catalogo)
        if _sin_cambio(persona, estado, aviso):
            resumen["sin_cambios"] += 1
            continue
        if (persona.pk, categoria) in ya_gestionadas:
            resumen["ya_gestionadas"] += 1
            continue
        ya_gestionadas.add((persona.pk, categoria))
        nuevas.append(
            PasIncompatibilidad(
                persona=persona,
                categoria=categoria,
                origen=PasIncompatibilidad.Origen.SINTYS,
                periodo_impacto=circuito.periodo,
                detalle=(fila["MOTIVO"] or evaluacion.capitalize())[:255],
                estado_propuesto=estado,
                aviso_propuesto=aviso,
            )
        )
    PasIncompatibilidad.objects.bulk_create(nuevas)
    resumen["alertas"] = len(nuevas)
    return resumen


def actualizar_procesamiento_alertas(circuito):
    """Marca la etapa de alertas completa cuando el retorno no deja pendientes."""

    if not circuito.pk:
        return circuito
    pendientes = (
        incompatibilidades_pendientes()
        .filter(periodo_impacto__lte=circuito.periodo)
        .exists()
    )
    completa = bool(circuito.fecha_importacion_sintys) and not pendientes
    if completa and not circuito.fecha_procesamiento_alertas:
        circuito.fecha_procesamiento_alertas = timezone.now()
    elif not completa:
        circuito.fecha_procesamiento_alertas = None
    circuito.save(update_fields=["fecha_procesamiento_alertas"])
    return circuito


@transaction.atomic
def registrar_importacion_sintys(circuito, archivo, usuario):
    """Guarda el retorno, genera las alertas y devuelve el resumen del proceso.

    Si el archivo no tiene el formato esperado levanta ``ValidationError`` y no
    registra nada.
    """

    filas = leer_retorno_sintys(archivo)
    resumen = procesar_retorno_sintys(circuito, filas)
    archivo.seek(0)
    circuito.fecha_importacion_sintys = timezone.now()
    circuito.importado_por = usuario
    circuito.resultado_importacion_sintys = resumen
    circuito.archivo_retorno_sintys.save(archivo.name, archivo, save=False)
    circuito.save(
        update_fields=[
            "fecha_importacion_sintys",
            "importado_por",
            "archivo_retorno_sintys",
            "resultado_importacion_sintys",
        ]
    )
    actualizar_procesamiento_alertas(circuito)
    return resumen


def mensaje_importacion(resumen):
    texto = (
        f"Retorno SINTyS procesado: {resumen['total']} registros, "
        f"{resumen['alertas']} alertas nuevas, {resumen['compatibles']} compatibles, "
        f"{resumen['sin_cambios']} sin cambios."
    )
    if resumen["ya_gestionadas"]:
        texto += f" {resumen['ya_gestionadas']} ya estaban confirmadas."
    if resumen["errores"]:
        texto += f" {len(resumen['errores'])} filas con observaciones."
    return texto


def incompatibilidades_pendientes():
    return (
        PasIncompatibilidad.objects.select_related(
            "persona", "persona__estado", "estado_propuesto", "aviso_propuesto"
        )
        .filter(estado=PasIncompatibilidad.Estado.PENDIENTE)
        .exclude(
            persona__estado__nombre__iexact=NOMBRE_ESTADO_BAJA,
            persona__avisos__codigo=CODIGO_AVISO_FALLECIDO,
        )
        .distinct()
        .order_by("-fecha_deteccion", "pk")
    )


def _bloquear_pendiente(incompatibilidad):
    actual = (
        PasIncompatibilidad.objects.select_for_update()
        .select_related("persona", "estado_propuesto", "aviso_propuesto")
        .get(pk=incompatibilidad.pk)
    )
    if actual.estado != PasIncompatibilidad.Estado.PENDIENTE:
        raise ValueError("La alerta ya fue gestionada.")
    return actual


def _observacion(incompatibilidad):
    """Detalle que trajo el cruce, para el historial del titular."""

    return (
        f"{incompatibilidad.get_origen_display()} · "
        f"{incompatibilidad.get_categoria_display()}: {incompatibilidad.detalle}"
    )


def _marcar_confirmada(incompatibilidad, usuario):
    incompatibilidad.estado = PasIncompatibilidad.Estado.CONFIRMADA
    incompatibilidad.fecha_gestion = timezone.now()
    incompatibilidad.gestionada_por = usuario
    incompatibilidad.save(update_fields=["estado", "fecha_gestion", "gestionada_por"])
    actualizar_procesamiento_alertas(
        PasCircuitoMensual.objects.filter(
            periodo=incompatibilidad.periodo_impacto
        ).first()
        or PasCircuitoMensual(periodo=incompatibilidad.periodo_impacto)
    )
    return incompatibilidad


@transaction.atomic
def confirmar_incompatibilidad(incompatibilidad, usuario=None):
    """Aplica el cambio propuesto por el cruce y deja la alerta confirmada."""

    actual = _bloquear_pendiente(incompatibilidad)
    persona = actual.persona
    if actual.estado_propuesto_id:
        avisos_actuales = set(persona.avisos.values_list("pk", flat=True))
        if persona.estado_id != actual.estado_propuesto_id or avisos_actuales != {
            actual.aviso_propuesto_id
        }:
            aplicar_cambio_estado(
                persona,
                actual.estado_propuesto,
                [actual.aviso_propuesto] if actual.aviso_propuesto_id else [],
                usuario=usuario,
                observacion=_observacion(actual),
            )
    return _marcar_confirmada(actual, usuario)


@transaction.atomic
def modificar_incompatibilidad(incompatibilidad, form, usuario=None):
    """Aplica el cambio de estado elegido por el operador y confirma la alerta."""

    actual = _bloquear_pendiente(incompatibilidad)
    cambiar_estado(
        actual.persona, form, usuario=usuario, observacion=_observacion(actual)
    )
    return _marcar_confirmada(actual, usuario)


def construir_etapas(circuito):
    definiciones = (
        ("Exportación a SINTyS (VIAS)", circuito.fecha_exportacion_sintys, False),
        ("Importación retorno SINTyS", circuito.fecha_importacion_sintys, False),
        ("Cruce FTP Justicia", circuito.fecha_cruce_justicia, True),
        ("Cruce Migraciones", circuito.fecha_cruce_migraciones, True),
        ("Procesamiento de alertas", circuito.fecha_procesamiento_alertas, False),
        ("Cierre del circuito mensual", circuito.fecha_cierre, False),
    )
    return [
        {
            "numero": numero,
            "nombre": nombre,
            "fecha": fecha,
            "completada": bool(fecha),
            "integracion_pendiente": integracion_pendiente and not fecha,
        }
        for numero, (nombre, fecha, integracion_pendiente) in enumerate(
            definiciones, start=1
        )
    ]
