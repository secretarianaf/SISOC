"""Fixtures compartidas de los tests de Celiaquia."""

import pytest

from celiaquia.services.expediente_service import (  # pylint: disable=no-name-in-module
    _estado_id,
)


@pytest.fixture(autouse=True)
def _limpiar_cache_de_estados():
    """Vacia el `lru_cache` de `_estado_id` entre tests.

    `_estado_id` memoiza el PK de cada `EstadoExpediente`. En produccion esos
    ids son estables, pero en los tests cada caso corre en una transaccion que
    se revierte: el id que quedo cacheado en un test apunta a una fila que ya no
    existe en el siguiente, y el `create_expediente` de ese siguiente test falla
    con un FK invalido. El sintoma aparece solo al correr dos tests juntos, que
    es la forma mas facil de perder una tarde.
    """

    _estado_id.cache_clear()
    yield
    _estado_id.cache_clear()
