from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory, override_settings

from core.v2_frontend import frontend_v2


@override_settings(FRONTEND_V2_UPSTREAMS={"vpsl": "http://front_vpsl:8080"})
def test_v2_exige_sesion_y_destino_allowlist():
    request = RequestFactory().get("/v2/vpsl/jornadas/1/")
    request.user = AnonymousUser()
    response = frontend_v2(request, "vpsl", "jornadas/1/")
    assert response.status_code == 302
    assert "/login/?next=/v2/vpsl/jornadas/1/" in response["Location"]

    request.user = SimpleNamespace(is_authenticated=True)
    with pytest.raises(Http404):
        frontend_v2(request, "desconocido", "")


@override_settings(FRONTEND_V2_UPSTREAMS={"vpsl": "http://front_vpsl:8080"})
def test_v2_no_reenvia_credenciales_y_cachea_asset_con_hash():
    request = RequestFactory().get(
        "/v2/vpsl/assets/index-ABC123.js",
        HTTP_COOKIE="sessionid=secreto",
        HTTP_AUTHORIZATION="Bearer secreto",
    )
    request.user = SimpleNamespace(is_authenticated=True)
    upstream = SimpleNamespace(
        status=200,
        headers={"Content-Type": "application/javascript"},
        read=lambda: b"export {};",
        __enter__=lambda self: self,
        __exit__=lambda self, *_args: None,
    )
    # SimpleNamespace special methods are resolved on the type, so use a mock.
    from unittest.mock import MagicMock

    source = MagicMock()
    source.__enter__.return_value = upstream
    with patch("core.v2_frontend.urlopen", return_value=source) as fetch:
        response = frontend_v2(request, "vpsl", "assets/index-ABC123.js")

    outbound = fetch.call_args.args[0]
    assert outbound.full_url == "http://front_vpsl:8080/v2/vpsl/assets/index-ABC123.js"
    assert outbound.headers.get("Cookie") is None
    assert outbound.headers.get("Authorization") is None
    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=31536000, immutable"


@pytest.mark.parametrize(
    "debug,path,allows_hmr",
    [
        (True, "/v2/vpsl/", True),
        (True, "/ver-para-ser-libre/", False),
        (False, "/v2/vpsl/", False),
    ],
)
def test_csp_hmr_solo_en_v2_desarrollo(settings, debug, path, allows_hmr):
    from django.http import HttpResponse
    from config.middlewares.csp import ContentSecurityPolicyMiddleware

    settings.DEBUG = debug
    settings.ENABLE_CSP = True
    settings.CSP_ALLOW_UNSAFE_INLINE_SCRIPTS = False
    settings.CSP_REPORT_ONLY = False
    settings.FRONTEND_V2_HMR_ORIGINS = ["http://localhost:5173", "ws://localhost:5173"]
    response = ContentSecurityPolicyMiddleware(lambda _request: HttpResponse())(
        RequestFactory().get(path)
    )
    policy = response["Content-Security-Policy"]
    assert ("ws://localhost:5173" in policy) is allows_hmr
    script_policy = policy.split("script-src ")[1].split(";")[0]
    assert "'unsafe-inline'" not in script_policy
