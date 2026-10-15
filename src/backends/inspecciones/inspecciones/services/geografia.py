"""Provincias y localidades de SISOC para el catálogo de escuelas.

El padrón trae la jurisdicción y la localidad como texto. La provincia se
resuelve por nombre (con dos equivalencias fijas) y la localidad se busca
dentro de la provincia, normalizando: sin tildes, sin mayúsculas y con los
espacios colapsados. Una sola coincidencia se vincula; varias o ninguna dejan
la escuela "a revisar" con el texto original guardado.

Para importar 64.500 filas sin una consulta por fila, ``MapaGeografico`` carga
una sola vez en memoria las provincias y las localidades con su municipio.
"""

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from core.models import Localidad, Provincia

NOMBRE_CABA = "ciudad autonoma de buenos aires"

# Texto del padrón (normalizado) -> nombre de la provincia en SISOC (normalizado).
EQUIVALENCIAS_PROVINCIA = {
    "ciudad de buenos aires": NOMBRE_CABA,
    "tierra del fuego": "tierra del fuego, antartida e islas del atlantico sur",
}

# En CABA el padrón trae "CIUDAD DE BUENOS AIRES" para todas las escuelas: se
# vinculan a la localidad genérica de la ciudad.
LOCALIDADES_GENERICAS_CABA = frozenset({"ciudad de buenos aires", NOMBRE_CABA, "caba"})


@lru_cache(maxsize=65536)
def normalizar(texto):
    """Sin tildes, en minúsculas y con los espacios colapsados.

    Con caché: en el padrón las mismas provincias y localidades se repiten
    decenas de miles de veces.
    """
    texto = str(texto or "")
    if not texto.isascii():
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split()).lower()


@dataclass(frozen=True)
class LocalidadSisoc:
    id: int
    nombre: str
    municipio: str
    provincia_id: int


@dataclass
class ResolucionLocalidad:
    localidad: LocalidadSisoc | None = None
    motivo: str = ""
    coincidencias: int = 0


@dataclass
class MapaGeografico:
    """Provincias y localidades en memoria, indexadas por nombre normalizado."""

    provincias: dict = field(default_factory=dict)
    nombres_provincia: dict = field(default_factory=dict)
    localidades: dict = field(default_factory=dict)
    genericas_caba: list = field(default_factory=list)

    @classmethod
    def cargar(cls):
        mapa = cls()
        for provincia_id, nombre in Provincia.objects.values_list("id", "nombre"):
            mapa.provincias[normalizar(nombre)] = provincia_id
            mapa.nombres_provincia[provincia_id] = nombre
        caba_id = mapa.provincias.get(NOMBRE_CABA)
        filas = Localidad.objects.filter(
            municipio__provincia__isnull=False
        ).values_list("id", "nombre", "municipio__nombre", "municipio__provincia_id")
        for localidad_id, nombre, municipio, provincia_id in filas:
            localidad = LocalidadSisoc(localidad_id, nombre, municipio, provincia_id)
            clave = (provincia_id, normalizar(nombre))
            mapa.localidades.setdefault(clave, []).append(localidad)
            if provincia_id == caba_id and clave[1] == NOMBRE_CABA:
                mapa.genericas_caba.append(localidad)
        return mapa

    def provincia(self, texto):
        """``(provincia_id, equivalencia_aplicada)``; ``(None, False)`` si no existe."""
        clave = normalizar(texto)
        destino = EQUIVALENCIAS_PROVINCIA.get(clave, clave)
        provincia_id = self.provincias.get(destino)
        return provincia_id, provincia_id is not None and destino != clave

    def es_caba(self, provincia_id):
        return provincia_id is not None and provincia_id == self.provincias.get(
            NOMBRE_CABA
        )

    def localidad(self, provincia_id, texto):
        clave = normalizar(texto)
        if self.es_caba(provincia_id) and clave in LOCALIDADES_GENERICAS_CABA:
            if len(self.genericas_caba) == 1:
                return ResolucionLocalidad(self.genericas_caba[0], "", 1)
        candidatas = self.localidades.get((provincia_id, clave), []) if clave else []
        if len(candidatas) == 1:
            return ResolucionLocalidad(candidatas[0], "", 1)
        if candidatas:
            return ResolucionLocalidad(
                None, "localidad_repetida", len({c.municipio for c in candidatas})
            )
        return ResolucionLocalidad(None, "localidad_inexistente", 0)


def textos_de_ubicacion(localidad, *, texto_original="", distrito_anterior=""):
    """``(localidad, distrito)`` en texto, como los lee la app.

    Con localidad vinculada: su nombre y el de su municipio. La localidad
    genérica de CABA pertenece en la base a un municipio puntual (una comuna),
    que no es el distrito de todas las escuelas de la ciudad: ahí el distrito
    es la ciudad. Sin vínculo: el texto original y el distrito que ya tenía.
    """
    if localidad is None:
        return texto_original[:255], distrito_anterior[:120]
    if isinstance(localidad, LocalidadSisoc):
        return _textos(localidad.nombre, localidad.municipio)
    municipio = getattr(getattr(localidad, "municipio", None), "nombre", "")
    return _textos(localidad.nombre, municipio)


@lru_cache(maxsize=32768)
def _textos(nombre, municipio):
    if normalizar(nombre) == NOMBRE_CABA:
        municipio = nombre
    return nombre[:255], (municipio or "")[:120]


def opciones_de_localidad(provincia_id, texto="", *, limite=30):
    """Localidades de una provincia para Select2: "Localidad · Municipio"."""
    if not provincia_id:
        return []
    queryset = Localidad.objects.filter(municipio__provincia_id=provincia_id)
    texto = (texto or "").strip()
    if texto:
        queryset = queryset.filter(nombre__icontains=texto)
    filas = queryset.order_by("nombre", "municipio__nombre").values_list(
        "id", "nombre", "municipio__nombre"
    )[:limite]
    return [
        {"id": localidad_id, "text": etiqueta_localidad(nombre, municipio)}
        for localidad_id, nombre, municipio in filas
    ]


def etiqueta_localidad(nombre, municipio):
    return f"{nombre} · {municipio}" if municipio else nombre


def opcion_localidad_por_id(localidad_id, *, provincia_id=None):
    """Opción ya elegida para precargar el Select2, o ``None``."""
    try:
        localidad_id = int(localidad_id)
    except (TypeError, ValueError):
        return None
    queryset = Localidad.objects.filter(pk=localidad_id)
    if provincia_id:
        queryset = queryset.filter(municipio__provincia_id=provincia_id)
    fila = queryset.values_list("id", "nombre", "municipio__nombre").first()
    if fila is None:
        return None
    return {"id": fila[0], "text": etiqueta_localidad(fila[1], fila[2])}
