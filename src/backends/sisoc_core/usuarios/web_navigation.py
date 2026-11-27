"""Read-only projection of the legacy sidebar into a JSON-safe tree.

The caller is responsible for resolving web-session readiness first. This
module mirrors the sidebar's visibility rules; it does not authorize actions.
"""

from urllib.parse import urlsplit

from django.urls import reverse

from core.services.sidebar_items import obtener_tableros
from core.templatetags.custom_filters import (
    has_any_group,
    has_any_perm,
    has_perm_code,
    is_cdi_local_sidebar_only,
    is_datacalle_sidebar_only,
    is_vat_sidebar_only,
    puede_gestionar_inspecciones,
)
from iam.roles_datos import puede_administrar_tableros

_ADMINISTRATION_PERMISSIONS = (
    "auth.view_user",
    "auth.add_user",
    "auth.change_user",
    "auth.delete_user",
    "auth.view_group",
    "auth.add_group",
    "auth.change_group",
    "encuestas.view_encuesta",
    "encuestas.ver_resultados",
)
_CONFIGURATION_PERMISSIONS = (
    "auth.role_admin",
    "core.view_montoprestacionprograma",
    "pwa.view_catalogoactividadpwa",
    "pwa.manage_catalogoactividadpwa",
    "insumos.view_insumo",
    "admisiones.gestionar_templates_informe_tecnico",
)
_MONTHLY_RENDICION_PERMISSIONS = (
    "rendicioncuentasmensual.view_rendicioncuentamensual",
    "rendicioncuentasmensual.manage_territorial_stage",
    "rendicioncuentasmensual.manage_auditoria_review_stage",
    "rendicioncuentasmensual.manage_auditoria_stage",
    "rendicioncuentasmensual.manage_regularizacion_stage",
)


def _item(item_id, label, href=None, children=None):
    return {
        "id": item_id,
        "label": label,
        "href": href,
        "children": children or [],
    }


def _link(route_name, label):
    return _item(route_name, label, reverse(route_name))


def _group(item_id, label, children):
    return _item(item_id, label, children=children)


def _direct_permission(user, permission_code):
    """Mirror template ``perms.<app>.<codename>`` checks verbatim."""
    return user.has_perm(permission_code)


def _valid_internal_href(href):
    if not isinstance(href, str):
        raise ValueError("A dashboard sidebar URL must be a string path.")
    parsed = urlsplit(href)
    if (
        not href.startswith("/")
        or parsed.scheme
        or parsed.netloc
        or href.startswith("//")
    ):
        raise ValueError("A dashboard sidebar URL must be an internal path.")
    return href


def _dashboard_item(item):
    if item["tipo"] == "single":
        href = _valid_internal_href(item["url"])
        return _item(f"dashboard:{href}", item["nombre"], href)

    children = [_dashboard_item(hijo) for hijo in item["hijos"]]
    if not children:
        raise ValueError("A dashboard sidebar group must contain a child.")
    return _group(f"dashboard-group:{children[0]['id']}", item["nombre"], children)


def _administration(user, vat_sidebar_only):
    # Preserve Django template's `and`-before-`or` precedence here. The audit
    # permission and superuser branches bypass the VAT-only branch.
    if not (
        (not vat_sidebar_only and has_any_perm(user, _ADMINISTRATION_PERMISSIONS))
        or _direct_permission(user, "auditlog.view_logentry")
        or user.is_superuser
    ):
        return None

    children = [_link("usuarios", "Usuarios")]
    if has_perm_code(user, "auth.view_group"):
        children.append(_link("grupos", "Grupos"))
    children.append(_link("programa_listar", "Programas"))
    if _direct_permission(user, "auditlog.view_logentry"):
        children.append(_link("audittrail:log_list", "Auditoría"))
    if has_any_perm(user, ("encuestas.view_encuesta", "encuestas.ver_resultados")):
        children.append(_link("encuestas_listar", "Encuestas"))
    if user.is_superuser:
        children.append(_link("papelera_list", "Papelera"))
    children.append(_link("vat_voucher_parametria_list", "Parametrías de Voucher"))
    return _group("administracion-sistema", "Administración del sistema", children)


