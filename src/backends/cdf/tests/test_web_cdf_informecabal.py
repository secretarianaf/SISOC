"""Web API (G1 v1) of the CDF Informe Cabal screens (CDF01).

The endpoints run the native views (``InformeCabalListView``, the file, registro
and per-centre detail views); the tests pin the access chain, the projections
(pagination, formats, the per-row flags) and the native quirks verbatim.
"""

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase
from django.utils import timezone
from django.utils.html import escape

from centrodefamilia.models import CabalArchivo, Centro, InformeCabalRegistro

pytestmark = pytest.mark.django_db


def _actor(username, *, view=True):
    user = User.objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    return User.objects.get(pk=user.pk)


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="actor")
def actor_fixture():
    return _actor("cdf_cabal")


def _archivo(actor, nombre="informe.xlsx", **totales):
    archivo = CabalArchivo(
        nombre_original=nombre,
        usuario=actor,
        total_filas=totales.get("total_filas", 3),
        total_validas=totales.get("total_validas", 2),
        total_invalidas=totales.get("total_invalidas", 1),
    )
    archivo.archivo.save(nombre, ContentFile(b"x"), save=False)
    archivo.save()
    return archivo


def _centro(codigo="CAB-1"):
    return Centro.objects.create(
        nombre=f"Centro {codigo}",
        tipo="faro",
        codigo=codigo,
        domicilio_actividad="Domicilio",
        telefono="1",
        celular="2",
        correo="c@example.com",
        nombre_referente="R",
        apellido_referente="E",
        telefono_referente="3",
        correo_referente="r@example.com",
    )


def _registro(archivo, fila, centro=None, motivo="", importe="1234.5"):
    return InformeCabalRegistro.objects.create(
        archivo=archivo,
        centro=centro,
        nro_tarjeta="1",
        nro_auto="2",
        mti="3",
        nro_comercio=f"NC{fila}",
        razon_social=f"Razon {fila}",
        importe=importe,
        fecha_trx="2026-10-05",
        moneda_origen="ARS",
        importe_pesos=importe,
        motivo_rechazo=motivo,
        fila_numero=fila,
    )


# --- Access chain -------------------------------------------------------------


def test_access_chain_is_login_view_centro_then_object(actor):
    archivo = _archivo(actor)
    centro = _centro()
    urls = (
        "/api/web/cdf/informecabal/",
        f"/api/web/cdf/informecabal/{archivo.pk}/",
        f"/api/web/cdf/informecabal/registro/{archivo.pk}/",
        f"/api/web/cdf/centros/{centro.pk}/informecabal/{archivo.pk}/",
    )
    sin_permiso = _client(_actor("cdf_cabal_sin", view=False))

    for url in urls:
        assert Client().get(url).status_code == 401
        assert sin_permiso.get(url).status_code == 403
        assert _client(actor).get(url).status_code == 200
        assert _client(actor).post(url).status_code == 405
    assert _client(actor).get("/api/web/cdf/informecabal/999999/").status_code == 404
    assert (
        _client(actor).get("/api/web/cdf/informecabal/registro/999999/").status_code
        == 404
    )
    assert (
        _client(actor)
        .get(f"/api/web/cdf/centros/999999/informecabal/{archivo.pk}/")
        .status_code
        == 404
    )
    assert (
        _client(actor)
        .get(f"/api/web/cdf/centros/{centro.pk}/informecabal/999999/")
        .status_code
        == 404
    )


# --- History list ---------------------------------------------------------------


def test_list_is_paginated_by_ten_newest_first_with_native_tolerance(actor):
    for numero in range(12):
        _archivo(actor, f"f{numero:02d}.xlsx")
    client = _client(actor)

    first = client.get("/api/web/cdf/informecabal/").json()
    assert first["page"] == 1
    assert [fila["nombre_original"] for fila in first["results"]][0] == "f11.xlsx"
    assert len(first["results"]) == 10
    assert (first["has_previous"], first["has_next"]) == (False, True)
    assert (first["previous_page"], first["next_page"]) == (None, 2)
    second = client.get("/api/web/cdf/informecabal/?page=2").json()
    assert len(second["results"]) == 2
    assert (second["has_previous"], second["has_next"]) == (True, False)
    # ``Paginator.get_page``: garbage is the first page, out of range the last.
    assert client.get("/api/web/cdf/informecabal/?page=x").json()["page"] == 1
    assert client.get("/api/web/cdf/informecabal/?page=99").json()["page"] == 2


