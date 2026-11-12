"""Web API (G1 v1) of the Organizaciones legajo (O05.01).

``/api/web/comedores/organizaciones/<pk>/`` runs the native
``OrganizacionDetailView`` and returns the ``content`` block of
``organizacion_detail.html``. The tests compare that fragment with the native
HTML page ``/organizaciones/detalle/<pk>`` and pin today's access: any of
``ORGANIZACION_DOCUMENTACION_PERMS`` and the dupla scope (404 outside it).
"""

import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from organizaciones.models import Organizacion, SubtipoEntidad, TipoEntidad

VIEW = "organizaciones.view_organizacion"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
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
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


def _organizacion():
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    sub = SubtipoEntidad.objects.create(nombre="Mutual", tipo_entidad=tipo)
    return Organizacion.objects.create(
        nombre="Legajo Sintético",
        cuit=20111111112,
        telefono=1140000000,
        email="legajo@ejemplo.org",
        tipo_entidad=tipo,
        subtipo_entidad=sub,
    )


def _api(organizacion):
    return f"/api/web/comedores/organizaciones/{organizacion.pk}/"


def _normal(texto):
    """Whitespace-insensitive text; the CSRF token is masked anew on every render."""
    texto = re.sub(r'data-csrf-token="[^"]*"', 'data-csrf-token="T"', texto)
    return " ".join(texto.split())


MARCADOR = re.compile(r'<div data-legajo-seccion="\d+"></div>')


def _es_el_bloque_nativo(fragmento, pagina):
    """The fragment is the native block, but for the sections React draws itself.

    Every piece of HTML around the section placeholders is in the native page,
    in order; the placeholders stand where the native partial was.
    """
    nativa, posicion = _normal(pagina), 0
    for trozo in MARCADOR.split(fragmento):
        trozo = _normal(trozo)
        encontrado = nativa.find(trozo, posicion) if trozo else posicion
        assert encontrado >= 0, trozo[:120]
        posicion = encontrado + len(trozo)


def test_fragment_is_the_native_content_block():
    organizacion = _organizacion()
    web = _client(_usuario("lector_leg", VIEW))

    data = web.get(_api(organizacion)).json()
    nativa = web.get(f"/organizaciones/detalle/{organizacion.pk}")

    assert nativa.status_code == 200
    assert data["title"] == "Organización: Legajo Sintético"
    _es_el_bloque_nativo(data["html"], nativa.content.decode())
    for texto in (
        "Legajo Sintético",
        "CUIT: 20111111112",
        "Datos de la Organización",
        "Sin programas",
        'href="/organizaciones/editar/%d"' % organizacion.pk,
    ):
        assert texto in data["html"]
    # The documentation table is a React section: no native script is needed.
    assert data["scripts"] == []
    assert "documentos" in [s["kind"] for s in data["sections"]]
    assert data["messages"] == []


def test_program_and_section_parameters_reach_the_native_view():
    organizacion = _organizacion()
    web = _client(_usuario("lector_par", VIEW))
    consulta = "?programa=999&seccion=rendiciones&proyecto=X"

    data = web.get(_api(organizacion) + consulta).json()
    nativa = web.get(f"/organizaciones/detalle/{organizacion.pk}{consulta}")

    _es_el_bloque_nativo(data["html"], nativa.content.decode())


def test_technicians_see_only_their_dupla_and_no_manage_buttons():
    propia, ajena = _organizacion(), Organizacion.objects.create(nombre="Ajena")
    tecnico = _usuario("tecnico_leg", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("abogado_leg")
    )
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=propia, dupla=dupla)
    web = _client(tecnico)

    respuesta = web.get(_api(propia))

    assert respuesta.status_code == 200
    assert "/organizaciones/editar/" not in respuesta.json()["html"]
    assert web.get(_api(ajena)).status_code == 404
    assert web.get("/api/web/comedores/organizaciones/999999/").status_code == 404


def test_without_the_codes_the_answer_is_403_and_anonymous_401():
    organizacion = _organizacion()

    assert _client(_usuario("sin_leg")).get(_api(organizacion)).status_code == 403
    anonimo = Client().get(_api(organizacion))
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}


def test_pending_messages_are_consumed_like_the_native_page():
    organizacion = _organizacion()
    web = _client(_usuario("lector_msg", VIEW))
    # The native delete of another organization queues a message for this session.
    web.post(f"/organizaciones/eliminar/{Organizacion.objects.create(nombre='B').pk}")

    mensajes = web.get(_api(organizacion)).json()["messages"]

    assert mensajes == [
        {
            "message": "La organización B fue dada de baja correctamente.",
            "level": "success",
        }
    ]
    assert web.get(_api(organizacion)).json()["messages"] == []


def test_read_only_get_without_writes():
    organizacion = _organizacion()
    web = _client(_usuario("lector_ro", VIEW))
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(_api(organizacion)).status_code == 405, metodo
    with CaptureQueriesContext(connection) as consultas:
        assert web.get(_api(organizacion)).status_code == 200
    assert not [
        q["sql"]
        for q in consultas.captured_queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
