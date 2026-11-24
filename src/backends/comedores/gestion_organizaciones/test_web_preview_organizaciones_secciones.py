"""Local React preview entries of O01-O04 (``gestion_organizaciones.web_preview``).

Each entry keeps its native URL, route decorator and lookup; only then the
frozen ``index.html`` is served. The native POSTs of these URLs do not exist
here: React saves through ``/api/web/comedores/organizaciones/``.
"""

import types

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, override_settings

from comedores.models import Comedor, Programas
from config.urls_all import urlpatterns as monolith_patterns
from duplas.models import Dupla
from gestion_organizaciones.models import Firmante, LineaProyecto
from gestion_organizaciones.web_preview import organizaciones_preview_patterns
from organizaciones.models import (
    Aval,
    DocumentacionOrganizacion,
    Organizacion,
    ProyectoOrganizacion,
)
from rendicioncuentasmensual.models import RendicionCuentaMensual

INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)
ASSET = '/organizaciones/react/assets/app-1.js"'

pytestmark = pytest.mark.django_db


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("organizaciones_secciones_preview_test_urls")
    module.urlpatterns = organizaciones_preview_patterns(tmp_path) + list(
        monolith_patterns
    )
    with override_settings(ROOT_URLCONF=module):
        yield


def _login(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    client = Client()
    client.force_login(usuario)
    return client


def _proyecto(linea=True):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=Organizacion.objects.create(nombre="Preview"), codigo="P-1"
    )
    if linea:
        LineaProyecto.objects.create(
            proyecto=proyecto,
            programa=Programas.objects.create(
                nombre="Abordaje comunitario - Línea Secos"
            ),
        )
    return proyecto


@pytest.mark.usefixtures("preview")
def test_the_convenio_gets_the_frozen_index_with_the_native_guards_and_lookup():
    proyecto = _proyecto()
    url = f"/organizaciones/proyectos/{proyecto.pk}/convenio/"
    lector = _login("conv_prev", "organizaciones.view_organizacion")

    assert Client().get(url).status_code == 403
    assert (
        _login("conv_prev_tec", "auth.role_tecnico_comedor").get(url).status_code == 403
    )
    respuesta = lector.get(url)
    assert respuesta.status_code == 200
    assert ASSET in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert lector.post(url).status_code == 405
    assert lector.get("/organizaciones/proyectos/999999/convenio/").status_code == 404


@pytest.mark.usefixtures("preview")
def test_the_convenio_without_line_redirects_like_the_native_view():
    proyecto = _proyecto(linea=False)
    lector = _login("conv_prev_sin", "organizaciones.view_organizacion")

    respuesta = lector.get(f"/organizaciones/proyectos/{proyecto.pk}/convenio/")

    assert respuesta.status_code == 302
    assert respuesta.url == f"/organizaciones/editar/{proyecto.organizacion_id}"


@pytest.mark.usefixtures("preview")
def test_the_history_keeps_the_native_guards_and_the_dupla_lookup():
    organizacion = Organizacion.objects.create(nombre="Hist")
    ajena = Organizacion.objects.create(nombre="Hist ajena")
    documento = DocumentacionOrganizacion.objects.create(
        nombre="Estatuto", categoria=DocumentacionOrganizacion.CATEGORIA_PERSONERIA
    )
    tecnico = get_user_model().objects.create_user("hist_prev_tec")
    abogado = get_user_model().objects.create_user("hist_prev_abo")
    dupla = Dupla.objects.create(nombre="D", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    url = f"/organizaciones/{organizacion.pk}/documentacion/{documento.pk}/historial/"
    limitado = _login("hist_prev_lim", "auth.role_tecnico_comedor")
    limitado.force_login(tecnico)
    tecnico.user_permissions.add(
        Permission.objects.get(codename="role_tecnico_comedor")
    )

    assert Client().get(url).status_code == 403
    assert _login("hist_prev_sin").get(url).status_code == 403
    respuesta = limitado.get(url)
    assert respuesta.status_code == 200
    assert ASSET in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert (
        limitado.get(
            f"/organizaciones/{ajena.pk}/documentacion/{documento.pk}/historial/"
        ).status_code
        == 404
    )
    assert (
        limitado.get(
            f"/organizaciones/{organizacion.pk}/documentacion/999999/historial/"
        ).status_code
        == 404
    )
    assert limitado.post(url).status_code == 405


@pytest.mark.usefixtures("preview")
def test_the_signers_and_avales_entries_keep_the_native_guards_and_lookups():
    organizacion = Organizacion.objects.create(nombre="Firmantes preview")
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Ana")
    aval = Aval.objects.create(organizacion=organizacion, nombre="Beto")
    paths = (
        f"/organizaciones/firmante/crear/{organizacion.pk}",
        f"/organizaciones/firmante/editar/{firmante.pk}",
        f"/organizaciones/firmante/eliminar/{firmante.pk}",
        f"/organizaciones/aval/crear/{organizacion.pk}",
        f"/organizaciones/aval/editar/{aval.pk}",
        f"/organizaciones/aval/eliminar/{aval.pk}",
    )
    lector = _login("firm_prev", "organizaciones.view_organizacion")
    tecnico = _login("firm_prev_tec", "auth.role_tecnico_comedor")

    for path in paths:
        assert Client().get(path).status_code == 403
        assert tecnico.get(path).status_code == 403
        respuesta = lector.get(path)
        assert respuesta.status_code == 200
        assert ASSET in respuesta.content.decode()
        assert "no-store" in respuesta["Cache-Control"]
        # React saves through the web API: the entry has no native POST.
        assert lector.post(path).status_code == 405
    for ruta in (
        "firmante/editar",
        "firmante/eliminar",
        "aval/editar",
        "aval/eliminar",
    ):
        assert lector.get(f"/organizaciones/{ruta}/999999").status_code == 404
    # The native alta does not look the organization up either.
    assert lector.get("/organizaciones/firmante/crear/999999").status_code == 200


@pytest.mark.usefixtures("preview")
def test_the_rendicion_detail_keeps_the_native_queryset_and_guards():
    organizacion = Organizacion.objects.create(nombre="Rend preview")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="P-1"
    )
    rendicion = RendicionCuentaMensual.objects.create(
        mes=1, anio=2026, proyecto=proyecto
    )
    ajena = Organizacion.objects.create(nombre="Rend ajena")
    url = f"/organizaciones/{organizacion.pk}/rendiciones/{rendicion.pk}/detalle/"
    lector = _login("rend_prev", "organizaciones.view_organizacion")

    assert Client().get(url).status_code == 403
    assert _login("rend_prev_sin").get(url).status_code == 403
    respuesta = lector.get(url)
    assert respuesta.status_code == 200
    assert ASSET in respuesta.content.decode()
    assert "no-store" in respuesta["Cache-Control"]
    assert lector.post(url).status_code == 405
    assert (
        lector.get(
            f"/organizaciones/{ajena.pk}/rendiciones/{rendicion.pk}/detalle/"
        ).status_code
        == 404
    )
    assert (
        lector.get(
            f"/organizaciones/{organizacion.pk}/rendiciones/999999/detalle/"
        ).status_code
        == 404
    )
