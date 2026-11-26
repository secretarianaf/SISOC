"""Every pagos URL requires the same permission as Cupos and the DRF pagos API."""

import pytest
from django.urls import reverse

from celiaquia.models import PagoExpediente
from celiaquia.tests.test_permisos_dashboard_reporte import _usuario
from core.models import Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture
def urls(settings):
    settings.REACT_VERTICALES_ACTIVAS = ()
    provincia = Provincia.objects.create(nombre="Provincia Pagos")
    creador = _usuario("creador_pago")
    pago = PagoExpediente.objects.create(
        provincia=provincia, periodo="2026-11", creado_por=creador
    )
    return {
        "list": ("get", reverse("pago_expediente_list", args=[provincia.pk])),
        "create": ("post", reverse("pago_expediente_create", args=[provincia.pk])),
        "detail": ("get", reverse("pago_expediente_detail", args=[pago.pk])),
        "export": ("get", reverse("pago_expediente_export", args=[pago.pk])),
        "nomina": ("get", reverse("pago_nomina_export_actual", args=[pago.pk])),
    }


@pytest.mark.parametrize("name", ["list", "create", "detail", "export", "nomina"])
def test_anonymous_and_users_without_permission_are_denied(client, urls, name):
    method, url = urls[name]
    count = PagoExpediente.objects.count()
    anonymous = getattr(client, method)(url)
    assert anonymous.status_code in {302, 403}
    client.force_login(_usuario(f"sin_permiso_{name}", "view_expediente"))
    assert getattr(client, method)(url).status_code == 403
    assert PagoExpediente.objects.count() == count


@pytest.mark.parametrize("name", ["list", "detail"])
def test_cupo_dashboard_permission_keeps_access(client, urls, name):
    method, url = urls[name]
    client.force_login(_usuario(f"con_permiso_{name}", "view_cupo_dashboard"))
    assert getattr(client, method)(url).status_code == 200
