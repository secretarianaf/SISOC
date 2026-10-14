"""El abogado de la dupla no adjunta ni elimina documentacion de admision (#2654)."""

from types import SimpleNamespace

import pytest

from admisiones.services.admisiones_service import AdmisionService
from admisiones.templatetags.admisiones_tags import (
    puede_gestionar_documentacion_admision,
)
from admisiones.views import web_views as module

VIEW_PERMS = {
    "comedores.view_comedor",
    "admisiones.view_admision",
    "acompanamientos.view_informacionrelevante",
}
ROLE_ABOGADO = "auth.role_abogado_dupla"
ROLE_TECNICO = "auth.role_tecnico_comedor"


class _Groups:
    def __init__(self, names=()):
        self._names = set(names)

    def filter(self, name):
        return SimpleNamespace(exists=lambda: name in self._names)


def _user(perms=(), groups=(), superuser=False):
    perms = set(perms)
    return SimpleNamespace(
        is_authenticated=True,
        is_superuser=superuser,
        has_perm=lambda code: code in perms,
        groups=_Groups(groups),
    )


def _abogado():
    return _user(perms=VIEW_PERMS | {ROLE_ABOGADO})


def _tecnico():
    return _user(perms=VIEW_PERMS | {ROLE_TECNICO})


@pytest.mark.parametrize(
    "user,esperado",
    [
        (_abogado(), True),
        (_tecnico(), False),
        (_user(perms=VIEW_PERMS | {ROLE_ABOGADO, ROLE_TECNICO}), False),
        (_user(perms=VIEW_PERMS | {ROLE_ABOGADO}, groups=["Tecnico Comedor"]), False),
        (_user(superuser=True), False),
        (None, False),
    ],
)
def test_es_abogado_dupla_sin_rol_tecnico(user, esperado):
    assert AdmisionService.es_abogado_dupla_sin_rol_tecnico(user) is esperado


@pytest.mark.parametrize(
    "user,esperado",
    [
        (_abogado(), False),
        (_tecnico(), True),
        (_user(perms=VIEW_PERMS), True),
        (_user(groups=["Tecnico Comedor"]), True),
        (_user(superuser=True), True),
        (_user(), False),
    ],
)
def test_puede_gestionar_documentacion_admision(user, esperado):
    assert puede_gestionar_documentacion_admision(user) is esperado


def test_subir_archivo_admision_rechaza_abogado(mocker):
    upload = mocker.patch(
        "admisiones.views.web_views.AdmisionService.handle_file_upload"
    )
    req = SimpleNamespace(FILES={"archivo": object()}, user=_abogado(), method="POST")

    resp = module.subir_archivo_admision(req, 1, 2)

    assert resp.status_code == 403
    upload.assert_not_called()


def test_crear_documento_personalizado_rechaza_abogado(mocker):
    crear = mocker.patch(
        "admisiones.views.web_views.AdmisionService.crear_documento_personalizado"
    )
    req = SimpleNamespace(
        FILES={"archivo": object()},
        POST={"nombre": "Doc"},
        user=_abogado(),
        method="POST",
    )

    resp = module.crear_documento_personalizado(req, 1)

    assert resp.status_code == 403
    crear.assert_not_called()


def test_detalle_documento_personalizado_post_rechaza_abogado(mocker):
    crear = mocker.patch(
        "admisiones.views.web_views.AdmisionService.crear_documento_personalizado"
    )
    req = SimpleNamespace(
        FILES={"archivo": object()},
        POST={"nombre": "Doc"},
        user=_abogado(),
        method="POST",
    )

    resp = module.AdmisionDetailView()._handle_documento_personalizado_post(req)

    assert resp.status_code == 403
    crear.assert_not_called()


def test_eliminar_archivo_admision_rechaza_abogado(mocker):
    delete = mocker.patch(
        "admisiones.views.web_views.AdmisionService.delete_admision_file"
    )
    req = SimpleNamespace(method="DELETE", user=_abogado(), GET={})

    resp = module.eliminar_archivo_admision(req, 1, 2)

    assert resp.status_code == 403
    delete.assert_not_called()
