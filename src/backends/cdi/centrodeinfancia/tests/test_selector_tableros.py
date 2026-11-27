"""El selector de tableros solo expone CDI activos al equipo de Datos."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import CentroDeInfancia

pytestmark = pytest.mark.django_db


def test_selector_exige_rol_y_filtra_estados():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    sinrol = User.objects.create_user(username="sinrol", is_staff=True)
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    activo = CentroDeInfancia.objects.create(nombre="Activo", estado="activo")
    pendiente = CentroDeInfancia.objects.create(nombre="Pendiente", estado="pendiente")
    baja = CentroDeInfancia.objects.create(nombre="Baja", estado="baja")
    eliminado = CentroDeInfancia.objects.create(nombre="Eliminado", estado="activo")
    eliminado.deleted_at = timezone.now()
    eliminado.save(update_fields=["deleted_at"])
    client = Client()
    url = reverse("cdi_selector_tableros")
    client.force_login(sinrol)
    assert client.get(url).status_code == 403
    assert client.head(url, HTTP_X_VIEW="1").status_code == 403
    client.force_login(actor)
    response = client.get(
        url, {"ids": f"{activo.pk},{pendiente.pk},{baja.pk},{eliminado.pk}"}
    )
    assert response.status_code == 200
    assert response.json()["centros"] == [{"id": activo.pk, "nombre": "Activo"}]


def test_selector_rechaza_identificadores_malformados():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    client = Client()
    client.force_login(actor)
    url = reverse("cdi_selector_tableros")
    assert client.get(url, {"ids": "1,0"}).status_code == 400
    assert client.get(url, {"ids": "1,1"}).status_code == 400


def test_selector_admite_superusuario_activo_sin_rol_de_datos():
    actor = User.objects.create_superuser(username="supervisor", password="x")
    activo = CentroDeInfancia.objects.create(nombre="Activo", estado="activo")
    client = Client()
    client.force_login(actor)
    respuesta = client.get(reverse("cdi_selector_tableros"), {"ids": str(activo.pk)})
    assert respuesta.status_code == 200
    assert respuesta.json()["centros"] == [{"id": activo.pk, "nombre": "Activo"}]
    actor.is_active = False
    actor.save(update_fields=["is_active"])
    assert client.get(reverse("cdi_selector_tableros")).status_code == 403
