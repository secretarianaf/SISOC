"""Web API (G1 v1) of the comedor PNUD/Abordaje convenio (CO07.03).

The endpoint runs the native ``ComedorDatosConvenioPnudUpdateView``; these tests
check the projection of the real variant forms, the persisted effects (Decimal
montos included), that every rejection leaves the record unchanged and the
access in front of the view.
"""

from decimal import Decimal

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.forms.convenio_pnud_form import PRESTACIONES_APROBADAS_FIELDS
from comedores.models import Comedor, ComedorDatosConvenioPnud, Programas
from duplas.models import Dupla

pytestmark = pytest.mark.django_db
User = get_user_model()
ROOT = "/api/web/comedores/comedores/"
MONTOS = (
    "monto_total_conveniado",
    "monto_convenio_prestaciones_alimentarias",
    "monto_convenio_siph",
)


@pytest.fixture(name="comedor_fixture", autouse=True)
def sin_dobles_del_conftest():
    """Same name as the folder's autouse double: these tests run the real services."""


def _perm(user, code):
    app, codename = code.split(".")
    if app == "auth":
        permiso = Permission.objects.get_or_create(
            codename=codename,
            content_type=ContentType.objects.get_for_model(User),
            defaults={"name": codename},
        )[0]
    else:
        permiso = Permission.objects.get(content_type__app_label=app, codename=codename)
    user.user_permissions.add(permiso)


def _user(username, *codes):
    user = User.objects.create_user(username, password="x")
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        _perm(user, code)
    return user


def _client(user, enforce_csrf=False):
    client = Client(enforce_csrf_checks=enforce_csrf)
    client.force_login(user)
    return client


def _url(comedor):
    return f"{ROOT}{comedor.pk}/convenio-pnud/"


def _comedor(programa, nombre="Comedor Convenio", **extra):
    return Comedor.objects.create(
        nombre=nombre,
        programa=Programas.objects.create(nombre=programa),
        **extra,
    )


@pytest.fixture(name="gestor")
def gestor_fixture():
    return _client(_user("gestor_k5conv", "comedores.change_comedor"))


@pytest.fixture(name="resto")
def resto_fixture():
    return _comedor("PNUD")


@pytest.fixture(name="secos")
def secos_fixture():
    return _comedor("Abordaje Comunitario - Linea Secos", "Comedor Secos")


@pytest.fixture(name="tradicional")
def tradicional_fixture():
    return _comedor("Abordaje Comunitario - Linea Tradicional", "Comedor Tradicional")


def _matriz(tipo, valor=1):
    """The weekly matrix the variant renders (every column the form keeps)."""
    if tipo == "secos":
        return {}
    return {
        n: str(valor)
        for n in PRESTACIONES_APROBADAS_FIELDS
        if tipo == "tradicional" or "reforzada" not in n
    }


def _datos(tipo, **extra):
    return {"nro_convenio": "CV-1", **_matriz(tipo), **extra}


def _snapshot(comedor):
    datos = ComedorDatosConvenioPnud.objects.filter(comedor=comedor).first()
    if datos is None:
        return None
    return {
        c.name: getattr(datos, c.name)
        for c in ComedorDatosConvenioPnud._meta.concrete_fields
    }


def _mensajes(respuesta):
    return [str(m) for m in messages.get_messages(respuesta.wsgi_request)]


def test_access_anonymous_401_reader_403_and_csrf_403(resto):
    lector = _client(_user("lector_k5conv", "comedores.view_comedor"))
    estricto = _client(
        _user("estricto_k5conv", "comedores.change_comedor"), enforce_csrf=True
    )

    assert Client().get(_url(resto)).status_code == 401
    assert Client().post(_url(resto), {}).status_code == 401
    assert lector.get(_url(resto)).status_code == 403
    assert lector.post(_url(resto), _datos("resto")).status_code == 403
    assert estricto.post(_url(resto), {"nro_convenio": "X"}).status_code == 403
    assert not ComedorDatosConvenioPnud.objects.exists()


def test_get_projects_the_resto_variant_in_form_order_with_prefill(gestor, resto):
    resto.codigo_de_proyecto = "PRY-7"
    resto.save()

    datos = gestor.get(_url(resto)).json()["form"]

    nombres = [f["name"] for f in datos["fields"]]
    assert nombres[:4] == [
        "monto_total_conveniado",
        "nro_convenio",
        "monto_convenio_prestaciones_alimentarias",
        "monto_convenio_siph",
    ]
    assert "prestaciones_financiadas_mensuales" in nombres
    assert "cantidad_modulos" in nombres
    assert not [n for n in nombres if "diarias" in n or "reforzada" in n]
    assert len([n for n in nombres if n.startswith("aprobadas_")]) == 28
    assert datos["es_linea_secos"] is False and datos["es_linea_tradicional"] is False
    assert datos["prefill"]["codigo_proyecto"] == "PRY-7"
    assert datos["prefill"]["nombre_espacio"] == "Comedor Convenio"
    assert datos["prefill"]["domicilio_completo"] == "Sin información"
    assert datos["urls"]["ficha"] == f"/comedores/{resto.pk}"
    campos = {f["name"]: f for f in datos["fields"]}
    assert campos["monto_total_conveniado"]["monto"] is True
    assert campos["monto_total_conveniado"]["type"] == "text"
    assert campos["monto_total_conveniado"]["attrs"]["inputmode"] == "numeric"
    assert campos["aprobadas_desayuno_lunes"]["required"] is True
    assert campos["aprobadas_desayuno_lunes"]["value"] == "0"
    assert campos["aprobadas_desayuno_lunes"]["attrs"]["min"] == "0"
    assert campos["nro_convenio"]["attrs"]["maxlength"] == "120"


