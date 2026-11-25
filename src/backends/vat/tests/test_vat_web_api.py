"""Compuerta G1 v1 de la API web de VAT (``/api/web/vat/``) del frontend INET.

La API se mudó desde ``/api/inet/`` sin alias: mismas vistas, recursos y
escritores. En el runtime de VAT exige la constancia firmada por el core y en
el monolito evalúa localmente los requisitos web del core. Los tests de negocio
de cada vista siguen en ``test_inet_api.py``.
"""

import json
from dataclasses import dataclass

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import Resolver404, resolve, reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIClient

from config.backends import load_backends_registry
from core import web_gate
from core.backend_proxy import backend_proxy_urlpatterns
from VAT import web_api_urls
from VAT.models import (
    Centro,
    Curso,
    ModalidadCursada,
    PlanVersionCurricular,
    Sector,
)
from core.models import Localidad, Municipio, Provincia
from core.url_registry import REGISTRY_PATH

pytestmark = pytest.mark.django_db

WEB_ROOT = "/api/web/vat/"
INET_ROOT = "/api/inet/"


@dataclass(frozen=True)
class _Access:
    state: str
    required_action_url: str | None = None


READY = _Access("ready")
PENDING = _Access("password_change_required", "/password/first-change/")


def _policy(access):
    return lambda request: access


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="vat",
        ROOT_URLCONF="vat_runtime.urls",
        SISOC_WEB_ACCESS_POLICY=_policy(READY),
        INTERNAL_IPS=[],
    ):
        yield


@pytest.fixture(name="data")
def data_fixture():
    province = Provincia.objects.create(nombre="Buenos Aires")
    city = Municipio.objects.create(nombre="La Plata", provincia=province)
    locality = Localidad.objects.create(nombre="Tolosa", municipio=city)
    center = Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=province,
        municipio=city,
        localidad=locality,
    )
    mode = ModalidadCursada.objects.create(nombre="Presencial")
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=province,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=mode,
        horas_reloj=100,
    )
    return {"center": center, "plan": plan, "mode": mode}


def _login(user, **client_kwargs):
    client = APIClient(**client_kwargs)
    client.force_login(user)
    return client, client.cookies[settings.SESSION_COOKIE_NAME].value


def _signed(user, session_key, target, method="GET", audience="vat"):
    return web_gate.sign(
        audience=audience,
        user_pk=user.pk,
        session_key=session_key,
        method=method,
        target=target,
    )


def _course_payload(data, name):
    return {
        "campos": {
            "centro": data["center"].pk,
            "nombre": name,
            "plan_estudio": data["plan"].pk,
            "estado": "activo",
            "inscripcion_libre": True,
        }
    }


# --- Superficie -------------------------------------------------------------


def _web_route_names():
    return [pattern.name for pattern in web_api_urls.urlpatterns]


@pytest.mark.parametrize("name", _web_route_names())
def test_every_inet_view_is_published_only_under_api_web_vat_behind_the_gate(name):
    sample = {"pk": 7, "curso_id": 7, "field": "provincia", "aporte": "vat"}
    pattern = next(p for p in web_api_urls.urlpatterns if p.name == name)
    kwargs = {key: sample[key] for key in pattern.pattern.converters}
    web_path = reverse(f"vat_web_api:{name}", kwargs=kwargs)
    assert web_path.startswith(WEB_ROOT)
    view = resolve(web_path).func.view_class
    assert view.permission_classes[0] is web_gate.WebGatePermission
    assert IsAuthenticated in view.permission_classes
    with pytest.raises(Resolver404):
        resolve(INET_ROOT + web_path.removeprefix(WEB_ROOT))


def test_no_ungated_inet_alias_is_registered():
    regexes = [entry["regex"] for entry in json.loads(REGISTRY_PATH.read_text("utf-8"))]
    assert not [regex for regex in regexes if "api/inet/" in regex]
    assert r"^api/web/vat/session/\Z" in regexes
    assert not any(
        "api/inet/" in prefix
        for spec in load_backends_registry().values()
        for prefix in spec["url_prefixes"]
    )


