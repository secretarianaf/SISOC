# pylint: disable=too-many-lines
"""Definición declarativa del Formulario de Calidad de los CDI (200_CalidadCDI).

Es la fuente única del instrumento: de acá salen los campos del modelo
(`models_formulario_calidad`), el form, el template y las reglas de visibilidad
y completitud. Cada variable SQL de la especificación es una columna con
`db_column` igual al nombre de la matriz SQL; el campo Python lleva el prefijo
`p` porque los identificadores no pueden empezar con un dígito.

Las respuestas de opción guardan sólo el número de la opción (20.3 -> 3).
"""

from __future__ import annotations

from dataclasses import dataclass

RADIO = "radio"
NUMERO = "numero"
MATRIZ_NUMERICA = "matriz_numerica"
GRILLA = "grilla"
CHECKBOX = "checkbox"

SI_NO = ("Sí", "No")


@dataclass(frozen=True)
class Condicion:
    """La pregunta se muestra si `campo` toma (o no toma) alguno de `valores`."""

    campo: str
    valores: tuple[int, ...]
    negar: bool = False

    def se_cumple(self, valor) -> bool:
        if valor in (None, ""):
            return False
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            return False
        incluido = valor in self.valores
        return not incluido if self.negar else incluido


@dataclass(frozen=True)
class Especificar:
    """Campo de texto obligatorio cuando se elige una opción puntual."""

    clave: str
    cuando: int | str  # número de opción (radio) o clave de fila (checkbox)
    etiqueta: str = "Especificar"


@dataclass(frozen=True)
class Pregunta:
    numero: int
    texto: str
    tipo: str
    clave: str
    opciones: tuple[str, ...] = ()
    filas: tuple[tuple[str, str], ...] = ()
    nota: str = ""
    visible_si: Condicion | None = None
    especificar: Especificar | None = None
    subtitulo: str = ""

    def nombre_campo(self, fila: str | None = None) -> str:
        clave = self.clave.format(fila=fila) if fila is not None else self.clave
        return f"p{self.numero}_{clave.lower()}"

    def db_column(self, fila: str | None = None) -> str:
        clave = self.clave.format(fila=fila) if fila is not None else self.clave
        return f"{self.numero}_{clave}"

    @property
    def campos(self) -> list[str]:
        """Campos de respuesta (sin el de especificar)."""
        if self.filas:
            return [self.nombre_campo(fila) for fila, _ in self.filas]
        return [self.nombre_campo()]

    @property
    def campo_especificar(self) -> str | None:
        if not self.especificar:
            return None
        return f"p{self.numero}_{self.especificar.clave.lower()}"

    @property
    def campo_control_especificar(self) -> str | None:
        """Campo cuya respuesta habilita el texto de especificar."""
        if not self.especificar:
            return None
        if self.tipo == CHECKBOX:
            return self.nombre_campo(self.especificar.cuando)
        return self.nombre_campo()

    @property
    def db_column_especificar(self) -> str | None:
        if not self.especificar:
            return None
        return f"{self.numero}_{self.especificar.clave}"

    @property
    def choices(self) -> list[tuple[int, str]]:
        return list(enumerate(self.opciones, 1))


@dataclass(frozen=True)
class Seccion:
    id: str
    titulo: str
    preguntas: tuple[Pregunta, ...]


def _radio(numero, clave, texto, opciones, **kwargs):
    return Pregunta(numero, texto, RADIO, clave, opciones=tuple(opciones), **kwargs)


def _grilla(numero, clave, texto, filas, opciones, **kwargs):
    return Pregunta(
        numero,
        texto,
        GRILLA,
        clave,
        opciones=tuple(opciones),
        filas=tuple(filas),
        **kwargs,
    )


def _checkbox(numero, clave, texto, filas, **kwargs):
    return Pregunta(numero, texto, CHECKBOX, clave, filas=tuple(filas), **kwargs)


def _no_es(campo, *valores):
    return Condicion(campo, tuple(valores), negar=True)


def _es(campo, *valores):
    return Condicion(campo, tuple(valores))


CARTEL_INICIAL = (
    "Seleccione la o las opciones más cercanas a la realidad del CDI al momento "
    "de responder este cuestionario."
)

CAPACITACIONES = (
    "4 o más instancias de capacitación",
    "3 instancias de capacitación",
    "2 instancias de capacitación",
    "1 instancia de capacitación",
    "Ninguna instancia de capacitación",
)

FRECUENCIA_REGISTRO = (
    "Mensualmente",
    "Trimestralmente",
    "Semestralmente",
    "Anualmente",
)

FILAS_MATERIALES = (
    ("i", "Para el desarrollo de habilidades de coordinación manual."),
    ("ii", "Para el desarrollo psicomotriz grueso."),
    ("iii", "Libros adecuados a las distintas edades."),
    ("iv", "Para juego simbólico."),
    ("v", "Para actividades artísticas plásticas."),
    ("vi", "Para actividades artísticas musicales."),
)

FILAS_ARTICULACION = (
    ("i_a", "Servicio de Promoción y Protección de los Derechos — Local"),
    ("i_b", "Servicio de Promoción y Protección de los Derechos — Zonal"),
    ("ii_a", "Salud — Centros de atención primaria, hospitales municipales"),
    ("ii_b", "Salud — Hospitales provinciales"),
    ("iii_a", "Educación — Jardines Maternales"),
    ("iii_b", "Educación — Escuelas Primarias"),
    ("iv_a", "Desarrollo Social — Municipal"),
    ("iv_b", "Desarrollo Social — Provincial"),
    ("v_a", "Justicia — Juzgado de paz, de familia u otros"),
    ("vi_a", "Cultura — Juegotecas"),
    ("vi_b", "Cultura — Espacios comunitarios"),
    ("vi_c", "Cultura — Iglesias"),
    ("vii_a", "Seguridad — Policía (provincial o federal)"),
    (
        "viii",
        "Seguridad Social — Administración Nacional de la Seguridad Social (ANSES)",
    ),
    ("ix_a", "Identidad — Registro Nacional de las Personas (RENAPER)"),
)


