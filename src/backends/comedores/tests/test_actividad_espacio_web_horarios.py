"""Alta web de actividades de Abordaje Comunitario: días agrupados y datos nuevos.

Un horario agrupa varios días con la misma hora de inicio y fin; cada día se
guarda como una actividad. "Nombre de fantasía" y "Número de personas" son
datos informativos.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.datastructures import MultiValueDict

from comedores.forms.actividad_espacio_pwa_form import ActividadEspacioPWAWebForm
from comedores.models import Comedor, Programas
from core.models import Dia
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA

DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


@pytest.fixture
def dias(db):
    return {nombre: Dia.objects.get_or_create(nombre=nombre)[0] for nombre in DIAS}


@pytest.fixture
def comedor(db):
    programa = Programas.objects.create(nombre="PNUD Abordaje prueba")
    return Comedor.objects.create(nombre="Espacio horarios", programa=programa)


@pytest.fixture
def catalogo(db):
    return CatalogoActividadPWA.objects.create(categoria="Salud", actividad="Yoga")


def _post(catalogo, grupos, **extra):
    """Arma el POST del formulario: grupos = [(clave, [dias], inicio, fin)]."""
    data = MultiValueDict(
        {
            "categoria": [catalogo.categoria],
            "catalogo_actividad": [str(catalogo.pk)],
            "schedule_grupo": [clave for clave, *_ in grupos],
            "schedule_hora_inicio": [inicio for *_, inicio, _fin in grupos],
            "schedule_hora_fin": [fin for *_, fin in grupos],
        }
    )
    for clave, dias_grupo, *_ in grupos:
        data.setlist(f"schedule_dias_{clave}", [str(dia.pk) for dia in dias_grupo])
    for campo, valor in extra.items():
        data[campo] = valor
    return data


def _horarios(form):
    return [
        (row["dia_actividad"].nombre, f"{row['hora_inicio']:%H:%M}")
        for row in form.get_schedule_data()
    ]


@pytest.mark.django_db
def test_un_horario_con_varios_dias_genera_una_fila_por_dia(comedor, catalogo, dias):
    data = _post(
        catalogo,
        [("0", [dias["Viernes"], dias["Lunes"], dias["Miércoles"]], "11:00", "12:00")],
    )
    form = ActividadEspacioPWAWebForm(data=data, comedor=comedor)

    assert form.is_valid(), form.errors
    assert _horarios(form) == [
        ("Lunes", "11:00"),
        ("Miércoles", "11:00"),
        ("Viernes", "11:00"),
    ]


@pytest.mark.django_db
def test_nuevo_horario_suma_un_dia_con_otro_horario(comedor, catalogo, dias):
    data = _post(
        catalogo,
        [
            ("0", [dias["Lunes"], dias["Miércoles"]], "11:00", "12:00"),
            ("n1", [dias["Sábado"]], "09:00", "10:30"),
        ],
    )
    form = ActividadEspacioPWAWebForm(data=data, comedor=comedor)

    assert form.is_valid(), form.errors
    assert _horarios(form) == [
        ("Lunes", "11:00"),
        ("Miércoles", "11:00"),
        ("Sábado", "09:00"),
    ]


@pytest.mark.django_db
def test_horario_sin_dias_marca_error_en_ese_grupo(comedor, catalogo, dias):
    data = _post(
        catalogo,
        [
            ("0", [dias["Lunes"]], "11:00", "12:00"),
            ("n1", [], "09:00", "10:00"),
        ],
    )
    form = ActividadEspacioPWAWebForm(data=data, comedor=comedor)

    assert not form.is_valid()
    assert form.schedule_errors == [{}, {"dias": "Seleccioná al menos un día."}]


@pytest.mark.django_db
def test_dos_horarios_que_se_pisan_el_mismo_dia_se_rechazan(comedor, catalogo, dias):
    data = _post(
        catalogo,
        [
            ("0", [dias["Lunes"], dias["Martes"]], "11:00", "12:00"),
            ("n1", [dias["Martes"]], "11:30", "12:30"),
        ],
    )
    form = ActividadEspacioPWAWebForm(data=data, comedor=comedor)

    assert not form.is_valid()
    assert any("cruzados" in error for error in form.non_field_errors())


@pytest.mark.django_db
def test_sigue_aceptando_el_formato_anterior_de_un_dia_por_fila(
    comedor, catalogo, dias
):
    data = MultiValueDict(
        {
            "categoria": ["Salud"],
            "catalogo_actividad": [str(catalogo.pk)],
            "schedule_dia_actividad": [str(dias["Lunes"].pk), str(dias["Jueves"].pk)],
            "schedule_hora_inicio": ["10:00", "10:00"],
            "schedule_hora_fin": ["11:00", "11:00"],
        }
    )
    form = ActividadEspacioPWAWebForm(data=data, comedor=comedor)

    assert form.is_valid(), form.errors
    assert _horarios(form) == [("Lunes", "10:00"), ("Jueves", "10:00")]


@pytest.mark.django_db
def test_numero_de_personas_solo_acepta_enteros_no_negativos(comedor, catalogo, dias):
    grupos = [("0", [dias["Lunes"]], "11:00", "12:00")]
    for invalido in ("-1", "doce", "2.5"):
        form = ActividadEspacioPWAWebForm(
            data=_post(catalogo, grupos, cantidad_personas=invalido), comedor=comedor
        )
        assert not form.is_valid()
        assert "cantidad_personas" in form.errors


@pytest.mark.django_db
def test_edicion_muestra_el_dia_de_la_actividad_marcado(comedor, catalogo, dias):
    actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=catalogo,
        dia_actividad=dias["Martes"],
        hora_inicio=datetime.time(8, 0),
        hora_fin=datetime.time(9, 0),
        horario_actividad="08:00 a 09:00",
    )
    form = ActividadEspacioPWAWebForm(instance=actividad, comedor=comedor)

    assert form.schedule_form_rows[0]["values"]["dias"] == [str(dias["Martes"].pk)]


@pytest.mark.django_db
def test_alta_web_guarda_una_actividad_por_dia_con_los_datos_nuevos(
    client, comedor, catalogo, dias
):
    admin = get_user_model().objects.create_superuser("admin_act", "a@a.com", "x")
    client.force_login(admin)
    url = reverse("actividad_espacio_pwa_crear", kwargs={"pk": comedor.pk})

    assert client.get(url).status_code == 200

    data = _post(
        catalogo,
        [("0", [dias["Lunes"], dias["Miércoles"], dias["Viernes"]], "11:00", "12:00")],
        nombre_fantasia="Yoga en la plaza",
        cantidad_personas="15",
    )
    response = client.post(url, {campo: data.getlist(campo) for campo in data})

    assert response.status_code == 302
    actividades = ActividadEspacioPWA.objects.filter(comedor=comedor)
    assert sorted(a.dia_actividad.nombre for a in actividades) == [
        "Lunes",
        "Miércoles",
        "Viernes",
    ]
    assert {(a.nombre_fantasia, a.cantidad_personas) for a in actividades} == {
        ("Yoga en la plaza", 15)
    }

    detalle = client.get(reverse("comedor_detalle", kwargs={"pk": comedor.pk}))
    contenido = detalle.content.decode()
    assert "Yoga en la plaza" in contenido
    assert "N&uacute;mero de personas" in contenido
