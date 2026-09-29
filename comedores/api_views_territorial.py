"""API mobile para usuarios territoriales de comedores (SISOC - Mobile).

El territorial (usuario SISOC con ``Profile.es_territorial_comedor=True``) lee
sus comedores asignados con scope por las provincias que tiene cargadas en
``TerritorialComedorProvincia``. Auth por DRF Token.
"""

import hashlib
import json

from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, mixins, serializers, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.api_serializers import (
    ComedorDetailSerializer,
    NoSaveSerializer,
    TerritorialComedorWriteSerializer,
)
from comedores.api_views_territorial_actas import (
    ActasComplementariasTerritorialMixin,
    TerritorialComedorActasFieldsMixin,
    actas_payload,
)
from comedores.api_views_territorial_adjuntos import AdjuntosTerritorialMixin
from comedores.api_views_territorial_pnud import (
    SeguimientosPnudTerritorialMixin,
    TerritorialComedorPnudFieldsMixin,
    linea_pnud,
    prestaciones_aprobadas_por_dia,
    seguimientos_pnud_payload,
)
from comedores.api_views_territorial_validaciones import (
    leer_texto,
)
from comedores.models import (
    Comedor,
    ComedorPwaCreateOperation,
)
from core.utils import format_fecha_django
from relevamientos.models import (
    ActaComplementaria,
    MotivoExcepcionSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)
from users.api_permissions import IsTerritorialComedorUser
from users.services_pwa import (
    get_territorial_comedor_provincia_ids,
    get_territorial_comedor_provincias,
)


class TerritorialUltimoRelevamientoSerializer(NoSaveSerializer):
    id = serializers.IntegerField()
    estado = serializers.CharField(allow_null=True)
    fecha_visita = serializers.DateTimeField(allow_null=True)
    territorial_user = serializers.IntegerField(
        source="territorial_user_id", allow_null=True
    )
    # Ciclo de validación del coordinador: la app muestra "Corregir y reenviar"
    # solo con "A subsanar" y lo oculta con "Validado".
    estado_validacion = serializers.CharField(allow_null=True)
    observaciones_coordinador = serializers.CharField(allow_null=True)
    fecha_revision_coordinador = serializers.DateTimeField(allow_null=True)
    # De donde salio el registro: asignado por SISOC o autoactivado en la app.
    origen = serializers.CharField()
    asignado_desde_sisoc = serializers.BooleanField()


