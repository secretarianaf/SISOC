"""Validación de las filas de un lote de carga masiva (sección 7 del issue #2939).

Cada validación recorre el lote completo: las reglas entre filas (repetidos,
titular compartido) dependen de todas, y con el tope de 500 filas alcanza con
pocas consultas agrupadas. No consulta servicios externos (RNF-03).
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

from centrodefamilia.models import (
    Actividad,
    Beneficiario,
    FilaCargaMasivaPreinscriptos,
    PadronBeneficiarios,
    Responsable,
)
from centrodefamilia.services.carga_masiva.columnas import (
    CAMPOS_CONTACTO_TITULAR,
    CAMPOS_IDENTIDAD_TITULAR,
    COLUMNAS,
    COLUMNAS_POR_CLAVE,
    SEPARADOR_MULTIPLE,
    Tipo,
)
from core.models import Localidad, Municipio, Provincia

Estado = FilaCargaMasivaPreinscriptos.Estado
AccionPreinscripto = FilaCargaMasivaPreinscriptos.AccionPreinscripto
AccionTitular = FilaCargaMasivaPreinscriptos.AccionTitular

CUIL_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
_SEPARADORES_NUMERO = re.compile(r"[\s.\-]")
_FECHA = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")
_ESPACIOS = re.compile(r"\s+")
_SEXOS = {
    "f": "F",
    "femenino": "F",
    "mujer": "F",
    "m": "M",
    "masculino": "M",
    "varon": "M",
    "x": "X",
    "otro": "X",
    "no binario": "X",
    "otro/no binario": "X",
}
_SI = {"si", "s"}
_NO = {"no", "n", ""}
_TIPOS_CATALOGO_GEOGRAFICO = (Tipo.PROVINCIA, Tipo.MUNICIPIO, Tipo.LOCALIDAD)


class ValorNoReconocido(ValueError):
    """Valor fuera de lista o catálogo: error si la columna es obligatoria (RN-17)."""


@dataclass
class Invalido:
    """Valor que no se pudo interpretar; se conserva el texto para comparar filas."""

    texto: str


@dataclass
class ResultadoFila:
    numero_fila: int
    valores: dict = field(default_factory=dict)
    errores: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    accion_preinscripto: str = ""
    accion_titular: str = ""
    fila_titular: int | None = None
    beneficiario_existente: int | None = None
    titular_existente: int | None = None

    def error(self, clave, mensaje):
        self.errores.append({"columna": _encabezado(clave), "mensaje": mensaje})

    def advertencia(self, clave, mensaje):
        self.advertencias.append({"columna": _encabezado(clave), "mensaje": mensaje})

    def valor(self, clave):
        """Valor interpretado o None si falta o es inválido."""
        valor = self.valores.get(clave)
        return None if isinstance(valor, Invalido) else valor

    @property
    def estado(self):
        if self.errores:
            return Estado.ERROR
        if self.advertencias:
            return Estado.ADVERTENCIA
        return Estado.VALIDA


def _encabezado(clave):
    columna = COLUMNAS_POR_CLAVE.get(clave)
    return columna.encabezado if columna else clave


def normalizar(texto):
    """Compara textos de catálogo sin importar mayúsculas, tildes ni espacios (DT-08)."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto or ""))
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return _ESPACIOS.sub(" ", sin_tildes).strip().casefold()


