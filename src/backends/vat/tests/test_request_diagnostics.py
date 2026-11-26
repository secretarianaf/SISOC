"""Cobertura del diagnóstico VAT sin datos de solicitudes en sus registros."""

import logging
import os
import re

import pytest
from django.http import HttpResponse
from django.test import override_settings
from django.urls import path, resolve

from vat_runtime import gunicorn_conf, request_diagnostics

RUTA = "prueba/<str:identificador>/"
MIDDLEWARE = "vat_runtime.request_diagnostics.DiagnosticoPeticionMiddleware"


def responder(_request, **_kwargs):
    return HttpResponse(status=204)


urlpatterns = [path(RUTA, responder)]


def handler404(_request, exception):  # pylint: disable=unused-argument
    return HttpResponse(status=404)


@override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[MIDDLEWARE])
def test_registra_patron_y_estado_sin_datos_de_la_peticion(client, caplog):
    with caplog.at_level(logging.INFO, logger=request_diagnostics.__name__):
        respuesta = client.post(
            "/prueba/id-sensible/?query=valor-sensible",
            data="body-sensible",
            content_type="text/plain",
            HTTP_AUTHORIZATION="Bearer token-sensible",
            HTTP_COOKIE="sesion=cookie-sensible",
            HTTP_X_REQUEST_ID="identificador-enviado",
        )

    assert respuesta.status_code == 204
    assert re.fullmatch(
        rf"vat_request id=[a-f0-9]{{32}} metodo=POST ruta={re.escape(RUTA)} "
        rf"estado=204 duracion_ms=\d+\.\d pid={os.getpid()}",
        caplog.records[-1].getMessage(),
    )
    assert request_diagnostics.peticion_activa.get() is None


@override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[MIDDLEWARE])
def test_ruta_desconocida_y_metodo_arbitrario_no_se_registran(client, caplog):
    with caplog.at_level(logging.INFO, logger=request_diagnostics.__name__):
        respuesta = client.generic("METODOSECRETO", "/ruta-personal/")

    assert respuesta.status_code == 404
    (mensaje,) = [
        record.getMessage()
        for record in caplog.records
        if record.name == request_diagnostics.__name__
    ]
    assert "metodo=OTRO ruta=sin_resolver estado=404" in mensaje
    assert "ruta-personal" not in mensaje
    assert "METODOSECRETO" not in mensaje


@pytest.mark.parametrize("con_peticion", [False, True])
@override_settings(ROOT_URLCONF=__name__)
def test_worker_abort_registra_contexto_seguro_y_traza(
    rf, mocker, caplog, con_peticion
):
    worker = mocker.Mock(pid=os.getpid())
    traza = mocker.patch.object(gunicorn_conf.faulthandler, "dump_traceback")
    if con_peticion:
        request = rf.get("/prueba/valor-privado/")
        request.resolver_match = resolve(request.path)

        def responder_durante_abort(peticion):
            middleware.process_view(peticion, None, (), {})
            gunicorn_conf.worker_abort(worker)
            return HttpResponse(status=204)

        middleware = request_diagnostics.DiagnosticoPeticionMiddleware(
            responder_durante_abort
        )
        with caplog.at_level(logging.INFO, logger=request_diagnostics.__name__):
            assert middleware(request).status_code == 204

        formato, pid, correlacion, metodo, ruta, duracion = (
            worker.log.warning.call_args.args
        )
        assert pid == worker.pid
        assert f"id={correlacion}" in caplog.records[-1].getMessage()
        assert (metodo, ruta) == ("GET", RUTA)
        assert duracion >= 0
        assert formato.startswith("vat_worker_abort")
    else:
        gunicorn_conf.worker_abort(worker)
        worker.log.warning.assert_called_once_with(
            "vat_worker_abort pid=%d id=sin_peticion", worker.pid
        )

    traza.assert_called_once_with(all_threads=False)


def test_limpia_contexto_si_se_interrumpe_la_peticion(rf):
    def interrumpir(_request):
        raise SystemExit

    middleware = request_diagnostics.DiagnosticoPeticionMiddleware(interrumpir)

    with pytest.raises(SystemExit):
        middleware(rf.get("/"))

    assert request_diagnostics.peticion_activa.get() is None


def test_logger_omite_uri_del_error_de_gunicorn_tras_un_aborto(mocker):
    logger = object.__new__(gunicorn_conf.LoggerVAT)
    error = mocker.patch.object(logger, "error")

    try:
        raise SystemExit(1)
    except SystemExit:
        logger.exception("Error handling request %s", "/identificador/?token=secreto")

    error.assert_called_once_with("vat_worker_abort fin de la solicitud")


def test_logger_conserva_los_otros_errores_de_gunicorn(mocker):
    logger = object.__new__(gunicorn_conf.LoggerVAT)
    fallback = mocker.patch.object(gunicorn_conf.Logger, "exception")

    logger.exception("Error de servidor")

    fallback.assert_called_once_with("Error de servidor")
