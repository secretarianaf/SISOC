"""Contrato de la API de sesión que consume INET React."""

# DTOs de entrada/salida: la persistencia vive en servicios, no en Serializer.save().
# pylint: disable=abstract-method
from rest_framework import serializers


class InetDetailFieldSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField(allow_blank=True)


class InetItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    estado = serializers.CharField(allow_blank=True)
    provincia = serializers.CharField(allow_blank=True)
    localidad = serializers.CharField(allow_blank=True)
    cue = serializers.CharField(allow_blank=True)
    centro_id = serializers.IntegerField(allow_null=True)
    curso_id = serializers.IntegerField(allow_null=True)
    comision_id = serializers.IntegerField(allow_null=True)
    fecha_inicio = serializers.DateField(allow_null=True)
    fecha_fin = serializers.DateField(allow_null=True)
    detalle = InetDetailFieldSerializer(many=True)
    puede_gestionar = serializers.BooleanField()
    puede_editar = serializers.BooleanField()
    puede_eliminar = serializers.BooleanField()
    comisiones_count = serializers.IntegerField()
    inscriptos_count = serializers.IntegerField()
    clases_count = serializers.IntegerField()
    clases_realizadas = serializers.IntegerField()
    asistencia_pct = serializers.FloatField(allow_null=True)
    documento = serializers.CharField(allow_blank=True)
    email = serializers.CharField(allow_blank=True)
    telefono = serializers.CharField(allow_blank=True)
    identidad_pendiente = serializers.BooleanField()


class InetPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = InetItemSerializer(many=True)


class InetOptionSerializer(serializers.Serializer):
    value = serializers.CharField(allow_blank=True)
    label = serializers.CharField()


class InetOptionsPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = InetOptionSerializer(many=True)


class InetFormFieldSerializer(serializers.Serializer):
    name = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=[
            "text",
            "textarea",
            "number",
            "date",
            "time",
            "email",
            "checkbox",
            "select",
            "multiselect",
        ]
    )
    required = serializers.BooleanField()
    disabled = serializers.BooleanField()
    help_text = serializers.CharField(allow_blank=True)
    value = serializers.JSONField()
    options = InetOptionSerializer(many=True)
    remote_options = serializers.BooleanField()


class InetFormSerializer(serializers.Serializer):
    fields = InetFormFieldSerializer(many=True)


class InetFormInputSerializer(serializers.Serializer):
    campos = serializers.DictField(child=serializers.JSONField(allow_null=True))
    horarios = serializers.ListField(
        child=serializers.DictField(), required=False, max_length=7
    )
    contactos = serializers.ListField(
        child=serializers.DictField(), required=False, max_length=20
    )


class InetSessionSerializer(serializers.Serializer):
    username = serializers.CharField()
    nombre = serializers.CharField()
    permissions = serializers.ListField(child=serializers.CharField())
    puede_ver_planes = serializers.BooleanField()


class InetEstadoInputSerializer(serializers.Serializer):
    estado = serializers.CharField()
    observaciones = serializers.CharField(required=False, allow_blank=True)


class InetInscripcionInputSerializer(serializers.Serializer):
    ciudadano_id = serializers.IntegerField(required=False)
    ciudadano = serializers.DictField(
        child=serializers.JSONField(allow_null=True), required=False
    )
    observaciones = serializers.CharField(required=False, allow_blank=True)


class InetAsistenciaRowSerializer(serializers.Serializer):
    inscripcion_id = serializers.IntegerField()
    nombre = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True)
    presente = serializers.BooleanField(allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class InetAsistenciaSerializer(serializers.Serializer):
    sesion_id = serializers.IntegerField(read_only=True)
    fecha = serializers.DateField(read_only=True)
    filas = InetAsistenciaRowSerializer(many=True)


class InetCiudadanoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    documento = serializers.CharField(allow_blank=True)
    fecha_nacimiento = serializers.DateField(allow_null=True)


class InetCiudadanoPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = InetCiudadanoSerializer(many=True)


class InetHorarioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dia = serializers.CharField()
    hora_desde = serializers.TimeField()
    hora_hasta = serializers.TimeField()
    vigente = serializers.BooleanField()


class InetDeleteGroupSerializer(serializers.Serializer):
    modelo = serializers.CharField()
    cantidad = serializers.IntegerField()
    modo = serializers.CharField()


class InetDeletePreviewSerializer(serializers.Serializer):
    total_afectados = serializers.IntegerField()
    total_baja_logica = serializers.IntegerField()
    total_borrado_fisico = serializers.IntegerField()
    desglose_por_modelo = InetDeleteGroupSerializer(many=True)
