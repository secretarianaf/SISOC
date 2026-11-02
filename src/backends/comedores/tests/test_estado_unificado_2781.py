"""#2781: estados unificados Pendiente / En curso / Pendiente Revisión /
Finalizado en SISOC web y en la API territorial.

Es una etiqueta calculada: ``estado`` y ``estado_validacion`` guardados no
cambian.
"""

import pytest
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.api_views_territorial_actas import serialize_acta
from comedores.api_views_territorial_pnud import serialize_seguimiento_pnud
from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import (
    ActaComplementaria,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)
from relevamientos.service import RelevamientoService
from users.models import TerritorialComedorProvincia

PENDIENTE = "Pendiente"
EN_CURSO = "En curso"
REVISION = "Pendiente Revisión"
FINALIZADO = "Finalizado"

V_PEND = Relevamiento.ESTADO_VALIDACION_PENDIENTE
V_SUBS = Relevamiento.ESTADO_VALIDACION_A_SUBSANAR
V_OK = Relevamiento.ESTADO_VALIDACION_VALIDADO


def test_constantes_de_los_cuatro_estados():
    assert RelevamientoService.ESTADOS_UNIFICADOS == (
        PENDIENTE,
        EN_CURSO,
        REVISION,
        FINALIZADO,
    )
    for estado in RelevamientoService.ESTADOS_UNIFICADOS:
        assert RelevamientoService.badge_estado_unificado(estado)


@pytest.mark.parametrize(
    "estado,validacion,esperado",
    [
        # Asignado y sin empezar
        ("Pendiente", None, PENDIENTE),
        ("Visita pendiente", None, PENDIENTE),
        ("Visita Pendiente", "", PENDIENTE),
        (None, None, PENDIENTE),
        ("", None, PENDIENTE),
        # Sin circuito de validación: terminado (históricos de GESTIONAR)
        ("Finalizado", None, FINALIZADO),
        ("Finalizado/Excepciones", "", FINALIZADO),
        # Enviado a revisión
        ("Finalizado", V_PEND, REVISION),
        ("Finalizado/Excepciones", V_PEND, REVISION),
        ("Visita pendiente", V_PEND, REVISION),
        ("Pendiente de validación", None, REVISION),
        ("Pendiente revisión", None, REVISION),
        # Devuelto por el coordinador
        ("Finalizado", V_SUBS, EN_CURSO),
        ("Visita pendiente", V_SUBS, EN_CURSO),
        (None, V_SUBS, EN_CURSO),
        # Validado
        ("Finalizado", V_OK, FINALIZADO),
        ("Visita pendiente", V_OK, FINALIZADO),
        # Estado desconocido y no vacío: empezado, no enviado
        ("En proceso", None, EN_CURSO),
    ],
)
def test_mapeo_relevamiento(estado, validacion, esperado):
    relevamiento = Relevamiento(estado=estado, estado_validacion=validacion)

    assert RelevamientoService.estado_unificado(relevamiento) == esperado


@pytest.mark.parametrize("tipo", [t for t, _ in PrimerSeguimiento.TIPO_CHOICES])
@pytest.mark.parametrize(
    "estado,validacion,esperado",
    [
        ("Asignado", None, PENDIENTE),
        (None, None, PENDIENTE),
        ("", "", PENDIENTE),
        ("En Proceso", None, EN_CURSO),
        ("En Proceso", V_SUBS, EN_CURSO),
        ("Completo", V_SUBS, EN_CURSO),
        ("Completo", None, FINALIZADO),
        ("Completo", "", FINALIZADO),
        ("Completo", V_PEND, REVISION),
        ("En Proceso", V_PEND, REVISION),
        ("Completo", V_OK, FINALIZADO),
        ("Asignado", V_OK, FINALIZADO),
    ],
)
def test_mapeo_primer_seguimiento_todos_los_tipos(tipo, estado, validacion, esperado):
    seguimiento = PrimerSeguimiento(
        tipo=tipo, estado=estado, estado_validacion=validacion
    )

    assert RelevamientoService.estado_unificado(seguimiento) == esperado


@pytest.mark.parametrize(
    "validacion,datos,origen,esperado",
    [
        (None, {}, "sisoc", PENDIENTE),
        (None, {}, "app", PENDIENTE),
        (None, {"campo": "x"}, "sisoc", EN_CURSO),
        (None, {"campo": "x"}, "app", REVISION),
        (V_PEND, {"campo": "x"}, "app", REVISION),
        (V_PEND, {}, "sisoc", REVISION),
        (V_SUBS, {"campo": "x"}, "sisoc", EN_CURSO),
        (V_OK, {"campo": "x"}, "app", FINALIZADO),
    ],
)
def test_mapeo_seguimiento_pnud(validacion, datos, origen, esperado):
    seguimiento = SeguimientoPnud(
        formulario="siph", datos=datos, origen=origen, estado_validacion=validacion
    )

    assert RelevamientoService.estado_unificado(seguimiento) == esperado