def test_list_row_formats_and_urls(actor):
    archivo = _archivo(
        actor, "datos.xlsx", total_filas=7, total_validas=5, total_invalidas=2
    )
    local = timezone.localtime(archivo.fecha_subida)

    payload = _client(actor).get("/api/web/cdf/informecabal/").json()

    assert payload["results"] == [
        {
            "id": archivo.pk,
            "nombre_original": "datos.xlsx",
            "fecha_subida": local.strftime("%d/%m/%Y %H:%M"),
            "fecha_orden": local.strftime("%Y-%m-%d %H:%M"),
            "usuario": "cdf_cabal",
            "total_filas": 7,
            "total_validas": 5,
            "total_invalidas": 2,
            "urls": {"detail": f"/centrodefamilia/informecabal/{archivo.pk}/"},
        }
    ]
    assert payload["urls"] == {
        "list": "/centrodefamilia/informecabal/",
        "preview": "/centrodefamilia/informecabal/preview/",
        "process": "/centrodefamilia/informecabal/process/",
        "reprocess": "/centrodefamilia/informecabal/reprocess/",
    }
    assert payload["messages"] == []


def test_list_empty_has_no_rows_and_response_is_private(actor):
    response = _client(actor).get("/api/web/cdf/informecabal/")

    assert response.json()["results"] == []
    assert "private" in response["Cache-Control"]


def test_list_consumes_the_queued_message_with_its_native_tags(actor, monkeypatch):
    archivo = _archivo(actor)
    monkeypatch.setattr(
        "centrodefamilia.views.informecabal.persist_file_and_rows",
        lambda *args, **kwargs: (archivo, 3, 2, 1),
    )
    client = _client(actor)
    client.post(
        "/centrodefamilia/informecabal/process/",
        {"file": SimpleUploadedFile("nuevo.xlsx", b"x")},
    )

    first = client.get("/api/web/cdf/informecabal/").json()
    second = client.get("/api/web/cdf/informecabal/").json()

    assert first["alerts"] == [
        {"message": "Informe CABAL procesado correctamente.", "tags": "success"}
    ]
    assert second["alerts"] == []


# --- File detail ----------------------------------------------------------------


def test_archivo_detail_rows_flags_and_formats(actor):
    archivo = _archivo(actor)
    centro = _centro()
    _registro(archivo, 2, centro=centro, motivo="0")
    _registro(archivo, 1, centro=None, motivo="05", importe="10")
    _registro(archivo, 3, centro=centro, motivo="")

    payload = _client(actor).get(f"/api/web/cdf/informecabal/{archivo.pk}/").json()

    assert payload["archivo"]["nombre_original"] == "informe.xlsx"
    assert payload["archivo"]["usuario"] == "cdf_cabal"
    assert (
        payload["archivo"]["total_filas"],
        payload["archivo"]["total_validas"],
        payload["archivo"]["total_invalidas"],
    ) == (3, 2, 1)
    assert payload["urls"] == {"list": "/centrodefamilia/informecabal/"}
    # Native order is by id; the counter is the template's ``forloop.counter``.
    assert [fila["numero"] for fila in payload["registros"]] == [1, 2, 3]
    assert [fila["nro_comercio"] for fila in payload["registros"]] == [
        "NC2",
        "NC1",
        "NC3",
    ]
    assert [fila["pago_aceptado"] for fila in payload["registros"]] == [
        True,
        False,
        True,
    ]
    assert [fila["impactado"] for fila in payload["registros"]] == [True, False, True]
    assert payload["registros"][0]["fecha_trx"] == "05/10/2026"
    assert payload["registros"][0]["importe"] == "1234,50"
    assert payload["registros"][1]["importe_pesos"] == "10,00"


def test_archivo_detail_without_rows_is_empty(actor):
    archivo = _archivo(actor)

    payload = _client(actor).get(f"/api/web/cdf/informecabal/{archivo.pk}/").json()

    assert payload["registros"] == []


# --- Registro detail -----------------------------------------------------------


def test_registro_detail_projects_only_what_the_native_page_shows(actor):
    archivo = _archivo(actor)
    _registro(archivo, 1)

    payload = (
        _client(actor).get(f"/api/web/cdf/informecabal/registro/{archivo.pk}/").json()
    )

    assert payload == {"messages": []}


