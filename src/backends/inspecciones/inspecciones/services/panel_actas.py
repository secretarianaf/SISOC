"""Actas en el backoffice: listado con filtros, detalle legible y archivos.

El detalle se arma desde la instantánea del acta (lo que se cerró y firmó),
con las etiquetas de la versión del formulario guardada en ella; nada se lee
del borrador. Las imágenes, la firma, las fotos de la notificación y el PDF
se sirven por vistas del panel (sesión + permiso de gestión), nunca por
``/media``.
"""

from django.db.models import Q
from django.http import Http404

from inspecciones.models import (
    Acta,
    ArchivoNotificacion,
    EventoInspeccion,
    ImagenInspeccion,
)
from inspecciones.services.asignaciones import (
    ESTADO_ACTA_ANULADAS,
    ESTADO_ACTA_PRUEBA,
    ESTADO_ACTA_VALIDAS,
)
from inspecciones.services.auditoria import ACCIONES_VISIBLES
from inspecciones.services.formato import fecha_hora_desde_texto, nombre_actor

SIN_DATO = "—"

# Justificaciones de advertencias: en qué respuesta se muestran.
JUSTIFICACIONES = {
    "presentes_superan": ("f10", "Presentes superan lo previsto"),
    "sin_personal_con_presentes": ("f10", "Hay presentes sin personal educativo"),
    "aulas_superan": ("f12", "Aulas funcionando superan las previstas"),
    "sin_estudiantes_con_aulas": ("f12", "Hay aulas funcionando sin estudiantes"),
}


def listar_actas_panel(*, fecha=None, inspector_id=None, provincia_id=None, estado=""):
    queryset = Acta.objects.select_related(
        "inspector", "escuela__provincia", "escuela__localidad_vinculada"
    )
    if fecha:
        queryset = queryset.filter(fecha_visita=fecha)
    if inspector_id:
        queryset = queryset.filter(inspector_id=inspector_id)
    if provincia_id:
        queryset = queryset.filter(escuela__provincia_id=provincia_id)
    if estado == ESTADO_ACTA_VALIDAS:
        queryset = queryset.filter(estado=Acta.Estado.FINALIZADA, es_prueba=False)
    elif estado == ESTADO_ACTA_ANULADAS:
        queryset = queryset.filter(estado=Acta.Estado.ANULADA)
    elif estado == ESTADO_ACTA_PRUEBA:
        queryset = queryset.filter(es_prueba=True)
    return queryset.order_by("-cerrada_at", "-id")


def escuela_del_acta(acta):
    """Nombre, provincia y localidad: del catálogo o, si no, de la instantánea."""
    escuela = acta.instantanea.get("payload", {}).get("escuela") or {}
    if acta.escuela_id:
        catalogo = acta.escuela
        return {
            "nombre": catalogo.nombre,
            "cueanexo": catalogo.cueanexo,
            "provincia": catalogo.provincia.nombre if catalogo.provincia_id else "",
            "localidad": catalogo.localidad,
        }
    return {
        "nombre": escuela.get("nombre", ""),
        "cueanexo": escuela.get("cue", ""),
        "provincia": "",
        "localidad": escuela.get("localidad", ""),
    }


def etiqueta_turno(acta):
    """Etiqueta del turno según la versión del formulario guardada en el acta."""
    formulario = (acta.instantanea or {}).get("formulario") or {}
    for turno in formulario.get("turnos", []):
        if turno.get("valor") == acta.turno:
            return turno.get("etiqueta", acta.turno)
    return acta.turno or SIN_DATO


def fila_de_acta(acta):
    return {
        "acta": acta,
        "escuela": escuela_del_acta(acta),
        "turno": etiqueta_turno(acta),
    }


def obtener_acta(numero):
    acta = (
        Acta.objects.select_related(
            "inspeccion",
            "inspector",
            "anulada_por",
            "escuela__provincia",
            "escuela__localidad_vinculada__municipio",
        )
        .filter(numero=numero)
        .first()
    )
    if acta is None:
        raise Http404("No existe el acta.")
    return acta


# --- Detalle -------------------------------------------------------------


def _obj(valor):
    return valor if isinstance(valor, dict) else {}


def _etiqueta(formulario, grupo, valor):
    for opcion in formulario.get("opciones", {}).get(grupo, []):
        if opcion.get("valor") == valor:
            return opcion.get("etiqueta", valor)
    return valor or SIN_DATO


def _cantidad(formulario, grupo, cantidad):
    cantidad = _obj(cantidad)
    if cantidad.get("condicion", "dato") == "dato":
        valor = cantidad.get("valor")
        return (SIN_DATO if valor is None else str(valor)), ""
    return _etiqueta(formulario, grupo, cantidad.get("condicion")), cantidad.get(
        "motivo", ""
    )


def _valor_conocido(cantidad):
    cantidad = _obj(cantidad)
    if cantidad.get("condicion", "dato") != "dato" or cantidad.get("valor") is None:
        return SIN_DATO
    return str(cantidad["valor"])


