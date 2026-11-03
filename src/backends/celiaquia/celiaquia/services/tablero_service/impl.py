"""Tablero de Celiaquía: datos agregados para la pantalla de seguimiento.

Solo cuenta beneficiarios (los responsables no reciben la prestación ni ocupan
cupo) de legajos y expedientes sin borrado lógico. La provincia es la del
ciudadano, igual que el cupo (`cupo_service`) y el Reporter (`reporte_service`).
No devuelve datos de personas: solo conteos, por provincia o por expediente.
"""

import re
from collections import defaultdict

from django.db.models import Count, Min, Q
from django.utils import timezone

from core.models import Provincia  # pylint: disable=import-error

from celiaquia.models import (
    EstadoCupo,
    ExpedienteCiudadano,
    HistorialValidacionTecnica,
    ProvinciaCupo,
    RegistroErroneo,
    ResultadoSintys,
    RevisionTecnico,
    SubsanacionObservacion,
    TipoSubsanacion,
)

ESTADO_CRUCE_FINALIZADO = "CRUCE_FINALIZADO"
ROLES_BENEFICIARIO = (
    ExpedienteCiudadano.ROLE_BENEFICIARIO,
    ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
)
SIN_PROVINCIA = "Sin provincia"
PROVINCIA = "ciudadano__provincia__nombre"

_APROBADO = Q(revision_tecnico=RevisionTecnico.APROBADO)
# Titular = dentro del cupo, activo, aprobado y con MATCH (`pago_service`).
_TITULAR = (
    Q(estado_cupo=EstadoCupo.DENTRO, es_titular_activo=True)
    & _APROBADO
    & Q(resultado_sintys=ResultadoSintys.MATCH)
)

# Conteos de legajos. Las claves son las que lee el JS del tablero.
CONTEOS_LEGAJO = {
    "leg": Count("id"),
    "pend": Count("id", filter=Q(revision_tecnico=RevisionTecnico.PENDIENTE)),
    "apr": Count("id", filter=_APROBADO),
    "rech": Count("id", filter=Q(revision_tecnico=RevisionTecnico.RECHAZADO)),
    "sub": Count(
        "id",
        filter=Q(
            revision_tecnico__in=[RevisionTecnico.SUBSANAR, RevisionTecnico.SUBSANADO]
        ),
    ),
    "match": Count("id", filter=_APROBADO & Q(resultado_sintys=ResultadoSintys.MATCH)),
    "nomatch": Count(
        "id", filter=_APROBADO & Q(resultado_sintys=ResultadoSintys.NO_MATCH)
    ),
    "sincruce": Count(
        "id", filter=_APROBADO & Q(resultado_sintys=ResultadoSintys.SIN_CRUCE)
    ),
    "tit": Count("id", filter=_TITULAR),
    "susp": Count(
        "id", filter=Q(estado_cupo=EstadoCupo.DENTRO, es_titular_activo=False)
    ),
    "fuera": Count("id", filter=Q(estado_cupo=EstadoCupo.FUERA)),
}
CONTEOS_PROVINCIA = {
    "exp": Count("expediente", distinct=True),
    "expProc": Count(
        "expediente",
        distinct=True,
        filter=~Q(expediente__estado__nombre=ESTADO_CRUCE_FINALIZADO),
    ),
    "per": Count("ciudadano", distinct=True),
    **CONTEOS_LEGAJO,
}

# Tramos de edad de la pirámide: (etiqueta, edad máxima incluida).
TRAMOS_EDAD = (
    ("0-5", 5),
    ("6-12", 12),
    ("13-17", 17),
    ("18-29", 29),
    ("30-44", 44),
    ("45-64", 64),
    ("65+", None),
)
SEXOS = {"Femenino": "F", "Masculino": "M"}

# Motivos de rechazo: el motivo es texto libre (trae nombres), así que se
# clasifica por palabras clave y el texto nunca sale del servidor. Un texto
# puede mencionar más de un motivo: cuenta en cada uno. `\b` reconoce letras
# con tilde y ñ, así "años" o "Ríos" no se leen como "OS".
SIN_MOTIVO = "Sin motivo registrado"
OTRO_MOTIVO = "Otro motivo"
MOTIVOS_RECHAZO = (
    (
        "Diagnóstico no acreditado",
        re.compile(r"diagn|diag:|1408|anatomopatol|m[eé]dico", re.I),
    ),
    (
        "Tiene obra social",
        re.compile(r"obra social|\bos\b|codem", re.I),
    ),
    (
        "Documento de identidad (RENAPER / DNI)",
        re.compile(r"renaper|dni|no corresponde a la persona", re.I),
    ),
    (
        "Domicilio en otra provincia",
        re.compile(r"otra provincia|otra pcia|vivir en la pcia", re.I),
    ),
    ("Falta vínculo o responsable", re.compile(r"v[ií]nculo|adulto responsable", re.I)),
    ("Baja a pedido de la provincia", re.compile(r"\bbaja\b", re.I)),
)

