"""Web API (G1 v1) of one acta: ``/api/web/inspecciones/actas/<numero>/``.

The detail runs ``ActaDetalleView`` and prints every text as
``acta_detalle.html`` does; the two actions run the native ``post()`` of
``views_anulacion`` (service, messages, ``next``). Monolith tests use
``config.settings_all``; runtime tests switch to the inspecciones URLconf,
where only a request the core signed reaches the view.
"""

import types

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from config.urls_all import urlpatterns as monolith_patterns
from core import web_gate
from inspecciones.models import Acta, EventoInspeccion
from inspecciones.web_preview import actas_preview_patterns

API = "/api/web/inspecciones/actas/"
MOTIVO = "Acta cargada sobre la escuela equivocada"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


@pytest.fixture(name="gestor_web")
def gestor_web_fixture(gestor):
    gestor.first_name, gestor.last_name = "Gestora", "Panel"
    gestor.save()
    return _ready(gestor)


@pytest.fixture(name="web")
def web_fixture(gestor_web):
    client = Client()
    client.force_login(gestor_web)
    return client


@pytest.fixture(name="acta")
def acta_fixture(api_a, escuela, cerrar, imagen, nuevo_uuid):
    """A real acta closed by the PWA API, with its entrance photo."""
    inspeccion_uuid, imagen_uuid = nuevo_uuid(), nuevo_uuid()
    subida = api_a.put(
        f"/api/inspecciones/borradores/{inspeccion_uuid}/imagenes/{imagen_uuid}/",
        {"archivo": imagen(), "tipo": "ingreso", "descripcion": "Frente"},
        format="multipart",
    )
    assert subida.status_code in (200, 201), subida.content
    _uuid, cierre = cerrar(
        api_a, escuela, inspeccion_uuid=inspeccion_uuid, imagen_ingreso=imagen_uuid
    )
    assert cierre.status_code == 200, cierre.content
    return Acta.objects.get(numero=cierre.json()["numero"])


def _url(acta, accion=""):
    return f"{API}{acta.numero}/{accion}"


def _toasts(web, acta):
    """Messages the next page load shows (and consumes), as the native toastr."""
    return [m["message"] for m in web.get(_url(acta)).json()["messages"]]


def _estado(acta):
    acta.refresh_from_db()
    return (
        acta.estado,
        acta.es_prueba,
        acta.motivo_anulacion,
        acta.anulada_por_id,
        EventoInspeccion.objects.filter(inspeccion=acta.inspeccion).count(),
    )


# --- Detail ----------------------------------------------------------------


def test_detail_projects_the_native_page(web, acta):
    respuesta = web.get(_url(acta))

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    assert "Cookie" in respuesta["Vary"]
    data = respuesta.json()
    nativo = web.get(reverse("inspecciones_acta_detalle", args=[acta.numero]))
    contexto = nativo.context
    assert data["layout"]["breadcrumb"] == [
        {"text": "Inicio", "url": reverse("inicio")},
        {"text": "Inspecciones escolares", "url": reverse("inspecciones_panel")},
        {"text": acta.numero, "url": None},
    ]
    assert data["layout"]["initials"] == contexto["iniciales_usuario"]
    assert data["acta"]["numero"] == acta.numero
    assert data["acta"]["anulada"] is False and data["acta"]["prueba"] is False
    assert data["acta"]["pdf_url"] is None
    assert data["acta"]["anular_url"] == _url(acta, "anular/")
    assert data["acta"]["prueba_url"] == _url(acta, "prueba/")
    cierre = timezone.localtime(acta.cerrada_at).strftime("%d/%m/%Y %H:%M")
    assert data["acta"]["linea"] == (
        f"{contexto['escuela']['nombre']} · Turno "
        f"{contexto['turno'].lower()} · cierre oficial {cierre}"
    )
    assert [fila["codigo"] for fila in data["respuestas"]] == [
        f"F{i:02d}" for i in range(17)
    ]
    assert [fila["respuesta"] for fila in data["respuestas"]] == [
        fila["respuesta"] for fila in contexto["respuestas"]
    ]
    assert data["resumen"]["personal"] == "20 / 24"
    html = nativo.content.decode()
    for imagen in data["evidencia"]:
        assert imagen["url"] in html
        assert f'alt="{imagen["alt"]}"' in html
    assert data["evidencia"][0]["titulo"] == "Ingreso (F04)"
    assert data["institucion"]["editar_url"] in html.replace("&amp;", "&")
    assert data["inspector"]["usuario"] == "inspector_a"
    assert data["notificaciones"] == []
    assert data["messages"] == []


