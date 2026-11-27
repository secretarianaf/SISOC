"""Búsqueda y alta múltiple de miembros de audiencias de tableros."""

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models.signals import pre_save
from django.test import Client
from django.urls import reverse

from dashboard.models import AudienciaTableros, MiembroAudienciaTableros

pytestmark = pytest.mark.django_db


@pytest.fixture
def datos():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    cliente = Client()
    cliente.force_login(actor)
    return cliente, actor


@pytest.fixture
def audiencia():
    return AudienciaTableros.objects.create(nombre="Equipo A")


def _detalle(audiencia):
    return reverse("dashboard_audiencia_detalle", args=[audiencia.pk])


def _busqueda(audiencia):
    return f"{_detalle(audiencia)}miembros/buscar/"


def _agregar(cliente, audiencia, ids):
    return cliente.post(
        _detalle(audiencia), {"accion": "agregar_miembros", "usuarios": ids}
    )


def test_detalle_muestra_selector_multiple_al_final(datos, audiencia):
    cliente, _ = datos
    respuesta = cliente.get(_detalle(audiencia))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert html.index('id="asignaciones-titulo"') < html.index('id="miembros-titulo"')
    selector = html.split('name="usuarios"', 1)[1].split(">", 1)[0]
    assert "multiple" in selector and "select2" in selector
    assert _busqueda(audiencia) in html


def test_busqueda_limitada_a_nombre_de_usuario_y_sin_miembros_propios(datos, audiencia):
    cliente, _ = datos
    existente = User.objects.create_user(username="encontrar-miembro")
    receptor = User.objects.create_user(
        username="encontrar-receptor", email="privado@example.test", is_active=False
    )
    User.objects.create_user(username="otro", email="encontrar@example.test")
    audiencia.agregar_miembro(existente)
    otra = AudienciaTableros.objects.create(nombre="Equipo B")
    otra.agregar_miembro(receptor)

    assert cliente.get(_busqueda(audiencia)).json() == {"results": []}
    respuesta = cliente.get(_busqueda(audiencia), {"q": " ENCONTRAR "})
    assert respuesta.json() == {
        "results": [{"id": str(receptor.pk), "text": receptor.username}]
    }
    assert "no-store" in respuesta.headers["Cache-Control"]
    assert cliente.head(_busqueda(audiencia), HTTP_X_VIEW="1").status_code == 200
    assert cliente.get(_busqueda(otra), {"q": "receptor"}).json() == {"results": []}
    ausente = reverse("dashboard_audiencia_detalle", args=[99999])
    assert (
        cliente.get(ausente + "miembros/buscar/", {"q": "receptor"}).status_code == 404
    )


def test_busqueda_acota_sugerencias(datos, audiencia):
    cliente, _ = datos
    User.objects.bulk_create([User(username=f"sugerencia-{i:02}") for i in range(26)])
    respuesta = cliente.get(_busqueda(audiencia), {"q": "sugerencia"})
    assert [item["text"] for item in respuesta.json()["results"]] == [
        f"sugerencia-{i:02}" for i in range(25)
    ]
    precisa = cliente.get(_busqueda(audiencia), {"q": "sugerencia-25"})
    assert [item["text"] for item in precisa.json()["results"]] == ["sugerencia-25"]


@pytest.mark.parametrize(
    ("atributos", "estado"),
    [
        ({"is_staff": True}, 403),
        ({"is_staff": True, "is_superuser": True, "is_active": False}, 403),
        ({"is_staff": True, "is_superuser": True}, 200),
        (None, 403),
    ],
)
def test_busqueda_y_alta_exigen_rol(audiencia, atributos, estado):
    cliente = Client(REMOTE_ADDR="203.0.113.42" if atributos is None else "127.0.0.1")
    if atributos is not None:
        cliente.force_login(User.objects.create_user(username="actor", **atributos))
    receptor = User.objects.create_user(username="receptor")
    assert cliente.get(_busqueda(audiencia), {"q": "receptor"}).status_code == estado
    head = cliente.head(_busqueda(audiencia), HTTP_X_VIEW="1")
    assert head.status_code == estado
    assert "X-View" not in head
    assert _agregar(cliente, audiencia, [receptor.pk]).status_code == (
        302 if estado == 200 else estado
    )
    assert audiencia.membresias.filter(usuario=receptor).exists() is (estado == 200)


