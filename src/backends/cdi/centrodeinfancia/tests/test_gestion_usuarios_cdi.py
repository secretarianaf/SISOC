"""Gestión de usuarios del CDI: responsable, botonera y cambio de referente.

El referente responsable (el vigente en la ficha) administra a los demás
usuarios del centro: genera, suspende, reactiva y da de baja. Al cambiar el
referente en la ficha, el anterior conserva su acceso hasta que el nuevo decida.
"""

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.urls import reverse

from centrodeinfancia.access import (
    puede_administrar_usuarios_cdi,
    puede_generar_usuario_cdi,
    usuarios_cdi_activos,
)
from centrodeinfancia.models import AccesoCDI, CentroDeInfancia
from centrodeinfancia.services_renaper_bloques import crear_token
from centrodeinfancia.services_user_provisioning import actualizar_referente_cdi
from core.constants import UserGroups
from core.models import Provincia
from users.models import Profile

pytestmark = pytest.mark.django_db

Estado = AccesoCDI.Estado


@pytest.fixture(autouse=True)
def _grupo_referente():
    """Las data migrations no corren en tests (TEST MIGRATE=False)."""
    Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)


@pytest.fixture
def centro():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    return CentroDeInfancia.objects.create(
        nombre="CDI Usuarios",
        provincia=provincia,
        nombre_referente="Ana",
        apellido_referente="Gómez",
        email_referente="ana@example.com",
        dni_referente="30123456",
    )


def _referente(centro, username, *, responsable=False, estado=Estado.ACTIVO):
    user = User.objects.create_user(
        username=username, email=f"{username}@example.com", password="test1234"
    )
    Profile.objects.get_or_create(user=user)
    user.groups.add(Group.objects.get(name=UserGroups.CDI_REFERENTE_CENTRO))
    user.user_permissions.add(Permission.objects.get(codename="view_centrodeinfancia"))
    acceso = AccesoCDI.objects.create(
        user=user, centro=centro, es_responsable=responsable, estado=estado
    )
    return user, acceso


def _url_estado(centro, acceso):
    return reverse(
        "centrodeinfancia_usuario_estado",
        kwargs={"pk": centro.pk, "acceso_id": acceso.pk},
    )


# ── Modelo ────────────────────────────────────────────────────────────────


def test_activo_queda_sincronizado_con_el_estado(centro):
    # Forma previa de crear una baja: ``activo=False`` sin estado.
    legacy_user = User.objects.create_user("legacy", password="test1234")
    legacy = AccesoCDI.objects.create(user=legacy_user, centro=centro, activo=False)
    assert legacy.estado == Estado.BAJA

    _, suspendido = _referente(centro, "susp", estado=Estado.SUSPENDIDO)
    assert suspendido.activo is False


def test_la_suspension_ocupa_cupo_y_la_baja_lo_libera(centro):
    _referente(centro, "activo")
    _referente(centro, "suspendido", estado=Estado.SUSPENDIDO)
    _referente(centro, "baja", estado=Estado.BAJA)

    assert usuarios_cdi_activos(centro) == 2


# ── Permisos ──────────────────────────────────────────────────────────────


def test_solo_el_responsable_administra_entre_los_referentes(centro):
    responsable, _ = _referente(centro, "resp", responsable=True)
    comun, _ = _referente(centro, "comun")

    assert puede_administrar_usuarios_cdi(responsable, centro)
    assert puede_generar_usuario_cdi(responsable, centro)
    assert not puede_administrar_usuarios_cdi(comun, centro)
    assert not puede_generar_usuario_cdi(comun, centro)


def test_responsable_suspendido_no_administra(centro):
    responsable, acceso = _referente(centro, "resp", responsable=True)
    acceso.estado = Estado.SUSPENDIDO
    acceso.save()

    assert not puede_administrar_usuarios_cdi(responsable, centro)


# ── Botonera ──────────────────────────────────────────────────────────────


