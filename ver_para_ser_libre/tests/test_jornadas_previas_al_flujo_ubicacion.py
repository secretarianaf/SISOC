"""Compatibilidad de datos previos al flujo de ubicacion por jornada."""

from datetime import date
from decimal import Decimal
from importlib import import_module
from urllib.request import Request

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.models import Localidad, Municipio, Provincia
from ver_para_ser_libre.forms import JornadaVPSLForm
from ver_para_ser_libre.models import (
    ChecklistJornadaVPSL,
    EstadoEvaluacionVPSL,
    EstadoItinerario,
    ItinerarioVPSL,
    JornadaVPSL,
    RegistroNominalVPSL,
    ResultadoAtencion,
    SedeVPSL,
)
from ver_para_ser_libre.services import map_location

pytestmark = pytest.mark.django_db

migracion_checklist = import_module(
    "ver_para_ser_libre.migrations.0016_copiar_checklist_sede_a_jornadas"
)


def _crear_itinerario():
    return ItinerarioVPSL.objects.create(
        provincia=Provincia.objects.create(nombre="Buenos Aires"),
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
        referente_nombre="Referente",
        referente_telefono="11111111",
        referente_email="referente@example.com",
        carta_archivo=SimpleUploadedFile("carta.pdf", b"contenido"),
        carta_archivo_estado=EstadoEvaluacionVPSL.APROBADO,
        estado=EstadoItinerario.APROBADO,
    )


def _crear_jornada_previa(itinerario, sede, fecha=date(2026, 9, 15)):
    # Jornada cargada con el flujo anterior: sede del catalogo, sin localidad
    # ni ubicacion propias.
    return JornadaVPSL.objects.create(
        itinerario=itinerario, fecha=fecha, sede_vpsl=sede
    )


def _crear_sede():
    return SedeVPSL.objects.create(
        jurisdiccion="Buenos Aires",
        localidad="Berazategui",
        nombre="Escuela 12",
        domicilio="Calle 14 1234",
    )


def _datos_formulario_jornada(jornada, **overrides):
    datos = {
        "fecha": jornada.fecha.isoformat(),
        "sede": jornada.sede,
        "localidad": jornada.localidad_id or "",
        "ubicacion_url": jornada.ubicacion_url,
        "direccion": jornada.direccion,
        "horario_inicio": "10:00",
        "horario_fin": "18:00",
        "referente_dni": "",
        "referente_sexo": "",
        "referente_telefono": "",
        "observaciones": "",
    }
    datos.update(overrides)
    return datos


def test_jornada_previa_muestra_y_exporta_localidad_de_la_sede(client):
    itinerario = _crear_itinerario()
    jornada = _crear_jornada_previa(itinerario, _crear_sede())
    client.force_login(
        get_user_model().objects.create_superuser(username="vpsl-localidad-previa")
    )

    assert jornada.localidad_display == "Berazategui"
    detalle = client.get(reverse("vpsl_jornada_detail", kwargs={"pk": jornada.pk}))
    itinerario_detalle = client.get(
        reverse("vpsl_itinerario_detail", kwargs={"pk": itinerario.pk})
    )
    csv_itinerario = b"".join(
        client.get(
            reverse("vpsl_itinerario_export", kwargs={"pk": itinerario.pk})
        ).streaming_content
    ).decode("utf-8")
    csv_jornada = b"".join(
        client.get(
            reverse("vpsl_jornada_export", kwargs={"pk": jornada.pk})
        ).streaming_content
    ).decode("utf-8")

    assert "Berazategui" in detalle.content.decode()
    assert "Berazategui" in itinerario_detalle.content.decode()
    assert "Berazategui" in csv_itinerario
    assert "Berazategui" in csv_jornada


def test_localidad_propia_tiene_prioridad_sobre_la_sede():
    itinerario = _crear_itinerario()
    localidad = Localidad.objects.create(
        nombre="Quilmes",
        municipio=Municipio.objects.create(
            nombre="Quilmes", provincia=itinerario.provincia
        ),
    )
    jornada = _crear_jornada_previa(itinerario, _crear_sede())
    jornada.localidad = localidad

    assert jornada.localidad_display == "Quilmes"


def test_migracion_copia_checklist_de_sede_a_cada_jornada_y_revierte():
    itinerario = _crear_itinerario()
    sede = _crear_sede()
    primera = _crear_jornada_previa(itinerario, sede)
    segunda = _crear_jornada_previa(itinerario, sede, fecha=date(2026, 9, 16))
    ChecklistJornadaVPSL.objects.create(
        jornada=primera, sede=sede, item="electricidad", cumple=True
    )
    ChecklistJornadaVPSL.objects.create(
        jornada=primera, sede=sede, item="seguridad", cumple=False, observacion="x"
    )

    migracion_checklist.copiar_checklist_de_sede_a_jornadas(apps, None)
    migracion_checklist.copiar_checklist_de_sede_a_jornadas(apps, None)

    copiados = {fila.item: fila for fila in segunda.checklist.all()}
    assert set(copiados) == {"electricidad", "seguridad"}
    assert copiados["electricidad"].cumple is True
    assert copiados["seguridad"].observacion == "x"
    assert primera.checklist.count() == 2

    migracion_checklist.eliminar_copias_de_checklist(apps, None)

    assert not segunda.checklist.exists()
    assert primera.checklist.count() == 2


