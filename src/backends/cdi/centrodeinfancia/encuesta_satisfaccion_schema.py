"""Esquema de la Encuesta de satisfacción de CDI (instrumento 210SatisfaccionCDI).

Fuente: especificación v1.3 del área (PFPI / SIMEPI) y sus respuestas del
27/11/2026. Los códigos numéricos son el contrato con el procesamiento del
área: salen tal cual en la vista ``v_210SatisfaccionCDI_descarga``. Cambiar un
código o una pregunta es una versión nueva del instrumento (RF-28), no una
edición de la anterior.

Las etiquetas viven acá y no en tablas de catálogo: la vista las resuelve con
``CASE`` en la migración, así que cambiar una etiqueta pide una migración nueva.
"""

from django.db import models

VERSION_INSTRUMENTO = "1.0"


class Canal(models.IntegerChoices):
    QR = 1, "QR"
    URL = 2, "URL acortada"
    SIN_IDENTIFICAR = 9, "Sin identificar"


class Sala(models.IntegerChoices):
    """Salas de la nómina del CDI (respuesta del área, punto 4)."""

    MENOS_DE_UN_ANO = 1, "Menos de un año"
    UN_ANO = 2, "1 año"
    DOS_ANOS = 3, "2 años"
    TRES_ANOS = 4, "3 años"
    CUATRO_ANOS = 5, "4 años"
    MULTIEDAD = 6, "Multiedad"


# Clave de sala de la ficha de nómina (``NominaCentroInfancia.sala``) -> código
# de la encuesta. Solo las claves del formulario de nómina: los valores libres
# heredados de cargas viejas no ofrecen sala.
SALA_DESDE_NOMINA = {
    "menos_de_un_ano": Sala.MENOS_DE_UN_ANO,
    "un_ano": Sala.UN_ANO,
    "dos_anos": Sala.DOS_ANOS,
    "tres_anos": Sala.TRES_ANOS,
    "cuatro_anos": Sala.CUATRO_ANOS,
    "multiedad": Sala.MULTIEDAD,
}


class SalaOrigen(models.IntegerChoices):
    """De dónde salió la lista de salas que se le ofreció a la familia."""

    NOMINA = 1, "Salas de la nómina del CDI"
    LISTA_COMPLETA = 2, "Lista completa (CDI sin nómina activa)"


class Escala(models.IntegerChoices):
    NUNCA = 1, "Nunca"
    CASI_NUNCA = 2, "Casi nunca"
    A_VECES = 3, "A veces"
    CASI_SIEMPRE = 4, "Casi siempre"
    SIEMPRE = 5, "Siempre"
    NO_BRINDA_ALIMENTACION = 9, "No brinda alimentación"


ESCALA_FRECUENCIA = (
    Escala.NUNCA,
    Escala.CASI_NUNCA,
    Escala.A_VECES,
    Escala.CASI_SIEMPRE,
    Escala.SIEMPRE,
)


class Dispositivo(models.IntegerChoices):
    MOVIL = 1, "Móvil"
    TABLET = 2, "Tablet"
    ESCRITORIO = 3, "Escritorio"
    SIN_IDENTIFICAR = 9, "Sin identificar"


class EstadoRegistro(models.IntegerChoices):
    VALIDO = 1, "Válido"
    ANULADO = 2, "Anulado por auditoría"


class MotivoRechazo(models.IntegerChoices):
    CAPTCHA = 1, "Captcha no superado"
    LIMITE_IP = 2, "Límite de envíos por IP superado"
    TOKEN = 3, "Token inválido, vencido o ya utilizado"
    VALIDACION = 4, "Error de validación de datos"
    CDI_NO_DISPONIBLE = 5, "CDI inexistente o dado de baja"


VINCULO = "Vínculo y Comunicación"
BIENESTAR = "Bienestar Infantil"
ENTORNO = "Entorno y Gestión"

# (código, campo de la tabla, sección, enunciado, admite "No brinda alimentación")
PREGUNTAS = (
    (
        "P01",
        "p01_informacion_avances",
        VINCULO,
        "¿La educadora le brinda información clara sobre los avances de su hijo?",
        False,
    ),
    (
        "P02",
        "p02_recomendaciones_hogar",
        VINCULO,
        "¿Recibe recomendaciones útiles para jugar o aprender en casa?",
        False,
    ),
    (
        "P03",
        "p03_escucha_respeto",
        VINCULO,
        "¿Siente que el personal lo escucha con atención y respeto?",
        False,
    ),
    (
        "P04",
        "p04_respeto_cultura",
        VINCULO,
        "¿El centro respeta las costumbres y cultura de su familia?",
        False,
    ),
    (
        "P05",
        "p05_comodidad_dudas",
        VINCULO,
        "¿Se siente cómodo al expresar sus dudas sobre la crianza?",
        False,
    ),
    (
        "P06",
        "p06_ingreso_alegria",
        BIENESTAR,
        "¿Su hijo entra al centro con alegría o tranquilidad?",
        False,
    ),
    (
        "P07",
        "p07_deteccion_malestar",
        BIENESTAR,
        "¿El personal nota rápido si su hijo está triste o tiene dolor?",
        False,
    ),
    (
        "P08",
        "p08_seguridad_proteccion",
        BIENESTAR,
        "¿Siente que su hijo está seguro y protegido en este lugar?",
        False,
    ),
    (
        "P09",
        "p09_confianza_educadora",
        BIENESTAR,
        "¿Nota que su hijo ha desarrollado confianza con su educadora?",
        False,
    ),
    (
        "P10",
        "p10_participacion_juegos",
        BIENESTAR,
        "¿Su hijo participa con entusiasmo en los juegos propuestos?",
        False,
    ),
    (
        "P11",
        "p11_materiales_adecuados",
        ENTORNO,
        "¿Los juguetes y materiales son variados y adecuados para su edad?",
        False,
    ),
    (
        "P12",
        "p12_limpieza_orden",
        ENTORNO,
        "¿Las salas y baños están siempre limpios y ordenados?",
        False,
    ),
    (
        "P13",
        "p13_alimentacion",
        ENTORNO,
        "¿La alimentación que recibe su hijo es suficiente y de calidad?",
        True,
    ),
    (
        "P14",
        "p14_medidas_seguridad",
        ENTORNO,
        "¿Las instalaciones cuentan con medidas de seguridad para evitar accidentes?",
        False,
    ),
    (
        "P15",
        "p15_horario_adecuado",
        ENTORNO,
        "¿El horario del centro se adapta a las necesidades de su familia?",
        False,
    ),
)

CAMPOS_PREGUNTAS = tuple(campo for _, campo, _, _, _ in PREGUNTAS)
CAMPOS_CON_NO_BRINDA = tuple(campo for _, campo, _, _, admite in PREGUNTAS if admite)

COMENTARIOS_MAX = 1000

# Lo único que puede cambiar en una respuesta ya registrada: la anulación lógica
# (próxima etapa) y la purga de ``ip_hash`` a los 30 días. El resto es inmutable
# (RF-19), en la aplicación y, en MySQL, también por trigger.
CAMPOS_MODIFICABLES = frozenset(
    {
        "estado_registro",
        "motivo_anulacion",
        "anulado_por",
        "anulado_por_id",
        "fecha_anulacion",
        "ip_hash",
        "updated_at",
    }
)