def test_alta_multiple_conserva_miembros_audita_solo_altas_y_no_modifica_roles(
    datos, audiencia
):
    cliente, actor = datos
    previo = User.objects.create_user(username="previo")
    uno = User.objects.create_user(username="uno")
    dos = User.objects.create_user(username="dos", is_active=False)
    audiencia.agregar_miembro(previo)
    grupo = Group.objects.get(name="Equipo de Datos")
    uno.groups.add(grupo)

    seleccion = [previo.pk, uno.pk, dos.pk, uno.pk]
    assert _agregar(cliente, audiencia, seleccion).url == _detalle(audiencia)
    assert _agregar(cliente, audiencia, seleccion).status_code == 302
    miembros = audiencia.membresias.all()
    assert set(miembros.values_list("usuario_id", flat=True)) == {
        previo.pk,
        uno.pk,
        dos.pk,
    }
    assert set(uno.groups.all()) == {grupo}
    assert not dos.groups.exists()
    assert not dos.user_permissions.exists()
    contenido = ContentType.objects.get_for_model(MiembroAudienciaTableros)
    assert set(
        LogEntry.objects.filter(
            actor=actor, content_type=contenido, action=LogEntry.Action.CREATE
        ).values_list("object_pk", flat=True)
    ) == {str(m.pk) for m in miembros.exclude(usuario=previo)}
    assert (
        LogEntry.objects.filter(
            actor=actor, content_type=contenido, action=LogEntry.Action.CREATE
        ).count()
        == 2
    )


@pytest.mark.parametrize(
    "invalido", [None, "0", "-1", "no-es-id", "99999", "9223372036854775808"]
)
def test_alta_invalida_no_modifica_audiencia(datos, audiencia, invalido):
    cliente, _ = datos
    previo = User.objects.create_user(username="previo")
    audiencia.agregar_miembro(previo)
    valido = User.objects.create_user(username="valido")
    ids = [] if invalido is None else [valido.pk, invalido]

    respuesta = _agregar(cliente, audiencia, ids)
    assert respuesta.status_code == 400
    assert respuesta.context["formulario_miembro"]["usuarios"].errors
    assert set(audiencia.membresias.values_list("usuario_id", flat=True)) == {previo.pk}


def test_alta_multiple_acota_lote_y_exige_csrf(datos, audiencia):
    cliente, actor = datos
    receptor = User.objects.create_user(username="receptor")
    assert _agregar(cliente, audiencia, [receptor.pk] * 101).status_code == 400
    sin_csrf = Client(enforce_csrf_checks=True)
    sin_csrf.force_login(actor)
    assert _agregar(sin_csrf, audiencia, [receptor.pk]).status_code == 403
    assert not audiencia.membresias.exists()


def test_alta_multiple_revierte_membresias_y_auditoria_si_falla_el_segundo_alta(
    datos, audiencia
):
    cliente, actor = datos
    previo = User.objects.create_user(username="previo")
    uno = User.objects.create_user(username="uno")
    dos = User.objects.create_user(username="dos")
    audiencia.agregar_miembro(previo)

    def fallar_segundo(sender, instance, **kwargs):
        if instance.usuario_id == dos.pk:
            assert audiencia.membresias.filter(usuario=uno).exists()
            raise ValidationError("No se pudo completar el lote.")

    pre_save.connect(fallar_segundo, sender=MiembroAudienciaTableros)
    try:
        respuesta = _agregar(cliente, audiencia, [uno.pk, dos.pk])
    finally:
        pre_save.disconnect(fallar_segundo, sender=MiembroAudienciaTableros)

    assert respuesta.status_code == 400
    assert "No se pudo completar el lote." in respuesta.content.decode()
    assert set(audiencia.membresias.values_list("usuario_id", flat=True)) == {previo.pk}
    contenido = ContentType.objects.get_for_model(MiembroAudienciaTableros)
    assert not LogEntry.objects.filter(actor=actor, content_type=contenido).exists()
