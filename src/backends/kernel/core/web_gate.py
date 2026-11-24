"""G1 v1: signed per-request attestation from the core to a vertical runtime.

Decision: ``docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md``.

The core owns the session and the web prerequisites (web access, password,
profile, survey). For ``/api/web/<vertical>/`` it evaluates them, and only when
the user is ready it forwards the request with an internal header signed with
the shared ``SECRET_KEY``. The runtime of ``<vertical>`` verifies that header
after authentication and before anything reads the body, then applies its own
session authentication, CSRF, permissions and object scope as usual.

- Envelope: ``TimestampSigner`` (SHA-256, salt ``sisoc.web-gate.v1``) whose
  timestamp is ``iat``. Exact fields: ``v``, ``aud``, ``sub``,
  ``session_binding``, ``method``, ``target`` and ``iat``.
- ``session_binding`` is an HMAC of the session key of the cookie the request
  arrives with: Django may cycle the key during authentication when the session
  hash only validates with a ``SECRET_KEY_FALLBACKS`` entry.
- ``target`` is the exact ``path_url`` the core sends; the runtime compares it
  with gunicorn's ``RAW_URI``. Without ``RAW_URI`` the route is not enabled.
- ``MAX_AGE_SECONDS`` equals the proxy read timeout for this namespace: a
  request the core already gave up on (504) must not start business later.
- No anti-replay: a captured header can be replayed inside the window with the
  same cookie, method and target. It never reaches the browser or the logs.

The monolith (``config.settings_all``) has no remote hop: ``WebGatePermission``
evaluates the core policy locally and the header is never trusted anywhere but
in a runtime.
"""

import functools
import re
import time
import uuid

from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.utils.cache import patch_vary_headers
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

HEADER = "X-SISOC-Web-Gate"
META_KEY = "HTTP_X_SISOC_WEB_GATE"
ENVELOPE_SALT = "sisoc.web-gate.v1"
BINDING_SALT = "sisoc.web-gate.session.v1"
VERSION = 1
FIELDS = frozenset({"v", "aud", "sub", "session_binding", "method", "target", "iat"})
MAX_HEADER_BYTES = 6144
MAX_TARGET_BYTES = 4000
FUTURE_SKEW_SECONDS = 2
MAX_AGE_SECONDS = 60
WEB_API_ROOT = "api/web/"

DETAIL_UNAUTHENTICATED = "Inicie sesión para continuar."
DETAIL_REQUIREMENT = "Debe completar el requisito de acceso web."
DETAIL_REJECTED = "Solicitud no autorizada."
DETAIL_UNAVAILABLE = "Servicio no disponible."
DETAIL_TARGET_TOO_LONG = "La dirección solicitada es demasiado larga."
DETAIL_TIMEOUT = "El servicio no respondió a tiempo."
DETAIL_UNCERTAIN = (
    "No se pudo confirmar el resultado. Verificá el estado antes de reintentar."
)

_REQUEST_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")


class TargetTooLarge(ValueError):
    """The target exceeds ``MAX_TARGET_BYTES``; the core must answer 414."""


def _now():
    return time.time()


def web_api_prefix(vertical):
    """``url_prefixes`` entry that publishes the web API of ``vertical``."""
    return f"{WEB_API_ROOT}{vertical}/"


def session_binding(session_key, secret=None):
    return salted_hmac(
        BINDING_SALT, session_key, secret=secret, algorithm="sha256"
    ).hexdigest()


class _Signer(signing.TimestampSigner):
    """Envelope signer whose timestamp is exactly ``iat``."""

    def __init__(self, iat=None):
        super().__init__(salt=ENVELOPE_SALT, algorithm="sha256")
        self._iat = iat

    def timestamp(self):
        return signing.b62_encode(self._iat)


def sign(
    *, audience, user_pk, session_key, method, target, now=None
):  # pylint: disable=too-many-arguments
    """Header value for one request the core forwards to ``audience``."""
    if len(target.encode()) > MAX_TARGET_BYTES:
        raise TargetTooLarge(target[:80])
    iat = int(_now() if now is None else now)
    payload = {
        "v": VERSION,
        "aud": audience,
        "sub": str(user_pk),
        "session_binding": session_binding(session_key),
        "method": method.upper(),
        "target": target,
        "iat": iat,
    }
    return _Signer(iat).sign_object(payload, compress=False)


def _secrets():
    return [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]


def _strict_int(value):
    """``int`` but not ``bool``: ``True`` must not pass as version 1."""
    return isinstance(value, int) and not isinstance(value, bool)


def _payload(token):
    """Signed payload, or ``None``; the envelope timestamp must equal ``iat``."""
    try:
        payload = _Signer().unsign_object(token)
        timestamp = signing.b62_decode(token.rsplit(":", 2)[1])
    except (signing.BadSignature, ValueError, TypeError, IndexError):
        return None
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        return None
    if not (_strict_int(payload["v"]) and _strict_int(payload["iat"])):
        return None
    if payload["iat"] != timestamp:
        return None
    if not all(
        isinstance(payload[field], str)
        for field in ("aud", "sub", "session_binding", "method", "target")
    ):
        return None
    return payload


