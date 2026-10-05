"""Validación RENAPER por bloque: responsables, niño/a y referente del CDI.

Los datos de identidad que vienen de RENAPER quedan bloqueados (el servidor los
toma del token firmado, no del POST) y solo el contacto sigue editable, con
registro de quién lo cambia.
"""

from datetime import date
from unittest.mock import patch

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import User
from django.urls import reverse

from ciudadanos.models import Ciudadano
from centrodeinfancia.forms import (
    CentroDeInfanciaForm,
    NominaCentroInfanciaDestinatariosForm,
    NominaCentroInfanciaForm,
)
from centrodeinfancia.models import CentroDeInfancia, NominaCentroInfancia
from centrodeinfancia.services_renaper_bloques import crear_token
from centrodeinfancia.tests.test_centrodeinfancia_form import (  # noqa: F401
    datos_validos as datos_cdi,
    fixture_servicio,
    fixture_ubicacion,
)
from centrodeinfancia.tests.test_destinatario_form import (
    datos_validos as datos_nomina,
)
from core.models import Nacionalidad, Sexo

pytestmark = pytest.mark.django_db

CONSULTA_RENAPER = (
    "centrodeinfancia.services_renaper_bloques.obtener_datos_ciudadano_desde_renaper"
)

# Coincide con el Responsable 1 de `datos_nomina`.
RESPONSABLE = {
    "documento": 30123456,
    "apellido": "Torres",
    "nombre": "Laura",
    "fecha_nacimiento": date(1990, 5, 4),
    "cuil_cuit": "27301234568",
}
VALORES_RESPONSABLE_1 = {
    "responsable_legal_1_dni": 30123456,
    "responsable_legal_1_apellido": "Torres",
    "responsable_legal_1_nombre": "Laura",
    "responsable_legal_1_fecha_nacimiento": "1990-05-04",
    "responsable_legal_1_sexo_registral": "mujer",
    "responsable_legal_1_nacionalidad": "Argentino",
    "responsable_legal_1_cuit": "27301234568",
}


def _respuesta_renaper(sexo="Femenino", nacionalidad="Argentino", **data):
    sexo_obj, _ = Sexo.objects.get_or_create(sexo=sexo)
    nacionalidad_obj, _ = Nacionalidad.objects.get_or_create(nacionalidad=nacionalidad)
    return {
        "success": True,
        "message": "Datos obtenidos desde RENAPER.",
        "data": {**data, "sexo": sexo_obj.pk, "nacionalidad": nacionalidad_obj.pk},
        "datos_api": {"dato_privado": "RAW_RENAPER_NO_PUBLICAR"},
    }


@pytest.fixture
def admin(client):
    user = User.objects.create_superuser("renaper-bloques", "", "test1234")
    client.force_login(user)
    return user


@pytest.fixture
def centro():
    return CentroDeInfancia.objects.create(nombre="CDI Bloques")


def _consultar(client, bloque, dni, respuesta):
    url = reverse("centrodeinfancia_renaper_bloque", args=[bloque])
    with patch(CONSULTA_RENAPER, return_value=respuesta) as consultar:
        response = client.get(url, {"dni": dni})
    return response, consultar


def _alta_nomina(client, centro, **data):
    url = reverse("centrodeinfancia_nomina_crear", kwargs={"pk": centro.pk})
    response = client.post(url, {**datos_nomina(centro), **data})
    assert response.status_code == 302, response.context["form"].errors
    return NominaCentroInfancia.objects.get(centro=centro)


def _token_responsable_1(client):
    response, _ = _consultar(
        client,
        "responsable_legal_1",
        "30123456",
        _respuesta_renaper(**RESPONSABLE),
    )
    return response.json()["token"]


# ── Consulta ─────────────────────────────────────────────────────────────


def test_consulta_devuelve_valores_del_bloque_y_token(client, admin):
    response, consultar = _consultar(
        client,
        "responsable_legal_1",
        "30123456",
        _respuesta_renaper(**RESPONSABLE),
    )

    consultar.assert_called_once_with("30123456")
    assert response.status_code == 200
    body = response.json()
    assert body["valores"] == VALORES_RESPONSABLE_1
    assert body["token"]
    assert "RAW_RENAPER_NO_PUBLICAR" not in response.content.decode()


def test_consulta_sin_resultado_permite_carga_manual(client, admin):
    response, _ = _consultar(
        client,
        "responsable_legal_1",
        "30123456",
        {"success": False, "message": "No se encontraron datos en RENAPER."},
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "message": "No se encontraron datos en RENAPER.",
    }


def test_consulta_bloque_inexistente_da_404(client, admin):
    response, consultar = _consultar(client, "otro", "30123456", {})

    assert response.status_code == 404
    consultar.assert_not_called()


def test_consulta_requiere_permiso_de_alta_o_edicion(client):
    user = User.objects.create_user("sin-permisos", password="test1234")
    client.force_login(user)

    response, consultar = _consultar(client, "referente", "30123456", {})

    assert response.status_code == 403
    consultar.assert_not_called()


