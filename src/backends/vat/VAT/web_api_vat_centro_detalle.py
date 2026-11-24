"""Web API (G1 v1) del detalle de un centro de VAT (V06.01) y de su panel de cursos y comisiones (V05.01).

``/api/web/vat/centros-detalle/<pk>/`` corre la vista nativa ``CentroDetailView`` (``setup`` + ``get_object`` con su guarda de
alcance, 404 fuera del queryset y 403 fuera del alcance del usuario, y ``get_context_data``) y proyecta lo que imprime
``centro_detail.html``; ``/api/web/vat/centros-detalle/<pk>/cursos/`` corre ``CentroCursosPanelView`` y proyecta
``partials/centro_cursos_panel.html``, el fragmento que la página nativa carga por AJAX. Los valores se renderizan con el
motor de plantillas para que el texto coincida con el HTML nativo. Acceso: ``VAT.view_centro``, como la ruta.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.centro import CentroCursosPanelView, CentroDetailView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto
from VAT.web_api_vat_centro_acciones import campos_modal, planes_curriculares

_VER = ["VAT.view_centro"]
_GUION = "{{ v|default:'-' }}"
_MAPA = (
    "https://maps.google.com/maps?hl=es&q={{ c.calle|urlencode }}"
    "{% if c.numero %}+{{ c.numero|urlencode }}{% endif %},"
    "+{{ c.localidad.nombre|urlencode }},+{{ c.provincia.nombre|urlencode }},"
    "+Argentina+({{ c.nombre|urlencode }})&t=&z=16&ie=UTF8&iwloc=B&output=embed"
)


def _guion(valor):
    return texto(_GUION, v=valor)


def _domicilio(centro):
    if centro.calle:
        return texto(
            "{{ c.calle }} {% if c.numero %}{{ c.numero }}{% endif %}", c=centro
        ).strip()
    return _guion(centro.domicilio_actividad)


def _mapa(centro):
    if centro.calle and centro.localidad and centro.provincia:
        return texto(_MAPA, c=centro)
    return None


def _referente(centro, contacto):
    """The «Referente del centro» list: the centro fields first, then the primary additional contact."""
    nombre = "-"
    if centro.nombre_referente or centro.apellido_referente:
        nombre = f"{centro.nombre_referente} {centro.apellido_referente}"
    elif contacto and contacto.nombre_contacto:
        nombre = contacto.nombre_contacto
    telefono = (
        centro.telefono_referente
        or (contacto.telefono_contacto if contacto else "")
        or "-"
    )
    correo = (
        centro.correo_referente or (contacto.email_contacto if contacto else "") or "-"
    )
    return {
        "nombre": nombre,
        "telefono": telefono,
        "dni": str(contacto.documento) if contacto and contacto.documento else "-",
        "correo": correo,
    }


def _usuarios_referentes(referentes):
    return [
        texto(
            "{{ u.get_full_name|default:u.username }}",
            u=usuario,
        )
        for usuario in referentes
    ]


def _ubicacion(ubicacion):
    return {
        "id": ubicacion.pk,
        "nombre": texto(
            "{{ u.nombre_ubicacion|default:u.get_rol_ubicacion_display }}",
            u=ubicacion,
        ),
        "caracteristica": ubicacion.get_rol_ubicacion_display(),
        "localidad": texto("{{ u.localidad|default:'-' }}", u=ubicacion),
        "domicilio": texto("{{ u.domicilio|default:'-' }}", u=ubicacion),
        "urls": {
            "form": f"/api/web/vat/centros-acciones/ubicaciones/{ubicacion.pk}/editar/",
            "guardar": f"/api/web/vat/institucion/ubicaciones/{ubicacion.pk}/editar/",
            "eliminar": f"/api/web/vat/institucion/ubicaciones/{ubicacion.pk}/eliminar/",
        },
    }


def _contacto(contacto):
    return {
        "id": contacto.pk,
        "nombre": _guion(contacto.nombre_contacto),
        "documento": _guion(contacto.documento),
        "rol": _guion(contacto.rol_area),
        "principal": bool(contacto.es_principal),
        "telefono": _guion(contacto.telefono_contacto),
        "urls": {
            "form": f"/api/web/vat/centros-acciones/contactos/{contacto.pk}/editar/",
            "guardar": f"/api/web/vat/institucion/contactos/{contacto.pk}/editar/",
            "eliminar": f"/api/web/vat/institucion/contactos/{contacto.pk}/eliminar/",
        },
    }


def _modales_detalle(contexto, centro):
    """The add forms of the native modals (``contacto_form.as_p`` and ``ubicacion_form.as_p``); they exist only for an editable centro."""
    if not contexto["can_edit_centro"]:
        return None
    return {
        "contacto": {
            "fields": campos_modal(contexto["contacto_form"]),
            "crear": f"/api/web/vat/institucion/contactos/nuevo/?centro={centro.pk}",
        },
        "ubicacion": {
            "fields": campos_modal(contexto["ubicacion_form"]),
            "crear": f"/api/web/vat/institucion/ubicaciones/nuevo/?centro={centro.pk}",
            "localidades": reverse("ajax_load_localidades"),
        },
    }


class CentroDetalleWebView(VatNativeReadView):
    """``GET .../centros-detalle/<pk>/``: ``centro_detail.html`` (information, additional locations and contacts)."""

    native_class = CentroDetailView
    codigos = _VER

    def get(self, request, pk):
        _vista, contexto = self.detalle(pk)
        centro = contexto["centro"]
        usuario = request.user
        contactos = contexto["contactos"]
        principal = contactos[0] if contactos else None
        return Response(
            {
                "id": centro.pk,
                "nombre": centro.nombre,
                "codigo": _guion(centro.codigo),
                "activo": bool(centro.activo),
                "mostrar_datos_administrativos": bool(
                    contexto["mostrar_datos_administrativos"]
                ),
                "tipo_gestion": _guion(centro.tipo_gestion),
                "domicilio": _domicilio(centro),
                "telefono": _guion(centro.telefono),
                "celular": _guion(centro.celular),
                "correo": centro.correo or None,
                "mapa": _mapa(centro),
                "referente": {
                    **_referente(centro, principal),
                    "usuarios": _usuarios_referentes(contexto["referentes_centro"]),
                },
                "ubicaciones": [_ubicacion(u) for u in contexto["ubicaciones"]],
                "contactos": [_contacto(c) for c in contactos],
                "permisos": {
                    "editar_centro": bool(contexto["can_edit_centro"]),
                    "agregar_ubicacion": usuario.has_perm(
                        "VAT.add_institucionubicacion"
                    ),
                    "editar_ubicacion": usuario.has_perm(
                        "VAT.change_institucionubicacion"
                    ),
                    "eliminar_ubicacion": usuario.has_perm(
                        "VAT.delete_institucionubicacion"
                    ),
                    "agregar_contacto": usuario.has_perm("VAT.add_institucioncontacto"),
                    "editar_contacto": usuario.has_perm(
                        "VAT.change_institucioncontacto"
                    ),
                    "eliminar_contacto": usuario.has_perm(
                        "VAT.delete_institucioncontacto"
                    ),
                },
                "urls": {
                    "cursos": f"/api/web/vat/centros-detalle/{centro.pk}/cursos/",
                },
                "modales": _modales_detalle(contexto, centro),
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )


def _curso(curso, permisos, gestionar):
    return {
        "id": curso.pk,
        "nombre": curso.nombre,
        "plan": texto("{{ c.plan_estudio_label|default:'' }}", c=curso),
        "comisiones": int(curso.comisiones_count),
        "edicion": (
            {
                "plan_estudio": str(curso.plan_estudio_id or ""),
                "nombre": curso.nombre,
                "tipo": [str(valor) for valor in (curso.tipo or [])],
                "estado": curso.estado or "",
                "inscripcion_libre": bool(curso.inscripcion_libre),
                "observaciones": curso.observaciones or "",
                "guardar": f"/api/web/vat/centros-acciones/cursos/{curso.pk}/editar/",
            }
            if gestionar and permisos["editar_curso"]
            else None
        ),
        "urls": {
            "detalle": (
                reverse("vat_curso_detail", args=[curso.pk])
                if permisos["ver_curso"]
                else None
            ),
            "comision_nueva": (
                reverse("vat_comision_curso_wizard", args=[curso.pk])
                if gestionar and permisos["agregar_comision"]
                else None
            ),
            "eliminar": (
                reverse("vat_curso_delete", args=[curso.pk])
                if gestionar and permisos["eliminar_curso"]
                else None
            ),
        },
    }


def _comision(comision, permisos, gestionar):
    return {
        "id": comision.pk,
        "curso_id": comision.curso_id,
        "curso_nombre": comision.curso.nombre,
        "codigo": comision.codigo_comision or "",
        "nombre": comision.nombre or "",
        "codigo_o_nombre": texto(
            "{{ c.codigo_comision|default:c.nombre }}", c=comision
        ),
        "ubicacion": texto("{{ c.ubicacion|default:'' }}", c=comision),
        "fecha_inicio": texto(
            "{{ c.fecha_inicio|date:'d/m/Y'|default:'-' }}", c=comision
        ),
        "fecha_fin": texto("{{ c.fecha_fin|date:'d/m/Y'|default:'-' }}", c=comision),
        "cupo": texto("{{ c.cupo_total|default:'-' }}", c=comision),
        "estado": comision.estado,
        "edicion": (
            {
                "curso": str(comision.curso_id),
                "curso_nombre": comision.curso.nombre,
                "ubicacion": str(comision.ubicacion_id or ""),
                "cupo_total": texto("{{ c.cupo_total }}", c=comision),
                "acepta_lista_espera": bool(comision.acepta_lista_espera),
                "cupo_lista_espera": texto(
                    "{{ c.cupo_lista_espera|default_if_none:'' }}", c=comision
                ),
                "fecha_inicio": texto("{{ c.fecha_inicio|date:'Y-m-d' }}", c=comision),
                "fecha_fin": texto("{{ c.fecha_fin|date:'Y-m-d' }}", c=comision),
                "estado": comision.estado,
                "observaciones": comision.observaciones or "",
                "guardar": f"/api/web/vat/comisiones-formularios/cursos/{comision.pk}/editar/",
            }
            if gestionar and permisos["editar_comision"]
            else None
        ),
        "urls": {
            "detalle": (
                reverse("vat_comision_curso_detail", args=[comision.pk])
                if permisos["ver_comision"]
                else None
            ),
            "eliminar": (
                reverse("vat_comision_curso_delete", args=[comision.pk])
                if gestionar and permisos["eliminar_comision"]
                else None
            ),
        },
    }


def _modales_panel(contexto, centro_id):
    """The forms of ``#modalCurso`` and ``#modalComisionCurso`` and the rows of the plan selector (only for a manageable centro)."""
    curso_form = contexto["curso_form"]
    return {
        "curso": {
            "fields": campos_modal(curso_form),
            "planes": planes_curriculares(curso_form),
            "crear": f"/api/web/vat/centros-acciones/cursos/nuevo/?centro={centro_id}",
        },
        "comision_curso": {
            "fields": campos_modal(contexto["comision_curso_form"]),
        },
    }


