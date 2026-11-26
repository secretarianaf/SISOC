"""Selects de ciudadano e inscripción sin cargar toda la tabla (#2889).

Estos formularios renderizaban el padrón completo en cada GET: tardaban más que
el timeout del proxy y dejaban a VAT sin workers. Ahora solo cargan la opción
elegida y el resto se busca por documento.
"""

from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Programa, Provincia
from VAT.forms import InscripcionForm, ResultadoEvaluacionForm, VoucherForm
from VAT.models import Inscripcion, ModalidadCursada
from VAT.services import buscador_ciudadano_service as service
from VAT.test_buscador_ciudadano import (
    _build_comision_curso,
    _centro_basico,
    _grant_referente_role,
)

pytestmark = pytest.mark.django_db


def _ciudadano(documento, apellido="Pérez", nombre="Ana"):
    return Ciudadano.objects.create(
        apellido=apellido,
        nombre=nombre,
        fecha_nacimiento=date(2000, 1, 1),
        tipo_documento=Ciudadano.DOCUMENTO_DNI,
        documento=documento,
    )


def _pasaporte(numero):
    return Ciudadano.objects.create(
        apellido="Silva",
        nombre="Joao",
        fecha_nacimiento=date(2000, 1, 1),
        tipo_documento=Ciudadano.DOCUMENTO_PASAPORTE,
        documento_pasaporte=numero,
    )


def _geo(sufijo):
    provincia = Provincia.objects.create(nombre=f"Provincia {sufijo}")
    municipio = Municipio.objects.create(
        nombre=f"Municipio {sufijo}", provincia=provincia
    )
    localidad = Localidad.objects.create(
        nombre=f"Localidad {sufijo}", municipio=municipio
    )
    return provincia, municipio, localidad


def _cliente(*codenames):
    user = User.objects.create_user("operador", password="x")
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    client = Client()
    client.force_login(user)
    return client


def _consultas_a_ciudadanos(contexto):
    tabla = Ciudadano._meta.db_table
    return [
        consulta["sql"]
        for consulta in contexto.captured_queries
        if f'"{tabla}"' in consulta["sql"] or f"`{tabla}`" in consulta["sql"]
    ]


def test_form_sin_valor_no_consulta_el_padron_al_renderizar():
    _ciudadano(30111222)
    _ciudadano(30111223)

    with CaptureQueriesContext(connection) as contexto:
        html = str(VoucherForm()["ciudadano"])

    assert _consultas_a_ciudadanos(contexto) == []
    assert "30111222" not in html
    assert "Pérez" not in html


def test_widget_declara_la_busqueda_remota():
    attrs = InscripcionForm().fields["ciudadano"].widget.attrs

    assert attrs["data-ajax--url"] == reverse("vat_ajax_buscar_ciudadanos")
    assert attrs["data-minimum-input-length"] == 6


def test_form_con_initial_muestra_solo_la_persona_elegida():
    elegido = _ciudadano(30111222)
    otro = _ciudadano(30111223, apellido="Gómez")

    form = VoucherForm(initial={"ciudadano": str(elegido.pk)})

    assert list(form.fields["ciudadano"].queryset) == [elegido]
    assert str(otro) not in str(form["ciudadano"])


