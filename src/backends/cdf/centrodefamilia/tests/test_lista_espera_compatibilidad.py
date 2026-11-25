"""Contrato W1 de compatibilidad de la lista de espera CDF (#2811)."""

from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.urls import reverse

from ciudadanos.models import Ciudadano
from core.models import Provincia
from centrodefamilia.models import (
    Actividad,
    ActividadCentro,
    Categoria,
    Centro,
    ParticipanteActividad,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def cliente_publico(client):
    """Evita la consulta diagnóstica HEAD de admindocs para IPs internas."""
    client.defaults["REMOTE_ADDR"] = "203.0.113.42"


@pytest.fixture
def escenario_espera():
    provincia = Provincia.objects.create(nombre="Provincia sintética W1")
    centros = [
        Centro.objects.create(
            nombre=f"CDF W1 {numero}",
            provincia=provincia,
            tipo="faro",
            codigo=f"cdf-w1-{numero}",
            domicilio_actividad="Domicilio sintético",
            correo=f"centro-{numero}@example.test",
            nombre_referente="Referente",
            apellido_referente="Sintético",
        )
        for numero in (1, 2)
    ]
    categoria = Categoria.objects.create(nombre="Categoría W1")
    actividad = Actividad.objects.create(nombre="Actividad W1", categoria=categoria)
    actividad_centro = ActividadCentro.objects.create(
        centro=centros[0],
        actividad=actividad,
        cantidad_personas=1,
        horariosdesde="10:00",
        horarioshasta="12:00",
    )
    participantes = []
    for numero, estado in enumerate(("inscrito", "lista_espera"), start=1):
        ciudadano = Ciudadano.objects.create(
            apellido="Sintético",
            nombre=f"Participante W1 {numero}",
            fecha_nacimiento=date(2000, 1, 1),
            documento=39000000 + numero,
        )
        participantes.append(
            ParticipanteActividad.objects.create(
                actividad_centro=actividad_centro,
                ciudadano=ciudadano,
                estado=estado,
            )
        )
    return centros[0], centros[1], actividad_centro, participantes


@pytest.fixture
def usuario_consulta():
    usuario = User.objects.create_user(username="consulta-w1", password="synthetic")
    _habilitar_web(usuario)
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="centrodefamilia", codename="view_centro"
        )
    )
    return usuario


def _habilitar_web(usuario):
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()


def _url(centro_id, actividad_id):
    return reverse(
        "actividadcentro_lista_espera",
        kwargs={"centro_id": centro_id, "actividad_id": actividad_id},
    )


def _estado_participantes():
    return list(ParticipanteActividad.objects.order_by("pk").values())


@pytest.mark.parametrize("metodo", ["get", "head"])
def test_w1_redirige_a_seccion_existente_sin_mutar(
    client, escenario_espera, usuario_consulta, metodo
):
    centro, _, actividad, _ = escenario_espera
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = getattr(client, metodo)(_url(centro.pk, actividad.pk))

    assert respuesta.status_code == 302
    assert respuesta["Location"] == (
        reverse("actividadcentro_detail", kwargs={"pk": actividad.pk}) + "#lista-espera"
    )
    assert respuesta.content == b""
    assert _estado_participantes() == antes


@pytest.mark.parametrize(
    "query",
    [
        "?next=https://example.test/externo",
        "?url=//example.test/externo&next=/otra-ruta/&promo_error=1",
    ],
)
def test_w1_ignora_destinos_y_query_del_cliente(
    client, escenario_espera, usuario_consulta, query
):
    centro, _, actividad, _ = escenario_espera
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = client.get(_url(centro.pk, actividad.pk) + query)

    assert respuesta.status_code == 302
    assert respuesta["Location"] == (
        reverse("actividadcentro_detail", kwargs={"pk": actividad.pk}) + "#lista-espera"
    )
    assert _estado_participantes() == antes