def test_vat_publishes_its_web_prefix_and_the_core_gates_it():
    registry = load_backends_registry()
    assert web_gate.web_api_prefix("vat") in registry["vat"]["url_prefixes"]
    backends = {
        name: {**spec, "origin": spec["default_origin"]}
        for name, spec in registry.items()
    }
    with override_settings(SISOC_BACKENDS=backends):
        patterns = backend_proxy_urlpatterns()  # raises on a foreign api/web/
    names = {pattern.name for pattern in patterns}
    assert "backend_proxy_vat_api_web_vat" in names


# --- Runtime de VAT (constancia firmada por el core) -------------------------


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_session_request_privately(superuser):
    client, key = _login(superuser)
    target = WEB_ROOT + "session/"
    response = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(superuser, key, target),
    )
    assert response.status_code == 200, response.content
    assert "add_centro" in response.data["permissions"]
    assert "csrftoken" in response.cookies
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.usefixtures("runtime")
@pytest.mark.parametrize("token", ["missing", "other_audience", "other_target"])
def test_runtime_rejects_unsigned_or_foreign_requests_as_json(superuser, token):
    client, key = _login(superuser)
    target = WEB_ROOT + "centros/"
    headers = {
        "missing": {},
        "other_audience": {
            "HTTP_X_SISOC_WEB_GATE": _signed(superuser, key, target, audience="pas")
        },
        "other_target": {
            "HTTP_X_SISOC_WEB_GATE": _signed(superuser, key, WEB_ROOT + "cursos/")
        },
    }[token]
    response = client.get(target, RAW_URI=target, **headers)
    assert response.status_code == 403
    assert response.json() == {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_without_session_is_401_json():
    target = WEB_ROOT + "session/"
    response = APIClient().get(target, RAW_URI=target)
    assert response.status_code == 401
    assert response.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


@pytest.mark.usefixtures("runtime")
def test_runtime_signed_create_uses_the_native_writer_and_unsigned_writes_nothing(
    superuser, data
):
    client, key = _login(superuser)
    target = WEB_ROOT + "cursos/"
    unsigned = client.post(
        target, _course_payload(data, "Sin firma"), format="json", RAW_URI=target
    )
    assert unsigned.status_code == 403
    assert not Curso.objects.filter(nombre="Sin firma").exists()

    response = client.post(
        target,
        _course_payload(data, "Curso web"),
        format="json",
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(superuser, key, target, method="POST"),
    )
    assert response.status_code == 201, response.data
    course = Curso.objects.get(pk=response.data["id"])
    assert course.nombre == "Curso web"
    # Same native validation as /api/inet/: the plan sets the modality.
    assert course.modalidad == data["mode"]


@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_owner_csrf_and_action_permissions(superuser, user, data):
    target = WEB_ROOT + "cursos/"
    csrf_client, key = _login(superuser, enforce_csrf_checks=True)
    response = csrf_client.post(
        target,
        _course_payload(data, "Sin CSRF"),
        format="json",
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(superuser, key, target, method="POST"),
    )
    assert response.status_code == 403
    assert not Curso.objects.filter(nombre="Sin CSRF").exists()

    client, key = _login(user)
    target = WEB_ROOT + "centros/"
    response = client.get(
        target,
        RAW_URI=target,
        HTTP_X_SISOC_WEB_GATE=_signed(user, key, target),
    )
    assert response.status_code == 403
    assert response.json() != {"detail": web_gate.DETAIL_REJECTED}


# --- Monolito (config.settings_all, sin salto remoto) ------------------------


def test_monolith_evaluates_core_requirements_and_ignores_the_header(superuser):
    client, key = _login(superuser)
    target = WEB_ROOT + "centros/"
    forged = {"HTTP_X_SISOC_WEB_GATE": _signed(superuser, key, target)}
    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(PENDING)):
        pending = client.get(target, **forged)
    assert pending.status_code == 403
    assert pending.json() == {
        "detail": web_gate.DETAIL_REQUIREMENT,
        "state": PENDING.state,
        "required_action_url": PENDING.required_action_url,
    }
    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(READY)):
        ready = client.get(target)
    assert ready.status_code == 200
    assert set(ready.data) == {"count", "next", "previous", "results"}


def test_monolith_without_session_is_401_with_the_gate_message():
    with override_settings(SISOC_WEB_ACCESS_POLICY=_policy(READY)):
        response = APIClient().get(WEB_ROOT + "session/")
    assert response.status_code == 401
    assert response.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
