"""Formato Word del Informe Técnico generado desde el Gestor de templates.

Replica el membrete y las tablas con celdas combinadas del modelo institucional
del Programa Alimentar Comunidad, que htmldocx no resuelve por sí solo.
"""

import logging
import os
import re

from django.apps import apps
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum import text as docx_text
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from htmldocx import HtmlToDocx

logger = logging.getLogger("admisiones.services.informes")

PARRAFO_VACIO_EDITOR = re.compile(r"<p(\s[^>]*)?>\s*<br\s*/?>\s*</p>", re.IGNORECASE)

# Elementos que el esquema de w:tblPr ubica después de w:tblBorders.
SUCESORES_BORDES_TABLA = (
    "w:shd",
    "w:tblLayout",
    "w:tblCellMar",
    "w:tblLook",
    "w:tblCaption",
    "w:tblDescription",
)

# Elementos que el esquema de w:pPr ubica después de w:pBdr.
SUCESORES_BORDES_PARRAFO = (
    "w:shd",
    "w:tabs",
    "w:suppressAutoHyphens",
    "w:spacing",
    "w:ind",
    "w:contextualSpacing",
    "w:jc",
    "w:outlineLvl",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)

# python-docx arma sus enums en tiempo de ejecución y pylint no los ve.
# pylint: disable=no-member
ALINEACIONES_HTML = {
    "left": docx_text.WD_ALIGN_PARAGRAPH.LEFT,
    "center": docx_text.WD_ALIGN_PARAGRAPH.CENTER,
    "right": docx_text.WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": docx_text.WD_ALIGN_PARAGRAPH.JUSTIFY,
}
CENTRADO_VERTICAL = WD_CELL_VERTICAL_ALIGNMENT.CENTER
TABULACION_CENTRADA = docx_text.WD_TAB_ALIGNMENT.CENTER
# pylint: enable=no-member


class HtmlToDocxConCeldasCombinadas(HtmlToDocx):
    """HtmlToDocx que respeta ``colspan`` y ``rowspan`` en las tablas.

    htmldocx 0.0.6 dimensiona la tabla con las celdas de la primera fila e
    ignora las combinadas: una tabla con título combinado rompe el parseo y el
    informe termina en el fallback de texto plano.
    """

    def run_process(self, html):
        # El editor deja los renglones vacíos como <p><br></p>: en el navegador
        # ocupan una línea, pero htmldocx los convierte en un párrafo con salto.
        super().run_process(PARRAFO_VACIO_EDITOR.sub(r"<p\1></p>", html))

    def handle_table(self):
        tabla_soup = self.tables[self.table_no]
        filas = self.get_table_rows(tabla_soup)
        ubicaciones, total_filas, total_columnas = self._ubicar_celdas(filas)
        self.table = self.doc.add_table(total_filas, total_columnas)

        if self.table_style:
            try:
                self.table.style = self.table_style
            except KeyError as error:
                raise ValueError(
                    f"Unable to apply style {self.table_style}."
                ) from error

        for celda_soup, fila, columna, alto, ancho in ubicaciones:
            celda = self.table.cell(fila, columna)
            if alto > 1 or ancho > 1:
                celda = celda.merge(
                    self.table.cell(fila + alto - 1, columna + ancho - 1)
                )
            contenido = self.get_cell_html(celda_soup)
            if celda_soup.name == "th":
                contenido = f"<b>{contenido}</b>"
            parser_celda = type(self)()
            parser_celda.copy_settings_from(self)
            parser_celda.add_html_to_cell(contenido, celda)
            self._alinear_celda(celda_soup, celda)

        # Igual que htmldocx: ignorar las etiquetas hasta cerrar esta tabla.
        self.instances_to_skip = len(tabla_soup.find_all("table"))
        self.skip_tag = "table"
        self.skip = True
        self.table = None

    def _ubicar_celdas(self, filas):
        """Devuelve la posición en grilla de cada celda y el tamaño total."""

        ocupadas = set()
        ubicaciones = []
        for indice_fila, fila in enumerate(filas):
            columna = 0
            for celda_soup in self.get_table_columns(fila):
                while (indice_fila, columna) in ocupadas:
                    columna += 1
                alto = min(
                    self._leer_span(celda_soup, "rowspan"),
                    len(filas) - indice_fila,
                )
                ancho = self._leer_span(celda_soup, "colspan")
                for fila_ocupada in range(indice_fila, indice_fila + alto):
                    for columna_ocupada in range(columna, columna + ancho):
                        ocupadas.add((fila_ocupada, columna_ocupada))
                ubicaciones.append((celda_soup, indice_fila, columna, alto, ancho))
                columna += ancho

        total_columnas = max((columna for _, columna in ocupadas), default=-1) + 1
        return ubicaciones, len(filas), total_columnas

    def _alinear_celda(self, celda_soup, celda):
        """Traslada el ``text-align`` de la celda HTML a sus párrafos."""

        estilos = self.parse_dict_string(celda_soup.get("style") or "")
        alineacion = ALINEACIONES_HTML.get(estilos.get("text-align", "").strip())
        if alineacion is None:
            return
        for parrafo in celda.paragraphs:
            if parrafo.alignment is None:
                parrafo.alignment = alineacion

    @staticmethod
    def _leer_span(celda_soup, atributo):
        valor = str(celda_soup.get(atributo) or "1").strip()
        return int(valor) if valor.isdigit() and int(valor) > 0 else 1


