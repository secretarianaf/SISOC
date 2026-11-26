import re
from urllib.parse import urlparse, urlunparse

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.db.models.functions import Cast, Concat
from django.urls import reverse

from core.permissions.registry import build_legacy_permission_code

ADMIN_DASHBOARD_PERMISSION_CODES = (
    "auth.role_admin",
    "auth.role_administrador",
    "auth.role_superadmin",
)
LOOKER_STUDIO_HOSTS = {
    "datastudio.google.com",
    "lookerstudio.google.com",
}
# Ruta absoluta dentro de SISOC: empieza con "/" pero no con "//" ni "/\", que
# el navegador interpreta como otro sitio, y no lleva espacios.
RUTA_INTERNA_RE = re.compile(r"^/(?![/\\])[^\s\\]*$")


def validar_ruta_interna(valor):
    if valor and not RUTA_INTERNA_RE.match(valor):
        raise ValidationError(
            "Usá una ruta de SISOC que empiece con /, por ejemplo /celiaquia/tablero/."
        )


class Dashboard(models.Model):
    """
    Modelo para almacenar información de dashboard.
    """

    llave = models.CharField(
        max_length=255,
        unique=True,
        primary_key=True,
        help_text="Llave única para identificar el registro en el dashboard.",
    )
    cantidad = models.BigIntegerField(
        default=0, help_text="Cantidad asociada al registro en el dashboard."
    )

    def aumentar_cantidad(self, cantidad: int = 1):
        self.cantidad += cantidad
        self.save()


class Tablero(models.Model):
    """
    Modelo para administrar tableros embebidos y sus permisos.
    """

    nombre = models.CharField(
        max_length=255,
        help_text="Nombre visible en el menú y el encabezado del tablero.",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Identificador único para la URL del tablero.",
    )
    grupo_menu = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Nombre del programa/grupo bajo el que se agrupa en el menú de "
            "Tableros. Vacío = aparece como enlace directo (sin submenú). "
            "No confundir con los grupos de permisos."
        ),
    )
    url = models.URLField(
        blank=True,
        help_text="URL embebida del tablero (Power BI u otra herramienta).",
    )
    ruta_interna = models.CharField(
        max_length=255,
        blank=True,
        default="",
        validators=[validar_ruta_interna],
        help_text=(
            "Ruta de una pantalla de SISOC (por ejemplo /celiaquia/tablero/). "
            "Si está cargada, el menú lleva a esa pantalla en lugar de embeber "
            "la URL."
        ),
    )
    mensaje_construccion = models.TextField(
        blank=True,
        help_text="Mensaje a mostrar cuando el tablero no tiene URL.",
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden de aparición en el menú de tableros.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Desactiva la ficha del catálogo; las rutas internas tienen sus propios controles.",
    )
    visible_menu = models.BooleanField(
        default=True,
        verbose_name="Visible en el menú",
        help_text="Ocultar el enlace no cambia los permisos ni bloquea la ruta directa.",
    )
    permisos = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Listado de permisos con acceso al tablero (app_label.codename). "
            "Se aceptan nombres de grupo legacy por compatibilidad."
        ),
    )

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "tablero"
        verbose_name_plural = "tableros"

    def __str__(self):
        return self.nombre

    @property
    def titulo(self):
        return f"Tablero {self.nombre}"

    def get_absolute_url(self):
        if self.ruta_interna:
            return self.ruta_interna
        return reverse("dashboard_tablero", kwargs={"slug": self.slug})

    @staticmethod
    def _strip_looker_user_prefix(path):
        return re.sub(r"^/u/\d+/", "/", path or "")

    def usa_url_compartible_looker_studio(self):
        if not self.url:
            return False

        parsed_url = urlparse(self.url)
        hostname = (parsed_url.hostname or "").lower()
        if hostname not in LOOKER_STUDIO_HOSTS:
            return False

        normalized_path = self._strip_looker_user_prefix(parsed_url.path)
        return normalized_path.startswith("/reporting/")

    def get_embed_url(self):
        if not self.url:
            return ""

        parsed_url = urlparse(self.url)
        hostname = (parsed_url.hostname or "").lower()
        if hostname not in LOOKER_STUDIO_HOSTS:
            return self.url

        normalized_path = self._strip_looker_user_prefix(parsed_url.path)
        if normalized_path.startswith("/embed/reporting/"):
            if normalized_path == parsed_url.path:
                return self.url
            return urlunparse(parsed_url._replace(path=normalized_path))

        if not normalized_path.startswith("/reporting/"):
            return self.url

        return urlunparse(parsed_url._replace(path=f"/embed{normalized_path}"))

    @staticmethod
    def permission_codes_de_usuario(user):
        if not user or not user.is_authenticated:
            return []
        if hasattr(user, "cached_permission_codes"):
            return list(user.cached_permission_codes)
        permission_codes = list(user.get_all_permissions())
        user.cached_permission_codes = set(permission_codes)
        return permission_codes

    def _normalized_required_permissions(self):
        if not self.permisos:
            return []

        normalized = []
        for raw_value in self.permisos:
            raw_text = str(raw_value or "").strip()
            if not raw_text:
                continue
            if "." in raw_text:
                normalized.append(raw_text)
            else:
                normalized.append(build_legacy_permission_code(raw_text))
        return normalized

    def tiene_acceso_para_permisos(self, permission_codes):
        required = self._normalized_required_permissions()
        if not required:
            return False
        return any(permission in permission_codes for permission in required)

    def usuario_puede_ver(self, user, *, configuracion=...):
        if not user or not user.is_authenticated:
            return False
        from dashboard.services.politicas import (  # pylint: disable=import-outside-toplevel
            visibilidad_tablero_interno,
        )

        decision = visibilidad_tablero_interno(user, self, configuracion=configuracion)
        if decision is not None:
            return decision
        if user.is_superuser:
            return True

        permission_codes = self.permission_codes_de_usuario(user)
        if any(code in permission_codes for code in ADMIN_DASHBOARD_PERMISSION_CODES):
            return True
        return self.tiene_acceso_para_permisos(permission_codes)

    def get_mensaje_construccion(self):
        if self.mensaje_construccion:
            return self.mensaje_construccion
        return f"El tablero de {self.nombre} estará disponible próximamente."


