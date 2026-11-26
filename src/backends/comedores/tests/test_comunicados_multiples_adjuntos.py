import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from comunicados.forms import MultipleFileField


def test_multiples_adjuntos_conservan_orden_y_validan_cada_archivo():
    campo = MultipleFileField()
    primero = SimpleUploadedFile("primero.pdf", b"primero")
    segundo = SimpleUploadedFile("segundo.pdf", b"segundo")

    assert campo.clean([primero, segundo]) == [primero, segundo]

    vacio = SimpleUploadedFile("vacio.pdf", b"")
    with pytest.raises(ValidationError) as error:
        campo.clean([primero, vacio])
    assert error.value.code == "empty"
