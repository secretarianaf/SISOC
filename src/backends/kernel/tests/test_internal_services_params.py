"""Parámetros GET equivalentes en servicios internos locales y remotos."""

from unittest.mock import MagicMock, patch

from core.internal_services import RespuestaInterna, pedir_json_interno


def test_parametros_get_se_entregan_a_handler_local():
    request = object()
    handler = MagicMock(return_value=RespuestaInterna(200, {"centros": []}))
    with (
        patch("core.internal_services.backend_de_app", return_value=None),
        patch.dict(
            "core.internal_services._local_handlers", {"/interno/prueba/": handler}
        ),
    ):
        respuesta = pedir_json_interno(
            request, "cdi", "/interno/prueba/", params={"q": "Salta"}
        )
    assert respuesta.status == 200
    handler.assert_called_once_with(request, {"q": "Salta"})


def test_parametros_get_se_envian_remotamente_y_su_omision_no_cambia_el_contrato():
    response = MagicMock(status_code=200)
    response.json.return_value = {"centros": []}
    context = MagicMock()
    context.__enter__.return_value = response
    with (
        patch(
            "core.internal_services.backend_de_app",
            return_value={"origin": "http://example.invalid"},
        ),
        patch("core.internal_services.outbound_headers", return_value={}),
        patch(
            "core.internal_services.requests.request", return_value=context
        ) as enviar,
    ):
        pedir_json_interno(object(), "cdi", "/interno/prueba/", params={"q": "Salta"})
        assert enviar.call_args.kwargs["params"] == {"q": "Salta"}
        pedir_json_interno(object(), "cdi", "/interno/prueba/")
        assert "params" not in enviar.call_args.kwargs