@pytest.mark.django_db
@pytest.mark.parametrize(
    "validacion,con_contenido,origen,esperado",
    [
        (None, False, "sisoc", PENDIENTE),
        (None, False, "app", PENDIENTE),
        (None, True, "sisoc", EN_CURSO),
        (None, True, "app", REVISION),
        (V_PEND, True, "app", REVISION),
        (V_SUBS, True, "app", EN_CURSO),
        (V_OK, True, "sisoc", FINALIZADO),
    ],
)
def test_mapeo_acta_complementaria(validacion, con_contenido, origen, esperado):
    provincia = Provincia.objects.create(nombre="Prov acta 2781")
    comedor = Comedor.objects.create(nombre="Comedor acta", provincia=provincia)
    acta = ActaComplementaria.objects.create(
        comedor=comedor,
        origen=origen,
        estado_validacion=validacion,
        observaciones="Cambio de prestación" if con_contenido else None,
    )

    assert RelevamientoService.estado_unificado(acta) == esperado


def test_objeto_desconocido_es_pendiente():
    assert RelevamientoService.estado_unificado(object()) == PENDIENTE


def test_filtros_de_template_muestran_etiqueta_y_badge():
    relevamiento = Relevamiento(estado="Finalizado", estado_validacion=V_PEND)

    html = Template(
        "{% load estado_unificado %}"
        "{{ r|estado_unificado }}|{{ r|badge_estado_unificado }}"
    ).render(Context({"r": relevamiento}))

    assert html == "Pendiente Revisión|bg-warning text-dark"


@pytest.mark.django_db
def test_listado_web_muestra_la_etiqueta_unificada(client):
    provincia = Provincia.objects.create(nombre="Prov web 2781")
    comedor = Comedor.objects.create(nombre="Comedor web", provincia=provincia)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", estado_validacion=V_PEND
    )
    PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, estado="En Proceso", numero_orden=1
    )
    ActaComplementaria.objects.create(comedor=comedor)
    SeguimientoPnud.objects.create(comedor=comedor, formulario="siph", datos={})
    user = get_user_model().objects.create_superuser(
        username="admin2781", email="admin2781@example.com", password="x"
    )
    client.force_login(user)

    response = client.get(reverse("relevamientos", kwargs={"comedor_pk": comedor.id}))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Pendiente Revisión" in html
    assert "En curso" in html
    assert "Pendiente</span>" in html

    detalle = client.get(
        reverse(
            "relevamiento_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": relevamiento.id},
        )
    )
    assert detalle.status_code == 200
    assert "Pendiente Revisión" in detalle.content.decode()


# --- API territorial -------------------------------------------------------


def _territorial():
    provincia = Provincia.objects.create(nombre="Prov api 2781")
    comedor = Comedor.objects.create(nombre="Comedor api", provincia=provincia)
    user = get_user_model().objects.create_user(
        username="terr2781", email="terr2781@example.com", password="x"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client, user, comedor


@pytest.mark.django_db
def test_api_territorial_expone_estado_unificado_en_relevamientos_y_seguimientos():
    client, user, comedor = _territorial()
    relevamiento = Relevamiento.objects.create(
        comedor=comedor,
        estado="Finalizado",
        estado_validacion=V_PEND,
        territorial_user=user,
    )
    PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento, estado="Asignado", numero_orden=1
    )

    response = client.get(f"/api/territorial/comedores/{comedor.id}/")

    assert response.status_code == 200
    rels = response.data["relevamientos"]
    assert rels["ultimo"]["estado_unificado"] == REVISION
    assert rels["ultimo"]["estado"] == "Finalizado"
    assert rels["items"][0]["estado_unificado"] == REVISION
    seg = response.data["seguimientos"]["items"][0]
    assert seg["estado_unificado"] == PENDIENTE
    assert seg["estado"] == "Asignado"


@pytest.mark.django_db
def test_api_territorial_expone_estado_unificado_en_actas_y_pnud():
    client, user, comedor = _territorial()
    acta = ActaComplementaria.objects.create(
        comedor=comedor,
        tecnico=user,
        origen="app",
        estado_validacion=V_PEND,
        observaciones="x",
    )
    pnud = SeguimientoPnud.objects.create(
        comedor=comedor, tecnico=user, formulario="siph", datos={}
    )
    assert serialize_acta(acta, user.id)["estado_unificado"] == REVISION
    assert serialize_seguimiento_pnud(pnud, True)["estado_unificado"] == PENDIENTE


@pytest.mark.django_db
def test_api_territorial_reintento_de_alta_incluye_estado_unificado():
    client, _, comedor = _territorial()
    Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", client_uuid="uuid-2781"
    )

    response = client.post(
        f"/api/territorial/comedores/{comedor.id}/relevamientos/",
        {"client_uuid": "uuid-2781"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["estado_unificado"] == PENDIENTE
