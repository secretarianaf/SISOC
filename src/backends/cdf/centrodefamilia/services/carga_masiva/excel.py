"""Lectura y generación de archivos Excel de la carga masiva."""

import re
import zipfile
from datetime import date, datetime
from io import BytesIO

from django.core.exceptions import ValidationError
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from centrodefamilia.models import Actividad, FilaCargaMasivaPreinscriptos
from centrodefamilia.services.carga_masiva.columnas import (
    COLUMNAS,
    ENCABEZADOS,
    HOJA_ACTIVIDADES,
    HOJA_DATOS,
    HOJA_INSTRUCCIONES,
    HOJA_LISTAS,
    HOJA_UBICACIONES,
    MAX_FILAS,
    MAX_TAMANIO_BYTES,
    SEPARADOR_MULTIPLE,
    Tipo,
)
from core.models import Localidad, Municipio, Provincia
from core.services.csv_export import neutralize_csv_formula

NOMBRE_PLANTILLA = "plantilla_carga_masiva_preinscriptos.xlsx"
FILAS_CON_FORMATO = MAX_FILAS + 1
# Corta la lectura de hojas con miles de filas vacías con formato.
MAX_FILAS_LEIDAS = 10000
_ESPACIOS = re.compile(r"\s+")
_ENCABEZADO = Font(bold=True, color="FFFFFF")
_FONDO_ENCABEZADO = PatternFill("solid", fgColor="04756F")


def _normalizar_encabezado(valor):
    return _ESPACIOS.sub(" ", str(valor or "")).strip().casefold()


