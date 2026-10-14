"""Modelos de Inspecciones escolares (PWA Sisoc Inspecciones).

Contrato con la app: docs del repo de la PWA (``CONTRATO-API-INSPECCIONES.md``)
y ``docs/registro/decisiones/2026-10-14-inspecciones-escolares-backend.md``.

- ``Inspeccion`` es el borrador del teléfono, identificado por el ``uuid`` que
  genera la app. Al cerrarse queda ``finalizada`` y nace su ``Acta``.
- ``Acta`` guarda una instantánea inmutable con número y hora oficial del
  servidor. El número sale de ``SecuenciaActa`` (una fila por año, bloqueada
  con ``select_for_update`` dentro de la transacción del cierre).
- Los archivos son privados (``inspecciones.storage``): no tienen URL pública.
- Los campos desnormalizados (``fecha_visita``, ``turno``, ``resultado``,
  ``escuela``, ``firma_tipo``, ``notificacion_estado``, ``es_prueba``) dejan el
  modelo listo para el dashboard de coordinación (segunda etapa).
"""

from django.conf import settings
from django.db import models

from core.soft_delete import SoftDeleteModelMixin
from inspecciones.storage import (
    almacenamiento_privado,
    ruta_archivo_notificacion,
    ruta_imagen,
    ruta_pdf,
)


class Escuela(SoftDeleteModelMixin, models.Model):
    """Catálogo de escuelas. ``codigo`` es la clave que viaja como ``id``.

    El Cueanexo (9 dígitos, con ceros a la izquierda) es la clave de las
    escuelas nuevas: se guarda en ``codigo`` (único, el ``id`` de la API) y en
    ``cue`` (lo que la API expone como ``cue``). ``codigo`` no cambia después
    del alta porque la app lo guarda en sus borradores.

    ``localidad`` y ``distrito`` son el texto que lee la app: salen de la
    localidad vinculada de SISOC (``localidad_vinculada`` y su municipio) y,
    si no hay vínculo, del texto original. Los mantiene
    ``inspecciones.services.geografia.textos_de_ubicacion``.
    """

    class MotivoRevision(models.TextChoices):
        LOCALIDAD_REPETIDA = (
            "localidad_repetida",
            "La localidad existe en 2 o más municipios",
        )
        LOCALIDAD_INEXISTENTE = (
            "localidad_inexistente",
            "La localidad no está en la base de SISOC",
        )
        MAIL_INVALIDO = "mail_invalido", "Mail inválido"

    codigo = models.CharField(
        max_length=40,
        unique=True,
        help_text="Clave del catálogo (el Cueanexo). Es el id de la API.",
    )
    nombre = models.CharField(max_length=255)
    # Texto, no número: el Cueanexo conserva los ceros a la izquierda.
    cue = models.CharField(
        max_length=20, blank=True, db_index=True, help_text="Cueanexo (9 dígitos)."
    )
    provincia = models.ForeignKey(
        "core.Provincia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    localidad_vinculada = models.ForeignKey(
        "core.Localidad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Localidad de SISOC. Vacía si no se pudo resolver.",
    )
    distrito = models.CharField(max_length=120, blank=True, db_index=True)
    localidad = models.CharField(max_length=255, blank=True)
    domicilio = models.CharField(max_length=255, blank=True)
    cp = models.CharField("C. P.", max_length=20, blank=True)
    telefono = models.CharField("teléfono", max_length=255, blank=True)
    # Texto libre: la importación guarda el mail tal cual aunque sea inválido.
    mail = models.CharField(max_length=255, blank=True)
    nivel = models.CharField(max_length=60, blank=True)
    jurisdiccion_original = models.CharField(
        max_length=120, blank=True, help_text="Jurisdicción tal como vino del archivo."
    )
    localidad_original = models.CharField(
        max_length=255, blank=True, help_text="Localidad tal como vino del archivo."
    )
    a_revisar = models.BooleanField(default=False, db_index=True)
    motivos_revision = models.JSONField(default=list, blank=True)
    creada_at = models.DateTimeField(auto_now_add=True)
    actualizada_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "Escuela"
        verbose_name_plural = "Escuelas"
        indexes = [models.Index(fields=["nombre"], name="insp_escuela_nombre_idx")]
        permissions = [
            (
                "gestionar_inspecciones",
                "Puede importar escuelas y asignaciones de Inspecciones escolares",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.cueanexo})"

    @property
    def cueanexo(self):
        return self.cue or self.codigo

    @property
    def motivos_revision_display(self):
        etiquetas = dict(self.MotivoRevision.choices)
        return [etiquetas.get(m, m) for m in self.motivos_revision or []]


