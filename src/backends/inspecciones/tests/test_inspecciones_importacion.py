"""Backoffice: quién entra al panel.

La importación del padrón está en ``test_inspecciones_padron.py`` y la de
asignaciones, junto con el resto del panel, en ``test_inspecciones_panel.py``.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_panel_solo_para_coordinacion_o_permiso(client, inspector_a, coordinacion):
    url = reverse("inspecciones_panel")

    client.force_login(inspector_a)
    assert client.get(url).status_code == 403

    client.force_login(coordinacion)
    assert client.get(url).status_code == 200

    gestor = get_user_model().objects.create_user(username="gestor", password="x")
    gestor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="inspecciones", codename="gestionar_inspecciones"
        )
    )
    client.force_login(gestor)
    assert client.get(url).status_code == 200


def test_panel_muestra_los_totales(client, coordinacion, escuela):
    client.force_login(coordinacion)

    respuesta = client.get(reverse("inspecciones_panel"))

    resumen = respuesta.context["resumen"]
    assert resumen["escuelas"] == 1
    assert resumen["escuelas_a_revisar"] == 0
    assert "Escuelas con datos a revisar" in respuesta.content.decode()