# Audiencias y concesiones nuevas no alteran la política legacy por sí solas.
class ConfiguracionTableroInternoQuerySet(models.QuerySet):
    def delete(self):
        with transaction.atomic(using=self.db):
            # Pylint infiere incorrectamente el método dinámico del QuerySet.
            # pylint: disable-next=not-callable
            bloqueadas = self.select_for_update()
            activas = list(bloqueadas.values_list("activa", flat=True))
            if any(activas):
                raise ValidationError("No se puede eliminar una política activa.")
            return super().delete()


class ConfiguracionTableroInterno(models.Model):
    codigo = models.CharField(max_length=64, unique=True)
    tablero = models.OneToOneField(
        Tablero, on_delete=models.PROTECT, related_name="configuracion_interna"
    )
    activa = models.BooleanField(default=False)
    objects = ConfiguracionTableroInternoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(codigo="progresar_curso"),
                name="dashboard_interno_codigo_valido",
            )
        ]

    def delete(self, using=None, keep_parents=False):
        resultado = (
            type(self)
            .objects.using(using or self._state.db)
            .filter(pk=self.pk)
            .delete()
        )
        self.pk = None
        return resultado


class AudienciaTableros(models.Model):
    nombre = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.nombre

    def agregar_miembro(self, usuario):
        miembro, _ = MiembroAudienciaTableros.objects.get_or_create(
            audiencia=self, usuario=usuario
        )
        return miembro

    def quitar_miembro(self, usuario):
        return self.membresias.filter(usuario=usuario).delete()


class MiembroAudienciaTableros(models.Model):
    audiencia = models.ForeignKey(
        AudienciaTableros, on_delete=models.CASCADE, related_name="membresias"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membresias_tableros",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("audiencia", "usuario"),
                name="dashboard_audiencia_usuario_unico",
            )
        ]


