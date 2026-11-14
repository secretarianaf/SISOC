"""Corrección del código de un proyecto ya cargado desde la edición de la organización."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import reverse

from comedores.models import Comedor
from comedores.territoriales_pnud import territoriales_proyecto_comedor
from gestion_organizaciones.services.proyectos import cambiar_codigo_proyecto
from organizaciones.models import Organizacion, ProyectoOrganizacion


@pytest.fixture
def organizacion(db):
    return Organizacion.objects.create(nombre="Org código", sin_vencimiento=True)


@pytest.fixture
def proyecto(organizacion):
    return ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="P-0l")


@pytest.fixture
def admin_client(client):
    admin = get_user_model().objects.create_superuser("admin_cod", "c@c.com", "x")
    client.force_login(admin)
    return client


def _url(proyecto):
    return reverse("organizacion_proyecto_codigo", kwargs={"proyecto_id": proyecto.pk})


@pytest.mark.django_db
def test_cambia_el_codigo_en_el_proyecto_y_en_sus_comedores(organizacion, proyecto):
    por_fk = Comedor.objects.create(
        nombre="Por FK",
        organizacion=organizacion,
        proyecto=proyecto,
        codigo_de_proyecto="P-0l",
    )
    por_texto = Comedor.objects.create(
        nombre="Por texto", organizacion=organizacion, codigo_de_proyecto="P-0l"
    )
    dado_de_baja = Comedor.objects.create(
        nombre="De baja",
        organizacion=organizacion,
        proyecto=proyecto,
        codigo_de_proyecto="P-0l",
    )
    dado_de_baja.delete()
    otra = Organizacion.objects.create(nombre="Otra org", sin_vencimiento=True)
    ajeno = Comedor.objects.create(
        nombre="Ajeno", organizacion=otra, codigo_de_proyecto="P-0l"
    )

    actualizados = cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=" P-01 ")

    assert actualizados == 3
    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-01"
    for comedor in (por_fk, por_texto):
        comedor.refresh_from_db()
        assert comedor.codigo_de_proyecto == "P-01"
    assert Comedor.all_objects.get(pk=dado_de_baja.pk).codigo_de_proyecto == "P-01"
    ajeno.refresh_from_db()
    assert ajeno.codigo_de_proyecto == "P-0l"


@pytest.mark.django_db
def test_los_territoriales_del_comedor_siguen_vinculados(organizacion, proyecto):
    territorial = get_user_model().objects.create_user(username="terr_cod")
    proyecto.territoriales.add(territorial)
    comedor = Comedor.objects.create(
        nombre="Vinculado por texto",
        organizacion=organizacion,
        codigo_de_proyecto="P-0l",
    )
    antes = territoriales_proyecto_comedor(comedor)

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo="P-01")

    comedor.refresh_from_db()
    assert antes
    assert [
        fila["territorial"] for fila in territoriales_proyecto_comedor(comedor)
    ] == [fila["territorial"] for fila in antes]


@pytest.mark.django_db
@pytest.mark.parametrize("repetido", ["P-02", "p-02", "Q-09"])
def test_rechaza_codigos_de_la_misma_organizacion(organizacion, proyecto, repetido):
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="P-02")
    ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="Q-09", activo=False
    )

    with pytest.raises(ValidationError):
        cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=repetido)
    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-0l"


@pytest.mark.django_db
@pytest.mark.parametrize("invalido", ["", "   ", "P,01", "X" * 256])
def test_rechaza_codigos_invalidos(proyecto, invalido):
    with pytest.raises(ValidationError):
        cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo=invalido)


@pytest.mark.django_db
def test_el_mismo_codigo_de_otra_organizacion_se_permite(proyecto):
    otra = Organizacion.objects.create(nombre="Otra", sin_vencimiento=True)
    ProyectoOrganizacion.objects.create(organizacion=otra, codigo="P-01")

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo="P-01")

    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-01"


@pytest.mark.django_db
def test_pantalla_corrige_el_codigo_y_vuelve_a_la_edicion(
    admin_client, organizacion, proyecto
):
    Comedor.objects.create(
        nombre="Comedor", organizacion=organizacion, proyecto=proyecto
    )
    respuesta = admin_client.get(_url(proyecto))
    assert respuesta.status_code == 200
    assert respuesta.context["cantidad_comedores"] == 1

    respuesta = admin_client.post(_url(proyecto), {"codigo": "P-01"})

    assert respuesta.status_code == 302
    assert respuesta.url == (
        reverse("organizacion_editar", kwargs={"pk": organizacion.pk})
        + "#abordaje-card"
    )
    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-01"
    mensajes = [str(m) for m in get_messages(respuesta.wsgi_request)]
    assert any("P-0l a P-01" in mensaje for mensaje in mensajes)


@pytest.mark.django_db
def test_pantalla_muestra_el_error_de_codigo_repetido(
    admin_client, organizacion, proyecto
):
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="P-02")

    respuesta = admin_client.post(_url(proyecto), {"codigo": "P-02"})

    assert respuesta.status_code == 200
    assert "ya tiene el proyecto P-02" in respuesta.content.decode()
    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-0l"


@pytest.mark.django_db
def test_no_edita_proyectos_quitados(admin_client, proyecto):
    proyecto.activo = False
    proyecto.save()

    assert admin_client.get(_url(proyecto)).status_code == 404


@pytest.mark.django_db
def test_requiere_permiso(client, proyecto):
    usuario = get_user_model().objects.create_user("sin_perm_cod", password="x")
    client.force_login(usuario)

    assert client.post(_url(proyecto), {"codigo": "P-01"}).status_code in (302, 403)
    proyecto.refresh_from_db()
    assert proyecto.codigo == "P-0l"


# --- Línea de rendición deducida del código (prefijo AMBA, #2642) -------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viejo, nuevo",
    [("AMBA-123", "AMB-123"), ("AMB-123", "AMBA-123")],
    ids=["deja_de_ser_amba", "pasa_a_ser_amba"],
)
def test_cambiar_el_prefijo_amba_pide_confirmacion(
    admin_client, organizacion, viejo, nuevo
):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=viejo
    )

    respuesta = admin_client.post(_url(proyecto), {"codigo": nuevo})

    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "las rendiciones nuevas del proyecto pasan de" in html
    proyecto.refresh_from_db()
    assert proyecto.codigo == viejo

    respuesta = admin_client.post(
        _url(proyecto), {"codigo": nuevo, "confirmar_cambio_linea": "on"}
    )

    assert respuesta.status_code == 302
    proyecto.refresh_from_db()
    assert proyecto.codigo == nuevo


@pytest.mark.django_db
def test_sin_cambio_de_linea_no_pide_confirmacion(admin_client, organizacion):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AMBA-12"
    )

    respuesta = admin_client.post(_url(proyecto), {"codigo": "AMBA-123"})

    assert respuesta.status_code == 302
    proyecto.refresh_from_db()
    assert proyecto.codigo == "AMBA-123"


@pytest.mark.django_db
def test_la_linea_deducida_sigue_al_codigo_y_no_toca_rendiciones_creadas(
    organizacion,
):
    from comedores.models import Programas  # pylint: disable=import-outside-toplevel
    from rendicioncuentasmensual.models import (  # pylint: disable=import-outside-toplevel
        RendicionCuentaMensual,
    )
    from rendicioncuentasmensual.services import (  # pylint: disable=import-outside-toplevel
        inferir_linea_programatica,
    )

    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="AMBA-7"
    )
    comedor = Comedor.objects.create(
        nombre="Comedor AMBA",
        organizacion=organizacion,
        proyecto=proyecto,
        programa=Programas.objects.create(nombre="Programa prueba"),
    )
    creada = RendicionCuentaMensual.objects.create(
        comedor=comedor,
        proyecto=proyecto,
        mes=1,
        anio=2026,
        numero_rendicion=1,
        periodo_inicio="2026-01-01",
        periodo_fin="2026-01-31",
        linea_programatica=inferir_linea_programatica(comedor, proyecto),
    )
    assert creada.linea_programatica == RendicionCuentaMensual.LINEA_SECOS

    cambiar_codigo_proyecto(proyecto=proyecto, codigo_nuevo="BMA-7")
    proyecto.refresh_from_db()
    creada.refresh_from_db()

    assert creada.linea_programatica == RendicionCuentaMensual.LINEA_SECOS
    assert (
        inferir_linea_programatica(comedor, proyecto)
        == RendicionCuentaMensual.LINEA_TRADICIONAL
    )
