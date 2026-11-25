import pytest
from django.http import Http404, HttpResponse
from django.urls import resolve, reverse

from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
PATH = "/reporter-provincias/"
SHELL = b'<meta name="sisoc-celiaquia-report" content="v1"><div id="root"></div>'


def test_exact_report_uses_static_shell_after_native_permission(
    client, settings, monkeypatch
):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    settings.FRONTEND_V2_UPSTREAMS = {"celiaquia": "http://celiaquia-static.invalid"}
    calls = []

    class StaticResponse:
        status = 200
        headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def read(self):
            return SHELL

    def open_static(request, timeout):
        calls.append(request)
        return StaticResponse()

    monkeypatch.setattr("core.v2_frontend.urlopen", open_static)
    assert reverse("reporter_provincias") == PATH
    assert (
        resolve(PATH, urlconf="celiaquia_runtime.urls").url_name
        == "reporter_provincias"
    )
    assert client.get(PATH).status_code == 403
    client.force_login(_usuario("canon_sin_permiso", "view_expediente"))
    assert client.get(PATH).status_code == 403
    assert calls == []

    client.force_login(_usuario("canon_reporte", "view_reporte_provincias"))
    response = client.get(
        PATH,
        {"documento_persona": "000", "page": 2},
        HTTP_AUTHORIZATION="Bearer synthetic",
    )
    assert response.status_code == 200
    assert response.content == SHELL
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]
    assert len(calls) == 1
    outbound = calls[0]
    assert outbound.full_url == "http://celiaquia-static.invalid/v2/celiaquia/"
    assert outbound.method == "GET"
    assert "authorization" not in {name.lower() for name, _ in outbound.header_items()}
    assert "cookie" not in {name.lower() for name, _ in outbound.header_items()}

    head = client.head(PATH, REMOTE_ADDR="203.0.113.15")
    assert head.status_code == 200
    assert head.content == b""
    assert int(head["Content-Length"]) == len(SHELL)
    assert head["Cache-Control"] == response["Cache-Control"]
    for method in (client.post, client.put):
        assert method(PATH).status_code == 405
    assert client.get(PATH + "otro/").status_code == 404
    assert len(calls) == 2
    assert calls[1].full_url == outbound.full_url
    assert calls[1].method == "GET"


@pytest.mark.parametrize("failure", ["old", "unavailable", "missing", "non_html"])
def test_old_or_invalid_shell_uses_native_report(
    client, settings, monkeypatch, failure
):
    client.force_login(_usuario("canon_fallback", "view_reporte_provincias"))
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)

    def upstream(request, module):
        if failure == "missing":
            raise Http404
        if failure == "unavailable":
            return HttpResponse(status=503)
        if failure == "non_html":
            return HttpResponse(SHELL, content_type="application/octet-stream")
        return HttpResponse(b"<div>old</div>")

    monkeypatch.setattr("core.v2_frontend.frontend_v2", upstream)

    response = client.get(PATH, {"revision_tecnico": "APROBADO", "page": 2})
    assert response.status_code == 200
    assert "celiaquia/reporter_provincias.html" in response.template_name
    assert response.context["current_querystring"] == "revision_tecnico=APROBADO"


def test_disabled_report_keeps_native_view_without_calling_static(
    client, settings, monkeypatch
):
    client.force_login(_usuario("canon_apagado", "view_reporte_provincias"))
    settings.REACT_VERTICALES_ACTIVAS = ()

    def forbidden(*args, **kwargs):
        pytest.fail("disabled canonical report reached the static upstream")

    monkeypatch.setattr("core.v2_frontend.frontend_v2", forbidden)
    response = client.get(PATH)
    assert response.status_code == 200
    assert "celiaquia/reporter_provincias.html" in response.template_name
