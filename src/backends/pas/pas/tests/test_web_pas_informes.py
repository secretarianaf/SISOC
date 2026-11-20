"""Web API (G1 v1) of the PAS reports: ``/api/web/pas/informes/`` (PAS04.01, PAS04.03).

Monolith tests go through ``config.settings_all`` (policy evaluated locally);
the runtime tests switch to ``SISOC_BACKEND="pas"`` with the real runtime
URLconf, where only a request the core signed reaches the view.
"""

from datetime import datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings
from django.utils import timezone

from core import web_gate
from pas.models import PasEstado, PasInforme
from pas.services.informe_service import CSV_COLUMNS

ROOT = "/api/web/pas/informes/"
VIEW = ("pas", "view_paspersona")
VIEW_INFORME = ("pas", "view_pasinforme")
ADD_INFORME = ("pas", "add_pasinforme")
EXPORT_CSV = ("auth", "role_exportar_a_csv")

pytestmark = pytest.mark.django_db


def _permission(app_label, codename):
    if (app_label, codename) == EXPORT_CSV:
        return Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": "Exportar a csv"},
        )[0]
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _user(username, *codes, **extra):
    user = _ready(get_user_model().objects.create_user(username, **extra))
    user.user_permissions.add(*[_permission(*code) for code in codes])
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _informe(pk=None, creado=None, usuario=None, **extra):
    datos = {"usuario": usuario, "total_personas": 3, "total_cambios": 1}
    if pk is not None:
        datos["id"] = pk
    datos.update(extra)
    informe = PasInforme.objects.create(**datos)
    if creado is not None:
        PasInforme.objects.filter(pk=informe.pk).update(creado=creado)
        informe.refresh_from_db()
    return informe


def _local(*args):
    return timezone.make_aware(datetime(*args))


@pytest.fixture(name="lector")
def lector_fixture():
    return _user("lector_inf", VIEW, VIEW_INFORME)


@pytest.fixture(name="web")
def web_fixture(lector):
    return _client(lector)


# --- Access: G1 first, then the native route rule ---------------------------


def test_anonymous_gets_401_json(client):
    informe = _informe()
    for url in (ROOT, f"{ROOT}{informe.pk}/"):
        respuesta = client.get(url)
        assert respuesta.status_code == 401, url
        assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


@pytest.mark.parametrize(
    "codes",
    [(), (VIEW,), (VIEW_INFORME,), (VIEW, ADD_INFORME, EXPORT_CSV)],
)
def test_reads_need_both_view_codes_like_the_native_routes(codes):
    informe = _informe()
    client = _client(_user("parcial", *codes))

    for api, native in (
        (ROOT, "/pas/informes"),
        (f"{ROOT}{informe.pk}/", f"/pas/informes/{informe.pk}"),
    ):
        respuesta = client.get(api)
        assert respuesta.status_code == 403, api
        assert "state" not in respuesta.json()
        assert client.get(native).status_code == 403, native


def test_both_view_codes_or_superuser_read(web):
    informe = _informe()
    admin = _client(
        _ready(get_user_model().objects.create_superuser("super_inf", password="x"))
    )

    for client in (web, admin):
        for url in (ROOT, f"{ROOT}{informe.pk}/"):
            respuesta = client.get(url)
            assert respuesta.status_code == 200, url
            assert respuesta["Cache-Control"] == "private, no-store"
            assert "Cookie" in respuesta["Vary"]


def test_reads_only_answer_get(web):
    informe = _informe()
    for url in (ROOT, f"{ROOT}{informe.pk}/"):
        for metodo in ("post", "put", "patch", "delete"):
            assert getattr(web, metodo)(url).status_code == 405, (url, metodo)


def test_reads_write_nothing(web):
    informe = _informe(filtros={"dni": 1}, resultado=[{"dni": 1}])
    antes = list(PasInforme.objects.values())

    web.get(ROOT)
    web.get(f"{ROOT}{informe.pk}/")

    assert list(PasInforme.objects.values()) == antes