def test_archive_links_open_the_exact_registro_in_both_surfaces(actor):
    archivo = _archivo(actor)
    first = _registro(archivo, 3, centro=_centro())
    second = _registro(archivo, 7)
    second.no_coincidente = True
    second.save(update_fields=["no_coincidente"])
    foreign = _registro(_archivo(actor, "otro.xlsx"), 9)
    client = _client(actor)
    detail = f"/centrodefamilia/informecabal/{archivo.pk}/"
    native_base = f"/centrodefamilia/informecabal/registro/{archivo.pk}/"
    api_base = f"/api/web/cdf/informecabal/registro/{archivo.pk}/"

    native_list = client.get(detail)
    api_list = client.get(f"/api/web/cdf/informecabal/{archivo.pk}/").json()
    for row, selected, centro, no_coincidente in (
        (api_list["registros"][0], first, str(first.centro), "No"),
        (api_list["registros"][1], second, "—", "Sí"),
    ):
        url = f"{native_base}?registro={selected.pk}"
        assert url in native_list.content.decode()
        assert row["urls"]["detail"] == url
        native = client.get(url)
        assert native.context["registro"].pk == selected.pk
        SimpleTestCase().assertContains(
            native,
            f'<dt class="col-sm-3">Centro</dt><dd class="col-sm-9">{escape(centro)}</dd>',
            html=True,
        )
        SimpleTestCase().assertContains(
            native,
            f'<dt class="col-sm-3">No coincidente</dt><dd class="col-sm-9">{no_coincidente}</dd>',
            html=True,
        )
        api = client.get(f"{api_base}?registro={selected.pk}").json()
        assert api["registro"]["id"] == selected.pk
        assert api["registro"]["nro_comercio"] == selected.nro_comercio
        assert api["registro"]["centro"] == centro
        assert api["registro"]["no_coincidente"] == no_coincidente
        assert api["urls"]["archivo"] == detail

    for invalid in (
        str(foreign.pk),
        "0",
        "abc",
        "",
        "9" * 19,
        "9" * 40,
        f"{first.pk}&registro={second.pk}",
    ):
        assert client.get(f"{native_base}?registro={invalid}").status_code == 404
        assert client.get(f"{api_base}?registro={invalid}").status_code == 404


# --- Per-centre detail ------------------------------------------------------------


def test_por_centro_filters_orders_and_formats(actor):
    archivo = _archivo(actor)
    centro = _centro()
    otro = _centro("CAB-2")
    _registro(archivo, 2, centro=centro, motivo="0", importe="1234.5")
    _registro(archivo, 1, centro=centro, motivo="07", importe="5")
    _registro(archivo, 3, centro=otro)

    payload = (
        _client(actor)
        .get(f"/api/web/cdf/centros/{centro.pk}/informecabal/{archivo.pk}/")
        .json()
    )

    assert payload["centro"] == {"id": centro.pk, "nombre": "Centro CAB-1"}
    assert payload["count"] == 2
    assert (payload["page"], payload["num_pages"]) == (1, 1)
    assert [fila["nro_comercio"] for fila in payload["results"]] == ["NC1", "NC2"]
    assert [fila["numero"] for fila in payload["results"]] == [1, 2]
    assert [fila["pago_aceptado"] for fila in payload["results"]] == [False, True]
    # ``${{ importe|floatformat:2 }}`` is localized by the template engine.
    assert [fila["importe"] for fila in payload["results"]] == ["$5,00", "$1234,50"]
    assert payload["results"][0]["fecha_trx"] == "05/10/2026"


def test_por_centro_paginates_by_fifty_with_native_fallback(actor):
    archivo = _archivo(actor)
    centro = _centro()
    for fila in range(1, 53):
        _registro(archivo, fila, centro=centro)
    client = _client(actor)
    url = f"/api/web/cdf/centros/{centro.pk}/informecabal/{archivo.pk}/"

    first = client.get(url).json()
    assert (first["page"], first["num_pages"], first["count"]) == (1, 2, 52)
    assert len(first["results"]) == 50
    assert (first["has_previous"], first["has_next"]) == (False, True)
    assert (first["previous_page"], first["next_page"]) == (None, 2)
    second = client.get(url + "?page=2").json()
    assert len(second["results"]) == 2
    assert second["results"][0]["numero"] == 1
    assert client.get(url + "?page=zz").json()["page"] == 1


def test_por_centro_without_rows_is_empty(actor):
    archivo = _archivo(actor)
    centro = _centro()

    payload = (
        _client(actor)
        .get(f"/api/web/cdf/centros/{centro.pk}/informecabal/{archivo.pk}/")
        .json()
    )

    assert payload["results"] == []
    assert payload["count"] == 0
