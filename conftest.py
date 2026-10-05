"""Fixtures globales de pytest para todos los tests (kernel y verticales)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def global_temp_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="smoke_user",
        email="smoke_user@example.com",
        password="testpass",
    )


@pytest.fixture(name="superuser")
def superuser_fixture(db):
    user_model = get_user_model()
    return user_model.objects.create_superuser(
        username="smoke_admin",
        email="smoke_admin@example.com",
        password="testpass",
    )


@pytest.fixture
def auth_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture(name="api_key")
def api_key_fixture(db):
    # Import diferido: el conftest raíz se carga antes de que Django arme las apps.
    from rest_framework_api_key.models import (
        APIKey,
    )  # pylint: disable=import-outside-toplevel

    _, key = APIKey.objects.create_key(name="smoke-tests")
    return key


@pytest.fixture
def api_client(api_key):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {api_key}")
    return client
