"""API de encuestas consumida por la PWA de Espacios Comunitarios."""

from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_permissions import AccesoEspaciosComunitarios
from .services_pwa import listar_encuestas_pwa, responder_encuesta_pwa


class RespuestaEncuestaPWASerializer(
    serializers.Serializer
):  # pylint: disable=abstract-method
    response_id = serializers.UUIDField()
    respuestas = serializers.DictField(child=serializers.JSONField(), allow_empty=True)


class EncuestasPWAView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, AccesoEspaciosComunitarios]

    def get(self, request):
        return Response(listar_encuestas_pwa(request.user))


class ResponderEncuestaPWAView(EncuestasPWAView):
    http_method_names = ["post", "options"]

    def post(self, request, ronda_id):
        serializer = RespuestaEncuestaPWASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resultado = responder_encuesta_pwa(
                ronda_id, request.user, serializer.validated_data["respuestas"]
            )
        except ValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)
        return Response(resultado)