def test_admindocs_head_does_not_bypass_the_web_api(client):
    informe = _informe()
    client.force_login(_user("staff_inf", is_staff=True))

    for url in (ROOT, f"{ROOT}{informe.pk}/"):
        respuesta = client.head(url)
        assert respuesta.status_code == 403, url
        assert "X-View" not in respuesta


# --- PAS04.01 listado ---------------------------------------------------------


def test_list_projects_the_native_rows_newest_first(web):
    autor = get_user_model().objects.create_user(
        "autor", first_name="Ana", last_name="Gómez"
    )
    solo_usuario = get_user_model().objects.create_user("solo_username")
    viejo = _informe(creado=_local(2026, 1, 2, 9, 5), usuario=autor)
    medio = _informe(creado=_local(2026, 3, 4, 10, 30), usuario=solo_usuario)
    nuevo = _informe(creado=_local(2026, 5, 6, 23, 59), total_personas=0)

    data = web.get(ROOT).json()

    assert [r["id"] for r in data["results"]] == [nuevo.pk, medio.pk, viejo.pk]
    assert data["results"][2] == {
        "id": viejo.pk,
        "numero": f"PAS-INF-{viejo.pk:06d}",
        "creado": "02/01/2026 09:05",
        "usuario": "Ana Gómez",
        "total_personas": 3,
        "total_cambios": 1,
        "detail_path": f"/pas/informes/{viejo.pk}",
        "download_url": None,
    }
    assert data["results"][1]["usuario"] == "solo_username"
    assert data["results"][0]["usuario"] == ""
    assert data["results"][0]["total_personas"] == 0
    assert data["query"] == ""
    assert data["breadcrumb"] == [
        {"text": "PAS", "url": "/pas/listar"},
        {"text": "Informes", "url": "/pas/informes"},
        {"text": "Listar", "url": None},
    ]


def test_list_same_tie_break_as_the_model_order(web):
    momento = _local(2026, 2, 2, 8, 0)
    primero = _informe(creado=momento)
    segundo = _informe(creado=momento)

    ids = [r["id"] for r in web.get(ROOT).json()["results"]]

    assert ids == [segundo.pk, primero.pk]


@pytest.mark.parametrize("texto", ["PAS-INF-000012", "pas-inf-000012", "12", " 12 "])
def test_search_by_number(web, texto):
    _informe(pk=12)
    _informe(pk=13)

    data = web.get(ROOT, {"q": texto}).json()

    assert [r["id"] for r in data["results"]] == [12]
    assert data["query"] == texto


def test_search_by_username_first_and_last_name(web):
    marta = get_user_model().objects.create_user(
        "mperez", first_name="Marta", last_name="Pérez"
    )
    otro = get_user_model().objects.create_user("jlopez", first_name="Juan")
    suyo = _informe(usuario=marta)
    _informe(usuario=otro)

    for texto in ("mpe", "MARTA", "pérez"):
        ids = [r["id"] for r in web.get(ROOT, {"q": texto}).json()["results"]]
        assert ids == [suyo.pk], texto
    assert web.get(ROOT, {"q": "nadie"}).json()["results"] == []


def test_pages_of_ten_without_a_count(web):
    for _ in range(11):
        _informe()

    primera = web.get(ROOT).json()
    segunda = web.get(ROOT, {"page": 2}).json()

    assert len(primera["results"]) == 10
    assert primera["count"] is None
    assert primera["is_paginated"] is True
    assert (primera["page"], primera["has_next"], primera["next"]) == (1, True, 2)
    # ``build_no_count_page_range`` cannot know the last page: it adds a gap.
    assert primera["page_range"] == [1, 2, "…"]
    assert len(segunda["results"]) == 1
    assert (segunda["page"], segunda["has_previous"], segunda["previous"]) == (
        2,
        True,
        1,
    )
    assert segunda["has_next"] is False


def test_ten_reports_are_one_page(web):
    for _ in range(10):
        _informe()

    data = web.get(ROOT).json()

    assert len(data["results"]) == 10
    assert data["is_paginated"] is False


@pytest.mark.parametrize("page", ["9", "x", "0", "-1"])
def test_invalid_page_behaves_like_get_page(web, page):
    autor = get_user_model().objects.create_user("autor_pag")
    for _ in range(11):
        _informe(usuario=autor)

    native = web.get("/pas/informes", {"page": page}).context["page_obj"].number
    data = web.get(ROOT, {"page": page}).json()

    assert data["page"] == native


