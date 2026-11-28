"""Personas con identidad reservada en Datos del Convenio (issue #2917).

En Abordaje Comunitario (Línea Tradicional / Secos) se carga la "Cantidad de
personas con identidad reservada". No figuran en la nómina, pero ocupan lugar:
el máximo de personas con prestación alimentaria pasa a ser
``personas conveniadas - personas con identidad reservada``.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from ciudadanos.models import Ciudadano
from comedores.forms.comedor_form import NominaExtraForm
from comedores.forms.convenio_pnud_form import (
    PRESTACIONES_APROBADAS_FIELDS,
    ComedorDatosConvenioPnudForm,
)
from comedores.models import Comedor, ComedorDatosConvenioPnud, Nomina, Programas
from pwa.services.nomina_service import resumen_cupo_nomina_alimentaria

pytestmark = pytest.mark.django_db

TRADICIONAL = "Abordaje Comunitario - Línea Tradicional"
SECOS = "Abordaje Comunitario - Línea Secos"
ETIQUETA = "Cantidad de personas con identidad reservada"


def _comedor(programa_nombre):
    programa, _ = Programas.objects.get_or_create(
        nombre=programa_nombre, defaults={"usa_admision_para_nomina": False}
    )
    return Comedor.objects.create(nombre="Espacio 2917", programa=programa)


def _form(comedor, instance=None, **data):
    return ComedorDatosConvenioPnudForm(
        data={**{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS}, **data},
        instance=instance,
        comedor=comedor,
    )


def _llenar_nomina(comedor, cantidad, desde=0):
    for indice in range(desde, desde + cantidad):
        Nomina.objects.create(
            comedor=comedor,
            ciudadano=Ciudadano.objects.create(
                nombre="Nombre",
                apellido="Apellido",
                documento=29170000 + indice,
                fecha_nacimiento="1990-01-01",
            ),
            estado=Nomina.ESTADO_ACTIVO,
        )


@pytest.fixture(name="admin_client")
def admin_client_fixture(client):
    client.force_login(
        get_user_model().objects.create_superuser(
            username="admin_2917", password="x", email="admin2917@example.com"
        )
    )
    return client


@pytest.mark.parametrize("programa", [TRADICIONAL, SECOS])
def test_el_campo_se_carga_en_abordaje_comunitario(programa):
    form = ComedorDatosConvenioPnudForm(comedor=_comedor(programa))

    campos = list(form.fields)
    assert campos.index("personas_identidad_reservada") == (
        campos.index("personas_conveniadas") + 1
    )
    assert form.fields["personas_identidad_reservada"].label == ETIQUETA
    html = str(form["personas_identidad_reservada"])
    assert 'type="number"' in html
    assert "data-solo-numeros" in html


def test_el_campo_no_se_carga_en_otros_programas():
    form = ComedorDatosConvenioPnudForm(comedor=_comedor("PNUD"))

    assert "personas_identidad_reservada" not in form.fields


def test_sin_completar_se_guarda_cero():
    comedor = _comedor(SECOS)
    form = _form(comedor, personas_conveniadas=10, personas_identidad_reservada="")

    assert form.is_valid(), form.errors
    form.instance.comedor = comedor
    assert form.save().personas_identidad_reservada == 0


@pytest.mark.parametrize("valor", ["abc", "1.5", "-3"])
def test_acepta_solo_numeros_enteros_no_negativos(valor):
    form = _form(_comedor(SECOS), personas_identidad_reservada=valor)

    assert not form.is_valid()
    assert "personas_identidad_reservada" in form.errors


def test_no_puede_superar_a_las_personas_conveniadas():
    form = _form(
        _comedor(TRADICIONAL),
        personas_conveniadas=10,
        personas_identidad_reservada=11,
    )

    assert not form.is_valid()
    assert form.errors["personas_identidad_reservada"] == [
        "No puede superar la cantidad de Personas Conveniadas (10)."
    ]


def test_puede_igualar_a_las_personas_conveniadas():
    form = _form(
        _comedor(TRADICIONAL),
        personas_conveniadas=10,
        personas_identidad_reservada=10,
    )

    assert form.is_valid(), form.errors


def test_el_tope_de_nomina_descuenta_las_identidades_reservadas():
    comedor = _comedor(TRADICIONAL)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=5, personas_identidad_reservada=3
    )
    _llenar_nomina(comedor, 1)

    assert resumen_cupo_nomina_alimentaria(comedor_id=comedor.pk) == {
        "tope": 2,
        "ocupados": 1,
        "completo": False,
    }


def test_el_alta_en_nomina_se_rechaza_al_llegar_al_tope_reducido():
    # El alta web reconoce Abordaje Comunitario por el id del programa.
    programa, _ = Programas.objects.update_or_create(
        pk=3, defaults={"nombre": TRADICIONAL, "usa_admision_para_nomina": False}
    )
    comedor = Comedor.objects.create(nombre="Espacio 2917", programa=programa)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=5, personas_identidad_reservada=3
    )
    datos = {"estado": Nomina.ESTADO_ACTIVO, "asistencia_alimentaria": "on"}

    _llenar_nomina(comedor, 1)
    assert NominaExtraForm(datos, comedor=comedor).is_valid()

    # Con 2 en nómina se llega al tope (5 conveniadas - 3 reservadas), aunque
    # todavía no se alcancen las 5 personas conveniadas.
    _llenar_nomina(comedor, 1, desde=1)
    form = NominaExtraForm(datos, comedor=comedor)
    assert not form.is_valid()
    assert "asistencia_alimentaria" in form.errors


def test_el_tope_nunca_es_negativo():
    comedor = _comedor(SECOS)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=2, personas_identidad_reservada=5
    )

    assert resumen_cupo_nomina_alimentaria(comedor_id=comedor.pk) == {
        "tope": 0,
        "ocupados": 0,
        "completo": True,
    }


def test_sin_personas_conveniadas_sigue_sin_haber_tope():
    comedor = _comedor(SECOS)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=None, personas_identidad_reservada=3
    )

    assert resumen_cupo_nomina_alimentaria(comedor_id=comedor.pk) is None


def test_la_vista_de_edicion_guarda_el_dato(admin_client):
    comedor = _comedor(TRADICIONAL)
    url = reverse("comedor_convenio_pnud", args=[comedor.pk])

    assert ETIQUETA in admin_client.get(url).content.decode()

    respuesta = admin_client.post(
        url,
        {
            **{name: 0 for name in PRESTACIONES_APROBADAS_FIELDS},
            "personas_conveniadas": 8,
            "personas_identidad_reservada": 3,
        },
    )

    assert respuesta.status_code == 302
    datos = ComedorDatosConvenioPnud.objects.get(comedor=comedor)
    assert datos.personas_identidad_reservada == 3


def test_el_legajo_muestra_el_dato_en_convenio_y_en_nomina(admin_client):
    comedor = _comedor(TRADICIONAL)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=8, personas_identidad_reservada=3
    )

    html = admin_client.get(reverse("comedor_detalle", args=[comedor.pk])).content
    html = " ".join(html.decode().split())

    # Cuadro "Datos del Convenio".
    assert f'{ETIQUETA}</span> <span class="d-block fw-bold">3</span>' in html
    # Apartado "Nómina", junto a los demás contadores.
    assert (
        '<div class="fw-bold fs-2 mb-0 py-0 text-white">3</div> '
        '<p class="mb-0 text-white fw-bold">Personas con identidad reservada</p>'
    ) in html


def test_el_legajo_de_otros_programas_no_muestra_el_dato(admin_client):
    comedor = _comedor("PNUD")
    ComedorDatosConvenioPnud.objects.create(comedor=comedor, personas_conveniadas=8)

    html = admin_client.get(reverse("comedor_detalle", args=[comedor.pk])).content

    assert "identidad reservada" not in html.decode()


@pytest.mark.parametrize("programa", [TRADICIONAL, SECOS])
def test_los_asistentes_suman_las_identidades_reservadas(admin_client, programa):
    comedor = _comedor(programa)
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=8, personas_identidad_reservada=3
    )
    _llenar_nomina(comedor, 2)

    contexto = admin_client.get(reverse("comedor_detalle", args=[comedor.pk])).context

    # 2 personas de la nómina + 3 con identidad reservada.
    assert contexto["nomina_asistentes"] == 5
    # Las reservadas no tienen edad: caen en "Sin dato" y el resto se reparte
    # sobre el total, así los porcentajes siguen sumando 100.
    assert contexto["nomina_pct_sin_dato"] == 60
    assert contexto["nomina_pct_adultos"] == 40


def test_los_asistentes_de_otros_programas_no_suman_el_dato(admin_client):
    comedor = _comedor("PNUD")
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor, personas_conveniadas=8, personas_identidad_reservada=3
    )
    _llenar_nomina(comedor, 2)

    contexto = admin_client.get(reverse("comedor_detalle", args=[comedor.pk])).context

    assert contexto["nomina_asistentes"] == 2
    assert contexto["nomina_pct_sin_dato"] == 0
