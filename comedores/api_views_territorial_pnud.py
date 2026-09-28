"""Seguimientos PNUD (N22) en la API territorial.

Abordaje Comunitario tiene cinco formularios de seguimiento propios que el
territorial carga desde la app sin asignacion previa. El formulario lo decide el
PROGRAMA del comedor en SISOC ("FLUJO APP PNUD" §4.2): Linea Secos → FORM-PNUD-
SECOS; Linea Tradicional → FORM II A / II A.1 / II B / II B.1 (el tecnico elige
modalidad y prestacion). Separado del viewset territorial para mantener ese
modulo acotado; se mezcla como mixin.
"""

import json
import posixpath
from urllib.parse import unquote, urlparse

from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from comedores.api_serializers import NoSaveSerializer
from comedores.models import ComedorDatosConvenioPnud
from comedores.services.comedor_service import ComedorService
from comedores.utils import (
    is_abordaje_comunitario_linea_secos_program,
    is_abordaje_comunitario_linea_tradicional_program,
    usa_datos_convenio_pnud,
)
from core.utils import format_fecha_django
from relevamientos.models import SeguimientoPnud
from relevamientos.pnud_formularios import campos_tabla

# Tope de las respuestas de un seguimiento PNUD (N22): los cinco formularios en
# papel caben holgados; evita que un cliente guarde blobs (p.ej. firmas base64).
MAX_DATOS_PNUD_BYTES = 512 * 1024

DIAS_SEMANA = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)
COMIDAS_PNUD = ("desayuno", "almuerzo", "merienda", "merienda_reforzada", "cena")

LINEA_SECOS = "secos"
LINEA_TRADICIONAL = "tradicional"
# Ids de fixture (comedores/fixtures/programas.json) como respaldo del nombre.
_PROGRAMA_ID_POR_LINEA = {3: LINEA_SECOS, 4: LINEA_TRADICIONAL}
FORMULARIOS_POR_LINEA = {
    LINEA_SECOS: (SeguimientoPnud.FORMULARIO_SECOS,),
    LINEA_TRADICIONAL: (
        SeguimientoPnud.FORMULARIO_II_A,
        SeguimientoPnud.FORMULARIO_II_A1,
        SeguimientoPnud.FORMULARIO_II_B,
        SeguimientoPnud.FORMULARIO_II_B1,
    ),
}


def linea_pnud(comedor):
    """``"secos"``, ``"tradicional"`` o ``None`` si el comedor no es PNUD (§3)."""
    if is_abordaje_comunitario_linea_secos_program(comedor):
        return LINEA_SECOS
    if is_abordaje_comunitario_linea_tradicional_program(comedor):
        return LINEA_TRADICIONAL
    # El id de fixture es solo respaldo para un programa SIN nombre: un
    # "Alimentar comunidad" que en otra base tenga id 3 no debe pasar por Secos.
    programa = getattr(comedor, "programa", None)
    if programa is not None and (getattr(programa, "nombre", "") or "").strip():
        return None
    return _PROGRAMA_ID_POR_LINEA.get(getattr(comedor, "programa_id", None))


def formulario_permitido(comedor, formulario):
    linea = linea_pnud(comedor)
    return linea is not None and formulario in FORMULARIOS_POR_LINEA[linea]


def datos_comedor_pnud(comedor):
    """Datos del comedor para el encabezado y el ruteo de los formularios PNUD."""
    return {
        "programa_id": comedor.programa_id,
        "linea_pnud": linea_pnud(comedor),
        "codigo_proyecto": comedor.codigo_de_proyecto,
        "id_externo": comedor.id_externo,
    }


def _fecha_iso(valor):
    # Siempre en hora de Buenos Aires (-03:00): el 201 y el GET no deben diferir.
    return timezone.localtime(valor).isoformat() if valor else None


def _nombre_usuario(usuario):
    if usuario is None:
        return None
    return usuario.get_full_name() or usuario.get_username()