class TerritorialComedorSerializer(
    TerritorialComedorActasFieldsMixin,
    TerritorialComedorPnudFieldsMixin,
    NoSaveSerializer,
):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    tipo = serializers.SerializerMethodField()
    programa = serializers.SerializerMethodField()
    organizacion = serializers.SerializerMethodField()
    comienzo = serializers.IntegerField(allow_null=True)
    mes_ejecucion = serializers.IntegerField(allow_null=True, read_only=True)  # #2472
    provincia = serializers.SerializerMethodField()
    municipio = serializers.SerializerMethodField()
    localidad = serializers.SerializerMethodField()
    calle = serializers.CharField(allow_null=True)
    numero = serializers.IntegerField(allow_null=True)
    entre_calle_1 = serializers.CharField(allow_null=True)
    entre_calle_2 = serializers.CharField(allow_null=True)
    barrio = serializers.CharField(allow_null=True)
    codigo_postal = serializers.IntegerField(allow_null=True)
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    estado = serializers.CharField(allow_null=True)
    relevamientos = serializers.SerializerMethodField()
    seguimientos = serializers.SerializerMethodField()

    def get_provincia(self, obj):
        return obj.provincia.nombre if obj.provincia_id else None

    def get_tipo(self, obj):
        return obj.tipocomedor.nombre if obj.tipocomedor_id else None

    def get_programa(self, obj):
        return obj.programa.nombre if obj.programa_id else None

    def get_organizacion(self, obj):
        return obj.organizacion.nombre if obj.organizacion_id else None

    def get_municipio(self, obj):
        return obj.municipio.nombre if obj.municipio_id else None

    def get_localidad(self, obj):
        return obj.localidad.nombre if obj.localidad_id else None

    def get_relevamientos(self, obj):
        relevamientos = getattr(obj, "relevamientos_territorial", None)
        if relevamientos is None:
            relevamientos = list(
                obj.relevamiento_set.all().order_by("-fecha_visita", "-id")
            )
        # `items` expone TODOS los relevamientos del comedor (no solo `ultimo`),
        # para que la PWA liste el pendiente aunque exista uno finalizado más
        # reciente. `ultimo` se mantiene por compatibilidad.
        items = TerritorialUltimoRelevamientoSerializer(relevamientos, many=True).data
        ultimo = relevamientos[0] if relevamientos else None
        return {
            "total": len(relevamientos),
            "ultimo": (
                TerritorialUltimoRelevamientoSerializer(ultimo).data if ultimo else None
            ),
            "items": items,
        }

    def get_seguimientos(self, obj):
        # TODAS las instancias del ciclo de seguimiento de cada relevamiento del
        # comedor (primer, posteriores, virtual y actas de excepcion), ordenadas
        # por `numero_orden`. `id` = PK de la instancia: es el `sisoc_id` del
        # PATCH /api/relevamiento/seguimiento.
        relevamientos = getattr(obj, "relevamientos_territorial", None)
        if relevamientos is None:
            relevamientos = list(
                obj.relevamiento_set.all().prefetch_related("seguimientos")
            )
        items = []
        for relevamiento in relevamientos:
            seguimientos = sorted(
                relevamiento.seguimientos.all(),
                key=lambda seguimiento: seguimiento.numero_orden,
            )
            for seguimiento in seguimientos:
                items.append(
                    {
                        "id": seguimiento.id,
                        "tipo": seguimiento.tipo,
                        "numero_orden": seguimiento.numero_orden,
                        "estado": seguimiento.estado,
                        "id_relevamiento": relevamiento.id,
                        "gestionar_id": seguimiento.gestionar_id,
                        "fecha": seguimiento.fecha_hora,
                        "estado_validacion": seguimiento.estado_validacion,
                        "observaciones_coordinador": (
                            seguimiento.observaciones_coordinador
                        ),
                        "fecha_revision_coordinador": (
                            seguimiento.fecha_revision_coordinador
                        ),
                        "origen": seguimiento.origen,
                        "asignado_desde_sisoc": seguimiento.asignado_desde_sisoc,
                    }
                )
        return {"total": len(items), "items": items}