def test_get_projects_the_secos_and_tradicional_variants(gestor, secos, tradicional):
    en_secos = gestor.get(_url(secos)).json()["form"]
    en_tradicional = gestor.get(_url(tradicional)).json()["form"]

    secos_nombres = [f["name"] for f in en_secos["fields"]]
    assert en_secos["es_linea_secos"] is True
    assert "cantidad_modulos" in secos_nombres
    assert not [
        n
        for n in secos_nombres
        if n.startswith("aprobadas_")
        or "diarias" in n
        or n == "prestaciones_financiadas_mensuales"
    ]
    tradicional_nombres = [f["name"] for f in en_tradicional["fields"]]
    assert en_tradicional["es_linea_tradicional"] is True
    assert len([n for n in tradicional_nombres if n.startswith("aprobadas_")]) == 35
    assert len([n for n in tradicional_nombres if "diarias" in n]) == 5
    assert "cantidad_modulos" not in tradicional_nombres
    assert "prestaciones_financiadas_mensuales" not in tradicional_nombres


def test_get_creates_the_empty_record_once_as_the_native_view_does(gestor, resto):
    gestor.get(_url(resto))
    gestor.get(_url(resto))

    assert ComedorDatosConvenioPnud.objects.filter(comedor=resto).count() == 1


def test_a_comedor_that_does_not_use_the_convenio_gets_the_native_redirect(gestor):
    otro = _comedor("Alimentar Comunidad", "Comedor Otro")

    otro_cliente = _client(_user("otro_k5conv", "comedores.change_comedor"))
    respuesta = gestor.get(_url(otro))
    posteo = otro_cliente.post(_url(otro), _datos("resto", nro_convenio="X"))

    for resp in (respuesta, posteo):
        assert resp.status_code == 200
        assert resp.json() == {"redirect": f"/comedores/{otro.pk}"}
        assert _mensajes(resp) == [
            "Esta opcion solo aplica para comedores PNUD o Abordaje Comunitario."
        ]
    assert not ComedorDatosConvenioPnud.objects.exists()


def test_outside_the_scope_is_404_and_creates_nothing(resto):
    abogado = _user("abogado_k5conv", "auth.role_abogado_dupla")
    dupla = Dupla.objects.create(nombre="Otra", estado="Activo", abogado=abogado)
    comedor = _comedor("PNUD", "Comedor Ajeno", dupla=dupla)
    ajeno = _client(
        _user("ajeno_k5conv", "comedores.change_comedor", "auth.role_tecnico_comedor")
    )

    assert ajeno.get(_url(comedor)).status_code == 404
    assert ajeno.post(_url(comedor), _datos("resto")).status_code == 404
    assert not ComedorDatosConvenioPnud.objects.exists()


