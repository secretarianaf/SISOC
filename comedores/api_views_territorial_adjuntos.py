"""Fotos y firmas de la API territorial (mixin de ``TerritorialComedorViewSet``).

- ``POST   /api/territorial/comedores/{id}/imagenes/`` -> sube una foto.
- ``DELETE /api/territorial/comedores/{id}/imagenes/{imagen_id}/`` -> borra una
  foto subida desde la app.
- ``POST   /api/territorial/comedores/{id}/firma/`` -> sube una firma y devuelve
  su URL.

Las tres resuelven el comedor con ``_comedor_accesible()`` (asignado a mí o de
mi zona), el mismo criterio que las altas: si el técnico pudo activar el
seguimiento sobre un comedor de su zona, tiene que poder subir sus fotos y su
firma; antes ``imagenes`` exigía asignación previa y el seguimiento quedaba
trabado con un 404 definitivo.
"""

import hashlib

from django.core.files.storage import default_storage
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from comedores.api_views_territorial_validaciones import extension_de_imagen
from comedores.models import ImagenComedor
from comedores.services.comedor_service import ComedorService
from relevamientos.models import PrimerSeguimiento, Relevamiento

MAX_IMAGENES_COMEDOR = 15
MAX_FIRMA_FILE_SIZE = 3 * 1024 * 1024  # 3 MB