class MembreteInformeTecnico:
    """Encabezado y pie del modelo institucional del Informe Técnico.

    El modelo arma el encabezado con una tabla invisible; acá se replica con
    párrafos y tabulaciones porque GDE no admite tablas en el documento.
    """

    ARCHIVO_ESCUDO = "escudo_informe_tecnico.jpg"
    RENGLONES_PROGRAMA = ("PROGRAMA ALIMENTAR", "COMUNIDAD")
    TEXTO_SECRETARIA = "Secretaría de Niñez Adolescencia y Familia"
    TEXTO_MINISTERIO = "Ministerio de Capital Humano"
    FUENTE = "Times New Roman"
    COLOR_TEXTO = RGBColor(0x17, 0x37, 0x5E)
    COLOR_LINEA = "002060"
    ANCHO_ESCUDO_PT = 24
    TAMANIO_PROGRAMA_PT = 10.5
    TAMANIO_SECRETARIA_PT = 8.5
    TAMANIO_MINISTERIO_PT = 10.5
    # Ejes centrados del bloque del programa y del bloque del ministerio.
    EJE_PROGRAMA_MM = 22
    EJE_MINISTERIO_MM = 123

    @classmethod
    def aplicar(cls, documento):
        seccion = documento.sections[0]
        cls._armar_encabezado(seccion.header)
        cls._armar_pie(seccion.footer)

    @classmethod
    def _armar_encabezado(cls, encabezado):
        # El primer párrafo se conserva: la vista previa le agrega la marca de agua.
        parrafo_escudo = encabezado.paragraphs[0]
        parrafo_secretaria = encabezado.add_paragraph()
        parrafo_ministerio = encabezado.add_paragraph()
        for parrafo in (parrafo_escudo, parrafo_secretaria, parrafo_ministerio):
            cls._preparar_renglon(parrafo)

        ruta_escudo = cls._ruta_escudo()
        if os.path.exists(ruta_escudo):
            parrafo_escudo.add_run("\t\t")
            parrafo_escudo.add_run().add_picture(
                ruta_escudo, width=Pt(cls.ANCHO_ESCUDO_PT)
            )
        else:
            logger.warning("No se encontró el escudo del membrete: %s", ruta_escudo)

        programa_superior, programa_inferior = cls.RENGLONES_PROGRAMA
        cls._agregar_texto(
            parrafo_secretaria, f"\t{programa_superior}", cls.TAMANIO_PROGRAMA_PT
        )
        cls._agregar_texto(
            parrafo_secretaria, f"\t{cls.TEXTO_SECRETARIA}", cls.TAMANIO_SECRETARIA_PT
        )
        cls._agregar_texto(
            parrafo_ministerio, f"\t{programa_inferior}", cls.TAMANIO_PROGRAMA_PT
        )
        cls._agregar_texto(
            parrafo_ministerio, f"\t{cls.TEXTO_MINISTERIO}", cls.TAMANIO_MINISTERIO_PT
        )
        cls._aplicar_linea_inferior(parrafo_ministerio)

    @classmethod
    def _armar_pie(cls, pie):
        parrafo = pie.paragraphs[0]
        parrafo.alignment = ALINEACIONES_HTML["right"]
        campo = OxmlElement("w:fldSimple")
        campo.set(qn("w:instr"), "PAGE")
        run = OxmlElement("w:r")
        texto = OxmlElement("w:t")
        texto.text = "1"
        run.append(texto)
        campo.append(run)
        parrafo._p.append(campo)  # pylint: disable=protected-access

    @classmethod
    def _preparar_renglon(cls, parrafo):
        # Sin el estilo "Header", que trae sus propias tabulaciones.
        parrafo.style = "Normal"
        parrafo.alignment = ALINEACIONES_HTML["left"]
        formato = parrafo.paragraph_format
        formato.space_before = 0
        formato.space_after = 0
        formato.line_spacing = 1
        for eje_mm in (cls.EJE_PROGRAMA_MM, cls.EJE_MINISTERIO_MM):
            formato.tab_stops.add_tab_stop(Mm(eje_mm), TABULACION_CENTRADA)

    @classmethod
    def _agregar_texto(cls, parrafo, texto, tamanio_pt):
        run = parrafo.add_run(texto)
        run.font.name = cls.FUENTE
        run.font.size = Pt(tamanio_pt)
        run.font.color.rgb = cls.COLOR_TEXTO

    @classmethod
    def _aplicar_linea_inferior(cls, parrafo):
        propiedades = parrafo._p.get_or_add_pPr()  # pylint: disable=protected-access
        bordes = OxmlElement("w:pBdr")
        borde = OxmlElement("w:bottom")
        borde.set(qn("w:val"), "single")
        borde.set(qn("w:sz"), "12")
        borde.set(qn("w:space"), "8")
        borde.set(qn("w:color"), cls.COLOR_LINEA)
        bordes.append(borde)
        propiedades.insert_element_before(bordes, *SUCESORES_BORDES_PARRAFO)

    @classmethod
    def _ruta_escudo(cls):
        return os.path.join(
            apps.get_app_config("admisiones").path,
            "templates",
            "admisiones",
            "docx",
            cls.ARCHIVO_ESCUDO,
        )
