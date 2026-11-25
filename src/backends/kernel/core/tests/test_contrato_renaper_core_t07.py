"""T07.01: contrato de ``/api/renaper/consultar/``; ``HasAPIKey`` no equivale a una sesión web.

La consulta externa se reemplaza siempre: nunca se llama a RENAPER ni se usa una credencial real.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = "/api/renaper/consultar/"
CUERPO = {"dni": "12345678", "sexo": "m"}


def _post(client, cuerpo=None, key=None):
    extra = {"HTTP_AUTHORIZATION": f"Api-Key {key}"} if key else {}
    return client.post(
        URL, cuerpo if cuerpo is not None else CUERPO, format="json", **extra
    )


def test_una_sesion_web_sin_clave_no_alcanza(api_key):
    del api_key
    user = User.objects.create_superuser(username="t07_super", password="x")
    cliente = APIClient()
    cliente.force_login(user)
    with patch("core.api_views.consultar_datos_renaper") as consulta:
        respuesta = _post(cliente)
    assert respuesta.status_code in (401, 403)
    consulta.assert_not_called()


def test_clave_invalida_o_mal_formada_se_rechaza(api_key):
    del api_key
    for key in ("clave-inventada", ""):
        with patch("core.api_views.consultar_datos_renaper") as consulta:
            respuesta = _post(APIClient(), key=key or None)
        assert respuesta.status_code == 401
        consulta.assert_not_called()


def test_la_clave_no_abre_ninguna_ruta_de_sesion_web(api_key):
    cliente = Client()
    for url in (
        "/api/web/core/programas/",
        "/api/web/core/novedades/",
        "/api/web/core/papelera/",
        "/api/web/session/",
    ):
        assert (
            cliente.get(url, HTTP_AUTHORIZATION=f"Api-Key {api_key}").status_code == 401
        )


def test_clave_valida_devuelve_solo_exito_y_datos(api_client):
    respuesta_renaper = {
        "success": True,
        "data": {"nombre": "Ana"},
        "interno": "no se reenvia",
    }
    with patch(
        "core.api_views.consultar_datos_renaper", return_value=respuesta_renaper
    ) as consulta:
        respuesta = _post(api_client)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True, "data": {"nombre": "Ana"}}
    consulta.assert_called_once_with("12345678", "M")


def test_error_de_renaper_responde_200_con_el_error(api_client):
    with patch(
        "core.api_views.consultar_datos_renaper",
        return_value={"success": False, "error": "No encontrado"},
    ):
        respuesta = _post(api_client)
    assert (respuesta.status_code, respuesta.json()) == (
        200,
        {"success": False, "error": "No encontrado"},
    )
    with patch(
        "core.api_views.consultar_datos_renaper", return_value={"success": False}
    ):
        assert _post(api_client).json() == {
            "success": False,
            "error": "Error desconocido",
        }


def test_entrada_invalida_es_400_sin_consultar(api_client):
    for cuerpo in (
        {},
        {"dni": "1"},
        {"dni": " ", "sexo": "M"},
        {"dni": "1", "sexo": "Z"},
    ):
        with patch("core.api_views.consultar_datos_renaper") as consulta:
            respuesta = _post(api_client, cuerpo)
        datos = respuesta.json()
        assert respuesta.status_code == 400
        assert datos["success"] is False and datos["error"] == "Datos inválidos"
        assert "details" in datos
        consulta.assert_not_called()


def test_falla_inesperada_no_filtra_el_detalle_ni_la_clave(api_client, api_key):
    with patch(
        "core.api_views.consultar_datos_renaper",
        side_effect=RuntimeError("token-secreto-interno https://renaper.interno"),
    ):
        respuesta = _post(api_client)
    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "success": False,
        "error": "No se pudo consultar RENAPER en este momento.",
    }
    cuerpo = respuesta.content.decode()
    assert "token-secreto-interno" not in cuerpo and api_key not in cuerpo


def test_solo_admite_post(api_client, api_key):
    assert api_client.get(URL, HTTP_AUTHORIZATION=f"Api-Key {api_key}").status_code in (
        404,
        405,
    )
