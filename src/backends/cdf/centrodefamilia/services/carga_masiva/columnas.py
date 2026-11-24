"""Columnas de la plantilla oficial de carga masiva (sección 6.1 del issue #2939).

El orden de la lista es el orden de las columnas del Excel y no se cambia sin
avisar al área: la plantilla vieja dejaría de aceptarse (RN-10).
"""

from dataclasses import dataclass

from centrodefamilia.models import Beneficiario, BeneficiarioResponsable

MAX_FILAS = 500
MAX_TAMANIO_BYTES = 10 * 1024 * 1024
# Edad del preinscripto al validar: de 6 a 17 años inclusive.
EDAD_MINIMA = 6
EDAD_MAXIMA = 17
SEPARADOR_MULTIPLE = ";"

HOJA_DATOS = "Preinscriptos"
HOJA_INSTRUCCIONES = "Instrucciones"
HOJA_ACTIVIDADES = "Actividades"
HOJA_LISTAS = "Listas"
HOJA_UBICACIONES = "Ubicaciones"


class Tipo:
    TEXTO = "texto"
    CUIL = "cuil"
    DNI = "dni"
    SEXO = "sexo"
    FECHA = "fecha"
    ENTERO = "entero"
    DIGITOS = "digitos"
    EMAIL = "email"
    SI_NO = "si_no"
    OPCION = "opcion"
    OPCIONES = "opciones"
    PROVINCIA = "provincia"
    MUNICIPIO = "municipio"
    LOCALIDAD = "localidad"
    ACTIVIDADES = "actividades"


@dataclass(frozen=True)
class Columna:
    clave: str
    encabezado: str
    tipo: str
    obligatoria: bool = False
    largo_maximo: int | None = None
    opciones: tuple = ()
    descripcion: str = ""

    @property
    def es_titular(self):
        return self.clave.startswith("titular_")


def _valores(choices):
    return tuple(valor for valor, _ in choices)


SEXOS = ("F", "M", "X")
SI_NO = ("Sí", "No")
NIVELES_ACTUALES = _valores(Beneficiario.NIVEL_EDUCATIVO_ACTUAL_CHOICES)
MAXIMOS_NIVELES = _valores(Beneficiario.MAXIMO_NIVEL_EDUCATIVO_CHOICES)
ACTIVIDADES_PREFERIDAS = _valores(Beneficiario.ACTIVIDAD_PREFERIDA_CHOICES)
VINCULOS = _valores(BeneficiarioResponsable.VINCULO_PARENTAL_CHOICES)