@pytest.mark.parametrize("metodo", ["get", "head"])
@pytest.mark.parametrize(
    "caso", ["centro_inexistente", "actividad_inexistente", "ajena"]
)
def test_w1_rechaza_objetos_inexistentes_o_relacion_incongruente(
    client, escenario_espera, usuario_consulta, caso, metodo
):
    centro, otro_centro, actividad, _ = escenario_espera
    centro_id = otro_centro.pk if caso == "ajena" else centro.pk
    actividad_id = actividad.pk
    if caso == "centro_inexistente":
        centro_id = otro_centro.pk + 1000
    if caso == "actividad_inexistente":
        actividad_id += 1000
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = getattr(client, metodo)(_url(centro_id, actividad_id))

    assert respuesta.status_code == 404
    assert "Location" not in respuesta
    if metodo == "head":
        assert respuesta.content == b""
    assert _estado_participantes() == antes


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete", "options"])
def test_w1_metodos_no_admitidos_no_promueven_ni_modifican(
    client, escenario_espera, usuario_consulta, metodo
):
    centro, _, actividad, _ = escenario_espera
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = getattr(client, metodo)(_url(centro.pk, actividad.pk))

    assert respuesta.status_code == 405
    assert set(respuesta["Allow"].split(", ")) == {"GET", "HEAD"}
    assert "Location" not in respuesta
    assert _estado_participantes() == antes


@pytest.mark.parametrize("autenticado", [False, True])
@pytest.mark.parametrize("metodo", ["get", "head", "post", "delete"])
def test_w1_guard_conserva_403_antes_de_objetos_y_metodos(
    client, escenario_espera, autenticado, metodo
):
    centro, _, actividad, _ = escenario_espera
    if autenticado:
        usuario = User.objects.create_user(
            username="sin-permiso-w1", password="synthetic"
        )
        _habilitar_web(usuario)
        client.force_login(usuario)
    antes = _estado_participantes()

    respuesta = getattr(client, metodo)(_url(centro.pk + 1000, actividad.pk + 1000))

    assert respuesta.status_code == 403
    assert "Location" not in respuesta
    assert _estado_participantes() == antes


@pytest.mark.parametrize("diagnostico", ["ip_interna", "staff"])
def test_w1_head_diagnostico_conserva_admindocs_sin_consultar_objetos(
    client, escenario_espera, diagnostico
):
    centro, _, actividad, _ = escenario_espera
    direccion = "127.0.0.1" if diagnostico == "ip_interna" else "203.0.113.42"
    if diagnostico == "staff":
        usuario = User.objects.create_user(
            username="staff-diagnostico-w1", password="synthetic", is_staff=True
        )
        _habilitar_web(usuario)
        client.force_login(usuario)
    antes = _estado_participantes()

    respuesta = client.head(
        _url(centro.pk + 1000, actividad.pk + 1000), REMOTE_ADDR=direccion
    )

    assert respuesta.status_code == 200
    assert "ParticipanteActividadListEsperaView" in respuesta["X-View"]
    assert respuesta.content == b""
    assert _estado_participantes() == antes


def test_w1_destino_conserva_contenido_y_expone_ancla(
    client, escenario_espera, usuario_consulta
):
    centro, _, actividad, participantes = escenario_espera
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = client.get(
        reverse("actividadcentro_detail", kwargs={"pk": actividad.pk})
    )

    assert respuesta.status_code == 200
    assert respuesta.content.count(b'id="lista-espera"') == 1
    assert list(respuesta.context["lista_espera"]) == [participantes[1]]
    assert list(respuesta.context["participantes"]) == [participantes[0]]
    assert (
        reverse(
            "participanteactividad_promover",
            kwargs={
                "centro_id": centro.pk,
                "actividad_id": actividad.pk,
                "pk": participantes[1].pk,
            },
        ).encode()
        in respuesta.content
    )
    assert _estado_participantes() == antes


def test_w1_destino_vacio_conserva_ancla_y_no_crea_participantes(
    client, escenario_espera, usuario_consulta
):
    _, _, actividad, participantes = escenario_espera
    participantes[1].estado = "dado_baja"
    participantes[1].save(update_fields=["estado"])
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = client.get(
        reverse("actividadcentro_detail", kwargs={"pk": actividad.pk})
    )

    assert respuesta.status_code == 200
    assert respuesta.content.count(b'id="lista-espera"') == 1
    assert b"Sin lista de espera" in respuesta.content
    assert not respuesta.context["lista_espera"].exists()
    assert _estado_participantes() == antes


def test_w1_promocion_get_conserva_retorno_y_no_muta(
    client, escenario_espera, usuario_consulta
):
    centro, _, actividad, participantes = escenario_espera
    client.force_login(usuario_consulta)
    antes = _estado_participantes()

    respuesta = client.get(
        reverse(
            "participanteactividad_promover",
            kwargs={
                "centro_id": centro.pk,
                "actividad_id": actividad.pk,
                "pk": participantes[1].pk,
            },
        )
    )

    assert respuesta.status_code == 302
    assert respuesta["Location"] == (
        reverse("actividadcentro_detail", kwargs={"pk": actividad.pk})
        + "?promo_error=1"
    )
    assert _estado_participantes() == antes
