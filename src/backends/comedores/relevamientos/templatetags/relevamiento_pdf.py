from django import template

from relevamientos.pdf_service import tipo_imagen_pdf as _tipo_imagen_pdf

register = template.Library()


@register.filter
def tipo_imagen_pdf(url):
    """``local``, ``externa`` o ``vacia`` (ver ``relevamientos.pdf_service``)."""
    return _tipo_imagen_pdf(url)