# Errores de la carga masiva: `mensaje_error` se vacía cuando el registro se
# corrige o se procesa, así que "sin mensaje" son mayormente errores resueltos.
SIN_MENSAJE = "Corregido o sin mensaje"
ERRORES_IMPORTACION = (
    ("field 'documento' expected a number", "Documento no numérico"),
    ("documento es obligatorio", "Falta documento"),
    ("field 'altura' expected a number", "Altura no numérica"),
    ("municipio inválido para la provin", "Municipio no corresponde a la provincia"),
    ("especificar municipio", "Falta municipio"),
    ("fecha de nacimiento inválida", "Fecha de nacimiento inválida"),
)


def legajos_del_tablero(provincias_visibles=None):
    """Legajos que cuenta el tablero.

    `provincias_visibles` queda para cuando se defina el alcance por usuario:
    None = todas las provincias.
    """
    legajos = ExpedienteCiudadano.objects.filter(
        expediente__deleted_at__isnull=True,
        rol__in=ROLES_BENEFICIARIO,
    )
    if provincias_visibles is not None:
        legajos = legajos.filter(ciudadano__provincia_id__in=provincias_visibles)
    return legajos


def _nombre(provincia):
    return provincia or SIN_PROVINCIA


def filas_por_provincia(legajos):
    cupos = dict(
        ProvinciaCupo.objects.values_list("provincia__nombre", "total_asignado")
    )
    filas = []
    for fila in (
        legajos.values(PROVINCIA).annotate(**CONTEOS_PROVINCIA).order_by("-leg")
    ):
        provincia = fila.pop(PROVINCIA)
        filas.append({"p": _nombre(provincia), "cupo": cupos.get(provincia, 0), **fila})
    return filas


def _tramo(fecha_nacimiento, hoy):
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    for indice, (_, maximo) in enumerate(TRAMOS_EDAD):
        if maximo is None or edad <= maximo:
            return indice
    return len(TRAMOS_EDAD) - 1


def titulares_por_edad_y_sexo(legajos, hoy=None):
    """Por provincia: {"F": [...], "M": [...]}, un valor por tramo de edad.

    Quedan afuera los titulares sin fecha de nacimiento o sin sexo F/M.
    """
    hoy = hoy or timezone.localdate()
    piramide = defaultdict(
        lambda: {"F": [0] * len(TRAMOS_EDAD), "M": [0] * len(TRAMOS_EDAD)}
    )
    for provincia, sexo, nacimiento, cantidad in (
        legajos.filter(_TITULAR, ciudadano__fecha_nacimiento__isnull=False)
        .values_list(PROVINCIA, "ciudadano__sexo__sexo", "ciudadano__fecha_nacimiento")
        .annotate(cantidad=Count("id"))
        .order_by()
    ):
        clave = SEXOS.get(sexo)
        if clave:
            piramide[_nombre(provincia)][clave][_tramo(nacimiento, hoy)] += cantidad
    return dict(piramide)


def clasificar_motivo_de_rechazo(motivo):
    """Categorías que menciona el motivo; nunca vacío, para que toda rechazada
    cuente en alguna barra."""
    if not motivo:
        return [SIN_MOTIVO]
    categorias = [n for n, patron in MOTIVOS_RECHAZO if patron.search(motivo)]
    return categorias or [OTRO_MOTIVO]


def motivos_de_rechazo(legajos):
    """Por provincia: rechazadas que mencionan cada motivo (último motivo cargado)."""
    rechazados = dict(
        legajos.filter(revision_tecnico=RevisionTecnico.RECHAZADO).values_list(
            "id", PROVINCIA
        )
    )
    ultimo_motivo = {}
    for legajo_id, motivo in (
        HistorialValidacionTecnica.objects.filter(
            legajo_id__in=rechazados, estado_nuevo=RevisionTecnico.RECHAZADO
        )
        .exclude(motivo__isnull=True)
        .exclude(motivo__regex=r"^\s*$")
        .order_by("legajo_id", "-creado_en", "-id")
        .values_list("legajo_id", "motivo")
    ):
        ultimo_motivo.setdefault(legajo_id, motivo)

    motivos = defaultdict(lambda: defaultdict(int))
    for legajo_id, provincia in rechazados.items():
        for categoria in clasificar_motivo_de_rechazo(ultimo_motivo.get(legajo_id)):
            motivos[_nombre(provincia)][categoria] += 1
    return {provincia: dict(conteo) for provincia, conteo in motivos.items()}