class CentroCursosPanelWebView(VatNativeReadView):
    """``GET .../centros-detalle/<pk>/cursos/``: ``partials/centro_cursos_panel.html`` (courses and commissions)."""

    native_class = CentroCursosPanelView
    codigos = _VER

    def get(self, request, pk):
        _vista, contexto = self.detalle(pk)
        usuario = request.user
        gestionar = bool(contexto["can_manage_centro"])
        permisos = {
            "ver_curso": usuario.has_perm("VAT.view_curso"),
            "agregar_comision": usuario.has_perm("VAT.add_comisioncurso"),
            "editar_curso": usuario.has_perm("VAT.change_curso"),
            "eliminar_curso": usuario.has_perm("VAT.delete_curso"),
            "ver_comision": usuario.has_perm("VAT.view_comisioncurso"),
            "editar_comision": usuario.has_perm("VAT.change_comisioncurso"),
            "eliminar_comision": usuario.has_perm("VAT.delete_comisioncurso"),
        }
        return Response(
            {
                "cursos": [
                    _curso(curso, permisos, gestionar) for curso in contexto["cursos"]
                ],
                "comisiones": [
                    _comision(comision, permisos, gestionar)
                    for comision in contexto["comisiones_curso"]
                ],
                "permisos": {
                    "gestionar": gestionar,
                    "agregar_curso": usuario.has_perm("VAT.add_curso"),
                    "editar_curso": usuario.has_perm("VAT.change_curso"),
                    "editar_comision": usuario.has_perm("VAT.change_comisioncurso"),
                },
                "modales": (
                    _modales_panel(contexto, self.kwargs["pk"]) if gestionar else None
                ),
            }
        )
