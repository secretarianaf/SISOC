"""Lectura de planillas ``.xlsx`` y ``.csv`` para las importaciones del panel.

- Del ``.xlsx`` se lee sólo la **primera hoja**: el padrón oficial trae otras
  hojas que pueden tener datos personales y no se abren.
- El encabezado no siempre está en la primera fila (el padrón trae filas de
  título): se busca entre las primeras filas la que tenga las columnas
  obligatorias.
- El ``.xlsx`` se recorre en streaming con ``lxml`` en vez de ``openpyxl``:
  con el padrón real (64.495 filas) ``openpyxl`` en modo ``read_only`` tarda el
  doble, y la importación tiene que entrar en el tiempo de un request. El XML
  se parsea sin DTD, sin entidades y sin red, y se limita el tamaño
  descomprimido de cada parte para no aceptar bombas zip.
"""

import csv
import io
import posixpath
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import lru_cache

from django.core.exceptions import ValidationError
from lxml import etree

MAX_BYTES_ARCHIVO = 25 * 1024 * 1024
MAX_BYTES_PARTE_XML = 300 * 1024 * 1024
FILAS_BUSQUEDA_ENCABEZADO = 30
EXTENSIONES = ("xlsx", "csv")

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
COLUMNA_CELDA = re.compile(r"^[A-Z]+$")
TAG_V = f"{NS_MAIN}v"


class NumeroCelda(str):
    """Texto de una celda numérica del ``.xlsx`` (Excel le saca los ceros)."""


@dataclass
class Planilla:
    """Encabezado reconocido y filas como ``(numero_de_fila, {campo: valor})``."""

    fila_encabezado: int
    columnas: list
    filas: list


def normalizar_encabezado(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def extension_de(nombre):
    return (nombre or "").rsplit(".", 1)[-1].lower() if "." in (nombre or "") else ""


def _parser_seguro():
    return etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
    )


def _abrir_parte(libro, nombre):
    try:
        info = libro.getinfo(nombre)
    except KeyError as exc:
        raise ValidationError("El archivo Excel está incompleto.") from exc
    if info.file_size > MAX_BYTES_PARTE_XML:
        raise ValidationError("El archivo Excel es demasiado grande.")
    return libro.open(info)


def _ruta_primera_hoja(libro):
    with _abrir_parte(libro, "xl/workbook.xml") as parte:
        workbook = etree.parse(parte, _parser_seguro()).getroot()
    hoja = workbook.find(f"{NS_MAIN}sheets/{NS_MAIN}sheet")
    if hoja is None:
        raise ValidationError("El archivo Excel no tiene hojas.")
    rel_id = hoja.get(f"{NS_REL}id")
    with _abrir_parte(libro, "xl/_rels/workbook.xml.rels") as parte:
        relaciones = etree.parse(parte, _parser_seguro()).getroot()
    for relacion in relaciones.iter(f"{NS_PKG_REL}Relationship"):
        if relacion.get("Id") == rel_id:
            destino = relacion.get("Target", "")
            if destino.startswith("/"):
                return destino.lstrip("/")
            return posixpath.normpath(posixpath.join("xl", destino))
    raise ValidationError("No se encontró la primera hoja del archivo Excel.")


def _textos_compartidos(libro):
    if "xl/sharedStrings.xml" not in libro.namelist():
        return []
    textos = []
    tag_t = f"{NS_MAIN}t"
    with _abrir_parte(libro, "xl/sharedStrings.xml") as parte:
        for _evento, item in etree.iterparse(
            parte,
            tag=f"{NS_MAIN}si",
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
        ):
            primero = item[0] if len(item) else None
            if len(item) == 1 and primero.tag == tag_t:
                # Caso común: un solo <t> sin formato.
                textos.append(primero.text or "")
            else:
                # Texto con formato (<r><t>…): sin el fonético (<rPh>).
                textos.append(
                    "".join(
                        t.text or ""
                        for t in item.iter(tag_t)
                        if t.getparent().tag != f"{NS_MAIN}rPh"
                    )
                )
            item.clear()
            while item.getprevious() is not None:
                del item.getparent()[0]
    return textos


@lru_cache(maxsize=4096)
def _indice_de_letras(letras):
    if not COLUMNA_CELDA.match(letras):
        return None
    indice = 0
    for letra in letras:
        indice = indice * 26 + ord(letra) - 64
    return indice - 1


def _indice_columna(referencia, siguiente):
    indice = _indice_de_letras((referencia or "").rstrip("0123456789"))
    return siguiente if indice is None else indice


def _texto_compartido(texto, compartidos):
    try:
        return compartidos[int(texto)]
    except (TypeError, ValueError, IndexError):
        return ""


def _numero(texto):
    """Celda numérica como texto (``20000100``, no ``20000100.0``)."""
    try:
        numero = float(texto)
    except ValueError:
        return texto
    return NumeroCelda(str(int(numero)) if numero.is_integer() else texto)


