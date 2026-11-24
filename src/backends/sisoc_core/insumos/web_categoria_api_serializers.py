"""Explicit transport shapes for the INS-B category circuit."""

from rest_framework import serializers

from insumos.web_api_serializers import InsumoSelectOptionSerializer

# Output/request descriptions only; the existing ModelForm owns persistence.
# pylint: disable=abstract-method


class CategoriaReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    programa = serializers.CharField()
    orden = serializers.IntegerField()
    activo = serializers.BooleanField()


class CategoriaCapabilitiesSerializer(serializers.Serializer):
    can_add = serializers.BooleanField()
    can_change = serializers.BooleanField()
    can_delete = serializers.BooleanField()


class CategoriaPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    pages = serializers.IntegerField()
    capabilities = CategoriaCapabilitiesSerializer()
    results = CategoriaReadSerializer(many=True)


class CategoriaInitialSerializer(serializers.Serializer):
    programa = serializers.CharField(allow_blank=True)
    nombre = serializers.CharField(allow_blank=True)
    descripcion = serializers.CharField(allow_blank=True)
    orden = serializers.CharField(allow_blank=True)
    activo = serializers.BooleanField()


class CategoriaOptionsSerializer(serializers.Serializer):
    programa = InsumoSelectOptionSerializer(many=True)


class CategoriaFormSerializer(serializers.Serializer):
    initial = CategoriaInitialSerializer()
    options = CategoriaOptionsSerializer()
    current_file = serializers.JSONField(allow_null=True)


class CategoriaRequestSerializer(serializers.Serializer):
    programa = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField(required=False, allow_blank=True)
    orden = serializers.IntegerField()
    activo = serializers.BooleanField(required=False)


class CategoriaConfirmationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
