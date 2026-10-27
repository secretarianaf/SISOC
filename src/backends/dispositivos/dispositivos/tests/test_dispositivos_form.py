import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Localidad, Municipio, Provincia
from dispositivos.forms import DispositivoForm
from dispositivos.models import Dispositivo


def _base_data(provincia, municipio, **overrides):
    data = {
        "nombre_institucion": "Hogar Test",
        "tipo_gestion": "estatal",
        "cuit_institucion": "20123456789",
        "provincia": provincia.id,
        "municipio": municipio.id,
        "calle": "Calle 1",
        "altura": "123",
        "telefono_prefijo": "221",
        "telefono_numero": "1234567",
        "correo_electronico": "test@example.com",
        "responsable_nombre_completo": "Juan Perez",
        "responsable_dni": "12345678",
        "tipo_dispositivo": "refugio",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "16_30",
        "dias_atencion": ["lunes"],
        "horarios_funcionamiento": ["manana"],
    }
    data.update(overrides)
    return data


def _archivo(nombre, contenido=b"contenido", content_type="application/pdf"):
    return SimpleUploadedFile(nombre, contenido, content_type=content_type)


@pytest.mark.django_db
def test_form_requiere_texto_otro_tipo_dispositivo():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)

    form = DispositivoForm(
        data=_base_data(provincia, municipio, tipo_dispositivo="otro")
    )

    assert not form.is_valid()
    assert "tipo_dispositivo_otro" in form.errors


@pytest.mark.django_db
def test_form_configura_municipios_por_provincia_instancia():
    provincia = Provincia.objects.create(nombre="Mendoza")
    municipio = Municipio.objects.create(nombre="Capital", provincia=provincia)

    form = DispositivoForm(initial={"provincia": provincia.id})
    form.fields["municipio"].queryset = Municipio.objects.filter(provincia=provincia)

    assert municipio in form.fields["municipio"].queryset


@pytest.mark.django_db
def test_form_rechaza_documentacion_con_extension_no_permitida():
    provincia = Provincia.objects.create(nombre="Cordoba")
    municipio = Municipio.objects.create(nombre="Cordoba", provincia=provincia)

    form = DispositivoForm(
        data=_base_data(provincia, municipio),
        files={
            "documentacion_dispositivo": _archivo(
                "documentacion.html",
                b"<script>alert('x')</script>",
                content_type="text/html",
            )
        },
    )

    assert not form.is_valid()
    assert "documentacion_dispositivo" in form.errors


@pytest.mark.django_db
def test_form_rechaza_documentacion_con_content_type_no_permitido():
    provincia = Provincia.objects.create(nombre="Santa Fe")
    municipio = Municipio.objects.create(nombre="Rosario", provincia=provincia)

    form = DispositivoForm(
        data=_base_data(provincia, municipio),
        files={
            "documentacion_dispositivo": _archivo(
                "documentacion.pdf",
                b"texto plano",
                content_type="text/plain",
            )
        },
    )

    assert not form.is_valid()
    assert "documentacion_dispositivo" in form.errors


@pytest.mark.django_db
def test_modelo_rechaza_documentacion_demasiado_grande():
    provincia = Provincia.objects.create(nombre="Chaco")
    municipio = Municipio.objects.create(nombre="Resistencia", provincia=provincia)
    data = _base_data(provincia, municipio)
    data["provincia"] = provincia
    data["municipio"] = municipio
    dispositivo = Dispositivo(
        **data,
        documentacion_dispositivo=_archivo(
            "documentacion.pdf",
            b"x" * ((10 * 1024 * 1024) + 1),
            content_type="application/pdf",
        ),
    )

    with pytest.raises(ValidationError):
        dispositivo.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    ["calle", "altura", "telefono_prefijo", "telefono_numero"],
)
def test_modelo_requiere_contacto_desdoblado(field_name):
    provincia = Provincia.objects.create(nombre="Neuquen")
    municipio = Municipio.objects.create(nombre="Neuquen", provincia=provincia)
    data = _base_data(provincia, municipio)
    data["provincia"] = provincia
    data["municipio"] = municipio
    data[field_name] = ""
    dispositivo = Dispositivo(**data)

    with pytest.raises(ValidationError) as exc_info:
        dispositivo.full_clean()

    assert field_name in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", ["telefono_prefijo", "telefono_numero"])
def test_modelo_rechaza_telefono_desdoblado_no_numerico(field_name):
    provincia = Provincia.objects.create(nombre="Rio Negro")
    municipio = Municipio.objects.create(nombre="Bariloche", provincia=provincia)
    data = _base_data(provincia, municipio)
    data["provincia"] = provincia
    data["municipio"] = municipio
    data[field_name] = "22-abc"
    dispositivo = Dispositivo(**data)

    with pytest.raises(ValidationError) as exc_info:
        dispositivo.full_clean()

    assert field_name in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "coordinates",
    [
        {"latitud": "-91", "longitud": "0"},
        {"latitud": "0", "longitud": "181"},
        {"latitud": "-34.9"},
        {"longitud": "-57.9"},
        {"latitud": "NaN", "longitud": "0"},
    ],
)
def test_form_rechaza_coordenadas_invalidas(coordinates):
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    form = DispositivoForm(data=_base_data(provincia, municipio, **coordinates))
    assert not form.is_valid()
    assert {"latitud", "longitud"} & form.errors.keys()


@pytest.mark.django_db
def test_form_guarda_localidad_coordenadas_y_conserva_domicilio():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    form = DispositivoForm(
        data=_base_data(
            provincia,
            municipio,
            localidad=localidad.pk,
            latitud="-34.900001",
            longitud="-57.900001",
        )
    )
    assert form.is_valid(), form.errors
    dispositivo = form.save()
    dispositivo.refresh_from_db()
    assert dispositivo.localidad == localidad
    assert str(dispositivo.latitud) == "-34.900001"
    assert str(dispositivo.longitud) == "-57.900001"
    assert (dispositivo.calle, dispositivo.altura) == ("Calle 1", "123")
    edit = DispositivoForm(instance=dispositivo)
    assert localidad in edit.fields["localidad"].queryset


@pytest.mark.django_db
def test_form_rechaza_localidad_de_otro_municipio():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    otro = Municipio.objects.create(nombre="Otro", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Otra localidad", municipio=otro)
    form = DispositivoForm(
        data=_base_data(provincia, municipio, localidad=localidad.pk)
    )
    assert not form.is_valid()
    assert "localidad" in form.errors


@pytest.mark.django_db
def test_modelo_rechaza_localidad_de_otro_municipio():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    otro = Municipio.objects.create(nombre="Otro", provincia=provincia)
    data = _base_data(provincia, municipio)
    data.update(
        provincia=provincia,
        municipio=municipio,
        localidad=Localidad.objects.create(nombre="Otra", municipio=otro),
    )
    with pytest.raises(ValidationError) as error:
        Dispositivo(**data).full_clean()
    assert "localidad" in error.value.message_dict
