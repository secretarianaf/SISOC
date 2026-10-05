"""Validaciones de entrada de la API territorial: 400 ``{"detail"}`` en vez de 500.

La app arma el JSON en el dispositivo y GESTIONAR manda multipart, así que un
valor puede llegar con el tipo equivocado (un número donde va texto, texto donde
va un entero, cadenas vacías) o más largo que la columna. Estas funciones
normalizan lo aceptable y levantan ``ParseError`` (que DRF responde como 400
``{"detail": "..."}``) con lo demás, antes de tocar la base: en MySQL estricto
un largo excedido o un entero fuera de rango terminaban en 500.
"""

from PIL import Image
from rest_framework.exceptions import ParseError

MAX_CANTIDAD_PRESTACION = 100_000
MAX_FILAS_PRESTACIONES = 100
MAX_LARGO_TEXTO_CORTO = 255
MAX_LARGO_FIRMA = 600
MAX_LARGO_OBSERVACIONES = 10_000
# Formato real detectado por Pillow -> extensión con la que se guarda la firma.
FORMATOS_IMAGEN = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif"}


def leer_texto(data, campo, max_length=None):
    """Texto recortado; ``None`` si no vino o vino vacío; 400 si no es texto."""
    valor = data.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ParseError(f"'{campo}' debe ser texto.")
    valor = valor.strip()
    if max_length is not None and len(valor) > max_length:
        raise ParseError(f"'{campo}' supera los {max_length} caracteres.")
    return valor or None


def leer_entero_no_negativo(valor, campo, maximo=MAX_CANTIDAD_PRESTACION):
    """Entero entre 0 y ``maximo``; acepta texto numérico; ``None`` si vacío."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, bool):
        raise ParseError(f"'{campo}' debe ser un entero.")
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, float) and valor.is_integer():
        numero = int(valor)
    elif isinstance(valor, str):
        try:
            numero = int(valor.strip())
        except ValueError as exc:
            raise ParseError(f"'{campo}' debe ser un entero.") from exc
    else:
        raise ParseError(f"'{campo}' debe ser un entero.")
    if numero < 0 or numero > maximo:
        raise ParseError(f"'{campo}' debe estar entre 0 y {maximo}.")
    return numero


def validar_prestaciones_acta(prestaciones):
    """Filas de la tabla día × tipo del acta (§18.5), ya normalizadas.

    Cada fila queda con ``dias_prestacion`` y ``tipo_prestacion`` como texto de
    hasta 255 caracteres (o ``None``) y las cantidades como enteros 0..100000
    (o ``None``). Cualquier otra cosa es 400, sin crear nada.
    """
    if not isinstance(prestaciones, list) or any(
        not isinstance(fila, dict) for fila in prestaciones
    ):
        raise ParseError("'prestaciones' debe ser una lista de objetos.")
    if len(prestaciones) > MAX_FILAS_PRESTACIONES:
        raise ParseError(f"'prestaciones' admite hasta {MAX_FILAS_PRESTACIONES} filas.")
    return [
        {
            "dias_prestacion": leer_texto(
                fila, "dias_prestacion", MAX_LARGO_TEXTO_CORTO
            ),
            "tipo_prestacion": leer_texto(
                fila, "tipo_prestacion", MAX_LARGO_TEXTO_CORTO
            ),
            "cantidad_actual": leer_entero_no_negativo(
                fila.get("cantidad_actual"), "cantidad_actual"
            ),
            "cantidad_espera": leer_entero_no_negativo(
                fila.get("cantidad_espera"), "cantidad_espera"
            ),
        }
        for fila in prestaciones
    ]


def extension_de_imagen(archivo):
    """Extensión según el contenido real del archivo; ``None`` si no es imagen.

    El ``Content-Type`` lo declara el cliente y no alcanza: un SVG (que puede
    llevar script) o un texto cualquiera con ``image/png`` pasaban. Pillow abre
    el archivo y dice qué es; solo se aceptan los formatos de ``FORMATOS_IMAGEN``.
    """
    try:
        with Image.open(archivo) as imagen:
            imagen.verify()
            formato = imagen.format
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None
    finally:
        archivo.seek(0)
    return FORMATOS_IMAGEN.get(formato)