def _commedores_configuration(user, vat_sidebar_only, datacalle_sidebar_only):
    if (
        vat_sidebar_only
        or datacalle_sidebar_only
        or not has_any_perm(user, _CONFIGURATION_PERMISSIONS)
    ):
        return None

    children = []
    if has_perm_code(user, "auth.role_admin"):
        children.append(_link("dupla_list", "Equipos Técnicos"))
    if has_perm_code(user, "core.view_montoprestacionprograma"):
        children.append(_link("montoprestacion_listar", "Monto de Prestaciones"))
    if has_perm_code(user, "auth.role_admin"):
        children.append(_link("cursos_app_mobile_list", "Cursos App Mobile"))
    if has_any_perm(
        user,
        (
            "auth.role_admin",
            "pwa.view_catalogoactividadpwa",
            "pwa.manage_catalogoactividadpwa",
        ),
    ):
        children.append(_link("actividades_pnud_list", "Actividades PNUD"))
    if has_perm_code(user, "insumos.view_insumo"):
        children.append(_link("insumos_listar", "Insumos"))

    if has_perm_code(user, "admisiones.gestionar_templates_informe_tecnico"):
        children.append(
            _group(
                "gestor-templates",
                "Gestor de templates",
                [
                    _link("gestor_templates_listar", "Templates"),
                    _link(
                        "gestor_templates_variables_listar", "Variables documentales"
                    ),
                    _link(
                        "gestor_templates_incidencias_listar",
                        "Incidencias de templates",
                    ),
                ],
            )
        )
    return _group("configuracion-comedores", "Configuración de Comedores", children)


def _history_social(user):
    children = []
    if has_perm_code(user, "ciudadanos.view_ciudadano"):
        children.append(_link("ciudadanos", "Búsqueda"))
    if has_perm_code(user, "ciudadanos.revision_identidad"):
        children.append(_link("ciudadanos_cola_revision", "Revisión de Identidad"))
    if has_perm_code(user, "ciudadanos.add_ciudadano"):
        children.append(_link("ciudadanos_importacion_masiva", "Importación masiva"))
    return _group("historia-social-digital", "Historia Social Digital", children)


def _comedores(user):
    children = []
    if has_perm_code(user, "comedores.view_comedor"):
        children.append(_link("comedores", "Ver Comedores"))
    if has_perm_code(user, "admisiones.view_admision"):
        children.append(
            _group(
                "admision-comedores",
                "Admisión - Comedores",
                [
                    _link("admisiones_tecnicos_listar", "Técnicos"),
                    _link("admisiones_legales_listar", "Legales"),
                ],
            )
        )
    if has_perm_code(user, "acompanamientos.view_informacionrelevante"):
        children.append(_link("lista_comedores_acompanamiento", "Acompañamiento"))
    if has_perm_code(user, "importarexpediente.view_archivosimportados"):
        children.append(_link("importarexpedientes_list", "Expedientes de Pago"))
    # Rendición Final is inside a Django comment, not a live sidebar link.
    return _group("comedores", "Comedores", children)


def _organizations(user):
    children = []
    if any(
        has_perm_code(user, code)
        for code in (
            "organizaciones.view_organizacion",
            "auth.role_tecnico_comedor",
            "auth.role_abogado_dupla",
        )
    ):
        children.append(_link("organizaciones", "Ver Organizaciones"))
    if has_any_perm(user, _MONTHLY_RENDICION_PERMISSIONS):
        children.append(_link("rendicioncuentasmensual_global_list", "Rendiciones"))
    return _group("organizaciones", "Organizaciones", children)