@extend_schema(tags=["Territorial"])
class TerritorialComedorViewSet(
    ActasComplementariasTerritorialMixin,
    SeguimientosPnudTerritorialMixin,
    AdjuntosTerritorialMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Comedores asignados y operaciones territoriales de Gestionar.

    - ``GET /api/territorial/comedores/`` -> lista asignada al usuario.
    - ``GET /api/territorial/comedores/{id}/`` -> detalle de un comedor asignado
      o de mi zona (404 en cualquier otro caso).
    - ``POST /api/territorial/comedores/`` -> alta idempotente por ``client_uuid``.
    - ``PATCH /api/territorial/comedores/{id}/`` -> edición por provincia asignada.
    - ``POST /api/territorial/comedores/{id}/imagenes/`` -> subida de foto
      (multipart, campo ``imagen``); ``DELETE .../imagenes/{imagen_id}/`` la
      borra (ver ``AdjuntosTerritorialMixin``).
    """

    serializer_class = TerritorialComedorSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsTerritorialComedorUser]
    # DELETE solo lo atiende ``borrar_imagen``; el resto de las rutas responde 405.
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    # Un pk no numérico ("loc_abc", el id local de la app antes de sincronizar)
    # no rutea: 404 JSON en vez de un ValueError -> 500 en `filter(pk=...)`.
    lookup_value_regex = r"\d+"
    _CREATE_PAYLOAD_FIELDS = (
        "nombre",
        "tipo",
        "programa",
        "organizacion",
        "comienzo",
        "provincia",
        "municipio",
        "localidad",
        "calle",
        "numero",
        "entre_calle_1",
        "entre_calle_2",
        "barrio",
        "codigo_postal",
        "latitud",
        "longitud",
    )

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return TerritorialComedorWriteSerializer
        return TerritorialComedorSerializer

    def _response_data(self, comedor):
        return TerritorialComedorSerializer(
            comedor, context=self.get_serializer_context()
        ).data

    def _replay_is_authorized(self, operation):
        comedor = operation.comedor
        scope_ids = set(get_territorial_comedor_provincia_ids(self.request.user))
        if not comedor or comedor.provincia_id not in scope_ids:
            raise PermissionDenied(
                "La operación ya no pertenece a su alcance territorial actual."
            )
        return comedor

    @classmethod
    def _request_payload_digest(cls, payload):
        """Huella durable del request, independiente de catálogos renombrables."""
        normalized = {}
        for field in cls._CREATE_PAYLOAD_FIELDS:
            value = payload.get(field)
            normalized[field] = value.strip() if isinstance(value, str) else value
        return hashlib.sha256(
            json.dumps(
                normalized,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _idempotency_conflict_response():
        return Response(
            {
                "detail": "La clave de idempotencia ya fue usada con otro payload.",
                "code": "idempotency_payload_conflict",
            },
            status=status.HTTP_409_CONFLICT,
        )

    def create(self, request, *args, **kwargs):
        client_uuid = request.data.get("client_uuid")
        if client_uuid:
            payload_digest = self._request_payload_digest(request.data)
            operation = (
                ComedorPwaCreateOperation.objects.select_related("comedor")
                .filter(user=request.user, client_uuid=client_uuid)
                .first()
            )
            if operation is not None:
                comedor = self._replay_is_authorized(operation)
                if operation.payload_digest != payload_digest:
                    return self._idempotency_conflict_response()
                return Response(self._response_data(comedor), status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_uuid = serializer.validated_data.get("client_uuid")
        if not client_uuid:
            raise serializers.ValidationError(
                {"client_uuid": "Este campo es obligatorio para crear un comedor."}
            )

        payload_digest = self._request_payload_digest(request.data)
        try:
            with transaction.atomic():
                operation = ComedorPwaCreateOperation.objects.create(
                    user=request.user,
                    client_uuid=client_uuid,
                    payload_digest=payload_digest,
                )
                comedor = serializer.save()
                operation.comedor = comedor
                operation.save(update_fields=["comedor"])
        except IntegrityError:
            operation = (
                ComedorPwaCreateOperation.objects.select_related("comedor")
                .filter(user=request.user, client_uuid=client_uuid)
                .first()
            )
            if operation is None:
                raise
            comedor = self._replay_is_authorized(operation)
            if operation.payload_digest != payload_digest:
                return self._idempotency_conflict_response()
            return Response(self._response_data(comedor), status=status.HTTP_200_OK)

        return Response(self._response_data(comedor), status=status.HTTP_201_CREATED)

    def get_queryset(self):
        # Visibilidad "solo asignados a mí": el territorial ve los comedores que
        # tienen al menos un relevamiento asignado a él (``territorial_user``), y
        # dentro de cada comedor solo sus relevamientos asignados. Reemplaza el
        # scope por provincia (un territorial ve exactamente su trabajo asignado,
        # aunque el comedor sea de otra provincia; la asignación se hace desde el
        # backoffice).
        user = self.request.user
        # ``Relevamiento.objects`` (manager soft-delete) excluye borrados, tanto
        # en el prefetch como en la subconsulta del filtro de comedores: un
        # comedor cuyo único relevamiento asignado esté borrado no aparece con
        # ``items: []``.
        relevamientos_asignados = (
            Relevamiento.objects.filter(territorial_user=user)
            .prefetch_related("seguimientos")
            .order_by("-fecha_visita", "-id")
        )
        return (
            Comedor.objects.filter(id__in=self._comedor_ids_asignados(user))
            .select_related("provincia", "municipio", "localidad")
            .prefetch_related(
                Prefetch(
                    "relevamiento_set",
                    queryset=relevamientos_asignados,
                    to_attr="relevamientos_territorial",
                ),
                "seguimientos_pnud__tecnico",
                # Actas del listado (sin prestaciones en la respuesta): una
                # consulta por página; las prestaciones se precargan solo para
                # calcular ``sin_cargar`` sin N+1 (+1 consulta por página).
                "actas_complementarias__prestaciones",
            )
            .order_by("nombre", "id")
        )

    @staticmethod
    def _comedor_ids_asignados(user):
        """Ids de los comedores con trabajo asignado a ``user``.

        Relevamientos asignados (el manager soft-delete excluye los borrados) y,
        desde H1/H5, seguimientos PNUD y actas complementarias asignados desde
        SISOC. Se juntan primero en tres consultas por índice y el listado filtra
        ``Comedor`` por PK: un OR de subconsultas sobre ``Comedor`` recorría toda
        la tabla con tres DEPENDENT SUBQUERY por fila (EXPLAIN en MySQL).
        """
        ids = set(
            Relevamiento.objects.filter(territorial_user=user).values_list(
                "comedor_id", flat=True
            )
        )
        for modelo in (SeguimientoPnud, ActaComplementaria):
            ids.update(
                modelo.objects.filter(
                    tecnico=user, asignado_desde_sisoc=True
                ).values_list("comedor_id", flat=True)
            )
        return sorted(ids)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict):
            response.data["provincias"] = get_territorial_comedor_provincias(
                request.user
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        # Asignado a mí o de mi zona (S3), el mismo criterio que las altas: el
        # técnico crea un seguimiento sobre un comedor de su zona y después tiene
        # que poder verlo y precargarlo. Un comedor asignado a mí responde como
        # siempre (solo mis relevamientos y sus seguimientos); uno de la zona sin
        # asignación expone todos sus relevamientos y seguimientos (como el
        # listado de SISOC web, y como ya hacían `relevamiento_actual_mobile` y
        # `seguimiento_anterior_mobile`). El listado sigue siendo "asignados a mí".
        comedor = self._comedor_accesible()
        if comedor is None:
            return self._fuera_de_zona()
        data = self.get_serializer(comedor).data
        # Precarga profunda del relevamiento (mismo shape que
        # GET /api/comedores/{id}/ -> relevamiento_actual_mobile.sections), pero
        # bajo la superficie scopeada del territorial. Reutiliza el builder del
        # ComedorDetailSerializer (que se autoconsulta si no hay prefetch).
        detail_serializer = ComedorDetailSerializer(context={"request": request})
        data["relevamiento_actual_mobile"] = (
            detail_serializer.get_relevamiento_actual_mobile(comedor)
        )
        # Autocompletado en cadena (N17): snapshot del seguimiento inmediato
        # anterior al que el territorial va a completar, en el mismo formato de
        # secciones que `relevamiento_actual_mobile`.
        data["seguimiento_anterior_mobile"] = (
            detail_serializer.build_seguimiento_mobile(
                self._seguimiento_anterior(comedor)
            )
        )
        # Actas complementarias extraordinarias del comedor (N15), con su
        # estado de validación del coordinador (N16).
        data["actas_complementarias"] = actas_payload(comedor, request.user)
        # Seguimientos PNUD (N22) con respuestas y aprobados para precargarlos.
        data["seguimientos_pnud"] = seguimientos_pnud_payload(comedor, request.user)
        data["prestaciones_aprobadas"] = prestaciones_aprobadas_por_dia(comedor)
        return Response(data)

    def _seguimiento_anterior(self, comedor):
        """La instancia previa a la que está pendiente de completar.

        Se toma la pendiente (la de mayor ``numero_orden`` que todavía no está
        completa) y se devuelve la anterior a ella. Si no hay ninguna pendiente,
        se devuelve la última del ciclo, que es de donde conviene prellenar.
        """
        seguimientos = sorted(
            PrimerSeguimiento.objects.filter(
                id_relevamiento__comedor=comedor
            ).select_related(*PrimerSeguimiento.BLOQUES_ONE_TO_ONE),
            key=lambda seguimiento: seguimiento.numero_orden,
        )
        if not seguimientos:
            return None

        pendientes = [
            seguimiento
            for seguimiento in seguimientos
            if seguimiento.estado != PrimerSeguimiento.ESTADO_COMPLETO
        ]
        if not pendientes:
            return seguimientos[-1]

        orden_pendiente = pendientes[-1].numero_orden
        anteriores = [
            seguimiento
            for seguimiento in seguimientos
            if seguimiento.numero_orden < orden_pendiente
        ]
        return anteriores[-1] if anteriores else None

    # ------------------------------------------------------------------ #
    # Altas desde la app (N15 / N18)
    # ------------------------------------------------------------------ #
    # El scope de lectura es "asignado a mi", pero para CREAR hace falta poder
    # actuar sobre un comedor de la zona que todavia no tiene nada asignado. Por
    # eso estas acciones resuelven el comedor por PROVINCIA y no con
    # get_object(), que exige asignacion previa.

    def _pk_numerico(self):
        """El pk de la URL, o ``None`` si no es un entero (nunca un ValueError)."""
        pk = str(self.kwargs.get("pk", "")).strip()
        return int(pk) if pk.isdigit() else None

    def _comedor_de_mi_zona(self):
        pk = self._pk_numerico()
        if pk is None:
            return None
        provincia_ids = get_territorial_comedor_provincia_ids(self.request.user)
        return (
            Comedor.objects.filter(pk=pk, provincia_id__in=provincia_ids)
            .select_related("provincia", "municipio", "localidad")
            .first()
        )

    def _comedor_accesible(self):
        """Comedor con un relevamiento asignado a mí o, si no, de mi zona.

        Es el criterio de `firma`, extendido al detalle y a las fotos: lo que el
        técnico puede activar en su zona también lo puede ver y adjuntar. Primero
        la asignación, porque ese comedor trae el prefetch de "mis" relevamientos
        (`relevamientos_territorial`) y el detalle no cambia respecto de antes;
        el de zona no lo trae y el serializer cae a todos los del comedor.
        """
        pk = self._pk_numerico()
        if pk is None:
            return None
        comedor = self.get_queryset().filter(pk=pk).first()
        if comedor is not None:
            return comedor
        return self._comedor_de_mi_zona()

    @staticmethod
    def _conflicto_concurrente(detalle):
        """409 cuando dos altas simultáneas chocan en un UNIQUE que no es el
        ``client_uuid`` (p. ej. ``numero_orden`` del ciclo). La app lo muestra
        como error definitivo con su motivo; el técnico vuelve a enviar."""
        return Response({"detail": detalle}, status=status.HTTP_409_CONFLICT)

    def partial_update(self, request, *args, **kwargs):
        # La edición sigue la misma regla provincial que las altas N15/N18: no
        # depende de una asignación previa de relevamiento.
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()
        serializer = self.get_serializer(comedor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._response_data(comedor), status=status.HTTP_200_OK)

    @staticmethod
    def _fuera_de_zona():
        return Response(
            {"detail": "El comedor no pertenece a su zona."},
            status=status.HTTP_404_NOT_FOUND,
        )

    @staticmethod
    def _leer_client_uuid(request):
        valor = request.data.get("client_uuid") or ""
        if not isinstance(valor, str) or len(valor.strip()) > 64:
            raise ParseError("'client_uuid' debe ser texto de hasta 64 caracteres.")
        return valor.strip() or None

    @staticmethod
    def _falta_client_uuid():
        return Response(
            {"detail": "Falta 'client_uuid'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _fecha_invalida(campo):
        return Response(
            {"detail": f"'{campo}' debe tener formato dd/mm/YYYY HH:MM."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="relevamientos")
    def crear_relevamiento(  # pylint: disable=too-many-return-statements
        self, request, pk=None
    ):
        """Autoactivacion de un relevamiento sobre un comedor de la zona."""
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()

        client_uuid = self._leer_client_uuid(request)
        if not client_uuid:
            return self._falta_client_uuid()

        # Idempotencia: el mismo uuid devuelve el registro ya creado. Se busca con
        # `all_objects` porque el indice UNIQUE de client_uuid incluye a los
        # soft-deleted: si SISOC borro logicamente el relevamiento y la cola
        # offline reintenta el mismo uuid, con `objects` no lo encontrariamos,
        # el INSERT chocaria contra el UNIQUE y el reintento daria 500 para siempre.
        existente = Relevamiento.all_objects.filter(client_uuid=client_uuid).first()
        if existente is not None:
            return Response(
                self._serialize_relevamiento_creado(existente),
                status=status.HTTP_200_OK,
            )

        # `validate_relevamientos_activos` no permite dos activos en el mismo
        # comedor: en vez de un 500 opaco se devuelve el id del activo para que
        # la app lo complete en lugar de crear otro.
        activo = Relevamiento.objects.filter(
            comedor=comedor, estado__in=["Pendiente", "Visita pendiente"]
        ).first()
        if activo is not None:
            return Response(
                {
                    "detail": "El comedor ya tiene un relevamiento activo.",
                    "relevamiento_id": activo.id,
                },
                status=status.HTTP_409_CONFLICT,
            )

        relevamiento = Relevamiento(
            comedor=comedor,
            estado="Visita pendiente",
            territorial_user=request.user,
            origen=Relevamiento.ORIGEN_APP,
            asignado_desde_sisoc=False,
            client_uuid=client_uuid,
        )
        fecha_visita = leer_texto(request.data, "fecha_visita")
        if fecha_visita:
            try:
                relevamiento.fecha_visita = format_fecha_django(fecha_visita)
            except (ValueError, TypeError):
                return self._fecha_invalida("fecha_visita")
        try:
            with transaction.atomic():
                relevamiento.save()
        except IntegrityError:
            # Carrera con otro reintento del mismo uuid (o uuid de uno borrado).
            existente = Relevamiento.all_objects.filter(client_uuid=client_uuid).first()
            if existente is None:
                # Otro UNIQUE (comedor + fecha_visita) con una alta simultánea.
                return self._conflicto_concurrente(
                    "El comedor ya tiene un relevamiento con esa fecha de visita."
                )
            return Response(
                self._serialize_relevamiento_creado(existente),
                status=status.HTTP_200_OK,
            )

        return Response(
            self._serialize_relevamiento_creado(relevamiento),
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _serialize_relevamiento_creado(relevamiento):
        return {
            "id": relevamiento.id,
            "comedor": relevamiento.comedor_id,
            "estado": relevamiento.estado,
            "fecha_visita": relevamiento.fecha_visita,
            "territorial_user": relevamiento.territorial_user_id,
            "origen": relevamiento.origen,
            "asignado_desde_sisoc": relevamiento.asignado_desde_sisoc,
            "client_uuid": relevamiento.client_uuid,
        }

    @action(detail=True, methods=["post"], url_path="seguimientos")
    def crear_seguimiento(  # pylint: disable=too-many-return-statements
        self, request, pk=None
    ):
        """Autoactivacion de una instancia del ciclo de seguimiento."""
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()

        client_uuid = self._leer_client_uuid(request)
        if not client_uuid:
            return self._falta_client_uuid()

        existente = PrimerSeguimiento.objects.filter(client_uuid=client_uuid).first()
        if existente is not None:
            return Response(
                self._serialize_seguimiento_creado(existente),
                status=status.HTTP_200_OK,
            )

        tipo = leer_texto(request.data, "tipo") or ""
        if tipo not in PrimerSeguimiento.TIPOS_CREABLES_DESDE_APP:
            return Response(
                {
                    "detail": (
                        "'tipo' invalido. Validos: "
                        f"{list(PrimerSeguimiento.TIPOS_CREABLES_DESDE_APP)}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # El ciclo cuelga del relevamiento ancla del comedor.
        relevamiento = (
            Relevamiento.objects.filter(comedor=comedor)
            .order_by("-fecha_visita", "-id")
            .first()
        )
        if relevamiento is None:
            return Response(
                {
                    "detail": (
                        "El comedor no tiene un relevamiento del cual colgar el "
                        "seguimiento."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        ultimo_orden = (
            PrimerSeguimiento.objects.filter(id_relevamiento=relevamiento)
            .order_by("-numero_orden")
            .values_list("numero_orden", flat=True)
            .first()
        ) or 0

        seguimiento = PrimerSeguimiento(
            id_relevamiento=relevamiento,
            tipo=tipo,
            numero_orden=ultimo_orden + 1,
            estado=PrimerSeguimiento.ESTADO_ASIGNADO,
            origen=PrimerSeguimiento.ORIGEN_APP,
            asignado_desde_sisoc=False,
            client_uuid=client_uuid,
        )
        try:
            with transaction.atomic():
                seguimiento.save()
        except IntegrityError:
            existente = PrimerSeguimiento.objects.filter(
                client_uuid=client_uuid
            ).first()
            if existente is None:
                # Dos activaciones con uuids distintos calcularon el mismo
                # `numero_orden` (unique_together con el relevamiento): la app
                # reintenta y toma el siguiente.
                return self._conflicto_concurrente(
                    "Otra activación de seguimiento se registró al mismo tiempo "
                    "sobre este comedor."
                )
            return Response(
                self._serialize_seguimiento_creado(existente),
                status=status.HTTP_200_OK,
            )

        return Response(
            self._serialize_seguimiento_creado(seguimiento),
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _serialize_seguimiento_creado(seguimiento):
        return {
            "id": seguimiento.id,
            "id_relevamiento": seguimiento.id_relevamiento_id,
            "tipo": seguimiento.tipo,
            "numero_orden": seguimiento.numero_orden,
            "estado": seguimiento.estado,
            "origen": seguimiento.origen,
            "asignado_desde_sisoc": seguimiento.asignado_desde_sisoc,
            "client_uuid": seguimiento.client_uuid,
        }


@extend_schema(tags=["Territorial"])
class MotivosExcepcionSeguimientoView(APIView):
    """Catalogo de motivos del acta de excepcion de seguimiento (§18.3).

    Es un catalogo cerrado: el PATCH rechaza un motivo que no este en esta
    lista, asi que la app valida en cliente con estos mismos valores.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsTerritorialComedorUser]

    def get(self, request):
        items = list(
            MotivoExcepcionSeguimiento.objects.order_by("nombre").values("id", "nombre")
        )
        return Response({"items": items})