def test_responsable_suspende_reactiva_y_da_de_baja(client, centro):
    responsable, _ = _referente(centro, "resp", responsable=True)
    _, otro = _referente(centro, "otro")
    client.force_login(responsable)
    url = _url_estado(centro, otro)

    response = client.post(url, {"accion": "suspender", "motivo": "Licencia"})
    assert response.status_code == 302
    assert response.url.endswith("#usuarios")
    otro.refresh_from_db()
    assert (otro.estado, otro.activo, otro.motivo_estado) == (
        Estado.SUSPENDIDO,
        False,
        "Licencia",
    )

    client.post(url, {"accion": "reactivar"})
    otro.refresh_from_db()
    assert (otro.estado, otro.activo) == (Estado.ACTIVO, True)

    client.post(url, {"accion": "baja", "motivo": "Dejó el centro"})
    otro.refresh_from_db()
    assert (otro.estado, otro.activo) == (Estado.BAJA, False)
    assert otro.fecha_baja is not None


@pytest.mark.parametrize(
    "accion,motivo",
    [("suspender", ""), ("baja", "   "), ("reactivar", ""), ("otra", "x")],
)
def test_transiciones_invalidas_no_cambian_el_estado(client, centro, accion, motivo):
    # Suspender/baja sin motivo, reactivar un activo o una acción inexistente.
    responsable, _ = _referente(centro, "resp", responsable=True)
    _, otro = _referente(centro, "otro")
    client.force_login(responsable)

    client.post(_url_estado(centro, otro), {"accion": accion, "motivo": motivo})

    otro.refresh_from_db()
    assert otro.estado == Estado.ACTIVO


def test_la_baja_es_definitiva(client, centro):
    responsable, _ = _referente(centro, "resp", responsable=True)
    _, otro = _referente(centro, "otro", estado=Estado.BAJA)
    client.force_login(responsable)

    client.post(_url_estado(centro, otro), {"accion": "reactivar"})

    otro.refresh_from_db()
    assert otro.estado == Estado.BAJA


def test_nadie_suspende_al_responsable_ni_a_si_mismo(client, centro):
    responsable, acceso_responsable = _referente(centro, "resp", responsable=True)
    client.force_login(responsable)
    client.post(
        _url_estado(centro, acceso_responsable),
        {"accion": "suspender", "motivo": "x"},
    )
    acceso_responsable.refresh_from_db()
    assert acceso_responsable.estado == Estado.ACTIVO

    admin = User.objects.create_superuser("admin-cdi", "", "test1234")
    client.force_login(admin)
    client.post(
        _url_estado(centro, acceso_responsable),
        {"accion": "baja", "motivo": "x"},
    )
    acceso_responsable.refresh_from_db()
    assert acceso_responsable.estado == Estado.ACTIVO


def test_referente_comun_no_puede_usar_la_botonera(client, centro):
    _referente(centro, "resp", responsable=True)
    comun, _ = _referente(centro, "comun")
    _, otro = _referente(centro, "otro")
    client.force_login(comun)

    response = client.post(
        _url_estado(centro, otro), {"accion": "suspender", "motivo": "x"}
    )

    assert response.status_code == 403
    otro.refresh_from_db()
    assert otro.estado == Estado.ACTIVO


def test_responsable_de_otro_cdi_no_administra_este(client, centro):
    otro_centro = CentroDeInfancia.objects.create(nombre="Otro CDI")
    ajeno, _ = _referente(otro_centro, "ajeno", responsable=True)
    _, acceso = _referente(centro, "victima")
    client.force_login(ajeno)

    response = client.post(
        _url_estado(centro, acceso), {"accion": "baja", "motivo": "x"}
    )

    assert response.status_code == 403


def test_detalle_muestra_botonera_solo_al_responsable(client, centro):
    responsable, _ = _referente(centro, "resp", responsable=True)
    comun, _ = _referente(centro, "comun")
    url = reverse("centrodeinfancia_detalle", kwargs={"pk": centro.pk})

    client.force_login(responsable)
    response = client.get(url)
    assert response.context["puede_administrar_usuarios_cdi"] is True
    assert {a.user.username for a in response.context["usuarios_cdi"]} == {
        "resp",
        "comun",
    }
    assert "usuario-estado-btn" in response.content.decode()

    client.force_login(comun)
    response = client.get(url)
    assert response.context["puede_administrar_usuarios_cdi"] is False
    assert [a.user.username for a in response.context["usuarios_cdi"]] == ["comun"]
    assert "usuario-estado-btn" not in response.content.decode()