def test_detail_prints_annulment_test_mark_and_pdf_like_the_template(
    web, acta, coordinacion, pdf, api_a
):
    api_a.put(_pwa_pdf(acta), {"archivo": pdf()}, format="multipart")
    coordinacion.first_name, coordinacion.last_name = "Coordina", "Cion"
    coordinacion.save()
    acta.refresh_from_db()
    Acta.objects.filter(pk=acta.pk).update(es_prueba=True)
    from inspecciones.services.anulacion import (  # pylint: disable=import-outside-toplevel
        anular_acta,
    )

    anular_acta(acta, MOTIVO, coordinacion)
    acta.refresh_from_db()

    data = web.get(_url(acta)).json()

    anulada_at = timezone.localtime(acta.anulada_at).strftime("%d/%m/%Y %H:%M")
    assert data["acta"]["anulada"] is True
    assert data["acta"]["prueba"] is True
    assert data["acta"]["anulada_at"] == anulada_at
    assert data["acta"]["anulada_por"] == "Coordina Cion"
    assert data["acta"]["motivo_anulacion"] == MOTIVO
    assert data["acta"]["pdf_url"] == reverse(
        "inspecciones_acta_pdf", args=[acta.numero]
    )
    html = web.get(reverse("inspecciones_acta_detalle", args=[acta.numero])).content
    texto = " ".join(html.decode().split())
    assert f"el {anulada_at} por Coordina Cion . Motivo: {MOTIVO}" in texto
    assert [evento["texto"] for evento in data["historial"]][-1] == (
        "Anulada · Coordina Cion"
    )
    assert data["historial"][-1]["motivo"] == MOTIVO


def _pwa_pdf(acta):
    return f"/api/inspecciones/actas/{acta.numero}/pdf/"


def test_detail_reads_never_write_and_only_answers_get(web, acta):
    antes = _estado(acta)
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(_url(acta)).status_code == 200
    assert not [
        q["sql"] for q in consultas.captured_queries if q["sql"].startswith(WRITES)
    ]
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(_url(acta)).status_code == 405, metodo
    assert _estado(acta) == antes


def test_detail_missing_acta_is_404_and_guards_match_the_native_rule(
    web, client, acta, inspector_a
):
    assert web.get(f"{API}ACTA-1999-000001/").status_code == 404

    anonimo = client.get(_url(acta))
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    for usuario in (inspector_a, get_user_model().objects.create_user("otro")):
        client.force_login(_ready(usuario))
        assert client.get(_url(acta)).status_code == 403, usuario.username


def test_detail_consumes_the_messages_of_the_previous_action(web, acta):
    web.post(
        reverse("inspecciones_marcar_prueba_acta", args=[acta.numero]),
        {"es_prueba": "1"},
    )

    assert web.get(_url(acta)).json()["messages"] == [
        {"message": f"Acta {acta.numero} marcada como de prueba.", "level": "success"}
    ]
    assert web.get(_url(acta)).json()["messages"] == []


# --- Actions -----------------------------------------------------------------