def test_pagination_prefix_repeats_the_query_like_the_template(web):
    for numero in range(11):
        _informe(usuario=get_user_model().objects.create_user(f"pag_{numero}"))

    data = web.get(ROOT, {"q": "pag", "page": 1}).json()

    assert data["query_prefix"] == "busqueda=pag&q=pag&"


def test_capabilities_follow_each_permission():
    informe = _informe()
    casos = [
        ((VIEW, VIEW_INFORME), False, False),
        ((VIEW, VIEW_INFORME, ADD_INFORME), True, False),
        ((VIEW, VIEW_INFORME, EXPORT_CSV), False, True),
        ((VIEW, VIEW_INFORME, ADD_INFORME, EXPORT_CSV), True, True),
    ]
    for numero, (codes, genera, descarga) in enumerate(casos):
        client = _client(_user(f"cap_{numero}", *codes))
        lista = client.get(ROOT).json()
        detalle = client.get(f"{ROOT}{informe.pk}/").json()
        esperado = f"/pas/informes/{informe.pk}/descargar" if descarga else None
        assert lista["can_generate"] is genera, codes
        assert lista["results"][0]["download_url"] == esperado, codes
        assert detalle["download_url"] == esperado, codes


def test_superuser_gets_every_capability():
    informe = _informe()
    admin = _client(
        _ready(get_user_model().objects.create_superuser("super_cap", password="x"))
    )

    data = admin.get(ROOT).json()

    assert data["can_generate"] is True
    assert data["results"][0]["download_url"] == f"/pas/informes/{informe.pk}/descargar"


def test_empty_list(web):
    data = web.get(ROOT).json()

    assert data["results"] == []
    assert data["is_paginated"] is False


# --- PAS04.01 detalle ---------------------------------------------------------


def test_detail_projects_the_snapshot(web):
    autor = get_user_model().objects.create_user("autor_det", first_name="Ana")
    estado = PasEstado.objects.get_or_create(nombre="Activo")[0]
    informe = _informe(
        creado=_local(2026, 7, 8, 14, 3),
        usuario=autor,
        total_personas=2,
        total_cambios=0,
        filtros={
            "fecha_creacion_desde": "2026-01-01",
            "estado_actual": {"id": estado.pk, "label": "Activo"},
            "dni": 30111222,
        },
        resultado=[
            {key: f"{key}-1" for key, _ in CSV_COLUMNS},
            {"id_persona": 7, "dni": 30111222, "cuit": None, "apellido": "=1+1"},
        ],
    )

    data = web.get(f"{ROOT}{informe.pk}/").json()

    assert data["numero"] == f"PAS-INF-{informe.pk:06d}"
    assert data["creado"] == "08/07/2026 14:03"
    assert data["usuario"] == "Ana"
    assert (data["total_personas"], data["total_cambios"]) == (2, 0)
    assert data["filtros"] == [
        {"clave": "fecha_creacion_desde", "valor": "2026-01-01"},
        {"clave": "estado_actual", "valor": "Activo"},
        {"clave": "dni", "valor": "30111222"},
    ]
    assert data["columns"] == [{"key": k, "label": label} for k, label in CSV_COLUMNS]
    assert len(data["columns"]) == 16
    assert data["rows"][0] == [f"{key}-1" for key, _ in CSV_COLUMNS]
    # The template prints the stored value: a missing key is empty, ``None`` is
    # "None", and a formula is shown as stored (only the CSV neutralizes it).
    assert data["rows"][1][:5] == ["7", "=1+1", "", "30111222", "None"]
    assert data["rows"][1][5:] == [""] * 11
    assert data["breadcrumb"] == [
        {"text": "PAS", "url": "/pas/listar"},
        {"text": "Informes", "url": "/pas/informes"},
        {"text": data["numero"], "url": None},
    ]


def test_detail_without_filters_or_rows(web):
    informe = _informe(filtros={}, resultado=[])

    data = web.get(f"{ROOT}{informe.pk}/").json()

    assert data["filtros"] == []
    assert data["rows"] == []
    assert data["usuario"] == ""


