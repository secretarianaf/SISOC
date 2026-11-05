"""Explicit output-only DTOs for the INS-A read surface."""

from rest_framework import serializers

# These serializers project read-only values; no persistence methods are needed.
# pylint: disable=abstract-method


class InsumoReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()
    activo = serializers.BooleanField()
    categoria = serializers.CharField()
    fecha_carga = serializers.CharField()
    cargado_por = serializers.CharField()
    download_url = serializers.CharField()


class InsumoFiltersSerializer(serializers.Serializer):
    busqueda = serializers.CharField(allow_blank=True)
    categoria = serializers.CharField(allow_blank=True)


class InsumoPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    pages = serializers.IntegerField()
    filters = InsumoFiltersSerializer()
    results = InsumoReadSerializer(many=True)


class InsumoCategoryOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class InsumosOptionsSerializer(serializers.Serializer):
    categories = InsumoCategoryOptionSerializer(many=True)