def verify(request, token, audience):
    """``"ok"`` or the rejection reason (for tests and metrics, never the client)."""
    if not token:
        return "missing"
    if len(token.encode("latin-1", "replace")) > MAX_HEADER_BYTES:
        return "too_large"
    payload = _payload(token)
    if payload is None:
        return "bad_signature"
    reason = "ok"
    now = _now()
    if payload["v"] != VERSION:
        reason = "version"
    elif payload["iat"] > now + FUTURE_SKEW_SECONDS:
        reason = "future"
    elif now - payload["iat"] > MAX_AGE_SECONDS:
        reason = "expired"
    elif payload["aud"] != audience:
        reason = "audience"
    elif payload["sub"] != str(request.user.pk):
        reason = "subject"
    elif not _binding_matches(
        payload["session_binding"], request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    ):
        reason = "session"
    elif payload["method"] != request.method:
        reason = "method"
    elif payload["target"] != request.META.get("RAW_URI"):
        reason = "target"
    return reason


def _binding_matches(binding, cookie_key):
    if not cookie_key:
        return False
    return any(
        constant_time_compare(binding, session_binding(cookie_key, secret=secret))
        for secret in _secrets()
    )


def request_id(value):
    """Correlation id for the runtime: kept when well formed, else generated.

    It is not signed and is never part of the authorization.
    """
    if value and _REQUEST_ID.fullmatch(value):
        return value
    return uuid.uuid4().hex


def mark_private(response):
    response["Cache-Control"] = "private, no-store"
    patch_vary_headers(response, ("Cookie",))
    return response


def json_response(status_code, body):
    response = mark_private(JsonResponse(body, status=status_code))
    if status_code == status.HTTP_401_UNAUTHORIZED:
        response["WWW-Authenticate"] = "Session"
    return response


def unauthenticated_response():
    return json_response(401, {"detail": DETAIL_UNAUTHENTICATED})


def requirement_response(access):
    return json_response(
        403,
        {
            "detail": DETAIL_REQUIREMENT,
            "state": access.state,
            "required_action_url": access.required_action_url,
        },
    )


def resolve_local_policy(request):
    """Core web prerequisites (``SISOC_WEB_ACCESS_POLICY``), evaluated here.

    The setting names the core resolver by dotted path, so the kernel never
    imports the core. It returns an object with ``state`` and
    ``required_action_url``; ``state == "ready"`` means no requirement pending.
    """
    policy = settings.SISOC_WEB_ACCESS_POLICY
    if isinstance(policy, str):
        policy = import_string(policy)
    return policy(request)


@functools.lru_cache(maxsize=1)
def _registered_web_api_paths():
    from config.backends import (  # pylint: disable=import-outside-toplevel
        load_backends_registry,
    )

    return tuple("/" + web_api_prefix(name) for name in load_backends_registry())


def _is_web_api_path(path):
    if getattr(settings, "SISOC_BACKEND", None):
        return path.startswith("/" + WEB_API_ROOT)
    return path.startswith(_registered_web_api_paths())


class WebGateMiddleware:
    """Drops the gate header everywhere; a vertical runtime also verifies it.

    Goes right after ``AuthenticationMiddleware``: it runs before any view or
    ``process_view`` (CSRF) reads the body. In the core and the monolith the
    header is only removed, so nothing downstream can trust a client value.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.META.pop(META_KEY, None)
        request.sisoc_web_gate = False
        audience = getattr(settings, "SISOC_BACKEND", None)
        if audience and request.path_info.startswith("/" + WEB_API_ROOT):
            if not request.user.is_authenticated:
                return unauthenticated_response()
            if request.META.get("RAW_URI") is None:
                return json_response(503, {"detail": DETAIL_UNAVAILABLE})
            if verify(request, token, audience) != "ok":
                return json_response(403, {"detail": DETAIL_REJECTED})
            request.sisoc_web_gate = True
        response = self.get_response(request)
        if _is_web_api_path(request.path_info):
            mark_private(response)
        return response


class WebGateUnauthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = DETAIL_UNAUTHENTICATED
    auth_header = "Session"


class WebGateRejected(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = DETAIL_REJECTED


class WebGateRequirementPending(APIException):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, access):
        super().__init__()
        self.detail = {
            "detail": DETAIL_REQUIREMENT,
            "state": access.state,
            "required_action_url": access.required_action_url,
        }


class WebGatePermission(BasePermission):
    """Permission for the views of ``/api/web/<vertical>/``.

    In a runtime it only accepts requests the middleware verified. In the
    monolith it evaluates the core policy locally and ignores any header.
    Action permissions and object scope stay with the owner's view.
    """

    def has_permission(self, request, view):
        if getattr(settings, "SISOC_BACKEND", None):
            if getattr(request, "sisoc_web_gate", False) is True:
                return True
            raise WebGateRejected()
        if not request.user or not request.user.is_authenticated:
            raise WebGateUnauthenticated()
        access = resolve_local_policy(request)
        if access.state == "unauthenticated":
            raise WebGateUnauthenticated()
        if access.state != "ready":
            raise WebGateRequirementPending(access)
        return True