class AsignacionEscuela(SoftDeleteModelMixin, models.Model):
    """Escuela asignada a un inspector para una jornada."""

    escuela = models.ForeignKey(
        Escuela, on_delete=models.PROTECT, related_name="asignaciones"
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asignaciones_inspeccion",
    )
    fecha = models.DateField(db_index=True, help_text="Jornada de la visita.")
    creada_at = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ("fecha", "escuela__nombre")
        verbose_name = "Asignación de escuela"
        verbose_name_plural = "Asignaciones de escuelas"
        constraints = [
            models.UniqueConstraint(
                fields=["escuela", "inspector", "fecha"],
                name="uniq_inspecciones_asignacion_jornada",
            )
        ]

    def __str__(self):
        return f"{self.escuela} - {self.inspector} ({self.fecha})"


class Inspeccion(SoftDeleteModelMixin, models.Model):
    """Inspección de una escuela: borrador editable y luego finalizada."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        FINALIZADA = "finalizada", "Finalizada"

    uuid = models.UUIDField(unique=True, help_text="Identificador que genera la app.")
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspecciones_escolares",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR, db_index=True
    )
    revision = models.PositiveIntegerField(
        default=0, help_text="Mayor revisión recibida del cliente (0: sin datos)."
    )
    formulario_version = models.CharField(max_length=20, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    escuela = models.ForeignKey(
        Escuela,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inspecciones",
    )
    escuela_carga_manual = models.BooleanField(
        default=False, help_text="Escuela fuera del catálogo, marcada para revisión."
    )
    fecha_visita = models.DateField(null=True, blank=True, db_index=True)
    turno = models.CharField(max_length=20, blank=True)
    resultado = models.CharField(max_length=20, blank=True)
    reemplaza = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reemplazada_por",
        help_text="Inspección anterior que esta corrige (segunda etapa).",
    )
    creada_cliente_at = models.DateTimeField(null=True, blank=True)
    actualizada_cliente_at = models.DateTimeField(null=True, blank=True)
    creada_at = models.DateTimeField(auto_now_add=True)
    guardada_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Inspección"
        verbose_name_plural = "Inspecciones"
        indexes = [
            models.Index(
                fields=["inspector", "estado"], name="insp_inspector_estado_idx"
            ),
            models.Index(
                fields=["escuela", "fecha_visita"], name="insp_escuela_fecha_idx"
            ),
        ]

    def __str__(self):
        return f"Inspección {self.uuid} ({self.get_estado_display()})"


class ImagenInspeccion(models.Model):
    """Foto del ingreso, imagen adicional o firma en pantalla."""

    class Tipo(models.TextChoices):
        INGRESO = "ingreso", "Foto del ingreso"
        ADICIONAL = "adicional", "Imagen adicional"
        FIRMA = "firma", "Firma"

    uuid = models.UUIDField(unique=True)
    inspeccion = models.ForeignKey(
        Inspeccion, on_delete=models.PROTECT, related_name="imagenes"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    archivo = models.FileField(
        storage=almacenamiento_privado, upload_to=ruta_imagen, max_length=255
    )
    mime = models.CharField(max_length=30)
    tamano = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    descripcion = models.TextField(blank=True)
    capturada_at = models.DateTimeField(
        null=True, blank=True, help_text="Fecha de captura informada; nunca se inventa."
    )
    subida_at = models.DateTimeField(auto_now_add=True)
    subida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        verbose_name = "Imagen de inspección"
        verbose_name_plural = "Imágenes de inspección"

    def __str__(self):
        return f"{self.get_tipo_display()} {self.uuid}"


class SecuenciaActa(models.Model):
    """Último número de acta emitido por año. Se bloquea al cerrar."""

    anio = models.PositiveIntegerField(primary_key=True)
    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de actas"
        verbose_name_plural = "Secuencias de actas"

    def __str__(self):
        return f"{self.anio}: {self.ultimo}"


class Acta(models.Model):
    """Acta emitida: instantánea inmutable con número y hora oficial."""

    class Estado(models.TextChoices):
        FINALIZADA = "finalizada", "Finalizada"
        ANULADA = "anulada", "Anulada"

    class EstadoNotificacion(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CARGADA = "cargada", "Cargada"

    # Lo que firmó la persona y lo que se numeró no cambia después del cierre.
    CAMPOS_INMUTABLES = (
        "inspeccion_id",
        "inspector_id",
        "numero",
        "anio",
        "secuencia",
        "cerrada_at",
        "instantanea",
        "instantanea_sha256",
    )

    inspeccion = models.OneToOneField(
        Inspeccion, on_delete=models.PROTECT, related_name="acta"
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="actas_inspeccion",
    )
    escuela = models.ForeignKey(
        Escuela,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="actas",
    )
    numero = models.CharField(max_length=20, unique=True)
    anio = models.PositiveIntegerField()
    secuencia = models.PositiveIntegerField()
    cerrada_at = models.DateTimeField(db_index=True, help_text="Hora oficial.")
    fecha_visita = models.DateField(null=True, blank=True, db_index=True)
    turno = models.CharField(max_length=20, blank=True)
    resultado = models.CharField(max_length=20, blank=True)
    firma_tipo = models.CharField(max_length=20, blank=True)
    formulario_version = models.CharField(max_length=20, blank=True)
    instantanea = models.JSONField(default=dict)
    instantanea_sha256 = models.CharField(max_length=64)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.FINALIZADA,
        db_index=True,
    )
    anulada_at = models.DateTimeField(null=True, blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    motivo_anulacion = models.TextField(blank=True)
    notificacion_estado = models.CharField(
        max_length=20,
        choices=EstadoNotificacion.choices,
        default=EstadoNotificacion.PENDIENTE,
        db_index=True,
    )
    pdf = models.FileField(
        storage=almacenamiento_privado,
        upload_to=ruta_pdf,
        max_length=255,
        null=True,
        blank=True,
    )
    pdf_sha256 = models.CharField(max_length=64, blank=True)
    pdf_subido_at = models.DateTimeField(null=True, blank=True)
    pdf_subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    es_prueba = models.BooleanField(
        default=False, help_text="Acta de prueba: fuera de los indicadores."
    )

    class Meta:
        ordering = ("-cerrada_at",)
        verbose_name = "Acta de inspección"
        verbose_name_plural = "Actas de inspección"
        constraints = [
            models.UniqueConstraint(
                fields=["anio", "secuencia"], name="uniq_inspecciones_acta_secuencia"
            )
        ]

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if self.pk:
            self._verificar_inmutables(kwargs.get("update_fields"))
        super().save(*args, **kwargs)

    def _verificar_inmutables(self, update_fields):
        campos = list(self.CAMPOS_INMUTABLES)
        if update_fields is not None:
            nombres = set(update_fields)
            campos = [
                c for c in campos if c in nombres or c.removesuffix("_id") in nombres
            ]
            if not campos:
                return
        original = type(self).objects.filter(pk=self.pk).values(*campos).first()
        if original is None:
            return
        cambiados = [c for c in campos if original[c] != getattr(self, c)]
        if cambiados:
            raise ValueError(
                "El acta es inmutable; no se puede modificar: " + ", ".join(cambiados)
            )


class NotificacionPapel(models.Model):
    """Carga de la foto de la notificación en papel, posterior al cierre.

    Versionada: una corrección es una carga nueva que ``reemplaza`` a la
    anterior, que se conserva.
    """

    class CondicionFirma(models.TextChoices):
        FIRMADA = "firmada", "Firmada"
        NEGATIVA = "negativa", "Negativa a firmar"
        SIN_RECEPTOR = "sin_receptor", "Sin receptor disponible"

    uuid = models.UUIDField(unique=True, help_text="Identificador de la carga (app).")
    acta = models.ForeignKey(
        Acta, on_delete=models.PROTECT, related_name="notificaciones"
    )
    version = models.PositiveIntegerField()
    cargada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    cargada_at = models.DateTimeField(auto_now_add=True)
    notificada_at = models.DateTimeField(help_text="Fecha y hora informadas.")
    receptor_nombre = models.CharField(max_length=200)
    receptor_cargo = models.CharField(max_length=200)
    condicion_firma = models.CharField(max_length=20, choices=CondicionFirma.choices)
    motivo = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    numero_confirmado = models.CharField(max_length=20)
    reemplaza = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="correcciones",
    )
    motivo_correccion = models.TextField(blank=True)

    class Meta:
        ordering = ("acta", "version")
        verbose_name = "Notificación en papel"
        verbose_name_plural = "Notificaciones en papel"
        constraints = [
            models.UniqueConstraint(
                fields=["acta", "version"],
                name="uniq_inspecciones_notificacion_version",
            )
        ]

    def __str__(self):
        return f"{self.acta.numero} v{self.version}"


class ArchivoNotificacion(models.Model):
    """Foto (cara o página) de una notificación en papel."""

    uuid = models.UUIDField(unique=True)
    notificacion = models.ForeignKey(
        NotificacionPapel, on_delete=models.PROTECT, related_name="archivos"
    )
    orden = models.PositiveSmallIntegerField()
    archivo = models.FileField(
        storage=almacenamiento_privado,
        upload_to=ruta_archivo_notificacion,
        max_length=255,
    )
    mime = models.CharField(max_length=30)
    tamano = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)

    class Meta:
        ordering = ("notificacion", "orden")
        verbose_name = "Archivo de notificación"
        verbose_name_plural = "Archivos de notificación"

    def __str__(self):
        return f"{self.notificacion} #{self.orden}"


class EventoInspeccion(models.Model):
    """Historial de auditoría: actor, acción y fecha."""

    class Accion(models.TextChoices):
        CREADA = "creada", "Creada"
        EDITADA = "editada", "Editada"
        IMAGEN_SUBIDA = "imagen_subida", "Imagen subida"
        IMAGEN_ELIMINADA = "imagen_eliminada", "Imagen eliminada"
        DESCARTADA = "descartada", "Borrador descartado"
        FIRMADA = "firmada", "Firmada"
        EXCEPCION_FIRMA = "excepcion_firma", "Excepción de firma registrada"
        FINALIZADA = "finalizada", "Finalizada"
        PDF_SUBIDO = "pdf_subido", "PDF subido"
        NOTIFICACION_CARGADA = "notificacion_cargada", "Notificación cargada"
        NOTIFICACION_CORREGIDA = "notificacion_corregida", "Notificación corregida"
        ANULADA = "anulada", "Anulada"

    inspeccion = models.ForeignKey(
        Inspeccion, on_delete=models.PROTECT, related_name="eventos"
    )
    acta = models.ForeignKey(
        Acta,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eventos",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    actor_nombre = models.CharField(max_length=200, blank=True)
    accion = models.CharField(max_length=40, choices=Accion.choices)
    at = models.DateTimeField(help_text="Cuándo ocurrió.")
    registrado_at = models.DateTimeField(auto_now_add=True)
    detalle = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("at", "id")
        verbose_name = "Evento de inspección"
        verbose_name_plural = "Eventos de inspección"

    def __str__(self):
        return f"{self.get_accion_display()} ({self.at})"