def cuil_valido(cuil):
    if len(cuil) != 11 or not cuil.isdigit():
        return False
    total = sum(int(d) * p for d, p in zip(cuil[:10], CUIL_PESOS))
    verificador = 11 - (total % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    return verificador == int(cuil[-1])


# ——— Interpretación de cada celda ———


def _solo_digitos(texto):
    limpio = _SEPARADORES_NUMERO.sub("", texto)
    return limpio if limpio.isdigit() else ""


def _parsear_cuil(texto, _columna):
    digitos = _solo_digitos(texto)
    if len(digitos) != 11:
        raise ValueError("El CUIL debe tener 11 dígitos.")
    if not cuil_valido(digitos):
        raise ValueError("El CUIL tiene el dígito verificador inválido.")
    return int(digitos)


def _parsear_dni(texto, _columna):
    digitos = _solo_digitos(texto).lstrip("0")
    if not 7 <= len(digitos) <= 8:
        raise ValueError("El DNI debe tener 7 u 8 dígitos.")
    return int(digitos)


def _parsear_sexo(texto, _columna):
    sexo = _SEXOS.get(normalizar(texto))
    if not sexo:
        raise ValorNoReconocido("Debe ser F, M o X.")
    return sexo


def _parsear_fecha(texto, _columna):
    coincidencia = _FECHA.match(texto.strip())
    if not coincidencia:
        raise ValueError("La fecha debe tener el formato dd/mm/aaaa.")
    dia, mes, anio = (int(parte) for parte in coincidencia.groups())
    try:
        fecha = date(anio, mes, dia)
    except ValueError as exc:
        raise ValueError("La fecha no es válida.") from exc
    if fecha > date.today():
        raise ValueError("La fecha no puede ser futura.")
    if anio < 1900:
        raise ValueError("La fecha no es válida.")
    return fecha


def _parsear_entero(texto, _columna):
    digitos = texto.strip()
    if not digitos.isdigit() or len(digitos) > 9:
        raise ValueError("Debe ser un número entero.")
    return int(digitos)


def _parsear_digitos(texto, columna):
    digitos = _solo_digitos(texto)
    if not digitos:
        raise ValueError("Solo puede tener números.")
    if len(digitos) > columna.largo_maximo:
        raise ValueError(f"Puede tener hasta {columna.largo_maximo} dígitos.")
    return digitos


def _parsear_email(texto, columna):
    if len(texto) > columna.largo_maximo:
        raise ValueError(f"Puede tener hasta {columna.largo_maximo} caracteres.")
    try:
        validate_email(texto)
    except ValidationError as exc:
        raise ValueError("El correo electrónico no es válido.") from exc
    return texto


def _parsear_texto(texto, columna):
    if columna.largo_maximo and len(texto) > columna.largo_maximo:
        raise ValueError(f"Puede tener hasta {columna.largo_maximo} caracteres.")
    return texto


def _parsear_si_no(texto, _columna):
    normalizado = normalizar(texto)
    if normalizado in _SI:
        return True
    if normalizado in _NO:
        return False
    raise ValorNoReconocido("Debe ser Sí o No.")


def _opcion(texto, columna):
    por_nombre = {normalizar(opcion): opcion for opcion in columna.opciones}
    opcion = por_nombre.get(normalizar(texto))
    if opcion is None:
        raise ValorNoReconocido(
            f"«{texto}» no es un valor válido. Valores: {', '.join(columna.opciones)}."
        )
    return opcion


def _parsear_opciones(texto, columna):
    valores = []
    for parte in texto.split(SEPARADOR_MULTIPLE):
        if parte.strip():
            opcion = _opcion(parte, columna)
            if opcion not in valores:
                valores.append(opcion)
    if not valores:
        raise ValorNoReconocido("Indique al menos un valor.")
    return valores


_PARSERS = {
    Tipo.CUIL: _parsear_cuil,
    Tipo.DNI: _parsear_dni,
    Tipo.SEXO: _parsear_sexo,
    Tipo.FECHA: _parsear_fecha,
    Tipo.ENTERO: _parsear_entero,
    Tipo.DIGITOS: _parsear_digitos,
    Tipo.EMAIL: _parsear_email,
    Tipo.TEXTO: _parsear_texto,
    Tipo.SI_NO: _parsear_si_no,
    Tipo.OPCION: _opcion,
    Tipo.OPCIONES: _parsear_opciones,
}


def _no_reconocido(resultado, columna, mensaje):
    """RN-17: error en columna obligatoria; advertencia y sin dato en opcional."""
    if columna.obligatoria:
        resultado.error(columna.clave, mensaje)
        resultado.valores[columna.clave] = Invalido(mensaje)
    else:
        resultado.advertencia(columna.clave, f"{mensaje} Se cargará sin este dato.")
        resultado.valores[columna.clave] = None


def _interpretar_celdas(resultado, datos):
    for columna in COLUMNAS:
        if (
            columna.tipo in _TIPOS_CATALOGO_GEOGRAFICO
            or columna.tipo == Tipo.ACTIVIDADES
        ):
            continue
        texto = str(datos.get(columna.clave) or "").strip()
        if not texto:
            if columna.obligatoria:
                resultado.error(columna.clave, "Es obligatoria.")
                resultado.valores[columna.clave] = Invalido("")
            else:
                resultado.valores[columna.clave] = (
                    False if columna.tipo == Tipo.SI_NO else None
                )
            continue
        try:
            resultado.valores[columna.clave] = _PARSERS[columna.tipo](texto, columna)
        except ValorNoReconocido as exc:
            _no_reconocido(resultado, columna, str(exc))
        except ValueError as exc:
            resultado.error(columna.clave, str(exc))
            resultado.valores[columna.clave] = Invalido(texto)


def _validar_dni_en_cuil(resultado, clave_cuil, clave_dni):
    """RN-15: el DNI tiene que ser el número de documento contenido en el CUIL."""
    cuil = resultado.valor(clave_cuil)
    dni = resultado.valor(clave_dni)
    if cuil and dni and int(str(cuil)[2:10]) != dni:
        resultado.error(clave_dni, "No coincide con el número de documento del CUIL.")


def _validar_titular_distinto(resultado):
    """El titular no puede ser la misma persona que el preinscripto."""
    mismo_dni = resultado.valor("dni") and resultado.valor(
        "titular_dni"
    ) == resultado.valor("dni")
    mismo_cuil = resultado.valor("cuil") and resultado.valor(
        "titular_cuil"
    ) == resultado.valor("cuil")
    if mismo_dni or mismo_cuil:
        resultado.error(
            "titular_dni",
            "El titular no puede tener el mismo DNI o CUIL que el preinscripto.",
        )


def _validar_nivel_actual(resultado):
    """RN-19: el nivel actual solo se guarda si estudia actualmente."""
    if resultado.valor("nivel_educativo_actual") and not resultado.valor(
        "estado_academico"
    ):
        resultado.advertencia(
            "nivel_educativo_actual",
            "Se informó nivel educativo actual pero no estudia actualmente: el "
            "dato no se guardará.",
        )
        resultado.valores["nivel_educativo_actual"] = None


# ——— Catálogos ———


class Catalogos:
    """Catálogos vigentes indexados por nombre normalizado (S-02: ambiguo = no reconocido)."""

    def __init__(self, filas_datos):
        self.provincias = self._indexar(Provincia.objects.values_list("id", "nombre"))
        provincia_ids = set()
        for datos in filas_datos:
            for clave in ("provincia", "titular_provincia"):
                ids = self.provincias.get(normalizar(datos.get(clave)), [])
                if len(ids) == 1:
                    provincia_ids.add(ids[0])
        self.municipios = self._indexar_por_padre(
            Municipio.objects.filter(provincia_id__in=provincia_ids).values_list(
                "id", "nombre", "provincia_id"
            )
        )
        self.localidades = self._indexar_por_padre(
            Localidad.objects.filter(
                municipio__provincia_id__in=provincia_ids
            ).values_list("id", "nombre", "municipio_id")
        )
        self.actividades = self._indexar(Actividad.objects.values_list("id", "nombre"))

    @staticmethod
    def _indexar(pares):
        indice = defaultdict(list)
        for pk, nombre in pares:
            indice[normalizar(nombre)].append(pk)
        return indice

    @staticmethod
    def _indexar_por_padre(ternas):
        indice = defaultdict(list)
        for pk, nombre, padre_id in ternas:
            indice[(padre_id, normalizar(nombre))].append(pk)
        return indice


def _unico(ids):
    return ids[0] if len(ids) == 1 else None


def _interpretar_ubicacion(resultado, datos, catalogos, prefijo):
    clave_provincia = f"{prefijo}provincia"
    clave_municipio = f"{prefijo}municipio"
    clave_localidad = f"{prefijo}localidad"
    texto_provincia = str(datos.get(clave_provincia) or "").strip()
    texto_municipio = str(datos.get(clave_municipio) or "").strip()
    texto_localidad = str(datos.get(clave_localidad) or "").strip()

    provincia_id = None
    if not texto_provincia:
        resultado.error(clave_provincia, "Es obligatoria.")
    else:
        provincia_id = _unico(catalogos.provincias.get(normalizar(texto_provincia), []))
        if provincia_id is None:
            resultado.error(
                clave_provincia, f"«{texto_provincia}» no es una provincia válida."
            )
    resultado.valores[clave_provincia] = provincia_id or Invalido(texto_provincia)

    municipio_id = None
    if texto_municipio:
        municipio_id = _unico(
            catalogos.municipios.get((provincia_id, normalizar(texto_municipio)), [])
        )
        if municipio_id is None:
            resultado.advertencia(
                clave_municipio,
                f"«{texto_municipio}» no es un municipio de la provincia indicada. "
                "Se cargará sin este dato.",
            )
    resultado.valores[clave_municipio] = municipio_id

    localidad_id = None
    if texto_localidad:
        localidad_id = _unico(
            catalogos.localidades.get((municipio_id, normalizar(texto_localidad)), [])
        )
        if localidad_id is None:
            resultado.advertencia(
                clave_localidad,
                f"«{texto_localidad}» no es una localidad del municipio indicado. "
                "Se cargará sin este dato.",
            )
    resultado.valores[clave_localidad] = localidad_id


def _interpretar_actividades(resultado, datos, catalogos):
    texto = str(datos.get("actividades_detalle") or "").strip()
    realiza = resultado.valor("actividades_extracurriculares")
    resultado.valores["actividades_detalle"] = []
    nombres = [p.strip() for p in texto.split(SEPARADOR_MULTIPLE) if p.strip()]
    if not realiza:
        if nombres:
            resultado.advertencia(
                "actividades_detalle",
                "No realiza actividades extracurriculares: las actividades "
                "indicadas no se guardarán.",
            )
        return
    if not nombres:
        resultado.error(
            "actividades_detalle",
            "Es obligatoria si realiza actividades extracurriculares.",
        )
        return
    ids, desconocidas = [], []
    for nombre in nombres:
        pk = _unico(catalogos.actividades.get(normalizar(nombre), []))
        if pk is None:
            desconocidas.append(nombre)
        elif pk not in ids:
            ids.append(pk)
    if desconocidas:
        resultado.error(
            "actividades_detalle",
            "No se reconocen en el catálogo de actividades: "
            + ", ".join(f"«{nombre}»" for nombre in desconocidas)
            + ".",
        )
        return
    resultado.valores["actividades_detalle"] = ids


def validar_fila(numero_fila, datos, catalogos):
    """Reglas de una sola fila (7.1 y 7.2)."""
    resultado = ResultadoFila(numero_fila=numero_fila)
    _interpretar_celdas(resultado, datos)
    _validar_dni_en_cuil(resultado, "cuil", "dni")
    _validar_dni_en_cuil(resultado, "titular_cuil", "titular_dni")
    _validar_titular_distinto(resultado)
    _interpretar_ubicacion(resultado, datos, catalogos, "")
    _interpretar_ubicacion(resultado, datos, catalogos, "titular_")
    _interpretar_actividades(resultado, datos, catalogos)
    _validar_nivel_actual(resultado)
    return resultado


# ——— Reglas entre filas y contra SISOC ———


def buscar_en_padron(cuils):
    """Registros del padrón por CUIL (texto, como lo guarda la tabla externa)."""
    padron = defaultdict(list)
    for registro in PadronBeneficiarios.objects.filter(
        cuil__in=[str(cuil) for cuil in cuils]
    ).values("cuil", "dni", "genero", "provincia_tabla", "municipio_tabla"):
        padron[str(registro["cuil"]).strip()].append(registro)
    return padron


def _dni_del_padron(valor):
    digitos = re.sub(r"\D", "", str(valor or ""))
    return int(digitos) if digitos else None


def _validar_padron(resultados):
    cuils = {r.valor("cuil") for r in resultados if r.valor("cuil")}
    padron = buscar_en_padron(cuils) if cuils else {}
    for resultado in resultados:
        cuil, dni, sexo = (
            resultado.valor("cuil"),
            resultado.valor("dni"),
            resultado.valor("genero"),
        )
        if not cuil:
            continue
        registros = padron.get(str(cuil), [])
        if not registros:
            resultado.error("cuil", "El CUIL no está en el padrón de beneficiarios.")
            continue
        if not dni:
            continue  # DNI inválido: su error ya está informado.
        mismo_dni = [r for r in registros if _dni_del_padron(r["dni"]) == dni]
        if not mismo_dni:
            # Si el DNI no coincide ni con el CUIL, ese error ya lo explica.
            if str(cuil)[2:10] == f"{dni:08d}":
                resultado.error(
                    "dni", "El DNI no coincide con el del padrón para ese CUIL."
                )
            continue
        mismo_sexo = [
            r for r in mismo_dni if str(r["genero"] or "").strip().upper() == sexo
        ]
        if not mismo_sexo:
            if sexo:
                resultado.error(
                    "genero", "El sexo no coincide con el del padrón para ese CUIL."
                )
            continue
        registro = mismo_sexo[0]
        resultado.valores["provincia_tabla"] = registro.get("provincia_tabla") or ""
        resultado.valores["municipio_tabla"] = registro.get("municipio_tabla") or ""


def _validar_repetidos(resultados):
    """RN-22: la primera aparición vale; las siguientes son error (S-01)."""
    por_cuil, por_dni = {}, {}
    for resultado in resultados:
        cuil, dni = resultado.valor("cuil"), resultado.valor("dni")
        anterior = por_cuil.get(cuil) or por_dni.get(dni)
        if anterior:
            resultado.error(
                "cuil",
                f"El preinscripto está repetido: ya aparece en la fila {anterior}.",
            )
            continue
        if cuil:
            por_cuil[cuil] = resultado.numero_fila
        if dni:
            por_dni[dni] = resultado.numero_fila


def _existentes(modelo, resultados, clave_cuil, clave_dni):
    cuils = {r.valor(clave_cuil) for r in resultados if r.valor(clave_cuil)}
    dnis = {r.valor(clave_dni) for r in resultados if r.valor(clave_dni)}
    if not cuils and not dnis:
        return {}, {}
    registros = list(modelo.all_objects.filter(Q(cuil__in=cuils) | Q(dni__in=dnis)))
    return (
        {registro.cuil: registro for registro in registros},
        {registro.dni: registro for registro in registros},
    )


def _buscar_existente(resultado, por_cuil, por_dni, clave_cuil, clave_dni):
    """Devuelve (registro, conflicto): conflicto si DNI y CUIL son de personas distintas."""
    por_c = por_cuil.get(resultado.valor(clave_cuil))
    por_d = por_dni.get(resultado.valor(clave_dni))
    if por_c and por_d and por_c.pk != por_d.pk:
        return None, True
    return por_c or por_d, False


def _validar_preinscriptos_existentes(resultados):
    """RN-23: activo = error; dado de baja = se reactiva."""
    por_cuil, por_dni = _existentes(Beneficiario, resultados, "cuil", "dni")
    for resultado in resultados:
        existente, conflicto = _buscar_existente(
            resultado, por_cuil, por_dni, "cuil", "dni"
        )
        if conflicto:
            resultado.error(
                "dni", "El DNI y el CUIL pertenecen a preinscriptos distintos en SISOC."
            )
            continue
        if not existente:
            resultado.accion_preinscripto = AccionPreinscripto.CREAR
            continue
        if existente.cuil != resultado.valor(
            "cuil"
        ) or existente.dni != resultado.valor("dni"):
            resultado.error(
                "dni",
                "El CUIL y el DNI no coinciden con los del preinscripto registrado "
                "en SISOC.",
            )
        elif not existente.is_deleted:
            resultado.error("cuil", "El preinscripto ya se encuentra en el programa.")
        else:
            resultado.advertencia(
                "cuil",
                "El preinscripto estaba dado de baja: se reactivará con los datos "
                "del Excel.",
            )
            resultado.accion_preinscripto = AccionPreinscripto.REACTIVAR
            resultado.beneficiario_existente = existente.pk


def _datos_titular(resultado):
    return {
        clave: resultado.valores.get(clave)
        for clave in COLUMNAS_POR_CLAVE
        if clave.startswith("titular_")
    }


def _agrupar_titulares(resultados):
    """RN-24/25: un titular puede repetirse; gana la primera aparición."""
    por_cuil, por_dni = {}, {}
    for resultado in resultados:
        cuil, dni = resultado.valor("titular_cuil"), resultado.valor("titular_dni")
        primero_cuil, primero_dni = por_cuil.get(cuil), por_dni.get(dni)
        if primero_cuil and primero_dni and primero_cuil is not primero_dni:
            resultado.error(
                "titular_dni",
                "El DNI y el CUIL del titular corresponden a titulares de filas "
                f"distintas ({primero_dni.numero_fila} y {primero_cuil.numero_fila}).",
            )
            continue
        primero = primero_cuil or primero_dni
        if primero:
            resultado.fila_titular = primero.numero_fila
            if _datos_titular(resultado) != _datos_titular(primero):
                resultado.advertencia(
                    "titular_cuil",
                    "Se usaron los datos del titular de la fila "
                    f"{primero.numero_fila}.",
                )
            continue
        resultado.fila_titular = resultado.numero_fila
        if cuil:
            por_cuil[cuil] = resultado
        if dni:
            por_dni[dni] = resultado


CAMPOS_UBICACION = ("provincia", "municipio", "localidad")


def _comparable(valor):
    if isinstance(valor, str):
        return normalizar(valor) or None
    return valor


def _diferencias(resultado, existente, campos):
    diferentes = []
    for campo in campos:
        atributo = f"{campo}_id" if campo in CAMPOS_UBICACION else campo
        valor_excel = resultado.valores.get(f"titular_{campo}")
        if _comparable(valor_excel) != _comparable(getattr(existente, atributo)):
            diferentes.append(campo)
    return diferentes


def _validar_titulares_existentes(resultados):
    """RN-26/27/28. S-03 (identidad al reactivar) se trata igual que RN-26."""
    por_cuil, por_dni = _existentes(
        Responsable, resultados, "titular_cuil", "titular_dni"
    )
    for resultado in resultados:
        if not resultado.valor("titular_cuil") or not resultado.valor("titular_dni"):
            continue
        existente, conflicto = _buscar_existente(
            resultado, por_cuil, por_dni, "titular_cuil", "titular_dni"
        )
        if conflicto:
            resultado.error(
                "titular_dni",
                "El DNI y el CUIL del titular pertenecen a personas distintas en SISOC.",
            )
            continue
        if not existente:
            resultado.accion_titular = AccionTitular.CREAR
            continue
        identidad = _diferencias(resultado, existente, CAMPOS_IDENTIDAD_TITULAR)
        for campo in identidad:
            resultado.error(
                f"titular_{campo}",
                "No coincide con el dato del titular registrado en SISOC.",
            )
        if identidad:
            continue
        resultado.titular_existente = existente.pk
        if existente.is_deleted:
            resultado.advertencia(
                "titular_cuil",
                "El titular estaba dado de baja: se reactivará con los datos del Excel.",
            )
            resultado.accion_titular = AccionTitular.REACTIVAR
        elif _diferencias(resultado, existente, CAMPOS_CONTACTO_TITULAR):
            resultado.advertencia(
                "titular_cuil",
                "Se actualizarán los datos de contacto y domicilio del titular.",
            )
            resultado.accion_titular = AccionTitular.ACTUALIZAR
        else:
            resultado.accion_titular = AccionTitular.EXISTENTE


def _heredar_accion_titular(resultados):
    """Las filas que repiten un titular informan lo que se hace con él en su primera fila."""
    por_fila = {resultado.numero_fila: resultado for resultado in resultados}
    for resultado in resultados:
        primero = por_fila.get(resultado.fila_titular)
        if primero and primero is not resultado:
            resultado.accion_titular = primero.accion_titular
            resultado.titular_existente = primero.titular_existente


def validar_filas(filas):
    """Valida [(numero_fila, datos)] y devuelve {numero_fila: ResultadoFila}."""
    filas = sorted(filas, key=lambda fila: fila[0])
    catalogos = Catalogos([datos for _, datos in filas])
    resultados = [validar_fila(numero, datos, catalogos) for numero, datos in filas]
    _validar_repetidos(resultados)
    _validar_padron(resultados)
    _validar_preinscriptos_existentes(resultados)
    _agrupar_titulares(resultados)
    _validar_titulares_existentes(resultados)
    _heredar_accion_titular(resultados)
    return {resultado.numero_fila: resultado for resultado in resultados}
