"""Local React preview entries of the CDF activity screens (``centrodefamilia.web_preview_actividades``)."""

import types

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from centrodefamilia.models import (
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
    ParticipanteActividad,
)
from centrodefamilia.web_preview_actividades import cdf_actividades_preview_patterns
from ciudadanos.models import Ciudadano
from config.urls_all import urlpatterns as monolith_patterns

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _client(*, view=True, superuser=False):
    user = User.objects.create_user("preview_actividades")
    if superuser:
        user.is_superuser = True
        user.save()
    if view:
        user.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Centro),
                codename="view_centro",
            )
        )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="actividad")
def actividad_fixture():
    centro = Centro.objects.create(
        nombre="Centro Preview",
        tipo="faro",
        codigo="PREV-A",
        domicilio_actividad="Domicilio",
        telefono="1",
        celular="2",
        correo="c@example.com",
        nombre_referente="R",
        apellido_referente="E",
        telefono_referente="3",
        correo_referente="r@example.com",
    )
    base = Actividad.objects.create(
        nombre="Taller", categoria=Categoria.objects.create(nombre="Arte")
    )
    return ActividadCentro.objects.create(
        centro=centro, actividad=base, cantidad_personas=3, horariosdesde="09:00"
    )


@pytest.fixture(name="preview_urls")
def preview_urls_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("cdf_actividades_preview_test_urls")
    module.urlpatterns = cdf_actividades_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    return module


def _participante(actividad):
    ciudadano = Ciudadano.objects.create(
        nombre="Ana", apellido="Paz", documento=30111222
    )
    return ParticipanteActividad.objects.create(
        actividad_centro=actividad, ciudadano=ciudadano
    )


def _get(client, urlconf, url, method="get"):
    with override_settings(ROOT_URLCONF=urlconf):
        return getattr(client, method)(url)


def test_entries_serve_the_frozen_index_with_rewritten_assets(actividad, preview_urls):
    participante = _participante(actividad)
    base = f"/centrodefamilia/centros/{actividad.centro_id}/actividades/{actividad.pk}"

    for url in (
        f"/centrodefamilia/centros/actividades/{actividad.pk}/detalle/",
        f"{base}/participantes/crear/",
        f"{base}/participantes/{participante.pk}/eliminar/",
        f"/centrodefamilia/centros/actividades/{actividad.pk}/asistencia/",
        "/centrodefamilia/actividades/",
        "/centrodefamilia/actividades/nueva/",
        f"/centrodefamilia/centros/{actividad.centro_id}/actividades/nueva/",
        f"/centrodefamilia/centros/actividades/{actividad.pk}/editar/",
    ):
        client = _client(superuser=True)
        respuesta = _get(client, preview_urls, url)
        head = _get(client, preview_urls, url, "head")

        assert respuesta.status_code == 200, url
        assert '/centrodefamilia/react/assets/app-1.js"' in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        assert "csrftoken" in respuesta.cookies
        assert head.content == b""
        User.objects.all().delete()


def test_native_guards_and_object_rule_decide_exactly_as_the_native_pages(
    actividad, preview_urls
):
    base = f"/centrodefamilia/centros/{actividad.centro_id}/actividades/{actividad.pk}"
    urls = (
        f"/centrodefamilia/centros/actividades/{actividad.pk}/detalle/",
        f"{base}/participantes/crear/",
        f"{base}/participantes/999999/eliminar/",
        "/centrodefamilia/actividades/",
        "/centrodefamilia/actividades/nueva/",
        f"/centrodefamilia/centros/{actividad.centro_id}/actividades/nueva/",
        f"/centrodefamilia/centros/actividades/{actividad.pk}/editar/",
    )

    anonimo_nativo = Client().get(urls[0]).status_code
    assert _get(Client(), preview_urls, urls[0]).status_code == anonimo_nativo
    for url in urls:
        assert _get(_client(view=False), preview_urls, url).status_code == 403, url
        User.objects.all().delete()
    assert (
        _get(
            _client(),
            preview_urls,
            "/centrodefamilia/centros/actividades/999999/detalle/",
        ).status_code
        == 404
    )
    User.objects.all().delete()
    assert _get(_client(), preview_urls, urls[2]).status_code == 404
    User.objects.all().delete()
    asistencia = f"/centrodefamilia/centros/actividades/{actividad.pk}/asistencia/"
    assert _get(_client(), preview_urls, asistencia).status_code == 403
    User.objects.all().delete()
    assert (
        _get(
            _client(superuser=True),
            preview_urls,
            "/centrodefamilia/centros/actividades/999999/asistencia/",
        ).status_code
        == 404
    )
    assert _get(Client(), preview_urls, urls[2]).status_code == anonimo_nativo


def test_assets_are_frozen_and_nothing_else_is_served(preview_urls):
    client = Client()

    assert (
        _get(client, preview_urls, "/centrodefamilia/react/assets/app-1.js").status_code
        == 200
    )
    assert (
        _get(
            client, preview_urls, "/centrodefamilia/react/assets/missing.js"
        ).status_code
        == 404
    )
