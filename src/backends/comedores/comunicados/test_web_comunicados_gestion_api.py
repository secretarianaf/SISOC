"""Web API of the comunicados management list and manager detail (CM02.01)."""

from datetime import timedelta

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.utils import timezone

from comunicados.models import Comunicado, EstadoComunicado, TipoComunicado

# Other domains' models are resolved through the app registry, as the
# import contract forbids importing their internals (.importlinter).
Comedor = apps.get_model("comedores", "Comedor")
Dupla = apps.get_model("duplas", "Dupla")

GESTION = "/api/web/comedores/comunicados/gestion/"
DETALLE = "/api/web/comedores/comunicados/{}/"

pytestmark = pytest.mark.django_db


def _perm(user, code):
    app, codename = code.split(".")
    if app == "auth":
        permiso = Permission.objects.get_or_create(
            codename=codename,
            content_type=ContentType.objects.get_for_model(User),
            defaults={"name": codename},
        )[0]
    else:
        permiso = Permission.objects.get(content_type__app_label=app, codename=codename)
    user.user_permissions.add(permiso)


def _user(username, *codes, **flags):
    user = User.objects.create_user(username=username, **flags)
    for code in codes:
        _perm(user, code)
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


def _com(creador, titulo="Aviso", **campos):
    datos = {
        "cuerpo": "Texto",
        "estado": EstadoComunicado.BORRADOR,
        "tipo": TipoComunicado.INTERNO,
        **campos,
    }
    if datos["estado"] == EstadoComunicado.PUBLICADO:
        datos.setdefault("fecha_publicacion", timezone.now())
    return Comunicado.objects.create(titulo=titulo, usuario_creador=creador, **datos)


@pytest.fixture(name="creador")
def creador_fixture():
    return User.objects.create_user("autor_cm02", first_name="Ana", last_name="Pérez")


def _ids(respuesta):
    return [fila["id"] for fila in respuesta.json()["results"]]


def test_anonymous_401_and_reader_403_with_native_message():
    assert Client().get(GESTION).status_code == 401
    respuesta = _client(_user("lector_cm02")).get(GESTION)

    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detail": "No tiene permisos para gestionar comunicados."
    }


def test_admin_sees_everything_with_row_fields_and_actions(creador):
    creado = timezone.make_aware(timezone.datetime(2026, 3, 4, 23, 30))
    borrador = _com(creador, "uno dos tres cuatro cinco seis siete ocho nueve")
    Comunicado.objects.filter(pk=borrador.pk).update(fecha_creacion=creado)
    publicado = _com(creador, "Pub", estado=EstadoComunicado.PUBLICADO)
    externo = _com(
        creador, "Ext", estado=EstadoComunicado.PUBLICADO, tipo=TipoComunicado.EXTERNO
    )
    vencido = _com(
        creador,
        "Venc",
        estado=EstadoComunicado.PUBLICADO,
        fecha_vencimiento=timezone.now() - timedelta(days=1),
    )
    archivado = _com(creador, "Arch", estado=EstadoComunicado.ARCHIVADO)
    admin = _client(_user("admin_cm02", "auth.role_admin"))

    datos = admin.get(GESTION).json()

    assert _ids(admin.get(GESTION)) == [
        archivado.pk,
        vencido.pk,
        externo.pk,
        publicado.pk,
        borrador.pk,
    ]
    filas = {f["id"]: f for f in datos["results"]}
    assert filas[borrador.pk] == {
        "id": borrador.pk,
        "titulo": "uno dos tres cuatro cinco seis siete ocho nueve",
        "titulo_corto": "uno dos tres cuatro cinco seis siete ocho …",
        "tipo": "interno",
        "estado": "borrador",
        "esta_vencido": False,
        "destacado": False,
        "fecha_creacion": timezone.localtime(creado).strftime("%d/%m/%Y"),
        "fecha_publicacion": "",
        "creador": "Ana Pérez",
        "acciones": {
            "editar": True,
            "publicar": True,
            "archivar": False,
            "destacado": False,
        },
    }
    assert filas[publicado.pk]["acciones"] == {
        "editar": False,
        "publicar": False,
        "archivar": True,
        "destacado": True,
    }
    assert filas[externo.pk]["acciones"]["destacado"] is False
    assert filas[vencido.pk]["esta_vencido"] is True
    assert not any(filas[archivado.pk]["acciones"].values())
    assert datos["flags"] == {"can_create": True, "is_admin": True, "es_tecnico": False}
    assert datos["mailing_url"] == "/comunicados/mailing/"
    assert datos["filtros"] == {"titulo": "", "estado": "", "tipo": ""}


