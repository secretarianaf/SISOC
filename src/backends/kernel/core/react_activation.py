"""Activación por flag de las pantallas React migradas (#2785).

Cada pantalla migrada tiene una entrada ``web_preview*`` que conserva la URL
nativa, el decorador de permisos y el despacho de la vista nativa: solo el GET
devuelve el ``index.html`` congelado del build; cualquier otro método llega a
la vista nativa. Este módulo las monta en las URLconf reales, detrás de
``settings.REACT_VERTICALES_ACTIVAS``: sin la variable de entorno están todas
activas (``"todas"``); ``ninguna`` o vacío las apaga.

El kernel no importa las verticales: el registro usa rutas con punto y cada
URLconf pide solo las claves que le corresponden (``react_preview_patterns``).
Las entradas van ANTES de las rutas nativas del mismo URLconf para que el GET
las alcance; no tapan POST ni subrutas porque heredan la vista nativa y solo
cubren las rutas exactas que migraron.
"""

import logging
from importlib import import_module
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# build -> nombre del setting con el directorio del build congelado.
BUILD_SETTINGS = {
    "sisoc": "SISOC_REACT_BUILD_DIR",
    "pas": "SISOC_REACT_PAS_BUILD_DIR",
}

# clave de activación -> (módulo, función, build). Las claves de vertical
# coinciden con config/backends.json; "core", "ciudadanos", "audittrail",
# "dashboard", "encuestas", "insumos" y "usuarios" son pantallas del core.
REGISTRO = {
    "cdf": (
        ("centrodefamilia.web_preview", "cdf_preview_patterns", "sisoc"),
        (
            "centrodefamilia.web_preview_actividades",
            "cdf_actividades_preview_patterns",
            "sisoc",
        ),
        (
            "centrodefamilia.web_preview_informecabal",
            "cdf_informecabal_preview_patterns",
            "sisoc",
        ),
    ),
    "cdi": (
        ("centrodeinfancia.web_preview", "cdi_preview_patterns", "sisoc"),
        (
            "centrodeinfancia.web_preview_centro_form",
            "centro_form_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_destinatario",
            "destinatario_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_formularios",
            "formularios_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_formularios_institucionales",
            "cdi_formularios_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_intervencion_form",
            "intervencion_form_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_nomina_asistencia",
            "nomina_asistencia_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_nomina_formulario",
            "nomina_formulario_preview_patterns",
            "sisoc",
        ),
        (
            "centrodeinfancia.web_preview_trabajadores",
            "cdi_trabajadores_preview_patterns",
            "sisoc",
        ),
        ("centrodeinfancia.web_preview_bajas", "cdi_bajas_preview_patterns", "sisoc"),
    ),
    "comedores": (
        ("acompanamientos.web_preview", "acompanamientos_preview_patterns", "sisoc"),
        (
            "admisiones.web_preview_informe_complementario",
            "complementario_preview_patterns",
            "sisoc",
        ),
        ("admisiones.web_preview_informes", "informes_preview_patterns", "sisoc"),
        ("admisiones.web_preview_legales", "legales_preview_patterns", "sisoc"),
        ("admisiones.web_preview_seguimiento", "seguimiento_preview_patterns", "sisoc"),
        ("admisiones.web_preview_templates", "templates_preview_patterns", "sisoc"),
        (
            "comedores.web_preview_actividades_espacio",
            "actividades_espacio_preview_patterns",
            "sisoc",
        ),
        ("comedores.web_preview_asistencia", "asistencia_preview_patterns", "sisoc"),
        ("comedores.web_preview_catalogos", "catalogos_preview_patterns", "sisoc"),
        (
            "comedores.web_preview_certificaciones",
            "certificaciones_preview_patterns",
            "sisoc",
        ),
        (
            "comedores.web_preview_colaboradores",
            "colaboradores_preview_patterns",
            "sisoc",
        ),
        ("comedores.web_preview_comedores", "comedores_preview_patterns", "sisoc"),
        (
            "comedores.web_preview_convenio_tarjeta",
            "convenio_tarjeta_preview_patterns",
            "sisoc",
        ),
        ("comedores.web_preview_cursos", "cursos_preview_patterns", "sisoc"),
        (
            "comedores.web_preview_dupla_asignar",
            "dupla_asignar_preview_patterns",
            "sisoc",
        ),
        ("comedores.web_preview_nomina", "nomina_preview_patterns", "sisoc"),
        (
            "comedores.web_preview_nomina_crear",
            "nomina_crear_preview_patterns",
            "sisoc",
        ),
        (
            "comedores.web_preview_observaciones",
            "observaciones_preview_patterns",
            "sisoc",
        ),
        (
            "comedores.web_preview_transacciones",
            "transacciones_preview_patterns",
            "sisoc",
        ),
        ("comunicados.web_preview", "comunicados_preview_patterns", "sisoc"),
        ("comunicados.web_preview_mailing", "mailing_preview_patterns", "sisoc"),
        ("duplas.web_preview", "duplas_preview_patterns", "sisoc"),
        ("expedientespagos.web_preview", "expedientes_preview_patterns", "sisoc"),
        (
            "gestion_organizaciones.web_preview",
            "organizaciones_preview_patterns",
            "sisoc",
        ),
        (
            "importarexpediente.web_preview_importarexpedientes",
            "importarexpedientes_preview_patterns",
            "sisoc",
        ),
        ("intervenciones.web_preview", "intervenciones_preview_patterns", "sisoc"),
        ("relevamientos.web_preview", "relevamientos_preview_patterns", "sisoc"),
        (
            "rendicioncuentasfinal.web_preview",
            "rendicion_final_preview_patterns",
            "sisoc",
        ),
        ("rendicioncuentasmensual.web_preview", "rendicion_preview_patterns", "sisoc"),
    ),
    "dispositivos": (
        ("datacalle.web_preview", "datacalle_preview_patterns", "sisoc"),
        ("dispositivos.web_preview", "dispositivos_preview_patterns", "sisoc"),
        (
            "dispositivos.web_preview_dispositivo_form",
            "dispositivo_form_preview_patterns",
            "sisoc",
        ),
    ),
    "inspecciones": (("inspecciones.web_preview", "actas_preview_patterns", "sisoc"),),
    "audittrail": (("audittrail.web_preview", "audittrail_preview_patterns", "sisoc"),),
    "ciudadanos": (
        ("ciudadanos.web_preview", "ciudadanos_preview_patterns", "sisoc"),
        (
            "ciudadanos.web_preview_cola_revision",
            "cola_revision_preview_patterns",
            "sisoc",
        ),
        (
            "ciudadanos.web_preview_familiar_eliminar",
            "familiar_eliminar_preview_patterns",
            "sisoc",
        ),
        ("ciudadanos.web_preview_importacion", "importacion_preview_patterns", "sisoc"),
        ("ciudadanos.web_preview_listado", "listado_preview_patterns", "sisoc"),
    ),
    "core": (("core.web_preview_core_pages", "core_preview_patterns", "sisoc"),),
    "insumos": (("insumos.web_preview", "insumos_preview_patterns", "sisoc"),),
    "ocr": (("ocr.web_preview", "ocr_preview_patterns", "sisoc"),),
    "pas": (
        ("pas.ddjj_preview", "ddjj_preview_patterns", "pas"),
        ("pas.web_preview_backoffice", "backoffice_preview_patterns", "sisoc"),
        ("pas.web_preview_cruces", "cruces_preview_patterns", "sisoc"),
        ("pas.web_preview_informes", "informes_preview_patterns", "sisoc"),
        (
            "pas.web_preview_titulares_import",
            "titulares_import_preview_patterns",
            "sisoc",
        ),
    ),
    "dashboard": (
        ("dashboard.web_preview_dashboard", "dashboard_preview_patterns", "sisoc"),
    ),
    "encuestas": (
        ("encuestas.web_preview_encuestas", "encuestas_preview_patterns", "sisoc"),
    ),
    "usuarios": (("usuarios.identity_preview", "identity_preview_patterns", "sisoc"),),
    "vat": (
        ("VAT.web_preview_vat", "vat_preview_patterns", "sisoc"),
        ("VAT.web_preview_vat_asistencia", "asistencia_preview_patterns", "sisoc"),
        ("VAT.web_preview_vat_catalogos", "catalogos_preview_patterns", "sisoc"),
        ("VAT.web_preview_vat_centros_lista", "centros_preview_patterns", "sisoc"),
        (
            "VAT.web_preview_vat_comision_detalle",
            "comision_detalle_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_comision_forms",
            "comision_forms_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_comision_horario_forms",
            "comision_horario_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_comision_horarios",
            "comision_horarios_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_comision_lista",
            "comision_lista_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_comision_wizard",
            "comision_wizard_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_inscripcion_oferta",
            "inscripcion_oferta_preview_patterns",
            "sisoc",
        ),
        (
            "VAT.web_preview_vat_inscripcion_persona",
            "inscripcion_persona_preview_patterns",
            "sisoc",
        ),
        ("VAT.web_preview_vat_oferta_curso", "oferta_curso_preview_patterns", "sisoc"),
        (
            "VAT.web_preview_vat_oferta_curso_forms",
            "oferta_curso_forms_preview_patterns",
            "sisoc",
        ),
        ("VAT.web_preview_vat_planes", "planes_preview_patterns", "sisoc"),
    ),
}


