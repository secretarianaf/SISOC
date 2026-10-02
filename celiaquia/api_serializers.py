"""Serializers de la API REST de Celiaquia.

Se arman desde los modelos con `ModelSerializer`, pero **nunca** con
`fields = "__all__"`: varios modelos guardan FileFields con rutas internas y FKs
a `User` que no deben salir de la aplicacion. Los campos se listan a mano.

Los serializers son de lectura: las escrituras pasan por
`celiaquia/services/`, donde vive la maquina de estados.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from celiaquia.models import (
    AsignacionTecnico,
    HistorialComentarios,
    CupoMovimiento,
    DocumentoLegajo,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    ExpedienteEstadoHistorial,
    Organismo,
    PagoExpediente,
    PagoNomina,
    ProvinciaCupo,
    RegistroErroneo,
    Subsanacion,
    TipoCruce,
    TipoDocumento,
)


class UsuarioResumenSerializer(serializers.Serializer):
    """Identidad minima de un usuario: nunca mail, permisos ni credenciales."""

    id = serializers.IntegerField(read_only=True)
    nombre = serializers.SerializerMethodField()

    def get_nombre(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


# --- Catalogos -------------------------------------------------------------


class _CatalogoNombreSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "nombre"]


class EstadoExpedienteSerializer(_CatalogoNombreSerializer):
    class Meta(_CatalogoNombreSerializer.Meta):
        model = EstadoExpediente


class EstadoLegajoSerializer(_CatalogoNombreSerializer):
    class Meta(_CatalogoNombreSerializer.Meta):
        model = EstadoLegajo


class OrganismoSerializer(_CatalogoNombreSerializer):
    class Meta(_CatalogoNombreSerializer.Meta):
        model = Organismo


class TipoCruceSerializer(_CatalogoNombreSerializer):
    class Meta(_CatalogoNombreSerializer.Meta):
        model = TipoCruce


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ["id", "nombre", "descripcion", "requerido", "orden", "activo"]


# --- Expediente ------------------------------------------------------------


class ExpedienteSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    provincia = serializers.SerializerMethodField()
    usuario_provincia = UsuarioResumenSerializer(read_only=True)
    legajos_total = serializers.SerializerMethodField()

    class Meta:
        model = Expediente
        fields = [
            "id",
            "numero_expediente",
            "estado",
            "provincia",
            "usuario_provincia",
            "observaciones",
            "legajos_total",
            "fecha_creacion",
            "fecha_modificacion",
            "fecha_cierre",
        ]

    def get_provincia(self, obj) -> str:
        """Provincia derivada del perfil de quien creo el expediente.

        El listado web la deriva de los ciudadanos con un Subquery; aca se usa
        el valor anotado cuando el ViewSet lo provee y se cae al perfil.
        """

        derivada = getattr(obj, "provincia_derivada", None)
        if derivada:
            return derivada
        perfil = getattr(obj.usuario_provincia, "profile", None)
        provincia = getattr(perfil, "provincia", None)
        return getattr(provincia, "nombre", "") or ""

    def get_legajos_total(self, obj) -> int:
        anotado = getattr(obj, "legajos_total_count", None)
        if anotado is not None:
            return anotado
        return obj.expediente_ciudadanos.count()


class ExpedienteEstadoHistorialSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    usuario = UsuarioResumenSerializer(read_only=True)

    class Meta:
        model = ExpedienteEstadoHistorial
        fields = ["id", "estado", "usuario", "fecha"]


class AsignacionTecnicoSerializer(serializers.ModelSerializer):
    tecnico = UsuarioResumenSerializer(read_only=True)

    class Meta:
        model = AsignacionTecnico
        fields = ["id", "tecnico", "fecha_asignacion", "activa"]


# --- Legajos ---------------------------------------------------------------


class ReporteCasoSerializer(serializers.Serializer):
    """Una fila del detalle del reporte, ya clasificada por el service."""

    id = serializers.IntegerField()
    ciudadano = serializers.CharField(allow_blank=True)
    documento = serializers.CharField(allow_blank=True)
    provincia = serializers.CharField(allow_blank=True)
    expediente_id = serializers.IntegerField(allow_null=True)
    expediente_numero = serializers.CharField(allow_blank=True)
    revision_tecnico = serializers.CharField(allow_blank=True)
    resultado_sintys = serializers.CharField(allow_blank=True)
    estado_cupo = serializers.CharField(allow_blank=True)
    archivos_ok = serializers.BooleanField()
    clasificacion = serializers.CharField(allow_blank=True)
    creado_en = serializers.DateTimeField(allow_null=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ReporteSerializer(serializers.Serializer):
    """Reporte de Celiaquia.

    Las agregaciones las calcula `reporte_service`, el mismo que usa la
    pantalla Django. Acá solo se les da forma JSON: las reglas de qué cuenta
    como persona única o como dupla no se replican.
    """

    total_casos = serializers.IntegerField()
    casos_documentos_ok = serializers.IntegerField()
    casos_documentos_incompletos = serializers.IntegerField()
    porcentaje_documentos_ok = serializers.FloatField()
    porcentaje_documentos_incompletos = serializers.FloatField()
    casos_con_comentarios = serializers.IntegerField()
    metricas_principales = serializers.ListField(child=serializers.DictField())
    casos_por_instancia = serializers.DictField()
    resumen_validacion = serializers.ListField(child=serializers.DictField())
    resumen_sintys = serializers.ListField(child=serializers.DictField())
    resumen_cupo = serializers.ListField(child=serializers.DictField())
    clasificacion_aprobados = serializers.DictField()
    tendencia_mensual = serializers.ListField(child=serializers.DictField())
    expedientes_por_provincia = serializers.ListField(child=serializers.DictField())
    casos = ReporteCasoSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    detalle_desde = serializers.IntegerField()
    detalle_hasta = serializers.IntegerField()
    es_usuario_provincial = serializers.BooleanField()
    provincias = serializers.ListField(child=serializers.DictField())
    filtros_activos = serializers.ListField(child=serializers.DictField())

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ArchivoLegajoSerializer(serializers.Serializer):
    """Estado de uno de los tres slots de documentacion de un legajo.

    Cuales se piden depende del rol (beneficiario, responsable o ambos) y lo
    decide `LegajoService.get_archivos_requeridos_por_legajo`. Sin esto el front
    no sabe que subir ni con que etiqueta.
    """

    slot = serializers.IntegerField()
    campo = serializers.CharField()
    etiqueta = serializers.CharField()
    cargado = serializers.BooleanField()
    url = serializers.CharField(allow_blank=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class LegajoSerializer(serializers.ModelSerializer):
    """`ExpedienteCiudadano` es el legajo de una persona dentro del expediente."""

    estado = serializers.CharField(source="estado.nombre", read_only=True)
    ciudadano_id = serializers.IntegerField(read_only=True)
    ciudadano = serializers.SerializerMethodField()
    documento = serializers.SerializerMethodField()
    archivos = serializers.SerializerMethodField()

    class Meta:
        model = ExpedienteCiudadano
        fields = [
            "id",
            "expediente_id",
            "ciudadano_id",
            "ciudadano",
            "documento",
            "estado",
            "rol",
            "archivos_ok",
            "archivos",
            "cruce_ok",
            "observacion_cruce",
            "revision_tecnico",
            "resultado_sintys",
            "estado_cupo",
            "es_titular_activo",
            "estado_validacion_renaper",
            "subsanacion_tipo",
            "subsanacion_motivo",
            "subsanacion_solicitada_en",
            "subsanacion_enviada_en",
            "creado_en",
            "modificado_en",
        ]

    def get_ciudadano(self, obj) -> str:
        ciudadano = obj.ciudadano
        nombre = f"{ciudadano.apellido or ''} {ciudadano.nombre or ''}".strip()
        return nombre or f"#{ciudadano.pk}"

    def get_documento(self, obj) -> str:
        return str(getattr(obj.ciudadano, "documento", "") or "")

    @extend_schema_field(ArchivoLegajoSerializer(many=True))
    def get_archivos(self, obj):
        """Slots que este legajo tiene que presentar, con su estado.

        No hace consultas: los requeridos salen del rol del legajo y los
        archivos son campos del propio modelo.
        """

        from celiaquia.services.legajo_service import LegajoService

        requeridos = LegajoService.get_archivos_requeridos_por_legajo(obj)
        request = self.context.get("request")
        salida = []
        for campo, etiqueta in requeridos.items():
            archivo = getattr(obj, campo, None)
            url = ""
            if archivo:
                url = (
                    request.build_absolute_uri(archivo.url) if request else archivo.url
                )
            salida.append(
                {
                    "slot": int(campo.replace("archivo", "")),
                    "campo": campo,
                    "etiqueta": etiqueta,
                    "cargado": bool(archivo),
                    "url": url,
                }
            )
        return salida


class DocumentoLegajoSerializer(serializers.ModelSerializer):
    tipo_documento = serializers.CharField(
        source="tipo_documento.nombre", read_only=True
    )
    usuario_carga = UsuarioResumenSerializer(read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoLegajo
        fields = [
            "id",
            "legajo_id",
            "tipo_documento",
            "archivo_url",
            "observaciones",
            "usuario_carga",
            "fecha_carga",
        ]

    def get_archivo_url(self, obj) -> str:
        """URL absoluta del archivo; nunca la ruta de almacenamiento."""

        archivo = getattr(obj, "archivo", None)
        if not archivo:
            return ""
        request = self.context.get("request")
        url = archivo.url
        return request.build_absolute_uri(url) if request else url


class SubsanacionSerializer(serializers.ModelSerializer):
    solicitada_por = UsuarioResumenSerializer(read_only=True)
    respondida_por = UsuarioResumenSerializer(read_only=True)

    class Meta:
        model = Subsanacion
        fields = [
            "id",
            "legajo_id",
            "estado",
            "motivo_general",
            "solicitada_por",
            "solicitada_en",
            "respondida_por",
            "respondida_en",
        ]


# --- Cupos -----------------------------------------------------------------


class ProvinciaCupoSerializer(serializers.ModelSerializer):
    provincia = serializers.CharField(source="provincia.nombre", read_only=True)
    # `provincia` es el nombre, para mostrar. El id va aparte porque el front
    # lo necesita para `cupos/provincia/<id>/configurar`: sin esto no hay forma
    # de configurar un cupo desde el listado.
    provincia_id = serializers.IntegerField(read_only=True)
    disponibles = serializers.SerializerMethodField()

    class Meta:
        model = ProvinciaCupo
        fields = [
            "id",
            "provincia",
            "provincia_id",
            "total_asignado",
            "usados",
            "disponibles",
        ]

    def get_disponibles(self, obj) -> int:
        return max((obj.total_asignado or 0) - (obj.usados or 0), 0)


class CupoMovimientoSerializer(serializers.ModelSerializer):
    provincia = serializers.CharField(source="provincia.nombre", read_only=True)
    usuario = UsuarioResumenSerializer(read_only=True)

    class Meta:
        model = CupoMovimiento
        fields = [
            "id",
            "provincia",
            "expediente_id",
            "legajo_id",
            "tipo",
            "delta",
            "motivo",
            "usuario",
            "creado_en",
        ]


# --- Pagos -----------------------------------------------------------------


class PagoExpedienteSerializer(serializers.ModelSerializer):
    provincia = serializers.CharField(source="provincia.nombre", read_only=True)

    class Meta:
        model = PagoExpediente
        fields = [
            "id",
            "provincia",
            "periodo",
            "estado",
            "total_candidatos",
            "total_validados",
            "total_excluidos",
            "creado_en",
            "modificado_en",
        ]


class PagoNominaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoNomina
        fields = [
            "id",
            "pago_id",
            "legajo_id",
            "documento",
            "nombre",
            "apellido",
            "estado",
            "observacion",
            "creado_en",
        ]


# --- Entradas de las acciones ---------------------------------------------


class AsignarTecnicoSerializer(serializers.Serializer):
    tecnico_id = serializers.IntegerField()

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")


class SolicitarSubsanacionSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=2000)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")


class AccionResultadoSerializer(serializers.Serializer):
    """Respuesta uniforme de las acciones que delegan en un service."""

    detail = serializers.CharField()
    expediente = ExpedienteSerializer(required=False)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class _EntradaSerializer(serializers.Serializer):
    """Base de los serializers de solo entrada: no persisten nada.

    Las escrituras de este modulo pasan siempre por `celiaquia/services/`, asi
    que `create`/`update` no deben existir. Se centraliza el rechazo para no
    repetirlo en cada serializer.
    """

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo entrada.")


class ExpedienteCreateSerializer(_EntradaSerializer):
    """Alta del expediente con su Excel masivo."""

    numero_expediente = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    observaciones = serializers.CharField(required=False, allow_blank=True)
    excel_masivo = serializers.FileField(required=False)


class ExpedienteUpdateSerializer(_EntradaSerializer):
    """Metadatos editables mientras el expediente esta en CREADO."""

    numero_expediente = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    observaciones = serializers.CharField(required=False, allow_blank=True)


class PreviewExcelSerializer(_EntradaSerializer):
    """Previsualizacion del Excel antes de crear el expediente."""

    excel_masivo = serializers.FileField()
    limit = serializers.IntegerField(required=False, min_value=1, max_value=5000)


class PreviewExcelResultadoSerializer(serializers.Serializer):
    """Respuesta de `preview-excel/`.

    Sin esto, drf-spectacular documentaba el serializer de **entrada** como si
    fuera la respuesta, y los tipos generados para el front quedaban al reves.

    No se expone `all_rows`, que el servicio devuelve para que la vista web lo
    guarde en sesion: son hasta 5000 filas duplicadas que ningun cliente de la
    API consume.
    """

    headers = serializers.ListField(child=serializers.CharField())
    rows = serializers.ListField(child=serializers.DictField())
    total_rows = serializers.IntegerField()
    shown_rows = serializers.IntegerField()

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ExclusionImportacionSerializer(serializers.Serializer):
    """Fila que no se importó porque la persona ya está en el programa.

    No es un "registro erróneo": la fila está bien formada, pero el beneficiario
    ya existe. El Excel no se puede arreglar para que entre, así que no aparece
    en la grilla de errores y antes se perdía en silencio.
    """

    fila = serializers.IntegerField()
    documento = serializers.CharField(allow_blank=True)
    nombre = serializers.CharField(allow_blank=True)
    apellido = serializers.CharField(allow_blank=True)
    motivo = serializers.CharField()
    expediente_origen_id = serializers.IntegerField(required=False, allow_null=True)
    estado_expediente_origen = serializers.CharField(required=False, allow_blank=True)


class ProcesamientoResultadoSerializer(serializers.Serializer):
    """Resultado de procesar el Excel masivo.

    `ExpedienteService.procesar_expediente` ya devolvía esto; la API lo
    descartaba y respondía solo "Expediente procesado". El front no tenía forma
    de saber cuántas filas quedaron afuera ni por qué.
    """

    creados = serializers.IntegerField()
    errores = serializers.IntegerField()
    excluidos = serializers.IntegerField()
    excluidos_detalle = ExclusionImportacionSerializer(many=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ProcesarExpedienteRespuestaSerializer(serializers.Serializer):
    """Respuesta de `procesar/`: el expediente actualizado y el resumen."""

    detail = serializers.CharField()
    expediente = ExpedienteSerializer()
    resultado = ProcesamientoResultadoSerializer()

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ImportacionResultadoSerializer(serializers.Serializer):
    """Resultado de importar los legajos del Excel masivo ya cargado."""

    validos = serializers.IntegerField()
    errores = serializers.IntegerField()
    detalles_errores = serializers.ListField(
        child=serializers.DictField(), default=list
    )
    warnings = serializers.ListField(child=serializers.DictField(), default=list)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class OpcionCatalogoSerializer(serializers.Serializer):
    """Opción de un desplegable: id y etiqueta, nada más.

    El formulario de corrección de registros erróneos guarda **ids**, igual que
    la pantalla Django: el Excel trae texto libre ("F", "ARGENTINA") o códigos
    de otro sistema, y por eso falla la importación.
    """

    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class CatalogosRegistroErroneoSerializer(serializers.Serializer):
    """Catálogos chicos que el formulario necesita enteros."""

    sexos = OpcionCatalogoSerializer(many=True)
    nacionalidades = OpcionCatalogoSerializer(many=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class GuardarValidacionRenaperSerializer(_EntradaSerializer):
    """Resultado que el tecnico elige tras ver la comparacion con RENAPER."""

    estado = serializers.ChoiceField(choices=["1", "2", "3"])
    comentario = serializers.CharField(required=False, allow_blank=True)


class LocalidadLookupSerializer(serializers.Serializer):
    """Localidad con su municipio y provincia, para los selectores del alta."""

    localidad_id = serializers.IntegerField(source="id", read_only=True)
    localidad_nombre = serializers.CharField(source="nombre", read_only=True)
    municipio_id = serializers.IntegerField(read_only=True)
    municipio_nombre = serializers.CharField(
        source="municipio.nombre", read_only=True, default=""
    )
    provincia_id = serializers.IntegerField(
        source="municipio.provincia_id", read_only=True, default=None
    )
    provincia_nombre = serializers.CharField(
        source="municipio.provincia.nombre", read_only=True, default=""
    )

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ComentarioLegajoSerializer(serializers.ModelSerializer):
    """Comentario del panel de un legajo.

    Los comentarios tecnicos estructurados (issue #2318) traen ademas tipo de
    documento y observacion; en el resto esos campos vienen vacios.
    """

    usuario = UsuarioResumenSerializer(read_only=True)
    tipo_documento_display = serializers.CharField(
        source="get_tipo_documento_display", read_only=True
    )
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = HistorialComentarios
        fields = [
            "id",
            "comentario",
            "usuario",
            "fecha_creacion",
            "es_interno",
            "es_comentario_tecnico",
            "tipo_comentario",
            "tipo_documento",
            "tipo_documento_display",
            "archivo_url",
        ]

    def get_archivo_url(self, obj) -> str:
        archivo = getattr(obj, "archivo_adjunto", None)
        if not archivo:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(archivo.url) if request else archivo.url


class CrearComentarioTecnicoSerializer(_EntradaSerializer):
    """Alta estructurada: tipo de documento + Si/No + observacion.

    La combinacion valida la decide `ComentariosTecnicosService.registrar`, que
    es el mismo camino que usa la pantalla.
    """

    tipo_documento = serializers.CharField()
    tiene_observaciones = serializers.CharField()
    observacion_codigo = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    observacion_libre = serializers.CharField(required=False, allow_blank=True)


class MotivoPreviewSerializer(serializers.Serializer):
    """Motivo que se propondria al subsanar o rechazar, ya concatenado."""

    lineas = serializers.ListField(child=serializers.CharField())
    motivo = serializers.CharField(allow_blank=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ResponderSubsanacionSerializer(_EntradaSerializer):
    """Respuesta de la provincia: uno o varios archivos como evidencia nueva."""

    archivos = serializers.ListField(child=serializers.FileField(), allow_empty=False)
    descripcion = serializers.CharField(required=False, allow_blank=True)
    observacion_id = serializers.IntegerField(required=False, allow_null=True)


class ActualizarRegistroErroneoSerializer(_EntradaSerializer):
    """Correccion de una fila que quedo con error en la importacion.

    Las claves dependen del Excel, asi que se acepta el diccionario entero y la
    validacion real la hace `registros_erroneos_service`, que es el mismo camino
    que usa la pantalla.
    """

    datos = serializers.DictField(child=serializers.CharField(allow_blank=True))


class ReprocesoResultadoSerializer(serializers.Serializer):
    """Resumen de `registros-erroneos/reprocesar`."""

    creados = serializers.IntegerField()
    errores = serializers.IntegerField()
    errores_detalle = serializers.ListField(child=serializers.CharField())
    excluidos = serializers.IntegerField()
    excluidos_detalle = serializers.ListField(child=serializers.DictField())
    registros_restantes = serializers.IntegerField()
    alerta_resumen = serializers.CharField(allow_blank=True)

    def create(self, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Serializer de solo lectura.")


class ArchivoSerializer(_EntradaSerializer):
    """Subida generica de un archivo (cruce, respuesta de Sintys)."""

    archivo = serializers.FileField()


class ObservacionSubsanacionSerializer(_EntradaSerializer):
    tipo = serializers.CharField(max_length=50)
    detalle = serializers.CharField(max_length=500, allow_blank=True)


class RevisarLegajoSerializer(_EntradaSerializer):
    """Entrada de la revision tecnica de un legajo.

    `texto_libre` es solo el complemento: el motivo final lo compone el service
    concatenando las observaciones tecnicas del legajo. Lo que mande el cliente
    no es la fuente de verdad.
    """

    accion = serializers.ChoiceField(
        choices=["APROBAR", "RECHAZAR", "SUBSANAR", "ELIMINAR"]
    )
    texto_libre = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )
    tipo_subsanacion = serializers.CharField(
        required=False, allow_blank=True, max_length=50
    )
    observaciones = ObservacionSubsanacionSerializer(many=True, required=False)


class SubirArchivoLegajoSerializer(_EntradaSerializer):
    """Documentacion de un legajo. El slot es el campo archivo1/2/3."""

    archivo = serializers.FileField()
    slot = serializers.IntegerField(required=False, min_value=1, max_value=3)


class ConfigurarCupoSerializer(_EntradaSerializer):
    total_asignado = serializers.IntegerField(min_value=0)


class MotivoSerializer(_EntradaSerializer):
    """Motivo de una baja, suspension o reactivacion de cupo."""

    motivo = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )


class CrearPagoSerializer(_EntradaSerializer):
    provincia_id = serializers.IntegerField()
    periodo = serializers.CharField(max_length=7, required=False, allow_blank=True)


class CrearLegajosSerializer(_EntradaSerializer):
    """Alta manual de legajos desde las filas previsualizadas."""

    rows = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class RegistroErroneoSerializer(serializers.ModelSerializer):
    """Fila del Excel que no pudo importarse.

    `datos_raw` sale tal cual entro: es lo que el usuario tiene que corregir.
    """

    class Meta:
        model = RegistroErroneo
        fields = [
            "id",
            "expediente",
            "fila_excel",
            "datos_raw",
            "campo_error",
            "mensaje_error",
            "procesado",
            "creado_en",
            "procesado_en",
        ]
