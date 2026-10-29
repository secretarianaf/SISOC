"""Regresiones de inferencia por proyecto para homologación (#2642)."""

from datetime import date

import pytest

from rendicioncuentasmensual.services import RendicionCuentaMensualService
from tests.test_rendicioncuentasmensual_domain_rules import (
    scopes,
)  # pylint: disable=unused-import


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codigo,nombre,linea",
    [
        ("AMBA", "", "secos"),
        ("AMBA111", "", "secos"),
        ("AMBA123", "", "secos"),
        ("AMBA-123", "", "secos"),
        ("AMBA_123", "", "secos"),
        ("AMBA 1111", "", "secos"),
        (" amba111 ", "", "secos"),
        ("CODIGO", " AMBA 1111 ", "secos"),
        ("XAMBA111", "", "tradicional"),
        ("CODIGO", " amba ", "secos"),
        ("OTRO", "Otro", "tradicional"),
    ],
)
def test_alta_deriva_linea_del_proyecto_aunque_cliente_envie_otra(
    scopes, codigo, nombre, linea
):
    comedor, proyecto, _, _ = scopes
    proyecto.codigo, proyecto.nombre = codigo, nombre
    proyecto.save()
    rendicion = RendicionCuentaMensualService.crear_rendicion_mobile(
        comedor=comedor,
        data={
            "proyecto_id": proyecto.pk,
            "convenio": "P01",
            "numero_rendicion": 1,
            "periodo_inicio": date(2026, 1, 1),
            "periodo_fin": date(2026, 1, 31),
            "linea_programatica": "tradicional" if linea == "secos" else "secos",
        },
    )
    assert rendicion.linea_programatica == linea


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codigo,linea", [("AMBA 1111", "secos"), ("XAMBA123", "tradicional")]
)
def test_api_informa_y_valida_linea_del_proyecto(scopes, monkeypatch, codigo, linea):
    from comedores.api_views import ComedorDetailViewSet
    from comedores.models import Programas
    from pwa.models import AccesoComedorPWA
    from tests.test_pwa_comedores_api import (
        _create_pwa_user,
        _grant_mobile_rendicion_permission,
        _token_client,
    )

    comedor, proyecto, _, _ = scopes
    proyecto.codigo = codigo
    proyecto.save()
    comedor.programa, _ = Programas.objects.get_or_create(nombre="Abordaje Comunitario")
    comedor.save()
    catalogo = ComedorDetailViewSet._get_active_projects_by_organization([comedor])
    item = next(
        item for item in catalogo[comedor.organizacion_id] if item["id"] == proyecto.pk
    )
    assert item["linea_programatica"] == linea

    usuario = _create_pwa_user(
        comedor=comedor,
        role=AccesoComedorPWA.ROL_REPRESENTANTE,
        username="amba_hml",
    )
    _grant_mobile_rendicion_permission(usuario)
    client = _token_client(usuario)
    lineas_validadas = []
    original = RendicionCuentaMensualService.validar_datos_generales

    def validar(**kwargs):
        lineas_validadas.append(kwargs["linea_programatica"])
        return original(**kwargs)

    monkeypatch.setattr(
        RendicionCuentaMensualService, "validar_datos_generales", validar
    )
    response = client.post(
        f"/api/comedores/{comedor.pk}/rendiciones/validar/",
        {
            "proyecto_id": proyecto.pk,
            "convenio": "P01",
            "numero_rendicion": 1,
            "periodo_inicio": "2026-01-01",
            "periodo_fin": "2026-01-31",
            "linea_programatica": "tradicional" if linea == "secos" else "secos",
        },
        format="json",
    )
    assert response.status_code == 204, response.data
    assert lineas_validadas == [linea]
    assert not comedor.rendiciones_cuentas_mensuales.exists()