def _resumen(formulario, respuestas):
    return {
        "abierta": _etiqueta(formulario, "si_no", respuestas.get("f05")),
        "resultado": _etiqueta(formulario, "resultado", respuestas.get("resultado")),
        "motivo_parcial": respuestas.get("motivo_parcial", ""),
        "personal": (
            f"{_valor_conocido(respuestas.get('f10'))} / "
            f"{_valor_conocido(respuestas.get('f09'))}"
        ),
        "aulas": (
            f"{_valor_conocido(respuestas.get('f12'))} / "
            f"{_valor_conocido(respuestas.get('f11'))}"
        ),
    }


def _respuesta_f04(f04):
    if f04.get("imagen_uuid"):
        return "Adjunta (ver evidencia)", ""
    return "Sin foto", f04.get("motivo_sin_foto", "")


def _respuesta_f06(f06):
    if f06.get("nadie") is True:
        return "Nadie atiende", ""
    partes = [f06.get("nombre", ""), f06.get("funcion", "")]
    return " · ".join(p for p in partes if p) or SIN_DATO, ""


def _respuestas(payload, formulario):  # pylint: disable=too-many-locals
    """Filas F00–F16: ``{codigo, pregunta, respuesta, notas}``."""
    preguntas = formulario.get("preguntas", {})
    escuela = _obj(payload.get("escuela"))
    r = _obj(payload.get("respuestas"))
    resultado = r.get("resultado")
    cue = escuela.get("cue") or SIN_DATO
    nota_cue = ""
    if escuela.get("cue_desconocido") is True:
        cue, nota_cue = "No se conoce", escuela.get("motivo_sin_cue", "")
    adicionales = [
        im
        for im in payload.get("imagenes") or []
        if _obj(im).get("tipo") == "adicional"
    ]
    valores = {
        "f00": (escuela.get("nombre") or SIN_DATO, ""),
        "f01": (cue, nota_cue),
        "f02": (escuela.get("domicilio") or SIN_DATO, ""),
        "f03": (
            " · ".join(
                p for p in (escuela.get("localidad"), escuela.get("distrito")) if p
            )
            or SIN_DATO,
            "",
        ),
        "f04": _respuesta_f04(_obj(r.get("f04"))),
        "f05": (_etiqueta(formulario, "si_no", r.get("f05")), ""),
        "f06": _respuesta_f06(_obj(r.get("f06"))),
        "f07": (_etiqueta(formulario, "constatacion", r.get("f07")), ""),
        "f08": (_etiqueta(formulario, "constatacion", r.get("f08")), ""),
        "f09": _cantidad(formulario, "condicion_f09_f11", r.get("f09")),
        "f10": _cantidad(formulario, "condicion_f10_f12", r.get("f10")),
        "f11": _cantidad(formulario, "condicion_f09_f11", r.get("f11")),
        "f12": _cantidad(formulario, "condicion_f10_f12", r.get("f12")),
        "f13": ("Sí" if resultado == "cerrada" else "No", ""),
        "f14": (
            "Sí" if resultado == "no_ingreso" else "No",
            r.get("que_ocurrio", "") if resultado == "no_ingreso" else "",
        ),
        "f15": (f"{len(adicionales)} (ver evidencia)" if adicionales else "0", ""),
        "f16": (r.get("f16") or SIN_DATO, ""),
    }
    notas_extra = {}
    for clave, texto in _obj(r.get("justificaciones")).items():
        if texto and clave in JUSTIFICACIONES:
            codigo, etiqueta = JUSTIFICACIONES[clave]
            notas_extra.setdefault(codigo, []).append(f"{etiqueta}: {texto}")
    filas = []
    for codigo in sorted(valores):
        respuesta, nota = valores[codigo]
        notas = ([f"Motivo: {nota}"] if nota else []) + notas_extra.get(codigo, [])
        filas.append(
            {
                "codigo": codigo.upper(),
                "pregunta": preguntas.get(codigo, codigo.upper()),
                "respuesta": respuesta,
                "notas": notas,
            }
        )
    return filas


def _imagenes(instantanea, payload):
    descripciones = {
        _obj(im).get("uuid"): _obj(im).get("descripcion", "")
        for im in payload.get("imagenes") or []
    }
    evidencia = []
    numero_adicional = 0
    for imagen in instantanea.get("imagenes", []):
        tipo = imagen.get("tipo")
        if tipo == ImagenInspeccion.Tipo.FIRMA:
            continue
        if tipo == ImagenInspeccion.Tipo.INGRESO:
            titulo = "Ingreso (F04)"
        else:
            numero_adicional += 1
            titulo = f"Imagen adicional {numero_adicional}"
        evidencia.append(
            {
                "uuid": imagen.get("uuid"),
                "titulo": titulo,
                "descripcion": imagen.get("descripcion")
                or descripciones.get(imagen.get("uuid"), ""),
                "capturada_at": fecha_hora_desde_texto(imagen.get("capturada_at")),
                "subida_at": fecha_hora_desde_texto(imagen.get("subida_at")),
            }
        )
    return evidencia


