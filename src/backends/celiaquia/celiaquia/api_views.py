"""API REST de Celiaquia.

Dos reglas que ordenan todo este modulo:

1. **El alcance se aplica en `get_queryset()`**, siempre, reusando
   `celiaquia.scope`. Las pantallas filtraban por rol y territorio; un endpoint
   que devuelva el queryset pelado expone expedientes de otras provincias.
2. **Las escrituras delegan en `celiaquia/services/`.** Los expedientes tienen
   maquina de estados, historial y cupos: persistir desde el serializer saltea
   todo eso. Por eso los ViewSets son de lectura y las transiciones son
   `@action` que llaman al service.

Ademas, cada ViewSet exige el permiso de modulo que piden las pantallas
(`celiaquia.api_permissions`): estar logueado no alcanza.
"""

# Un ViewSet por recurso con sus transiciones como `@action`: el tamano del
# modulo y de `ExpedienteViewSet` sigue a los 70 endpoints que expone.
# pylint: disable=too-many-lines,too-many-public-methods

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from celiaquia.api_permissions import (
    TieneAccesoCupos,
    TieneAccesoExpedientes,
    TieneAccesoReporte,
)
from celiaquia.api_serializers import (
    AccionResultadoSerializer,
    ArchivoSerializer,
    AsignacionTecnicoSerializer,
    AsignarTecnicoSerializer,
    ConfigurarCupoSerializer,
    CrearLegajosSerializer,
    CrearPagoSerializer,
    CupoMovimientoSerializer,
    DocumentoLegajoSerializer,
    EstadoExpedienteSerializer,
    EstadoLegajoSerializer,
    ExpedienteCreateSerializer,
    ExpedienteEstadoHistorialSerializer,
    ExpedienteSerializer,
    ExpedienteUpdateSerializer,
    LegajoSerializer,
    MotivoSerializer,
    OrganismoSerializer,
    PagoExpedienteSerializer,
    PagoNominaSerializer,
    ActualizarRegistroErroneoSerializer,
    GuardarValidacionRenaperSerializer,
    FilaCupoProvinciaSerializer,
    ImportacionResultadoSerializer,
    ProcesamientoResultadoSerializer,
    ProcesarExpedienteRespuestaSerializer,
    CatalogosRegistroErroneoSerializer,
    LocalidadLookupSerializer,
    OpcionCatalogoSerializer,
    ComentarioLegajoSerializer,
    CrearComentarioTecnicoSerializer,
    MotivoPreviewSerializer,
    ResponderSubsanacionSerializer,
    PreviewExcelResultadoSerializer,
    ReporteSerializer,
    ReprocesoResultadoSerializer,
    PreviewExcelSerializer,
    ProvinciaCupoSerializer,
    RegistroErroneoSerializer,
    RevisarLegajoSerializer,
    SolicitarSubsanacionSerializer,
    SubirArchivoLegajoSerializer,
    SubsanacionSerializer,
    TipoCruceSerializer,
    TipoDocumentoSerializer,
    UsuarioResumenSerializer,
)
from celiaquia.models import (
    CupoMovimiento,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    Organismo,
    PagoExpediente,
    PagoNomina,
    ProvinciaCupo,
    RegistroErroneo,
    Subsanacion,
    TipoCruce,
    TipoDocumento,
)
from celiaquia.scope import (
    is_admin,
    is_coordinador,
    is_provincial,
    is_tecnico,
    scope_expedientes,
    tecnicos_asignables,
)
from celiaquia.permissions import (
    can_confirm_subsanacion,
    can_edit_legajo_files,
    can_review_legajo,
    documentos_legajo_bloqueados,
    exigir_acceso_nacion_a_comentarios,
)

# Varios paquetes de `celiaquia/services/` se reemplazan por su `impl.py` en
# `sys.modules` (ver su `__init__.py`). pylint analiza el `__init__` y, si no
# reexporta el nombre, no lo ve aunque en ejecucion exista.
# pylint: disable=no-name-in-module
from celiaquia.services.asignacion_service import AsignacionService
from celiaquia.services.comentarios_tecnicos_service import ComentariosTecnicosService
from celiaquia.services.cruce_service import CruceService
from celiaquia.services.cupo_service import CupoService
from celiaquia.services.documentos_service import DocumentosService
from celiaquia.services.expediente_service import ExpedienteService
from celiaquia.services.familia_service import FamiliaService
from celiaquia.services.importacion_service import ImportacionService
from celiaquia.services.legajo_service import LegajoService
from celiaquia.services.padron_final_service import PadronFinalService
from celiaquia.services.pago_service import PagoService
from celiaquia.services.reporte_service import build_report_payload
from celiaquia.services.revision_service import RevisionService
from celiaquia.services.subsanacion_service import SubsanacionService
from celiaquia.services import registros_erroneos_service, validacion_renaper_service

# pylint: enable=no-name-in-module
from core.models import Localidad, Municipio, Nacionalidad, Provincia, Sexo


def _error_renaper(payload: dict, estado_http: int) -> Exception:
    """El payload de RENAPER trae el motivo en `error`; se respeta el status."""

    detalle = payload.get("error") or "No se pudo validar con RENAPER."
    if estado_http == 403:
        return PermissionDenied(detalle)
    return ValidationError({"detail": [detalle]})


def _traducir_error(exc: Exception) -> ValidationError:
    """Los services levantan ValidationError de Django; la API responde 400."""

    mensajes = getattr(exc, "messages", None) or [str(exc)]
    return ValidationError({"detail": mensajes})


EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _respuesta_excel(contenido: bytes, nombre: str) -> HttpResponse:
    """Descarga de un xlsx generado por un service."""

    respuesta = HttpResponse(contenido, content_type=EXCEL_CONTENT_TYPE)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def _para_listar_legajos(queryset):
    """Lo que `LegajoSerializer` lee de cada fila, en la misma consulta.

    Sin esto, cada legajo de un listado de cupo (una provincia entera) cuesta
    dos consultas mas: `estado` y `ciudadano`.
    """

    return queryset.select_related("estado", "ciudadano")


PERMISOS_EXPEDIENTES = [IsAuthenticated, TieneAccesoExpedientes]
PERMISOS_CUPOS = [IsAuthenticated, TieneAccesoCupos]


class CeliaquiaCatalogoViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogos: los lee cualquier usuario autenticado del modulo."""

    permission_classes = PERMISOS_EXPEDIENTES
    pagination_class = None


class EstadoExpedienteViewSet(CeliaquiaCatalogoViewSet):
    queryset = EstadoExpediente.objects.all().order_by("nombre")
    serializer_class = EstadoExpedienteSerializer


class EstadoLegajoViewSet(CeliaquiaCatalogoViewSet):
    queryset = EstadoLegajo.objects.all().order_by("nombre")
    serializer_class = EstadoLegajoSerializer


class OrganismoViewSet(CeliaquiaCatalogoViewSet):
    queryset = Organismo.objects.all().order_by("nombre")
    serializer_class = OrganismoSerializer


class TipoCruceViewSet(CeliaquiaCatalogoViewSet):
    queryset = TipoCruce.objects.all().order_by("nombre")
    serializer_class = TipoCruceSerializer


class TipoDocumentoViewSet(CeliaquiaCatalogoViewSet):
    serializer_class = TipoDocumentoSerializer
    queryset = TipoDocumento.objects.none()

    def get_queryset(self):
        return DocumentosService.obtener_tipos_documento_activos()


class ExpedienteViewSet(viewsets.ReadOnlyModelViewSet):
    """Expedientes visibles para el usuario, con sus transiciones de estado."""

    permission_classes = PERMISOS_EXPEDIENTES
    serializer_class = ExpedienteSerializer
    # Solo para que el schema derive el tipo del pk: get_queryset() manda.
    queryset = Expediente.objects.none()

    def get_queryset(self):
        queryset = (
            Expediente.objects.select_related(
                "estado", "usuario_provincia__profile__provincia"
            )
            .annotate(legajos_total_count=Count("expediente_ciudadanos", distinct=True))
            .order_by("-fecha_creacion", "pk")
        )
        queryset = scope_expedientes(queryset, self.request.user)

        estado = (self.request.query_params.get("estado") or "").strip()
        if estado:
            queryset = queryset.filter(estado__nombre__iexact=estado)
        numero = (self.request.query_params.get("numero_expediente") or "").strip()
        if numero:
            queryset = queryset.filter(numero_expediente__icontains=numero)
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter("estado", str, description="Nombre exacto del estado."),
            OpenApiParameter(
                "numero_expediente", str, description="Coincidencia parcial."
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # --- Sub-recursos ------------------------------------------------------

    @extend_schema(responses=LegajoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def legajos(self, request, pk=None):
        """Legajos del expediente (`ExpedienteCiudadano`)."""

        expediente = self.get_object()
        queryset = LegajoService.listar_legajos(expediente)
        pagina = self.paginate_queryset(queryset)
        serializer = LegajoSerializer(
            pagina if pagina is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(responses=ExpedienteEstadoHistorialSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="historial-estados")
    def historial_estados(self, request, pk=None):
        expediente = self.get_object()
        queryset = expediente.historial.select_related(
            "estado_nuevo", "estado_anterior", "usuario"
        ).order_by("-fecha")
        return Response(
            ExpedienteEstadoHistorialSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(responses=AsignacionTecnicoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def asignaciones(self, request, pk=None):
        expediente = self.get_object()
        queryset = AsignacionService.obtener_historial_asignaciones(expediente)
        return Response(
            AsignacionTecnicoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(responses=LegajoSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="fuera-de-cupo")
    def fuera_de_cupo(self, request, pk=None):
        expediente = self.get_object()
        queryset = _para_listar_legajos(
            CupoService.lista_fuera_de_cupo_por_expediente(expediente.pk)
        )
        return Response(
            LegajoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    # --- Transiciones (delegan en el service) ------------------------------

    def _exigir_gestion(self, expediente=None):
        """Procesar/importar/confirmar son de la provincia duena, o admin.

        Mismo alcance que las vistas Django (`ProcesarExpedienteView`,
        `ExpedienteImportView`, `ExpedienteConfirmView`): admin opera cualquiera,
        la provincia lo que su territorio alcanza (ya lo filtra `get_object`) y
        cualquier otro rol, incluida coordinacion, solo los que creo.

        Sin `expediente` (alta o previsualizacion) alcanza con el rol.
        """

        user = self.request.user
        if not (is_admin(user) or is_provincial(user) or is_coordinador(user)):
            raise PermissionDenied("No tiene permisos para operar el expediente.")
        if expediente is None or is_admin(user) or is_provincial(user):
            return
        if expediente.usuario_provincia_id != user.pk:
            raise PermissionDenied("Solo la provincia duena opera este expediente.")

    @extend_schema(request=None, responses=ImportacionResultadoSerializer)
    @action(detail=True, methods=["post"])
    def importar(self, request, pk=None):
        """Importa los legajos del Excel masivo ya cargado en el expediente.

        La pantalla Django devuelve los totales por `messages`; aca se devuelven
        como JSON para que el front pueda mostrar validos, errores y
        advertencias sin parsear texto.
        """

        expediente = self.get_object()
        self._exigir_gestion(expediente)
        try:
            resultado = ImportacionService.importar_legajos_desde_excel(
                expediente, expediente.excel_masivo, request.user
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(ImportacionResultadoSerializer(resultado).data)

    @extend_schema(request=None, responses=ProcesarExpedienteRespuestaSerializer)
    @action(detail=True, methods=["post"])
    def procesar(self, request, pk=None):
        """Procesa el Excel masivo y crea los legajos."""

        expediente = self.get_object()
        self._exigir_gestion(expediente)
        try:
            resultado = ExpedienteService.procesar_expediente(expediente, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        expediente.refresh_from_db()
        # El resumen incluye las filas excluidas por duplicado: son validaciones
        # que corrieron y que el front tiene que poder mostrar.
        return Response(
            {
                "detail": "Expediente procesado.",
                "expediente": ExpedienteSerializer(
                    expediente, context=self.get_serializer_context()
                ).data,
                "resultado": ProcesamientoResultadoSerializer(resultado).data,
            }
        )

    @extend_schema(request=None, responses=AccionResultadoSerializer)
    @action(detail=True, methods=["post"], url_path="confirmar-envio")
    def confirmar_envio(self, request, pk=None):
        """Cierra la carga provincial y envia el expediente a revision."""

        expediente = self.get_object()
        self._exigir_gestion(expediente)
        try:
            ExpedienteService.exigir_sin_registros_erroneos(expediente)
            ExpedienteService.confirmar_envio(expediente, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        expediente.refresh_from_db()
        return Response(
            {
                "detail": "Envio confirmado.",
                "expediente": ExpedienteSerializer(
                    expediente, context=self.get_serializer_context()
                ).data,
            }
        )

    @extend_schema(
        request=AsignarTecnicoSerializer, responses=AccionResultadoSerializer
    )
    @action(detail=True, methods=["post"], url_path="asignar-tecnico")
    def asignar_tecnico(self, request, pk=None):
        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("Solo coordinacion puede asignar tecnicos.")
        expediente = self.get_object()
        entrada = AsignarTecnicoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        # Los mismos que ofrece `tecnicos/`: no se asigna a cualquier usuario.
        tecnico = get_object_or_404(
            tecnicos_asignables(), pk=entrada.validated_data["tecnico_id"]
        )
        try:
            ExpedienteService.asignar_tecnico(expediente, tecnico, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response({"detail": "Tecnico asignado."})

    # --- Escrituras --------------------------------------------------------

    @extend_schema(request=ExpedienteCreateSerializer, responses=ExpedienteSerializer)
    def create(self, request, *args, **kwargs):
        """Alta del expediente, opcionalmente con su Excel masivo.

        El alta la hace la provincia: el expediente queda a nombre del usuario
        que lo crea y es lo que despues determina su alcance.
        """

        self._exigir_gestion()
        entrada = ExpedienteCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        try:
            expediente = ExpedienteService.create_expediente(
                request.user,
                {
                    "numero_expediente": datos.get("numero_expediente") or None,
                    "observaciones": datos.get("observaciones", ""),
                },
                datos.get("excel_masivo"),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(
            ExpedienteSerializer(
                expediente, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ExpedienteUpdateSerializer, responses=ExpedienteSerializer)
    def partial_update(self, request, *args, **kwargs):
        """Edicion de metadatos. Solo mientras el expediente esta en CREADO."""

        expediente = self.get_object()
        self._exigir_gestion(expediente)
        if expediente.estado.nombre != "CREADO":
            raise ValidationError(
                {"detail": ["Solo se pueden editar expedientes en estado CREADO."]}
            )
        entrada = ExpedienteUpdateSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        for campo, valor in entrada.validated_data.items():
            setattr(expediente, campo, valor)
        expediente.save()
        return Response(
            ExpedienteSerializer(expediente, context=self.get_serializer_context()).data
        )

    def destroy(self, request, *args, **kwargs):
        """Baja del expediente. Reservada a coordinacion y admin."""

        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("Solo coordinacion puede eliminar expedientes.")
        expediente = self.get_object()
        expediente.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={
            (
                200,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ): bytes
        }
    )
    @action(detail=False, methods=["get"], url_path="plantilla-excel")
    def plantilla_excel(self, request):
        """Excel vacio con las columnas que espera la importacion masiva."""

        contenido = ImportacionService.generar_plantilla_excel()
        respuesta = HttpResponse(
            contenido,
            content_type=(
                "application/vnd.openxmlformats-officedocument" ".spreadsheetml.sheet"
            ),
        )
        respuesta["Content-Disposition"] = (
            'attachment; filename="plantilla_expediente.xlsx"'
        )
        return respuesta

    @extend_schema(responses=UsuarioResumenSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="tecnicos")
    def tecnicos(self, request):
        """Tecnicos que se pueden asignar a un expediente.

        Solo coordinacion y admin asignan, asi que solo ellos ven la lista: un
        provincial no tiene por que conocer la nomina de tecnicos.
        """

        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("Solo coordinación asigna técnicos.")
        queryset = tecnicos_asignables().order_by("last_name", "first_name")
        return Response(UsuarioResumenSerializer(queryset, many=True).data)

    @extend_schema(responses=CatalogosRegistroErroneoSerializer)
    @action(detail=False, methods=["get"], url_path="catalogos")
    def catalogos(self, request):
        """Sexos y nacionalidades para el formulario de corrección.

        Son chicos (3 y ~190 filas), así que van enteros en una sola llamada.
        Municipios y localidades no: se piden filtrados, porque son 2.264 y
        15.394 y meterlos en la pantalla la vuelve inusable.
        """

        return Response(
            CatalogosRegistroErroneoSerializer(
                {
                    "sexos": [
                        {"id": s.id, "nombre": s.sexo}
                        for s in Sexo.objects.all().order_by("sexo")
                    ],
                    "nacionalidades": [
                        {"id": n.id, "nombre": n.nacionalidad}
                        for n in Nacionalidad.objects.all().order_by("nacionalidad")
                    ],
                }
            ).data
        )

    @extend_schema(responses=OpcionCatalogoSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="municipios")
    def municipios(self, request, pk=None):
        """Municipios que la corrección de un registro erróneo va a aceptar.

        Va acotado a la **provincia del expediente**, no al país: el validador
        de la importación arma su caché con
        `Municipio.objects.filter(provincia_id=provincia_usuario_id)`, así que
        un municipio de otra provincia se rechaza con "municipio N no
        encontrado". Ofrecer opciones que después no se aceptan es peor que no
        ofrecer ninguna.

        Se resuelve la provincia con la misma función que usa la validación,
        para que el desplegable y el validador no puedan desalinearse.
        """

        expediente = self.get_object()
        provincia_id = registros_erroneos_service.provincia_de(request.user, expediente)
        queryset = Municipio.objects.all()
        if provincia_id:
            queryset = queryset.filter(provincia_id=provincia_id)
        return Response(
            OpcionCatalogoSerializer(
                [{"id": m.id, "nombre": m.nombre} for m in queryset.order_by("nombre")],
                many=True,
            ).data
        )

    @extend_schema(
        parameters=[OpenApiParameter("municipio", int)],
        responses=LocalidadLookupSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="localidades")
    def localidades(self, request, pk=None):
        """Localidades que la correccion de este expediente va a aceptar.

        Acotadas a la **provincia del expediente**, por lo mismo que los
        municipios: el validador resuelve `localidad_responsable` contra
        `Localidad.objects.filter(municipio__provincia_id=provincia_usuario_id)`.

        Con `?municipio=` se acota ademas a ese municipio, que es lo que usa el
        campo `localidad` del beneficiario. Sin el parametro devuelve toda la
        provincia, que es lo que necesita `localidad_responsable`: ese campo no
        tiene municipio propio, el validador lo deriva de la localidad elegida.
        """

        expediente = self.get_object()
        provincia_id = registros_erroneos_service.provincia_de(request.user, expediente)
        queryset = Localidad.objects.select_related("municipio__provincia")
        if provincia_id:
            queryset = queryset.filter(municipio__provincia_id=provincia_id)

        municipio_id = (request.query_params.get("municipio") or "").strip()
        if municipio_id.isdigit():
            queryset = queryset.filter(municipio_id=int(municipio_id))

        queryset = queryset.order_by("municipio__nombre", "nombre")
        return Response(LocalidadLookupSerializer(queryset, many=True).data)

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    @action(detail=True, methods=["get"], url_path="excel-masivo")
    def excel_masivo(self, request, pk=None):
        """Descarga la copia del Excel masivo vigente del expediente."""

        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("No tiene permisos para descargar el Excel masivo.")
        expediente = self.get_object()
        if not expediente.excel_masivo:
            raise ValidationError(
                {"detail": "El expediente no tiene Excel masivo cargado."}
            )
        nombre = expediente.excel_masivo.name.rsplit("/", 1)[-1]
        return FileResponse(
            expediente.excel_masivo.open("rb"), as_attachment=True, filename=nombre
        )

    @extend_schema(
        request=PreviewExcelSerializer, responses=PreviewExcelResultadoSerializer
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="preview-excel",
        parser_classes=[MultiPartParser, FormParser],
    )
    def preview_excel(self, request):
        """Lee el Excel y devuelve las filas, sin crear nada.

        Es la previsualizacion del alta: permite corregir el archivo antes de
        que exista un expediente.
        """

        self._exigir_gestion()
        entrada = PreviewExcelSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            preview = ImportacionService.preview_excel(
                entrada.validated_data["excel_masivo"],
                max_rows=entrada.validated_data.get("limit"),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        # `all_rows` queda afuera: lo usa la vista web para su cache de sesion.
        return Response(PreviewExcelResultadoSerializer(preview).data)

    @extend_schema(request=None, responses=AccionResultadoSerializer)
    @action(detail=True, methods=["post"])
    def recepcionar(self, request, pk=None):
        """Nacion toma el expediente que la provincia confirmo."""

        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("Solo coordinacion puede recepcionar.")
        expediente = self.get_object()
        try:
            ExpedienteService.recepcionar(expediente, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        expediente.refresh_from_db()
        return Response(
            {
                "detail": "Expediente recepcionado.",
                "expediente": ExpedienteSerializer(
                    expediente, context=self.get_serializer_context()
                ).data,
            }
        )

    @extend_schema(request=ArchivoSerializer, responses=None)
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def cruce(self, request, pk=None):
        """Sube el Excel de respuesta de Sintys y ejecuta el cruce por CUIT."""

        # Igual que `SubirCruceExcelView`: admin o el tecnico asignado.
        if not (is_admin(request.user) or is_tecnico(request.user)):
            raise PermissionDenied("Solo la tecnica asignada ejecuta el cruce.")
        expediente = self.get_object()
        if not is_admin(request.user) and not (
            expediente.asignaciones_tecnicos.filter(tecnico=request.user).exists()
        ):
            raise PermissionDenied("No sos un técnico asignado a este expediente.")
        entrada = ArchivoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resultado = CruceService.procesar_cruce_por_cuit(
                expediente, entrada.validated_data["archivo"], request.user
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(resultado)

    @extend_schema(request=CrearLegajosSerializer, responses=None)
    @action(detail=True, methods=["post"], url_path="crear-legajos")
    def crear_legajos(self, request, pk=None):
        """Alta manual de legajos a partir de filas ya previsualizadas."""

        expediente = self.get_object()
        self._exigir_gestion(expediente)
        entrada = CrearLegajosSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resultado = ExpedienteService.crear_legajos_desde_filas(
                expediente, entrada.validated_data["rows"], request.user
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(resultado)

    # --- Sub-recursos de proceso -------------------------------------------

    @extend_schema(responses=RegistroErroneoSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="registros-erroneos")
    def registros_erroneos(self, request, pk=None):
        """Filas del Excel que no pudieron importarse."""

        expediente = self.get_object()
        queryset = RegistroErroneo.objects.filter(
            expediente=expediente, procesado=False
        ).order_by("fila_excel")
        return Response(
            RegistroErroneoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    def _exigir_gestion_registros_erroneos(self):
        """Mismo permiso que la pantalla: lo decide el service, no la API."""

        if not registros_erroneos_service.puede_gestionar(self.request.user):
            raise PermissionDenied(
                "No tiene permisos para gestionar los registros erróneos."
            )

    @extend_schema(
        request=ActualizarRegistroErroneoSerializer,
        responses=AccionResultadoSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=r"registros-erroneos/(?P<registro_id>[0-9]+)/actualizar",
    )
    def actualizar_registro_erroneo(self, request, pk=None, registro_id=None):
        """Corrige una fila erronea, con la misma validacion que la pantalla."""

        self._exigir_gestion_registros_erroneos()
        expediente = self.get_object()
        entrada = ActualizarRegistroErroneoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        registro = get_object_or_404(
            RegistroErroneo, pk=registro_id, expediente=expediente
        )
        try:
            registros_erroneos_service.actualizar(
                expediente, registro, entrada.validated_data["datos"], request.user
            )
        except DjangoValidationError as exc:
            # Se devuelven los campos invalidos como los espera un formulario.
            raise ValidationError(
                {
                    "detail": str(exc),
                    "invalid_fields": registros_erroneos_service.campos_invalidos(exc),
                }
            ) from exc
        return Response({"detalle": "Registro actualizado correctamente."})

    @extend_schema(request=None, responses=ReprocesoResultadoSerializer)
    @action(detail=True, methods=["post"], url_path="registros-erroneos/reprocesar")
    def reprocesar_registros_erroneos(self, request, pk=None):
        """Reintenta crear los legajos de las filas que quedaron con error."""

        self._exigir_gestion_registros_erroneos()
        expediente = self.get_object()
        try:
            resumen = registros_erroneos_service.reprocesar(expediente, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(ReprocesoResultadoSerializer(resumen).data)

    @extend_schema(request=None, responses=AccionResultadoSerializer)
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"registros-erroneos/(?P<registro_id>[0-9]+)",
    )
    def eliminar_registro_erroneo(self, request, pk=None, registro_id=None):
        """Descarta una fila erronea sin importarla."""

        self._exigir_gestion_registros_erroneos()
        expediente = self.get_object()
        registro = get_object_or_404(
            RegistroErroneo, pk=registro_id, expediente=expediente
        )
        registros_erroneos_service.eliminar(registro, request.user)
        return Response({"detalle": "Registro eliminado correctamente."})

    @extend_schema(responses=None)
    @action(detail=True, methods=["get"], url_path="estructura-familiar")
    def estructura_familiar(self, request, pk=None):
        """Responsables e hijos a cargo del expediente."""

        expediente = self.get_object()
        return Response(
            FamiliaService.obtener_estructura_familiar_expediente(expediente)
        )

    # --- Descargas ---------------------------------------------------------

    @extend_schema(responses={200: {"type": "string", "format": "binary"}})
    @action(detail=True, methods=["get"], url_path="nomina-sintys")
    def nomina_sintys(self, request, pk=None):
        """Excel con la nomina a enviar a Sintys."""

        expediente = self.get_object()
        try:
            contenido = CruceService.generar_nomina_sintys_excel(expediente)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return _respuesta_excel(contenido, f"nomina_sintys_{expediente.pk}.xlsx")

    @extend_schema(responses={200: {"type": "string", "format": "binary"}})
    @action(detail=True, methods=["get"], url_path="padron-final")
    def padron_final(self, request, pk=None):
        """Excel con los legajos aprobados del expediente."""

        expediente = self.get_object()
        if not PadronFinalService.hay_aprobados(expediente):
            raise ValidationError({"detail": ["El expediente no tiene aprobados."]})
        contenido = PadronFinalService.generar_padron_final_excel(expediente)
        return _respuesta_excel(contenido, f"padron_final_{expediente.pk}.xlsx")

    @extend_schema(request=None, responses=AccionResultadoSerializer)
    @action(detail=True, methods=["post"], url_path="desasignar-tecnico")
    def desasignar_tecnico(self, request, pk=None):
        if not (is_admin(request.user) or is_coordinador(request.user)):
            raise PermissionDenied("Solo coordinacion puede desasignar tecnicos.")
        expediente = self.get_object()
        try:
            AsignacionService.desasignar_tecnico(expediente, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response({"detail": "Tecnico desasignado."})


class ReporteViewSet(viewsets.ViewSet):
    """Reporte de Celiaquia.

    Delega entero en `reporte_service`, el mismo que usa la pantalla Django:
    las reglas de que cuenta como persona unica o como dupla no se replican.
    El alcance territorial tambien lo aplica el service.
    """

    permission_classes = [IsAuthenticated, TieneAccesoReporte]

    @extend_schema(
        parameters=[
            OpenApiParameter("provincia", int),
            OpenApiParameter("fecha_desde", str),
            OpenApiParameter("fecha_hasta", str),
            OpenApiParameter("expediente_numero", str),
            OpenApiParameter("documento_persona", str),
            OpenApiParameter("revision_tecnico", str),
            OpenApiParameter("resultado_sintys", str),
            OpenApiParameter("estado_cupo", str),
            OpenApiParameter("page", int),
        ],
        responses=ReporteSerializer,
    )
    def list(self, request):
        return Response(ReporteSerializer(build_report_payload(request)).data)


class LegajoViewSet(viewsets.ReadOnlyModelViewSet):
    """Legajos, acotados a los expedientes que el usuario puede ver."""

    permission_classes = PERMISOS_EXPEDIENTES
    serializer_class = LegajoSerializer
    # Solo para que el schema derive el tipo del pk: get_queryset() manda.
    queryset = ExpedienteCiudadano.objects.none()

    def get_queryset(self):
        expedientes_visibles = scope_expedientes(
            Expediente.objects.all(), self.request.user
        )
        queryset = (
            ExpedienteCiudadano.objects.filter(expediente__in=expedientes_visibles)
            .select_related("estado", "ciudadano", "expediente")
            .order_by("-creado_en", "pk")
        )

        expediente_id = (self.request.query_params.get("expediente") or "").strip()
        if expediente_id.isdigit():
            queryset = queryset.filter(expediente_id=int(expediente_id))
        revision = (self.request.query_params.get("revision_tecnico") or "").strip()
        if revision:
            queryset = queryset.filter(revision_tecnico=revision.upper())
        estado_cupo = (self.request.query_params.get("estado_cupo") or "").strip()
        if estado_cupo:
            queryset = queryset.filter(estado_cupo=estado_cupo.upper())
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter("expediente", int),
            OpenApiParameter("revision_tecnico", str),
            OpenApiParameter("estado_cupo", str),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=None, responses=None)
    @action(detail=True, methods=["post"], url_path="validar-renaper")
    def validar_renaper(self, request, pk=None):
        """Consulta RENAPER y devuelve la comparacion con los datos cargados.

        No guarda nada: el resultado se confirma con `validacion-renaper`.
        """

        if not validacion_renaper_service.puede_validar(request.user):
            raise PermissionDenied("Solo técnica o coordinación validan con RENAPER.")
        legajo = self.get_object()
        payload, estado_http = validacion_renaper_service.consultar(
            legajo, request.user
        )
        if not payload.get("success"):
            # La pantalla devuelve los errores de negocio con HTTP 200; la API
            # los traduce a 400, que es lo que corresponde en REST.
            if estado_http == 200:
                estado_http = 400
            raise _error_renaper(payload, estado_http)
        return Response(payload)

    @extend_schema(
        request=GuardarValidacionRenaperSerializer,
        responses=AccionResultadoSerializer,
    )
    @action(detail=True, methods=["post"], url_path="validacion-renaper")
    def guardar_validacion_renaper(self, request, pk=None):
        """Confirma el resultado: 1 acepta, 2 rechaza y libera cupo, 3 subsana."""

        if not validacion_renaper_service.puede_validar(request.user):
            raise PermissionDenied("Solo técnica o coordinación validan con RENAPER.")
        legajo = self.get_object()
        entrada = GuardarValidacionRenaperSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            etiqueta = validacion_renaper_service.guardar_estado(
                legajo,
                entrada.validated_data["estado"],
                request.user,
                comentario=entrada.validated_data.get("comentario", ""),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response({"detalle": f"Validación Renaper guardada: {etiqueta}"})

    @extend_schema(responses=ComentarioLegajoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def comentarios(self, request, pk=None):
        """Historial de comentarios del legajo, deduplicado como la pantalla."""

        legajo = self.get_object()
        exigir_acceso_nacion_a_comentarios(request.user, legajo)
        historial = ComentariosTecnicosService.historial(legajo)
        return Response(
            ComentarioLegajoSerializer(
                historial, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(
        request=CrearComentarioTecnicoSerializer,
        responses=ComentarioLegajoSerializer,
    )
    @action(detail=True, methods=["post"], url_path="comentarios/tecnico")
    def crear_comentario_tecnico(self, request, pk=None):
        """Alta de un comentario tecnico interno sobre el legajo.

        Solo el tecnico asignado, el coordinador o un admin: la provincia ve el
        panel pero no escribe, igual que en la pantalla.
        """

        legajo = self.get_object()
        exigir_acceso_nacion_a_comentarios(request.user, legajo)
        entrada = CrearComentarioTecnicoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            comentario = ComentariosTecnicosService.registrar(
                legajo, usuario=request.user, **entrada.validated_data
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(
            ComentarioLegajoSerializer(
                comentario, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses=MotivoPreviewSerializer)
    @action(detail=True, methods=["get"], url_path="motivo-preview")
    def motivo_preview(self, request, pk=None):
        """Motivos elegibles al subsanar o rechazar, como la pantalla.

        `ComentariosTecnicosService` ya no concatena el historial entero: desde
        el issue #2592 cada instancia lleva solo las observaciones elegidas.
        """

        legajo = self.get_object()
        exigir_acceso_nacion_a_comentarios(request.user, legajo)
        opciones = ComentariosTecnicosService.opciones_seleccionables(legajo)
        return Response(
            MotivoPreviewSerializer(
                {"opciones": opciones, "tiene_observaciones": bool(opciones)}
            ).data
        )

    @extend_schema(request=None, responses=LegajoSerializer)
    @action(detail=True, methods=["post"], url_path="confirmar-subsanacion")
    def confirmar_subsanacion(self, request, pk=None):
        """Pasa el legajo de SUBSANAR a SUBSANADO.

        Es el paso que faltaba: responder una subsanacion sube la evidencia y
        marca la subsanacion como RESPONDIDA, pero **no cambia el estado del
        legajo**. Sin confirmar, el legajo sigue en SUBSANAR y la tecnica no
        puede volver a aprobarlo ni rechazarlo.

        Exige lo mismo que la pantalla: archivos obligatorios cargados,
        evidencia de subsanacion adjunta y que no haya una subsanacion RENAPER
        pendiente.
        """

        legajo = self.get_object()
        try:
            can_confirm_subsanacion(request.user, legajo.expediente)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc) or "Permiso denegado.") from exc
        try:
            SubsanacionService.confirmar(legajo, request.user)
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        legajo.refresh_from_db()
        return Response(
            LegajoSerializer(legajo, context=self.get_serializer_context()).data
        )

    @extend_schema(
        request=ResponderSubsanacionSerializer, responses=AccionResultadoSerializer
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="responder-subsanacion",
        parser_classes=[MultiPartParser, FormParser],
    )
    def responder_subsanacion(self, request, pk=None):
        """La provincia adjunta evidencia nueva para la subsanacion activa."""

        legajo = self.get_object()
        self._exigir_edicion_de_archivos(legajo)

        entrada = ResponderSubsanacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            SubsanacionService.exigir_puede_responder(legajo)
            SubsanacionService.responder(
                legajo=legajo,
                archivos=entrada.validated_data["archivos"],
                usuario=request.user,
                descripcion=entrada.validated_data.get("descripcion", ""),
                observacion_id=entrada.validated_data.get("observacion_id"),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response({"detalle": "Archivos de subsanación cargados correctamente."})

    @extend_schema(responses=DocumentoLegajoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def documentos(self, request, pk=None):
        legajo = self.get_object()
        queryset = DocumentosService.obtener_documentos_legajo(legajo)
        return Response(
            DocumentoLegajoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(responses=SubsanacionSerializer(many=True))
    @action(detail=True, methods=["get"])
    def subsanaciones(self, request, pk=None):
        legajo = self.get_object()
        queryset = Subsanacion.objects.filter(legajo=legajo).select_related(
            "solicitada_por", "respondida_por"
        )
        return Response(
            SubsanacionSerializer(
                queryset.order_by("-solicitada_en"),
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        request=SolicitarSubsanacionSerializer, responses=AccionResultadoSerializer
    )
    @action(detail=True, methods=["post"], url_path="solicitar-subsanacion")
    def solicitar_subsanacion(self, request, pk=None):
        """Marca el legajo para subsanar. Es una accion del tecnico revisor.

        Mismo permiso que `LegajoSubsanarView`: admin, coordinacion o el
        tecnico asignado. La provincia duena del expediente no.
        """

        legajo = self.get_object()
        try:
            can_review_legajo(request.user, legajo.expediente)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc) or "Permiso denegado.") from exc
        entrada = SolicitarSubsanacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            LegajoService.solicitar_subsanacion(
                legajo, entrada.validated_data["motivo"], request.user
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response({"detail": "Subsanacion solicitada."})

    @extend_schema(request=RevisarLegajoSerializer, responses=None)
    @action(detail=True, methods=["post"])
    def revisar(self, request, pk=None):
        """Revision tecnica: aprobar, rechazar, subsanar o eliminar.

        Todo el flujo (permisos, transiciones, liberacion de cupo, historial y
        publicacion de observaciones) vive en `RevisionService`, el mismo que
        usa la pantalla.
        """

        legajo = self.get_object()
        entrada = RevisarLegajoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        accion = datos["accion"]

        try:
            RevisionService.verificar_permiso(request.user, legajo.expediente, accion)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        try:
            RevisionService.validar_transicion(legajo, accion)

            if accion == "ELIMINAR":
                # La baja de la provincia la revalida el service con el
                # expediente bloqueado (`can_delete_legajo`).
                return Response(RevisionService.eliminar(legajo, request.user))

            # Atomico: liberar el cupo y despues fallar al validar la
            # documentacion complementaria no puede dejar el cupo liberado.
            with transaction.atomic():
                return Response(self._aplicar_revision(legajo, accion, datos))
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc) or "Permiso denegado.") from exc
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc

    def _aplicar_revision(self, legajo, accion, datos) -> dict:
        usuario = self.request.user
        motivo = ""
        comentarios = []
        if accion in ("RECHAZAR", "SUBSANAR"):
            comentarios = RevisionService.resolver_seleccion(
                legajo, datos.get("observaciones_ids", [])
            )
            motivo = RevisionService.componer_motivo(
                comentarios, datos.get("texto_libre", "")
            )

        RevisionService.liberar_cupo_si_corresponde(legajo, usuario, accion)

        if accion == "APROBAR":
            return RevisionService.aprobar(legajo, usuario)
        if accion == "RECHAZAR":
            return RevisionService.rechazar(
                legajo, usuario, motivo, comentarios=comentarios
            )
        return RevisionService.subsanar(
            legajo,
            usuario,
            motivo,
            tipo_subsanacion=datos.get("tipo_subsanacion", ""),
            comentarios=comentarios,
            documentacion_complementaria=datos.get("documentacion_complementaria", []),
            observaciones_fallback=[
                (obs["tipo"], obs["detalle"]) for obs in datos.get("observaciones", [])
            ],
        )

    def _exigir_edicion_de_archivos(self, legajo):
        """Quien puede cargar archivos en el legajo: la regla de la pantalla."""

        try:
            can_edit_legajo_files(self.request.user, legajo.expediente, legajo)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc) or "Permiso denegado.") from exc

    @extend_schema(request=SubirArchivoLegajoSerializer, responses=None)
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def archivos(self, request, pk=None):
        """Sube un archivo al legajo, en el slot indicado (1, 2 o 3).

        Mismas reglas que `LegajoArchivoUploadView`: permiso por rol y estado
        (`can_edit_legajo_files`) y, una vez enviado el expediente o con el
        legajo en subsanacion, 409: las correcciones van como evidencia de
        subsanacion, no reemplazando los originales.
        """

        legajo = self.get_object()
        self._exigir_edicion_de_archivos(legajo)
        if documentos_legajo_bloqueados(legajo):
            return Response(
                {
                    "detail": (
                        "Los documentos del legajo no pueden reemplazarse en este "
                        "estado. Cargá las correcciones como archivos de "
                        "subsanación."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        entrada = SubirArchivoLegajoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            LegajoService.subir_archivo_individual(
                legajo,
                entrada.validated_data["archivo"],
                entrada.validated_data.get("slot"),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        legajo.refresh_from_db()
        return Response(
            DocumentoLegajoSerializer(
                DocumentosService.obtener_documentos_legajo(legajo),
                many=True,
                context=self.get_serializer_context(),
            ).data
        )


class ProvinciaCupoViewSet(viewsets.ReadOnlyModelViewSet):
    """Cupos por provincia. Solo lectura: el alta la hace `CupoService`."""

    permission_classes = PERMISOS_CUPOS
    serializer_class = ProvinciaCupoSerializer
    queryset = ProvinciaCupo.objects.none()

    def get_queryset(self):
        return ProvinciaCupo.objects.select_related("provincia").order_by(
            "provincia__nombre"
        )

    @extend_schema(responses=FilaCupoProvinciaSerializer(many=True))
    # Sin paginar: son las 24 provincias. Declararlo hace que el schema no la
    # documente como pagina.
    @action(detail=False, methods=["get"], pagination_class=None)
    def dashboard(self, request):
        """Cuadro de cupos: **todas** las provincias, con cupo o sin él.

        El listado principal (`GET cupos/`) solo devuelve las configuradas,
        porque son los `ProvinciaCupo` que existen. Para poder asignar cupo a
        una provincia nueva hace falta verla: esto replica lo que muestra la
        pantalla Django.
        """

        filas = [
            {
                "provincia_id": fila["provincia"].id,
                "provincia": fila["provincia"].nombre,
                "cupo_id": fila["cupo_id"],
                "total_asignado": fila["total_asignado"],
                "usados": fila["usados"],
                "disponibles": fila["disponibles"],
                "fuera": fila["fuera"],
                "configurado": fila["cupo_id"] is not None,
            }
            for fila in CupoService.filas_dashboard()
        ]
        return Response(FilaCupoProvinciaSerializer(filas, many=True).data)

    @extend_schema(responses=ProvinciaCupoSerializer)
    @action(detail=True, methods=["get"])
    def metricas(self, request, pk=None):
        """Metricas calculadas por `CupoService`, no el contador crudo."""

        cupo = self.get_object()
        return Response(CupoService.metrics_por_provincia(cupo.provincia))

    @extend_schema(responses=LegajoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def ocupados(self, request, pk=None):
        cupo = self.get_object()
        queryset = _para_listar_legajos(
            CupoService.lista_ocupados_por_provincia(cupo.provincia)
        )
        return Response(
            LegajoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(responses=LegajoSerializer(many=True))
    @action(detail=True, methods=["get"])
    def suspendidos(self, request, pk=None):
        cupo = self.get_object()
        queryset = _para_listar_legajos(
            CupoService.lista_suspendidos_por_provincia(cupo.provincia)
        )
        return Response(
            LegajoSerializer(
                queryset, many=True, context=self.get_serializer_context()
            ).data
        )

    # --- Escrituras --------------------------------------------------------

    def _exigir_gestion_cupo(self):
        """Configurar cupo y mover titulares es de coordinacion o admin."""

        user = self.request.user
        if not (is_admin(user) or is_coordinador(user)):
            raise PermissionDenied("No tiene permisos para gestionar el cupo.")

    @extend_schema(request=ConfigurarCupoSerializer, responses=ProvinciaCupoSerializer)
    @action(detail=False, methods=["post"], url_path=r"provincia/(?P<provincia_id>\d+)")
    def configurar(self, request, provincia_id=None):
        """Fija el total asignado de una provincia. Crea el cupo si no existia.

        Va por provincia y no por pk del cupo porque la provincia puede todavia
        no tener `ProvinciaCupo`: es justamente el caso de "sin configurar".
        """

        self._exigir_gestion_cupo()
        provincia = get_object_or_404(Provincia, pk=provincia_id)
        entrada = ConfigurarCupoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            cupo = CupoService.configurar_total(
                provincia, entrada.validated_data["total_asignado"], request.user
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(
            ProvinciaCupoSerializer(cupo, context=self.get_serializer_context()).data
        )

    def _legajo_de_cupo(self, legajo_id):
        """El legajo tiene que estar dentro del alcance del usuario."""

        expedientes_visibles = scope_expedientes(
            Expediente.objects.all(), self.request.user
        )
        return get_object_or_404(
            ExpedienteCiudadano,
            pk=legajo_id,
            expediente__in=expedientes_visibles,
        )

    def _mover_cupo(self, request, legajo_id, operacion, mensaje):
        self._exigir_gestion_cupo()
        legajo = self._legajo_de_cupo(legajo_id)
        entrada = MotivoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            operacion(
                legajo=legajo,
                usuario=request.user,
                motivo=entrada.validated_data.get("motivo", ""),
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        legajo.refresh_from_db()
        return Response(
            {
                "detail": mensaje,
                "legajo": LegajoSerializer(
                    legajo, context=self.get_serializer_context()
                ).data,
            }
        )

    @extend_schema(request=MotivoSerializer, responses=AccionResultadoSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path=r"legajos/(?P<legajo_id>\d+)/baja",
    )
    def baja_legajo(self, request, legajo_id=None):
        """Libera definitivamente el cupo del titular."""

        return self._mover_cupo(
            request, legajo_id, CupoService.liberar_slot, "Titular dado de baja."
        )

    @extend_schema(request=MotivoSerializer, responses=AccionResultadoSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path=r"legajos/(?P<legajo_id>\d+)/suspender",
    )
    def suspender_legajo(self, request, legajo_id=None):
        """Suspende al titular sin liberar el cupo."""

        return self._mover_cupo(
            request, legajo_id, CupoService.suspender_slot, "Titular suspendido."
        )

    @extend_schema(request=MotivoSerializer, responses=AccionResultadoSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path=r"legajos/(?P<legajo_id>\d+)/reactivar",
    )
    def reactivar_legajo(self, request, legajo_id=None):
        """Reactiva un titular suspendido."""

        return self._mover_cupo(
            request, legajo_id, CupoService.reactivar_slot, "Titular reactivado."
        )


class CupoMovimientoViewSet(viewsets.ReadOnlyModelViewSet):
    """Auditoria de movimientos de cupo."""

    permission_classes = PERMISOS_CUPOS
    serializer_class = CupoMovimientoSerializer
    queryset = CupoMovimiento.objects.none()

    def get_queryset(self):
        queryset = CupoMovimiento.objects.select_related(
            "provincia", "usuario"
        ).order_by("-creado_en", "pk")
        provincia_id = (self.request.query_params.get("provincia") or "").strip()
        if provincia_id.isdigit():
            queryset = queryset.filter(provincia_id=int(provincia_id))
        expediente_id = (self.request.query_params.get("expediente") or "").strip()
        if expediente_id.isdigit():
            queryset = queryset.filter(expediente_id=int(expediente_id))
        return queryset


class PagoExpedienteViewSet(viewsets.ReadOnlyModelViewSet):
    """Lotes de pago y su nomina."""

    permission_classes = PERMISOS_CUPOS
    serializer_class = PagoExpedienteSerializer
    queryset = PagoExpediente.objects.none()

    def get_queryset(self):
        queryset = PagoExpediente.objects.select_related("provincia").order_by(
            "-creado_en", "pk"
        )
        # El listado de la pantalla es por provincia: filtrar aca evita que el
        # front tenga que recorrer todas las paginas de todas las provincias.
        provincia_id = (self.request.query_params.get("provincia") or "").strip()
        if provincia_id.isdigit():
            queryset = queryset.filter(provincia_id=int(provincia_id))
        periodo = (self.request.query_params.get("periodo") or "").strip()
        if periodo:
            queryset = queryset.filter(periodo=periodo)
        estado = (self.request.query_params.get("estado") or "").strip()
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter("provincia", int),
            OpenApiParameter("periodo", str),
            OpenApiParameter("estado", str),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def _exigir_gestion_pago(self):
        user = self.request.user
        if not (is_admin(user) or is_coordinador(user)):
            raise PermissionDenied("No tiene permisos para operar pagos.")

    @extend_schema(request=CrearPagoSerializer, responses=PagoExpedienteSerializer)
    def create(self, request, *args, **kwargs):
        """Arma el lote de pago de una provincia con su nomina activa."""

        self._exigir_gestion_pago()
        entrada = CrearPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        provincia = get_object_or_404(
            Provincia, pk=entrada.validated_data["provincia_id"]
        )
        try:
            pago = PagoService.crear_expediente_pago(
                provincia=provincia,
                usuario=request.user,
                periodo=entrada.validated_data.get("periodo") or None,
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(
            PagoExpedienteSerializer(pago, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ArchivoSerializer, responses=None)
    @action(
        detail=True,
        methods=["post"],
        url_path="procesar-respuesta",
        parser_classes=[MultiPartParser, FormParser],
    )
    def procesar_respuesta(self, request, pk=None):
        """Cruza la respuesta de Sintys contra la nomina del lote."""

        self._exigir_gestion_pago()
        pago = self.get_object()
        entrada = ArchivoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resultado = PagoService.procesar_respuesta(
                pago=pago,
                archivo_respuesta=entrada.validated_data["archivo"],
                usuario=request.user,
            )
        except DjangoValidationError as exc:
            raise _traducir_error(exc) from exc
        return Response(resultado)

    @extend_schema(responses={200: {"type": "string", "format": "binary"}})
    @action(detail=True, methods=["get"], url_path="exportar-nomina")
    def exportar_nomina(self, request, pk=None):
        """Excel con la nomina activa de la provincia del lote."""

        pago = self.get_object()
        contenido = PagoService.exportar_nomina_actual_excel(provincia=pago.provincia)
        return _respuesta_excel(contenido, f"nomina_pago_{pago.pk}.xlsx")

    @extend_schema(responses=PagoNominaSerializer(many=True))
    @action(detail=True, methods=["get"])
    def nomina(self, request, pk=None):
        pago = self.get_object()
        queryset = PagoNomina.objects.filter(pago=pago).order_by("apellido", "nombre")
        pagina = self.paginate_queryset(queryset)
        serializer = PagoNominaSerializer(
            pagina if pagina is not None else queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
