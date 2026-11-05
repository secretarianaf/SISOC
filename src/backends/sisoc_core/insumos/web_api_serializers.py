"""Explicit output-only DTOs for the INS-A read and form surfaces."""

from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

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


class InsumoSelectOptionSerializer(serializers.Serializer):
    value = serializers.CharField(allow_blank=True)
    label = serializers.CharField()
    programa_id = serializers.CharField(required=False)


class InsumoFormInitialSerializer(serializers.Serializer):
    programa = serializers.CharField(allow_blank=True)
    categoria = serializers.CharField(allow_blank=True)
    titulo = serializers.CharField(allow_blank=True)
    descripcion = serializers.CharField(allow_blank=True)
    activo = serializers.BooleanField()


class InsumoCurrentFileSerializer(serializers.Serializer):
    name = serializers.CharField()
    download_url = serializers.CharField(allow_null=True)


class InsumoFormOptionsSerializer(serializers.Serializer):
    programa = InsumoSelectOptionSerializer(many=True)
    categoria = InsumoSelectOptionSerializer(many=True)


class InsumoFormSchema(serializers.Serializer):
    initial = InsumoFormInitialSerializer()
    options = InsumoFormOptionsSerializer()
    current_file = InsumoCurrentFileSerializer(allow_null=True)


@extend_schema_field(OpenApiTypes.BINARY)
class InsumoUploadField(serializers.FileField):
    """Represent multipart uploads as binary rather than storage URLs."""


class InsumoCreateRequestSerializer(serializers.Serializer):
    programa = serializers.CharField()
    categoria = serializers.CharField(required=False, allow_blank=True)
    titulo = serializers.CharField()
    descripcion = serializers.CharField(required=False, allow_blank=True)
    archivo = InsumoUploadField()
    activo = serializers.BooleanField(required=False)


class InsumoEditRequestSerializer(serializers.Serializer):
    programa = serializers.CharField()
    categoria = serializers.CharField(required=False, allow_blank=True)
    titulo = serializers.CharField()
    descripcion = serializers.CharField(required=False, allow_blank=True)
    archivo = InsumoUploadField(required=False)
    activo = serializers.BooleanField(required=False)


class InsumoMutationSuccessSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    message = serializers.CharField()
    redirect = serializers.CharField()


class InsumoFormErrorDetailSerializer(serializers.Serializer):
    message = serializers.CharField()
    code = serializers.CharField()


class InsumoFormErrorsSerializer(serializers.Serializer):
    errors = serializers.DictField(
        child=serializers.ListField(child=InsumoFormErrorDetailSerializer())
    )


class InsumosWebErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    state = serializers.CharField(required=False)
    required_action_url = serializers.CharField(required=False, allow_null=True)


class InsumoDeleteConfirmationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()
