"""Fixtures compartidas de los tests de Centro de Infancia."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _limite_renaper_por_test():
    """El límite de consultas RENAPER vive en cache: cada test arranca de cero."""
    cache.clear()
    yield
    cache.clear()
