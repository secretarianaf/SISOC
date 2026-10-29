"""El persistidor común conserva los snapshots recibidos de autenticación."""

from types import SimpleNamespace
from uuid import UUID

from django.test import RequestFactory

from audittrail.auth import registrar_evento_auth


def test_registra_evento_y_snapshots_sin_consultar_el_dominio(mocker):
    crear = mocker.patch("audittrail.auth.AuditoriaSesionPWA.objects.create")
    request = RequestFactory().post(
        "/api/users/login/",
        HTTP_X_FORWARDED_FOR="192.0.2.10, 192.0.2.11",
        HTTP_USER_AGENT="cliente-pwa",
        HTTP_X_APP_VERSION="1.2.3",
        HTTP_X_PLATFORM="android",
        HTTP_X_PWA_STANDALONE="true",
    )
    user = SimpleNamespace(is_authenticated=True)
    session_id = UUID("00000000-0000-0000-0000-000000000001")

    registrar_evento_auth(
        request=request,
        evento="login_ok",
        resultado="ok",
        user=user,
        username_intentado="usuario",
        codigo_respuesta=200,
        session_id=session_id,
        contexto={
            "roles": ["representante"],
            "comedores_representados": [8, 3, 8],
            "comedor_operador_id": 5,
        },
    )

    crear.assert_called_once_with(
        user=user,
        username_intentado="usuario",
        evento="login_ok",
        resultado="ok",
        ip="192.0.2.10",
        user_agent="cliente-pwa",
        path="/api/users/login/",
        metodo_http="POST",
        codigo_respuesta=200,
        motivo_error=None,
        session_id=session_id,
        rol_pwa_snapshot=["representante"],
        comedor_ids_snapshot=[3, 5, 8],
        app_version="1.2.3",
        platform="android",
        is_standalone=True,
    )