def celda_a_texto(valor):
    """Convierte una celda a texto sin perder ceros, sin `.0` ni notación científica."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, float):
        return str(int(valor)) if valor.is_integer() else repr(valor)
    return str(valor).strip()


def leer_archivo(archivo):
    """Devuelve [(numero_fila, {clave: texto})] o lanza ValidationError (RN-10/11/12)."""
    nombre = getattr(archivo, "name", "") or ""
    if not nombre.lower().endswith(".xlsx"):
        raise ValidationError("Solo se aceptan archivos .xlsx de la plantilla oficial.")
    if archivo.size > MAX_TAMANIO_BYTES:
        raise ValidationError("El archivo supera el máximo de 10 MB.")

    try:
        archivo.seek(0)
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise ValidationError(
            "No se pudo leer el archivo. Verifique que sea un .xlsx de la "
            "plantilla oficial."
        ) from exc

    try:
        if HOJA_DATOS not in libro.sheetnames:
            raise ValidationError(
                f"El archivo no tiene la hoja «{HOJA_DATOS}» de la plantilla oficial."
            )
        filas = libro[HOJA_DATOS].iter_rows(values_only=True)
        _validar_encabezado(next(filas, ()))
        return _leer_filas(filas)
    finally:
        libro.close()


def _validar_encabezado(encabezado):
    recibidos = [_normalizar_encabezado(valor) for valor in encabezado]
    while recibidos and not recibidos[-1]:
        recibidos.pop()
    esperados = [_normalizar_encabezado(valor) for valor in ENCABEZADOS]
    if recibidos != esperados:
        raise ValidationError(
            "Los encabezados no coinciden con la plantilla oficial. Descargue la "
            "plantilla vigente y copie los datos sin cambiar columnas."
        )


def _leer_filas(filas):
    resultado = []
    for numero_fila, fila in enumerate(filas, start=2):
        if numero_fila > MAX_FILAS_LEIDAS:
            raise ValidationError(
                "El archivo tiene demasiadas filas. Copie los datos a la plantilla "
                "oficial sin filas de más."
            )
        valores = [celda_a_texto(valor) for valor in fila[: len(COLUMNAS)]]
        if not any(valores):
            continue
        if len(resultado) == MAX_FILAS:
            raise ValidationError(
                f"El archivo tiene más de {MAX_FILAS} filas con datos. Divídalo en "
                "varios archivos."
            )
        valores += [""] * (len(COLUMNAS) - len(valores))
        resultado.append(
            (
                numero_fila,
                {col.clave: valor for col, valor in zip(COLUMNAS, valores)},
            )
        )
    if not resultado:
        raise ValidationError("El archivo no tiene filas con datos.")
    return resultado


# ——— Plantilla ———


def generar_plantilla():
    libro = Workbook()
    hoja = libro.active
    hoja.title = HOJA_DATOS
    listas = libro.create_sheet(HOJA_LISTAS)
    rangos = _escribir_listas(listas)
    ubicaciones = libro.create_sheet(HOJA_UBICACIONES)
    rangos.update(_escribir_ubicaciones(ubicaciones))
    _escribir_hoja_datos(hoja, rangos)
    _escribir_actividades(libro.create_sheet(HOJA_ACTIVIDADES))
    _escribir_instrucciones(libro.create_sheet(HOJA_INSTRUCCIONES, 1))
    listas.sheet_state = "hidden"
    ubicaciones.sheet_state = "hidden"
    return _a_bytes(libro)


def _escribir_encabezado(hoja, encabezados):
    hoja.append(list(encabezados))
    for indice, celda in enumerate(hoja[1], start=1):
        celda.font = _ENCABEZADO
        celda.fill = _FONDO_ENCABEZADO
        hoja.column_dimensions[get_column_letter(indice)].width = max(
            14, len(str(celda.value)) + 2
        )
    hoja.freeze_panes = "A2"


def _listas_de_opciones():
    listas = {
        Tipo.PROVINCIA: list(
            Provincia.objects.order_by("nombre").values_list("nombre", flat=True)
        ),
    }
    for columna in COLUMNAS:
        if columna.opciones and columna.clave not in listas:
            listas[columna.clave] = list(columna.opciones)
    return listas


def _escribir_listas(hoja):
    """Escribe los valores de las listas desplegables y devuelve sus rangos."""
    rangos = {}
    for indice, (clave, valores) in enumerate(_listas_de_opciones().items(), start=1):
        letra = get_column_letter(indice)
        hoja.cell(row=1, column=indice, value=clave)
        for fila, valor in enumerate(valores, start=2):
            hoja.cell(row=fila, column=indice, value=neutralize_csv_formula(valor))
        ultima = max(len(valores) + 1, 2)
        rangos[clave] = f"'{HOJA_LISTAS}'!${letra}$2:${letra}${ultima}"
    return rangos


def _escribir_ubicaciones(hoja):
    """Municipios por provincia y localidades por municipio, ordenados por su padre.

    Cada lista desplegable dependiente toma el bloque contiguo de su padre con
    DESREF/COINCIDIR/CONTAR.SI, así que las filas tienen que quedar agrupadas.
    """
    hoja.append(["Provincia", "Municipio", "Provincia|Municipio", "Localidad"])
    municipios = list(
        Municipio.objects.filter(provincia__isnull=False)
        .order_by("provincia__nombre", "nombre")
        .values_list("provincia__nombre", "nombre")
    )
    localidades = list(
        Localidad.objects.filter(municipio__provincia__isnull=False)
        .order_by("municipio__provincia__nombre", "municipio__nombre", "nombre")
        .values_list("municipio__provincia__nombre", "municipio__nombre", "nombre")
    )
    for fila in range(max(len(municipios), len(localidades))):
        valores = ["", "", "", ""]
        if fila < len(municipios):
            valores[0:2] = municipios[fila]
        if fila < len(localidades):
            provincia, municipio, localidad = localidades[fila]
            valores[2:4] = [f"{provincia}|{municipio}", localidad]
        hoja.append([neutralize_csv_formula(valor) for valor in valores])
    ultima_municipio = len(municipios) + 1
    ultima_localidad = len(localidades) + 1
    return {
        Tipo.MUNICIPIO: (
            f"'{HOJA_UBICACIONES}'!$A$2:$A${ultima_municipio}",
            f"'{HOJA_UBICACIONES}'!$B$1",
        ),
        Tipo.LOCALIDAD: (
            f"'{HOJA_UBICACIONES}'!$C$2:$C${ultima_localidad}",
            f"'{HOJA_UBICACIONES}'!$D$1",
        ),
    }


def _formula_dependiente(rango_claves, origen, clave):
    """Lista con las filas de `rango_claves` iguales a `clave` (bloque contiguo)."""
    return (
        f"OFFSET({origen},MATCH({clave},{rango_claves},0),0,"
        f"COUNTIF({rango_claves},{clave}),1)"
    )


def _formula_lista(columna, rangos, letras):
    if columna.tipo == Tipo.MUNICIPIO:
        provincia = f"${letras[columna.clave.replace('municipio', 'provincia')]}2"
        return _formula_dependiente(*rangos[Tipo.MUNICIPIO], provincia)
    if columna.tipo == Tipo.LOCALIDAD:
        provincia = f"${letras[columna.clave.replace('localidad', 'provincia')]}2"
        municipio = f"${letras[columna.clave.replace('localidad', 'municipio')]}2"
        return _formula_dependiente(
            *rangos[Tipo.LOCALIDAD], f'{provincia}&"|"&{municipio}'
        )
    clave = Tipo.PROVINCIA if columna.tipo == Tipo.PROVINCIA else columna.clave
    return rangos.get(clave)


def _escribir_hoja_datos(hoja, rangos):
    _escribir_encabezado(hoja, ENCABEZADOS)
    letras = {
        columna.clave: get_column_letter(indice)
        for indice, columna in enumerate(COLUMNAS, start=1)
    }
    for indice, columna in enumerate(COLUMNAS, start=1):
        letra = get_column_letter(indice)
        rango_celdas = f"{letra}2:{letra}{FILAS_CON_FORMATO}"
        if columna.tipo in (Tipo.CUIL, Tipo.DNI, Tipo.DIGITOS):
            for fila in range(2, FILAS_CON_FORMATO + 1):
                hoja.cell(row=fila, column=indice).number_format = "@"
        formula = _formula_lista(columna, rangos, letras)
        if not formula:
            continue
        validacion = DataValidation(
            type="list",
            formula1=formula,
            allow_blank=True,
            # Varios valores separados por ; no entran en una lista desplegable.
            showErrorMessage=columna.tipo != Tipo.OPCIONES,
            errorTitle="Valor no válido",
            error="Elija un valor de la lista.",
        )
        validacion.add(rango_celdas)
        hoja.add_data_validation(validacion)


def _escribir_actividades(hoja):
    _escribir_encabezado(hoja, ("Actividad", "Categoría"))
    for nombre, categoria in (
        Actividad.objects.select_related("categoria")
        .order_by("categoria__nombre", "nombre")
        .values_list("nombre", "categoria__nombre")
    ):
        hoja.append([neutralize_csv_formula(nombre), neutralize_csv_formula(categoria)])


def _formato_columna(columna):
    formatos = {
        Tipo.CUIL: "11 dígitos, sin guiones. Debe coincidir con el DNI.",
        Tipo.DNI: "7 u 8 dígitos.",
        Tipo.SEXO: "F, M o X.",
        Tipo.FECHA: "dd/mm/aaaa. No puede ser futura.",
        Tipo.ENTERO: "Número entero.",
        Tipo.EMAIL: "Correo electrónico válido.",
        Tipo.SI_NO: "Sí o No. Vacío equivale a No.",
        Tipo.PROVINCIA: "Nombre de la lista.",
        Tipo.MUNICIPIO: "Lista desplegable con los municipios de la provincia elegida.",
        Tipo.LOCALIDAD: "Lista desplegable con las localidades del municipio elegido.",
    }
    partes = []
    if columna.tipo in formatos:
        partes.append(formatos[columna.tipo])
    if columna.tipo in (Tipo.OPCION, Tipo.OPCIONES):
        partes.append("Valores: " + ", ".join(columna.opciones) + ".")
    if columna.tipo == Tipo.DIGITOS:
        partes.append(f"Solo números, hasta {columna.largo_maximo} dígitos.")
    elif columna.largo_maximo and columna.tipo == Tipo.TEXTO:
        partes.append(f"Hasta {columna.largo_maximo} caracteres.")
    if columna.descripcion:
        partes.append(columna.descripcion)
    return " ".join(partes) or "Texto libre."


def _escribir_instrucciones(hoja):
    hoja.append(["Carga masiva de preinscriptos - Centros de Familia"])
    hoja["A1"].font = Font(bold=True, size=14)
    for linea in (
        "Complete la hoja «Preinscriptos»: una fila por preinscripto con su titular.",
        "No cambie, agregue ni reordene columnas: el archivo se rechaza completo.",
        f"Máximo {MAX_FILAS} filas con datos y 10 MB por archivo.",
        f"Para varios valores en una celda, sepárelos con «{SEPARADOR_MULTIPLE}».",
        "Las columnas de CUIL y DNI tienen formato texto para no perder dígitos.",
        "",
    ):
        hoja.append([linea])
    hoja.append(["#", "Columna", "Obligatoria", "Formato / valores"])
    for celda in hoja[hoja.max_row]:
        celda.font = _ENCABEZADO
        celda.fill = _FONDO_ENCABEZADO
    for numero, columna in enumerate(COLUMNAS, start=1):
        obligatoria = "Sí" if columna.obligatoria else "No"
        if columna.clave == "actividades_detalle":
            obligatoria = "Si realiza actividades extracurriculares"
        hoja.append(
            [numero, columna.encabezado, obligatoria, _formato_columna(columna)]
        )
    for letra, ancho in (("A", 6), ("B", 42), ("C", 22), ("D", 90)):
        hoja.column_dimensions[letra].width = ancho


# ——— Descargas ———


def _a_bytes(libro):
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _fila_segura(valores):
    return [neutralize_csv_formula(valor) for valor in valores]


def _motivos(mensajes):
    return "\n".join(f"{m['columna']}: {m['mensaje']}" for m in mensajes)


def generar_listado_errores(carga):
    """Filas con error y sus motivos, con los datos para corregir fuera de SISOC (RF-07)."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Errores"
    _escribir_encabezado(hoja, ("Fila", "Motivos") + ENCABEZADOS)
    filas = carga.filas.filter(
        quitada=False, estado=FilaCargaMasivaPreinscriptos.Estado.ERROR
    )
    for fila in filas:
        hoja.append(
            _fila_segura(
                [fila.numero_fila, _motivos(fila.errores)]
                + [fila.datos.get(col.clave, "") for col in COLUMNAS]
            )
        )
    return _a_bytes(libro)


