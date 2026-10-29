"""Etapa 4 del #2745: regla Comedor–Organización.

Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
El orden de carga es organización -> programas de la organización ->
proyectos de la línea elegida. Las organizaciones sin programas siguen como
hoy y editar otros datos de un comedor existente no se bloquea.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.forms.utils import ErrorDict
from django.urls import reverse

from comedores.forms.comedor_form import ComedorForm
from comedores.models import Comedor, Programas
from gestion_organizaciones.models import LineaProyecto, ProgramaOrganizacion
from organizaciones.models import Organizacion, ProyectoOrganizacion


@pytest.fixture
def programas(db):
    return SimpleNamespace(
        alco=Programas.objects.create(nombre="Alimentar comunidad"),
        secos=Programas.objects.create(nombre="Abordaje comunitario - Línea Secos"),
        tradicional=Programas.objects.create(
            nombre="Abordaje comunitario - Línea Tradicional"
        ),
        pnud=Programas.objects.create(nombre="PNUD Prog1"),
    )


def _organizacion(nombre, *programas_org):
    organizacion = Organizacion.objects.create(nombre=nombre)
    for programa in programas_org:
        ProgramaOrganizacion.objects.create(
            organizacion=organizacion, programa=programa
        )
    return organizacion


def _proyecto(organizacion, codigo, linea=None):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=codigo
    )
    if linea is not None:
        LineaProyecto.objects.create(proyecto=proyecto, programa=linea)
    return proyecto


def _validar(organizacion, programa, proyecto=None, instance=None):
    """Corre solo la regla nueva sobre un formulario enviado."""
    data = {
        "organizacion": str(organizacion.pk),
        "programa": str(programa.pk),
        "proyecto": str(proyecto.pk) if proyecto else "",
    }
    form = ComedorForm(data=data, instance=instance)
    form._errors = ErrorDict()  # pylint: disable=protected-access
    form.cleaned_data = {
        "organizacion": organizacion,
        "programa": programa,
        "proyecto": proyecto,
    }
    form._validar_programa_y_linea(  # pylint: disable=protected-access
        form.cleaned_data
    )
    return form._errors  # pylint: disable=protected-access


def test_organizacion_sin_programas_no_aplica_la_regla(programas):
    organizacion = _organizacion("Org libre")
    proyecto = _proyecto(organizacion, "P-1")

    assert not _validar(organizacion, programas.pnud)
    assert not _validar(organizacion, programas.secos, proyecto)


def test_alta_con_programa_que_la_organizacion_no_tiene(programas):
    organizacion = _organizacion("Org ALCO", programas.alco)

    errores = _validar(organizacion, programas.secos)

    assert errores["programa"] == ["La organización debe tener este programa cargado."]


def test_alta_con_proyecto_de_otra_linea(programas):
    organizacion = _organizacion("Org AC", programas.secos, programas.tradicional)
    proyecto_tradicional = _proyecto(organizacion, "T-1", programas.tradicional)

    errores = _validar(organizacion, programas.secos, proyecto_tradicional)

    assert errores["proyecto"] == ["El proyecto seleccionado pertenece a otra línea."]


def test_alta_con_proyecto_sin_linea(programas):
    organizacion = _organizacion("Org sin línea", programas.secos)
    proyecto = _proyecto(organizacion, "X-1")

    errores = _validar(organizacion, programas.secos, proyecto)

    assert "no tiene línea asignada" in errores["proyecto"][0]


def test_alta_valida(programas):
    organizacion = _organizacion("Org válida", programas.alco, programas.secos)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)

    assert not _validar(organizacion, programas.secos, proyecto)
    assert not _validar(organizacion, programas.alco)


def test_comedor_existente_se_edita_sin_cambiar_programa(programas):
    organizacion = _organizacion("Org histórica", programas.alco)
    comedor = Comedor.objects.create(
        nombre="Comedor PNUD", organizacion=organizacion, programa=programas.pnud
    )

    assert not _validar(organizacion, programas.pnud, instance=comedor)


def test_comedor_existente_que_cambia_programa_aplica_la_regla(programas):
    organizacion = _organizacion("Org cambio", programas.alco)
    comedor = Comedor.objects.create(
        nombre="Comedor ALCO", organizacion=organizacion, programa=programas.alco
    )

    errores = _validar(organizacion, programas.pnud, instance=comedor)

    assert "programa" in errores


def test_formulario_ofrece_solo_programas_de_la_organizacion(programas):
    organizacion = _organizacion("Org opciones", programas.alco, programas.secos)
    comedor = Comedor.objects.create(
        nombre="Comedor PNUD", organizacion=organizacion, programa=programas.pnud
    )

    form = ComedorForm(instance=comedor)

    assert set(form.fields["programa"].queryset) == {
        programas.alco,
        programas.secos,
        programas.pnud,
    }


def test_formulario_sin_programas_ofrece_todos(programas):
    organizacion = _organizacion("Org sin programas")
    comedor = Comedor.objects.create(nombre="C", organizacion=organizacion)

    form = ComedorForm(instance=comedor)

    assert set(form.fields["programa"].queryset) == set(Programas.objects.all())


def test_ajax_devuelve_linea_programas_y_filtra_por_programa(client, programas):
    user = User.objects.create_superuser(username="su-2745", password="x")
    organizacion = _organizacion("Org ajax", programas.secos, programas.tradicional)
    secos = _proyecto(organizacion, "S-1", programas.secos)
    tradicional = _proyecto(organizacion, "T-1", programas.tradicional)
    client.force_login(user)
    url = reverse(
        "organizacion_proyectos_ajax", kwargs={"organizacion_id": organizacion.pk}
    )

    datos = client.get(url).json()
    filtrado = client.get(url, {"programa": programas.secos.pk}).json()

    assert datos["programas"] == [programas.secos.pk, programas.tradicional.pk]
    assert {(p["codigo"], p["linea"]) for p in datos["proyectos"]} == {
        ("S-1", programas.secos.pk),
        ("T-1", programas.tradicional.pk),
    }
    assert [p["id"] for p in filtrado["proyectos"]] == [secos.pk]
    assert tradicional.pk not in [p["id"] for p in filtrado["proyectos"]]
