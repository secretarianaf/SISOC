"""Modelos de la Encuesta de satisfacción de CDI (210SatisfaccionCDI).

Encuesta pública y anónima: ninguna tabla guarda datos personales ni la IP en
claro. Las columnas de la respuesta llevan los nombres de la matriz SQL del
área; el procesamiento del área lee la vista ``v_210SatisfaccionCDI_descarga``
(migración 0058), que excluye los hashes y los datos del captcha.

Una respuesta registrada no se edita ni se borra (RF-19). Lo garantizan dos
capas: este módulo, para todo lo que pase por Django, y en MySQL los triggers
de la migración, para lo que se haga directo sobre la base.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from centrodeinfancia.encuesta_satisfaccion_schema import (
    CAMPOS_CON_NO_BRINDA,
    CAMPOS_MODIFICABLES,
    CAMPOS_PREGUNTAS,
    COMENTARIOS_MAX,
    ESCALA_FRECUENCIA,
    Canal,
    Dispositivo,
    Escala,
    EstadoRegistro,
    MotivoRechazo,
    Sala,
    SalaOrigen,
)


class RespuestaInmutableError(RuntimeError):
    """Se intentó editar o borrar el contenido de una respuesta registrada."""


def _pregunta(enunciado):
    return models.PositiveSmallIntegerField(
        choices=Escala.choices, verbose_name=enunciado
    )


def _en(campo, valores):
    return Q(**{f"{campo}__in": [int(valor) for valor in valores]})


def _restricciones_preguntas():
    restricciones = []
    for campo in CAMPOS_PREGUNTAS:
        valores = list(ESCALA_FRECUENCIA)
        if campo in CAMPOS_CON_NO_BRINDA:
            valores.append(Escala.NO_BRINDA_ALIMENTACION)
        restricciones.append(
            models.CheckConstraint(
                condition=_en(campo, valores), name=f"cdi_encuesta_{campo[:3]}_dominio"
            )
        )
    return restricciones


class EncuestaSatisfaccionToken(models.Model):
    """Token de un solo uso: se emite al abrir el formulario (vigencia 60 min).

    Solo se guarda el hash SHA-256; el token en claro lo tiene el navegador.
    """

    token_hash = models.CharField(max_length=64, unique=True)
    emitido_en = models.DateTimeField()
    expira_en = models.DateTimeField(db_index=True)
    usado_en = models.DateTimeField(null=True, blank=True)
    canal_ingreso = models.PositiveSmallIntegerField(choices=Canal.choices)
    ip_hash = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = "Encuesta de satisfacción CDI - token"
        verbose_name_plural = "Encuesta de satisfacción CDI - tokens"
        constraints = [
            models.CheckConstraint(
                condition=_en("canal_ingreso", Canal.values),
                name="cdi_encuesta_token_canal_dominio",
            ),
        ]

    def __str__(self):
        return f"Token {self.token_hash[:8]}"


class EncuestaSatisfaccionRespuestaQuerySet(models.QuerySet):
    def delete(self):
        raise RespuestaInmutableError(
            "Las respuestas de la encuesta no se eliminan; use la anulación lógica."
        )

    def update(self, **kwargs):
        prohibidos = set(kwargs) - CAMPOS_MODIFICABLES
        if prohibidos:
            raise RespuestaInmutableError(
                "El contenido de una respuesta no puede modificarse: "
                + ", ".join(sorted(prohibidos))
            )
        if kwargs.get("ip_hash") is not None:
            raise RespuestaInmutableError("ip_hash solo puede purgarse (NULL).")
        kwargs.setdefault("updated_at", timezone.now())
        return super().update(**kwargs)


class EncuestaSatisfaccionRespuesta(models.Model):
    """Una fila por encuesta enviada (tabla 210SatisfaccionCDI del área).

    Jurisdicción, departamento, institución y código son una copia del CDI al
    momento del envío: la respuesta conserva cómo se llamaba y dónde estaba el
    centro aunque el legajo cambie después.
    """

    # Identificación y control
    uuid_respuesta = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    version_instrumento = models.CharField(max_length=10)
    canal_ingreso = models.PositiveSmallIntegerField(choices=Canal.choices)

    # Espacio temporal
    centro = models.ForeignKey(
        "centrodeinfancia.CentroDeInfancia",
        on_delete=models.PROTECT,
        related_name="encuestas_satisfaccion",
        db_column="cdi_id",
    )
    jurisdiccion = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    institucion = models.CharField(max_length=255)
    codigo_institucion = models.CharField(max_length=32)
    sala = models.PositiveSmallIntegerField(choices=Sala.choices)
    sala_origen = models.PositiveSmallIntegerField(choices=SalaOrigen.choices)
    fecha_carga = models.DateTimeField()

    # P01 a P15
    p01_informacion_avances = _pregunta("P01. Información sobre los avances")
    p02_recomendaciones_hogar = _pregunta("P02. Recomendaciones para el hogar")
    p03_escucha_respeto = _pregunta("P03. Escucha y respeto")
    p04_respeto_cultura = _pregunta("P04. Respeto por la cultura familiar")
    p05_comodidad_dudas = _pregunta("P05. Comodidad para consultar dudas")
    p06_ingreso_alegria = _pregunta("P06. Ingreso con alegría")
    p07_deteccion_malestar = _pregunta("P07. Detección de malestar")
    p08_seguridad_proteccion = _pregunta("P08. Seguridad y protección")
    p09_confianza_educadora = _pregunta("P09. Confianza con la educadora")
    p10_participacion_juegos = _pregunta("P10. Participación en los juegos")
    p11_materiales_adecuados = _pregunta("P11. Materiales adecuados")
    p12_limpieza_orden = _pregunta("P12. Limpieza y orden")
    p13_alimentacion = _pregunta("P13. Alimentación")
    p14_medidas_seguridad = _pregunta("P14. Medidas de seguridad")
    p15_horario_adecuado = _pregunta("P15. Horario adecuado")

    comentarios = models.CharField(max_length=COMENTARIOS_MAX, null=True, blank=True)

    # Auditoría y seguridad
    ts_inicio = models.DateTimeField()
    ts_envio = models.DateTimeField()
    duracion_seg = models.PositiveIntegerField(null=True, blank=True)
    token = models.OneToOneField(
        EncuestaSatisfaccionToken,
        on_delete=models.PROTECT,
        related_name="respuesta",
    )
    ip_hash = models.CharField(max_length=64, null=True, blank=True)
    captcha_proveedor = models.CharField(max_length=20)
    captcha_score = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True
    )
    dispositivo_tipo = models.PositiveSmallIntegerField(choices=Dispositivo.choices)
    app_version = models.CharField(max_length=20)
    estado_registro = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices, default=EstadoRegistro.VALIDO
    )
    motivo_anulacion = models.CharField(max_length=255, null=True, blank=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    hash_integridad = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EncuestaSatisfaccionRespuestaQuerySet.as_manager()

    class Meta:
        verbose_name = "Encuesta de satisfacción CDI - respuesta"
        verbose_name_plural = "Encuesta de satisfacción CDI - respuestas"
        indexes = [
            models.Index(
                fields=["centro", "fecha_carga"], name="cdi_encuesta_cdi_fecha_idx"
            ),
            models.Index(
                fields=["jurisdiccion", "departamento"],
                name="cdi_encuesta_juris_depto_idx",
            ),
            models.Index(fields=["fecha_carga"], name="cdi_encuesta_fecha_idx"),
            models.Index(fields=["ip_hash", "ts_envio"], name="cdi_encuesta_ip_idx"),
        ]
        constraints = [
            *_restricciones_preguntas(),
            models.CheckConstraint(
                condition=_en("canal_ingreso", Canal.values),
                name="cdi_encuesta_canal_dominio",
            ),
            models.CheckConstraint(
                condition=_en("sala", Sala.values), name="cdi_encuesta_sala_dominio"
            ),
            models.CheckConstraint(
                condition=_en("sala_origen", SalaOrigen.values),
                name="cdi_encuesta_sala_origen_dominio",
            ),
            models.CheckConstraint(
                condition=_en("dispositivo_tipo", Dispositivo.values),
                name="cdi_encuesta_dispositivo_dominio",
            ),
            models.CheckConstraint(
                condition=_en("estado_registro", EstadoRegistro.values),
                name="cdi_encuesta_estado_dominio",
            ),
            models.CheckConstraint(
                condition=Q(ts_envio__gte=models.F("ts_inicio")),
                name="cdi_encuesta_tiempos",
            ),
            models.CheckConstraint(
                condition=Q(estado_registro=EstadoRegistro.VALIDO)
                | Q(
                    motivo_anulacion__isnull=False,
                    anulado_por__isnull=False,
                    fecha_anulacion__isnull=False,
                ),
                name="cdi_encuesta_anulacion_completa",
            ),
            models.CheckConstraint(
                condition=Q(captcha_score__isnull=True)
                | Q(captcha_score__gte=0, captcha_score__lte=1),
                name="cdi_encuesta_captcha_score",
            ),
        ]

    def __str__(self):
        return f"Encuesta {self.comprobante} - CDI {self.centro_id}"

    @property
    def comprobante(self):
        """Código de 8 caracteres que ve la familia (RF-18)."""
        return self.uuid_respuesta.hex[:8]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            update_fields = kwargs.get("update_fields")
            if update_fields is None or set(update_fields) - CAMPOS_MODIFICABLES:
                raise RespuestaInmutableError(
                    "El contenido de una respuesta no puede modificarse; "
                    "use la anulación lógica."
                )
            if "ip_hash" in update_fields and self.ip_hash is not None:
                raise RespuestaInmutableError("ip_hash solo puede purgarse (NULL).")
            kwargs["update_fields"] = {*update_fields, "updated_at"}
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RespuestaInmutableError(
            "Las respuestas de la encuesta no se eliminan; use la anulación lógica."
        )


class EncuestaSatisfaccionRechazo(models.Model):
    """Envío rechazado (RF-20): sin las respuestas ni datos personales.

    ``cdi_id`` es el valor que mandó el navegador, sin clave foránea: un
    rechazo puede deberse justamente a un CDI inexistente.
    """

    ts = models.DateTimeField(db_index=True)
    motivo = models.PositiveSmallIntegerField(choices=MotivoRechazo.choices)
    cdi_id = models.PositiveIntegerField(null=True, blank=True)
    canal_ingreso = models.PositiveSmallIntegerField(
        choices=Canal.choices, null=True, blank=True
    )
    ip_hash = models.CharField(max_length=64, null=True, blank=True)
    detalle = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Encuesta de satisfacción CDI - rechazo"
        verbose_name_plural = "Encuesta de satisfacción CDI - rechazos"
        constraints = [
            models.CheckConstraint(
                condition=_en("motivo", MotivoRechazo.values),
                name="cdi_encuesta_rechazo_motivo_dominio",
            ),
        ]

    def __str__(self):
        return f"Rechazo {self.get_motivo_display()} ({self.ts:%Y-%m-%d %H:%M})"
