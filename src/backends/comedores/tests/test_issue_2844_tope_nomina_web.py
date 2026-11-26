"""Tope de nómina alimentaria también en el alta desde SISOC web (issue #2844).

En Abordaje Comunitario (Línea Tradicional / Secos) el campo "Personas
conveniadas" de Datos del Convenio es el máximo de personas con prestación
alimentaria en la nómina. La PWA ya lo respetaba; el alta desde
``/comedores/<pk>/nomina/crear/`` no, y permitía superarlo.
"""

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from admisiones.models.admisiones import Admision
from ciudadanos.models import Ciudadano
from comedores.forms.comedor_form import (
    MENSAJE_CUPO_ALIMENTARIO_WEB,
    MENSAJE_SOLO_ACTIVIDADES_POR_CUPO,
    NominaExtraForm,
)
from comedores.models import (
    Comedor,
    ComedorDatosConvenioPnud,
    Nomina,
    Programas,
)
from core.models import Dia
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA, NominaEspacioPWA

pytestmark = pytest.mark.django_db


@pytest.fixture(name="comedor_abordaje")
def comedor_abordaje_fixture():
    programa, _ = Programas.objects.update_or_create(
        pk=3,
        defaults={
            "nombre": "Abordaje Comunitario - Línea Tradicional",
            "usa_admision_para_nomina": False,
        },
    )
    comedor = Comedor.objects.create(nombre="Espacio 2844", programa=programa)
    ComedorDatosConvenioPnud.objects.create(comedor=comedor, personas_conveniadas=2)
    return comedor


def _ciudadano(documento):
    return Ciudadano.objects.create(
        nombre="Nombre",
        apellido="Apellido",
        documento=documento,
        fecha_nacimiento="1990-01-01",
    )


def _llenar_nomina(comedor, cantidad, estado=Nomina.ESTADO_ACTIVO):
    for indice in range(cantidad):
        Nomina.objects.create(
            comedor=comedor,
            ciudadano=_ciudadano(30000000 + indice),
            estado=estado,
        )


def _form(comedor, **data):
    datos = {"estado": Nomina.ESTADO_ACTIVO, "asistencia_alimentaria": "on"}
    datos.update(data)
    return NominaExtraForm(datos, comedor=comedor)


def test_con_cupo_disponible_el_alta_alimentaria_es_valida(comedor_abordaje):
    _llenar_nomina(comedor_abordaje, 1)

    assert _form(comedor_abordaje).is_valid()


def test_con_cupo_completo_el_alta_alimentaria_se_rechaza(comedor_abordaje):
    _llenar_nomina(comedor_abordaje, 2)

    form = _form(comedor_abordaje)

    assert not form.is_valid()
    assert form.errors["asistencia_alimentaria"] == [MENSAJE_CUPO_ALIMENTARIO_WEB]


def test_las_bajas_no_ocupan_cupo(comedor_abordaje):
    _llenar_nomina(comedor_abordaje, 2, estado=Nomina.ESTADO_BAJA)

    assert _form(comedor_abordaje).is_valid()


def test_cargar_directamente_como_baja_no_consume_cupo(comedor_abordaje):
    _llenar_nomina(comedor_abordaje, 2)

    assert _form(comedor_abordaje, estado=Nomina.ESTADO_BAJA).is_valid()


def test_sin_personas_conveniadas_cargadas_no_hay_tope(comedor_abordaje):
    ComedorDatosConvenioPnud.objects.filter(comedor=comedor_abordaje).update(
        personas_conveniadas=None
    )
    _llenar_nomina(comedor_abordaje, 5)

    assert _form(comedor_abordaje).is_valid()


def test_solo_actividades_sin_actividades_cargadas_informa_el_motivo(
    comedor_abordaje,
):
    """Sin actividades, crispy no muestra el error de la lista vacía: el aviso
    tiene que quedar en el checkbox de Actividades."""
    form = _form(
        comedor_abordaje,
        asistencia_alimentaria="",
        asistencia_actividades="on",
    )

    assert not form.is_valid()
    assert "no tiene actividades cargadas" in form.errors["asistencia_actividades"][0]


@pytest.fixture(name="admin_client")
def admin_client_fixture(client, django_user_model):
    client.force_login(
        django_user_model.objects.create_superuser(
            username="admin_2844", password="x", email="admin2844@example.com"
        )
    )
    return client


@pytest.mark.parametrize(
    "en_nomina, completo, texto",
    [(1, False, "1 de 2"), (2, True, "Cupo de Prestación alimentaria completo")],
    ids=["con_lugar", "lleno"],
)
def test_el_formulario_muestra_el_cupo_ocupado(
    comedor_abordaje, admin_client, en_nomina, completo, texto
):
    _llenar_nomina(comedor_abordaje, en_nomina)

    response = admin_client.get(
        reverse("nomina_directa_crear", kwargs={"pk": comedor_abordaje.pk})
    )

    assert response.context["cupo_alimentario"] == {
        "tope": 2,
        "ocupados": en_nomina,
        "completo": completo,
    }
    html = response.content.decode()
    assert texto in html
    # Sin actividades cargadas no se sugiere un camino que no existe.
    assert "se sumarán solo a Actividades" not in html