def test_creator_without_edit_gets_no_row_actions_and_no_mailing(creador):
    _com(creador)
    gestor = _client(_user("gestor_add_cm02", "comunicados.add_comunicado"))

    datos = gestor.get(GESTION).json()

    assert datos["results"][0]["acciones"] == {
        "editar": False,
        "publicar": False,
        "archivar": False,
        "destacado": False,
    }
    assert datos["flags"] == {
        "can_create": True,
        "is_admin": False,
        "es_tecnico": False,
    }
    assert datos["mailing_url"] is None


def test_filters_are_exact_and_unvalidated(creador):
    _com(creador, "Alfa")
    publicado = _com(creador, "Alfa publicado", estado=EstadoComunicado.PUBLICADO)
    _com(creador, "Beta", estado=EstadoComunicado.PUBLICADO)
    editor = _client(_user("editor_cm02", "comunicados.change_comunicado"))

    respuesta = editor.get(
        GESTION, {"titulo": "alfa", "estado": "publicado", "tipo": "interno"}
    )

    assert _ids(respuesta) == [publicado.pk]
    assert respuesta.json()["filtros"] == {
        "titulo": "alfa",
        "estado": "publicado",
        "tipo": "interno",
    }
    assert _ids(editor.get(GESTION, {"estado": "otro"})) == []
    assert editor.get(GESTION, {"page": "9"}).status_code == 404


def test_technician_sees_only_external_ones_of_its_scope(creador):
    tecnico = _user(
        "tecnico_cm02", "comunicados.change_comunicado", "auth.role_tecnico_comedor"
    )
    dupla = Dupla.objects.create(
        nombre="Dupla CM02",
        estado="Activo",
        abogado=User.objects.create_user("abogado_cm02"),
    )
    dupla.tecnico.add(tecnico)
    suyo = Comedor.objects.create(nombre="Comedor propio", dupla=dupla)
    ajeno = Comedor.objects.create(nombre="Comedor ajeno")
    visible = _com(creador, "Suyo", tipo=TipoComunicado.EXTERNO)
    visible.comedores.add(suyo, suyo)
    _com(creador, "Ajeno", tipo=TipoComunicado.EXTERNO).comedores.add(ajeno)
    interno = _com(creador, "Interno")
    cliente = _client(tecnico)

    datos = cliente.get(GESTION).json()

    assert [f["id"] for f in datos["results"]] == [visible.pk]
    assert datos["flags"]["es_tecnico"] is True
    # Kept asymmetry: the manager detail does not apply the scope.
    assert cliente.get(DETALLE.format(interno.pk)).status_code == 200


def test_manager_detail_has_footer_data(creador):
    editor_user = _user("editor2_cm02", "comunicados.change_comunicado")
    borrador = _com(creador, usuario_ultima_modificacion=editor_user)
    editor = _client(editor_user)

    datos = editor.get(DETALLE.format(borrador.pk)).json()

    assert datos["estado"] == "borrador"
    assert datos["fecha_creacion"] == timezone.localtime(
        borrador.fecha_creacion
    ).strftime("%d/%m/%Y %H:%M")
    assert datos["modificado_por"] == "editor2_cm02"
    assert datos["can_manage"] is True
    assert datos["permisos"] == {
        "editar": True,
        "publicar": True,
        "archivar": True,
        "eliminar": False,
    }
    admin = _client(_user("admin2_cm02", is_superuser=True))
    assert admin.get(DETALLE.format(borrador.pk)).json()["permisos"]["eliminar"]


def test_gestion_reads_do_not_write(creador):
    _com(creador)
    antes = list(Comunicado.objects.values())
    editor = _client(_user("editor3_cm02", "comunicados.change_comunicado"))

    assert editor.get(GESTION).status_code == 200
    assert editor.head(GESTION).status_code == 200
    assert editor.post(GESTION).status_code == 405
    assert list(Comunicado.objects.values()) == antes