def _valor_celda(celda, compartidos):
    tipo = celda.get("t")
    if tipo == "s" and len(celda) and celda[0].tag == TAG_V:
        # Caso común (texto compartido), resuelto sin más búsquedas.
        return _texto_compartido(celda[0].text, compartidos)
    if tipo == "inlineStr":
        return "".join(t.text or "" for t in celda.iter(f"{NS_MAIN}t"))
    valor = celda.find(TAG_V)
    texto = valor.text if valor is not None and valor.text is not None else ""
    if tipo == "s":
        resultado = _texto_compartido(texto, compartidos)
    elif tipo in ("str", "d"):
        resultado = texto
    elif tipo in ("b", "e") or not texto:
        resultado = ""
    else:
        resultado = _numero(texto)
    return resultado


def _filas_xlsx(archivo):
    try:
        libro = zipfile.ZipFile(archivo)
    except zipfile.BadZipFile as exc:
        raise ValidationError("El archivo no es un Excel (.xlsx) válido.") from exc
    with libro:
        ruta = _ruta_primera_hoja(libro)
        compartidos = _textos_compartidos(libro)
        siguiente_fila = 1
        tag_c = f"{NS_MAIN}c"
        with _abrir_parte(libro, ruta) as parte:
            for _evento, fila in etree.iterparse(
                parte,
                tag=f"{NS_MAIN}row",
                resolve_entities=False,
                no_network=True,
                load_dtd=False,
            ):
                numero = int(fila.get("r") or siguiente_fila)
                siguiente_fila = numero + 1
                valores = []
                for celda in fila:  # las celdas <c> son hijas directas de <row>
                    if celda.tag != tag_c:
                        continue
                    indice = _indice_columna(celda.get("r"), len(valores))
                    if indice > len(valores):
                        valores.extend([""] * (indice - len(valores)))
                    valores.append(_valor_celda(celda, compartidos))
                fila.clear()
                while fila.getprevious() is not None:
                    del fila.getparent()[0]
                yield numero, valores


def _decodificar(crudo):
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ValidationError("No se pudo leer el archivo: guardalo como CSV UTF-8.")


def _filas_csv(archivo):
    texto = _decodificar(archivo.read())
    # El separador más frecuente al principio del archivo (``csv.Sniffer`` se
    # confunde con las filas de título, que no tienen separadores).
    muestra = texto[:8192]
    separador = max(",;|\t", key=muestra.count)
    lector = csv.reader(io.StringIO(texto), delimiter=separador)
    for numero, valores in enumerate(lector, 1):
        yield numero, valores


def _ubicar_encabezado(filas, alias, requeridas):
    """Busca la fila de encabezado entre las primeras ``FILAS_BUSQUEDA_ENCABEZADO``."""
    mejor = None
    for _ in range(FILAS_BUSQUEDA_ENCABEZADO):
        try:
            numero, valores = next(filas)
        except StopIteration:
            break
        columnas = [alias.get(normalizar_encabezado(v)) for v in valores]
        if all(c in columnas for c in requeridas):
            return numero, columnas, [str(v).strip() for v in valores]
        reconocidas = {c for c in columnas if c}
        if reconocidas and (mejor is None or len(reconocidas) > len(mejor)):
            mejor = reconocidas
    faltantes = [c for c in requeridas if not mejor or c not in mejor]
    raise ValidationError(
        "No se encontró el encabezado del archivo. Faltan columnas obligatorias: "
        + ", ".join(faltantes)
        + "."
    )


def leer_planilla(archivo, nombre, alias, requeridas):
    """Lee la primera hoja del ``.xlsx`` (o el ``.csv``) y mapea columnas.

    ``alias`` va del encabezado normalizado al campo; ``requeridas`` son los
    campos que tiene que tener el encabezado. Devuelve una ``Planilla`` con las
    filas no vacías posteriores al encabezado.
    """
    extension = extension_de(nombre)
    if extension not in EXTENSIONES:
        raise ValidationError("El archivo tiene que ser .xlsx o .csv.")
    archivo.seek(0, io.SEEK_END)
    if archivo.tell() > MAX_BYTES_ARCHIVO:
        raise ValidationError("El archivo no puede superar los 25 MB.")
    archivo.seek(0)
    filas = _filas_xlsx(archivo) if extension == "xlsx" else _filas_csv(archivo)
    fila_encabezado, columnas, originales = _ubicar_encabezado(filas, alias, requeridas)
    return Planilla(
        fila_encabezado=fila_encabezado,
        columnas=[
            {"original": original, "campo": campo}
            for original, campo in zip(originales, columnas)
            if campo
        ],
        filas=_filas_con_campos(filas, columnas),
    )


def _filas_con_campos(filas, columnas):
    """Filas no vacías como ``(numero, {campo: valor})``."""
    datos = []
    for numero, valores in filas:
        fila = {}
        for campo, valor in zip(columnas, valores):
            if campo and not fila.get(campo):
                fila[campo] = valor if isinstance(valor, NumeroCelda) else str(valor)
        if any(str(v).strip() for v in fila.values()):
            datos.append((numero, fila))
    return datos