def test_detail_filter_value_without_label_prints_the_value(web):
    informe = _informe(filtros={"provincia": {"id": 3, "label": ""}, "flag": True})

    data = web.get(f"{ROOT}{informe.pk}/").json()

    assert data["filtros"] == [
        {"clave": "provincia", "valor": "{'id': 3, 'label': ''}"},
        {"clave": "flag", "valor": "True"},
    ]


def test_detail_does_not_paginate_rows(web):
    informe = _informe(resultado=[{"dni": n} for n in range(120)])

    data = web.get(f"{ROOT}{informe.pk}/").json()

    assert len(data["rows"]) == 120


def test_detail_unknown_pk_is_404(web):
    assert web.get(f"{ROOT}999999/").status_code == 404
    assert web.get("/pas/informes/999999").status_code == 404


def test_download_stays_the_native_csv(client):
    informe = _informe(resultado=[{"apellido": "=CMD()", "dni": 1}])
    client.force_login(_user("descarga", VIEW, VIEW_INFORME, EXPORT_CSV))

    respuesta = client.get(f"/pas/informes/{informe.pk}/descargar")

    assert respuesta.status_code == 200
    assert respuesta["Content-Disposition"].endswith(
        f'filename="pas-inf-{informe.pk:06d}.csv"'
    )
    assert respuesta.content.startswith(b"\xef\xbb\xbf")
    assert b"'=CMD()" in respuesta.content


def test_native_pages_are_unchanged(web):
    informe = _informe(usuario=get_user_model().objects.create_user("autor_nat"))

    for url, plantilla in (
        ("/pas/informes", "pas/informe_list.html"),
        (f"/pas/informes/{informe.pk}", "pas/informe_detail.html"),
    ):
        respuesta = web.get(url)
        assert respuesta.status_code == 200, url
        assert plantilla in [t.name for t in respuesta.templates], url


def test_native_pages_fail_without_author_and_the_api_does_not(lector):
    """Kept quirk: ``default:informe.usuario.username`` raises when the author is gone.

    The native list and detail answer 500 for a report whose ``usuario`` is
    null (``SET_NULL``); the API returns ``""`` and the screen prints «-», the
    template's evident intent. Recorded as a deviation, not fixed natively.
    """
    informe = _informe(usuario=None)
    client = Client(raise_request_exception=False)
    client.force_login(lector)

    assert client.get("/pas/informes").status_code == 500
    assert client.get(f"/pas/informes/{informe.pk}").status_code == 500
    assert client.get(ROOT).json()["results"][0]["usuario"] == ""
    assert client.get(f"{ROOT}{informe.pk}/").json()["usuario"] == ""


# --- Split runtime ------------------------------------------------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="pas",
        ROOT_URLCONF="pas_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, *, target, now=None):
    return web_gate.sign(
        audience="pas",
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_signed_reads(web, lector):
    informe = _informe()
    for target in (ROOT, f"{ROOT}{informe.pk}/"):
        respuesta = web.get(
            target,
            RAW_URI=target,
            HTTP_X_SISOC_WEB_GATE=_signed(lector, web, target=target),
        )
        assert respuesta.status_code == 200, target
    assert respuesta.json()["id"] == informe.pk


@pytest.mark.usefixtures("runtime")
def test_runtime_rejects_unsigned_and_other_target_requests(web, lector):
    informe = _informe()
    target = f"{ROOT}{informe.pk}/"
    for token in (None, _signed(lector, web, target=ROOT)):
        extra = {"RAW_URI": target}
        if token:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        respuesta = web.get(target, **extra)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"detail": web_gate.DETAIL_REJECTED}


@pytest.mark.usefixtures("runtime")
def test_runtime_still_applies_the_native_rule(client):
    usuario = _user("sin_informe_runtime", VIEW)
    client.force_login(usuario)

    respuesta = client.get(
        ROOT, RAW_URI=ROOT, HTTP_X_SISOC_WEB_GATE=_signed(usuario, client, target=ROOT)
    )

    assert respuesta.status_code == 403
    assert respuesta.json() != {"detail": web_gate.DETAIL_REJECTED}
