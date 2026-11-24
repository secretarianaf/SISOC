"""Probe: guards precede JSON/static for every canonical URL; proxy hygiene."""

import io

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponse

from core.models import Provincia
from celiaquia.models import EstadoExpediente, Expediente
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario

pytestmark = pytest.mark.django_db
GUARDED = [
    "/celiaquia/expedientes/",
    "/celiaquia/expedientes/nuevo/",
    "/celiaquia/expedientes/{e}/",
    "/celiaquia/expedientes/{e}/editar/",
    "/celiaquia/cupos/",
    "/celiaquia/cupos/provincia/{p}/",
    "/celiaquia/tablero/",
]


def _setup(settings, monkeypatch):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    calls = []

    def boom(request, module):
        calls.append(request.path)
        return HttpResponse(b'<meta name="sisoc-celiaquia-x"', content_type="text/html")

    monkeypatch.setattr("core.v2_frontend.frontend_v2", boom)
    owner = get_user_model().objects.create_user("owner_x", password="p")
    state, _ = EstadoExpediente.objects.get_or_create(nombre="CREADO")
    exp = Expediente.objects.create(
        usuario_provincia=owner, estado=state, numero_expediente="EX"
    )
    prov = Provincia.objects.create(nombre="P1")
    return calls, exp, prov


@pytest.mark.parametrize("accept", ["application/json", "text/html"])
@pytest.mark.parametrize("method", ["get", "head", "post"])
def test_no_permission_and_anonymous(client, settings, monkeypatch, accept, method):
    calls, exp, prov = _setup(settings, monkeypatch)
    before = Expediente.objects.count()
    for tpl in GUARDED:
        url = tpl.format(e=exp.pk, p=prov.pk)
        client.logout()
        r = getattr(client, method)(url, HTTP_ACCEPT=accept, REMOTE_ADDR="203.0.113.15")
        assert r.status_code in (302, 403), (url, r.status_code)
        assert b'"version"' not in r.content
        client.force_login(
            _usuario(
                f"np_{method}_{accept[:4]}_{abs(hash(url))}", "view_reporte_provincias"
            )
        )
        r = getattr(client, method)(url, HTTP_ACCEPT=accept, REMOTE_ADDR="203.0.113.15")
        assert r.status_code == 403, (url, r.status_code)
        assert b'"version"' not in r.content
    assert calls == []
    assert Expediente.objects.count() == before


def test_out_of_scope_detail_and_edit(client, settings, monkeypatch):
    calls, exp, prov = _setup(settings, monkeypatch)
    other = _usuario("other_prov", "view_expediente")
    client.force_login(other)
    r = client.get(f"/celiaquia/expedientes/{exp.pk}/", HTTP_ACCEPT="application/json")
    assert r.status_code == 404
    # Native HTML also 404 for the same user
    settings.REACT_VERTICALES_ACTIVAS = ()
    assert client.get(f"/celiaquia/expedientes/{exp.pk}/").status_code == 404
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    rows = client.get("/celiaquia/expedientes/", HTTP_ACCEPT="application/json").json()[
        "rows"
    ]
    assert [row["id"] for row in rows] == []


class _Src(io.BytesIO):
    status = 200
    headers = {"Content-Type": "text/html"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_proxy_outbound_has_no_query_cookie_auth(client, settings, monkeypatch):
    settings.REACT_VERTICALES_ACTIVAS = ("celiaquia",)
    settings.FRONTEND_V2_UPSTREAMS = {
        **settings.FRONTEND_V2_UPSTREAMS,
        "celiaquia": "http://static.invalid",
    }
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.full_url, dict(req.header_items()), req.get_method()))
        return _Src(b'<html><meta name="sisoc-celiaquia-cupos" content="v1"></html>')

    monkeypatch.setattr("core.v2_frontend.urlopen", fake_urlopen)
    client.force_login(_usuario("prox", "view_cupo_dashboard"))
    r = client.get(
        "/celiaquia/cupos/?provincia=7&secret=1", HTTP_AUTHORIZATION="Bearer zzz"
    )
    assert r.status_code == 200 and b"sisoc-celiaquia-cupos" in r.content
    assert r["Cache-Control"] == "private, no-store"
    assert "Accept" in r["Vary"] and "Cookie" in r["Vary"]
    h = client.head(
        "/celiaquia/cupos/?a=1",
        HTTP_AUTHORIZATION="Bearer zzz",
        REMOTE_ADDR="203.0.113.15",
    )
    assert h.status_code == 200 and h.content == b""
    for url, headers, method in seen:
        assert "?" not in url, url
        assert method == "GET"
        low = {k.lower() for k in headers}
        assert "cookie" not in low and "authorization" not in low, headers
    assert len(seen) == 2
