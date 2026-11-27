"""Almacenamiento del XLSX bruto de las cargas masivas del CDF."""

from django.core.files.storage import FileSystemStorage


class AlmacenamientoCargaMasivaPrivado(FileSystemStorage):
    def url(self, name):
        raise NotImplementedError(
            "Los originales de carga masiva son privados: se descargan desde el lote."
        )


def almacenamiento_carga_masiva_privado():
    return AlmacenamientoCargaMasivaPrivado()
