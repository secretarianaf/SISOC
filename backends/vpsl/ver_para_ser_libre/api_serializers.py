"""Public JSON contract for the VPSL Front v2 API."""

from rest_framework import serializers


class ReadOnlySerializer(serializers.Serializer):
    """Contrato de salida: las escrituras usan los ModelForms compartidos."""

    def create(self, validated_data):
        raise TypeError(f"Contrato de lectura: {type(validated_data).__name__}")

    def update(self, instance, validated_data):
        raise TypeError(
            f"Contrato de lectura: {type(instance).__name__}, {type(validated_data).__name__}"
        )


class ChoiceSerializer(ReadOnlySerializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ProvinceOptionSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class SedeSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    cueanexo = serializers.CharField(allow_null=True)
    jurisdiccion = serializers.CharField()
    localidad = serializers.CharField()
    domicilio = serializers.CharField()
    telefono = serializers.CharField(allow_blank=True)
    mail = serializers.CharField(allow_blank=True)
    checklist_aprobado = serializers.BooleanField()
    mapa_query = serializers.CharField(allow_blank=True)


class ChecklistHistorySerializer(ReadOnlySerializer):
    fecha = serializers.DateTimeField()
    antes = serializers.BooleanField(allow_null=True)
    despues = serializers.BooleanField(allow_null=True)
    observacion = serializers.CharField(allow_blank=True)
    responsable = serializers.CharField(allow_blank=True)


class ChecklistSerializer(ReadOnlySerializer):
    item = serializers.CharField()
    descripcion = serializers.CharField()
    cumple = serializers.BooleanField(allow_null=True)
    observacion = serializers.CharField(allow_blank=True)
    evidencia_url = serializers.CharField(allow_blank=True)
    historial = ChecklistHistorySerializer(many=True)


class RegistroSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    dni = serializers.CharField()
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    numero_acta = serializers.CharField()
    resultado = serializers.CharField()
    cantidad_lentes = serializers.IntegerField()
    graduacion_izquierda = serializers.CharField(allow_blank=True)
    graduacion_derecha = serializers.CharField(allow_blank=True)


class LaboratorioHistorySerializer(ReadOnlySerializer):
    fecha = serializers.DateTimeField()
    antes = serializers.CharField()
    despues = serializers.CharField()
    responsable = serializers.CharField()


class LaboratorioSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    registro_id = serializers.IntegerField()
    persona = serializers.CharField()
    estado = serializers.CharField()
    siguiente = serializers.CharField(allow_null=True)
    historial = LaboratorioHistorySerializer(many=True)


class CierreHistorySerializer(ReadOnlySerializer):
    fecha = serializers.DateTimeField()
    responsable = serializers.CharField()
    atenciones = serializers.IntegerField()
    lentes = serializers.IntegerField()
    casos = serializers.IntegerField()
    acta_adjunta_url = serializers.CharField(allow_blank=True)


class CierreSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    consistente = serializers.BooleanField()
    responsable = serializers.CharField()
    atenciones = serializers.IntegerField()
    lentes = serializers.IntegerField()
    casos = serializers.IntegerField()
    observaciones = serializers.CharField(allow_blank=True)
    acta_adjunta_url = serializers.CharField(allow_blank=True)
    historial = CierreHistorySerializer(many=True)


class JornadaSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    itinerario_id = serializers.IntegerField()
    fecha = serializers.DateField()
    sede = serializers.CharField()
    localidad = serializers.CharField(allow_blank=True)
    ubicacion_url = serializers.CharField(allow_blank=True)
    latitud = serializers.CharField(allow_blank=True)
    longitud = serializers.CharField(allow_blank=True)
    vehiculos = serializers.ListField(child=serializers.CharField())
    direccion = serializers.CharField(allow_blank=True)
    estado = serializers.CharField()
    estado_label = serializers.CharField()
    referente = serializers.CharField(allow_blank=True)
    referente_telefono = serializers.CharField(allow_blank=True)
    equipo_asignado = serializers.CharField(allow_blank=True)
    observaciones = serializers.CharField(allow_blank=True)
    registros_total = serializers.IntegerField(allow_null=True)
    mapa_query = serializers.CharField(required=False)
    checklist = ChecklistSerializer(many=True, required=False)
    registros = RegistroSerializer(many=True, required=False)
    laboratorio = LaboratorioSerializer(many=True, required=False)
    cierre = CierreSerializer(required=False, allow_null=True)


class ItinerarioSerializer(ReadOnlySerializer):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    provincia = serializers.CharField()
    estado = serializers.CharField()
    estado_label = serializers.CharField()
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    referente = serializers.CharField(allow_blank=True)
    localidades = serializers.CharField(allow_blank=True)
    observaciones = serializers.CharField(allow_blank=True)
    referente_telefono = serializers.CharField(allow_blank=True)
    referente_email = serializers.CharField(allow_blank=True)
    jornadas_total = serializers.IntegerField(allow_null=True)
    jornadas = JornadaSerializer(many=True, required=False)
    carta_archivo_estado = serializers.CharField(required=False, allow_blank=True)
    carta_referencia_estado = serializers.CharField(required=False, allow_blank=True)
    carta_archivo_url = serializers.CharField(required=False, allow_blank=True)
    carta_referencia = serializers.CharField(required=False, allow_blank=True)
    subsanacion_observaciones = serializers.CharField(required=False, allow_blank=True)
    estados_evaluacion = ChoiceSerializer(many=True, required=False)


class ItinerarioPageSerializer(ReadOnlySerializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ItinerarioSerializer(many=True)
    estados = ChoiceSerializer(many=True, required=False)


class SedePageSerializer(ReadOnlySerializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = SedeSerializer(many=True)


class OptionsSerializer(ReadOnlySerializer):
    provincias = ProvinceOptionSerializer(many=True)


class SessionSerializer(ReadOnlySerializer):
    username = serializers.CharField()
    can_view_itinerarios = serializers.BooleanField()
    can_add_itinerarios = serializers.BooleanField()
    can_view_sedes = serializers.BooleanField()
    can_export = serializers.BooleanField()
    permissions = serializers.DictField(child=serializers.BooleanField())


class FormFieldSerializer(ReadOnlySerializer):
    name = serializers.CharField()
    label = serializers.CharField()
    type = serializers.CharField()
    required = serializers.BooleanField()
    disabled = serializers.BooleanField()
    help = serializers.CharField(allow_blank=True)
    value = serializers.JSONField()
    choices = ChoiceSerializer(many=True)
    min = serializers.CharField(allow_blank=True)
    max = serializers.CharField(allow_blank=True)
    step = serializers.CharField(allow_blank=True)
    graduacion_opcional = serializers.BooleanField()
    file_url = serializers.CharField(allow_blank=True)


class FormSchemaSerializer(ReadOnlySerializer):
    kind = serializers.CharField()
    fields = FormFieldSerializer(many=True)
    back = serializers.CharField(allow_blank=True)
    instrucciones = serializers.CharField(allow_blank=True)


class ActionResultSerializer(ReadOnlySerializer):
    ok = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True)
    redirect = serializers.CharField(required=False, allow_blank=True)


class LocationPreviewSerializer(ReadOnlySerializer):
    success = serializers.BooleanField()
    ubicacion_url = serializers.CharField()
    query = serializers.CharField()
    direccion = serializers.CharField(allow_blank=True)
    latitud = serializers.CharField(allow_blank=True)
    longitud = serializers.CharField(allow_blank=True)


class DeleteBreakdownSerializer(ReadOnlySerializer):
    modelo_key = serializers.CharField()
    modelo = serializers.CharField()
    cantidad = serializers.IntegerField()
    modo = serializers.ChoiceField(choices=["baja_logica", "borrado_fisico"])
    ejemplos = serializers.ListField(child=serializers.CharField())


class DeleteSummarySerializer(ReadOnlySerializer):
    operacion = serializers.ChoiceField(choices=["delete"])
    total_afectados = serializers.IntegerField()
    total_baja_logica = serializers.IntegerField()
    total_borrado_fisico = serializers.IntegerField()
    desglose_por_modelo = DeleteBreakdownSerializer(many=True)
    ejemplos_por_modelo = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class DeletePreviewSerializer(ReadOnlySerializer):
    preview = DeleteSummarySerializer()


class RenaperSerializer(ReadOnlySerializer):
    success = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True)
    data = serializers.DictField(required=False)
    datos_api = serializers.JSONField(required=False, allow_null=True)
    ciudadano_created = serializers.BooleanField(required=False)
    ciudadano_pendiente_creacion = serializers.BooleanField(required=False)


class RegistroPageSerializer(ReadOnlySerializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = RegistroSerializer(many=True)


class LaboratorioPageSerializer(ReadOnlySerializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = LaboratorioSerializer(many=True)