TODAS = "todas"


def claves_activas():
    """Claves activas en ``REACT_VERTICALES_ACTIVAS``; las desconocidas se avisan.

    ``"todas"`` expande a todas las claves de ``REGISTRO``.
    """
    activas = frozenset(getattr(settings, "REACT_VERTICALES_ACTIVAS", ()) or ())
    if TODAS in activas:
        return frozenset(REGISTRO)
    for clave in sorted(activas - set(REGISTRO)):
        logger.warning("REACT_VERTICALES_ACTIVAS: clave desconocida %r", clave)
    return activas & set(REGISTRO)


def _directorio_build(build):
    return getattr(settings, BUILD_SETTINGS[build], "") or ""


def react_preview_patterns(*claves):
    """Rutas de las entradas React de ``claves`` activas; ``[]`` si no hay ninguna.

    Con ``ninguna``, o con el build ausente, devuelve ``[]``: la URLconf queda igual
    que sin esta función y las pantallas siguen siendo las de Django.
    """
    activas = claves_activas()
    patrones = []
    vistos = set()
    for clave in claves:
        if clave not in activas:
            continue
        for modulo, funcion, build in REGISTRO[clave]:
            directorio = _directorio_build(build)
            if not directorio or not (Path(directorio) / "index.html").is_file():
                logger.error(
                    "React activo para %r pero falta el build en %s", clave, directorio
                )
                continue
            try:
                nuevos = getattr(import_module(modulo), funcion)(directorio)
            except (ValueError, OSError):
                logger.exception("No se pudo montar %s.%s", modulo, funcion)
                continue
            for patron in nuevos:
                # Varias entradas repiten las del backoffice o los assets.
                if str(patron.pattern) not in vistos:
                    vistos.add(str(patron.pattern))
                    patrones.append(patron)
    return patrones
