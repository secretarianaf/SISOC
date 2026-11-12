"""Web API of the published comunicados (CM03.01, ``comunicados.web_api_views``)."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from comunicados.models import (
    Comunicado,
    ComunicadoAdjunto,
    EstadoComunicado,
    TipoComunicado,
)

LISTADO = "/api/web/comedores/comunicados/"
ADD = "comunicados.add_comunicado"
CHANGE = "comunicados.change_comunicado"

pytestmark = pytest.mark.django_db


def _user(username, perms=()):
    user = User.objects.create_user(username=username, password="x")
    for code in perms:
        app, codename = code.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _comunicado(creador, titulo="Aviso", **campos):
    datos = {
        "cuerpo": "Contenido de prueba",
        "estado": EstadoComunicado.PUBLICADO,
        "tipo": TipoComunicado.INTERNO,
        "fecha_publicacion": timezone.now(),
        **campos,
    }
    return Comunicado.objects.create(titulo=titulo, usuario_creador=creador, **datos)


@pytest.fixture(name="creador")
def creador_fixture():
    return User.objects.create_user(
        username="creador_cm03", first_name="Ana", last_name="Pérez"
    )


@pytest.fixture(name="lector")
def lector_fixture():
    return _client(_user("lector_cm03"))


def _ids(response):
    return [fila["id"] for fila in response.json()["results"]]


def test_anonymous_gets_401_json():
    respuesta = Client().get(LISTADO)

    assert respuesta.status_code == 401
    assert respuesta["Content-Type"] == "application/json"


def test_reader_sees_only_published_internal_current_ones(creador, lector):
    visible = _comunicado(creador, "Visible")
    sin_vencer = _comunicado(
        creador, "Vigente", fecha_vencimiento=timezone.now() + timedelta(days=1)
    )
    ocultos = [
        _comunicado(creador, "Externo", tipo=TipoComunicado.EXTERNO),
        _comunicado(creador, "Borrador", estado=EstadoComunicado.BORRADOR),
        _comunicado(creador, "Archivado", estado=EstadoComunicado.ARCHIVADO),
        _comunicado(
            creador, "Vencido", fecha_vencimiento=timezone.now() - timedelta(days=1)
        ),
    ]

    respuesta = lector.get(LISTADO)

    assert respuesta.status_code == 200
    assert sorted(_ids(respuesta)) == sorted([visible.pk, sin_vencer.pk])
    for oculto in ocultos:
        assert lector.get(f"{LISTADO}{oculto.pk}/").status_code == 404
    assert lector.get(f"{LISTADO}{visible.pk}/").status_code == 200


def test_card_fields_match_the_template(creador, lector):
    publicado = timezone.make_aware(timezone.datetime(2026, 3, 4, 15, 7))
    cuerpo = " ".join(f"p{i}" for i in range(60))
    comunicado = _comunicado(
        creador, "Con datos", cuerpo=cuerpo, fecha_publicacion=publicado
    )
    ComunicadoAdjunto.objects.create(
        comunicado=comunicado,
        archivo=SimpleUploadedFile("a.pdf", b"%PDF-1.4", "application/pdf"),
        nombre_original="a.pdf",
    )

    datos = lector.get(LISTADO).json()

    assert datos["results"] == [
        {
            "id": comunicado.pk,
            "titulo": "Con datos",
            "cuerpo_resumen": " ".join(f"p{i}" for i in range(50)) + " …",
            "destacado": False,
            "fecha_publicacion": timezone.localtime(publicado).strftime(
                "%d/%m/%Y %H:%M"
            ),
            "creador": "Ana Pérez",
            "adjuntos_count": 1,
            "detail_url": f"/comunicados/ver/{comunicado.pk}/",
        }
    ]
    assert datos["filtro_titulo"] == ""
    assert datos["can_manage"] is False
    assert datos["gestion_url"] is None
    assert datos["messages"] == []
    assert datos["page"]["is_paginated"] is False
    assert datos["page"]["count"] == 1


def test_creator_without_full_name_shows_the_username(lector):
    sin_nombre = User.objects.create_user(username="solo_usuario_cm03")
    _comunicado(sin_nombre)

    assert lector.get(LISTADO).json()["results"][0]["creador"] == "solo_usuario_cm03"


def test_title_filter_and_featured_first(creador, lector):
    viejo = timezone.now() - timedelta(days=3)
    normal = _comunicado(creador, "Aviso reciente")
    destacado = _comunicado(
        creador, "Aviso destacado", destacado=True, fecha_publicacion=viejo
    )
    _comunicado(creador, "Otra cosa")

    respuesta = lector.get(LISTADO, {"titulo": "aviso"})

    assert _ids(respuesta) == [destacado.pk, normal.pk]
    assert respuesta.json()["filtro_titulo"] == "aviso"


def test_invalid_page_is_404(creador, lector):
    _comunicado(creador)

    for page in ("9", "x"):
        respuesta = lector.get(LISTADO, {"page": page})
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "Página no válida."}
    assert lector.get(LISTADO, {"page": "last"}).status_code == 200


def test_pagination_keeps_the_query_and_twenty_per_page(creador, lector):
    for i in range(21):
        _comunicado(creador, f"Aviso {i}")

    datos = lector.get(LISTADO, {"titulo": "Aviso", "page": "2"}).json()

    assert len(datos["results"]) == 1
    assert {k: datos["page"][k] for k in ("number", "num_pages", "count")} == {
        "number": 2,
        "num_pages": 2,
        "count": 21,
    }
    assert datos["page"]["previous"] == 1 and datos["page"]["next"] is None
    assert datos["page"]["range"] == [1, 2]
    assert datos["page"]["query_without_page"] == "titulo=Aviso&"


def test_managers_get_the_gestion_button(creador):
    _comunicado(creador)
    gestor = _client(_user("gestor_cm03", perms=[ADD]))

    datos = gestor.get(LISTADO).json()

    assert datos["can_manage"] is True
    assert datos["gestion_url"] == "/comunicados/gestion/"


def test_detail_fields_match_the_template(creador, lector):
    vence = timezone.now() + timedelta(days=2)
    comunicado = _comunicado(
        creador,
        "Detalle",
        cuerpo="Uno\n\nDos",
        destacado=True,
        fecha_vencimiento=vence,
    )
    adjunto = ComunicadoAdjunto.objects.create(
        comunicado=comunicado,
        archivo=SimpleUploadedFile("guia.pdf", b"%PDF-1.4", "application/pdf"),
        nombre_original="guia.pdf",
    )

    datos = lector.get(f"{LISTADO}{comunicado.pk}/").json()

    assert datos == {
        "id": comunicado.pk,
        "titulo": "Detalle",
        "cuerpo": "Uno\n\nDos",
        "estado": "publicado",
        "estado_label": "Publicado",
        "destacado": True,
        "fecha_publicacion": timezone.localtime(comunicado.fecha_publicacion).strftime(
            "%d/%m/%Y %H:%M"
        ),
        "fecha_vencimiento": timezone.localtime(vence).strftime("%d/%m/%Y %H:%M"),
        "esta_vencido": False,
        "creador": "Ana Pérez",
        "fecha_creacion": timezone.localtime(comunicado.fecha_creacion).strftime(
            "%d/%m/%Y %H:%M"
        ),
        "modificado_por": "",
        "adjuntos": [
            {
                "id": adjunto.pk,
                "nombre_original": "guia.pdf",
                "url": adjunto.archivo.url,
            }
        ],
        "can_manage": False,
        "permisos": {
            "editar": False,
            "publicar": False,
            "archivar": False,
            "eliminar": False,
        },
        "messages": [],
    }


def test_missing_detail_is_404(lector):
    respuesta = lector.get(f"{LISTADO}999999/")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "No encontrado."}


def test_manager_detail_is_not_filtered(creador):
    borrador = _comunicado(creador, estado=EstadoComunicado.BORRADOR)
    gestor = _client(_user("gestor2_cm03", perms=[CHANGE]))

    assert gestor.get(f"{LISTADO}{borrador.pk}/").status_code == 200


def test_reads_do_not_write_and_only_get_head(creador, lector):
    comunicado = _comunicado(creador)
    antes = list(Comunicado.objects.values())

    assert lector.head(LISTADO).status_code == 200
    assert lector.head(f"{LISTADO}{comunicado.pk}/").status_code == 200
    with CaptureQueriesContext(connection) as ctx:
        lector.get(LISTADO)
        lector.get(f"{LISTADO}{comunicado.pk}/")
    escrituras = [
        q["sql"]
        for q in ctx.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and "django_session" not in q["sql"]
    ]
    assert escrituras == []
    assert list(Comunicado.objects.values()) == antes
    assert lector.post(LISTADO).status_code == 405
    # SessionAuthentication enforces CSRF before the method check, as in the other G1 APIs.
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(User.objects.get(username="lector_cm03"))
    assert csrf.post(LISTADO).status_code == 403


def test_list_does_not_query_attachments_per_card(creador, lector):
    for idx in range(5):
        comunicado = _comunicado(creador, f"N{idx}")
        ComunicadoAdjunto.objects.create(
            comunicado=comunicado,
            archivo=SimpleUploadedFile(f"x{idx}.pdf", b"%PDF", "application/pdf"),
            nombre_original=f"x{idx}.pdf",
        )

    with CaptureQueriesContext(connection) as ctx:
        respuesta = lector.get(LISTADO)

    assert respuesta.status_code == 200
    adjuntos = [
        q["sql"]
        for q in ctx.captured_queries
        if "comunicados_comunicadoadjunto" in q["sql"].lower()
    ]
    assert len(adjuntos) <= 2


def test_pending_messages_are_consumed_once(creador):
    borrador = _comunicado(creador, estado=EstadoComunicado.BORRADOR)
    gestor = _client(_user("gestor3_cm03", perms=[CHANGE]))
    # The native action redirects and leaves its message queued.
    assert gestor.post(f"/comunicados/publicar/{borrador.pk}/").status_code == 302

    primero = gestor.get(LISTADO).json()["messages"]
    segundo = gestor.get(LISTADO).json()["messages"]

    assert primero == [
        {"message": "Comunicado publicado correctamente.", "level": "success"}
    ]
    assert segundo == []