def test_responsable_genera_otro_referente(client, centro, settings):
    settings.DOMINIO = "http://testserver"
    responsable, _ = _referente(centro, "resp", responsable=True)
    client.force_login(responsable)

    response = client.post(
        reverse("centrodeinfancia_generar_usuario", kwargs={"pk": centro.pk}),
        {
            "first_name": "Luis",
            "last_name": "Pérez",
            "email": "luis@example.com",
            "dni": "28456789",
            "cuil": "20284567898",
        },
    )

    assert response.status_code == 200
    nuevo = AccesoCDI.objects.get(user__email="luis@example.com")
    assert nuevo.centro == centro
    assert nuevo.estado == Estado.ACTIVO
    assert nuevo.es_responsable is False


# ── Cambio de referente en la ficha ──────────────────────────────────────


def _request(user):
    request = RequestFactory().post("/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)  # pylint: disable=protected-access
    return request


def test_cambio_de_persona_crea_nuevo_responsable_y_conserva_al_anterior(
    centro, settings
):
    settings.DOMINIO = "http://testserver"
    anterior, acceso_anterior = _referente(centro, "ana", responsable=True)
    email_anterior = anterior.email
    centro.nombre_referente = "Juan"
    centro.apellido_referente = "Díaz"
    centro.email_referente = "juan@example.com"
    centro.dni_referente = "28456789"
    centro.save()

    actualizar_referente_cdi(
        _request(anterior),
        centro,
        dni_anterior="30123456",
        email_anterior="ana@example.com",
    )

    nuevo = AccesoCDI.objects.get(user__email="juan@example.com")
    assert nuevo.es_responsable is True
    acceso_anterior.refresh_from_db()
    anterior.refresh_from_db()
    assert acceso_anterior.es_responsable is False
    assert acceso_anterior.estado == Estado.ACTIVO
    # La cuenta del anterior no se reasigna al nuevo referente.
    assert anterior.email == email_anterior


def test_misma_persona_con_otro_email_sincroniza_su_cuenta(centro):
    responsable, acceso = _referente(centro, "ana", responsable=True)
    responsable.profile.must_change_password = True
    responsable.profile.save()
    centro.email_referente = "ana.nueva@example.com"
    centro.save()

    actualizar_referente_cdi(
        _request(responsable),
        centro,
        dni_anterior="30123456",
        email_anterior=responsable.email,
    )

    responsable.refresh_from_db()
    assert responsable.email == "ana.nueva@example.com"
    assert AccesoCDI.objects.filter(centro=centro).count() == 1
    acceso.refresh_from_db()
    assert acceso.es_responsable is True


def test_cambio_a_un_referente_existente_lo_reactiva_como_responsable(centro):
    anterior, _ = _referente(centro, "ana", responsable=True)
    existente, acceso_existente = _referente(centro, "luis", estado=Estado.BAJA)
    centro.nombre_referente = "Luis"
    centro.apellido_referente = "Pérez"
    centro.email_referente = existente.email
    centro.dni_referente = "28456789"
    centro.save()

    actualizar_referente_cdi(
        _request(anterior),
        centro,
        dni_anterior="30123456",
        email_anterior="ana@example.com",
    )

    acceso_existente.refresh_from_db()
    assert (acceso_existente.estado, acceso_existente.es_responsable) == (
        Estado.ACTIVO,
        True,
    )
    assert AccesoCDI.objects.filter(centro=centro, es_responsable=True).count() == 1


# ── "Generar usuario" con validación RENAPER ─────────────────────────────

VALORES_USUARIO = {
    "dni": 28456789,
    "last_name": "Pérez",
    "first_name": "Luis",
    "cuil": "20284567898",
}


def test_generar_usuario_toma_la_identidad_del_token_renaper(client, centro, settings):
    settings.DOMINIO = "http://testserver"
    responsable, _ = _referente(centro, "resp", responsable=True)
    client.force_login(responsable)

    client.post(
        reverse("centrodeinfancia_generar_usuario", kwargs={"pk": centro.pk}),
        {
            "first_name": "Alterado",
            "last_name": "Alterado",
            "email": "luis@example.com",
            "dni": "99999999",
            "cuil": "20284567898",
            "renaper_token_usuario_cdi": crear_token(
                "usuario_cdi", responsable, VALORES_USUARIO
            ),
        },
    )

    nuevo = User.objects.get(email="luis@example.com")
    assert (nuevo.first_name, nuevo.last_name) == ("Luis", "Pérez")
    assert nuevo.profile.dni == "28456789"


def test_primer_usuario_usa_la_identidad_verificada_de_la_ficha(client, centro):
    centro.cuil_referente = "27301234568"
    centro.campos_verificados_renaper = [
        "nombre_referente",
        "apellido_referente",
        "dni_referente",
        "cuil_referente",
    ]
    centro.save()
    admin = User.objects.create_superuser("admin-generar", "", "test1234")
    client.force_login(admin)

    form = client.get(
        reverse("centrodeinfancia_generar_usuario", kwargs={"pk": centro.pk})
    ).context["form"]

    assert form.modos_renaper["usuario_cdi"] == "verificado"
    assert form.fields["dni"].disabled is True
    assert form.fields["email"].disabled is False


def test_generar_primer_referente_lo_asigna_como_responsable(client, centro, settings):
    settings.DOMINIO = "http://testserver"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    admin = User.objects.create_superuser("admin-primer-referente", "", "test1234")
    client.force_login(admin)
    response = client.post(
        reverse("centrodeinfancia_generar_usuario", kwargs={"pk": centro.pk}),
        {
            "first_name": centro.nombre_referente,
            "last_name": centro.apellido_referente,
            "email": centro.email_referente,
            "dni": centro.dni_referente,
            "cuil": "27301234568",
        },
    )
    assert response.status_code == 200
    acceso = AccesoCDI.objects.get(centro=centro)
    assert acceso.es_responsable is True
    assert puede_administrar_usuarios_cdi(acceso.user, centro) is True


@pytest.mark.parametrize("estado", [Estado.ACTIVO, Estado.BAJA])
def test_guardar_ficha_recupera_referente_sin_responsable(centro, estado):
    referente, acceso = _referente(centro, "ana", estado=estado)
    admin = User.objects.create_superuser("admin-recuperar", "", "test1234")
    actualizar_referente_cdi(
        _request(admin),
        centro,
        dni_anterior=centro.dni_referente,
        email_anterior=centro.email_referente,
    )
    acceso.refresh_from_db()
    assert acceso.es_responsable is True
    assert acceso.estado == Estado.ACTIVO
    assert AccesoCDI.objects.filter(centro=centro).count() == 1
    assert puede_administrar_usuarios_cdi(referente, centro) is True


@pytest.mark.parametrize("cuenta_temporal", [True, False])
def test_recuperar_responsable_con_otro_email_conserva_su_cuenta(
    centro, cuenta_temporal
):
    referente, acceso = _referente(centro, "ana")
    referente.profile.must_change_password = cuenta_temporal
    referente.profile.save(update_fields=["must_change_password"])
    admin = User.objects.create_superuser("admin-recuperar-email", "", "test1234")
    centro.email_referente = "ana.nueva@example.com"
    centro.save()
    actualizar_referente_cdi(
        _request(admin),
        centro,
        dni_anterior=centro.dni_referente,
        email_anterior="ana@example.com",
    )
    referente.refresh_from_db()
    acceso.refresh_from_db()
    assert acceso.es_responsable is True
    assert User.objects.count() == 2
    assert AccesoCDI.objects.filter(centro=centro).count() == 1
    assert referente.email == (
        "ana.nueva@example.com" if cuenta_temporal else "ana@example.com"
    )


def test_usuarios_siguientes_arrancan_pidiendo_el_dni(client, centro):
    responsable, _ = _referente(centro, "resp", responsable=True)
    client.force_login(responsable)

    response = client.get(
        reverse("centrodeinfancia_generar_usuario", kwargs={"pk": centro.pk})
    )

    assert response.context["form"].modos_renaper["usuario_cdi"] == "dni"
    assert 'data-renaper-bloque="usuario_cdi"' in response.content.decode()
