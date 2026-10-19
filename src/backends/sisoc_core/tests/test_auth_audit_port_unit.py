"""El registro común de autenticación no necesita un proveedor de negocio."""

from django.db import DatabaseError
from django.test import RequestFactory
from audittrail.models import AuditoriaSesionPWA
from usuarios.auth_audit import registrar_evento_auth


def test_registra_sin_consultar_espacios(db, mocker):
    contexto = mocker.patch(
        "pwa.services.accesos.get_pwa_context", side_effect=AssertionError
    )
    registrar_evento_auth(
        request=RequestFactory().post("/api/users/login/"),
        evento="login_error",
        resultado="error",
        username_intentado="invalido",
        codigo_respuesta=401,
    )
    assert AuditoriaSesionPWA.objects.get().username_intentado == "invalido"
    contexto.assert_not_called()


def test_error_de_persistencia_se_registra_sin_bloquear(mocker):
    mocker.patch(
        "audittrail.auth.AuditoriaSesionPWA.objects.create", side_effect=DatabaseError
    )
    log = mocker.patch("audittrail.auth.LOGGER.exception")
    registrar_evento_auth(
        request=RequestFactory().post("/api/users/login/"),
        evento="login_error",
        resultado="error",
    )
    log.assert_called_once()
