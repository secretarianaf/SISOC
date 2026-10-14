"""Validación de los pedidos multipart de la API de inspecciones.

Las respuestas las arman los services con el formato del contrato
(``inspecciones.services``); acá sólo se valida la forma de lo que llega.
"""

# Serializers de solo validación: no implementan create()/update() porque no
# se usan para .save(). W0223 (abstract-method) es falso positivo de DRF.
# pylint: disable=abstract-method

from rest_framework import serializers


class ImagenUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    tipo = serializers.CharField(max_length=20)
    descripcion = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000
    )
    capturada_at = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )


class PdfUploadSerializer(serializers.Serializer):
    archivo = serializers.FileField()


class NotificacionUploadSerializer(serializers.Serializer):
    uuid = serializers.CharField(max_length=64)
    notificada_at = serializers.CharField(required=False, allow_blank=True, default="")
    receptor_nombre = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )
    receptor_cargo = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=200
    )
    condicion_firma = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=20
    )
    motivo = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    numero_confirmado = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=20
    )
    reemplaza_uuid = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=64
    )
    motivo_correccion = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
