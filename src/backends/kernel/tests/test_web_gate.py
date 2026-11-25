"""G1 v1 web gate (``core.web_gate`` and ``/api/web/<vertical>/`` in the proxy).

The runtime side goes through the real middleware stack with a test-only
``/api/web/pas/probe/`` view; the core side forwards to a real HTTP server
that records what crossed the wire. Every rejection asserts that the probe's
business code did not run.
"""

import json
import threading
import time
import types
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings
from django.urls import Resolver404, re_path, resolve
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from config.backends import load_backends_registry
from core import backend_proxy, web_gate
from core.backend_proxy import backend_proxy_urlpatterns, outbound_headers

TARGET = "/api/web/pas/probe/x?b=2&a=1"
OLD_KEY = "synthetic-old-secret-key-for-g1-tests-0123456789"
NEW_KEY = "synthetic-new-secret-key-for-g1-tests-9876543210"

BUSINESS = []


@dataclass(frozen=True)
class _Access:
    state: str
    required_action_url: str | None = None


READY = _Access("ready")


def _policy(state):
    return lambda request: state


class _ProbeView(APIView):
    """Test-only owner view: records each business execution."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [web_gate.WebGatePermission]
    renderer_classes = [JSONRenderer]

    def _business(self, request):
        BUSINESS.append(
            {
                "method": request.method,
                "header_visible": web_gate.META_KEY in request.META,
            }
        )
        return Response({"user": request.user.pk, "method": request.method})

    def get(self, request, rest=""):
        del rest
        return self._business(request)

    def post(self, request, rest=""):
        del rest
        return self._business(request)


def _urlconf(patterns):
    module = types.ModuleType("web_gate_test_urlconf")
    module.urlpatterns = patterns
    return module


RUNTIME_URLS = _urlconf(
    [re_path(r"^api/web/pas/probe/(?P<rest>.*)$", _ProbeView.as_view())]
)


@pytest.fixture(autouse=True)
def _reset_business():
    BUSINESS.clear()
    yield
    BUSINESS.clear()


@pytest.fixture(name="user")
def user_fixture(django_user_model):
    return django_user_model.objects.create_user("g1user", password="x")


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="pas",
        ROOT_URLCONF=RUNTIME_URLS,
        SISOC_WEB_ACCESS_POLICY=_policy(READY),
        INTERNAL_IPS=[],
    ):
        yield


def _login(user, client=None):
    client = client or Client()
    client.force_login(user)
    return client, client.cookies[settings.SESSION_COOKIE_NAME].value


def _token(user, session_key, *, method="GET", target=TARGET, now=None, **override):
    fields = {
        "audience": "pas",
        "user_pk": user.pk,
        "session_key": session_key,
        "method": method,
        "target": target,
        "now": now,
    }
    fields.update(override)
    return web_gate.sign(**fields)


def _runtime_get(client, token, *, target=TARGET, method="get", **extra):
    if token is not None:
        extra["HTTP_X_SISOC_WEB_GATE"] = token
    return getattr(client, method)(target, RAW_URI=target, **extra)


# --- Runtime verifier -------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_accepts_valid_signed_request_and_hides_the_header(user):
    client, key = _login(user)

    response = _runtime_get(client, _token(user, key))

    assert response.status_code == 200
    assert response.json() == {"user": user.pk, "method": "GET"}
    assert BUSINESS == [{"method": "GET", "header_visible": False}]
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]


def _forged_signature(token):
    value, timestamp, signature = token.rsplit(":", 2)
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    return f"{value}:{timestamp}:{flipped}"


def _with_secret(user, key, secret):
    with override_settings(SECRET_KEY=secret, SECRET_KEY_FALLBACKS=[]):
        return _token(user, key)


def _raw_payload(payload, iat):
    signer = web_gate._Signer(iat)  # pylint: disable=protected-access
    return signer.sign_object(payload, compress=False)


def _valid_payload(user, key, iat):
    return {
        "v": 1,
        "aud": "pas",
        "sub": str(user.pk),
        "session_binding": web_gate.session_binding(key),
        "method": "GET",
        "target": TARGET,
        "iat": iat,
    }


TAMPERS = {
    "missing": lambda user, key, other: None,
    "audience": lambda user, key, other: _token(user, key, audience="vat"),
    "subject": lambda user, key, other: _token(user, key, user_pk=other.pk),
    "session": lambda user, key, other: _token(user, "other-key"),
    "method": lambda user, key, other: _token(user, key, method="POST"),
    "path": lambda user, key, other: _token(
        user, key, target="/api/web/pas/probe/y?b=2&a=1"
    ),
    "query": lambda user, key, other: _token(
        user, key, target="/api/web/pas/probe/x?b=3&a=1"
    ),
    "query_order": lambda user, key, other: _token(
        user, key, target="/api/web/pas/probe/x?a=1&b=2"
    ),
    "expired": lambda user, key, other: _token(user, key, now=time.time() - 62),
    "future": lambda user, key, other: _token(user, key, now=time.time() + 5),
    "signature": lambda user, key, other: _forged_signature(_token(user, key)),
    "other_secret": lambda user, key, other: _with_secret(user, key, "unrelated-key"),
    "duplicated_header": lambda user, key, other: ",".join([_token(user, key)] * 2),
    "oversize": lambda user, key, other: "x" * (web_gate.MAX_HEADER_BYTES + 1),
    "version": lambda user, key, other: _raw_payload(
        {**_valid_payload(user, key, int(time.time())), "v": 2}, int(time.time())
    ),
    "extra_field": lambda user, key, other: _raw_payload(
        {**_valid_payload(user, key, int(time.time())), "perms": ["all"]},
        int(time.time()),
    ),
    "missing_field": lambda user, key, other: _raw_payload(
        {
            k: v
            for k, v in _valid_payload(user, key, int(time.time())).items()
            if k != "session_binding"
        },
        int(time.time()),
    ),
    "iat_not_timestamp": lambda user, key, other: _raw_payload(
        _valid_payload(user, key, int(time.time()) - 1), int(time.time())
    ),
    "iat_type": lambda user, key, other: _raw_payload(
        {**_valid_payload(user, key, 0), "iat": str(int(time.time()))},
        int(time.time()),
    ),
}


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
@pytest.mark.parametrize("case", sorted(TAMPERS))
def test_runtime_rejects_every_tampered_attestation_without_business(
    case, user, django_user_model
):
    other = django_user_model.objects.create_user("g1other", password="x")
    client, key = _login(user)

    response = _runtime_get(client, TAMPERS[case](user, key, other))

    assert response.status_code == 403
    assert response.json() == {"detail": "Solicitud no autorizada."}
    assert response["Cache-Control"] == "private, no-store"
    assert BUSINESS == []


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
@pytest.mark.parametrize(
    ("age", "status"), [(0, 200), (59, 200), (60, 200), (61, 403), (-2, 200), (-3, 403)]
)
def test_runtime_window_is_sixty_seconds_and_two_in_the_future(
    age, status, user, monkeypatch
):
    client, key = _login(user)
    issued = 1_800_000_000
    token = _token(user, key, now=issued)
    monkeypatch.setattr(web_gate, "_now", lambda: issued + age)

    response = _runtime_get(client, token)

    assert response.status_code == status
    assert len(BUSINESS) == (1 if status == 200 else 0)


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_without_session_answers_401_json(user):
    client, key = _login(user)
    token = _token(user, key)
    client.logout()

    response = _runtime_get(client, token)

    assert response.status_code == 401
    assert response.json() == {"detail": "Inicie sesión para continuar."}
    assert response["WWW-Authenticate"] == "Session"
    assert BUSINESS == []


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_without_raw_uri_is_not_enabled(user):
    client, key = _login(user)

    response = client.get(TARGET, HTTP_X_SISOC_WEB_GATE=_token(user, key))

    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible."}
    assert BUSINESS == []


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_head_needs_a_head_attestation(user):
    client, key = _login(user)

    rejected = _runtime_get(client, _token(user, key), method="head")
    accepted = _runtime_get(client, _token(user, key, method="HEAD"), method="head")

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert BUSINESS == [{"method": "HEAD", "header_visible": False}]


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_options_is_verified_and_runs_no_business(user):
    client, key = _login(user)

    rejected = _runtime_get(client, _token(user, key), method="options")
    accepted = _runtime_get(
        client, _token(user, key, method="OPTIONS"), method="options"
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert BUSINESS == []


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_the_owner_csrf_check(user):
    client, key = _login(user, Client(enforce_csrf_checks=True))
    target = "/api/web/pas/probe/x"

    without_csrf = client.post(
        target,
        {"campo": "valor"},
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_token(user, key, method="POST", target=target),
    )
    client.cookies["csrftoken"] = "a" * 32
    with_csrf = client.post(
        target,
        {"campo": "valor"},
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_token(user, key, method="POST", target=target),
        HTTP_X_CSRFTOKEN="a" * 32,
    )

    assert without_csrf.status_code == 403
    assert "CSRF" in without_csrf.json()["detail"]
    assert with_csrf.status_code == 200
    assert BUSINESS == [{"method": "POST", "header_visible": False}]


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_binding_uses_incoming_cookie_when_auth_cycles_the_key(user):
    """Django cycles the key when the session hash only validates with a fallback."""
    with override_settings(SECRET_KEY=OLD_KEY, SECRET_KEY_FALLBACKS=[]):
        client, key = _login(user)
        old_client, old_key = _login(user)
    with override_settings(SECRET_KEY=NEW_KEY, SECRET_KEY_FALLBACKS=[OLD_KEY]):
        cycled = _runtime_get(client, _token(user, key))
        signed_by_old_core = _runtime_get(
            old_client, _with_secret(user, old_key, OLD_KEY)
        )
    with override_settings(SECRET_KEY=NEW_KEY, SECRET_KEY_FALLBACKS=[]):
        new_client, new_key = _login(user)
        retired = _runtime_get(new_client, _with_secret(user, new_key, OLD_KEY))

    assert cycled.status_code == 200
    assert client.cookies[settings.SESSION_COOKIE_NAME].value != key
    assert signed_by_old_core.status_code == 200
    assert retired.status_code == 403
    assert len(BUSINESS) == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("runtime")
def test_runtime_permission_rejects_a_view_reached_without_the_middleware(user):
    client, key = _login(user)
    other_root = "/elsewhere/probe/x"
    urls = _urlconf([re_path(r"^elsewhere/probe/(?P<rest>.*)$", _ProbeView.as_view())])

    with override_settings(ROOT_URLCONF=urls):
        response = client.get(
            other_root, RAW_URI=other_root, HTTP_X_SISOC_WEB_GATE=_token(user, key)
        )

    assert response.status_code == 403
    assert BUSINESS == []


# --- Monolith ----------------------------------------------------------------


@pytest.fixture(name="monolith")
def monolith_fixture():
    with override_settings(ROOT_URLCONF=RUNTIME_URLS, INTERNAL_IPS=[]):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("monolith")
def test_monolith_evaluates_policy_locally_and_ignores_the_header(user):
    client, key = _login(user)
    pending = _Access("password_change_required", "/password/first-change/")

    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(pending)):
        forged = _runtime_get(client, _token(user, key))
    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(READY)):
        ready = _runtime_get(client, None)

    assert forged.status_code == 403
    assert forged.json() == {
        "detail": "Debe completar el requisito de acceso web.",
        "state": "password_change_required",
        "required_action_url": "/password/first-change/",
    }
    assert ready.status_code == 200
    assert ready["Cache-Control"] == "private, no-store"
    assert BUSINESS == [{"method": "GET", "header_visible": False}]


@pytest.mark.django_db
@pytest.mark.usefixtures("monolith")
def test_monolith_without_session_answers_401(user):
    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(READY)):
        response = Client().get(TARGET)

    assert response.status_code == 401
    assert response.json() == {"detail": "Inicie sesión para continuar."}
    assert response["WWW-Authenticate"] == "Session"
    assert BUSINESS == []


def test_default_policy_is_the_core_resolver():
    assert settings.SISOC_WEB_ACCESS_POLICY == "usuarios.web_session.resolve_web_access"


# --- Core gate in the proxy --------------------------------------------------


class _Runtime(BaseHTTPRequestHandler):
    """Records every request that reaches the "runtime"."""

    hits = []
    delay = 0.0

    def log_message(self, *args):
        del args

    def _record(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        type(self).hits.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
            }
        )
        if type(self).delay:
            time.sleep(type(self).delay)
        body = json.dumps({"ok": True}).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "max-age=600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        except OSError:
            pass

    do_GET = do_POST = do_HEAD = do_OPTIONS = _record


@pytest.fixture(name="upstream")
def upstream_fixture():
    _Runtime.hits = []
    _Runtime.delay = 0.0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(name="core")
def core_fixture(upstream):
    backends = {
        "pas": {
            "url_prefixes": ("api/pas/", "api/web/pas/"),
            "origin": upstream,
        }
    }
    with override_settings(SISOC_BACKENDS=backends):
        urls = _urlconf(backend_proxy_urlpatterns())
    with override_settings(
        SISOC_BACKENDS=backends,
        ROOT_URLCONF=urls,
        SISOC_WEB_ACCESS_POLICY=_policy(READY),
        INTERNAL_IPS=[],
    ):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_core_signs_the_target_it_sends_and_the_runtime_accepts_it(user):
    client, _key = _login(user)

    response = client.get(TARGET, HTTP_X_SISOC_WEB_GATE="forged-by-client")
    sent = _Runtime.hits[0]
    with override_settings(
        SISOC_BACKEND="pas", ROOT_URLCONF=RUNTIME_URLS, SISOC_BACKENDS={}
    ):
        replay = client.get(
            sent["path"],
            RAW_URI=sent["path"],
            HTTP_X_SISOC_WEB_GATE=sent["headers"]["x-sisoc-web-gate"],
        )

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert "Cookie" in response["Vary"]
    assert sent["path"] == TARGET
    assert sent["headers"]["x-sisoc-web-gate"] != "forged-by-client"
    assert replay.status_code == 200
    assert BUSINESS == [{"method": "GET", "header_visible": False}]


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_core_forwards_and_signs_the_session_key_its_auth_rotated(user):
    with override_settings(SECRET_KEY=OLD_KEY, SECRET_KEY_FALLBACKS=[]):
        client, old_key = _login(user)
    with override_settings(SECRET_KEY=NEW_KEY, SECRET_KEY_FALLBACKS=[OLD_KEY]):
        response = client.get(TARGET)
        new_key = client.cookies[settings.SESSION_COOKIE_NAME].value
        sent = _Runtime.hits[0]
        with override_settings(
            SISOC_BACKEND="pas", ROOT_URLCONF=RUNTIME_URLS, SISOC_BACKENDS={}
        ):
            runtime = client.get(
                sent["path"],
                RAW_URI=sent["path"],
                HTTP_X_SISOC_WEB_GATE=sent["headers"]["x-sisoc-web-gate"],
            )

    assert response.status_code == 200
    assert new_key not in ("", old_key)
    assert sent["headers"]["cookie"] == f"{settings.SESSION_COOKIE_NAME}={new_key}"
    assert runtime.status_code == 200
    assert len(BUSINESS) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_core_rejects_anonymous_with_401_without_forwarding():
    response = Client().get(TARGET)

    assert response.status_code == 401
    assert response.json() == {"detail": "Inicie sesión para continuar."}
    assert response["Cache-Control"] == "private, no-store"
    assert _Runtime.hits == []


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
@pytest.mark.parametrize(
    "access",
    [
        _Access("web_access_denied"),
        _Access("mandatory_survey_required", "/inicio/"),
    ],
)
def test_core_rejects_pending_requirement_with_state_without_forwarding(user, access):
    client, _key = _login(user)

    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(access)):
        response = client.post(TARGET, {"campo": "valor"})

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Debe completar el requisito de acceso web.",
        "state": access.state,
        "required_action_url": access.required_action_url,
    }
    assert _Runtime.hits == []


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_core_refuses_targets_over_4000_bytes_with_414(user):
    client, _key = _login(user)
    prefix = "/api/web/pas/probe/x?q="
    fits = prefix + "a" * (web_gate.MAX_TARGET_BYTES - len(prefix))

    too_long = client.get(fits + "a")
    accepted = client.get(fits)

    assert too_long.status_code == 414
    assert too_long.json() == {"detail": "La dirección solicitada es demasiado larga."}
    assert accepted.status_code == 200
    assert [hit["path"] for hit in _Runtime.hits] == [fits]


@pytest.mark.django_db
def test_core_answers_503_json_when_the_runtime_is_down(user):
    backends = {
        "pas": {"url_prefixes": ("api/web/pas/",), "origin": "http://127.0.0.1:9"}
    }
    with override_settings(SISOC_BACKENDS=backends):
        urls = _urlconf(backend_proxy_urlpatterns())
    client, _key = _login(user)

    with override_settings(
        ROOT_URLCONF=urls, SISOC_WEB_ACCESS_POLICY=_policy(READY), INTERNAL_IPS=[]
    ):
        response = client.post(TARGET, {"campo": "valor"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Servicio no disponible."}


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
@pytest.mark.parametrize(
    ("method", "body"),
    [
        (
            "post",
            {
                "detail": "No se pudo confirmar el resultado. "
                "Verificá el estado antes de reintentar.",
                "uncertain": True,
            },
        ),
        ("get", {"detail": "El servicio no respondió a tiempo.", "uncertain": False}),
    ],
)
def test_core_timeout_is_504_json_uncertain_for_mutations_and_never_retried(
    user, monkeypatch, method, body
):
    client, _key = _login(user)
    monkeypatch.setattr(backend_proxy, "WEB_API_READ_TIMEOUT_SECONDS", 0.3)
    _Runtime.delay = 1.0

    response = getattr(client, method)(TARGET)

    assert response.status_code == 504
    assert response.json() == body
    assert len(_Runtime.hits) == 1


def _record_timeouts(monkeypatch):
    seen = []
    original = backend_proxy.requests.adapters.HTTPAdapter.send

    def send(self, request, *args, **kwargs):
        seen.append((request.path_url, kwargs.get("timeout")))
        return original(self, request, *args, **kwargs)

    monkeypatch.setattr(backend_proxy.requests.adapters.HTTPAdapter, "send", send)
    return seen


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_read_timeout_is_sixty_seconds_only_under_the_web_api_prefix(user, monkeypatch):
    client, _key = _login(user)
    seen = _record_timeouts(monkeypatch)

    client.get(TARGET)
    client.get("/api/pas/listado/")

    assert seen == [(TARGET, (5, 60)), ("/api/pas/listado/", (5, 25))]
    assert backend_proxy.WEB_API_READ_TIMEOUT_SECONDS == web_gate.MAX_AGE_SECONDS == 60


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
@pytest.mark.parametrize(
    ("sent", "kept"),
    [
        ("abc-123.X:9", True),
        ("bad id<script>", False),
        ("a" * 129, False),
        (None, False),
    ],
)
def test_core_sanitises_or_generates_the_request_id(user, sent, kept):
    client, _key = _login(user)
    extra = {} if sent is None else {"HTTP_X_REQUEST_ID": sent}

    client.get(TARGET, **extra)
    forwarded = _Runtime.hits[0]["headers"]["x-request-id"]

    if kept:
        assert forwarded == sent
    else:
        assert forwarded != sent
        assert len(forwarded) == 32


@pytest.mark.django_db
@pytest.mark.usefixtures("core")
def test_legacy_prefixes_keep_request_id_and_drop_a_client_gate_header(user):
    client, _key = _login(user)

    client.get(
        "/api/pas/listado/", HTTP_X_REQUEST_ID="bad id", HTTP_X_SISOC_WEB_GATE="x"
    )
    headers = _Runtime.hits[0]["headers"]

    assert headers["x-request-id"] == "bad id"
    assert "x-sisoc-web-gate" not in headers


def test_outbound_headers_never_copy_the_gate_header():
    request = types.SimpleNamespace(
        META={"HTTP_X_SISOC_WEB_GATE": "forged", "HTTP_ACCEPT": "*/*"},
        get_host=lambda: "testserver",
        scheme="http",
    )

    headers = outbound_headers(request)

    assert "x-sisoc-web-gate" not in headers
    assert headers["accept"] == "*/*"


def test_web_api_prefix_must_be_the_backend_own_name():
    backends = {"pas": {"url_prefixes": ("api/web/vat/",), "origin": "http://x"}}

    with override_settings(SISOC_BACKENDS=backends):
        with pytest.raises(ImproperlyConfigured):
            backend_proxy_urlpatterns()


def test_vertical_names_do_not_collide_with_core_web_api_routes():
    with override_settings(SISOC_BACKENDS={}):
        for name in load_backends_registry():
            with pytest.raises(Resolver404):
                resolve(f"/api/web/{name}/", urlconf="config.urls")
