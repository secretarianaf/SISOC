"""Puerto de auditoría para eventos de autenticación."""

from audittrail.auth import registrar_evento_auth

EVENTO_LOGIN_OK = "login_ok"
EVENTO_LOGIN_ERROR = "login_error"
EVENTO_LOGOUT = "logout"
EVENTO_ME_OK = "me_ok"
RESULTADO_OK = "ok"
RESULTADO_ERROR = "error"

__all__ = [
    "registrar_evento_auth",
    "EVENTO_LOGIN_OK",
    "EVENTO_LOGIN_ERROR",
    "EVENTO_LOGOUT",
    "EVENTO_ME_OK",
    "RESULTADO_OK",
    "RESULTADO_ERROR",
]
