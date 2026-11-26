"""#2946: native VAT delete confirmations (plan de estudio and centro). Synthetic data."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, ModalidadCursada, PlanVersionCurricular, Sector

pytestmark = pytest.mark.django_db

_COUNTER = itertools.count()


def _sse_client(*codes):
    user = get_user_model().objects.create_user(f"baja{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    rol, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_vat_sse",
        defaults={"name": "role_vat_sse"},
    )
    user.user_permissions.add(rol)
    client = Client()
    client.force_login(user)
    return client


def test_plan_delete_confirmation_renders_with_the_plan_and_its_cancel_link():
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricista domiciliario",
        provincia=Provincia.objects.create(nombre="Buenos Aires"),
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
        horas_reloj=120,
        nivel_requerido="sin_requisito",
        nivel_certifica="nivel_1",
    )
    client = _sse_client("delete_planversioncurricular")

    response = client.get(reverse("vat_planversioncurricular_delete", args=[plan.pk]))

    assert response.status_code == 200
    body = response.content.decode()
    assert "Electricista domiciliario (Presencial)" in body
    assert (
        f'href="{reverse("vat_planversioncurricular_detail", args=[plan.pk])}"' in body
    )
    assert PlanVersionCurricular.objects.filter(pk=plan.pk).exists()


def test_centro_delete_cancel_returns_to_the_vat_centro_detail():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    centro = Centro.objects.create(
        nombre="CFP 401",
        codigo="060000001",
        provincia=provincia,
        municipio=municipio,
        localidad=Localidad.objects.create(nombre="Tolosa", municipio=municipio),
    )
    client = _sse_client("view_centro")

    response = client.get(reverse("vat_centro_delete", args=[centro.pk]))

    assert response.status_code == 200
    body = response.content.decode()
    assert f'href="{reverse("vat_centro_detail", args=[centro.pk])}"' in body
    assert f'href="{reverse("centro_detail", args=[centro.pk])}"' not in body
    assert Centro.objects.filter(pk=centro.pk).exists()