def test_post_saves_decimal_montos_counts_and_the_matrix_and_goes_to_the_ficha(
    gestor, resto
):
    respuesta = gestor.post(
        _url(resto),
        _datos(
            "resto",
            monto_total_conveniado="100.000.000",
            monto_convenio_prestaciones_alimentarias="2500",
            monto_convenio_siph="",
            prestaciones_financiadas_mensuales="120",
            personas_conveniadas="30",
            personas_declaradas_siph="5",
            cantidad_modulos="2",
            aprobadas_cena_domingo="9",
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": f"/comedores/{resto.pk}"}
    assert _mensajes(respuesta) == []
    datos = ComedorDatosConvenioPnud.objects.get(comedor=resto)
    assert datos.monto_total_conveniado == Decimal("100000000.00")
    assert datos.monto_convenio_prestaciones_alimentarias == Decimal("2500.00")
    assert datos.monto_convenio_siph is None
    assert datos.nro_convenio == "CV-1"
    assert (datos.prestaciones_financiadas_mensuales, datos.personas_conveniadas) == (
        120,
        30,
    )
    assert (datos.personas_declaradas_siph, datos.cantidad_modulos) == (5, 2)
    assert datos.aprobadas_cena_domingo == 9 and datos.aprobadas_desayuno_lunes == 1


@pytest.mark.parametrize(
    "monto", ["1000,5", "1000.5", "10.00", "1.2345", "abc", "$100"]
)
def test_a_decimal_or_malformed_monto_is_rejected_with_the_native_message(
    gestor, resto, monto
):
    gestor.get(_url(resto))
    antes = _snapshot(resto)

    respuesta = gestor.post(_url(resto), _datos("resto", monto_total_conveniado=monto))

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["errors"]["monto_total_conveniado"] == [
        "Ingresá un monto sin decimales, por ejemplo 100.000.000."
    ]
    campos = {f["name"]: f for f in cuerpo["form"]["fields"]}
    assert campos["monto_total_conveniado"]["value"] == monto
    assert campos["monto_total_conveniado"]["errors"]
    assert _snapshot(resto) == antes


def test_editing_another_field_keeps_the_historical_cents(gestor, resto):
    datos = ComedorDatosConvenioPnud.objects.create(
        comedor=resto,
        monto_total_conveniado=Decimal("1234.56"),
        monto_convenio_siph=Decimal("99.50"),
    )
    web = gestor.get(_url(resto)).json()["form"]["fields"]
    visibles = {f["name"]: f["value"] for f in web}
    assert visibles["monto_total_conveniado"] == "1.235"
    assert visibles["monto_convenio_siph"] == "100"

    respuesta = gestor.post(
        _url(resto),
        _datos(
            "resto",
            monto_total_conveniado=visibles["monto_total_conveniado"],
            monto_convenio_siph=visibles["monto_convenio_siph"],
            personas_conveniadas="44",
        ),
    )

    assert respuesta.status_code == 200
    datos.refresh_from_db()
    assert datos.monto_total_conveniado == Decimal("1234.56")
    assert datos.monto_convenio_siph == Decimal("99.50")
    assert datos.personas_conveniadas == 44


def test_changing_the_visible_monto_replaces_the_cents(gestor, resto):
    datos = ComedorDatosConvenioPnud.objects.create(
        comedor=resto, monto_total_conveniado=Decimal("1234.56")
    )

    gestor.post(_url(resto), _datos("resto", monto_total_conveniado="1.300"))

    datos.refresh_from_db()
    assert datos.monto_total_conveniado == Decimal("1300.00")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("personas_conveniadas", "-1"),
        ("cantidad_modulos", "-3"),
        ("prestaciones_financiadas_mensuales", "1.5"),
        ("aprobadas_cena_lunes", "-2"),
        ("aprobadas_cena_lunes", ""),
        ("nro_convenio", "x" * 121),
    ],
)
def test_invalid_counts_matrix_and_numero_are_rejected_and_change_nothing(
    gestor, resto, campo, valor
):
    gestor.get(_url(resto))
    antes = _snapshot(resto)

    respuesta = gestor.post(_url(resto), _datos("resto", **{campo: valor}))

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"][campo]
    assert _snapshot(resto) == antes


def test_the_secos_variant_keeps_the_values_of_the_fields_it_does_not_render(
    gestor, secos
):
    datos = ComedorDatosConvenioPnud.objects.create(
        comedor=secos,
        prestaciones_financiadas_mensuales=7,
        prestaciones_financiadas_diarias_cena=3,
        aprobadas_desayuno_lunes=5,
    )

    respuesta = gestor.post(
        _url(secos),
        {
            "nro_convenio": "SEC-1",
            "personas_conveniadas": "8",
            "prestaciones_financiadas_mensuales": "999",
            "prestaciones_financiadas_diarias_cena": "999",
            "aprobadas_desayuno_lunes": "999",
        },
    )

    assert respuesta.status_code == 200
    datos.refresh_from_db()
    assert datos.nro_convenio == "SEC-1" and datos.personas_conveniadas == 8
    assert datos.prestaciones_financiadas_mensuales == 7
    assert datos.prestaciones_financiadas_diarias_cena == 3
    assert datos.aprobadas_desayuno_lunes == 5


def test_the_tradicional_variant_does_not_zero_the_omitted_modulos(gestor, tradicional):
    datos = ComedorDatosConvenioPnud.objects.create(
        comedor=tradicional, cantidad_modulos=4, prestaciones_financiadas_mensuales=6
    )

    respuesta = gestor.post(
        _url(tradicional),
        _datos(
            "tradicional",
            personas_conveniadas="2",
            prestaciones_financiadas_diarias_desayuno="3",
        ),
    )

    assert respuesta.status_code == 200
    datos.refresh_from_db()
    assert (datos.cantidad_modulos, datos.prestaciones_financiadas_mensuales) == (4, 6)
    assert datos.prestaciones_financiadas_diarias_desayuno == 3


def test_only_get_head_and_post_are_served(gestor, resto):
    assert gestor.put(_url(resto), {}).status_code == 405
    assert gestor.delete(_url(resto)).status_code == 405
