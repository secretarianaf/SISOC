import pytest
from django.contrib.auth.models import Group, User

from core.constants import UserGroups
from centrodefamilia.forms import CentroForm

GRUPO_ACTUAL = UserGroups.CDF_REFERENTE_CENTRO
GRUPO_LEGACY = "ReferenteCentro"


def _usuario_en_grupo(username, grupo_nombre=None):
    user = User.objects.create_user(username=username, password="test1234")
    if grupo_nombre:
        grupo, _ = Group.objects.get_or_create(name=grupo_nombre)
        user.groups.add(grupo)
    return user


@pytest.mark.django_db
def test_referente_incluye_usuarios_del_grupo_cdf_referente_centro():
    """Regresión: el form filtraba solo por el grupo legacy "ReferenteCentro" y
    los usuarios generados con el grupo actual no aparecían en el campo."""
    referente = _usuario_en_grupo("ref-cdf", GRUPO_ACTUAL)

    queryset = CentroForm().fields["referente"].queryset

    assert referente in queryset


@pytest.mark.django_db
def test_referente_conserva_usuarios_del_grupo_legacy():
    referente_legacy = _usuario_en_grupo("ref-legacy", GRUPO_LEGACY)

    queryset = CentroForm().fields["referente"].queryset

    assert referente_legacy in queryset


@pytest.mark.django_db
def test_referente_excluye_usuarios_sin_grupo_de_referente():
    otro = _usuario_en_grupo("sin-grupo")

    queryset = CentroForm().fields["referente"].queryset

    assert otro not in queryset


@pytest.mark.django_db
def test_referente_en_ambos_grupos_aparece_una_sola_vez():
    referente = _usuario_en_grupo("ref-doble", GRUPO_ACTUAL)
    grupo_legacy, _ = Group.objects.get_or_create(name=GRUPO_LEGACY)
    referente.groups.add(grupo_legacy)

    queryset = CentroForm().fields["referente"].queryset

    assert list(queryset.filter(pk=referente.pk)) == [referente]


@pytest.mark.django_db
def test_centro_guarda_coordenadas_y_conserva_domicilio(client, django_user_model):
    referente = _usuario_en_grupo("ref-pin", GRUPO_ACTUAL)
    form = CentroForm(
        data={
            "tipo": "faro",
            "nombre": "Centro prueba",
            "codigo": "pin-test",
            "referente": referente.pk,
            "domicilio_actividad": "Calle 123",
            "telefono": "123456",
            "celular": "123456",
            "correo": "centro@example.com",
            "nombre_referente": "Prueba",
            "apellido_referente": "Centro",
            "telefono_referente": "123456",
            "correo_referente": "ref@example.com",
            "latitud": "-34.123456",
            "longitud": "-58.123456",
            "calle": "Calle",
            "numero": "123",
        }
    )
    # La provincia del modelo es anulable, pero el formulario la exige.
    from core.models import Provincia

    form.data = {
        **form.data,
        "provincia": Provincia.objects.create(nombre="Buenos Aires").pk,
    }
    assert form.is_valid(), form.errors
    centro = form.save()
    centro.refresh_from_db()
    assert str(centro.latitud) == "-34.123456"
    assert str(centro.longitud) == "-58.123456"
    assert (centro.calle, centro.numero) == ("Calle", 123)
    from django.urls import reverse

    client.force_login(
        django_user_model.objects.create_superuser(
            username="cdf-pin-admin", password="test"
        )
    )
    response = client.get(reverse("centro_detail", args=[centro.pk]))
    assert response.status_code == 200
    assert b"q=-34.123456,-58.123456" in response.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "values",
    [
        {"latitud": "91", "longitud": "0"},
        {"latitud": "0", "longitud": "181"},
        {"latitud": "-34"},
    ],
)
def test_centro_rechaza_coordenadas_invalidas(values):
    form = CentroForm(data=values)
    assert not form.is_valid()
    assert (
        "latitud" in form.errors
        or "longitud" in form.errors
        or "Complete latitud y longitud" in str(form.non_field_errors())
    )
