from __future__ import annotations

import logging
from typing import Dict

from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F

from core.models import Provincia
from celiaquia.models import (
    ExpedienteCiudadano,
    ProvinciaCupo,
    CupoMovimiento,
    EstadoCupo,
    TipoMovimientoCupo,
    RevisionTecnico,
    ResultadoSintys,
    HistorialCupo,
)

logger = logging.getLogger("django")


class CupoNoConfigurado(Exception):
    pass


def _tope_total_asignado() -> int:
    """Maximo que acepta la columna `ProvinciaCupo.total_asignado`.

    Se lee del `MaxValueValidator` que Django le pone al `PositiveIntegerField`
    segun el motor (en MySQL, 4.294.967.295). Hardcodearlo significaria que si
    el campo cambia de tipo, el tope queda viejo y vuelve el error de columna
    fuera de rango.
    """

    from django.core.validators import MaxValueValidator

    campo = ProvinciaCupo._meta.get_field("total_asignado")
    for validador in campo.validators:
        if isinstance(validador, MaxValueValidator):
            return int(validador.limit_value)
    return 2_147_483_647


#: Tope de cupo por provincia. Pasarse hacia que MySQL tirara
#: `DataError: Out of range value`, que llegaba al usuario como un 500.
TOTAL_ASIGNADO_MAXIMO = _tope_total_asignado()


