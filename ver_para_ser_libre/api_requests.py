"""Conversión de transporte DRF a los ModelForms Django compartidos."""

from collections.abc import Mapping

from django.http import QueryDict
from rest_framework.exceptions import ParseError


def django_request(request):
    """Preserva sesión/CSRF/archivos; traduce JSON sin duplicar validaciones.

    DRF no expone públicamente el HttpRequest que requieren las vistas existentes.
    El acceso se limita a esta frontera y se cubre con pruebas de ambos formatos.
    """
    raw = request._request  # pylint: disable=protected-access
    if request.method == "POST" and request.content_type == "application/json":
        if not isinstance(request.data, Mapping):
            raise ParseError("El cuerpo JSON debe ser un objeto.")
        data = QueryDict(mutable=True)
        for key, value in request.data.items():
            values = value if isinstance(value, list) else [value]
            if any(isinstance(entry, (dict, list)) for entry in values):
                raise ParseError(f"El campo {key} no admite objetos anidados.")
            data.setlist(
                key,
                [
                    (
                        ""
                        if entry is None
                        else (
                            str(entry).lower()
                            if isinstance(entry, bool)
                            else str(entry)
                        )
                    )
                    for entry in values
                ],
            )
        raw.POST = data
    return raw