COLUMNAS = (
    # Datos del preinscripto
    Columna("cuil", "CUIL preinscripto", Tipo.CUIL, True),
    Columna("dni", "DNI preinscripto", Tipo.DNI, True),
    Columna("apellido", "Apellido preinscripto", Tipo.TEXTO, True, 100),
    Columna("nombre", "Nombre preinscripto", Tipo.TEXTO, True, 100),
    Columna("genero", "Sexo preinscripto", Tipo.SEXO, True, opciones=SEXOS),
    Columna("fecha_nacimiento", "Fecha de nacimiento preinscripto", Tipo.FECHA, True),
    Columna("domicilio", "Domicilio", Tipo.TEXTO, True, 255),
    Columna("provincia", "Provincia", Tipo.PROVINCIA, True),
    Columna("municipio", "Municipio", Tipo.MUNICIPIO),
    Columna("localidad", "Localidad", Tipo.LOCALIDAD),
    Columna("calle", "Calle", Tipo.TEXTO, largo_maximo=150),
    Columna("altura", "Altura", Tipo.ENTERO),
    Columna("piso_vivienda", "Piso", Tipo.TEXTO, largo_maximo=10),
    Columna("departamento_vivienda", "Departamento", Tipo.TEXTO, largo_maximo=10),
    Columna("codigo_postal", "Código postal", Tipo.ENTERO),
    Columna("barrio", "Barrio", Tipo.TEXTO, largo_maximo=100),
    Columna("monoblock", "Monoblock", Tipo.TEXTO, largo_maximo=100),
    Columna("prefijo_celular", "Prefijo celular", Tipo.DIGITOS, largo_maximo=4),
    Columna("numero_celular", "Número celular", Tipo.DIGITOS, largo_maximo=12),
    Columna(
        "prefijo_telefono_fijo", "Prefijo teléfono fijo", Tipo.DIGITOS, largo_maximo=4
    ),
    Columna(
        "numero_telefono_fijo", "Número teléfono fijo", Tipo.DIGITOS, largo_maximo=12
    ),
    Columna("correo_electronico", "Correo electrónico", Tipo.EMAIL, largo_maximo=150),
    Columna("estado_academico", "¿Estudia actualmente?", Tipo.SI_NO, opciones=SI_NO),
    Columna(
        "nivel_educativo_actual",
        "Nivel educativo actual",
        Tipo.OPCION,
        opciones=NIVELES_ACTUALES,
        descripcion="Solo si estudia actualmente.",
    ),
    Columna(
        "maximo_nivel_educativo",
        "Máximo nivel educativo",
        Tipo.OPCION,
        True,
        opciones=MAXIMOS_NIVELES,
    ),
    Columna(
        "institucion_academica",
        "Institución académica",
        Tipo.TEXTO,
        largo_maximo=150,
    ),
    Columna(
        "actividad_preferida",
        "Actividad preferida",
        Tipo.OPCIONES,
        True,
        opciones=ACTIVIDADES_PREFERIDAS,
        descripcion="Una o más, separadas por ;",
    ),
    Columna(
        "actividades_extracurriculares",
        "¿Realiza actividades extracurriculares?",
        Tipo.SI_NO,
        opciones=SI_NO,
    ),
    Columna(
        "actividades_detalle",
        "Actividades extracurriculares",
        Tipo.ACTIVIDADES,
        descripcion=(
            "Obligatoria si realiza actividades extracurriculares. Nombres de la "
            "hoja Actividades, separados por ;"
        ),
    ),
    # Datos del titular
    Columna("titular_cuil", "CUIL titular", Tipo.CUIL, True),
    Columna("titular_dni", "DNI titular", Tipo.DNI, True),
    Columna("titular_apellido", "Apellido titular", Tipo.TEXTO, True, 100),
    Columna("titular_nombre", "Nombre titular", Tipo.TEXTO, True, 100),
    Columna("titular_genero", "Sexo titular", Tipo.SEXO, True, opciones=SEXOS),
    Columna(
        "titular_fecha_nacimiento", "Fecha de nacimiento titular", Tipo.FECHA, True
    ),
    Columna(
        "vinculo_parental",
        "Vínculo con el preinscripto",
        Tipo.OPCION,
        True,
        opciones=VINCULOS,
    ),
    Columna("titular_calle", "Calle titular", Tipo.TEXTO, largo_maximo=150),
    Columna("titular_altura", "Altura titular", Tipo.ENTERO),
    Columna("titular_piso_vivienda", "Piso titular", Tipo.TEXTO, largo_maximo=10),
    Columna(
        "titular_departamento_vivienda",
        "Departamento titular",
        Tipo.TEXTO,
        largo_maximo=10,
    ),
    Columna("titular_codigo_postal", "Código postal titular", Tipo.ENTERO),
    Columna("titular_barrio", "Barrio titular", Tipo.TEXTO, largo_maximo=100),
    Columna("titular_monoblock", "Monoblock titular", Tipo.TEXTO, largo_maximo=100),
    Columna("titular_provincia", "Provincia titular", Tipo.PROVINCIA, True),
    Columna("titular_municipio", "Municipio titular", Tipo.MUNICIPIO),
    Columna("titular_localidad", "Localidad titular", Tipo.LOCALIDAD),
    Columna(
        "titular_prefijo_celular",
        "Prefijo celular titular",
        Tipo.DIGITOS,
        largo_maximo=4,
    ),
    Columna(
        "titular_numero_celular",
        "Número celular titular",
        Tipo.DIGITOS,
        largo_maximo=12,
    ),
    Columna(
        "titular_prefijo_telefono_fijo",
        "Prefijo teléfono fijo titular",
        Tipo.DIGITOS,
        largo_maximo=4,
    ),
    Columna(
        "titular_numero_telefono_fijo",
        "Número teléfono fijo titular",
        Tipo.DIGITOS,
        largo_maximo=12,
    ),
    Columna(
        "titular_correo_electronico",
        "Correo electrónico titular",
        Tipo.EMAIL,
        largo_maximo=150,
    ),
)

COLUMNAS_POR_CLAVE = {columna.clave: columna for columna in COLUMNAS}
ENCABEZADOS = tuple(columna.encabezado for columna in COLUMNAS)

# Campos del titular que identifican a la persona (RN-26): no se pisan.
CAMPOS_IDENTIDAD_TITULAR = (
    "cuil",
    "dni",
    "apellido",
    "nombre",
    "genero",
    "fecha_nacimiento",
)
# Columnas 38 a 52: contacto y domicilio del titular, se actualizan al confirmar.
CAMPOS_CONTACTO_TITULAR = (
    "calle",
    "altura",
    "piso_vivienda",
    "departamento_vivienda",
    "codigo_postal",
    "barrio",
    "monoblock",
    "provincia",
    "municipio",
    "localidad",
    "prefijo_celular",
    "numero_celular",
    "prefijo_telefono_fijo",
    "numero_telefono_fijo",
    "correo_electronico",
)