class TerritorialComedorZonaSerializer(NoSaveSerializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    provincia = serializers.SerializerMethodField()
    municipio = serializers.SerializerMethodField()
    localidad = serializers.SerializerMethodField()
    calle = serializers.CharField(allow_null=True)
    numero = serializers.IntegerField(allow_null=True)
    barrio = serializers.CharField(allow_null=True)
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    estado = serializers.CharField(allow_null=True)
    # Programa y línea PNUD (N22), mismos valores que el listado asignado: la
    # app elige el flujo (PAC / PNUD) de un comedor de su zona sin asignación.
    programa = serializers.SerializerMethodField()
    programa_id = serializers.IntegerField(allow_null=True, read_only=True)
    linea_pnud = serializers.SerializerMethodField()

    def get_provincia(self, obj):
        return obj.provincia.nombre if obj.provincia_id else None

    def get_municipio(self, obj):
        return obj.municipio.nombre if obj.municipio_id else None

    def get_localidad(self, obj):
        return obj.localidad.nombre if obj.localidad_id else None

    def get_programa(self, obj):
        return obj.programa.nombre if obj.programa_id else None

    def get_linea_pnud(self, obj):
        return linea_pnud(obj)


@extend_schema(tags=["Territorial"])
class TerritorialComedorZonaListView(generics.ListAPIView):
    """``GET /api/territorial/comedores-zona/`` - comedores de MI ZONA.

    Devuelve los comedores de las provincias del territorial, para que pueda
    activar trabajo sin esperar asignacion (N18). Es un endpoint aparte y con
    serializer liviano a proposito: `/territorial/comedores/` sigue siendo
    "asignados a mi", y meter aca los relevamientos/seguimientos reproduciria la
    lentitud que tenia el listado por provincia.
    """

    serializer_class = TerritorialComedorZonaSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsTerritorialComedorUser]
    # ``?search=`` por nombre / localidad / municipio: con miles de comedores por
    # provincia el filtro solo sobre lo ya paginado en la app es insuficiente.
    filter_backends = [filters.SearchFilter]
    search_fields = ["nombre", "localidad__nombre", "municipio__nombre"]

    def get_queryset(self):
        provincia_ids = get_territorial_comedor_provincia_ids(self.request.user)
        if not provincia_ids:
            return Comedor.objects.none()
        return (
            Comedor.objects.filter(provincia_id__in=provincia_ids)
            .select_related("provincia", "municipio", "localidad", "programa")
            .order_by("nombre", "id")
        )