def serialize_seguimiento_pnud(seguimiento, propio=False):
    """Instancia PNUD (N22) con los metadatos del ciclo del coordinador (N16).

    Las respuestas y las observaciones del coordinador (pueden citar datos
    personales del entrevistado) solo van al tecnico que la cargo.
    """
    data = {
        "id": seguimiento.id,
        "comedor": seguimiento.comedor_id,
        "formulario": seguimiento.formulario,
        "fecha_hora": _fecha_iso(seguimiento.fecha_hora),
        "tecnico": seguimiento.tecnico_id,
        "tecnico_nombre": _nombre_usuario(seguimiento.tecnico),
        "estado_validacion": seguimiento.estado_validacion,
        "observaciones_coordinador": (
            seguimiento.observaciones_coordinador if propio else None
        ),
        "fecha_revision_coordinador": _fecha_iso(
            seguimiento.fecha_revision_coordinador
        ),
        "origen": seguimiento.origen,
        "client_uuid": seguimiento.client_uuid,
    }
    if propio:
        data["datos"] = seguimiento.datos or {}
    return data


def seguimientos_pnud_payload(comedor, usuario):
    """Instancias del comedor; las respuestas (con datos personales del
    entrevistado) solo en las del propio tecnico, para "Corregir y reenviar"."""
    items = [
        serialize_seguimiento_pnud(s, propio=s.tecnico_id == usuario.id)
        for s in comedor.seguimientos_pnud.select_related("tecnico")
    ]
    return {"total": len(items), "items": items}


def prestaciones_aprobadas_por_dia(comedor):
    """Destinatarios aprobados por dia y comida, para precargar los PNUD (N22).

    Misma fuente que el detalle web y ``/prestacion-alimentaria/``: el convenio
    PNUD si el programa lo usa; si no, el informe tecnico finalizado efectivo
    de la admision vigente. SISOC no distingue presencial/vianda en lo
    aprobado: es un total por dia y comida.

    ``por_comida`` (destinatarios aprobados de cada prestacion, formularios de
    Modulo): las prestaciones financiadas diarias del convenio PNUD si estan
    cargadas; si no, el maximo diario. ``por_comida_fuente`` dice cual se uso.
    """
    fuente, origen = None, None
    if usa_datos_convenio_pnud(comedor):
        origen = ComedorDatosConvenioPnud.objects.filter(comedor=comedor).first()
        fuente = "convenio_pnud" if origen else None
    else:
        admision = ComedorService.get_admision_vigente_pwa(comedor.id)
        if admision:
            origen = ComedorService.get_informe_tecnico_finalizado_efectivo(admision)
            fuente = "informe_tecnico" if origen else None
    por_dia = {
        dia: {
            comida: (
                getattr(origen, f"aprobadas_{comida}_{dia}", None) if origen else None
            )
            for comida in COMIDAS_PNUD
        }
        for dia in DIAS_SEMANA
    }
    por_comida, por_comida_fuente = {}, {}
    for comida in COMIDAS_PNUD:
        financiadas = getattr(
            origen, f"prestaciones_financiadas_diarias_{comida}", None
        )
        if financiadas is not None:
            por_comida[comida] = financiadas
            por_comida_fuente[comida] = "financiadas_diarias"
            continue
        valores = [por_dia[dia][comida] for dia in DIAS_SEMANA]
        valores = [valor for valor in valores if valor is not None]
        por_comida[comida] = max(valores) if valores else None
        por_comida_fuente[comida] = "maximo_diario" if valores else None
    return {
        "fuente": fuente,
        "por_dia": por_dia,
        "por_comida": por_comida,
        "por_comida_fuente": por_comida_fuente,
    }


