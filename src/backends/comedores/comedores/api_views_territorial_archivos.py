"""Archivos adjuntos de los formularios (#2781), mixin de ``TerritorialComedorViewSet``.

- ``GET    /api/territorial/comedores/{id}/adjuntos/?formulario_tipo=&formulario_id=``
  -> lista de adjuntos de ese formulario.
- ``POST   /api/territorial/comedores/{id}/adjuntos/`` -> sube un documento
  (imagen JPG/PNG/WEBP o PDF, hasta 10 MB; 10 por formulario).
- ``DELETE /api/territorial/comedores/{id}/adjuntos/{adjunto_id}/`` -> borra un
  adjunto propio.

Mismas reglas que las fotos (``AdjuntosTerritorialMixin``): el comedor se
resuelve con ``_comedor_accesible()``, el alta es idempotente por ``client_uuid``
y solo borra quien lo subió. Todas las respuestas 200/201 devuelven
``{"adjuntos": [...]}`` con la lista completa del formulario.
"""

from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from relevamientos.models import ArchivoAdjunto
from relevamientos.services import adjuntos as adjuntos_service

TIPOS_FORMULARIO = {tipo for tipo, _ in ArchivoAdjunto.TIPO_CHOICES}


def _error(detalle, codigo=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": detalle}, status=codigo)


class ArchivosAdjuntosTerritorialMixin:
    """Usa del viewset: ``_comedor_accesible``, ``_fuera_de_zona`` y
    ``_leer_client_uuid``."""

    @staticmethod
    def _lista_adjuntos(request, comedor, formulario_tipo, formulario_id, codigo=200):
        adjuntos = adjuntos_service.adjuntos_de(
            comedor.id, formulario_tipo, formulario_id
        )
        return Response(
            {"adjuntos": adjuntos_service.serializar(adjuntos, request)},
            status=codigo,
        )

    @staticmethod
    def _validado(formulario):
        return Response(
            {
                "detail": (
                    "El registro está validado por el coordinador y sus "
                    "archivos no admiten cambios."
                ),
                "estado_validacion": formulario.estado_validacion,
            },
            status=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _leer_formulario(data):
        """``(tipo, id, error)`` con el par que identifica al formulario."""
        tipo = (data.get("formulario_tipo") or "").strip()
        if tipo not in TIPOS_FORMULARIO:
            return (
                None,
                None,
                _error(
                    "'formulario_tipo' debe ser uno de: "
                    + ", ".join(sorted(TIPOS_FORMULARIO))
                    + "."
                ),
            )
        formulario_id = str(data.get("formulario_id") or "").strip()
        if not formulario_id.isdigit() or int(formulario_id) > 2**31 - 1:
            return None, None, _error("'formulario_id' debe ser un entero.")
        return tipo, int(formulario_id), None

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="adjuntos",
        parser_classes=[MultiPartParser, FormParser],
    )
    def adjuntos(  # pylint: disable=too-many-return-statements,too-many-locals
        self, request, pk=None
    ):
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        origen = request.query_params if request.method == "GET" else request.data
        tipo, formulario_id, error = self._leer_formulario(origen)
        if error is not None:
            return error
        formulario = adjuntos_service.formulario_de_comedor(
            comedor, tipo, formulario_id
        )
        if formulario is None:
            return _error(
                "El formulario no existe en este comedor.", status.HTTP_404_NOT_FOUND
            )
        if request.method == "GET":
            return self._lista_adjuntos(request, comedor, tipo, formulario_id)

        # Idempotencia offline: el reintento con el mismo client_uuid no duplica.
        client_uuid = self._leer_client_uuid(request)
        previo = (
            ArchivoAdjunto.objects.filter(comedor=comedor, client_uuid=client_uuid)
            .only("formulario_tipo", "formulario_id")
            .first()
            if client_uuid
            else None
        )
        if previo is not None:
            if (previo.formulario_tipo, previo.formulario_id) != (tipo, formulario_id):
                return _error(
                    "El client_uuid ya se usó para un archivo de otro formulario."
                )
            return self._lista_adjuntos(request, comedor, tipo, formulario_id)
        if adjuntos_service.formulario_validado(formulario):
            return self._validado(formulario)
        archivo = request.FILES.get("archivo")
        if not archivo:
            return _error("Debe adjuntar un archivo en el campo 'archivo'.")
        extension, tipo_mime, detalle = adjuntos_service.validar_archivo(archivo)
        if detalle:
            return _error(detalle)
        if (
            adjuntos_service.adjuntos_de(comedor.id, tipo, formulario_id).count()
            >= adjuntos_service.MAX_ADJUNTOS_POR_FORMULARIO
        ):
            return _error(
                "Este formulario ya tiene el máximo de "
                f"{adjuntos_service.MAX_ADJUNTOS_POR_FORMULARIO} archivos. "
                "Borre alguno antes de subir otro."
            )
        nombre_original = (archivo.name or "")[:255]
        tamano = archivo.size
        archivo.name = adjuntos_service.nombre_en_disco(extension)
        adjunto = ArchivoAdjunto(
            comedor=comedor,
            formulario_tipo=tipo,
            formulario_id=formulario_id,
            archivo=archivo,
            nombre_original=nombre_original,
            tipo_mime=tipo_mime,
            tamano=tamano,
            client_uuid=client_uuid,
            subido_por=request.user,
        )
        try:
            adjunto.save()
        except IntegrityError:
            # Carrera con otro reintento del mismo client_uuid: se descarta la
            # copia recién guardada y se devuelve lo que ya existe.
            adjunto.archivo.delete(save=False)
            return self._lista_adjuntos(request, comedor, tipo, formulario_id)
        return self._lista_adjuntos(
            request, comedor, tipo, formulario_id, status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"adjuntos/(?P<adjunto_id>[0-9]+)",
        url_name="adjunto-borrar",
    )
    def borrar_adjunto(self, request, pk=None, adjunto_id=None):
        """Borra un adjunto que el propio técnico subió desde la app.

        - 200 ``{"adjuntos": [...]}``: borrado; lista del formulario.
        - 404: no existe en este comedor (idempotente para la app).
        - 403: lo subió otro técnico.
        - 409: el formulario ya está Validado por el coordinador.
        """
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        adjunto = comedor.archivos_adjuntos.filter(pk=adjunto_id).first()
        if adjunto is None:
            return _error(
                "El archivo no existe en este comedor.", status.HTTP_404_NOT_FOUND
            )
        if adjunto.subido_por_id != request.user.id:
            return _error(
                "El archivo lo subió otro técnico y no se puede borrar.",
                status.HTTP_403_FORBIDDEN,
            )
        formulario = adjuntos_service.formulario_de_comedor(
            comedor, adjunto.formulario_tipo, adjunto.formulario_id
        )
        if formulario is not None and adjuntos_service.formulario_validado(formulario):
            return self._validado(formulario)
        tipo, formulario_id = adjunto.formulario_tipo, adjunto.formulario_id
        archivo = adjunto.archivo
        adjunto.delete()
        if archivo:
            archivo.delete(save=False)
        return self._lista_adjuntos(request, comedor, tipo, formulario_id)