# ── Nómina: alta ──────────────────────────────────────────────────────────


def test_alta_bloquea_responsable_validado_y_deja_telefono_editable(
    client, admin, centro
):
    token = _token_responsable_1(client)

    nomina = _alta_nomina(
        client,
        centro,
        responsable_legal_1_apellido="Alterado",
        responsable_legal_1_telefono="1145678901",
        renaper_token_responsable_legal_1=token,
    )

    assert nomina.responsable_legal_1_apellido == "Torres"
    assert nomina.responsable_legal_1_telefono == 1145678901
    assert set(nomina.campos_verificados_renaper) == set(VALORES_RESPONSABLE_1)


@pytest.mark.parametrize("caso", ["otro_usuario", "otro_bloque", "alterado"])
def test_alta_no_confia_en_token_ajeno(client, admin, centro, caso):
    token = crear_token("responsable_legal_1", admin, VALORES_RESPONSABLE_1)
    campo_token = "renaper_token_responsable_legal_1"
    if caso == "otro_usuario":
        otro = User.objects.create_user("otro", password="test1234")
        token = crear_token("responsable_legal_1", otro, VALORES_RESPONSABLE_1)
    elif caso == "otro_bloque":
        campo_token = "renaper_token_responsable_legal_2"
    else:
        token += "alterado"

    nomina = _alta_nomina(
        client,
        centro,
        responsable_legal_1_apellido="Manual",
        **{campo_token: token},
    )

    assert nomina.responsable_legal_1_apellido == "Manual"
    assert nomina.campos_verificados_renaper == []


def test_alta_con_ciudadano_validado_bloquea_identidad_del_nino(client, admin, centro):
    data = datos_nomina(centro)
    ciudadano = Ciudadano.objects.create(
        documento=data["dni"],
        apellido=data["apellido"],
        nombre=data["nombre"],
        fecha_nacimiento=data["fecha_nacimiento"],
        estado_validacion_renaper=Ciudadano.RENAPER_VALIDADO,
    )

    nomina = _alta_nomina(client, centro, ciudadano_id=ciudadano.pk, nombre="Otro")

    assert nomina.nombre == ciudadano.nombre
    assert set(nomina.campos_verificados_renaper) == {
        "dni",
        "apellido",
        "nombre",
        "fecha_nacimiento",
    }


# ── Nómina: edición ──────────────────────────────────────────────────────


def _url_edicion(centro, nomina):
    return reverse(
        "centrodeinfancia_nomina_editar",
        kwargs={"pk": centro.pk, "nomina_id": nomina.pk},
    )


def test_edicion_mantiene_bloqueo_y_audita_cambio_de_telefono(client, admin, centro):
    nomina = _alta_nomina(
        client, centro, renaper_token_responsable_legal_1=_token_responsable_1(client)
    )

    response = client.post(
        _url_edicion(centro, nomina),
        datos_nomina(
            centro,
            responsable_legal_1_apellido="Alterado",
            responsable_legal_1_telefono="1199998888",
        ),
    )

    assert response.status_code == 302
    nomina.refresh_from_db()
    assert nomina.responsable_legal_1_apellido == "Torres"
    assert nomina.responsable_legal_1_telefono == 1199998888
    entrada = (
        LogEntry.objects.get_for_object(nomina)
        .filter(action=LogEntry.Action.UPDATE)
        .get()
    )
    assert entrada.actor == admin
    assert set(entrada.changes_dict) == {"responsable_legal_1_telefono"}


def test_edicion_permite_validar_registro_cargado_a_mano(client, admin, centro):
    nomina = _alta_nomina(client, centro)
    assert nomina.campos_verificados_renaper == []

    response = client.post(
        _url_edicion(centro, nomina),
        datos_nomina(
            centro,
            responsable_legal_1_apellido="Alterado",
            renaper_token_responsable_legal_1=_token_responsable_1(client),
        ),
    )

    assert response.status_code == 302
    nomina.refresh_from_db()
    assert nomina.responsable_legal_1_apellido == "Torres"
    assert set(nomina.campos_verificados_renaper) == set(VALORES_RESPONSABLE_1)


def test_edicion_no_cambia_identidad_del_nino_con_otro_dni(client, admin, centro):
    nomina = _alta_nomina(client, centro)
    token = crear_token(
        "nino",
        admin,
        {"dni": 99888777, "apellido": "Otra", "nombre": "Persona"},
    )

    response = client.post(
        _url_edicion(centro, nomina),
        datos_nomina(centro, renaper_token_nino=token),
    )

    assert response.status_code == 302
    nomina.refresh_from_db()
    assert nomina.dni == int(datos_nomina(centro)["dni"])
    assert nomina.campos_verificados_renaper == []


