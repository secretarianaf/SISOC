"""H16 (QA 28/9): ciclo de validación del coordinador en el acta complementaria.

Alta y corrección desde la app -> "Pendiente validación coordinador"; el
coordinador valida o devuelve "A subsanar" desde el backoffice; un acta
``Validado`` no admite más cambios (409 en la API, sin otra revisión en SISOC).
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import ActaComplementaria, PrestacionActaComplementaria
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

PENDIENTE = ActaComplementaria.ESTADO_VALIDACION_PENDIENTE
A_SUBSANAR = ActaComplementaria.ESTADO_VALIDACION_A_SUBSANAR
VALIDADO = ActaComplementaria.ESTADO_VALIDACION_VALIDADO


def _territorial(username, provincia):
    user = get_user_model().objects.create_user(username=username, password="x")
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    return user


def _api(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def zona():
    provincia = Provincia.objects.create(nombre="Prov H16")
    comedor = Comedor.objects.create(nombre="Comedor H16", provincia=provincia)
    return comedor, _territorial("terr_h16", provincia)


def _url(comedor, acta_id=None):
    base = f"/api/territorial/comedores/{comedor.id}/actas-complementarias/"
    return f"{base}{acta_id}/" if acta_id else base


def _acta(comedor, tecnico, **kwargs):
    acta = ActaComplementaria.objects.create(
        comedor=comedor, tecnico=tecnico, observaciones="Original", **kwargs
    )
    PrestacionActaComplementaria.objects.create(
        acta=acta, dias_prestacion="Lunes", tipo_prestacion="Almuerzo"
    )
    return acta


# ------------------------------------------------------------------ API


def test_alta_queda_pendiente_de_validacion(zona):
    comedor, tecnico = zona

    response = _api(tecnico).post(
        _url(comedor),
        {"client_uuid": "acta-h16", "prestaciones": []},
        format="json",
    )

    assert response.status_code == 201, response.content
    data = response.json()
    assert data["estado_validacion"] == PENDIENTE
    assert data["observaciones_coordinador"] is None
    assert data["fecha_revision_coordinador"] is None
    assert ActaComplementaria.objects.get().estado_validacion == PENDIENTE


def test_get_expone_estado_y_observaciones_solo_al_tecnico(zona):
    comedor, tecnico = zona
    otro = _territorial("terr_h16_otro", comedor.provincia)
    _acta(
        comedor,
        tecnico,
        estado_validacion=A_SUBSANAR,
        observaciones_coordinador="Falta la firma",
    )

    propio = _api(tecnico).get(_url(comedor)).json()["items"][0]
    ajeno = _api(otro).get(_url(comedor)).json()["items"][0]
    detalle = _api(tecnico).get(f"/api/territorial/comedores/{comedor.id}/").json()

    assert propio["estado_validacion"] == A_SUBSANAR
    assert propio["observaciones_coordinador"] == "Falta la firma"
    assert ajeno["estado_validacion"] == A_SUBSANAR
    assert ajeno["observaciones_coordinador"] is None
    item = detalle["actas_complementarias"]["items"][0]
    assert item["estado_validacion"] == A_SUBSANAR
    assert item["observaciones_coordinador"] == "Falta la firma"


# El caso sin estado (acta cargada desde el backoffice) ahora es 409: ver
# src/backends/sisoc_core/tests/test_territorial_actas_sin_cargar.py.
@pytest.mark.parametrize("estado_previo", [A_SUBSANAR, PENDIENTE])
def test_correccion_reemplaza_y_vuelve_a_pendiente(zona, estado_previo):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=estado_previo)

    response = _api(tecnico).patch(
        _url(comedor, acta.id),
        {
            "observaciones": "Corregida",
            "fecha_hora": "28/09/2026 10:00",
            "prestaciones": [
                {
                    "dias_prestacion": "Martes",
                    "tipo_prestacion": "Cena",
                    "cantidad_actual": 30,
                    "cantidad_espera": 5,
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.json()["estado_validacion"] == PENDIENTE
    acta.refresh_from_db()
    assert acta.estado_validacion == PENDIENTE
    assert acta.observaciones == "Corregida"
    assert acta.fecha_hora is not None
    filas = list(acta.prestaciones.values_list("dias_prestacion", "cantidad_actual"))
    assert filas == [("Martes", 30)]


def test_correccion_sin_prestaciones_no_toca_la_tabla(zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=A_SUBSANAR)

    _api(tecnico).patch(_url(comedor, acta.id), {"firma": "f.png"}, format="json")

    acta.refresh_from_db()
    assert acta.firma == "f.png"
    assert acta.observaciones == "Original"
    assert acta.prestaciones.count() == 1


def test_correccion_de_validado_da_409(zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=VALIDADO)

    response = _api(tecnico).patch(
        _url(comedor, acta.id), {"observaciones": "Cambio"}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["estado_validacion"] == VALIDADO
    acta.refresh_from_db()
    assert acta.observaciones == "Original"


def test_correccion_solo_del_tecnico_del_acta(zona):
    comedor, tecnico = zona
    otro = _territorial("terr_h16_b", comedor.provincia)
    acta = _acta(comedor, tecnico, estado_validacion=A_SUBSANAR)

    response = _api(otro).patch(
        _url(comedor, acta.id), {"observaciones": "x"}, format="json"
    )

    assert response.status_code == 403
    acta.refresh_from_db()
    assert acta.estado_validacion == A_SUBSANAR


def test_correccion_de_acta_inexistente_o_fuera_de_zona_da_404(zona):
    comedor, tecnico = zona
    lejos = _territorial("terr_h16_lejos", Provincia.objects.create(nombre="Lejos"))
    acta = _acta(comedor, tecnico)

    inexistente = _api(tecnico).patch(_url(comedor, 999999), {}, format="json")
    fuera = _api(lejos).patch(_url(comedor, acta.id), {}, format="json")

    assert inexistente.status_code == 404
    assert fuera.status_code == 404


def test_correccion_con_prestaciones_invalidas_da_400(zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=A_SUBSANAR)

    response = _api(tecnico).patch(
        _url(comedor, acta.id),
        {"prestaciones": [{"cantidad_actual": -1}]},
        format="json",
    )

    assert response.status_code == 400
    acta.refresh_from_db()
    assert acta.estado_validacion == A_SUBSANAR
    assert acta.prestaciones.count() == 1


def test_correccion_con_fecha_invalida_da_400(zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=A_SUBSANAR)

    response = _api(tecnico).patch(
        _url(comedor, acta.id), {"fecha_hora": "ayer"}, format="json"
    )

    assert response.status_code == 400
    acta.refresh_from_db()
    assert acta.estado_validacion == A_SUBSANAR


# ----------------------------------------------------------- backoffice


def _coordinador(client):
    user = get_user_model().objects.create_user(username="coord_h16", password="x")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=["review_relevamiento", "view_relevamiento"],
        )
    )
    client.force_login(user)
    return user


def _revisar(client, acta, **data):
    return client.post(
        reverse(
            "acta_complementaria_revision_coordinador",
            kwargs={"comedor_pk": acta.comedor_id, "pk": acta.id},
        ),
        data,
    )


def test_coordinador_valida_el_acta(client, zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=PENDIENTE)
    coordinador = _coordinador(client)

    response = _revisar(client, acta, estado_validacion=VALIDADO)

    assert response.status_code == 302
    acta.refresh_from_db()
    assert acta.estado_validacion == VALIDADO
    assert acta.coordinador_id == coordinador.id
    assert acta.fecha_revision_coordinador is not None


def test_coordinador_devuelve_con_observaciones(client, zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=PENDIENTE)
    _coordinador(client)

    sin_obs = _revisar(client, acta, estado_validacion=A_SUBSANAR)
    acta.refresh_from_db()
    assert acta.estado_validacion == PENDIENTE
    assert "debe indicar qué corregir" in " ".join(
        str(m) for m in get_messages(sin_obs.wsgi_request)
    )

    _revisar(
        client,
        acta,
        estado_validacion=A_SUBSANAR,
        observaciones_coordinador="Falta el domicilio",
    )
    acta.refresh_from_db()
    assert acta.estado_validacion == A_SUBSANAR
    assert acta.observaciones_coordinador == "Falta el domicilio"


def test_acta_validada_no_admite_otra_revision(client, zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=VALIDADO)
    _coordinador(client)

    response = _revisar(
        client,
        acta,
        estado_validacion=A_SUBSANAR,
        observaciones_coordinador="Volver",
    )

    acta.refresh_from_db()
    assert acta.estado_validacion == VALIDADO
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        "El acta complementaria ya está validada: no admite otra revisión."
    ]


def test_revision_exige_permiso(client, zona):
    comedor, tecnico = zona
    acta = _acta(comedor, tecnico, estado_validacion=PENDIENTE)
    client.force_login(
        get_user_model().objects.create_user(username="sin_perm_h16", password="x")
    )

    _revisar(client, acta, estado_validacion=VALIDADO)

    acta.refresh_from_db()
    assert acta.estado_validacion == PENDIENTE


@pytest.mark.parametrize("estado, visible", [(PENDIENTE, True), (VALIDADO, False)])
def test_detalle_muestra_revisar_y_estado(client, zona, estado, visible):
    comedor, tecnico = zona
    acta = _acta(
        comedor,
        tecnico,
        estado_validacion=estado,
        observaciones_coordinador="Nota del coordinador",
    )
    _coordinador(client)

    html = client.get(
        reverse(
            "acta_complementaria_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": acta.id},
        )
    ).content.decode()
    listado = client.get(
        reverse("relevamientos", kwargs={"comedor_pk": comedor.id})
    ).content.decode()

    assert ('data-bs-target="#modalRevisionActa"' in html) is visible
    assert estado in html
    assert "Nota del coordinador" in html
    assert estado in listado


def test_acta_asignada_sin_cargar_no_se_revisa_hasta_que_la_completen(client, zona):
    """Un acta asignada desde SISOC nace vacía y sin enviar: validarla antes de
    que el territorial la cargue la bloquearía para siempre (Validado es
    definitivo). Una vez completada desde la app, se revisa normalmente."""
    comedor, tecnico = zona
    acta = ActaComplementaria.objects.create(
        comedor=comedor,
        tecnico=tecnico,
        origen=ActaComplementaria.ORIGEN_SISOC,
        asignado_desde_sisoc=True,
    )
    _coordinador(client)
    url_detalle = reverse(
        "acta_complementaria_detalle",
        kwargs={"comedor_pk": comedor.id, "pk": acta.id},
    )

    detalle = client.get(url_detalle).content.decode()
    rechazada = _revisar(client, acta, estado_validacion=VALIDADO)

    acta.refresh_from_db()
    assert acta.estado_validacion is None
    assert 'data-bs-target="#modalRevisionActa"' not in detalle
    assert "Todavía no hay nada que revisar" in " ".join(
        str(m) for m in get_messages(rechazada.wsgi_request)
    )

    completada = _api(tecnico).patch(
        _url(comedor, acta.id), {"observaciones": "Cambio de menú"}, format="json"
    )
    assert completada.status_code == 200, completada.content
    detalle = client.get(url_detalle).content.decode()
    assert 'data-bs-target="#modalRevisionActa"' in detalle
    _revisar(client, acta, estado_validacion=VALIDADO)
    acta.refresh_from_db()
    assert acta.estado_validacion == VALIDADO
