"""CO-I2: ``delete_images`` solo borra imágenes del comedor indicado."""

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from comedores.models import Comedor, ImagenComedor
from comedores.services.comedor_service import ComedorService

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_aislado(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _imagen(comedor, nombre):
    imagen = ImagenComedor(comedor=comedor)
    imagen.imagen.save(nombre, ContentFile(b"x"), save=True)
    return imagen


def _post(*imagenes):
    return {f"imagen_ciudadano-borrar-{img.pk}": "on" for img in imagenes}


def test_borra_la_imagen_propia_del_comedor():
    comedor = Comedor.objects.create(nombre="Comedor A")
    propia = _imagen(comedor, "a.jpg")

    ComedorService.delete_images(_post(propia), comedor.pk)

    assert not ImagenComedor.objects.filter(pk=propia.pk).exists()


def test_no_borra_la_imagen_de_otro_comedor():
    comedor_a = Comedor.objects.create(nombre="Comedor A")
    comedor_b = Comedor.objects.create(nombre="Comedor B")
    propia = _imagen(comedor_a, "a.jpg")
    ajena = _imagen(comedor_b, "b.jpg")
    nombre_ajena = ajena.imagen.name

    ComedorService.delete_images(_post(propia, ajena), comedor_a.pk)

    assert not ImagenComedor.objects.filter(pk=propia.pk).exists()
    assert ImagenComedor.objects.filter(pk=ajena.pk, comedor=comedor_b).exists()
    assert default_storage.exists(nombre_ajena)