class CupoService:
    # -------------------- MÉTRICAS Y LISTADOS --------------------

    @staticmethod
    def metrics_por_provincia(provincia: Provincia) -> Dict[str, int]:
        """
        Devuelve: total_asignado, usados, disponibles y fuera (lista de espera).
        """
        try:
            pc = ProvinciaCupo.objects.only("total_asignado", "usados").get(
                provincia=provincia
            )
        except ProvinciaCupo.DoesNotExist:
            raise CupoNoConfigurado(
                f"La provincia '{provincia}' no tiene cupo configurado."
            )
        total = int(pc.total_asignado or 0)
        usados = int(pc.usados or 0)
        disponibles = max(total - usados, 0)
        fuera = ExpedienteCiudadano.objects.filter(
            ciudadano__provincia=provincia,
            estado_cupo=EstadoCupo.FUERA,
            es_titular_activo=False,
            rol__in=[
                ExpedienteCiudadano.ROLE_BENEFICIARIO,
                ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
            ],
        ).count()
        return {
            "total_asignado": total,
            "usados": usados,
            "disponibles": disponibles,
            "fuera": int(fuera),
        }

    @staticmethod
    def filas_dashboard() -> list:
        """Una fila por **cada provincia**, tenga cupo configurado o no.

        Las que no tienen `ProvinciaCupo` van con los contadores en `None`: es
        lo que permite entrar y configurarlas por primera vez. Si solo se
        listaran las configuradas, una provincia nueva nunca podria recibir
        cupo desde la pantalla.

        Vivia en `CupoDashboardView`; se extrae para que la API liste lo mismo.
        """

        filas = []
        configuradas = (
            ProvinciaCupo.objects.select_related("provincia")
            .all()
            .order_by("provincia__nombre")
        )
        for pc in configuradas:
            try:
                metricas = CupoService.metrics_por_provincia(pc.provincia)
            except CupoNoConfigurado:
                # Defensivo: el registro existe pero quedo inconsistente.
                metricas = {
                    "total_asignado": 0,
                    "usados": 0,
                    "disponibles": 0,
                    "fuera": 0,
                }
            filas.append(
                {
                    "provincia": pc.provincia,
                    "cupo_id": pc.pk,
                    "total_asignado": metricas.get("total_asignado", 0),
                    "usados": metricas.get("usados", 0),
                    "disponibles": metricas.get("disponibles", 0),
                    "fuera": metricas.get("fuera", 0),
                }
            )

        sin_cupo = Provincia.objects.exclude(
            id__in=configuradas.values_list("provincia_id", flat=True)
        ).order_by("nombre")
        for provincia in sin_cupo:
            filas.append(
                {
                    "provincia": provincia,
                    "cupo_id": None,
                    "total_asignado": None,
                    "usados": None,
                    "disponibles": None,
                    "fuera": None,
                }
            )
        return filas

    @staticmethod
    def lista_ocupados_por_provincia(provincia: Provincia):
        """
        Titulares activos que ocupan cupo.
        """
        return ExpedienteCiudadano.objects.filter(
            ciudadano__provincia=provincia,
            revision_tecnico=RevisionTecnico.APROBADO,
            resultado_sintys=ResultadoSintys.MATCH,
            estado_cupo=EstadoCupo.DENTRO,
            es_titular_activo=True,
            rol__in=[
                ExpedienteCiudadano.ROLE_BENEFICIARIO,
                ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
            ],
        )

    @staticmethod
    def lista_suspendidos_por_provincia(provincia: Provincia):
        """
        Titulares suspendidos: mantienen estado_cupo=DENTRO (cupo ocupado) pero es_titular_activo=False.
        """
        return ExpedienteCiudadano.objects.filter(
            ciudadano__provincia=provincia,
            estado_cupo=EstadoCupo.DENTRO,
            es_titular_activo=False,
            rol__in=[
                ExpedienteCiudadano.ROLE_BENEFICIARIO,
                ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
            ],
        )

    @staticmethod
    def lista_fuera_de_cupo_por_expediente(expediente_id: int):
        """
        Lista de espera de un expediente (estado_cupo=FUERA).
        """
        return ExpedienteCiudadano.objects.filter(
            expediente_id=expediente_id,
            estado_cupo=EstadoCupo.FUERA,
        )

    # -------------------- CONFIGURAR TOTAL --------------------

    @staticmethod
    def configurar_total(
        provincia: Provincia, total_asignado: int, usuario=None
    ) -> ProvinciaCupo:
        try:
            total = int(total_asignado)
        except Exception:
            raise ValidationError("El total asignado debe ser un entero válido.")
        if total < 0:
            raise ValidationError("El total asignado debe ser un entero ≥ 0.")
        if total > TOTAL_ASIGNADO_MAXIMO:
            raise ValidationError(
                f"El total asignado no puede superar {TOTAL_ASIGNADO_MAXIMO:,}".replace(
                    ",", "."
                )
                + "."
            )
        pc, created = ProvinciaCupo.objects.get_or_create(
            provincia=provincia,
            defaults={"total_asignado": total},
        )
        if not created:
            pc.total_asignado = total
            pc.save(update_fields=["total_asignado"])
        return pc

    # -------------------- OPERACIONES DE CUPO --------------------

    @staticmethod
    @transaction.atomic
    def reservar_slot(
        *, legajo: ExpedienteCiudadano, usuario, motivo: str = ""
    ) -> bool:
        """
        Intenta ocupar un cupo para el legajo.
        Reglas:
        - Sólo si (APROBADO + MATCH).
        - Sólo si el rol es BENEFICIARIO o BENEFICIARIO_Y_RESPONSABLE (no responsables puros).
        - Si el ciudadano ya ocupa un cupo DENTRO en la provincia (activo o suspendido), NO se reserva otro:
          este legajo queda FUERA (lista de espera) y no cambia 'usados'.
        - Si no hay disponibles, queda FUERA (lista de espera) y no cambia 'usados'.
        - Si se puede, incrementa 'usados', marca DENTRO + es_titular_activo=True y registra ALTA (+1).
        """
        legajo = (
            ExpedienteCiudadano.objects.select_for_update()
            .select_related(
                "expediente",
                "ciudadano",
                "ciudadano__provincia",
            )
            .get(pk=legajo.pk)
        )

        # Validar que califica para cupo: debe ser beneficiario (no responsable puro)
        if legajo.rol == ExpedienteCiudadano.ROLE_RESPONSABLE:
            if legajo.estado_cupo != EstadoCupo.NO_EVAL or legajo.es_titular_activo:
                legajo.estado_cupo = EstadoCupo.NO_EVAL
                legajo.es_titular_activo = False
                legajo.save(
                    update_fields=["estado_cupo", "es_titular_activo", "modificado_en"]
                )
            return False

        # Validar que califica para cupo: debe estar aprobado y matcheado
        if not (
            legajo.revision_tecnico == RevisionTecnico.APROBADO
            and legajo.resultado_sintys == ResultadoSintys.MATCH
        ):
            if legajo.estado_cupo != EstadoCupo.NO_EVAL or legajo.es_titular_activo:
                legajo.estado_cupo = EstadoCupo.NO_EVAL
                legajo.es_titular_activo = False
                legajo.save(
                    update_fields=["estado_cupo", "es_titular_activo", "modificado_en"]
                )
            return False

        provincia = legajo.ciudadano.provincia
        if not provincia:
            raise ValidationError("El legajo no tiene provincia asociada al ciudadano.")

        try:
            pc = (
                ProvinciaCupo.objects.select_for_update()
                .only("id", "usados", "total_asignado")
                .get(provincia=provincia)
            )
        except ProvinciaCupo.DoesNotExist:
            raise CupoNoConfigurado(
                f"La provincia '{provincia}' no tiene cupo configurado."
            )

        # Si ya está dentro y activo, nada para hacer
        if legajo.estado_cupo == EstadoCupo.DENTRO and legajo.es_titular_activo:
            return True

        # Si el ciudadano YA ocupa un cupo DENTRO en la provincia (activo o suspendido), no se puede reservar otro
        # Excluir responsables puros
        ya_ocupa = (
            ExpedienteCiudadano.objects.filter(
                ciudadano_id=legajo.ciudadano_id,
                ciudadano__provincia=provincia,
                estado_cupo=EstadoCupo.DENTRO,
                rol__in=[
                    ExpedienteCiudadano.ROLE_BENEFICIARIO,
                    ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
                ],
            )
            .exclude(pk=legajo.pk)
            .exists()
        )
        if ya_ocupa:
            if legajo.estado_cupo != EstadoCupo.FUERA or legajo.es_titular_activo:
                legajo.estado_cupo = EstadoCupo.FUERA
                legajo.es_titular_activo = False
                legajo.save(
                    update_fields=["estado_cupo", "es_titular_activo", "modificado_en"]
                )
            return False

        # Chequear disponibles
        disponibles = int(pc.total_asignado or 0) - int(pc.usados or 0)
        if disponibles <= 0:
            if legajo.estado_cupo != EstadoCupo.FUERA or legajo.es_titular_activo:
                legajo.estado_cupo = EstadoCupo.FUERA
                legajo.es_titular_activo = False
                legajo.save(
                    update_fields=["estado_cupo", "es_titular_activo", "modificado_en"]
                )
            return False

        # Ocupar cupo
        ProvinciaCupo.objects.filter(pk=pc.pk).update(usados=F("usados") + 1)
        pc.refresh_from_db(fields=["usados"])

        estado_anterior = legajo.estado_cupo
        activo_anterior = legajo.es_titular_activo

        legajo.estado_cupo = EstadoCupo.DENTRO
        legajo.es_titular_activo = True
        legajo.save(update_fields=["estado_cupo", "es_titular_activo", "modificado_en"])

        HistorialCupo.objects.create(
            legajo=legajo,
            estado_cupo_anterior=estado_anterior,
            estado_cupo_nuevo=EstadoCupo.DENTRO,
            es_titular_activo_anterior=activo_anterior,
            es_titular_activo_nuevo=True,
            tipo_movimiento=TipoMovimientoCupo.ALTA,
            usuario=usuario,
            motivo=(motivo or "").strip()[:255],
        )

        CupoMovimiento.objects.create(
            provincia=provincia,
            expediente=legajo.expediente,
            legajo=legajo,
            tipo=TipoMovimientoCupo.ALTA,
            delta=+1,
            motivo=(motivo or "").strip()[:255],
            usuario=usuario,
        )
        logger.info(
            "Cupo ALTA: provincia=%s usados=%s legajo=%s",
            provincia,
            pc.usados,
            legajo.pk,
        )
        return True

    @staticmethod
    @transaction.atomic
    def suspender_slot(
        *, legajo: ExpedienteCiudadano, usuario, motivo: str = ""
    ) -> bool:
        """
        Suspende el legajo manteniendo el cupo ocupado.
        - NO modifica ProvinciaCupo.usados.
        - Deja estado_cupo=DENTRO y es_titular_activo=False.
        - Registra movimiento SUSPENDIDO (delta=0).
        """
        legajo = (
            ExpedienteCiudadano.objects.select_for_update()
            .select_related(
                "expediente",
                "ciudadano",
                "ciudadano__provincia",
            )
            .get(pk=legajo.pk)
        )
        provincia = legajo.ciudadano.provincia
        if not provincia:
            raise ValidationError("El legajo no tiene provincia asociada al ciudadano.")

        # Sólo si tiene cupo DENTRO (activo o ya suspendido)
        if legajo.estado_cupo != EstadoCupo.DENTRO:
            # no cambia contadores ni estados NO_EVAL/FUERA aquí
            return False

        if legajo.es_titular_activo:
            legajo.es_titular_activo = False
            legajo.save(update_fields=["es_titular_activo", "modificado_en"])

            HistorialCupo.objects.create(
                legajo=legajo,
                estado_cupo_anterior=EstadoCupo.DENTRO,
                estado_cupo_nuevo=EstadoCupo.DENTRO,
                es_titular_activo_anterior=True,
                es_titular_activo_nuevo=False,
                tipo_movimiento=TipoMovimientoCupo.SUSPENDIDO,
                usuario=usuario,
                motivo=(motivo or "Suspensión de titular").strip()[:255],
            )

            CupoMovimiento.objects.create(
                provincia=provincia,
                expediente=legajo.expediente,
                legajo=legajo,
                tipo=TipoMovimientoCupo.SUSPENDIDO,
                delta=0,
                motivo=(motivo or "Suspensión de titular").strip()[:255],
                usuario=usuario,
            )
            logger.info(
                "Cupo SUSPENDIDO: provincia=%s usados (sin cambio) legajo=%s",
                provincia,
                legajo.pk,
            )

        return True

    @staticmethod
    @transaction.atomic
    def liberar_slot(*, legajo: ExpedienteCiudadano, usuario, motivo: str = "") -> bool:
        """
        Libera definitivamente el cupo (BAJA).
        - Si el legajo estaba DENTRO (activo o suspendido), disminuye ProvinciaCupo.usados en 1.
        - Pone estado_cupo=NO_EVAL y es_titular_activo=False.
        - Registra movimiento BAJA (delta=-1).
        """
        legajo = (
            ExpedienteCiudadano.objects.select_for_update()
            .select_related(
                "expediente",
                "ciudadano",
                "ciudadano__provincia",
            )
            .get(pk=legajo.pk)
        )
        provincia = legajo.ciudadano.provincia
        if not provincia:
            raise ValidationError("El legajo no tiene provincia asociada al ciudadano.")

        try:
            pc = (
                ProvinciaCupo.objects.select_for_update()
                .only("id", "usados")
                .get(provincia=provincia)
            )
        except ProvinciaCupo.DoesNotExist:
            raise CupoNoConfigurado(
                f"La provincia '{provincia}' no tiene cupo configurado."
            )

        # Sólo si estaba DENTRO se descuenta
        if legajo.estado_cupo != EstadoCupo.DENTRO:
            if legajo.estado_cupo != EstadoCupo.NO_EVAL or legajo.es_titular_activo:
                legajo.estado_cupo = EstadoCupo.NO_EVAL
                legajo.es_titular_activo = False
                legajo.save(
                    update_fields=["estado_cupo", "es_titular_activo", "modificado_en"]
                )
            return False

        if int(pc.usados or 0) > 0:
            ProvinciaCupo.objects.filter(pk=pc.pk).update(usados=F("usados") - 1)
            pc.refresh_from_db(fields=["usados"])

        estado_anterior = legajo.estado_cupo
        activo_anterior = legajo.es_titular_activo

        legajo.estado_cupo = EstadoCupo.NO_EVAL
        legajo.es_titular_activo = False
        legajo.save(update_fields=["estado_cupo", "es_titular_activo", "modificado_en"])

        HistorialCupo.objects.create(
            legajo=legajo,
            estado_cupo_anterior=estado_anterior,
            estado_cupo_nuevo=EstadoCupo.NO_EVAL,
            es_titular_activo_anterior=activo_anterior,
            es_titular_activo_nuevo=False,
            tipo_movimiento=TipoMovimientoCupo.BAJA,
            usuario=usuario,
            motivo=(motivo or "Baja de titular").strip()[:255],
        )

        CupoMovimiento.objects.create(
            provincia=provincia,
            expediente=legajo.expediente,
            legajo=legajo,
            tipo=TipoMovimientoCupo.BAJA,
            delta=-1,
            motivo=(motivo or "Baja de titular").strip()[:255],
            usuario=usuario,
        )
        logger.info(
            "Cupo BAJA: provincia=%s usados=%s legajo=%s",
            provincia,
            pc.usados,
            legajo.pk,
        )
        return True

    @staticmethod
    @transaction.atomic
    def reactivar_slot(
        *, legajo: ExpedienteCiudadano, usuario, motivo: str = ""
    ) -> bool:
        """
        Reactiva un legajo suspendido manteniendo el cupo ocupado.
        - NO modifica ProvinciaCupo.usados.
        - Requiere estado_cupo=DENTRO y es_titular_activo=False.
        - Deja es_titular_activo=True.
        - Registra movimiento AJUSTE (delta=0).
        """
        legajo = (
            ExpedienteCiudadano.objects.select_for_update()
            .select_related(
                "expediente",
                "ciudadano",
                "ciudadano__provincia",
            )
            .get(pk=legajo.pk)
        )
        provincia = legajo.ciudadano.provincia
        if not provincia:
            raise ValidationError("El legajo no tiene provincia asociada al ciudadano.")

        # Debe estar dentro de cupo y NO activo
        if legajo.estado_cupo != EstadoCupo.DENTRO or legajo.es_titular_activo:
            return False

        legajo.es_titular_activo = True
        legajo.save(update_fields=["es_titular_activo", "modificado_en"])

        HistorialCupo.objects.create(
            legajo=legajo,
            estado_cupo_anterior=EstadoCupo.DENTRO,
            estado_cupo_nuevo=EstadoCupo.DENTRO,
            es_titular_activo_anterior=False,
            es_titular_activo_nuevo=True,
            tipo_movimiento=TipoMovimientoCupo.REACTIVACION,
            usuario=usuario,
            motivo=(motivo or "Reactivación de titular").strip()[:255],
        )

        CupoMovimiento.objects.create(
            provincia=provincia,
            expediente=legajo.expediente,
            legajo=legajo,
            tipo=TipoMovimientoCupo.REACTIVACION,  # delta 0
            delta=0,
            motivo=(motivo or "Reactivación de titular").strip()[:255],
            usuario=usuario,
        )
        logger.info(
            "Cupo REACTIVADO (ajuste): provincia=%s legajo=%s", provincia, legajo.pk
        )
        return True
