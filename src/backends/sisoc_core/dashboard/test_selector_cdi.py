"""Validación del contrato CDI sin asumir que el servicio está disponible."""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from core.internal_services import RespuestaInterna
from dashboard.services.selector_cdi import buscar_centros, validar_centros


def test_busqueda_valida_formato_y_paginacion():
    respuesta = RespuestaInterna(
        200, {"centros": [{"id": 1, "nombre": "Centro"}], "hay_mas": False}
    )
    with patch(
        "dashboard.services.selector_cdi.pedir_json_interno", return_value=respuesta
    ) as pedir:
        assert buscar_centros(object(), "Centro", 1) == respuesta.data
    assert pedir.call_args.kwargs["params"] == {"q": "Centro", "pagina": "1"}


@pytest.mark.parametrize(
    "respuesta",
    [
        RespuestaInterna(503, None),
        RespuestaInterna(
            200, {"centros": [{"id": True, "nombre": "X"}], "hay_mas": False}
        ),
        RespuestaInterna(
            200,
            {
                "centros": [{"id": 1, "nombre": "X"}, {"id": 1, "nombre": "X"}],
                "hay_mas": False,
            },
        ),
    ],
)
def test_rechaza_servicio_caido_o_respuesta_invalida(respuesta):
    with patch(
        "dashboard.services.selector_cdi.pedir_json_interno", return_value=respuesta
    ):
        with pytest.raises(ValidationError):
            buscar_centros(object(), "", 1)


def test_validacion_exige_todos_los_cdi_solicitados():
    respuesta = RespuestaInterna(
        200, {"centros": [{"id": 1, "nombre": "Centro"}], "hay_mas": False}
    )
    with patch(
        "dashboard.services.selector_cdi.pedir_json_interno", return_value=respuesta
    ):
        assert validar_centros(object(), [1]) == frozenset({1})
        with pytest.raises(ValidationError):
            validar_centros(object(), [1, 2])


@pytest.mark.django_db
def test_contrato_local_cdi_descarta_inactivos():
    from centrodeinfancia.models import CentroDeInfancia

    call_command("create_groups", verbosity=0)
    usuario = User.objects.create_user(username="datos")
    usuario.groups.add(Group.objects.get(name="Equipo de Datos"))
    activo = CentroDeInfancia.objects.create(nombre="Centro activo", estado="activo")
    pendiente = CentroDeInfancia.objects.create(
        nombre="Centro pendiente", estado="pendiente"
    )
    request = RequestFactory().get("/dashboard/")
    request.user = usuario
    with patch("core.internal_services.backend_de_app", return_value=None):
        assert validar_centros(request, [activo.pk]) == frozenset({activo.pk})
        with pytest.raises(ValidationError):
            validar_centros(request, [activo.pk, pendiente.pk])