class ConcesionTablero(models.Model):
    class Tipo(models.TextChoices):
        NACIONAL = "nacional", "Nacional"
        PROVINCIA = "provincia", "Provincia"
        CDI = "cdi", "CDI"

    tablero = models.ForeignKey(
        Tablero, on_delete=models.CASCADE, related_name="concesiones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="concesiones_tableros",
    )
    audiencia = models.ForeignKey(
        AudienciaTableros,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="concesiones",
    )
    tipo = models.CharField(max_length=16, choices=Tipo.choices)
    provincia = models.ForeignKey(
        "core.Provincia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    # La identidad CDI se valida mediante el contrato de la vertical antes de activar una ruta.
    cdi_id = models.PositiveBigIntegerField(null=True, blank=True)
    alcance_key = models.CharField(max_length=64, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(usuario__isnull=False, audiencia__isnull=True)
                    | Q(usuario__isnull=True, audiencia__isnull=False)
                ),
                name="dashboard_concesion_sujeto_unico",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        tipo="nacional",
                        provincia__isnull=True,
                        cdi_id__isnull=True,
                        alcance_key="nacional",
                    )
                    | Q(
                        tipo="provincia",
                        provincia__isnull=False,
                        cdi_id__isnull=True,
                        alcance_key=Concat(
                            models.Value("provincia:"),
                            Cast("provincia_id", models.CharField()),
                        ),
                    )
                    | Q(
                        tipo="cdi",
                        provincia__isnull=True,
                        cdi_id__isnull=False,
                        cdi_id__gt=0,
                        alcance_key=Concat(
                            models.Value("cdi:"), Cast("cdi_id", models.CharField())
                        ),
                    )
                ),
                name="dashboard_concesion_alcance_valido",
            ),
            models.UniqueConstraint(
                fields=("tablero", "usuario", "alcance_key"),
                name="dashboard_concesion_usuario_unica",
            ),
            models.UniqueConstraint(
                fields=("tablero", "audiencia", "alcance_key"),
                name="dashboard_concesion_audiencia_unica",
            ),
        ]

    def clean(self):
        super().clean()
        if bool(self.usuario_id) == bool(self.audiencia_id):
            raise ValidationError("Seleccione un usuario o una audiencia, no ambos.")
        if self.tipo == self.Tipo.NACIONAL:
            if self.provincia_id is not None or self.cdi_id is not None:
                raise ValidationError("El alcance nacional no admite un territorio.")
            self.alcance_key = "nacional"
        elif self.tipo == self.Tipo.PROVINCIA:
            if not self.provincia_id or self.cdi_id is not None:
                raise ValidationError("Seleccione una provincia para este alcance.")
            self.alcance_key = f"provincia:{self.provincia_id}"
        elif self.tipo == self.Tipo.CDI:
            if (
                self.provincia_id is not None
                or not isinstance(self.cdi_id, int)
                or self.cdi_id <= 0
            ):
                raise ValidationError("Seleccione un CDI válido para este alcance.")
            self.alcance_key = f"cdi:{self.cdi_id}"
        else:
            raise ValidationError("Seleccione un tipo de alcance válido.")

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is not None:
            raise ValueError("Las concesiones deben guardarse completas.")
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Tablero Becas Progresar · Curso obligatorio
# ---------------------------------------------------------------------------
# Los datos de Progresar no viven en SISOC: el padrón y el curso (WordPress de FCH)
# los trae una carga diaria del equipo de Datos a tablas `bi_` de la base. SISOC solo
# las lee. Las mantiene el equipo de Datos (no se crean ni migran desde acá).

PERMISO_TABLERO_PROGRESAR_CURSO = "dashboard.view_tablero_progresar_curso"
# Ver todo el país (coordinación). Sin esta llave, el usuario ve solo las provincias
# de su alcance territorial: un alta incompleta no muestra datos de más.
PERMISO_TABLERO_PROGRESAR_CURSO_NACIONAL = (
    "dashboard.view_tablero_progresar_curso_nacional"
)


class ProgresarCursoResumen(models.Model):
    """Titulares por provincia, línea, estado del curso, género y edad (agregado)."""

    provincia_codigo = models.PositiveSmallIntegerField(
        help_text="Código INDEC de la provincia."
    )
    provincia = models.ForeignKey(
        "core.Provincia",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        related_name="+",
    )
    linea = models.CharField(max_length=30)
    estado_curso = models.CharField(max_length=25)
    genero_codigo = models.CharField(max_length=1, null=True)
    rango_edad = models.CharField(max_length=10)
    tramo_inactividad = models.CharField(max_length=10, null=True)
    tramo_aprobacion = models.CharField(max_length=15, null=True)
    titulares = models.PositiveIntegerField()
    suma_edad = models.PositiveIntegerField(null=True)
    casos_edad = models.PositiveIntegerField()
    fecha_carga = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "bi_progresar_curso_obligatorio_resumen"
        default_permissions = ()
        permissions = [
            (
                "view_tablero_progresar_curso",
                "Puede ver el Tablero Becas Progresar · Curso obligatorio",
            ),
            (
                "view_tablero_progresar_curso_nacional",
                "Puede ver todo el país en el Tablero Becas Progresar · Curso obligatorio",
            ),
        ]
        verbose_name = "resumen del tablero Progresar curso obligatorio"


class ProgresarCursoEvolucion(models.Model):
    """Inscriptos y aprobados por día, provincia, línea y género (agregado)."""

    fecha = models.DateField()
    provincia_codigo = models.PositiveSmallIntegerField(
        help_text="Código INDEC de la provincia."
    )
    provincia = models.ForeignKey(
        "core.Provincia",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        related_name="+",
    )
    linea = models.CharField(max_length=30)
    genero_codigo = models.CharField(max_length=1, null=True)
    inscriptos = models.PositiveIntegerField()
    aprobados = models.PositiveIntegerField()
    fecha_carga = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "bi_progresar_curso_obligatorio_evolucion"
        default_permissions = ()
        verbose_name = "evolución del tablero Progresar curso obligatorio"
