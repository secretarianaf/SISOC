"""Actas complementarias extraordinarias (N15) en la API territorial.

El territorial carga el acta desde la app (sin asignación previa, sobre un
comedor de su zona) o completa una que le asignó SISOC desde el popup del
backoffice. Pasa por el ciclo de validación del coordinador (N16), igual que
los seguimientos: el alta y la corrección la dejan en "Pendiente validación
coordinador"; el coordinador la valida o la devuelve "A subsanar"; un acta
``Validado`` no admite más cambios del territorial (409). Separado del viewset
territorial para mantener ese módulo acotado; se mezcla como mixin.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from comedores.api_views_territorial_validaciones import (
    MAX_LARGO_FIRMA,
    MAX_LARGO_OBSERVACIONES,
    leer_texto,
    validar_prestaciones_acta,
)
from core.utils import format_fecha_django
from relevamientos.models import ActaComplementaria, PrestacionActaComplementaria


def _fecha_iso(valor):
    return timezone.localtime(valor).isoformat() if valor else None


def serialize_acta(acta, usuario_id=None):
    """Acta con sus prestaciones y los metadatos del coordinador (N16).

    Las observaciones del coordinador solo van al técnico del acta (pueden
    citar datos personales), como en los seguimientos PNUD.
    """
    return {
        "id": acta.id,
        "comedor": acta.comedor_id,
        "tecnico": acta.tecnico_id,
        "fecha_hora": acta.fecha_hora,
        "observaciones": acta.observaciones,
        "firma": acta.firma,
        "origen": acta.origen,
        "asignado_desde_sisoc": acta.asignado_desde_sisoc,
        "client_uuid": acta.client_uuid,
        "estado_validacion": acta.estado_validacion,
        "observaciones_coordinador": (
            acta.observaciones_coordinador
            if usuario_id is not None and acta.tecnico_id == usuario_id
            else None
        ),
        "fecha_revision_coordinador": _fecha_iso(acta.fecha_revision_coordinador),
        "prestaciones": [
            {
                "id": fila.id,
                "dias_prestacion": fila.dias_prestacion,
                "tipo_prestacion": fila.tipo_prestacion,
                "cantidad_actual": fila.cantidad_actual,
                "cantidad_espera": fila.cantidad_espera,
            }
            for fila in acta.prestaciones.all()
        ],
    }


def actas_payload(comedor, usuario):
    actas = list(comedor.actas_complementarias.prefetch_related("prestaciones"))
    return {
        "total": len(actas),
        "items": [serialize_acta(acta, usuario.id) for acta in actas],
    }


def _error(mensaje, codigo, **extra):
    return Response({"detail": mensaje, **extra}, status=codigo)


class ActasComplementariasTerritorialMixin:
    """Acciones de actas del ``TerritorialComedorViewSet``.

    Usa del viewset: ``_comedor_de_mi_zona``, ``_fuera_de_zona``,
    ``_leer_client_uuid``, ``_falta_client_uuid``, ``_fecha_invalida`` y
    ``_conflicto_concurrente``.
    """

    def _aplicar_fecha_hora(self, request, acta):
        fecha_hora = leer_texto(request.data, "fecha_hora")
        if fecha_hora:
            try:
                acta.fecha_hora = format_fecha_django(fecha_hora)
            except (ValueError, TypeError):
                return self._fecha_invalida("fecha_hora")
        return None

    @action(detail=True, methods=["get", "post"], url_path="actas-complementarias")
    def crear_acta_complementaria(  # pylint: disable=too-many-return-statements
        self, request, pk=None
    ):
        """Acta complementaria extraordinaria (N15): cambio de prestacion.

        GET: actas del comedor con su estado de validación. POST: alta
        idempotente por ``client_uuid``; entra a validación del coordinador.
        """
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()

        if request.method == "GET":
            return Response(actas_payload(comedor, request.user))

        client_uuid = self._leer_client_uuid(request)
        if not client_uuid:
            return self._falta_client_uuid()

        existente = ActaComplementaria.objects.filter(client_uuid=client_uuid).first()
        if existente is not None:
            return Response(
                serialize_acta(existente, request.user.id), status=status.HTTP_200_OK
            )

        # Tipos y largos se validan antes de tocar la base (S5): una cantidad
        # negativa, un texto donde va un número o un largo excedido terminaban
        # en 500 (en MySQL estricto también por columna). Todo es 400 {detail}.
        prestaciones = validar_prestaciones_acta(request.data.get("prestaciones") or [])

        acta = ActaComplementaria(
            comedor=comedor,
            tecnico=request.user,
            observaciones=leer_texto(
                request.data, "observaciones", MAX_LARGO_OBSERVACIONES
            ),
            firma=leer_texto(request.data, "firma", MAX_LARGO_FIRMA),
            origen=ActaComplementaria.ORIGEN_APP,
            asignado_desde_sisoc=False,
            client_uuid=client_uuid,
            estado_validacion=ActaComplementaria.ESTADO_VALIDACION_PENDIENTE,
        )
        error = self._aplicar_fecha_hora(request, acta)
        if error is not None:
            return error

        try:
            with transaction.atomic():
                acta.save()
                PrestacionActaComplementaria.objects.bulk_create(
                    [
                        PrestacionActaComplementaria(acta=acta, **fila)
                        for fila in prestaciones
                    ]
                )
        except IntegrityError:
            existente = ActaComplementaria.objects.filter(
                client_uuid=client_uuid
            ).first()
            if existente is None:
                return self._conflicto_concurrente(
                    "Otra acta se registró al mismo tiempo sobre este comedor."
                )
            return Response(
                serialize_acta(existente, request.user.id), status=status.HTTP_200_OK
            )

        return Response(
            serialize_acta(acta, request.user.id), status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"actas-complementarias/(?P<acta_id>[0-9]+)",
    )
    def corregir_acta_complementaria(self, request, pk=None, acta_id=None):
        """Corrección del técnico (N16), o carga de un acta asignada por SISOC.

        Reemplaza los campos que vengan (``observaciones``, ``firma``,
        ``fecha_hora``; ``prestaciones`` reemplaza la tabla entera) y la manda
        a validación. Permitida mientras no esté ``Validado`` (409).
        """
        comedor = self._comedor_de_mi_zona()
        if comedor is None:
            return self._fuera_de_zona()
        # Validación de tipos antes de bloquear la fila (400 sin tocar la base).
        prestaciones = None
        if "prestaciones" in request.data:
            prestaciones = validar_prestaciones_acta(
                request.data.get("prestaciones") or []
            )
        textos = {
            campo: leer_texto(request.data, campo, maximo)
            for campo, maximo in (
                ("observaciones", MAX_LARGO_OBSERVACIONES),
                ("firma", MAX_LARGO_FIRMA),
            )
            if campo in request.data
        }
        with transaction.atomic():
            # Bloqueo de fila: una revisión del coordinador en paralelo no puede
            # quedar pisada (un Validado nunca vuelve a Pendiente).
            acta = (
                ActaComplementaria.objects.select_for_update()
                .filter(pk=acta_id, comedor=comedor)
                .first()
            )
            if acta is None:
                return _error("Acta no encontrada.", status.HTTP_404_NOT_FOUND)
            if acta.tecnico_id != request.user.id:
                return _error(
                    "Solo el técnico del acta puede corregirla.",
                    status.HTTP_403_FORBIDDEN,
                )
            if acta.esta_validado:
                return _error(
                    "Validado por el coordinador: no admite modificaciones.",
                    status.HTTP_409_CONFLICT,
                    estado_validacion=acta.estado_validacion,
                )
            error = self._aplicar_fecha_hora(request, acta)
            if error is not None:
                return error
            for campo, valor in textos.items():
                setattr(acta, campo, valor)
            # "A subsanar" (o sin enviar) vuelve a la bandeja del coordinador.
            acta.estado_validacion = ActaComplementaria.ESTADO_VALIDACION_PENDIENTE
            acta.save()
            if prestaciones is not None:
                acta.prestaciones.all().delete()
                PrestacionActaComplementaria.objects.bulk_create(
                    [
                        PrestacionActaComplementaria(acta=acta, **fila)
                        for fila in prestaciones
                    ]
                )
        return Response(serialize_acta(acta, request.user.id))