def test_jornada_previa_se_edita_sin_ubicacion_ni_localidad():
    itinerario = _crear_itinerario()
    jornada = _crear_jornada_previa(itinerario, _crear_sede())

    form = JornadaVPSLForm(
        data=_datos_formulario_jornada(jornada),
        instance=jornada,
        itinerario=itinerario,
    )

    assert not form.fields["ubicacion_url"].required
    assert not form.fields["localidad"].required
    assert form.is_valid(), form.errors


def test_jornada_nueva_sigue_exigiendo_ubicacion_y_localidad():
    itinerario = _crear_itinerario()
    form = JornadaVPSLForm(itinerario=itinerario)

    assert form.fields["ubicacion_url"].required
    assert form.fields["localidad"].required


def test_cambiar_ubicacion_actualiza_direccion_no_editada(monkeypatch):
    itinerario = _crear_itinerario()
    localidad = Localidad.objects.create(
        nombre="Quilmes",
        municipio=Municipio.objects.create(
            nombre="Quilmes", provincia=itinerario.provincia
        ),
    )
    jornada = JornadaVPSL.objects.create(
        itinerario=itinerario,
        fecha=date(2026, 9, 15),
        sede="Escuela",
        localidad=localidad,
        direccion="Direccion anterior",
        ubicacion_url="https://maps.app.goo.gl/anterior",
        latitud=Decimal("-34.600000"),
        longitud=Decimal("-58.300000"),
    )
    monkeypatch.setattr(
        map_location,
        "_resolve_short_url",
        lambda *_args, **_kwargs: (
            "https://www.google.com/maps/search/?api=1&query=Calle+Nueva+100"
        ),
    )

    form = JornadaVPSLForm(
        data=_datos_formulario_jornada(
            jornada, ubicacion_url="https://maps.app.goo.gl/nuevo"
        ),
        instance=jornada,
        itinerario=itinerario,
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["direccion"] == "Calle Nueva 100"


def test_registro_previo_a_graduacion_se_edita_sin_graduacion():
    jornada = _crear_jornada_previa(_crear_itinerario(), _crear_sede())
    datos = {
        "jornada": jornada,
        "dni": "30111222",
        "nombre": "Ana",
        "apellido": "Perez",
        "numero_acta": "1",
        "resultado": ResultadoAtencion.ENTREGADO_DIA,
        "cantidad_lentes": 1,
    }
    registro_previo = RegistroNominalVPSL.objects.create(**datos)

    RegistroNominalVPSL.objects.get(pk=registro_previo.pk).full_clean()

    nuevo = RegistroNominalVPSL(**{**datos, "numero_acta": "2"})
    with pytest.raises(ValidationError) as exc:
        nuevo.full_clean()
    assert "graduacion_izquierda" in exc.value.message_dict


def test_registro_que_pasa_a_requerir_graduacion_la_exige():
    jornada = _crear_jornada_previa(_crear_itinerario(), _crear_sede())
    registro = RegistroNominalVPSL.objects.create(
        jornada=jornada,
        dni="30111222",
        nombre="Ana",
        apellido="Perez",
        numero_acta="1",
        resultado=ResultadoAtencion.NO_REQUIERE,
    )
    registro = RegistroNominalVPSL.objects.get(pk=registro.pk)
    registro.resultado = ResultadoAtencion.DERIVADO

    with pytest.raises(ValidationError) as exc:
        registro.full_clean()
    assert "graduacion_derecha" in exc.value.message_dict


def test_redireccion_fuera_de_google_se_rechaza():
    handler = map_location._SafeGoogleRedirectHandler()
    request = Request("https://maps.app.goo.gl/abc", method="HEAD")

    with pytest.raises(ValidationError):
        handler.redirect_request(
            request, None, 302, "Found", {}, "https://169.254.169.254/latest"
        )
    permitido = handler.redirect_request(
        request, None, 302, "Found", {}, "https://www.google.com/maps/place/X"
    )
    assert permitido.full_url == "https://www.google.com/maps/place/X"


def test_enlace_de_lugar_prioriza_coordenadas_del_pin(monkeypatch):
    monkeypatch.setattr(
        map_location,
        "_resolve_short_url",
        lambda *_args, **_kwargs: (
            "https://www.google.com/maps/place/Escuela/@-34.610000,-58.390000,17z/"
            "data=!3m1!4b1!4m6!3m5!1s0x0:0x0!8m2!3d-34.603700!4d-58.381600"
        ),
    )

    location = map_location.resolve_google_maps_location(
        "https://maps.app.goo.gl/lugar"
    )

    assert location.latitude == Decimal("-34.603700")
    assert location.longitude == Decimal("-58.381600")
