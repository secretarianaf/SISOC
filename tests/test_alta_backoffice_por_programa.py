"""H1 (QA 28/9): el popup "Nuevo acompañamiento territorial" según el programa.

Alimentar Comunidad (PAC) ofrece el ciclo PAC; Abordaje Comunitario - Línea
Secos ofrece FORM-PNUD-SECOS y Línea Tradicional los FORM II. El criterio es el
de ``linea_pnud`` (nombre normalizado; el id 3/4 solo si el programa no tiene
nombre) y el servidor lo valida aunque el ``<select>`` mande otra cosa. Un
seguimiento PNUD creado desde SISOC queda asignado al territorial elegido y la
app lo ve y lo completa.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor, Programas
from core.models import Provincia
from relevamientos.alta_backoffice import opciones_alta, opciones_seguimiento_pac
from relevamientos.models import PrimerSeguimiento, Relevamiento, SeguimientoPnud
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

SECOS = "Abordaje comunitario - Línea Secos"
TRADICIONAL = "Abordaje comunitario - Línea Tradicional"


def _territorial(username, provincia):
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    return user


def _comedor(programa_nombre, programa_id=None):
    provincia = Provincia.objects.create(nombre=f"Prov {programa_nombre or 'sin'}")
    kwargs = {"nombre": programa_nombre}
    if programa_id is not None:
        kwargs["id"] = programa_id
    programa = Programas.objects.create(**kwargs)
    return Comedor.objects.create(
        nombre="Comedor H1", provincia=provincia, programa=programa
    )


def _login(client, username="bo_h1"):
    user = get_user_model().objects.create_user(username=username, password="x")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="relevamientos",
            codename__in=["view_relevamiento", "add_relevamiento"],
        )
    )
    client.force_login(user)
    return user


def _territorial_json(user):
    return json.dumps({"gestionar_uid": str(user.id), "nombre": user.username})


def _post(client, comedor, tipo, territorial=None, **extra):
    data = {"tipo_relevamiento": tipo, **extra}
    if territorial is not None:
        data["territorial"] = _territorial_json(territorial)
    return client.post(
        reverse("relevamiento_create_edit_ajax", kwargs={"pk": comedor.pk}),
        data,
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )


def _valores(comedor):
    return [valor for valor, _ in opciones_alta(comedor)]


# ------------------------------------------------------------- opciones


def test_alimentar_comunidad_ofrece_el_ciclo_pac():
    comedor = _comedor("Alimentar comunidad")

    assert _valores(comedor) == [
        "relevamiento_inicial",
        "primer_seguimiento",
        "seguimiento_posterior",
        "seguimiento_virtual",
        "acta_complementaria",
    ]
    assert opciones_seguimiento_pac(comedor)


def test_linea_secos_ofrece_solo_el_seguimiento_de_puntos_de_entrega():
    comedor = _comedor(SECOS)

    assert _valores(comedor) == ["relevamiento_inicial", "pnud_secos"]
    assert dict(opciones_alta(comedor))["pnud_secos"] == (
        "Seguimiento Puntos de Entrega (SECOS)"
    )
    assert opciones_seguimiento_pac(comedor) == []


def test_linea_tradicional_ofrece_los_form_ii():
    comedor = _comedor(TRADICIONAL)

    assert _valores(comedor) == [
        "relevamiento_inicial",
        "pnud_iia",
        "pnud_iia1",
        "pnud_iib",
        "pnud_iib1",
    ]


def test_el_nombre_manda_sobre_el_id_de_respaldo():
    # Un "Alimentar comunidad" con id 3 en otra base no pasa por Secos.
    assert _valores(_comedor("Alimentar comunidad", programa_id=3))[1] == (
        "primer_seguimiento"
    )
    # Solo un programa SIN nombre usa el id 3/4.
    assert _valores(_comedor("", programa_id=4))[1] == "pnud_iia"


def test_el_popup_muestra_las_opciones_del_programa(client):
    comedor = _comedor(SECOS)
    Relevamiento.objects.create(comedor=comedor, estado="Visita pendiente")
    _login(client)

    html = client.get(
        reverse("relevamientos", kwargs={"comedor_pk": comedor.pk})
    ).content.decode()

    assert 'value="pnud_secos"' in html
    assert "Seguimiento Puntos de Entrega (SECOS)" in html
    assert 'value="primer_seguimiento"' not in html
    # Sin ciclo PAC en PNUD: la fila del relevamiento no ofrece "Agregar".
    assert 'data-bs-target="#modalSeguimientoNuevo"' not in html


def test_el_popup_pac_no_ofrece_formularios_pnud(client):
    comedor = _comedor("Alimentar comunidad")
    _login(client)

    html = client.get(
        reverse("relevamientos", kwargs={"comedor_pk": comedor.pk})
    ).content.decode()

    assert 'value="primer_seguimiento"' in html
    assert "pnud_" not in html


# ----------------------------------------------------- validación servidor


@pytest.mark.parametrize(
    "programa, tipo",
    [
        (SECOS, "pnud_iia"),
        (SECOS, "primer_seguimiento"),
        (TRADICIONAL, "pnud_secos"),
        (TRADICIONAL, "seguimiento_virtual"),
        ("Alimentar comunidad", "pnud_secos"),
    ],
)
def test_el_servidor_rechaza_un_tipo_ajeno_al_programa(client, programa, tipo):
    comedor = _comedor(programa)
    territorial = _territorial("terr_h1", comedor.provincia)
    _login(client)

    response = _post(client, comedor, tipo, territorial)

    assert response.status_code == 400
    assert "programa" in response.json()["error"]
    assert not SeguimientoPnud.objects.exists()
    assert not PrimerSeguimiento.objects.exists()


def test_el_servidor_rechaza_desde_la_fila_un_seguimiento_pac_en_pnud(client):
    comedor = _comedor(TRADICIONAL)
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente"
    )
    _login(client)

    response = _post(
        client,
        comedor,
        "seguimiento_posterior",
        relevamiento_id=str(relevamiento.id),
    )

    assert response.status_code == 400
    assert not PrimerSeguimiento.objects.exists()


def test_tipo_pnud_desconocido_da_400(client):
    comedor = _comedor(SECOS)
    _login(client)

    response = _post(client, comedor, "pnud_zzz")

    assert response.status_code == 400


# ----------------------------------------------------- alta PNUD asignada


def test_crea_el_seguimiento_pnud_asignado_al_territorial(client):
    comedor = _comedor(SECOS)
    territorial = _territorial("terr_secos", comedor.provincia)
    _login(client)

    response = _post(client, comedor, "pnud_secos", territorial)

    assert response.status_code == 200, response.content
    seguimiento = SeguimientoPnud.objects.get()
    assert response.json()["url"] == reverse(
        "seguimiento_pnud_detalle",
        kwargs={"comedor_pk": comedor.pk, "pk": seguimiento.pk},
    )
    assert seguimiento.comedor_id == comedor.id
    assert seguimiento.tecnico_id == territorial.id
    assert seguimiento.formulario == "secos"
    assert seguimiento.origen == SeguimientoPnud.ORIGEN_SISOC
    assert seguimiento.asignado_desde_sisoc is True
    assert seguimiento.estado_validacion is None
    assert seguimiento.datos == {}


def test_territorial_sin_alcance_en_la_provincia_da_400(client):
    comedor = _comedor(TRADICIONAL)
    otra = Provincia.objects.create(nombre="Otra provincia")
    ajeno = _territorial("terr_ajeno", otra)
    _login(client)

    response = _post(client, comedor, "pnud_iib", ajeno)

    assert response.status_code == 400
    assert "territorial" in response.json()["error"].lower()
    assert not SeguimientoPnud.objects.exists()


def test_sin_permiso_de_alta_no_crea_el_pnud(client):
    comedor = _comedor(SECOS)
    territorial = _territorial("terr_perm", comedor.provincia)
    user = get_user_model().objects.create_user(username="sin_perm_h1", password="x")
    client.force_login(user)

    response = _post(client, comedor, "pnud_secos", territorial)

    assert response.status_code == 403
    assert not SeguimientoPnud.objects.exists()


def test_la_app_ve_y_completa_el_pnud_asignado(client):
    comedor = _comedor(TRADICIONAL)
    territorial = _territorial("terr_app", comedor.provincia)
    _login(client)
    _post(client, comedor, "pnud_iia", territorial)
    seguimiento = SeguimientoPnud.objects.get()
    token, _ = Token.objects.get_or_create(user=territorial)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    listado = api.get("/api/territorial/comedores/")
    get = api.get(f"/api/territorial/comedores/{comedor.id}/seguimientos-pnud/")
    patch = api.patch(
        f"/api/territorial/comedores/{comedor.id}/seguimientos-pnud/"
        f"{seguimiento.id}/",
        {"datos": {"funcionamiento": "Abierto, en funcionamiento alimentario"}},
        format="json",
    )

    assert listado.status_code == 200
    assert comedor.id in [item["id"] for item in listado.json()["results"]]
    item = get.json()["items"][0]
    assert item["origen"] == "sisoc"
    assert item["estado_validacion"] is None
    assert item["datos"] == {}
    assert patch.status_code == 200, patch.content
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE
    assert seguimiento.datos["funcionamiento"].startswith("Abierto")