SECCIONES = (
    Seccion(
        "infraestructura",
        "Infraestructura y servicios",
        (
            _radio(
                1,
                "INF_TENENCIA_TIPO",
                "¿Cuál es la modalidad de tenencia del inmueble donde funciona el CDI?",
                (
                    "Propio",
                    "Alquilado",
                    "Cedido o prestado por ente gubernamental "
                    "(Municipio / Departamento / Provincia)",
                    "Cedido o prestado por un privado",
                    "Comodato",
                    "Ocupado (de hecho)",
                    "Otra (especificar)",
                ),
                especificar=Especificar("INF_TENENCIA_OTRO", 7),
            ),
            _radio(
                2,
                "INF_ELEC_TIPO",
                "¿El CDI tiene electricidad?",
                (
                    "Por red formal",
                    "Por red informal",
                    "Generación propia renovable (solar, eólica)",
                    "Generación propia no renovable (motor, grupo electrógeno)",
                    "No tiene electricidad",
                ),
            ),
            _radio(
                3,
                "INF_ELEC_ESTADO",
                "¿Cuál es el estado de la instalación eléctrica del establecimiento "
                "y la frecuencia de sus revisiones?",
                (
                    "Cumple con las medidas de seguridad en todo el centro y cuenta "
                    "con revisiones periódicas (anuales o menores a un año).",
                    "Cumple con las medidas de seguridad en todo el centro, pero no "
                    "realiza revisiones periódicas formalizadas.",
                    "Cumple con las medidas de seguridad únicamente en áreas "
                    "destinadas a niños/as, independientemente de la frecuencia de "
                    "revisión.",
                    "Presenta falencias o riesgos de seguridad eléctrica en áreas "
                    "habitadas y no cuenta con revisiones periódicas.",
                    "No cumple con las medidas de seguridad básicas.",
                ),
            ),
            _radio(
                4,
                "INF_AGUA_TIPO",
                "¿El CDI tiene agua?",
                (
                    "En todos los ambientes necesarios",
                    "Sólo en un ambiente",
                    "Fuera del CDI pero dentro del terreno",
                    "Fuera del terreno",
                    "No tiene agua",
                ),
            ),
            _radio(
                5,
                "INF_AGUA_FUENTE",
                "¿Cuál es la fuente de agua utilizada para consumo en el CDI?",
                (
                    "Agua de red o embotellada - considerada segura para el consumo.",
                    "Agua de pozo con análisis vigente - con aprobación de "
                    "laboratorio en los últimos 2 años o potabilizada según métodos "
                    "recomendados.",
                    "Agua de pozo con análisis vencido o sin control - con "
                    "aprobación de laboratorio de más de 2 años o sin análisis "
                    "disponible.",
                    "Otra fuente de agua con información parcial - existe algún "
                    "proceso de potabilización pero sin garantía formal.",
                    "Otra fuente de agua sin información sobre su potabilización - "
                    "no se puede asegurar que sea apta para consumo.",
                ),
            ),
            _radio(
                6,
                "INF_COMBUSTIBLE_TIPO",
                "Para cocinar, ¿cuál es el combustible que el CDI utiliza "
                "principalmente?",
                (
                    "Gas de red",
                    "Gas en tubo o a granel (zeppelin) / Gas en garrafa",
                    "Electricidad",
                    "Leña o carbón",
                    "Otro combustible",
                ),
            ),
            _radio(
                7,
                "INF_DESAGUE_TIPO",
                "Para la eliminación de excretas, ¿el desagüe del CDI es...?",
                (
                    "A red pública (cloaca)",
                    "A cámara séptica y pozo ciego",
                    "Sólo a pozo ciego",
                    "A hoyo o excavación en la tierra",
                    "No tiene sistema de eliminación de excretas",
                ),
            ),
            _radio(
                8,
                "INF_RESIDUOS_GESTION",
                "¿De qué manera el CDI realiza la recolección y disposición final de "
                "los residuos sólidos (basura) generados en el establecimiento?",
                (
                    "Cuenta con servicio de recolección municipal regular "
                    "(puerta a puerta).",
                    "Disposición en contenedor o cesto comunitario (fuera del "
                    "predio).",
                    "Tratamiento dentro del predio mediante quema, entierro o "
                    "basural a cielo abierto.",
                    "No cuenta con un sistema organizado de gestión de residuos.",
                ),
            ),
            _radio(
                9,
                "INF_RESIDUOS_SEPARA",
                "En caso de corresponder, ¿realizan separación de residuos (por "
                "ejemplo, orgánicos y reciclables)?",
                SI_NO,
            ),
            _radio(
                10,
                "INF_BANIO_ADAPTADO",
                "¿El CDI cuenta con baños adaptados para niños?",
                SI_NO,
            ),
            _radio(
                11,
                "INF_INTERNET_CALIDAD",
                "¿El CDI cuenta con servicio de internet de calidad al que accede "
                "el personal?",
                SI_NO,
            ),
            _radio(
                12,
                "INF_INMUEBLE_RIESGO",
                "¿Las condiciones del inmueble son adecuadas para la prestación del "
                "servicio y no presenta riesgo por derrumbe o fallas estructurales?",
                (
                    "Sí",
                    "Parcialmente (deterioros sin riesgos para los niños)",
                    "No",
                ),
            ),
            _radio(
                13,
                "INF_AMENAZA_AMB",
                "A partir de la ubicación, ¿el CDI se encuentra expuesto a amenazas "
                "ambientales externas (zonas inundables, cercanía a focos de "
                "contaminación como basurales o industrias)?",
                (
                    "Riesgo identificado (especificar)",
                    "Sin riesgos significativos detectados",
                ),
                especificar=Especificar("INF_AMENAZA_ESPEC", 1),
            ),
            _radio(
                14,
                "INF_CONFORT_SALAS",
                "¿En qué medida las salas garantizan condiciones de confort "
                "ambiental (iluminación, ventilación y temperatura adecuada) para "
                "las niñas y niños?",
                (
                    "Todas las salas ofrecen un ambiente confortable, combinando "
                    "buena iluminación natural, ventilación adecuada y "
                    "climatización operativa/regulable.",
                    "Las salas son funcionales pero presentan dificultades/déficits "
                    "parciales en alguna de las dimensiones (ej. iluminación "
                    "desigual, ventilación acotada o equipos térmicos no "
                    "regulables/ruidosos).",
                    "Las salas presentan deficiencias críticas e integrales de "
                    "confort ambiental (ambientes oscuros, mal ventilados o con "
                    "temperaturas extremas de frío/calor).",
                ),
            ),
        ),
    ),
    Seccion(
        "espacios",
        "Organización de espacios y relación adulto-niño",
        (
            _radio(
                15,
                "ESP_COMPARTIDO",
                "¿El lugar físico en donde funciona el CDI es compartido con otras "
                "actividades, personas u organizaciones?",
                SI_NO,
            ),
            Pregunta(
                16,
                "¿Con cuántos ambientes cuenta el CDI (excluyendo cocina, baños, "
                "pasillos y garajes)?",
                NUMERO,
                "ESP_CANT_AMB",
            ),
            Pregunta(
                17,
                "¿Cuál es la superficie exclusiva de cada sala en m²?",
                MATRIZ_NUMERICA,
                "ESP_SUP_{fila}",
                filas=(
                    ("LACT", "Lactantes (menos de 1 año)"),
                    ("DEAM", "Deambuladores (1 año)"),
                    ("SALA2", "Sala de 2 años"),
                    ("SALA3", "Sala de 3 años"),
                    ("SALA4", "Sala de 4 años"),
                    ("MULTI", "Sala Multiedad"),
                ),
            ),
            _radio(
                18,
                "ESP_COCINA_EXCL",
                "¿Cuenta con espacio de cocina exclusivo para preparación de los "
                "alimentos?",
                SI_NO,
            ),
            _radio(
                19,
                "ESP_EXTERIOR_DISP",
                "¿El CDI cuenta con espacio exterior donde puedan realizarse "
                "actividades con los niños (patio, jardín, etc.)?",
                SI_NO,
            ),
            _radio(
                20,
                "ESP_DESCANSO_DISP",
                "¿De qué espacios dispone el CDI para la privacidad y el descanso "
                "de las niñas y niños?",
                (
                    "Cuenta con un área común y un espacio en cada sala destinados "
                    "exclusivamente al descanso y la privacidad de los niños.",
                    "Cuenta con un espacio en cada sala destinado exclusivamente al "
                    "descanso y privacidad de los niños, sin un área común con esa "
                    "finalidad.",
                    "En todas las salas se acondicionan áreas para el descanso o la "
                    "privacidad (se arman y desarman según la necesidad o el "
                    "momento del día), sin un área común con esa finalidad.",
                    "Sólo en algunas salas pueden acondicionarse áreas para el "
                    "descanso o la privacidad (se arman y desarman según la "
                    "necesidad o el momento del día), sin un área común con esa "
                    "finalidad.",
                    "No existen áreas específicas destinadas a la privacidad o al "
                    "descanso individual.",
                ),
            ),
            _radio(
                21,
                "ESP_DESCANSO_REG",
                "¿Cómo se regula el acceso de las niñas y niños a los espacios de "
                "privacidad y descanso durante la jornada?",
                (
                    "Las niñas y niños pueden acceder al espacio de descanso y "
                    "privacidad en cualquier momento de la jornada, según su propia "
                    "necesidad.",
                    "El espacio se utiliza principalmente en horarios prefijados "
                    "por el centro (ej. momento de la siesta posterior al "
                    "almuerzo).",
                    "El espacio existe pero su uso está limitado por barreras "
                    "físicas o normativas del centro.",
                ),
                visible_si=_no_es("p20_esp_descanso_disp", 5),
            ),
        ),
    ),
    Seccion(
        "materiales_mobiliario",
        "Materiales y mobiliario",
        (
            _grilla(
                22,
                "MAT_SUF_{fila}",
                "¿Los materiales disponibles son suficientes para todos los niños?",
                FILAS_MATERIALES,
                SI_NO,
                subtitulo="Materiales disponibles",
            ),
            _grilla(
                23,
                "MAT_VAR_{fila}",
                "¿Hay variedad de materiales conforme las necesidades e intereses de "
                "cada edad?",
                FILAS_MATERIALES,
                SI_NO,
            ),
            _grilla(
                24,
                "MAT_EST_{fila}",
                "¿En qué estado se encuentra la mayoría de los materiales?",
                FILAS_MATERIALES,
                (
                    "Buen estado de conservación e higiene",
                    "Con mínimo deterioro por el uso",
                    "Rotos, incompletos o sucios",
                ),
            ),
            _radio(
                25,
                "MAT_ACCESIBILIDAD",
                "¿Los materiales pedagógicos y las producciones de las niñas y niños "
                "están ubicados a una altura que permite su visualización y alcance "
                "físico?",
                (
                    "Tanto los materiales pedagógicos de uso cotidiano como las "
                    "producciones de los niños/as están expuestos al nivel de sus "
                    "ojos y a su alcance físico en todas las salas.",
                    "Las producciones o los materiales están a la altura de los "
                    "niños/as sólo en algunas salas o sectores específicos del "
                    "establecimiento y son de libre acceso.",
                    "Las producciones o los materiales están a la altura de los "
                    "niños/as sólo en algunas salas o sectores específicos del "
                    "establecimiento y sólo se accede por indicación o mediación de "
                    "adultos.",
                    "Las producciones están expuestas a la vista de los niños/as, "
                    "pero los materiales pedagógicos se ubican fuera de su alcance "
                    "físico (estantes altos o muebles cerrados).",
                    "Los materiales y producciones se ubican predominantemente a la "
                    "altura de los adultos o fuera de la vista y alcance de las "
                    "niñas y niños, o directamente no se exponen las producciones "
                    "de los niños y las niñas.",
                ),
            ),
            _radio(
                26,
                "MOB_ADECUACION",
                "¿El mobiliario (mesas, cunas, sillas, repisas, cambiadores) se "
                "adecua a las actividades desarrolladas en el CDI y se adapta al "
                "tamaño y postura de los niños?",
                ("Todos", "La mayoría", "Algunos", "Pocos", "Ninguno"),
                subtitulo="Mobiliario",
            ),
            _radio(
                27,
                "MOB_SUFICIENCIA",
                "¿Hay suficientes mesas, sillas, cunas y cambiadores para que todos "
                "los niños de las salas realicen actividades que correspondan al "
                "mismo tiempo?",
                SI_NO,
            ),
            _radio(
                28,
                "MOB_ESTADO_SEG",
                "¿Qué condiciones de seguridad y conservación presenta el mobiliario "
                "para los niños?",
                (
                    "El mobiliario es seguro para el uso de los niños y se encuentra "
                    "en muy buen estado de conservación.",
                    "El mobiliario es seguro para el uso de los niños, pero algunos "
                    "elementos están desgastados.",
                    "El mobiliario es seguro para el uso de los niños, pero se "
                    "encuentra muy deteriorado o roto.",
                    "El mobiliario presenta roturas o está muy deteriorado de modo "
                    "que compromete parcialmente la seguridad para el uso de los "
                    "niños.",
                    "El mobiliario está mayoritariamente deteriorado y presenta "
                    "condiciones que comprometen completamente la seguridad de los "
                    "niños.",
                ),
            ),
            _radio(
                29,
                "MOB_ORGANIZACION",
                "¿Cómo está organizado y distribuido el mobiliario y cómo favorece "
                "la circulación de niños y adultos?",
                (
                    "El mobiliario está organizado y distribuido de manera "
                    "funcional, permite la circulación autónoma y cómoda de niños y "
                    "adultos, incluyendo personas con discapacidad, y facilita la "
                    "organización de diferentes sectores o espacios de actividad. "
                    "Puede reorganizarse con facilidad según las actividades y "
                    "necesidades.",
                    "El mobiliario está organizado y distribuido de forma tal que "
                    "permite una circulación autónoma y cómoda de niños y adultos, "
                    "incluyendo personas con discapacidad. Hay sectores "
                    "diferenciados, aunque existen algunas limitaciones para "
                    "reorganizar el espacio.",
                    "El mobiliario permite la circulación de los niños, pero "
                    "presenta algunas dificultades para la circulación de los "
                    "adultos o personas con discapacidad. Hay sectores "
                    "diferenciados, pero la posibilidad de reorganizar el espacio "
                    "es limitada.",
                    "La distribución del mobiliario dificulta la circulación de "
                    "niños y/o adultos y limita el uso funcional de algunos "
                    "sectores. La organización del espacio es poco flexible.",
                    "La distribución del mobiliario obstaculiza significativamente "
                    "la circulación y el desplazamiento de niños y adultos y "
                    "dificulta el desarrollo de las actividades.",
                ),
            ),
        ),
    ),
    Seccion(
        "equipamiento",
        "Equipamiento",
        (
            _radio(
                30,
                "EQP_MATAFUEGOS",
                "¿El CDI cuenta con matafuegos vigentes?",
                SI_NO,
            ),
            _radio(
                31,
                "EQP_COMPUTADORA",
                "¿El CDI cuenta con computadora/s que funcione/n?",
                SI_NO,
            ),
            _radio(
                32,
                "EQP_BOTIQUIN",
                "¿El CDI cuenta con botiquín completo de primeros auxilios en buena "
                "conservación y con insumos dentro de la fecha de vencimiento, fuera "
                "del alcance de los niños?",
                ("Sí, en todas las salas", "Sí, sólo en un espacio común", "No"),
            ),
            _radio(
                33,
                "EQP_COCINA_SEG",
                "¿El espacio de cocina cuenta con el equipamiento adecuado para la "
                "producción y almacenamiento de alimentos en forma segura?",
                SI_NO,
            ),
            _radio(
                34,
                "EQP_JUEGOS_EXT",
                "¿El CDI cuenta con juegos infantiles de exterior (hamacas, "
                "toboganes, etc.) o en el Salón de Usos Múltiples?",
                SI_NO,
            ),
            _radio(
                35,
                "EQP_JUEGOS_ESTADO",
                "¿En qué estado de conservación y seguridad se encuentran los "
                "juegos infantiles en el patio exterior y/o Salón de Usos "
                "Múltiples?",
                (
                    "Estructuras íntegras, en muy buen estado de conservación, "
                    "seguras, bien ancladas y sin bordes filosos ni riesgos "
                    "visibles.",
                    "Estructuras íntegras, bien ancladas y sin bordes filosos ni "
                    "riesgos visibles, pero presentan desgaste por uso habitual.",
                    "Presentan desgaste por uso habitual, con estructuras débiles, "
                    "pero sin otros riesgos observables.",
                    "Elementos desgastados, con estructuras rotas, inestables, "
                    "oxidadas que representan un riesgo para el uso de los niños.",
                    "El CDI cuenta con juegos infantiles de exterior o S.U.M., pero "
                    "están inhabilitados.",
                ),
                visible_si=_es("p34_eqp_juegos_ext", 1),
            ),
            _radio(
                36,
                "EQP_JUEGOS_DISP",
                "¿De qué manera la disposición de los juegos en exterior y/o Salón "
                "de Usos Múltiples afecta el desplazamiento de las niñas y niños?",
                (
                    "La disposición delimita áreas claras de paso y permite el "
                    "juego libre y autónomo sin obstrucciones.",
                    "La ubicación de los juegos bloquea zonas de paso, salidas o "
                    "accesos, aumentando el riesgo de colisiones o caídas.",
                ),
                visible_si=_es("p34_eqp_juegos_ext", 1),
            ),
        ),
    ),
    Seccion(
        "personal",
        "Personal",
        (
            _radio(
                37,
                "PER_ANTIGUEDAD",
                "Permanencia promedio del personal. ¿Qué antigüedad promedio tiene "
                "el personal del CDI?",
                (
                    "6 años o más",
                    "4 a 5 años",
                    "2 a 3 años",
                    "6 meses a 1 año",
                    "Menos de 6 meses",
                ),
            ),
            _radio(
                38,
                "PER_ROTACION",
                "En el último año, ¿cómo ha sido la rotación promedio del personal?",
                (
                    "No hubo bajas ni reemplazos (0%)",
                    "Hubo muy pocas bajas y reemplazos de personal (1% a 25%)",
                    "Hubo pocas bajas y reemplazos de personal (26% a 50%)",
                    "Hubo algunas bajas y reemplazos de personal (51% a 75%)",
                    "Hubo muchas bajas y reemplazos de personal (76% o más)",
                ),
            ),
            _radio(
                39,
                "PER_CAP_PRIMEROS_AUX",
                "¿Todo el personal del CDI cuenta con capacitación certificada en "
                "primeros auxilios (Cruz Roja, Bomberos, otros)?",
                (
                    "Todo el personal",
                    "Mayoría del personal",
                    "Parte del personal",
                    "Poco personal",
                    "Ningún personal",
                ),
            ),
            _radio(
                40,
                "PER_CAP_SALA",
                "En los últimos tres años, ¿cuántas instancias de capacitación ha "
                "promovido el CDI para el personal de sala?",
                CAPACITACIONES,
                subtitulo="Instancias de capacitación del personal",
            ),
            _radio(
                41,
                "PER_CAP_COORD_TEC",
                "En los últimos tres años, ¿cuántas instancias de capacitación se "
                "han promovido para el equipo de coordinación y el equipo técnico "
                "del CDI?",
                CAPACITACIONES,
            ),
            _radio(
                42,
                "PER_CAP_COCINA",
                "En los últimos tres años, ¿cuántas instancias de capacitación e "
                "intercambio de saberes y prácticas ha promovido el CDI para el "
                "personal de cocina y comedor?",
                CAPACITACIONES + ("No cuenta con personal de cocina y comedor",),
            ),
            _radio(
                43,
                "PER_CAP_INCLUSIVA",
                "¿Durante el último año, el CDI promovió instancias de capacitación "
                "en educación inclusiva, diseños universales para el juego y "
                "aprendizaje o en procesos de trabajo con primera infancia "
                "adecuados a contextos de diversidad cultural, pueblos originarios "
                "o poblaciones migrantes?",
                SI_NO,
            ),
            _radio(
                44,
                "PER_CAP_PROTOCOLO_DER",
                "¿El CDI ha capacitado en el último año a todo el personal sobre el "
                "protocolo de actuación frente a sospecha o detección de situación "
                "de vulneración de derechos de los niños?",
                SI_NO,
            ),
        ),
    ),
    Seccion(
        "registro",
        "Instrumentos de registro",
        (
            _radio(
                45,
                "REG_PRIORIZACION_ING",
                "¿El CDI cuenta con un instrumento de priorización de ingreso de los "
                "niños al CDI?",
                SI_NO,
            ),
            _radio(
                46,
                "REG_LISTA_ESPERA",
                "¿Existe un registro de quienes quedan en lista de espera?",
                SI_NO,
            ),
            _radio(
                47,
                "REG_ASISTENCIA_FREQ",
                "¿Con qué frecuencia se registra por escrito la asistencia?",
                (
                    "Diariamente",
                    "Semanalmente",
                    "Quincenalmente",
                    "Mensualmente",
                    "No se registra la asistencia",
                ),
            ),
            _radio(
                48,
                "REG_DESARROLLO_FREQ",
                "¿Con qué frecuencia el CDI registra y actualiza en forma escrita la "
                "información sobre el desarrollo de cada niño/a a nivel cognitivo, "
                "sensorial, motor, socioafectivo y del lenguaje?",
                (
                    "Mensual",
                    "Trimestral",
                    "Semestral",
                    "Anual",
                    "No se lleva registro escrito",
                ),
            ),
            _radio(
                49,
                "REG_FAMILIA_FREQ",
                "¿Con qué frecuencia el CDI registra y actualiza en forma escrita la "
                "información familiar y las entrevistas con las familias de cada "
                "niño/a?",
                FRECUENCIA_REGISTRO
                + (
                    "No se registra información familiar y de entrevistas a las "
                    "familias",
                ),
            ),
            _radio(
                50,
                "REG_FREQ_SALUD",
                "¿Con qué frecuencia el CDI registra y actualiza en forma escrita la "
                "información sobre los controles de salud y vacunas de cada niño/a?",
                FRECUENCIA_REGISTRO
                + ("No se registra información de controles médicos y vacunas",),
            ),
        ),
    ),
    Seccion(
        "protocolos",
        "Protocolos de actuación",
        (
            _radio(
                51,
                "PROT_SALUD_EXISTE",
                "¿El CDI cuenta con un protocolo escrito de actuación en salud?",
                SI_NO,
            ),
            _checkbox(
                52,
                "PROT_SALUD_ASPECTOS_{fila}",
                "El protocolo de actuación en salud, ¿contempla algunos de los "
                "siguientes aspectos?",
                (
                    ("EMERG", "Actuación frente a emergencias médicas"),
                    ("MEDIC", "Suministro de medicamentos"),
                    ("SINTOMAS", "Pautas de actuación frente a síntomas de enfermedad"),
                    (
                        "REINTEGRO",
                        "Pautas para el reintegro de niños después de una enfermedad",
                    ),
                    (
                        "FIRMA_PERSONAL",
                        "Firma de todo el personal que da cuenta de su conocimiento",
                    ),
                    (
                        "FIRMA_FAMILIA",
                        "Suscripción de las familias que muestra que es conocido y "
                        "acordado con ellas",
                    ),
                ),
                visible_si=_es("p51_prot_salud_existe", 1),
            ),
            _radio(
                53,
                "PROT_EVAC_EXISTE",
                "¿El CDI cuenta con un Plan o Protocolo de Evacuación escrito y "
                "actualizado?",
                (
                    "Existe un documento formal, está vigente, adaptado a la "
                    "infraestructura actual del centro y acorde a la normativa "
                    "local/Defensa Civil.",
                    "Existe un documento, pero no ha sido revisado en el último año, "
                    "o no contempla cambios recientes en la infraestructura o nómina "
                    "de salas.",
                    "No se dispone de un protocolo de evacuación escrito.",
                ),
            ),
            _radio(
                54,
                "PROT_EVAC_CONOCIMIENTO",
                "¿En qué medida el personal del CDI conoce y ha sido capacitado en "
                "el protocolo de evacuación?",
                (
                    "El 100% del personal (docentes, auxiliares, cocina, "
                    "administración) conoce el protocolo y sus roles en la "
                    "emergencia.",
                    "Es conocido únicamente por el equipo directivo o el equipo "
                    "docente principal; pero los auxiliares o personal nuevo no han "
                    "sido capacitados al respecto.",
                    "El personal desconoce el procedimiento o no existen instancias "
                    "de capacitación sobre el tema.",
                ),
            ),
            _radio(
                55,
                "PROT_EVAC_SIMULACROS",
                "¿Con qué frecuencia se realizan simulacros de evacuación en el CDI?",
                (
                    "Dos veces al año",
                    "Una vez al año",
                    "Cada dos años",
                    "Con frecuencia mayor a 2 años",
                    "No se realizan simulacros",
                ),
            ),
            _radio(
                56,
                "PROT_VULNERACION_EXISTE",
                "¿El CDI cuenta con protocolo específico para la actuación ante "
                "sospecha o vulneración de derechos de los niños y se revisa "
                "periódicamente?",
                (
                    "Sí, y se actualiza anualmente",
                    "Sí, pero no se ha actualizado en los últimos dos años o más",
                    "No se cuenta con protocolo específico de actualización ante "
                    "vulneración de derechos",
                ),
            ),
        ),
    ),
    Seccion(
        "interacciones",
        "Interacciones entre adultos y niños",
        (
            _radio(
                57,
                "PROT_BUENTRATO",
                "En el CDI, el personal a cargo de sala, ¿aplica de manera habitual "
                "pautas de buen trato con las niñas y niños?",
                (
                    "Se cumple de manera sistemática en todas las salas y turnos.",
                    "Se cumple habitualmente, aunque se identifican aspectos a "
                    "reforzar en integrantes específicos.",
                    "Se observa una práctica heterogénea entre salas o turnos.",
                    "Sólo un grupo reducido aplica estas pautas de manera "
                    "sostenida.",
                    "No se cuenta con pautas de buen trato integradas o prevalecen "
                    "prácticas de manejo grupal rígidas/asistenciales.",
                ),
                nota="Observables: tono de voz adecuado, escucha atenta, contención "
                "ante el llanto/malestar y ausencia de gritos o sanciones punitivas.",
            ),
            _radio(
                58,
                "PROT_MEDIACION",
                "En el CDI, ¿qué proporción del personal de sala actúa como "
                "mediador para favorecer la convivencia y el buen trato entre "
                "pares?",
                (
                    "Se implementa de forma consistente por todo el equipo en todas "
                    "las salas.",
                    "Prevalece en la mayoría del equipo, identificándose "
                    "necesidades puntuales de fortalecimiento.",
                    "Práctica heterogénea; depende de la sala, el turno o el perfil "
                    "de la educadora.",
                    "Se observa únicamente de manera aislada en algunos integrantes "
                    "del equipo.",
                    "Prevalecen respuestas rígidas, desatención a necesidades "
                    "particulares, intervenciones punitivas o falta de mediación "
                    "ante conflictos infantiles.",
                ),
                nota="Observables: escucha/atención y sensibilidad a las demandas de "
                "cada niño, contención oportuna ante el malestar, promoción del "
                "aprendizaje de habilidades sociales, buen trato y respeto mutuo "
                "ante conflictos entre los niños.",
            ),
        ),
    ),
    Seccion(
        "planificacion",
        "Planificación y gestión institucional",
        (
            _radio(
                59,
                "PED_PSI_ESTADO",
                "¿En qué situación se encuentra el Proyecto Socioeducativo "
                "Institucional (PSI) del CDI?",
                (
                    "El CDI cuenta con un PSI escrito, actualizado en el último año "
                    "o ciclo lectivo, y sirve de marco para la planificación del "
                    "equipo.",
                    "El CDI cuenta con un PSI escrito, pero no se ha actualizado en "
                    "los últimos 2 años o más.",
                    "El CDI se encuentra redactando o reestructurando su PSI durante "
                    "el ciclo lectivo actual.",
                    "El CDI no cuenta con un PSI escrito, aunque se definen pautas "
                    "pedagógicas e institucionales de manera verbal o informal.",
                    "No cuenta con PSI: el centro no dispone de un proyecto "
                    "socioeducativo ni de pautas institucionales formalizadas.",
                ),
            ),
            _radio(
                60,
                "PED_PSI_CONTENIDOS",
                "¿Qué contenidos contempla el Proyecto Socioeducativo Institucional "
                "(PSI) escrito del CDI?",
                (
                    "El PSI explicita: diagnóstico de la comunidad infantil, "
                    "objetivos pedagógicos, estrategias de atención/cuidado de los "
                    "niños, trabajo con familias y modalidades de evaluación.",
                    "El PSI explicita: diagnóstico de la comunidad infantil, "
                    "objetivos pedagógicos, estrategias de atención/cuidado de los "
                    "niños, trabajo con familias, pero no se explicitan modalidades "
                    "de evaluación.",
                    "El PSI explicita: diagnóstico de la comunidad infantil, "
                    "objetivos pedagógicos y estrategias de atención/cuidado de los "
                    "niños, pero no explicita trabajo con familias ni modalidades de "
                    "evaluación.",
                    "El PSI explicita: diagnóstico de la comunidad infantil y "
                    "objetivos pedagógicos, pero no se explicitan estrategias de "
                    "atención/cuidado de los niños, trabajo con familias ni "
                    "modalidades de evaluación.",
                    "El PSI sólo define objetivos pedagógicos, pero no se explicita "
                    "diagnóstico de la comunidad infantil, estrategias de "
                    "atención/cuidado de los niños, trabajo con familias ni "
                    "modalidades de evaluación.",
                ),
                nota="Un PSI contempla: diagnóstico de la comunidad infantil local, "
                "objetivos pedagógicos y estrategias de atención/cuidado, criterios "
                "de trabajo con familias y relación con otras instituciones de la "
                "comunidad, y modalidades de evaluación de los procesos y/o "
                "resultados.",
                visible_si=_no_es("p59_ped_psi_estado", 5),
            ),
            _radio(
                61,
                "PED_PLANIF_EXISTE",
                "En el CDI, ¿cada una de las salas planifica sus actividades?",
                SI_NO,
            ),
            _radio(
                62,
                "PED_PLANIF_TIPO",
                "¿De qué manera se planifican las actividades semanales o diarias de "
                "las salas en el CDI?",
                (
                    "Las actividades planificadas se registran por escrito, se "
                    "articulan con el PSI y se enmarcan en un plan anual para la "
                    "sala.",
                    "Las actividades planificadas se registran por escrito, se "
                    "articulan con el PSI, pero no se cuenta con un plan anual para "
                    "la sala.",
                    "Las actividades planificadas se registran por escrito, sin "
                    "contar con plan anual de sala ni referencias al PSI.",
                    "Algunas actividades puntuales se registran por escrito "
                    "(efemérides, talleres, festejos), sin contar con plan anual de "
                    "la sala.",
                    "Las actividades de sala no se registran por escrito; la jornada "
                    "se organiza sobre la marcha cada semana del año.",
                ),
                nota="La planificación de actividades comprende el detalle de "
                "objetivos específicos, contenidos, propuestas "
                "pedagógicas/estrategias de cuidado con los niños y/o con las "
                "familias, además de la identificación de los recursos a utilizar y "
                "los procesos de evaluación. Es escrita y se explicita en documentos "
                "físicos o digitales.",
                visible_si=_es("p61_ped_planif_existe", 1),
            ),
            _radio(
                63,
                "PED_DUPLA_PROP",
                "¿En qué proporción de las salas del CDI se implementa el trabajo "
                "con dupla pedagógica a cargo de forma permanente durante la "
                "jornada?",
                (
                    "Todas las salas y turnos funcionan de manera permanente con al "
                    "menos dos personas a cargo.",
                    "Funciona como regla general, salvo en salas o turnos "
                    "específicos.",
                    "Se implementa de forma parcial según la disponibilidad de "
                    "personal o la franja horaria.",
                    "Se limita a salas de edades específicas (ej. lactantes) o a "
                    "situaciones excepcionales.",
                    "Cada sala está a cargo de un único referente o docente sin "
                    "pareja pedagógica.",
                ),
                nota="Se entiende por dupla pedagógica la presencia simultánea de al "
                "menos dos integrantes del personal educativo/auxiliar de sala a "
                "cargo del mismo grupo de niños.",
            ),
            _radio(
                64,
                "PED_REUNION_SALA_COORD",
                "¿Con qué frecuencia se realizan reuniones de trabajo y "
                "planificación socioeducativa entre el personal a cargo de sala y "
                "la coordinación o equipo técnico del CDI?",
                (
                    "Se realizan 2 o más veces al mes de manera planificada.",
                    "Se realiza 1 vez al mes de manera planificada.",
                    "Se realizan entre 3 y 5 veces a lo largo del año lectivo.",
                    "Se realizan sólo 1 a 2 veces al año.",
                    "No existen reuniones estructuradas de trabajo pedagógico entre "
                    "el personal de sala y la conducción/equipo técnico.",
                ),
                nota="Incluye instancias destinadas a la planificación de propuestas, "
                "evaluación de niños, análisis de situaciones y reflexión sobre la "
                "práctica en sala.",
            ),
            _radio(
                65,
                "PED_REUNION_NODOCENTE",
                "¿Con qué frecuencia la dirección o coordinación del CDI realiza "
                "reuniones estructuradas de trabajo con el personal no docente "
                "(servicios generales, cocina, limpieza y mantenimiento)?",
                (
                    "Se realiza al menos 1 reunión mensual con agenda de trabajo u "
                    "organización operativa.",
                    "Se realizan entre 3 y 6 reuniones al año de forma planificada.",
                    "Se realizan de manera puntual al inicio y/o cierre del ciclo "
                    "lectivo (1 a 2 veces al año).",
                    "Sólo se realizan convocatorias ante emergencias, imprevistos o "
                    "roturas de equipamiento.",
                    "No existen reuniones de trabajo estructuradas entre la "
                    "coordinación y el personal no docente.",
                ),
                nota="Incluye instancias destinadas a la revisión de protocolos de "
                "higiene, menú/nutrición, seguridad del inmueble y organización de "
                "la rutina diaria.",
            ),
            _radio(
                66,
                "PED_REUNION_GENERAL",
                "¿Con qué frecuencia se realizan reuniones que convocan a todo el "
                "personal del CDI (docente, técnico, cocina, limpieza y "
                "mantenimiento)?",
                (
                    "Mensual o bimestralmente",
                    "Trimestral o cuatrimestralmente",
                    "Semestral o anualmente",
                    "Sin periodicidad estable, sólo en ocasiones en las que surgen "
                    "imprevistos, emergencias o situaciones puntuales",
                    "No se realizan instancias de reunión con todo el personal",
                ),
                nota="Son instancias destinadas a la planificación o evaluación "
                "institucional, articulación de pautas de convivencia, eventos "
                "comunitarios o capacitación conjunta.",
            ),
        ),
    ),
    Seccion(
        "practicas",
        "Prácticas pedagógicas",
        (
            _radio(
                67,
                "PED_JUEGO_INTEGRACION",
                "¿En qué medida se integran el juego y la libre exploración de los "
                "niños en las actividades diarias del CDI?",
                (
                    "En todas las actividades.",
                    "En la mayoría de las actividades.",
                    "En algunas de las actividades.",
                    "En muy pocas actividades.",
                    "En ninguna actividad.",
                ),
            ),
            _radio(
                68,
                "PED_INTENCIONALIDAD",
                "El personal a cargo de sala, ¿promueve, con intencionalidad "
                "pedagógica, experiencias significativas orientadas al aprendizaje "
                "de nuevas habilidades, el logro progresivo de la autonomía y el "
                "desarrollo integral de los niños?",
                (
                    "El personal de sala desarrolla de forma rigurosa y sistemática "
                    "propuestas pedagógicas basadas en el juego, orientadas al "
                    "desarrollo y la autonomía, integradas de manera armónica y "
                    "cotidiana con la satisfacción de las necesidades de cuidado "
                    "(rutinas: alimentación, higiene y sueño).",
                    "El personal de sala desarrolla propuestas pedagógicas "
                    "intencionales basadas en el juego de forma regular y "
                    "sistemática, aunque su articulación fluida con las rutinas de "
                    "cuidado presenta cierta variabilidad según el grupo o docente.",
                    "El personal de sala implementa propuestas pedagógicas "
                    "intencionales basadas en el juego, pero su continuidad se "
                    "alterna con periodos donde predominan las rutinas básicas "
                    "(alimentación, higiene y sueño).",
                    "El personal de sala desarrolla propuestas pedagógicas "
                    "intencionales de manera esporádica o únicamente en algunas "
                    "salas del CDI, predominando de forma generalizada un enfoque "
                    "centrado fundamentalmente en la atención de las rutinas "
                    "básicas.",
                    "La dinámica institucional de las salas se reduce casi "
                    "exclusivamente a la cobertura de las rutinas de cuidado "
                    "físico, sin evidencia de planificación ni propuestas "
                    "pedagógicas intencionales en ninguna sala.",
                ),
            ),
            _radio(
                69,
                "PED_REGISTRO_FREQ",
                "¿Con qué frecuencia se lleva un registro de lo que ocurre en las "
                "salas en relación con el desarrollo de las actividades y "
                "experiencia de los niños?",
                (
                    "Diariamente",
                    "Semanalmente",
                    "Mensualmente",
                    "Mayor a un mes",
                    "No se lleva ningún registro",
                ),
            ),
            _radio(
                70,
                "PED_MEDIACION_OPORTUNA",
                "¿En qué medida el personal a cargo de sala interviene como "
                "mediador oportuno (observando, acompañando y orientando) tanto en "
                "las actividades planificadas como en las situaciones imprevistas y "
                "de juego libre?",
                (
                    "En todas las salas el personal actúa permanentemente como "
                    "mediador atento y oportuno en actividades y momentos "
                    "incidentales.",
                    "La mediación oportuna es la regla general en la mayoría de las "
                    "salas, aunque en momentos puntuales la intervención es más "
                    "directiva o pasiva.",
                    "Ocurre de manera consistente en aproximadamente la mitad o dos "
                    "tercios de las salas del centro.",
                    "Se observa sólo por iniciativa de educadoras específicas en "
                    "algunas salas.",
                    "El personal se limita a dar consignas o supervisar el orden "
                    "general, sin intervenir activamente como mediador en los "
                    "procesos de aprendizaje e interacción infantil.",
                ),
                nota="La mediación oportuna implica favorecer el desarrollo de "
                "habilidades socioemocionales, cognitivas, motoras y del lenguaje a "
                "partir de estar atento a las necesidades infantiles, ofrecer ayuda "
                "oportunamente y mediar entre los niños cuando fuese necesario.",
            ),
            _radio(
                71,
                "PED_JUEGO_LIBRE",
                "¿En qué proporción el personal a cargo de sala del CDI promueve el "
                "juego libre, simbólico y de exploración como herramienta principal "
                "de aprendizaje y desarrollo del lenguaje?",
                (
                    "Todo el personal de sala promueve activamente el juego libre, "
                    "la exploración y el acceso autónomo a libros y materiales.",
                    "Lo implementa la gran mayoría del personal, salvo excepciones "
                    "puntuales de algunas educadoras o en turnos específicos.",
                    "Se observa una práctica heterogénea dentro del equipo "
                    "pedagógico del centro.",
                    "Ocurre de manera aislada por iniciativa individual de "
                    "educadores/as específicos.",
                    "Predominan las actividades pasivas, el uso de pantallas o la "
                    "ejecución rígida de rutinas sin momentos de juego y "
                    "exploración.",
                ),
                nota="Se observa cuando el personal acompaña y enriquece el juego de "
                "los niños sin dirigir rígidamente, ofrece variedad de materiales al "
                "alcance de los niños e integra la lectura de libros de cuentos de "
                "forma natural durante los momentos de juego.",
            ),
            _radio(
                72,
                "PED_CULTURA_LOCAL",
                "¿De qué manera se integran en la propuesta pedagógica del CDI los "
                "elementos de la comunidad, el entorno local, las tradiciones "
                "familiares y la cultura territorial?",
                (
                    "La cultura local, el paisaje y los saberes familiares se "
                    "reflejan de forma permanente en las rutinas, la ambientación y "
                    "las actividades diarias de todas las salas.",
                    "Se planifican de manera regular proyectos, talleres o unidades "
                    "didácticas específicas que rescatan la identidad y tradiciones "
                    "de la comunidad.",
                    "La valoración cultural se limita a eventos puntuales del "
                    "calendario, fechas patrióticas, actos o festejos comunitarios "
                    "específicos.",
                    "Se realizan menciones o actividades de forma excepcional y sin "
                    "planificación pedagógica previa.",
                    "Las propuestas pedagógicas y recursos utilizados son "
                    "estandarizados y no guardan relación con el entorno, la cultura "
                    "o las tradiciones locales.",
                ),
                nota="Se observa en la selección de canciones, relatos, juegos, "
                "festejos, ambientación de salas y materiales que reflejan el "
                "contexto de los niños.",
            ),
            _radio(
                73,
                "PED_TRANSICIONES",
                "¿Cómo se organiza en el CDI la alternancia entre momentos de "
                "actividad/reposo y el manejo de los momentos de transición "
                "(ingresos, egresos y pasajes entre actividades)?",
                (
                    "La alternancia y las transiciones están organizadas, se "
                    "anticipan pedagógicamente y se adaptan con flexibilidad ante "
                    "las necesidades cambiantes del grupo.",
                    "La alternancia y las transiciones están organizadas de manera "
                    "general, aunque de forma ocasional se generan esperas o pasajes "
                    "un poco más rígidos.",
                    "Existe una estructura de tiempos fijada, pero ante imprevistos "
                    "o necesidades del grupo cuesta flexibilizar los momentos de "
                    "descanso, actividad o pasaje.",
                    "La alternancia de ritmos es irregular y las transiciones suelen "
                    "generar momentos de desorganización, llanto o esperas "
                    "prolongadas.",
                    "No hay previsibilidad en los tiempos de actividad/descanso ni "
                    "acompañamiento pedagógico en los momentos de transición.",
                ),
                nota="La gestión adecuada implica anticipar los cambios a los niños, "
                "evitar esperas prolongadas en silencio o inactividad y adaptar el "
                "ritmo según el estado de ánimo o cansancio del grupo.",
            ),
        ),
    ),
    Seccion(
        "alimentacion",
        "Servicio de alimentación",
        (
            _radio(
                74,
                "ALI_SERVICIO_DIRECTO",
                "¿El CDI ofrece de forma directa algún servicio de alimentación a "
                "los niños y niñas que concurren cotidianamente?",
                (
                    "Todos los días para todos los niños.",
                    "Algunos días para todos los niños.",
                    "Todos los días para algunos niños.",
                    "En algunas ocasiones para eventos puntuales.",
                    "No hay ningún servicio de alimentación.",
                ),
                nota="Incluye desayunos, colaciones, almuerzos o meriendas provistos "
                "por el centro, ya sea preparados en el lugar o entregados por "
                "catering/programas oficiales. No incluye viandas traídas por las "
                "familias.",
            ),
            _radio(
                75,
                "ALI_MENU_DISENO",
                "¿Cómo se diseña y adapta el menú alimentario que se ofrece a los "
                "niños y niñas en el CDI?",
                (
                    "El menú es elaborado o avalado por nutricionista, se revisa "
                    "periódicamente y se adapta estrictamente según grupos etarios, "
                    "porciones y texturas.",
                    "Cuenta con aval de nutricionista y diferenciación por edades, "
                    "pero las revisiones o adaptaciones a situaciones puntuales son "
                    "infrecuentes.",
                    "Existe un menú elaborado por nutricionista, pero se aplica de "
                    "forma homogénea a todos los niños del centro con escasa "
                    "adaptación de texturas/porciones.",
                    "El menú no cuenta con aval formal de nutricionista, pero el "
                    "personal de cocina intenta adaptar porciones o comidas según la "
                    "edad.",
                    "No existe intervención de nutricionista y se sirve exactamente "
                    "la misma comida y textura a todos los niños, independientemente "
                    "de su edad o etapa de desarrollo.",
                ),
                nota="El respaldo profesional incluye menús diseñados por "
                "nutricionistas. La adecuación etaria implica adaptar porciones, "
                "ingredientes y texturas según la edad: lactantes, 1 a 2 años, 2 a "
                "4 años.",
            ),
            _radio(
                76,
                "ALI_MENU_ADAPTACION",
                "¿El servicio de alimentación del CDI contempla y adapta las comidas "
                "según los requerimientos médicos/nutricionales específicos (ej. "
                "celiaquía, alergias, diabetes, HTA, malnutrición, entre otros) y "
                "los patrones alimentarios de los niños?",
                (
                    "Existe un protocolo institucional que registra, elabora y sirve "
                    "menús diferenciados y seguros para todas las necesidades "
                    "médicas (patologías/alergias) y contempla pautas alimentarias "
                    "de las familias.",
                    "Se preparan menús adaptados para patologías y alergias "
                    "declaradas, pero la respuesta ante patrones alimentarios "
                    "familiares es limitada o inconstante.",
                    "Sólo se contempla la adecuación frente a patologías graves con "
                    "diagnóstico médico explícito (ej. celiaquía), sin cubrir otras "
                    "necesidades o preferencias.",
                    "Las adaptaciones las realiza el personal de manera empírica, "
                    "sin protocolo formal ni garantías suficientes de bioseguridad "
                    "en cocina/sala.",
                    "Se sirve un menú único estandarizado, sin posibilidad de "
                    "adaptar ingredientes o preparaciones ante patologías, alergias "
                    "ni pautas familiares.",
                ),
                nota="Implica la existencia de un registro previo de la condición en "
                "el legajo/ficha médica del niño/a y la garantía de bioseguridad "
                "alimentaria para evitar contaminación cruzada.",
            ),
            _radio(
                77,
                "ALI_INGREDIENTES_TIPO",
                "¿Qué tipo de alimentos e ingredientes predominan en la preparación "
                "de las comidas y colaciones que se sirven en el CDI?",
                (
                    "Las comidas se elaboran diariamente a partir de ingredientes "
                    "naturales/frescos. No se ofrecen alimentos ni bebidas "
                    "ultraprocesadas.",
                    "La base de la alimentación es fresca, pero se utilizan de forma "
                    "complementaria algunos productos procesados simples (ej. "
                    "enlatados de tomate, quesos magros) sin incorporar "
                    "ultraprocesados.",
                    "Se combinan preparaciones caseras con la oferta regular de "
                    "productos comerciales procesados o ultraprocesados (ej. "
                    "galletitas dulces, jugos o postres industriales en algunas "
                    "colaciones).",
                    "La mayoría de las prestaciones se basan en productos "
                    "empaquetados, pre-elaborados, embutidos o de fácil preparación "
                    "industrial.",
                    "La oferta alimentaria consiste principalmente en productos "
                    "industriales listos para consumir, con nula o mínima presencia "
                    "de frutas, verduras y carnes frescas.",
                ),
                nota="Alimentos frescos = frutas, verduras, carnes, legumbres, "
                "huevos, cereales integrales. Procesados/mínimamente procesados = "
                "quesos, conservas, panes artesanos. Ultraprocesados = galletitas "
                "comerciales, jugos en caja/polvo, postrecitos lácteos industriales, "
                "salchichas/embutidos, caldos en cubo.",
            ),
            _radio(
                78,
                "ALI_CARNET_MANIPULADOR",
                "¿El personal a cargo de la cocina y la manipulación de alimentos en "
                "el CDI cuenta con el Carnet Oficial de Manipulador de Alimentos?",
                (
                    "La totalidad del personal de cocina posee Carnet Oficial "
                    "vigente.",
                    "Al menos una persona del equipo posee Carnet Oficial vigente, "
                    "garantizando supervisión capacitada.",
                    "Ningún integrante posee Carnet Oficial, pero han recibido "
                    "capacitaciones en higiene de cocina/manipulación de alimentos "
                    "con certificación de asistencia/aprobación.",
                    "Ningún integrante posee Carnet Oficial, pero han recibido "
                    "capacitaciones o talleres informales de higiene/manipulación.",
                    "Ningún integrante del personal de cocina cuenta con Carnet "
                    "Oficial ni ha recibido formación en la materia.",
                ),
                nota="Aplica a cocineros y auxiliares permanentes o rotativos de la "
                "cocina, según el art. 21 del Código Alimentario Argentino.",
            ),
            _radio(
                79,
                "ALI_ESPACIO_COCINA",
                "¿El CDI dispone de un espacio de cocina exclusivo y separado para "
                "la preparación y conservación de los alimentos?",
                (
                    "Sí; cuenta con un espacio delimitado destinado únicamente a la "
                    "cocina y guardado de insumos alimentarios.",
                    "Parcialmente; cuenta con un espacio delimitado para la "
                    "elaboración de alimentos, pero la conservación de los insumos "
                    "alimentarios se realiza en espacio compartido con otras "
                    "funciones del centro.",
                    "No; la cocina comparte espacio con otras funciones del centro o "
                    "las preparaciones se realizan en un área abierta/multiuso.",
                ),
                nota='Para considerarse "exclusivo", el espacio no debe ser utilizado '
                "para otros fines -como depósito, oficina o tránsito de salas- y "
                "debe contar con una delimitación física que impida el libre acceso "
                "de los niños y niñas.",
            ),
            _radio(
                80,
                "LACT_ESPACIO_EXTR",
                "¿El CDI cuenta con un espacio físico o sector destinado a la "
                "extracción de leche materna?",
                (
                    "Sí, cuenta con un ambiente destinado únicamente a la "
                    "lactancia/extracción.",
                    "Sí, cuenta con un ambiente institucional (ej. dirección, "
                    "consultorio, sala) que se acondiciona y reserva al momento de "
                    "requerirse.",
                    "No existe un sector delimitado ni adaptado para tal fin.",
                    "No hay lactantes matriculados ni trabajadoras en período de "
                    "lactancia que requieran el servicio.",
                ),
                subtitulo="Lactancia y alimentación complementaria",
            ),
            _checkbox(
                81,
                "LACT_COND_{fila}",
                "Indique las condiciones con las que cumple el espacio destinado a "
                "la extracción de leche materna:",
                (
                    (
                        "PRIV",
                        "Cuenta con puerta con traba/llave, cortinas o biombos que "
                        "impiden la visibilidad desde el exterior, garantizando "
                        "privacidad.",
                    ),
                    (
                        "LIMP",
                        "Espacio limpio, alejado de depósitos de residuos o zonas de "
                        "contaminación.",
                    ),
                    (
                        "MOB",
                        "Dispone de silla/sillón cómodo con apoyabrazos y "
                        "mesa/superficie de apoyo lavable.",
                    ),
                    (
                        "AGUA",
                        "Bacha o lavamanos con agua corriente y jabón en el espacio "
                        "o en zona contigua inmediata.",
                    ),
                ),
                visible_si=_es("p80_lact_espacio_extr", 1, 2),
            ),
            _radio(
                82,
                "LACT_ALMACENAMIENTO",
                "¿Cómo se realiza el almacenamiento de la leche humana extraída en "
                "el CDI?",
                (
                    "Se conserva en heladera (2°C a 4°C) en un sector o recipiente "
                    "exclusivo, con rotulado completo (nombre del niño/a, fecha y "
                    "hora) y verificación diaria de vigencia por parte del personal.",
                    "Se conserva en heladera con rotulado de nombre y fecha, pero no "
                    "se registra un control diario formal de vigencia.",
                    "Se almacena en heladera pero sin rotulación adecuada ni "
                    "sectorización.",
                    "No se dispone de refrigeración o la leche queda a temperatura "
                    "ambiente.",
                    "Las madres amamantan en el centro o no se almacena leche en la "
                    "jornada.",
                ),
                visible_si=_es("p80_lact_espacio_extr", 1, 2),
            ),
            _radio(
                83,
                "LACT_SENSIB_EXISTE",
                "¿El CDI realiza acciones de sensibilización e información sobre "
                "lactancia?",
                SI_NO,
            ),
            _radio(
                84,
                "ALI_COMPL_SENSIB",
                "¿El CDI realiza acciones de sensibilización e información sobre "
                "alimentación complementaria?",
                SI_NO,
            ),
            # Pendiente de producto: la especificación condiciona P85/P86 (lactancia)
            # a la P84 (alimentación complementaria). Se respeta tal cual está.
            _radio(
                85,
                "LACT_SENSIB_FREQ",
                "¿Con qué frecuencia el CDI realiza acciones de información y "
                "sensibilización sobre lactancia (talleres, reuniones, folletería u "
                "otras)?",
                FRECUENCIA_REGISTRO
                + (
                    "No se realizan acciones de información y sensibilización sobre "
                    "lactancia.",
                ),
                visible_si=_es("p84_ali_compl_sensib", 1),
            ),
            _radio(
                86,
                "LACT_SENSIB_ALCANCE",
                "¿Qué alcance se proponen las acciones de información y "
                "sensibilización sobre lactancia que realiza el CDI?",
                (
                    "Todas las familias y la comunidad circundante.",
                    "Todas las familias que llevan sus niños al CDI.",
                    "Sólo familias con lactantes.",
                    "Acciones con alcance limitado a familias específicamente "
                    "identificadas.",
                    "No se realizan acciones de información y sensibilización sobre "
                    "lactancia.",
                ),
                visible_si=_es("p84_ali_compl_sensib", 1),
            ),
        ),
    ),
    Seccion(
        "asistencia_medica",
        "Servicio de asistencia médica",
        (
            _radio(
                87,
                "SAL_EMERGENCIA_MEDICA",
                "¿De qué manera el CDI garantiza la atención médica ante emergencias "
                "o urgencias que puedan sufrir los niños, niñas o el personal "
                "dentro de la institución?",
                (
                    "Se cuenta con contrato vigente con un servicio privado de "
                    'emergencias médicas ("área protegida") con número de afiliado '
                    "y protocolo exhibido.",
                    "Se articuló formalmente con el sistema público de emergencias "
                    "en salud local, con número directo y protocolo visible en la "
                    "institución.",
                    "En caso de emergencia se recurre a la línea general pública "
                    "(107 / 911), pero no existe una articulación previa ni un "
                    "protocolo escrito exhibido.",
                    "En caso de emergencia se cuenta con el contacto informal de un "
                    "servicio privado al que se solicita cobertura de la urgencia.",
                    "El CDI no cuenta con cobertura médica contratada ni con un "
                    "procedimiento establecido para emergencias (se limita a avisar "
                    "a la familia).",
                ),
                nota="Emergencia = riesgo vital inminente. Debe existir un número "
                "telefónico de derivación directa y protocolo conocido por el "
                "equipo.",
            ),
        ),
    ),
    Seccion(
        "familias",
        "Actividades con las familias",
        (
            _radio(
                88,
                "FAM_FREQ_REUNIONES",
                "¿Con qué frecuencia el CDI establece instancias de encuentro o "
                "reuniones con las familias a lo largo del año?",
                (
                    "4 o más veces al año.",
                    "3 veces al año.",
                    "2 veces al año.",
                    "1 vez al año.",
                    "De forma esporádica, si fuese necesario.",
                ),
            ),
            _radio(
                89,
                "FAM_ESTRATEGIA_CRIANZA",
                "¿Cuál es la estrategia principal que utiliza el CDI para el "
                "fortalecimiento de la crianza con las familias?",
                (
                    "Talleres / Jornadas presenciales (3 o más al año)",
                    "Talleres / Jornadas presenciales (1 a 2 al año)",
                    "Entrega directa de cartillas / materiales de formación",
                    "Publicación pasiva en cartelera institucional",
                    "No se realizan actividades sobre crianza",
                ),
            ),
            _checkbox(
                90,
                "FAM_COM_{fila}",
                "¿Cuáles son los mecanismos a través de los cuales el CDI se "
                "comunica cotidianamente con las familias?",
                (
                    ("CUADERNO", "Cuaderno"),
                    ("CARTELERA", "Cartelera o paneles informativos"),
                    ("WHATSAPP", "Comunicaciones vía WhatsApp"),
                    ("LLAMADAS", "Llamadas telefónicas"),
                    ("RECEPCION", "Intercambios en momentos de recepción y despedida"),
                    ("OTROS", "Otros (especificar)"),
                ),
                especificar=Especificar("FAM_COM_OTRO_TEXT", "OTROS"),
            ),
            # Pendiente de producto: la matriz SQL suma 91_FAM_RECL_[CONOCIDO|
            # ANONIMO|DERIVACION] pero la especificación no trae sus textos.
            _radio(
                91,
                "FAM_RECLAMOS_EXISTE",
                "¿El CDI dispone de procedimientos claros y accesibles para que las "
                "familias presenten quejas o reclamos?",
                ("Sí", "Parcialmente", "No"),
            ),
            _radio(
                92,
                "ALI_EAN_FRECUENCIA",
                "¿Con qué frecuencia y modalidad el CDI realiza actividades de "
                "Educación Alimentaria Nutricional (EAN) con las familias?",
                (
                    "Jornadas presenciales frecuentes (3 o más al año)",
                    "Jornadas presenciales ocasionales (1 o 2 al año)",
                    "Distribución activa de material informativo / cartillas, sin "
                    "jornadas presenciales",
                    "Publicación de material informativo en cartelera, sin jornadas "
                    "presenciales ni cartillas que se distribuyen",
                    "No se realizan actividades de educación alimentaria",
                ),
            ),
            _radio(
                93,
                "ALI_EAN_COMUNIDAD",
                "¿Las jornadas presenciales de Educación Alimentaria Nutricional se "
                "abren a la participación de la comunidad general?",
                (
                    "Sí, las actividades convocan e integran a vecinos y actores "
                    "comunitarios del barrio.",
                    "No, las actividades están dirigidas únicamente a las familias "
                    "de los niños/as inscritos en el CDI.",
                ),
                visible_si=_es("p92_ali_ean_frecuencia", 1, 2),
            ),
            _radio(
                94,
                "PROT_ACCESO_DERECHOS",
                "¿El CDI realiza acciones para facilitar el acceso de los niños y sus "
                "familias a derechos y políticas/programas de promoción y protección "
                "social (identidad, AUH/AUD/AUE, pensiones, salud, discapacidad, "
                "entre otros)?",
                SI_NO,
            ),
            _radio(
                95,
                "PROT_GESTION_DERECHOS",
                "¿De qué manera el CDI gestiona y facilita el acceso de los niños/as "
                "y sus familias a los programas de protección social, salud y "
                "garantía de derechos (DNI/Identidad, AUH/AUE, CUD, vacunas, "
                "pensiones)?",
                (
                    "Se realiza un relevamiento sistemático al ingreso de la "
                    "matrícula, se gestionan trámites directamente con los "
                    "organismos (ANSES, Registro Civil, Salud) y se realiza "
                    "seguimiento individualizado hasta la efectivización del "
                    "derecho.",
                    "Se identifican las situaciones de vulnerabilidad de derechos y "
                    "se realiza la derivación formal a la red local (trabajo social, "
                    "Centro de Salud, Servicio de Protección), manteniendo registro "
                    "de los casos.",
                    "Se brinda información verbal o folletería a las familias sobre "
                    "los requisitos de los trámites únicamente cuando lo solicitan o "
                    "mediante cartelera.",
                    "Sólo se interviene ante casos de extrema emergencia o cuando lo "
                    "requiere una autoridad judicial/técnica externa.",
                    "No se realizan actividades ni relevamientos orientados a la "
                    "facilitación de acceso a derechos.",
                ),
            ),
            _radio(
                96,
                "FAM_PARTICIPACION_FREQ",
                "¿Con qué frecuencia se implementan actividades de promoción de la "
                "participación de las familias en el juego y los aprendizajes "
                "significativos de los niños (jornadas de juegos, encuentros, libros "
                "viajeros u otros elementos de circulación para la interacción con "
                "las familias, salidas educativas, festejos, etc.)?",
                FRECUENCIA_REGISTRO
                + (
                    "No incorpora dentro de su planificación institucional anual "
                    "actividades de participación de las familias en el juego y los "
                    "aprendizajes significativos de los niños.",
                ),
            ),
        ),
    ),
    Seccion(
        "articulacion",
        "Articulación con otras instituciones",
        (
            _grilla(
                97,
                "ART_{fila}_PLANIF",
                "¿El CDI mantiene articulaciones institucionales planificadas?",
                FILAS_ARTICULACION,
                SI_NO,
                subtitulo="Articulaciones y acuerdos interinstitucionales y "
                "comunitarios",
            ),
            _grilla(
                98,
                "ART_{fila}_FREQ",
                "¿Con qué frecuencia articula?",
                FILAS_ARTICULACION,
                (
                    "Mensual",
                    "Trimestral",
                    "Semestral",
                    "Anual",
                    "Ocasional",
                    "No se articula",
                ),
            ),
            _grilla(
                99,
                "ART_{fila}_ACUERDO",
                "¿El CDI cuenta con acuerdos formalizados con instituciones u "
                "organizaciones de la comunidad para el desarrollo de actividades de "
                "colaboración mutua, intercambios, o la atención de situaciones "
                "específicas?",
                FILAS_ARTICULACION,
                SI_NO,
            ),
        ),
    ),
    Seccion(
        "inclusion",
        "Inclusión y diversidad",
        (
            _radio(
                100,
                "ACC_ELEMENTOS_EXISTE",
                "¿El CDI cuenta con elementos de accesibilidad para personas con "
                "limitaciones permanentes o discapacidad de quienes concurren al "
                "CDI?",
                SI_NO,
                nota="Incluye rampas, señalización adaptada, ancho de pasillos y/o "
                "puertas adecuados, etc.",
            ),
            _checkbox(
                101,
                "ACC_TIPO_{fila}",
                "¿Con qué elementos de accesibilidad para personas con limitaciones "
                "permanentes o discapacidad cuenta el CDI?",
                (
                    ("RAMPAS_EXT", "Rampas exteriores"),
                    ("RAMPAS_INT", "Rampas interiores"),
                    ("ABERT_ADAPT", "Aberturas adaptadas"),
                    ("BANIO_ADAPT", "Baños adaptados a sillas de rueda"),
                    (
                        "SENAL_TACTIL",
                        "Señalización táctil o podotáctil, cartelería en sistema "
                        "Braille",
                    ),
                    ("AROS_MAGNET", "Aros magnéticos para personas hipoacúsicas"),
                    (
                        "PERS_LSA",
                        "Personal capacitado en lengua de señas argentina (LSA)",
                    ),
                    ("OTROS", "Otros"),
                ),
                nota="Incluye rampas, señalización adaptada, ancho de pasillos y/o "
                "puertas adecuados, etc.",
                visible_si=_es("p100_acc_elementos_existe", 1),
            ),
            _radio(
                102,
                "INCL_DISENO_UNIV_JUEGOS",
                "¿El CDI cuenta con materiales adaptados y criterios de diseño "
                "universal de juegos y juguetes que contemplen los diversos "
                "funcionamientos de los niños?",
                ("Todos", "La mayoría", "Algunos", "Pocos", "Ninguno"),
            ),
            _radio(
                103,
                "INCL_JUEGOS_EXT_ADAPT",
                "¿Los juegos de exterior o en el Salón de Usos Múltiples cuentan con "
                "características de Diseño Universal para la inclusión de niñas y "
                "niños con discapacidad?",
                (
                    "Los juegos incluyen adaptaciones (altura, arneses, rampas, "
                    "texturas) que permiten el uso autónomo por parte de niñas y "
                    "niños con diversidad funcional.",
                    "Existen algunas adaptaciones, pero la mayoría del equipamiento "
                    "requiere asistencia física del adulto.",
                    "El equipamiento carece de adaptaciones o presenta barreras "
                    "físicas infranqueables.",
                ),
            ),
        ),
    ),
)

