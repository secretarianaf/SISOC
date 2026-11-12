"""Web API of the comunicado create and edit form and its recipients panel (CM02.02)."""

import json

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from comedores.models import Comedor
from comunicados.models import (
    Comunicado,
    ComunicadoAdjunto,
    EstadoComunicado,
    SubtipoComunicado,
    TipoComunicado,
)
from duplas.models import Dupla

CREAR = "/api/web/comedores/comunicados/crear/"
EDITAR = "/api/web/comedores/comunicados/{}/editar/"
BUSCAR = "/api/web/comedores/comunicados/destinatarios/{}/buscar/"
TODOS = "/api/web/comedores/comunicados/destinatarios/{}/todos/"
GESTION = "/api/web/comedores/comunicados/gestion/"

pytestmark = pytest.mark.django_db


def _user(username, *codes, **flags):
    user = User.objects.create_user(username=username, **flags)
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                codename=codename,
                content_type=ContentType.objects.get_for_model(User),
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        user.user_permissions.add(permiso)
    return user


def _client(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


def _datos(**campos):
    return {
        "titulo": "Aviso nuevo",
        "cuerpo": "Texto del aviso",
        "tipo": TipoComunicado.INTERNO,
        "subtipo": "",
        "comedores": "",
        "organizaciones": "",
        "fecha_vencimiento": "",
        "adjuntos-TOTAL_FORMS": "1",
        "adjuntos-INITIAL_FORMS": "0",
        "adjuntos-MIN_NUM_FORMS": "0",
        "adjuntos-MAX_NUM_FORMS": "1000",
        **campos,
    }


@pytest.fixture(name="admin")
def admin_fixture():
    return _user("admin_cm0202f", is_superuser=True)


@pytest.fixture(name="creador")
def creador_fixture():
    return User.objects.create_user(
        "autor_cm0202f", first_name="Ana", last_name="Pérez"
    )


def _borrador(creador, **campos):
    return Comunicado.objects.create(
        titulo="Borrador",
        cuerpo="Texto",
        estado=EstadoComunicado.BORRADOR,
        usuario_creador=creador,
        **{"tipo": TipoComunicado.INTERNO, **campos},
    )


def test_create_form_metadata_for_admin(admin):
    datos = _client(admin).get(CREAR).json()

    assert datos["title"] == "Crear Comunicado"
    assert (datos["is_edit"], datos["es_tecnico"], datos["info"]) == (
        False,
        False,
        None,
    )
    assert [c["value"] for c in datos["fields"]["tipo"]["choices"]] == [
        "interno",
        "externo",
    ]
    # Django drops ``required`` from a select whose first choice is not blank.
    assert datos["fields"]["tipo"]["required"] is False
    assert datos["fields"]["titulo"]["required"] is True
    assert datos["fields"]["titulo"]["max_length"] == 255
    assert datos["fields"]["destacado"]["hidden"] is False
    assert datos["formset"]["prefix"] == "adjuntos"
    assert datos["formset"]["management"]["TOTAL_FORMS"] == "1"
    assert datos["formset"]["existing"] == []
    assert datos["extensiones"] == [".pdf", ".jpg", ".jpeg", ".png"]
    assert datos["max_adjunto_bytes"] == 10 * 1024 * 1024
    assert set(datos["filters_config"]) >= {"comedores", "organizaciones"}
    assert datos["messages"] == []


def test_technician_gets_limited_choices_and_hidden_highlight():
    tecnico = _user(
        "tecnico_cm0202f", "comunicados.add_comunicado", "auth.role_tecnico_comedor"
    )

    datos = _client(tecnico).get(CREAR).json()

    assert datos["es_tecnico"] is True
    assert [c["value"] for c in datos["fields"]["tipo"]["choices"]] == ["externo"]
    assert [c["value"] for c in datos["fields"]["subtipo"]["choices"]] == [
        "comedores",
        "organizaciones",
    ]
    assert datos["fields"]["destacado"]["hidden"] is True


@pytest.mark.parametrize("metodo", ["get", "post"])
def test_create_without_permission_403_and_anonymous_401(metodo):
    lector = _user("lector_cm0202f")

    respuesta = getattr(_client(lector), metodo)(CREAR)
    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": "No tiene permisos para crear comunicados."}
    assert getattr(Client(), metodo)(CREAR).status_code == 401


def test_create_saves_draft_creator_and_attachment_and_queues_the_message(admin):
    client = _client(admin)
    archivo = SimpleUploadedFile(
        "guia.pdf", b"%PDF-1.4 x", content_type="application/pdf"
    )

    respuesta = client.post(CREAR, _datos(archivos_adjuntos=archivo, destacado="on"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/comunicados/gestion/"}
    com = Comunicado.objects.get(titulo="Aviso nuevo")
    assert (com.estado, com.usuario_creador, com.destacado) == (
        EstadoComunicado.BORRADOR,
        admin,
        True,
    )
    assert list(com.adjuntos.values_list("nombre_original", flat=True)) == ["guia.pdf"]
    assert client.get(GESTION).json()["messages"] == [
        {"message": "Comunicado creado correctamente.", "level": "success"}
    ]


def test_create_rejects_with_400_errors_and_echoes_the_bound_values(admin):
    respuesta = _client(admin).post(
        CREAR,
        _datos(titulo="", cuerpo="", tipo=TipoComunicado.EXTERNO, subtipo="comedores"),
    )

    assert respuesta.status_code == 400
    campos = respuesta.json()["fields"]
    assert campos["titulo"]["errors"] == ["Este campo es requerido."]
    assert campos["cuerpo"]["errors"] == ["Este campo es requerido."]
    assert campos["comedores"]["errors"] == [
        "Debe seleccionar al menos un comedor o marcar 'Enviar a todos los comedores'."
    ]
    assert campos["tipo"]["value"] == "externo"
    assert not Comunicado.objects.exists()


@pytest.mark.parametrize(
    "nombre,contenido,mensaje",
    [
        ("virus.exe", b"x", "El archivo 'virus.exe' tiene una extensión no permitida."),
        (
            "grande.pdf",
            b"x" * (10 * 1024 * 1024 + 1),
            "El archivo 'grande.pdf' supera el tamaño máximo de 10 MB.",
        ),
    ],
)
def test_attachment_validations_keep_native_messages(admin, nombre, contenido, mensaje):
    archivo = SimpleUploadedFile(nombre, contenido)

    respuesta = _client(admin).post(CREAR, _datos(archivos_adjuntos=archivo))

    assert respuesta.status_code == 400
    # The native template does not print this error: it is projected, not drawn.
    assert respuesta.json()["attachment_errors"] == [mensaje]
    assert not Comunicado.objects.exists()


def test_external_to_comedores_saves_the_csv_selection_and_scope_checks_apply(admin):
    uno = Comedor.objects.create(nombre="Comedor uno")
    dos = Comedor.objects.create(nombre="Comedor dos")

    respuesta = _client(admin).post(
        CREAR,
        _datos(
            tipo=TipoComunicado.EXTERNO,
            subtipo=SubtipoComunicado.COMEDORES,
            comedores=f"{uno.pk},{dos.pk}",
        ),
    )

    assert respuesta.status_code == 200
    com = Comunicado.objects.get(titulo="Aviso nuevo")
    assert set(com.comedores.values_list("pk", flat=True)) == {uno.pk, dos.pk}
    assert com.organizaciones.count() == 0


def test_technician_editor_cannot_target_a_comedor_out_of_scope(creador):
    tecnico = _user(
        "tecnico2_cm0202f", "comunicados.change_comunicado", "auth.role_tecnico_comedor"
    )
    dupla = Dupla.objects.create(
        nombre="Dupla CM0202",
        estado="Activo",
        abogado=User.objects.create_user("abogado_cm0202f"),
    )
    dupla.tecnico.add(tecnico)
    propio = Comedor.objects.create(nombre="Comedor propio", dupla=dupla)
    ajeno = Comedor.objects.create(nombre="Comedor ajeno")
    com = _borrador(creador, tipo=TipoComunicado.EXTERNO)
    Comunicado.objects.filter(pk=com.pk).update(subtipo=SubtipoComunicado.COMEDORES)
    datos = _datos(
        tipo=TipoComunicado.EXTERNO,
        subtipo=SubtipoComunicado.COMEDORES,
        **{"adjuntos-TOTAL_FORMS": "1"},
    )

    rechazado = _client(tecnico).post(
        EDITAR.format(com.pk), {**datos, "comedores": str(ajeno.pk)}
    )
    aceptado = _client(tecnico).post(
        EDITAR.format(com.pk), {**datos, "comedores": str(propio.pk)}
    )

    assert rechazado.status_code == 400
    assert rechazado.json()["fields"]["comedores"]["errors"]
    assert aceptado.status_code == 200
    assert list(com.comedores.values_list("pk", flat=True)) == [propio.pk]


def test_post_format_must_be_form_data_and_csrf_is_required(admin):
    cuerpo = json.dumps(_datos())

    json_post = _client(admin).post(CREAR, cuerpo, content_type="application/json")
    sin_csrf = _client(admin, enforce_csrf_checks=True).post(CREAR, _datos())

    assert json_post.status_code == 415
    assert sin_csrf.status_code == 403
    assert not Comunicado.objects.exists()


def test_edit_form_metadata_with_current_values_attachments_and_info(admin, creador):
    com = _borrador(creador, destacado=True)
    ComunicadoAdjunto.objects.create(
        comunicado=com,
        archivo=SimpleUploadedFile("a.pdf", b"x"),
        nombre_original="a.pdf",
    )

    datos = _client(admin).get(EDITAR.format(com.pk)).json()

    assert datos["title"] == "Editar Comunicado"
    assert datos["fields"]["titulo"]["value"] == "Borrador"
    assert datos["fields"]["destacado"]["value"] is True
    assert datos["formset"]["management"]["INITIAL_FORMS"] == "1"
    [adjunto] = datos["formset"]["existing"]
    assert adjunto["nombre_original"] == "a.pdf"
    assert adjunto["delete"]["name"] == "adjuntos-0-DELETE"
    assert {h["name"] for h in adjunto["hidden"]} == {
        "adjuntos-0-id",
        "adjuntos-0-comunicado",
    }
    assert datos["info"]["estado_label"] == "Borrador"
    assert datos["info"]["creador"] == "Ana Pérez"


def test_edit_updates_modifier_and_removes_a_marked_attachment(admin, creador):
    com = _borrador(creador)
    adjunto = ComunicadoAdjunto.objects.create(
        comunicado=com,
        archivo=SimpleUploadedFile("a.pdf", b"x"),
        nombre_original="a.pdf",
    )
    client = _client(admin)

    respuesta = client.post(
        EDITAR.format(com.pk),
        _datos(
            titulo="Editado",
            **{
                "adjuntos-TOTAL_FORMS": "2",
                "adjuntos-INITIAL_FORMS": "1",
                "adjuntos-0-id": str(adjunto.pk),
                "adjuntos-0-comunicado": str(com.pk),
                "adjuntos-0-DELETE": "on",
            },
        ),
    )

    assert respuesta.status_code == 200
    com.refresh_from_db()
    assert (com.titulo, com.usuario_ultima_modificacion) == ("Editado", admin)
    assert com.adjuntos.count() == 0
    assert client.get(GESTION).json()["messages"] == [
        {"message": "Comunicado actualizado correctamente.", "level": "success"}
    ]


def test_edit_permissions_and_unknown_id(admin, creador):
    editor = _user("editor_cm0202f", "comunicados.change_comunicado")
    publicado = _borrador(creador)
    Comunicado.objects.filter(pk=publicado.pk).update(estado=EstadoComunicado.PUBLICADO)
    mensaje = {"detail": "No tiene permisos para editar este comunicado."}

    for metodo in ("get", "post"):
        respuesta = getattr(_client(editor), metodo)(EDITAR.format(publicado.pk))
        assert respuesta.status_code == 403
        assert respuesta.json() == mensaje
        assert getattr(_client(admin), metodo)(EDITAR.format(999999)).status_code == 404
    assert _client(admin).get(EDITAR.format(publicado.pk)).status_code == 200
    assert Client().get(EDITAR.format(publicado.pk)).status_code == 401


def test_recipients_endpoints_return_the_native_json_and_guards(admin):
    Comedor.objects.create(nombre="Comedor buscado")
    client = _client(admin)

    buscar = client.get(
        BUSCAR.format("comedores"), {"filters": '{"logic":"AND","items":[]}'}
    )
    todos = client.get(TODOS.format("comedores"))
    nativo = client.get(
        "/comunicados/destinatarios/comedores/buscar/",
        {"filters": '{"logic":"AND","items":[]}'},
    )

    assert buscar.status_code == 200
    assert buscar.json() == nativo.json()
    assert buscar.json()["results"][0]["nombre"] == "Comedor buscado"
    assert todos.json()["truncado"] is False
    desconocido = client.get(BUSCAR.format("otros"))
    assert (desconocido.status_code, desconocido.json()) == (
        404,
        {"error": "Universo desconocido."},
    )
    lector = _client(_user("lector2_cm0202f"))
    assert lector.get(BUSCAR.format("comedores")).status_code == 403
    assert Client().get(TODOS.format("comedores")).status_code == 401


def test_native_create_still_redirects(admin):
    respuesta = _client(admin).post("/comunicados/crear/", _datos(titulo="Nativo"))

    assert respuesta.status_code == 302
    assert respuesta["Location"] == "/comunicados/gestion/"