def motivos_de_subsanacion(legajos):
    """Por provincia: observaciones de subsanación por tipo."""
    etiquetas = dict(TipoSubsanacion.choices)
    motivos = defaultdict(dict)
    for provincia, tipo, cantidad in (
        SubsanacionObservacion.objects.filter(subsanacion__legajo__in=legajos)
        .values_list(f"subsanacion__legajo__{PROVINCIA}", "tipo")
        .annotate(cantidad=Count("id"))
        .order_by()
    ):
        motivos[_nombre(provincia)][etiquetas.get(tipo, tipo)] = cantidad
    return dict(motivos)


def _tipo_de_error(mensaje):
    texto = (mensaje or "").strip().lower()
    if not texto:
        return SIN_MENSAJE
    for fragmento, tipo in ERRORES_IMPORTACION:
        if fragmento in texto:
            return tipo
    return "Otro"


def errores_de_importacion(provincias_visibles=None):
    """Por provincia: filas del Excel masivo que no se pudieron cargar, por tipo.

    El registro erróneo no tiene ciudadano: la provincia es la de los ciudadanos
    del expediente y, si no tiene legajos, la del usuario que lo cargó.
    """
    registros = RegistroErroneo.objects.filter(expediente__deleted_at__isnull=True)
    expedientes = set(registros.values_list("expediente_id", flat=True))
    provincia_de = dict(
        ExpedienteCiudadano.all_objects.filter(expediente_id__in=expedientes)
        .values("expediente_id")
        .annotate(provincia=Min("ciudadano__provincia_id"))
        .values_list("expediente_id", "provincia")
    )
    errores = defaultdict(lambda: defaultdict(int))
    for expediente_id, provincia_usuario, mensaje in registros.values_list(
        "expediente_id",
        "expediente__usuario_provincia__profile__provincia_id",
        "mensaje_error",
    ):
        provincia = provincia_de.get(expediente_id) or provincia_usuario
        if provincias_visibles is not None and provincia not in provincias_visibles:
            continue
        errores[provincia][_tipo_de_error(mensaje)] += 1
    nombres = dict(
        Provincia.objects.filter(id__in=[p for p in errores if p]).values_list(
            "id", "nombre"
        )
    )
    return {
        _nombre(nombres.get(provincia)): dict(conteo)
        for provincia, conteo in errores.items()
    }


def expedientes_del_tablero(legajos, hoy=None):
    """Una fila por expediente y provincia del ciudadano (puede tener dos)."""
    hoy = hoy or timezone.localdate()
    filas = []
    for fila in (
        legajos.values(
            "expediente_id",
            "expediente__numero_expediente",
            "expediente__estado__nombre",
            "expediente__fecha_creacion",
            PROVINCIA,
        )
        .annotate(**CONTEOS_LEGAJO)
        .order_by("expediente_id")
    ):
        creado = fila.pop("expediente__fecha_creacion")
        filas.append(
            {
                "id": fila.pop("expediente_id"),
                "n": (fila.pop("expediente__numero_expediente") or "").strip(),
                "est": fila.pop("expediente__estado__nombre"),
                "d": (hoy - timezone.localdate(creado)).days,
                "p": _nombre(fila.pop(PROVINCIA)),
                **fila,
            }
        )
    return filas


def construir_tablero(provincias_visibles=None):
    """Todos los datos de la pantalla. Los filtros de provincia y expediente
    se aplican en el navegador sobre estos datos, que ya vienen limitados a
    `provincias_visibles`."""
    legajos = legajos_del_tablero(provincias_visibles)
    return {
        "provincias": filas_por_provincia(legajos),
        "piramide": titulares_por_edad_y_sexo(legajos),
        "rechazo": motivos_de_rechazo(legajos),
        "subsanacion": motivos_de_subsanacion(legajos),
        "errores": errores_de_importacion(provincias_visibles),
        "expedientes": expedientes_del_tablero(legajos),
        "tramos": [etiqueta for etiqueta, _ in TRAMOS_EDAD],
    }