def _error(mensaje, codigo=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({"detail": mensaje, **extra}, status=codigo)


def _leer_texto(request, campo):
    """Texto opcional del body: (valor o None, Response 400 si no es texto)."""
    valor = request.data.get(campo)
    if valor is None:
        return None, None
    if not isinstance(valor, str):
        return None, _error(f"'{campo}' debe ser texto.")
    return valor.strip() or None, None


def es_url_de_firma(valor, comedor, hosts):
    """¿``valor`` es una URL que devolvio ``/firma/`` para este comedor?

    Ruta relativa, o http(s) de un host propio (el de la API o el del
    storage); sin ``..``; y dentro de ``firmas/<comedor>/`` del storage.
    """
    if not isinstance(valor, str):
        return False
    url = urlparse(valor)
    if url.scheme or url.netloc:
        if url.scheme not in ("http", "https") or url.netloc not in hosts:
            return False
    ruta = unquote(url.path)
    if ".." in ruta.split("/"):
        return False
    prefijo = urlparse(default_storage.url(f"firmas/{comedor.id}/")).path
    return posixpath.normpath(ruta).startswith(prefijo.rstrip("/") + "/")


def _hosts_propios(request):
    hosts = {request.get_host(), urlparse(default_storage.url("firmas/")).netloc}
    return {host for host in hosts if host}


def _firmas_invalidas(datos, comedor, request):
    """Claves de firma cuyo valor no es una URL de ``/firma/`` de este comedor."""
    hosts = _hosts_propios(request)
    return [
        clave
        for clave, valor in datos.items()
        if "firma" in clave
        and valor not in (None, "")
        and not es_url_de_firma(valor, comedor, hosts)
    ]


def _tablas_invalidas(datos, formulario):
    """Campos tabla (hijos) que no llegan como lista de objetos."""
    return [
        nombre
        for nombre in campos_tabla(formulario)
        if datos.get(nombre) not in (None, "")
        and not (
            isinstance(datos[nombre], list)
            and all(isinstance(fila, dict) for fila in datos[nombre])
        )
    ]


class SeguimientosPnudTerritorialMixin:
    """Acciones PNUD del ``TerritorialComedorViewSet``.

    Usa del viewset: ``_comedor_de_mi_zona``, ``_fuera_de_zona``,
    ``_leer_client_uuid``, ``_falta_client_uuid`` y ``_fecha_invalida``.
    """

    @staticmethod
    def _leer_datos_pnud(request, comedor, formulario):
        """``datos`` validado (objeto JSON, tope de tamaño) o una Response 400."""
        datos = request.data.get("datos")
        if not isinstance(datos, dict):
            return None, _error("'datos' debe ser un objeto con las respuestas.")
        # Estos formularios NO actualizan el legajo del comedor: un bloque
        # `comedor` que llegue por error se descarta.
        datos = {clave: valor for clave, valor in datos.items() if clave != "comedor"}
        tamanio = len(json.dumps(datos, ensure_ascii=False).encode("utf-8"))
        if tamanio > MAX_DATOS_PNUD_BYTES:
            return None, _error("Las respuestas exceden el tamaño máximo (512 KB).")
        tablas = _tablas_invalidas(datos, formulario)
        if tablas:
            return None, _error(
                "Estos campos deben ser listas de filas: " + ", ".join(tablas) + "."
            )
        invalidas = _firmas_invalidas(datos, comedor, request)
        if invalidas:
            return None, _error(
                "Las firmas deben subirse con /firma/ de este comedor: "
                + ", ".join(invalidas)
                + "."
            )
        return datos, None

    def _leer_fecha_hora(self, request, seguimiento):
        fecha_hora, error = _leer_texto(request, "fecha_hora")
        if error is not None:
            return error
        if fecha_hora:
            try:
                seguimiento.fecha_hora = format_fecha_django(fecha_hora)
            except (ValueError, TypeError):
                return self._fecha_invalida("fecha_hora")
        return None

    @action(detail=True, methods=["get", "post"], url_path="seguimientos-pnud")
    def seguimientos_pnud(  # pylint: disable=too-many-return-statements
        self, request, pk=None
    ):
        """Seguimientos PNUD (N22) sobre un comedor de la zona, sin asignación.

        GET: instancias del comedor, aprobados para precargar y datos del
        programa. POST: alta idempotente por ``client_uuid``; entra a
        validación del coordinador (N16).
        """
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()

        if request.method == "GET":
            data = seguimientos_pnud_payload(comedor, request.user)
            data.update(datos_comedor_pnud(comedor))
            data["prestaciones_aprobadas"] = prestaciones_aprobadas_por_dia(comedor)
            return Response(data)

        client_uuid = self._leer_client_uuid(request)
        if not client_uuid:
            return self._falta_client_uuid()

        existente = SeguimientoPnud.objects.filter(client_uuid=client_uuid).first()
        if existente is not None:
            return self._respuesta_existente(existente, comedor, request)

        linea = linea_pnud(comedor)
        if linea is None:
            return _error(
                "El comedor no pertenece a un programa PNUD (Abordaje Comunitario "
                "- Línea Secos o Línea Tradicional)."
            )
        formulario, error = _leer_texto(request, "formulario")
        if error is not None:
            return error
        validos = FORMULARIOS_POR_LINEA[linea]
        if not formulario_permitido(comedor, formulario):
            return _error(
                f"'formulario' no corresponde al programa del comedor. "
                f"Válidos: {', '.join(validos)}."
            )
        datos, error = self._leer_datos_pnud(request, comedor, formulario)
        if error is not None:
            return error

        seguimiento = SeguimientoPnud(
            comedor=comedor,
            tecnico=request.user,
            formulario=formulario,
            datos=datos,
            origen=SeguimientoPnud.ORIGEN_APP,
            asignado_desde_sisoc=False,
            client_uuid=client_uuid,
            estado_validacion=SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE,
        )
        error = self._leer_fecha_hora(request, seguimiento)
        if error is not None:
            return error

        try:
            with transaction.atomic():
                seguimiento.save()
        except IntegrityError:
            # Alta concurrente con el mismo uuid: mismas reglas que el reintento.
            existente = SeguimientoPnud.objects.filter(client_uuid=client_uuid).first()
            if existente is None:
                raise
            return self._respuesta_existente(existente, comedor, request)
        return Response(
            serialize_seguimiento_pnud(seguimiento, propio=True),
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _respuesta_existente(existente, comedor, request):
        """Reintento con un ``client_uuid`` ya usado: 200 si es el mismo alta."""
        if (
            existente.comedor_id != comedor.id
            or existente.tecnico_id != request.user.id
        ):
            return _error(
                "El 'client_uuid' ya se usó en otro seguimiento.",
                status.HTTP_409_CONFLICT,
            )
        return Response(serialize_seguimiento_pnud(existente, propio=True))

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"seguimientos-pnud/(?P<pnud_id>[0-9]+)",
    )
    def corregir_seguimiento_pnud(  # pylint: disable=too-many-return-statements
        self, request, pk=None, pnud_id=None
    ):
        """Corrección del técnico (N16): reemplaza las respuestas y reenvía.

        Permitida mientras no esté ``Validado`` (``Pendiente`` o ``A subsanar``),
        igual que el PATCH de relevamientos y seguimientos PAC.
        """
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()
        with transaction.atomic():
            # Bloqueo de fila: una revisión del coordinador en paralelo no puede
            # quedar pisada (un Validado nunca vuelve a Pendiente).
            seguimiento = (
                SeguimientoPnud.objects.select_for_update()
                .filter(pk=pnud_id, comedor=comedor)
                .first()
            )
            if seguimiento is None:
                return _error(
                    "Seguimiento PNUD no encontrado.", status.HTTP_404_NOT_FOUND
                )
            if seguimiento.tecnico_id != request.user.id:
                return _error(
                    "Solo el técnico que lo cargó puede corregirlo.",
                    status.HTTP_403_FORBIDDEN,
                )
            if seguimiento.esta_validado:
                return _error(
                    "Validado por el coordinador: no admite modificaciones.",
                    status.HTTP_409_CONFLICT,
                    estado_validacion=seguimiento.estado_validacion,
                )
            # El programa del comedor pudo cambiar desde el alta.
            if not formulario_permitido(comedor, seguimiento.formulario):
                return _error(
                    "El comedor ya no pertenece a un programa PNUD compatible con "
                    "este formulario."
                )
            datos, error = self._leer_datos_pnud(
                request, comedor, seguimiento.formulario
            )
            if error is None:
                error = self._leer_fecha_hora(request, seguimiento)
            if error is not None:
                return error
            seguimiento.datos = datos
            # "A subsanar" (o sin enviar) vuelve a la bandeja del coordinador.
            seguimiento.estado_validacion = SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE
            seguimiento.save()
        return Response(serialize_seguimiento_pnud(seguimiento, propio=True))


class TerritorialComedorPnudFieldsMixin(NoSaveSerializer):
    """Campos PNUD (N22) del comedor en el listado/detalle territorial."""

    programa_id = serializers.IntegerField(allow_null=True, read_only=True)
    linea_pnud = serializers.SerializerMethodField()
    codigo_proyecto = serializers.CharField(
        source="codigo_de_proyecto", allow_null=True, read_only=True
    )
    id_externo = serializers.IntegerField(allow_null=True, read_only=True)
    seguimientos_pnud = serializers.SerializerMethodField()

    def get_linea_pnud(self, obj):
        return linea_pnud(obj)

    def get_seguimientos_pnud(self, obj):
        # Sin respuestas: el detalle y GET .../seguimientos-pnud/ las incluyen.
        # Las observaciones del coordinador, solo en las del propio tecnico.
        request = self.context.get("request")
        usuario_id = getattr(getattr(request, "user", None), "id", None)
        items = []
        for seguimiento in obj.seguimientos_pnud.all():
            item = serialize_seguimiento_pnud(
                seguimiento, propio=seguimiento.tecnico_id == usuario_id
            )
            item.pop("datos", None)
            items.append(item)
        return {"total": len(items), "items": items}
