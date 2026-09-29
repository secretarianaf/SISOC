import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from encuestas.models import (
    Encuesta,
    EstadoEncuesta,
    Pregunta,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_encuesta,
    actualizar_segmentacion,
    agregar_destinatario,
    publicar,
    quitar_destinatario,
    rechazar_publicacion,
    reemplazar_preguntas,
    solicitar_publicacion,
)
from core.permissions.registry import permission_codes_for_bootstrap_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def actores(django_user_model):
    gestor = django_user_model.objects.create_user(username="solicitante")
    admin = django_user_model.objects.create_user(username="aprobador")
    for user, codes in [
        (gestor, ["view_encuesta", "change_encuesta"]),
        (admin, ["view_encuesta", "aprobar_encuesta"]),
    ]:
        user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="encuestas", codename__in=codes
            )
        )
    return gestor, admin


@pytest.fixture
def encuesta(actores):
    obj = Encuesta.objects.create(
        titulo="Para revisar",
        usuario_creador=actores[0],
        es_opcional=True,
        duracion_ronda_dias=7,
    )
    Pregunta.objects.create(encuesta=obj, texto="¿Conforme?", tipo=TipoPregunta.SI_NO)
    actualizar_segmentacion(
        obj,
        tipo=TipoSegmentacion.LISTADO_DOCUMENTOS,
        destinatarios=[{"tipo_documento": "dni", "numero_documento": "12345678"}],
    )
    return obj


def test_solicitud_aprobacion_abre_una_sola_ronda(client, actores, encuesta):
    gestor, admin = actores
    client.force_login(gestor)
    assert (
        client.get(reverse("encuestas_publicar", args=[encuesta.pk])).status_code == 405
    )
    assert (
        client.post(reverse("encuestas_publicar", args=[encuesta.pk])).status_code
        == 302
    )
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION
    assert not encuesta.rondas.exists()
    assert encuesta.usuario_ultima_modificacion == gestor
    client.force_login(admin)
    response = client.get(
        reverse("encuestas_listar"), {"estado": "pendiente_aprobacion"}, follow=True
    )
    assert list(response.context["encuestas"]) == [encuesta]
    response = client.get(reverse("encuestas_revision", args=[encuesta.pk]))
    assert response.status_code == 200
    assert "¿Conforme?" in response.content.decode()
    assert "12345678" in response.content.decode()
    for _ in range(2):
        assert (
            client.post(reverse("encuestas_aprobar", args=[encuesta.pk])).status_code
            == 302
        )
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PUBLICADA
    assert encuesta.rondas.count() == 1
    assert encuesta.usuario_ultima_modificacion == admin


def test_rechazo_permite_editar_y_volver_a_solicitar(client, actores, encuesta):
    gestor, admin = actores
    solicitar_publicacion(encuesta, usuario=gestor)
    client.force_login(admin)
    assert (
        client.post(
            reverse("encuestas_rechazar", args=[encuesta.pk]),
            {"motivo": "Aclarar la pregunta."},
        ).status_code
        == 302
    )
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.BORRADOR
    assert not encuesta.rondas.exists()
    actualizar_encuesta(encuesta, usuario=gestor, titulo="Corregida")
    solicitar_publicacion(encuesta, usuario=gestor)
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION


@pytest.mark.parametrize(
    "motivo", ["", "   \n ", "x" * 2001], ids=["vacio", "espacios", "demasiado-largo"]
)
def test_rechazo_exige_motivo_valido(client, actores, encuesta, motivo):
    solicitar_publicacion(encuesta, usuario=actores[0])
    client.force_login(actores[1])
    response = client.post(
        reverse("encuestas_rechazar", args=[encuesta.pk]), {"motivo": motivo}
    )
    assert response.status_code == 400
    assert response.context["abrir_modal_rechazo"]
    assert response.context["rechazo_form"].errors
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION
    assert encuesta.motivo_rechazo == ""
    with pytest.raises(ValidationError):
        rechazar_publicacion(encuesta, usuario=actores[1], motivo=motivo)


def test_motivo_visible_escapado_y_conservado_al_corregir(client, actores, encuesta):
    gestor, admin = actores
    solicitar_publicacion(encuesta, usuario=gestor)
    motivo = 'Aclarar destinatarios.\n<script>alert("x")</script>'
    client.force_login(admin)
    response = client.post(
        reverse("encuestas_rechazar", args=[encuesta.pk]),
        {"motivo": "  " + motivo + "  "},
    )
    assert response.status_code == 302
    encuesta.refresh_from_db()
    assert encuesta.motivo_rechazo == motivo
    assert encuesta.usuario_rechazo == admin
    fecha = encuesta.fecha_rechazo
    assert fecha is not None
    assert encuesta.estado == EstadoEncuesta.BORRADOR
    client.force_login(gestor)
    response = client.get(reverse("encuestas_editar", args=[encuesta.pk]))
    assert b"Aclarar destinatarios" in response.content
    assert b"&lt;script&gt;" in response.content
    assert b'<script>alert("x")</script>' not in response.content
    assert b"Ver motivo del rechazo" in client.get(reverse("encuestas_listar")).content
    actualizar_encuesta(encuesta, usuario=gestor, titulo="Corregida")
    solicitar_publicacion(encuesta, usuario=gestor)
    encuesta.refresh_from_db()
    assert encuesta.motivo_rechazo == motivo
    assert encuesta.fecha_rechazo == fecha
    assert encuesta.usuario_rechazo == admin
    rechazar_publicacion(encuesta, usuario=admin, motivo="Falta precisar la fecha.")
    encuesta.refresh_from_db()
    assert encuesta.motivo_rechazo == "Falta precisar la fecha."