def test_la_vista_no_agrega_a_la_nomina_si_el_cupo_esta_completo(
    comedor_abordaje, admin_client
):
    _llenar_nomina(comedor_abordaje, 2)
    nuevo = _ciudadano(40000000)

    response = admin_client.post(
        reverse("nomina_directa_crear", kwargs={"pk": comedor_abordaje.pk}),
        {
            "ciudadano_id": nuevo.pk,
            "estado": Nomina.ESTADO_ACTIVO,
            "asistencia_alimentaria": "on",
        },
    )

    assert response.status_code == 200
    assert not Nomina.objects.filter(ciudadano=nuevo).exists()
    # El aviso fijo del cupo alcanza: no se duplica con un mensaje flotante.
    assert "Cupo de Prestación alimentaria completo" in response.content.decode()
    assert not list(get_messages(response.wsgi_request))


def test_el_alta_por_admision_tambien_muestra_el_cupo(comedor_abordaje, admin_client):
    """El alta con admisión aplica el mismo tope: sin el aviso fijo, el rechazo
    de un ciudadano existente quedaba sin ningún mensaje visible."""
    _llenar_nomina(comedor_abordaje, 2)
    admision = Admision.objects.create(comedor=comedor_abordaje)
    nuevo = _ciudadano(40000001)

    response = admin_client.post(
        reverse(
            "nomina_crear",
            kwargs={"pk": comedor_abordaje.pk, "admision_pk": admision.pk},
        ),
        {
            "ciudadano_id": nuevo.pk,
            "estado": Nomina.ESTADO_ACTIVO,
            "asistencia_alimentaria": "on",
        },
    )

    assert response.status_code == 200
    assert not Nomina.objects.filter(ciudadano=nuevo).exists()
    assert response.context["cupo_alimentario"]["completo"] is True
    assert "Cupo de Prestación alimentaria completo" in response.content.decode()


def test_con_cupo_completo_y_otro_error_se_mantiene_el_mensaje(
    comedor_abordaje, admin_client
):
    """El modal no muestra errores por campo: si el alta falla por algo que no
    es el cupo (acá, Actividades sin actividades cargadas), el mensaje
    genérico sigue siendo la única pista."""
    _llenar_nomina(comedor_abordaje, 2)
    nuevo = _ciudadano(40000002)

    response = admin_client.post(
        reverse("nomina_directa_crear", kwargs={"pk": comedor_abordaje.pk}),
        {
            "ciudadano_id": nuevo.pk,
            "estado": Nomina.ESTADO_ACTIVO,
            "asistencia_alimentaria": "on",
            "asistencia_actividades": "on",
        },
    )

    assert response.status_code == 200
    assert not Nomina.objects.filter(ciudadano=nuevo).exists()
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        "Datos inválidos para agregar ciudadano a la nómina."
    ]


@pytest.fixture(name="actividad")
def actividad_fixture(comedor_abordaje):
    return ActividadEspacioPWA.objects.create(
        comedor=comedor_abordaje,
        catalogo_actividad=CatalogoActividadPWA.objects.create(
            categoria="Deportes", actividad="Fútbol"
        ),
        dia_actividad=Dia.objects.create(nombre="Lunes"),
        horario_actividad="10 a 12",
    )


def test_con_cupo_completo_alimentaria_y_actividades_queda_solo_en_actividades(
    comedor_abordaje, actividad
):
    """Igual que la PWA: con el cupo lleno se suma solo a Actividades."""
    _llenar_nomina(comedor_abordaje, 2)

    form = _form(
        comedor_abordaje,
        asistencia_actividades="on",
        actividad_ids=[actividad.pk],
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["asistencia_alimentaria"] is False
    assert form.cleaned_data["asistencia_actividades"] is True
    assert form.alimentaria_omitida_por_cupo is True


def test_con_cupo_disponible_alimentaria_y_actividades_conserva_ambas(
    comedor_abordaje, actividad
):
    _llenar_nomina(comedor_abordaje, 1)

    form = _form(
        comedor_abordaje,
        asistencia_actividades="on",
        actividad_ids=[actividad.pk],
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["asistencia_alimentaria"] is True
    assert form.alimentaria_omitida_por_cupo is False


def test_la_vista_suma_solo_a_actividades_y_deja_la_advertencia_visible(
    comedor_abordaje, actividad, admin_client
):
    _llenar_nomina(comedor_abordaje, 2)
    nuevo = _ciudadano(40000003)

    response = admin_client.post(
        reverse("nomina_directa_crear", kwargs={"pk": comedor_abordaje.pk}),
        {
            "ciudadano_id": nuevo.pk,
            "estado": Nomina.ESTADO_ACTIVO,
            "asistencia_alimentaria": "on",
            "asistencia_actividades": "on",
            "actividad_ids": [actividad.pk],
        },
        follow=True,
    )

    perfil = NominaEspacioPWA.objects.get(nomina__ciudadano=nuevo)
    assert perfil.asistencia_alimentaria is False
    assert perfil.asistencia_actividades is True
    assert MENSAJE_SOLO_ACTIVIDADES_POR_CUPO in response.content.decode()

    # La advertencia se muestra una sola vez, no en cada visita a la nómina.
    otra_visita = admin_client.get(
        reverse("nomina_directa_ver", kwargs={"pk": comedor_abordaje.pk})
    )
    assert MENSAJE_SOLO_ACTIVIDADES_POR_CUPO not in otra_visita.content.decode()
