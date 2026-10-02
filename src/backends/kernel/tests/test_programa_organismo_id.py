"""``Programa.organismo_id``: el kernel guarda el id de la organización.

Antes era una FK a ``organizaciones.Organizacion``. Se verifica que el CRUD,
el import/export y el borrado de la organización se comporten igual.
"""

import pytest

from core.forms import ProgramaForm
from core.models import Programa
from core.resources import OrganismoPorNombreWidget
from organizaciones.models import Organizacion


@pytest.fixture(name="organizacion")
def organizacion_fixture(db):
    return Organizacion.objects.create(nombre="Organismo Test")


@pytest.mark.django_db
def test_organismo_resuelve_la_organizacion(organizacion):
    programa = Programa.objects.create(nombre="Alimentar", organismo_id=organizacion.pk)

    assert programa.organismo == organizacion
    assert Programa(nombre="Sin organismo").organismo is None


@pytest.mark.django_db
def test_formulario_guarda_y_precarga_el_organismo(organizacion):
    form = ProgramaForm(
        data={
            "nombre": "Programa con organismo",
            "estado": True,
            "observaciones": "",
            "organismo": organizacion.pk,
            "descripcion": "",
        }
    )
    assert form.is_valid(), form.errors
    programa = form.save()

    assert programa.organismo_id == organizacion.pk
    assert ProgramaForm(instance=programa).initial["organismo"] == organizacion.pk


@pytest.mark.django_db
def test_formulario_sin_organismo_guarda_null():
    form = ProgramaForm(
        data={"nombre": "Programa sin organismo", "estado": True, "organismo": ""}
    )
    assert form.is_valid(), form.errors

    assert form.save().organismo_id is None


@pytest.mark.django_db
def test_import_export_usa_el_nombre_del_organismo(organizacion):
    widget = OrganismoPorNombreWidget()

    assert widget.render(organizacion.pk) == "Organismo Test"
    assert widget.render(None) == ""
    assert widget.clean("Organismo Test") == organizacion.pk
    assert widget.clean("") is None


@pytest.mark.django_db
def test_borrar_la_organizacion_deja_el_programa_sin_organismo(organizacion):
    programa = Programa.objects.create(nombre="Huerfano", organismo_id=organizacion.pk)

    organizacion.hard_delete()

    programa.refresh_from_db()
    assert programa.organismo_id is None