def test_form_acepta_el_ciudadano_enviado():
    ciudadano = _ciudadano(30111222)
    programa = Programa.objects.create(nombre="Programa VAT")

    form = VoucherForm(
        {
            "ciudadano": ciudadano.pk,
            "programa": programa.pk,
            "cantidad_inicial": 2,
            "fecha_vencimiento": "2099-01-01",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["ciudadano"] == ciudadano


@pytest.mark.parametrize("valor", ["abc", "999999"])
def test_form_rechaza_un_ciudadano_invalido_sin_romper(valor):
    form = VoucherForm({"ciudadano": valor})

    assert not form.is_valid()
    assert "ciudadano" in form.errors


def test_form_de_resultado_no_carga_las_inscripciones():
    form = ResultadoEvaluacionForm()

    assert not form.fields["inscripcion"].queryset.exists()
    assert form.fields["inscripcion"].widget.attrs["data-ajax--url"] == reverse(
        "vat_ajax_buscar_inscripciones"
    )
    assert form.fields["inscripcion"].widget.attrs["data-minimum-input-length"] == 7


def test_opciones_ciudadano_busca_por_documento():
    ciudadano = _ciudadano(30111222)
    _ciudadano(40111222)

    assert service.opciones_ciudadano(" 3011122 ") == [
        {"id": ciudadano.pk, "text": "Pérez, Ana (30111222)"}
    ]


def test_opciones_ciudadano_busca_por_pasaporte():
    ciudadano = _pasaporte("AB123456")

    assert service.opciones_ciudadano("ab 1234") == [
        {"id": ciudadano.pk, "text": "Silva, Joao (Pasaporte AB123456)"}
    ]


@pytest.mark.parametrize("texto", ["", None, "301112", "Pérez", "abc"])
def test_opciones_ciudadano_no_busca_por_nombre_ni_prefijos_cortos(texto):
    _ciudadano(30111222)

    assert service.opciones_ciudadano(texto) == []


def test_opciones_ciudadano_acota_los_resultados(monkeypatch):
    monkeypatch.setattr(service, "LIMITE_OPCIONES", 2)
    for sufijo in range(3):
        _ciudadano(30111220 + sufijo)

    assert len(service.opciones_ciudadano("3011122")) == 2


def _inscripcion_en_centro(ciudadano, *, sufijo, referente):
    provincia, municipio, localidad = _geo(sufijo)
    centro = _centro_basico(
        f"Centro {sufijo}", f"10{sufijo}", provincia, municipio, localidad, referente
    )
    modalidad = ModalidadCursada.objects.create(nombre=f"Modalidad {sufijo}")
    comision = _build_comision_curso(
        centro=centro, localidad=localidad, modalidad=modalidad, suffix=sufijo
    )
    return Inscripcion.objects.create(
        ciudadano=ciudadano,
        comision_curso=comision,
        programa=Programa.objects.create(nombre=f"Programa {sufijo}"),
        estado="inscripta",
    )


def test_opciones_inscripcion_filtra_por_documento_y_alcance():
    referente = User.objects.create_user("referente", password="x")
    _grant_referente_role(referente)
    ciudadano = _ciudadano(30111222)
    visible = _inscripcion_en_centro(ciudadano, sufijo="1", referente=referente)
    _inscripcion_en_centro(ciudadano, sufijo="2", referente=None)
    _inscripcion_en_centro(_ciudadano(40111222), sufijo="3", referente=referente)

    assert service.opciones_inscripcion(referente, "30111222") == [
        {"id": visible.pk, "text": str(visible)}
    ]


@pytest.mark.parametrize("texto", ["", None, "301112", "Pérez", "99999999"])
def test_opciones_inscripcion_sin_documento_valido_no_consulta(mocker, texto):
    base = mocker.patch.object(service, "base_inscripciones_queryset_for_user")

    assert service.opciones_inscripcion(object(), texto) == []
    base.assert_not_called()


def test_vista_de_ciudadanos_devuelve_el_formato_de_select2():
    ciudadano = _ciudadano(30111222)
    client = _cliente("add_voucher")

    respuesta = client.get(reverse("vat_ajax_buscar_ciudadanos"), {"q": "30111222"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "results": [{"id": ciudadano.pk, "text": "Pérez, Ana (30111222)"}]
    }


def test_vista_de_ciudadanos_exige_permiso_de_vat():
    _ciudadano(30111222)
    client = _cliente("view_voucher")

    respuesta = client.get(reverse("vat_ajax_buscar_ciudadanos"), {"q": "30111222"})

    assert respuesta.status_code != 200


def test_vista_de_inscripciones_exige_permiso_de_resultados():
    client = _cliente("add_voucher")

    respuesta = client.get(reverse("vat_ajax_buscar_inscripciones"), {"q": "30111222"})

    assert respuesta.status_code != 200


def test_vista_de_inscripciones_sin_query_responde_vacio():
    client = _cliente("add_resultadoevaluacion")

    respuesta = client.get(reverse("vat_ajax_buscar_inscripciones"))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"results": []}


@pytest.mark.parametrize(
    "url_name",
    [
        "vat_inscripcion_create",
        "vat_inscripcion_oferta_create",
        "vat_voucher_create",
        "vat_resultado_evaluacion_create",
    ],
)
def test_alta_renderiza_sin_listar_al_padron(url_name):
    ciudadano = _ciudadano(30111222, apellido="Padrón")
    _inscripcion_en_centro(ciudadano, sufijo="1", referente=None)
    admin = User.objects.create_superuser("admin", password="x")
    client = Client()
    client.force_login(admin)

    respuesta = client.get(reverse(url_name))

    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "data-ajax--url" in html
    assert "Padrón" not in html


def test_editar_voucher_preseleccionado_por_query_string():
    ciudadano = _ciudadano(30111222, apellido="Elegida")
    admin = User.objects.create_superuser("admin", password="x")
    client = Client()
    client.force_login(admin)

    respuesta = client.get(reverse("vat_voucher_create"), {"ciudadano": ciudadano.pk})

    assert respuesta.status_code == 200
    assert "Elegida" in respuesta.content.decode()