def test_form_de_edicion_rapida_respeta_campos_bloqueados(centro):
    ciudadano = Ciudadano.objects.create(
        documento=45123456,
        apellido="Torres",
        nombre="Luca",
        fecha_nacimiento=date(2023, 1, 1),
    )
    nomina = NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        dni=45123456,
        apellido="Torres",
        nombre="Luca",
        responsable_legal_1_apellido="Torres",
        campos_verificados_renaper=["responsable_legal_1_apellido"],
    )

    form = NominaCentroInfanciaForm(instance=nomina)

    assert form.fields["responsable_legal_1_apellido"].disabled
    assert not form.fields["responsable_legal_1_telefono"].disabled


# ── Referente del CDI ────────────────────────────────────────────────────

VALORES_REFERENTE = {
    "dni_referente": 44535030,
    "apellido_referente": "Pérez",
    "nombre_referente": "Ana",
    "cuil_referente": "20445350304",
}


def test_consulta_referente_mapea_campos_del_cdi(client, admin):
    response, _ = _consultar(
        client,
        "referente",
        "44535030",
        _respuesta_renaper(
            documento=44535030,
            apellido="Pérez",
            nombre="Ana",
            fecha_nacimiento=date(1985, 1, 1),
            cuil_cuit="20445350304",
        ),
    )

    assert response.json()["valores"] == VALORES_REFERENTE


def test_referente_validado_queda_bloqueado_salvo_contacto(admin, ubicacion, servicio):
    form = CentroDeInfanciaForm(
        data=datos_cdi(ubicacion, servicio, nombre_referente="Alterado"),
        user=admin,
        valores_renaper=VALORES_REFERENTE,
    )
    assert form.is_valid(), form.errors
    centro = form.save()
    assert centro.nombre_referente == "Ana"
    assert set(centro.campos_verificados_renaper) == set(VALORES_REFERENTE)

    edicion = CentroDeInfanciaForm(
        data=datos_cdi(
            ubicacion,
            servicio,
            apellido_referente="Alterado",
            email_referente="nuevo@cdi.com",
            telefono_referente="4774-9999",
        ),
        instance=centro,
        user=admin,
    )
    assert edicion.is_valid(), edicion.errors
    edicion.save()
    centro.refresh_from_db()
    assert centro.apellido_referente == "Pérez"
    assert centro.email_referente == "nuevo@cdi.com"
    assert centro.telefono_referente == "4774-9999"


# ── Experiencia: modo inicial de cada bloque y cambio de persona ─────────


def test_cambiar_persona_no_deja_datos_de_la_anterior_bloqueados(client, admin, centro):
    nomina = _alta_nomina(
        client, centro, renaper_token_responsable_legal_1=_token_responsable_1(client)
    )
    # La persona nueva viene sin CUIL desde RENAPER: ese dato se completa a mano.
    token = crear_token(
        "responsable_legal_1",
        admin,
        {
            "responsable_legal_1_dni": 30123457,
            "responsable_legal_1_apellido": "Fernández",
            "responsable_legal_1_nombre": "Juan",
            "responsable_legal_1_fecha_nacimiento": "1985-01-02",
            "responsable_legal_1_sexo_registral": "varon",
        },
    )

    response = client.post(
        _url_edicion(centro, nomina),
        datos_nomina(
            centro,
            responsable_legal_1_cuit="20-30123457-1",
            renaper_token_responsable_legal_1=token,
        ),
    )

    assert response.status_code == 302
    nomina.refresh_from_db()
    assert nomina.responsable_legal_1_dni == 30123457
    assert nomina.responsable_legal_1_apellido == "Fernández"
    assert nomina.responsable_legal_1_cuit == "20301234571"
    assert "responsable_legal_1_cuit" not in nomina.campos_verificados_renaper
    assert "responsable_legal_1_dni" in nomina.campos_verificados_renaper


def test_modo_inicial_de_cada_bloque(centro):
    alta = NominaCentroInfanciaDestinatariosForm(centro=centro)
    assert alta.modos_renaper["responsable_legal_1"] == "dni"

    sin_dni = NominaCentroInfanciaDestinatariosForm(
        data={"responsable_legal_1_tipo_documentacion": "origen_sin_tramite"},
        centro=centro,
    )
    assert sin_dni.modos_renaper["responsable_legal_1"] == "manual"

    verificado = NominaCentroInfanciaDestinatariosForm(
        centro=centro, valores_renaper=VALORES_RESPONSABLE_1
    )
    assert verificado.modos_renaper["responsable_legal_1"] == "verificado"
    assert verificado.modos_renaper["responsable_legal_2"] == "dni"


def test_edicion_de_registro_manual_arranca_en_modo_manual(client, admin, centro):
    nomina = _alta_nomina(client, centro)

    response = client.get(_url_edicion(centro, nomina))

    html = response.content.decode()
    form = response.context["form"]
    assert form.modos_renaper["responsable_legal_1"] == "manual"
    assert form.modos_renaper["responsable_legal_2"] == "dni"
    assert 'data-renaper-bloque="responsable_legal_2"' in html
    assert 'data-opcional="1"' in html
