"""Errores de negocio que la API traduce a HTTP (ver ``inspecciones.api_views``)."""


class ErrorInspecciones(Exception):
    """Base: lleva el ``detail`` que muestra la app y datos extra opcionales."""

    status_code = 400

    def __init__(self, detail, **extra):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra

    def cuerpo(self):
        return {"detail": self.detail, **self.extra}


class NoEncontrado(ErrorInspecciones):
    """Inexistente o ajeno: responde 404 en los dos casos (no revela que existe)."""

    status_code = 404

    def __init__(self, detail="No encontrado.", **extra):
        super().__init__(detail, **extra)


class Conflicto(ErrorInspecciones):
    """El recurso está en un estado que no admite la operación (409)."""

    status_code = 409


class DatosInvalidos(ErrorInspecciones):
    """Validación del formulario o del pedido (400). ``errores``: campo → mensaje."""

    status_code = 400


class NoProcesable(ErrorInspecciones):
    """Archivo inválido o límite superado (422)."""

    status_code = 422