class AdjuntosTerritorialMixin:
    """Usa del viewset: ``_comedor_accesible``, ``_fuera_de_zona`` y
    ``_leer_client_uuid``."""

    @staticmethod
    def _serialize_imagenes(imagenes, request):
        # `client_uuid` viaja para que la app empareje cada foto con la suya
        # (antes lo hacía por "la última URL", que falla con reintentos).
        return [
            {
                "id": imagen.id,
                "relevamiento": imagen.relevamiento_id,
                "seguimiento": imagen.seguimiento_id,
                "client_uuid": imagen.client_uuid,
                "url": (
                    request.build_absolute_uri(imagen.imagen.url)
                    if imagen.imagen
                    else None
                ),
            }
            for imagen in imagenes
        ]

    @staticmethod
    def _resolver_destino_foto(request, comedor):
        """A que cuelga la foto: relevamiento (`sisoc_id`) o seguimiento
        (`seguimiento_id`), excluyentes. Devuelve (relevamiento_id,
        seguimiento_id, error_response)."""
        relevamiento_id = (request.data.get("sisoc_id") or "").strip() or None
        seguimiento_id = (request.data.get("seguimiento_id") or "").strip() or None
        if relevamiento_id is not None and seguimiento_id is not None:
            return (
                None,
                None,
                Response(
                    {
                        "detail": (
                            "Informe 'sisoc_id' (relevamiento) o 'seguimiento_id', "
                            "no ambos."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )
        if relevamiento_id is not None and (
            not relevamiento_id.isdigit()
            or not Relevamiento.objects.filter(
                id=relevamiento_id, comedor=comedor
            ).exists()
        ):
            return (
                None,
                None,
                Response(
                    {
                        "detail": "El sisoc_id no corresponde a un relevamiento de este comedor."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )
        if seguimiento_id is not None and (
            not seguimiento_id.isdigit()
            or not PrimerSeguimiento.objects.filter(
                id=seguimiento_id, id_relevamiento__comedor=comedor
            ).exists()
        ):
            return (
                None,
                None,
                Response(
                    {
                        "detail": (
                            "El seguimiento_id no corresponde a un seguimiento "
                            "de este comedor."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )
        return relevamiento_id, seguimiento_id, None

    @staticmethod
    def _scope_fotos(comedor, relevamiento_id, seguimiento_id):
        """Fotos sobre las que se cuenta el tope de 15 y se responde."""
        scope = comedor.imagenes.all()
        if relevamiento_id is not None:
            return scope.filter(relevamiento_id=relevamiento_id)
        if seguimiento_id is not None:
            return scope.filter(seguimiento_id=seguimiento_id)
        return scope

    @action(
        detail=True,
        methods=["post"],
        url_path="imagenes",
        parser_classes=[MultiPartParser, FormParser],
    )
    def imagenes(  # pylint: disable=too-many-return-statements,too-many-branches
        self, request, pk=None
    ):
        # Asignado a mí o de mi zona (S1): el seguimiento autoactivado sobre un
        # comedor de la zona cuelga de un relevamiento asignado a otro técnico.
        # Reutiliza el modelo ImagenComedor (origen="mobile").
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        imagen = request.FILES.get("imagen")
        if not imagen:
            return Response(
                {"detail": "Debe adjuntar una imagen en el campo 'imagen'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relevamiento_id, seguimiento_id, error = self._resolver_destino_foto(
            request, comedor
        )
        if error is not None:
            return error
        scope = self._scope_fotos(comedor, relevamiento_id, seguimiento_id)

        # Idempotencia offline: si la PWA reintenta con el mismo client_uuid, no se
        # duplica; se devuelve el estado actual del scope.
        client_uuid = self._leer_client_uuid(request)
        if client_uuid and comedor.imagenes.filter(client_uuid=client_uuid).exists():
            return Response(
                {"imagenes": self._serialize_imagenes(scope, request)},
                status=status.HTTP_200_OK,
            )
        if scope.count() >= MAX_IMAGENES_COMEDOR:
            destino = "el espacio"
            if relevamiento_id:
                destino = "este relevamiento"
            elif seguimiento_id:
                destino = "este seguimiento"
            return Response(
                {
                    "detail": (
                        f"{destino} ya tiene el máximo de {MAX_IMAGENES_COMEDOR} "
                        "fotos. Borre alguna antes de subir otra."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        creado = ComedorService.create_imagenes(imagen, comedor.pk, origen="mobile")
        if isinstance(creado, dict):
            return Response(creado, status=status.HTTP_400_BAD_REQUEST)
        # Quién la subió: solo él puede borrarla (S2).
        creado.subido_por = request.user
        update_fields = ["subido_por"]
        if relevamiento_id is not None:
            creado.relevamiento_id = relevamiento_id
            update_fields.append("relevamiento")
        if seguimiento_id is not None:
            creado.seguimiento_id = seguimiento_id
            update_fields.append("seguimiento")
        if client_uuid:
            creado.client_uuid = client_uuid
            update_fields.append("client_uuid")
        if update_fields:
            try:
                creado.save(update_fields=update_fields)
            except IntegrityError:
                # Carrera con otro reintento del mismo client_uuid: descarto el
                # duplicado recién creado y devuelvo lo que ya existe.
                creado.delete()
        scope = self._scope_fotos(comedor, relevamiento_id, seguimiento_id)
        return Response(
            {"imagenes": self._serialize_imagenes(scope, request)},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"imagenes/(?P<imagen_id>[0-9]+)",
        url_name="imagen-borrar",
    )
    def borrar_imagen(self, request, pk=None, imagen_id=None):
        """Borra una foto que el propio técnico subió desde la app (S2).

        El tope de 15 cuenta las fotos ya subidas, así que "Corregir y
        reenviar" con fotos reemplazadas se trababa en la 16. La app borra las
        que reemplaza y sube las nuevas.

        Respuestas:
        - 200 ``{"imagenes": [...]}``: borrada; el scope de la foto, como el POST.
        - 404: la foto no existe en este comedor o no es ``origen="mobile"`` (las
          cargadas en SISOC web no se tocan). **Idempotente para la app**: un
          reintento del mismo DELETE cae acá y la app lo toma como éxito ("ya
          no existe").
        - 403: la subió otro técnico (``subido_por``; ver ``_foto_es_del_tecnico``
          para las fotos anteriores a ese campo).
        - 409: el relevamiento o seguimiento de la foto ya está Validado.
        """
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        imagen = (
            comedor.imagenes.filter(pk=imagen_id, origen=ImagenComedor.ORIGEN_MOBILE)
            .select_related(
                "relevamiento", "seguimiento", "seguimiento__id_relevamiento"
            )
            .first()
        )
        if imagen is None:
            return Response(
                {
                    "detail": (
                        "La foto no existe en este comedor o no se subió desde "
                        "la app."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        if not self._foto_es_del_tecnico(imagen, request.user):
            return Response(
                {"detail": "La foto la subió otro técnico y no se puede borrar."},
                status=status.HTTP_403_FORBIDDEN,
            )
        registro = imagen.relevamiento or imagen.seguimiento
        if registro is not None and getattr(registro, "esta_validado", False):
            return Response(
                {
                    "detail": (
                        "El registro está validado por el coordinador y sus fotos "
                        "no admiten cambios."
                    ),
                    "estado_validacion": registro.estado_validacion,
                },
                status=status.HTTP_409_CONFLICT,
            )
        relevamiento_id = imagen.relevamiento_id
        seguimiento_id = imagen.seguimiento_id
        archivo = imagen.imagen
        imagen.delete()
        if archivo:
            archivo.delete(save=False)
        scope = self._scope_fotos(comedor, relevamiento_id, seguimiento_id)
        return Response(
            {"imagenes": self._serialize_imagenes(scope, request)},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _foto_es_del_tecnico(imagen, usuario):
        """Propia si ``subido_por`` es este usuario.

        Las fotos anteriores al campo no lo tienen: en ese caso vale que el
        relevamiento de la foto (o el ancla de su seguimiento, o alguno del
        comedor si es una foto del espacio) esté asignado al técnico, que es la
        condición con la que se podían subir antes de este cambio.
        """
        if imagen.subido_por_id is not None:
            return imagen.subido_por_id == usuario.id
        if imagen.relevamiento_id is not None:
            return imagen.relevamiento.territorial_user_id == usuario.id
        if imagen.seguimiento_id is not None:
            return imagen.seguimiento.id_relevamiento.territorial_user_id == usuario.id
        return imagen.comedor.relevamiento_set.filter(territorial_user=usuario).exists()

    @staticmethod
    def _nombre_firma_idempotente(comedor, client_uuid, extension):
        # El nombre sale del client_uuid: el mismo reintento cae en el mismo
        # archivo y no deja huérfanos. Se hashea para no llevar al storage
        # caracteres arbitrarios del cliente.
        huella = hashlib.sha256(client_uuid.encode("utf-8")).hexdigest()[:32]
        return f"firmas/{comedor.id}/{huella}.{extension}"

    @action(
        detail=True,
        methods=["post"],
        url_path="firma",
        parser_classes=[MultiPartParser, FormParser],
    )
    def firma(self, request, pk=None):  # pylint: disable=too-many-return-statements
        # Sube la firma como imagen y devuelve la URL, para guardarla como string
        # en excepcion.firma (relevamiento) o cierre.firma_* (seguimiento) vía el
        # PATCH. No se mezcla con las fotos del comedor (ImagenComedor).
        # Asignado a mí (como antes) o de mi zona (altas N15/N18/N22: actas y
        # seguimientos PNUD se firman sobre comedores sin asignacion previa).
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        archivo = request.FILES.get("firma")
        if not archivo:
            return Response(
                {"detail": "Debe adjuntar la firma en el campo 'firma'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content_type = getattr(archivo, "content_type", "") or ""
        if not content_type.startswith("image/"):
            return Response(
                {"detail": "La firma debe ser una imagen."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if archivo.size > MAX_FIRMA_FILE_SIZE:
            return Response(
                {"detail": "La firma excede el tamaño máximo de 3 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # El contenido manda, no el Content-Type: un SVG o un texto con
        # ``image/png`` no son una firma.
        extension = extension_de_imagen(archivo)
        if extension is None:
            return Response(
                {
                    "detail": "La firma debe ser una imagen PNG, JPEG, WEBP o GIF válida."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        client_uuid = self._leer_client_uuid(request)
        if client_uuid:
            # Idempotente como `imagenes`: el reintento offline del mismo uuid
            # devuelve la firma ya guardada en vez de subir otra copia.
            nombre = self._nombre_firma_idempotente(comedor, client_uuid, extension)
            if default_storage.exists(nombre):
                return Response(
                    {"url": request.build_absolute_uri(default_storage.url(nombre))},
                    status=status.HTTP_200_OK,
                )
            path = default_storage.save(nombre, archivo)
        else:
            path = default_storage.save(f"firmas/{comedor.id}/{archivo.name}", archivo)
        url = request.build_absolute_uri(default_storage.url(path))
        return Response({"url": url}, status=status.HTTP_201_CREATED)