PREGUNTAS = tuple(pregunta for seccion in SECCIONES for pregunta in seccion.preguntas)
PREGUNTAS_POR_NUMERO = {pregunta.numero: pregunta for pregunta in PREGUNTAS}


def campos_respuesta() -> list[str]:
    """Todos los campos de respuesta del instrumento, en orden."""
    nombres = []
    for pregunta in PREGUNTAS:
        nombres.extend(pregunta.campos)
        if pregunta.campo_especificar:
            nombres.append(pregunta.campo_especificar)
    return nombres


def pregunta_visible(pregunta: Pregunta, valores) -> bool:
    """Evalúa el pase condicional con los valores actuales (dict o modelo)."""
    if not pregunta.visible_si:
        return True
    getter = (
        valores.get
        if isinstance(valores, dict)
        else (lambda nombre: getattr(valores, nombre, None))
    )
    return pregunta.visible_si.se_cumple(getter(pregunta.visible_si.campo))


def especificar_requerido(pregunta: Pregunta, valores) -> bool:
    if not pregunta.especificar:
        return False
    getter = (
        valores.get
        if isinstance(valores, dict)
        else (lambda nombre: getattr(valores, nombre, None))
    )
    cuando = pregunta.especificar.cuando
    if pregunta.tipo == CHECKBOX:
        return bool(getter(pregunta.nombre_campo(cuando)))
    valor = getter(pregunta.nombre_campo())
    try:
        return int(valor) == cuando
    except (TypeError, ValueError):
        return False
