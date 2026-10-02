import json

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from encuestas.models import (
    CumplimientoRonda,
    Encuesta,
    EstadoEncuesta,
    Pregunta,
    TipoPregunta,
    TipoSegmentacion,
)
from encuestas.services import (
    actualizar_segmentacion,
    crear_encuesta,
    exportar_encuesta,
    get_rondas_pendientes,
    importar_encuesta,
    nueva_version,
    usuario_esta_segmentado,
)
from encuestas.tests.helpers import publicar_para_test

pytestmark = pytest.mark.django_db
TIPO = TipoSegmentacion.GRUPOS


@pytest.fixture
def escenario(django_user_model):
    usuarios = [
        django_user_model.objects.create_user(username=f"grupo-test-{i}")
        for i in range(4)
    ]
    grupos = [Group.objects.create(name=f"Equipo {i}") for i in range(2)]
    usuarios[1].groups.add(grupos[0])
    usuarios[2].groups.add(*grupos)
    encuesta = crear_encuesta(
        usuario=usuarios[0],
        titulo="Por grupos",
        es_obligatoria=True,
        duracion_ronda_dias=7,
    )
    Pregunta.objects.create(
        encuesta=encuesta, texto="¿Todo bien?", tipo=TipoPregunta.SI_NO, orden=1
    )
    actualizar_segmentacion(encuesta, tipo=TIPO, grupos_ids=[g.pk for g in grupos])
    return encuesta, usuarios, grupos


def test_union_sin_duplicados_y_membresia_dinamica(escenario):
    encuesta, usuarios, grupos = escenario
    ronda = publicar_para_test(encuesta, usuario=usuarios[0])
    for usuario in usuarios[1:3]:
        assert usuario_esta_segmentado(encuesta, usuario)
        assert [r.pk for r in get_rondas_pendientes(usuario)] == [ronda.pk]
    assert not usuario_esta_segmentado(encuesta, usuarios[3])
    assert get_rondas_pendientes(usuarios[3]) == []
    usuarios[3].groups.add(grupos[1])
    assert [r.pk for r in get_rondas_pendientes(usuarios[3])] == [ronda.pk]
    usuarios[3].groups.clear()
    assert get_rondas_pendientes(usuarios[3]) == []


def test_responder_verifica_pertenencia_actual(client, escenario):
    encuesta, usuarios, _ = escenario
    ronda = publicar_para_test(encuesta, usuario=usuarios[0])
    url = reverse("encuestas_responder", args=[ronda.pk])
    datos = {f"respuesta-{encuesta.preguntas.get().pk}": "si"}
    client.force_login(usuarios[1])
    usuarios[1].groups.clear()
    response = client.post(url, datos)
    assert any(
        "No estás habilitado" in str(m) for m in get_messages(response.wsgi_request)
    )
    assert not CumplimientoRonda.objects.filter(
        ronda=ronda, usuario=usuarios[1]
    ).exists()
    client.force_login(usuarios[2])
    assert client.post(url, datos).status_code == 302
    assert CumplimientoRonda.objects.filter(ronda=ronda, usuario=usuarios[2]).exists()
    assert get_rondas_pendientes(usuarios[2]) == []


@pytest.mark.parametrize("ids", [[], None, ["abc"], ["-1"], ["1.5"], [999999999]])
def test_seleccion_invalida_conserva_configuracion(escenario, ids):
    encuesta, usuarios, _ = escenario
    actualizar_segmentacion(
        encuesta, tipo=TipoSegmentacion.LISTADO_USUARIOS, usuarios_ids=[usuarios[1].pk]
    )
    with pytest.raises(ValidationError):
        actualizar_segmentacion(encuesta, tipo=TIPO, grupos_ids=ids)
    encuesta.refresh_from_db()
    assert encuesta.segmentacion.tipo == TipoSegmentacion.LISTADO_USUARIOS
    assert list(encuesta.segmentacion.usuarios.all()) == [usuarios[1]]


def test_cambiar_tipo_y_reemplazar_grupos(escenario):
    encuesta, usuarios, grupos = escenario
    actualizar_segmentacion(
        encuesta, tipo=TIPO, grupos_ids=[grupos[1].pk, grupos[1].pk]
    )
    assert list(encuesta.segmentacion.grupos.all()) == [grupos[1]]
    assert not usuario_esta_segmentado(encuesta, usuarios[1])
    actualizar_segmentacion(encuesta, tipo=TipoSegmentacion.LISTADO_DOCUMENTOS)
    assert not encuesta.segmentacion.grupos.exists()
    assert not usuario_esta_segmentado(encuesta, usuarios[2])


def test_pendiente_no_permite_cambiar_grupos(escenario):
    encuesta, _, grupos = escenario
    Encuesta.objects.filter(pk=encuesta.pk).update(
        estado=EstadoEncuesta.PENDIENTE_APROBACION
    )
    with pytest.raises(ValidationError):
        actualizar_segmentacion(encuesta, tipo=TIPO, grupos_ids=[grupos[0].pk])
    assert encuesta.segmentacion.grupos.count() == 2


def test_clonacion_y_portabilidad_por_nombre(escenario):
    encuesta, usuarios, grupos = escenario
    copia = nueva_version(encuesta, usuario=usuarios[0])
    assert set(copia.segmentacion.grupos.all()) == set(grupos)
    datos = exportar_encuesta(encuesta, incluir_segmentacion=True)
    assert datos["version_formato"] == 5
    assert datos["segmentacion"]["destinatarios"] == [{"grupo": g.name} for g in grupos]
    nombres = [g.name for g in grupos]
    Group.objects.filter(pk__in=[g.pk for g in grupos]).delete()
    nuevos = [Group.objects.create(name=n) for n in nombres]
    copia = importar_encuesta(
        SimpleUploadedFile("encuesta.json", json.dumps(datos).encode()),
        usuario=usuarios[0],
    )
    assert set(copia.segmentacion.grupos.all()) == set(nuevos)
    nuevos[0].delete()
    cantidad = Encuesta.objects.count()
    with pytest.raises(ValidationError, match="no existen"):
        importar_encuesta(
            SimpleUploadedFile("encuesta.json", json.dumps(datos).encode()),
            usuario=usuarios[0],
        )
    assert Encuesta.objects.count() == cantidad


def test_vistas_permisos_seleccion_revision_y_error(client, escenario):
    encuesta, usuarios, grupos = escenario
    url = reverse("encuestas_segmentacion_tipo", args=[encuesta.pk])
    client.force_login(usuarios[0])
    assert client.post(url, {"tipo": TIPO, "grupos": [grupos[0].pk]}).status_code == 403
    usuarios[0].user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="encuestas",
            codename__in=["change_encuesta", "view_encuesta"],
        )
    )
    response = client.post(url, {"tipo": TIPO, "grupos": [grupos[0].pk]})
    assert response.status_code == 302
    response = client.get(reverse("encuestas_segmentacion", args=[encuesta.pk]))
    assert response.context["grupos_seleccionados"] == {grupos[0].pk}
    response = client.get(reverse("encuestas_revision", args=[encuesta.pk]))
    assert grupos[0].name in response.content.decode()
    assert grupos[1].name not in response.content.decode()
    response = client.post(url, {"tipo": TIPO})
    assert any(
        "Seleccioná al menos" in str(m) for m in get_messages(response.wsgi_request)
    )
    encuesta.refresh_from_db()
    assert list(encuesta.segmentacion.grupos.all()) == [grupos[0]]