@pytest.mark.parametrize("accion", ["aprobar", "rechazar"])
def test_gestor_no_puede_resolver_solicitudes(client, actores, encuesta, accion):
    gestor, _ = actores
    solicitar_publicacion(encuesta, usuario=gestor)
    client.force_login(gestor)
    assert (
        client.post(reverse(f"encuestas_{accion}", args=[encuesta.pk])).status_code
        == 403
    )
    with pytest.raises(PermissionDenied):
        (publicar if accion == "aprobar" else rechazar_publicacion)(
            encuesta, usuario=gestor
        )
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION
    assert not encuesta.rondas.exists()


@pytest.mark.parametrize("accion", [publicar, rechazar_publicacion])
def test_no_se_puede_resolver_borrador(actores, encuesta, accion):
    with pytest.raises(ValidationError):
        accion(encuesta, usuario=actores[1])
    assert not encuesta.rondas.exists()


def test_solicitud_repetida_y_sin_permiso(actores, encuesta):
    with pytest.raises(PermissionDenied):
        solicitar_publicacion(encuesta, usuario=actores[1])
    solicitar_publicacion(encuesta, usuario=actores[0])
    with pytest.raises(ValidationError):
        solicitar_publicacion(encuesta, usuario=actores[0])


@pytest.mark.parametrize("faltante", ["preguntas", "segmentacion"])
def test_solicitud_incompleta_no_cambia_estado(actores, encuesta, faltante):
    if faltante == "preguntas":
        encuesta.preguntas.all().delete()
    else:
        encuesta.segmentacion.delete()
        encuesta = Encuesta.objects.get(pk=encuesta.pk)
    with pytest.raises(ValidationError):
        solicitar_publicacion(encuesta, usuario=actores[0])
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.BORRADOR


def test_pendiente_bloquea_todas_las_ediciones_incluso_instancia_vieja(
    actores, encuesta
):
    vieja = Encuesta.objects.get(pk=encuesta.pk)
    destinatario = encuesta.segmentacion.destinatarios.get()
    solicitar_publicacion(encuesta, usuario=actores[0])
    acciones = [
        lambda: actualizar_encuesta(vieja, usuario=actores[0], titulo="Cambio"),
        lambda: reemplazar_preguntas(vieja, "[]"),
        lambda: actualizar_segmentacion(
            vieja, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS
        ),
        lambda: agregar_destinatario(
            vieja, tipo_documento="dni", numero_documento="999"
        ),
        lambda: quitar_destinatario(vieja, destinatario.pk),
    ]
    for accion in acciones:
        with pytest.raises(ValidationError, match="pendiente"):
            accion()
    encuesta.refresh_from_db()
    assert encuesta.titulo == "Para revisar"
    assert encuesta.preguntas.count() == 1
    assert encuesta.segmentacion.destinatarios.count() == 1


def test_fallo_al_abrir_ronda_revierte_aprobacion(monkeypatch, actores, encuesta):
    solicitar_publicacion(encuesta, usuario=actores[0])

    def fallar(_encuesta):
        raise ValidationError("Error de ronda")

    monkeypatch.setattr("encuestas.services.abrir_ronda", fallar)
    with pytest.raises(ValidationError):
        publicar(encuesta, usuario=actores[1])
    encuesta.refresh_from_db()
    assert encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION
    assert encuesta.usuario_ultima_modificacion == actores[0]


def test_bootstrap_separa_aprobador_de_gestor():
    assert "encuestas.aprobar_encuesta" in permission_codes_for_bootstrap_group(
        "Administrador de Encuestas"
    )
    assert "encuestas.aprobar_encuesta" not in permission_codes_for_bootstrap_group(
        "Gestor de Encuestas"
    )


def test_create_groups_asigna_permiso_al_administrador(actores):
    from django.contrib.auth.models import Group
    from django.core.management import call_command

    call_command("create_groups", verbosity=0)
    grupo = Group.objects.get(name="Administrador de Encuestas")
    assert grupo.permissions.filter(
        codename="aprobar_encuesta", content_type__app_label="encuestas"
    ).exists()


@pytest.mark.parametrize("ruta", ["encuestas_editar", "encuestas_segmentacion"])
def test_pendiente_redirige_a_revision(client, actores, encuesta, ruta):
    solicitar_publicacion(encuesta, usuario=actores[0])
    client.force_login(actores[0])
    response = client.get(reverse(ruta, args=[encuesta.pk]))
    assert response.url == reverse("encuestas_revision", args=[encuesta.pk])


def test_admin_no_edita_contenido_pendiente(actores, encuesta, rf):
    from django.contrib import admin
    from encuestas.admin import (
        EncuestaAdmin,
        PreguntaAdmin,
        PreguntaInline,
        OpcionPreguntaInline,
    )

    solicitar_publicacion(encuesta, usuario=actores[0])
    request = rf.get("/admin/")
    request.user = actores[1]
    request.user.is_superuser = True
    for model_admin, obj in [
        (EncuestaAdmin(Encuesta, admin.site), encuesta),
        (PreguntaAdmin(Pregunta, admin.site), encuesta.preguntas.get()),
        (PreguntaInline(Encuesta, admin.site), encuesta),
        (OpcionPreguntaInline(Pregunta, admin.site), encuesta.preguntas.get()),
    ]:
        assert not model_admin.has_change_permission(request, obj)
        assert not model_admin.has_delete_permission(request, obj)
