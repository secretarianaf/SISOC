"""Diagnóstico del worker VAT cuando Gunicorn le envía SIGABRT."""

import faulthandler
import sys

from gunicorn.glogging import Logger


class LoggerVAT(Logger):
    """Evita el URI crudo al registrar el final de un worker abortado."""

    def exception(self, msg, *args, **kwargs):
        # El worker sync captura SystemExit tras worker_abort. Su mensaje
        # estándar incluye req.uri, con valores de ruta y cadena de consulta.
        if msg == "Error handling request %s" and sys.exc_info()[0] is SystemExit:
            return self.error("vat_worker_abort fin de la solicitud")
        return super().exception(msg, *args, **kwargs)


# Gunicorn busca esta opción con su nombre en minúsculas.
logger_class = LoggerVAT  # pylint: disable=invalid-name


def worker_abort(worker):
    # Gunicorn carga este archivo antes de que config inicialice el sys.path.
    from vat_runtime.request_diagnostics import peticion_activa

    peticion = peticion_activa.get()
    if peticion is None:
        worker.log.warning("vat_worker_abort pid=%d id=sin_peticion", worker.pid)
    else:
        worker.log.warning(
            "vat_worker_abort pid=%d id=%s metodo=%s ruta=%s duracion_ms=%.1f",
            worker.pid,
            peticion.correlacion,
            peticion.metodo,
            peticion.ruta,
            peticion.duracion_ms,
        )
    # Solo nombres de funciones, archivos y números de línea del hilo actual.
    faulthandler.dump_traceback(all_threads=False)