def _ubicacion(payload, formulario):
    ubicacion = _obj(payload.get("ubicacion"))
    lat, lng = ubicacion.get("lat"), ubicacion.get("lng")
    return {
        "fuente": _etiqueta(formulario, "fuente_ubicacion", ubicacion.get("fuente")),
        "es_gps": ubicacion.get("fuente") == "gps",
        "lat": lat,
        "lng": lng,
        "tiene_coordenadas": isinstance(lat, (int, float))
        and isinstance(lng, (int, float)),
        "precision_m": ubicacion.get("precision_m"),
        "capturada_at": fecha_hora_desde_texto(ubicacion.get("capturada_at")),
        "motivo_sin_gps": ubicacion.get("motivo_sin_gps", ""),
    }


def _recepcion(payload, formulario):
    firma = _obj(payload.get("firma"))
    tipo = firma.get("tipo")
    return {
        "tipo": tipo,
        "es_firma": tipo == "firma",
        "nombre": firma.get("nombre", ""),
        "cargo": firma.get("cargo", ""),
        "imagen_uuid": firma.get("imagen_uuid") if tipo == "firma" else None,
        "firmada_at": fecha_hora_desde_texto(
            firma.get("firmada_at") or firma.get("registrada_at")
        ),
        "texto_mostrado": firma.get("texto_mostrado", ""),
        "motivo_tipo": (
            _etiqueta(formulario, "excepcion_firma", firma.get("motivo_tipo"))
            if tipo == "excepcion"
            else ""
        ),
        "motivo": firma.get("motivo", ""),
    }


def _notificaciones(acta):
    notificaciones = (
        acta.notificaciones.select_related("cargada_por")
        .prefetch_related("archivos")
        .order_by("-version")
    )
    return [
        {
            "version": n.version,
            "cargada_at": n.cargada_at,
            "cargada_por": nombre_actor(n.cargada_por),
            "notificada_at": n.notificada_at,
            "receptor": " · ".join(
                p for p in (n.receptor_nombre, n.receptor_cargo) if p
            ),
            "condicion_firma": n.get_condicion_firma_display(),
            "motivo": n.motivo,
            "observaciones": n.observaciones,
            "motivo_correccion": n.motivo_correccion,
            "archivos": [{"uuid": a.uuid, "orden": a.orden} for a in n.archivos.all()],
        }
        for n in notificaciones
    ]


def _historial(acta):
    eventos = acta.inspeccion.eventos.filter(accion__in=ACCIONES_VISIBLES).order_by(
        "at", "id"
    )
    return [
        {
            "at": evento.at,
            "accion": evento.get_accion_display(),
            "codigo": evento.accion,
            "actor": evento.actor_nombre,
            "motivo": (
                _obj(evento.detalle).get("motivo", "")
                if evento.accion == EventoInspeccion.Accion.ANULADA
                else ""
            ),
        }
        for evento in eventos
    ]


def detalle_acta_panel(acta):
    instantanea = acta.instantanea or {}
    payload = _obj(instantanea.get("payload"))
    formulario = _obj(instantanea.get("formulario"))
    inspector = _obj(instantanea.get("inspector"))
    return {
        "acta": acta,
        "escuela": escuela_del_acta(acta),
        "escuela_catalogo": acta.escuela if acta.escuela_id else None,
        "escuela_snapshot": _obj(payload.get("escuela")),
        "carga_manual": instantanea.get("escuela_carga_manual", False),
        "turno": etiqueta_turno(acta),
        "formulario_version": formulario.get("version") or acta.formulario_version,
        "inspector_nombre": inspector.get("nombre") or nombre_actor(acta.inspector),
        "inspector_usuario": inspector.get("username") or acta.inspector.get_username(),
        "iniciada_at": fecha_hora_desde_texto(payload.get("creada_at")),
        "resumen_acta": _resumen(formulario, _obj(payload.get("respuestas"))),
        "respuestas": _respuestas(payload, formulario),
        "evidencia": _imagenes(instantanea, payload),
        "ubicacion": _ubicacion(payload, formulario),
        "recepcion": _recepcion(payload, formulario),
        "notificaciones": _notificaciones(acta),
        "historial": _historial(acta),
        "motivo_nueva_visita": payload.get("motivo_nueva_visita", ""),
    }


# --- Archivos ------------------------------------------------------------


def imagen_del_acta(acta, imagen_uuid):
    """Foto o firma de la inspección del acta (sólo las de esa inspección)."""
    imagen = ImagenInspeccion.objects.filter(
        inspeccion_id=acta.inspeccion_id, uuid=imagen_uuid
    ).first()
    if imagen is None or not imagen.archivo:
        raise Http404("No existe la imagen.")
    return imagen


def archivo_notificacion_del_acta(acta, archivo_uuid):
    archivo = ArchivoNotificacion.objects.filter(
        Q(notificacion__acta=acta), uuid=archivo_uuid
    ).first()
    if archivo is None or not archivo.archivo:
        raise Http404("No existe el archivo.")
    return archivo


def pdf_del_acta(acta):
    if not acta.pdf:
        raise Http404("El PDF todavía no está disponible.")
    return acta