def test_annul_runs_the_native_action(web, acta, gestor_web):
    respuesta = web.post(
        _url(acta, "anular/"), {"motivo": f"  {MOTIVO}  ", "next": _detail(acta)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": _detail(acta)}
    assert _toasts(web, acta) == [f"Acta {acta.numero} anulada."]
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA
    assert acta.anulada_por == gestor_web
    assert acta.motivo_anulacion == MOTIVO
    evento = EventoInspeccion.objects.get(acta=acta, accion="anulada")
    assert evento.detalle == {"numero": acta.numero, "motivo": MOTIVO}

    repetida = web.post(_url(acta, "anular/"), {"motivo": MOTIVO})
    assert repetida.json() == {"ok": True, "redirect": _detail(acta)}
    assert _toasts(web, acta) == [f"El acta {acta.numero} ya está anulada."]
    assert EventoInspeccion.objects.filter(acta=acta, accion="anulada").count() == 1


def _detail(acta):
    return reverse("inspecciones_acta_detalle", args=[acta.numero])


def test_annul_with_a_short_reason_keeps_the_acta(web, acta):
    antes = _estado(acta)

    respuesta = web.post(_url(acta, "anular/"), {"motivo": "  corto   mot "})

    assert respuesta.json() == {"ok": True, "redirect": _detail(acta)}
    assert _toasts(web, acta) == [
        "Indicá el motivo de la anulación (al menos 10 caracteres)."
    ]
    assert _estado(acta) == antes


def test_test_mark_messages_and_events_match_the_native_view(web, acta):
    url = _url(acta, "prueba/")
    eventos = EventoInspeccion.objects.filter(inspeccion=acta.inspeccion)
    base = eventos.count()

    marcar = web.post(url, {"es_prueba": "1"})
    assert _toasts(web, acta) == [f"Acta {acta.numero} marcada como de prueba."]
    otra_vez = web.post(url, {"es_prueba": "1"})
    assert _toasts(web, acta) == [f"Acta {acta.numero} marcada como de prueba."]
    assert eventos.count() == base + 1
    invalido = web.post(url, {"es_prueba": "si"})
    assert _toasts(web, acta) == ["Valor de prueba inválido."]
    acta.refresh_from_db()
    assert acta.es_prueba is True
    desmarcar = web.post(url, {"es_prueba": "0"})
    assert _toasts(web, acta) == [f"Acta {acta.numero} desmarcada como de prueba."]
    acta.refresh_from_db()
    assert acta.es_prueba is False

    web.post(_url(acta, "anular/"), {"motivo": MOTIVO})
    assert _toasts(web, acta) == [f"Acta {acta.numero} anulada."]
    bloqueada = web.post(url, {"es_prueba": "1"})
    assert _toasts(web, acta) == [
        f"El acta {acta.numero} está anulada: no se puede cambiar la marca de prueba."
    ]
    acta.refresh_from_db()
    assert acta.es_prueba is False


@pytest.mark.parametrize(
    "siguiente",
    ["https://ejemplo.com/robo/", "//ejemplo.com/robo/", "javascript:alert(1)"],
)
def test_external_next_falls_back_to_the_detail(web, acta, siguiente):
    respuesta = web.post(_url(acta, "prueba/"), {"es_prueba": "1", "next": siguiente})

    assert respuesta.json() == {"ok": True, "redirect": _detail(acta)}


def test_internal_next_is_kept(web, acta):
    siguiente = reverse("inspecciones_actas") + "?page=2"

    respuesta = web.post(_url(acta, "prueba/"), {"es_prueba": "1", "next": siguiente})

    assert respuesta.json() == {"ok": True, "redirect": siguiente}


def test_actions_are_post_only_and_rejections_do_not_write(
    web, client, acta, inspector_a
):
    antes = _estado(acta)
    otro = get_user_model().objects.create_user("otro")
    for accion, datos in (
        ("anular/", {"motivo": MOTIVO}),
        ("prueba/", {"es_prueba": "1"}),
    ):
        assert web.get(_url(acta, accion)).status_code == 405
        assert web.put(_url(acta, accion)).status_code == 405
        assert web.post(f"{API}ACTA-1999-000001/{accion}", datos).status_code == 404
        anonimo = Client().post(_url(acta, accion), datos)
        assert anonimo.status_code == 401
        for usuario in (inspector_a, otro):
            client.force_login(_ready(usuario))
            assert client.post(_url(acta, accion), datos).status_code == 403
        client.logout()
    assert _estado(acta) == antes


def test_actions_require_the_csrf_token(gestor_web, acta):
    client = Client(enforce_csrf_checks=True)
    client.force_login(gestor_web)
    antes = _estado(acta)

    respuesta = client.post(_url(acta, "anular/"), {"motivo": MOTIVO})

    assert respuesta.status_code == 403
    assert _estado(acta) == antes


def test_superuser_and_coordination_keep_the_native_rule(client, acta, coordinacion):
    superuser = _ready(
        get_user_model().objects.create_superuser("super_web", password="x")
    )
    for usuario in (superuser, _ready(coordinacion)):
        client.force_login(usuario)
        assert client.get(_url(acta)).status_code == 200, usuario.username
    respuesta = client.post(_url(acta, "prueba/"), {"es_prueba": "1"})
    assert respuesta.status_code == 200
    acta.refresh_from_db()
    assert acta.es_prueba is True


def test_admindocs_head_does_not_bypass_the_detail(client, acta):
    staff = _ready(get_user_model().objects.create_user("staff_web", is_staff=True))
    client.force_login(staff)

    for url in (_url(acta), _url(acta, "anular/"), _url(acta, "prueba/")):
        respuesta = client.head(url)
        assert "X-View" not in respuesta, url
        assert respuesta.status_code in (403, 405), url


# --- Runtime: only a signed request reaches the view ----------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="inspecciones",
        ROOT_URLCONF="inspecciones_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, method="GET"):
    return web_gate.sign(
        audience="inspecciones",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_detail_and_action(web, gestor_web, acta):
    detalle = _url(acta)
    respuesta = web.get(
        detalle,
        RAW_URI=detalle,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=detalle),
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["acta"]["numero"] == acta.numero

    accion = _url(acta, "prueba/")
    sin_firma = web.post(accion, {"es_prueba": "1"}, RAW_URI=accion)
    assert sin_firma.status_code == 403
    assert sin_firma.json() == {"detail": web_gate.DETAIL_REJECTED}
    firma_get = _signed(gestor_web, web, target=accion)
    assert (
        web.post(
            accion, {"es_prueba": "1"}, RAW_URI=accion, HTTP_X_SISOC_WEB_GATE=firma_get
        ).status_code
        == 403
    )
    acta.refresh_from_db()
    assert acta.es_prueba is False
    firmado = web.post(
        accion,
        {"es_prueba": "1"},
        RAW_URI=accion,
        HTTP_X_SISOC_WEB_GATE=_signed(gestor_web, web, target=accion, method="POST"),
    )
    assert firmado.status_code == 200
    assert firmado.json()["redirect"] == _detail(acta)
    acta.refresh_from_db()
    assert acta.es_prueba is True


# --- Local React entry ------------------------------------------------------------


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<!doctype html><script src="/v2/sisoc/assets/app-1.js"></script>',
        encoding="utf-8",
    )
    module = types.ModuleType("acta_detalle_preview_test_urls")
    module.urlpatterns = actas_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_entry_serves_the_index_after_the_native_guards(web, acta, inspector_a):
    respuesta = web.get(_detail(acta))
    assert respuesta.status_code == 200
    assert b"/inspecciones/react/assets/app-1.js" in respuesta.content
    assert "no-store" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert web.head(_detail(acta)).content == b""
    assert web.get("/inspecciones/actas/ACTA-1999-000001/").status_code == 404
    assert web.post(_detail(acta)).status_code == 405

    client = Client()
    anonimo = client.get(_detail(acta))
    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith("/login")
    client.force_login(inspector_a)
    assert client.get(_detail(acta)).status_code == 403


def test_production_urlconf_keeps_the_native_detail(web, acta):
    respuesta = web.get(_detail(acta))

    assert respuesta.status_code == 200
    assert "inspecciones/acta_detalle.html" in [t.name for t in respuesta.templates]