def generar_comprobante(carga):
    """Comprobante del lote: una fila por fila del Excel, cargada o rechazada (RF-12).

    Las filas con error no se cargan: figuran como «Rechazada» con sus motivos.
    """
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Comprobante"
    _escribir_encabezado(
        hoja,
        (
            "Fila",
            "CUIL preinscripto",
            "DNI preinscripto",
            "CUIL titular",
            "DNI titular",
            "Resultado preinscripto",
            "Resultado titular",
            "Motivos del rechazo",
            "Advertencias",
            "ID preinscripto en SISOC",
        ),
    )
    for fila in carga.filas.filter(quitada=False):
        rechazada = fila.estado == FilaCargaMasivaPreinscriptos.Estado.ERROR
        hoja.append(
            _fila_segura(
                [
                    fila.numero_fila,
                    fila.datos.get("cuil", ""),
                    fila.datos.get("dni", ""),
                    fila.datos.get("titular_cuil", ""),
                    fila.datos.get("titular_dni", ""),
                    (
                        "Rechazada"
                        if rechazada
                        else fila.get_accion_preinscripto_display()
                    ),
                    "" if rechazada else fila.get_accion_titular_display(),
                    _motivos(fila.errores) if rechazada else "",
                    _motivos(fila.advertencias),
                    fila.beneficiario_id or "",
                ]
            )
        )
    return _a_bytes(libro)