def _centro_de_infancia(user):
    children = [_link("centrodeinfancia", "Ver Centros de Infancia")]
    if has_perm_code(user, "auth.role_reportes_cdi"):
        children.append(_link("centrodeinfancia_reportes", "Reportes"))
    return _group("centro-de-infancia", "Centro de Infancia", children)


def _vpsl(user):
    children = [_link("vpsl_itinerario_list", "Itinerarios")]
    if has_perm_code(user, "ver_para_ser_libre.view_sedevpsl"):
        children.append(_link("vpsl_sede_list", "Sedes"))
    return _group("ver-para-ser-libres", "Ver Para Ser Libres", children)


def _pas():
    return _group(
        "pas",
        "PAS",
        [
            _link("pas_persona_listar", "Buscador PAS"),
            _link("pas_panel_control", "Panel de Control"),
            _link("pas_informe_listar", "Informes"),
        ],
    )


def _street_situation(user):
    children = []
    if has_perm_code(user, "dispositivos.view_dispositivo"):
        children.append(_link("dispositivos_listar", "Ver Dispositivos"))
    if has_perm_code(user, "datacalle.view_relevamiento"):
        children.append(
            _link("datacalle_relevamientos_listar", "Relevamientos DataCalle")
        )
    return _group("situacion-de-calle", "Situación de Calle", children)


def _family_center(user):
    return _group(
        "centro-de-familia",
        "Centro de Familia",
        [
            _link("centro_list", "Centros"),
            _link("beneficiarios_crear", "Nuevo Preinscripto"),
            _link("beneficiarios_list", "Lista de Preinscriptos"),
            _link("responsables_list", "Lista Responsables"),
        ],
    )


def _inet(user):
    children = [
        _link("vat_centro_list", "Centros de Formación Profesional"),
        _link(
            "vat_reporte_inscripciones_asistencias", "Reporte Inscriptos y Asistencias"
        ),
        _link("vat_buscador_ciudadano", "Buscador por Ciudadano"),
    ]
    catalog_children = []
    if has_perm_code(user, "VAT.view_modalidadcursada") and not has_any_group(
        user, "CFPINET"
    ):
        catalog_children.append(
            _link("vat_modalidadcursada_list", "Modalidades de Cursado")
        )
    if has_perm_code(user, "VAT.view_planversioncurricular"):
        catalog_children.append(
            _link("vat_planversioncurricular_list", "Planes Curriculares")
        )
    if has_perm_code(user, "VAT.view_modalidadcursada") or has_perm_code(
        user, "VAT.view_planversioncurricular"
    ):
        children.append(_group("inet-catalogos", "Catálogos", catalog_children))
    return _group("inet", "INET", children)


def _celiaquia(user):
    children = []
    if has_perm_code(user, "celiaquia.view_expediente"):
        children.append(_link("expediente_list", "Expedientes"))
    if has_perm_code(user, "celiaquia.view_cupo_dashboard"):
        children.append(_link("cupo_dashboard", "Dashboard Cupos"))
    if has_perm_code(user, "celiaquia.view_reporte_provincias"):
        children.append(_link("reporter_provincias", "Reporte"))
    return _group("celiaquia", "Celiaquía", children)


