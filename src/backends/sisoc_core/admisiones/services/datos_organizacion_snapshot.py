"""Snapshot de los datos de la organizacion que precargan el informe tecnico.

Issue #2571: al cambiar la organizacion del comedor (o sus datos en el legajo)
con una admision en curso, el informe tecnico tomaba siempre los datos de la
organizacion vigente, aunque el tecnico eligiera "Continuar operando con la
Admision actual". La admision guarda en ``datos_organizacion_snapshot``:

- ``informe``: datos con los que se precarga el informe tecnico.
- ``legajo``: ultimo estado del legajo que el tecnico acepto (linea de base
  para detectar cambios y mostrar el modal de resincronizacion).

"Actualizar" pisa ambos con el legajo actual (y los informes editables);
"Continuar" solo mueve la linea de base y conserva los datos del informe.
"""

from django.db.models import Q
from django.utils import timezone

from admisiones.models.admisiones import Admision, InformeTecnico

# Campo del informe tecnico -> atributo de la organizacion.
CAMPOS_ORGANIZACION_INFORME = {
    "nombre_organizacion": "nombre",
    "cuit_organizacion": "cuit",
    "mail_organizacion": "email",
    "telefono_organizacion": "telefono",
    "domicilio_organizacion": "domicilio",
    "localidad_organizacion": "localidad",
    "provincia_organizacion": "provincia",
    "partido_organizacion": "partido",
}

# Etiquetas para listar en el modal los datos que cambiaron.
ETIQUETAS_DATOS_ORGANIZACION = {
    "nombre_organizacion": "Nombre",
    "cuit_organizacion": "CUIT",
    "mail_organizacion": "Mail",
    "telefono_organizacion": "Teléfono",
    "domicilio_organizacion": "Domicilio",
    "localidad_organizacion": "Localidad",
    "provincia_organizacion": "Provincia",
    "partido_organizacion": "Partido",
}

# Mismo criterio que ``AdmisionService.puede_editar_informe_tecnico``: un
# informe finalizado (DOCX generado, enviado a validar o validado) no se toca,
# para que sus datos no queden distintos del documento ya emitido.
INFORMES_EDITABLES = Q(estado="A subsanar") | Q(
    estado__in=["Iniciado", "Para revision"], estado_formulario="borrador"
)


def _organizacion_de(admision):
    return getattr(getattr(admision, "comedor", None), "organizacion", None)


def _admisiones_en_curso(using=None):
    return Admision.objects.using(using).filter(enviada_a_archivo=False)


def _datos_aplican_al_informe(admision):
    """Los datos de la organizacion solo importan si van a precargar un informe
    nuevo o pueden cambiar en uno editable."""
    informes = InformeTecnico.objects.filter(admision=admision)
    return not informes.exists() or informes.filter(INFORMES_EDITABLES).exists()


def datos_organizacion_para_informe(organizacion):
    """Datos serializables de ``organizacion`` con las claves del informe."""
    if not organizacion:
        return {}
    datos = {}
    for campo_informe, atributo in CAMPOS_ORGANIZACION_INFORME.items():
        valor = getattr(organizacion, atributo, None)
        valor = getattr(valor, "nombre", valor)
        datos[campo_informe] = "" if valor is None else str(valor)
    return datos


def _snapshot_valido(admision):
    snapshot = getattr(admision, "datos_organizacion_snapshot", None)
    if (
        isinstance(snapshot, dict)
        and isinstance(snapshot.get("informe"), dict)
        and isinstance(snapshot.get("legajo"), dict)
    ):
        return snapshot
    return None


def _guardar_snapshot(admision, snapshot):
    admision.datos_organizacion_snapshot = snapshot
    Admision.objects.filter(pk=admision.pk).update(datos_organizacion_snapshot=snapshot)


def asegurar_snapshot(admision):
    """Inicializa el snapshot con la organizacion actual si la admision no
    tiene uno (admisiones legacy o recien creadas) y lo devuelve."""
    if not admision or not admision.pk:
        return None
    snapshot = _snapshot_valido(admision)
    if snapshot is not None:
        return snapshot
    organizacion = _organizacion_de(admision)
    if not organizacion:
        return None
    datos = datos_organizacion_para_informe(organizacion)
    snapshot = {"informe": datos, "legajo": dict(datos)}
    _guardar_snapshot(admision, snapshot)
    return snapshot


def datos_organizacion_informe(admision):
    """Datos de organizacion para precargar el informe tecnico: los del
    snapshot de la admision o, si no hay snapshot, los del legajo actual."""
    snapshot = _snapshot_valido(admision)
    if snapshot is not None:
        return snapshot["informe"]
    return datos_organizacion_para_informe(_organizacion_de(admision))


def datos_organizacion_modificados(admision):
    """Etiquetas de los datos del legajo que cambiaron respecto de la linea de
    base aceptada en la admision. Vacio si no hay cambios o si ya no afectan al
    informe tecnico (todos sus informes estan finalizados)."""
    organizacion = _organizacion_de(admision)
    if not organizacion:
        return []
    snapshot = asegurar_snapshot(admision)
    if snapshot is None:
        return []
    actuales = datos_organizacion_para_informe(organizacion)
    modificados = [
        ETIQUETAS_DATOS_ORGANIZACION[campo]
        for campo, valor in actuales.items()
        if snapshot["legajo"].get(campo) != valor
    ]
    if not modificados or not _datos_aplican_al_informe(admision):
        return []
    return modificados


def datos_organizacion_desactualizados(admision):
    """Indica si hay datos del legajo que cambiaron y afectan al informe."""
    return bool(datos_organizacion_modificados(admision))


def sincronizar_datos_organizacion(admision, actualizar_informe):
    """Alinea la linea de base con el legajo actual. Con
    ``actualizar_informe`` tambien reemplaza los datos del informe tecnico
    (snapshot e informes editables de la admision)."""
    organizacion = _organizacion_de(admision)
    if not admision or not admision.pk or not organizacion:
        return
    actuales = datos_organizacion_para_informe(organizacion)
    snapshot = _snapshot_valido(admision)
    if actualizar_informe or snapshot is None:
        datos_informe = dict(actuales)
    else:
        datos_informe = snapshot["informe"]
    _guardar_snapshot(admision, {"informe": datos_informe, "legajo": actuales})
    if actualizar_informe:
        # ``update`` no aplica ``auto_now``: se setea ``modificado`` a mano.
        InformeTecnico.objects.filter(admision=admision).filter(
            INFORMES_EDITABLES
        ).update(**actuales, modificado=timezone.localdate())


def congelar_datos_previos(admisiones, organizacion):
    """Antes de cambiar la organizacion de un comedor o sus datos, fija el
    snapshot con los datos previos en las admisiones que aun no lo tienen,
    para que "Continuar operando" conserve la informacion original."""
    if not organizacion:
        return
    datos = datos_organizacion_para_informe(organizacion)
    snapshot = {"informe": datos, "legajo": dict(datos)}
    admisiones.filter(datos_organizacion_snapshot__isnull=True).update(
        datos_organizacion_snapshot=snapshot
    )


def congelar_por_cambio_de_organizacion_en_comedor(
    comedor_id, organizacion_anterior, using=None
):
    congelar_datos_previos(
        _admisiones_en_curso(using).filter(comedor_id=comedor_id),
        organizacion_anterior,
    )


def congelar_por_edicion_de_organizacion(organizacion_anterior, using=None):
    congelar_datos_previos(
        _admisiones_en_curso(using).filter(comedor__organizacion=organizacion_anterior),
        organizacion_anterior,
    )