def _legajos(user, vat_sidebar_only):
    children = []
    if not vat_sidebar_only:
        if has_any_perm(
            user, ("ciudadanos.view_ciudadano", "ciudadanos.add_ciudadano")
        ):
            children.append(_history_social(user))

        if has_perm_code(user, "comedores.view_comedor") or has_perm_code(
            user, "importarexpediente.view_archivosimportados"
        ):
            children.append(_comedores(user))

        if any(
            has_perm_code(user, code)
            for code in (
                "organizaciones.view_organizacion",
                "auth.role_tecnico_comedor",
                "auth.role_abogado_dupla",
            )
        ) or has_any_perm(user, _MONTHLY_RENDICION_PERMISSIONS):
            children.append(_organizations(user))

        if has_perm_code(user, "centrodeinfancia.view_centrodeinfancia"):
            children.append(_centro_de_infancia(user))

        if has_perm_code(user, "ver_para_ser_libre.view_itinerariovpsl"):
            children.append(_vpsl(user))

        if has_perm_code(user, "pas.view_paspersona"):
            children.append(_pas())

        if puede_gestionar_inspecciones(user):
            children.append(_link("inspecciones_panel", "Inspecciones escolares"))

        if has_perm_code(user, "dispositivos.view_dispositivo") or has_perm_code(
            user, "datacalle.view_relevamiento"
        ):
            children.append(_street_situation(user))

        if has_perm_code(user, "centrodefamilia.view_centro"):
            children.append(_family_center(user))

    if has_perm_code(user, "VAT.view_centro"):
        children.append(_inet(user))

    # The template has a second not-VAT-only guard around this group.
    if not vat_sidebar_only and (
        has_perm_code(user, "celiaquia.view_expediente")
        or has_perm_code(user, "celiaquia.view_cupo_dashboard")
        or has_perm_code(user, "celiaquia.view_reporte_provincias")
        or user.is_superuser
    ):
        children.append(_celiaquia(user))

    return _group("legajos", "Legajos", children)


def _dashboard_items(request, user, vat_sidebar_only):
    administrar = puede_administrar_tableros(user)
    if vat_sidebar_only and not administrar:
        return None
    dashboard_context = (
        [] if vat_sidebar_only else obtener_tableros({"request": request})
    )
    if not (
        has_perm_code(user, "dashboard.view_dashboard")
        or dashboard_context
        or administrar
    ):
        return None
    children = [_dashboard_item(item) for item in dashboard_context]
    if administrar:
        children.insert(
            0, _link("dashboard_administracion_datos", "Administración de tableros")
        )
    return _group("tableros", "Tableros", children)


def build_web_navigation(request):
    """Project the current legacy sidebar into ordered, visible JSON-safe items.

    CSS ``order`` values are reflected in the returned top-level list. As in
    the legacy template, Legajos remains visible even when it has no children,
    and Mi Cuenta stays last as a sticky footer item.
    """
    user = request.user
    vat_sidebar_only = is_vat_sidebar_only(user)
    cdi_local_sidebar_only = is_cdi_local_sidebar_only(user)
    datacalle_sidebar_only = is_datacalle_sidebar_only(user)

    # The template's physical order is Inicio, Comunicados, Administración,
    # Configuración, OCR, Tableros, Legajos. CSS order is 1 through 7.
    items = [_link("inicio", "Inicio"), _legajos(user, vat_sidebar_only)]

    dashboard = _dashboard_items(request, user, vat_sidebar_only)
    if dashboard is not None:
        items.append(dashboard)

    administration = _administration(user, vat_sidebar_only)
    if administration is not None:
        items.append(administration)

    configuration = _commedores_configuration(
        user, vat_sidebar_only, datacalle_sidebar_only
    )
    if configuration is not None:
        items.append(configuration)

    if (
        not vat_sidebar_only
        and not datacalle_sidebar_only
        and (_direct_permission(user, "ocr.use_ocr") or user.is_superuser)
    ):
        items.append(_link("ocr_upload", "OCR"))

    if (
        not vat_sidebar_only
        and not cdi_local_sidebar_only
        and not datacalle_sidebar_only
    ):
        communicated_children = [_link("comunicados", "Ver Comunicados")]
        if has_any_perm(
            user,
            (
                "comunicados.add_comunicado",
                "comunicados.change_comunicado",
                "auth.role_admin",
                "auth.role_administrador",
                "auth.role_superadmin",
            ),
        ):
            communicated_children.append(
                _link("comunicados_gestion", "Crear comunicado")
            )
        items.append(_group("comunicados", "Comunicados", communicated_children))

    items.append(_link("mi_cuenta", "Mi cuenta"))
    return items
