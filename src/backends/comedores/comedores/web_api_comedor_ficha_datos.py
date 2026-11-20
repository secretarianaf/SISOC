"""Accordion of the comedor ficha for the web API (CO07.01): ``acordeon`` key.

Projects the four panels of ``comedor_detail.html`` (Ubicación, Responsables,
Prestaciones and Actividades / Acompañamiento Territorial) from the native
context. Every value is rendered with the same template expression the page uses
(defaults, ``date`` formats, the whitespace HTML collapses), so the JSON shows
what the page shows; React draws the markup.
"""

from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import Context, Template
from django.urls import reverse

# The package aliases its implementation module (pylint cannot see the name).
from core.services.image_service import (  # pylint: disable=no-name-in-module
    get_or_create_webp,
)

DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
COMIDAS = (
    ("Desayuno", "desayuno"),
    ("Almuerzo", "almuerzo"),
    ("Merienda", "merienda"),
    ("Cena", "cena"),
)
LOAD = "{% load custom_filters %}"


def _render(source, **context):
    """The template expression as plain text: whitespace collapsed, nothing HTML-escaped.

    The values reach React text nodes, which escape on their own; escaping here as well
    would show ``A&amp;B`` literally.
    """
    return " ".join(
        Template(LOAD + source).render(Context(context, autoescape=False)).split()
    )


def _dato(icon, label, value):
    return {"icon": icon, "label": label, "value": value}


def _mapa(comedor):
    coordenadas = _render(
        "{% google_maps_query comedor.latitud comedor.longitud as q %}{{ q }}",
        comedor=comedor,
    )
    if coordenadas:
        return {
            "tipo": "iframe",
            "src": f"https://maps.google.com/maps?q={coordenadas}&output=embed",
        }
    if (
        comedor.calle
        and comedor.numero
        and comedor.localidad
        and comedor.municipio
        and comedor.provincia
    ):
        return {
            "tipo": "iframe",
            "src": _render(
                "https://maps.google.com/maps?q={{ comedor.calle|urlencode }}"
                "+{{ comedor.numero }},+{{ comedor.localidad.nombre|urlencode }}"
                ",+{{ comedor.municipio.nombre|urlencode }}"
                ",+{{ comedor.provincia.nombre|urlencode }}&output=embed",
                comedor=comedor,
            ),
        }
    return {"tipo": "vacio", "src": None}


def _ubicacion(comedor):
    def campo(icon, label, expresion):
        return _dato(icon, label, _render(expresion, comedor=comedor))

    return {
        "mapa": _mapa(comedor),
        "datos": [
            campo(
                "bi bi-house-door-fill",
                "Nombre del espacio comunitario",
                '{{ comedor.nombre | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-tags",
                "Categorización",
                "{% if comedor.categoria_espacio_comunitario %}"
                "{{ comedor.get_categoria_espacio_comunitario_display }}"
                '{% if comedor.categoria_espacio_comunitario == "otra" and '
                "comedor.categoria_espacio_comunitario_otra %}"
                "— {{ comedor.categoria_espacio_comunitario_otra }}{% endif %}"
                "{% else %}-{% endif %}",
            ),
            campo("bi bi-geo", "Calle", '{{ comedor.calle | default_if_none:"-" }}'),
            campo(
                "bi bi-123",
                "Numeración",
                '{{ comedor.numero | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-grid", "Manzana", '{{ comedor.manzana | default_if_none:"-" }}'
            ),
            campo(
                "bi bi-building",
                "Piso y/o departamento",
                "{% if comedor.piso or comedor.departamento %}{{ comedor.piso }} "
                "{% if comedor.piso and comedor.departamento %}-{% endif %} "
                "{{ comedor.departamento }}{% else %}-{% endif %}",
            ),
            campo(
                "bi bi-signpost",
                "Entre calle 1",
                '{{ comedor.entre_calle_1 | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-signpost-2",
                "Entre calle 2",
                '{{ comedor.entre_calle_2 | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-mailbox",
                "Código Postal",
                '{{ comedor.codigo_postal | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-geo-alt",
                "Localidad",
                '{{ comedor.localidad.nombre | default_if_none:"-" }}',
            ),
            campo(
                "bi bi-map", "Partido", '{{ comedor.partido | default_if_none:"-" }}'
            ),
            campo(
                "bi bi-geo-alt-fill",
                "Provincia",
                '{{ comedor.provincia.nombre | default_if_none:"-" }}',
            ),
        ],
    }


def _foto(comedor):
    """``optimized_image``: the file, its WebP twin when there is one, or the default."""
    if not comedor.foto_legajo:
        return {
            "url": staticfiles_storage.url("custom/img/default.png"),
            "webp": None,
            "default": True,
        }
    url = comedor.foto_legajo.url
    webp = get_or_create_webp(url)
    return {
        "url": url,
        "webp": webp if webp != url and webp.endswith(".webp") else None,
        "default": False,
    }


def _responsables(context, comedor):
    organizacion = context["responsables_organizacion"]
    return {
        "foto": _foto(comedor),
        "hay_organizacion": bool(organizacion),
        "items": [
            {
                "icon": i["icon"],
                "label": i["label"],
                "value": (
                    _render("{{ v|date:'d/m/Y' }}", v=i["value"])
                    if i["is_date"]
                    else str(i["value"])
                ),
            }
            for i in context["responsables_organizacion_items"]
        ],
        "firmantes": [
            {"icon": f["icon"], "text": f["text"]}
            for f in context["responsables_firmantes"]
        ],
        "avales": [
            {"icon": a["icon"], "label": a["label"], "value": a["value"]}
            for a in context["responsables_avales"]
        ],
    }


def _celda(informe, comida, dia):
    return _render(
        '{% with val=informe|getattr:"@@" %}{% if val == "0" %}-{% else %}'
        '{{ val|default_if_none:"-" }}{% endif %}{% endwith %}'.replace(
            "@@", f"aprobadas_{comida}_{dia}"
        ),
        informe=informe,
    )


def _prestaciones(context):
    informe = context["prestaciones_aprobadas_source"]
    relevamiento = (context["relevamientos"] or [None])[0]
    sin_linea = context["es_linea_secos"] or context["es_linea_tradicional"]

    def cifra(valor):
        if sin_linea or not informe:
            return "-"
        return _render('{{ v|default_if_none:"-" }}', v=valor)

    filas = [*COMIDAS]
    if context["es_linea_tradicional"]:
        filas.insert(3, ("Merienda Reforzada", "merienda_reforzada"))
    return {
        "colaboradores": _render(
            '{{ r.colaboradores.cantidad_colaboradores.nombre|default:"-" }}',
            r=relevamiento,
        ),
        "dias_por_semana": _render(
            "{{ informe|dias_prestacion_semana }}", informe=informe
        ),
        "prestaciones_mensuales": cifra(context["prestaciones_aprobadas_total"]),
        "monto_mensual": cifra(context["monto_prestacion_mensual"]),
        "dias": [d.capitalize() for d in DIAS],
        "filas": [
            {"comida": etiqueta, "valores": [_celda(informe, clave, d) for d in DIAS]}
            for etiqueta, clave in filas
        ],
    }


def _actividad_pnud(a):
    def v(expresion):
        return _render(expresion, a=a)

    return {
        "id": a.pk,
        "categoria": v('{{ a.catalogo_actividad.categoria|default:"-" }}'),
        "actividad": v('{{ a.catalogo_actividad.actividad|default:"-" }}'),
        "dia": v('{{ a.dia_actividad|default:"-" }}'),
        "horario": v('{{ a.horario_actividad|default:"-" }}'),
        "responsable": v('{{ a.responsable_actividad|default:"-" }}'),
        "vigencia": v(
            "{% if a.vigencia_actividad_meses %}{{ a.vigencia_actividad_meses }}"
            " meses{% else %}-{% endif %}"
        ),
        "inscriptos": v('{{ a.inscriptos_activos_count|default_if_none:"0" }}'),
        "activo": bool(a.activo),
        "detalle": [
            ("Hora inicio", v('{{ a.hora_inicio|time:"H:i"|default:"-" }}')),
            ("Hora fin", v('{{ a.hora_fin|time:"H:i"|default:"-" }}')),
            ("Fecha alta", v('{{ a.fecha_alta|date:"d/m/Y H:i"|default:"-" }}')),
            (
                "Ultima actualizacion",
                v('{{ a.fecha_actualizacion|date:"d/m/Y H:i"|default:"-" }}'),
            ),
            ("Fecha baja", v('{{ a.fecha_baja|date:"d/m/Y H:i"|default:"-" }}')),
            ("Creado por", v('{{ a.creado_por|default:"-" }}')),
            ("Actualizado por", v('{{ a.actualizado_por|default:"-" }}')),
        ],
    }


NOMBRES_RECURSOS = (
    ("Particulares", "recibe_donaciones_particulares"),
    ("Estado nacional", "recibe_estado_nacional"),
    ("Estado provincial", "recibe_estado_provincial"),
    ("Estado municipal", "recibe_estado_municipal"),
    ("Otros", "recibe_otros"),
)
SERVICIOS = ("Servicio en el lugar", "Vianda", "Vianda y servicio")
ESPACIOS = (
    "Propio",
    "Alquilado",
    "Prestado (uso exclusivo)",
    "Comunitario (compartido)",
    "Casa de familia",
    "Otro",
)
ANEXO = (
    ("apoyo_escolar", "Apoyo escolar"),
    ("promocion_salud", "Promocion de la salud"),
    ("actividades_recreativas", "Recreacion"),
    ("actividades_deportivas", "Deportes"),
    ("actividades_religiosas", "Actividades religiosas"),
    ("actividades_jardin_maternal", "Jardin Maternal"),
    ("alfabetizacion_terminalidad", "Terminalidad educativa"),
    ("actividades_huerta", "Huerta"),
    ("actividades_culturales", "Actividades culturales"),
)


def _marcado(expresion, relevamiento):
    return bool(
        Template("{% if " + expresion + " %}1{% endif %}").render(
            Context({"relevamiento": relevamiento})
        )
    )


def _territorial(context):
    relevamiento = (context["relevamientos"] or [None])[0]
    anexo = getattr(relevamiento, "anexo", None) if relevamiento else None
    return {
        "donaciones": [
            {
                "label": etiqueta,
                "marcado": _marcado(
                    f"relevamiento and relevamiento.recursos and relevamiento.recursos.{campo}",
                    relevamiento,
                ),
            }
            for etiqueta, campo in NOMBRES_RECURSOS
        ],
        "servicio": [
            {
                "label": nombre,
                "marcado": _marcado(
                    "relevamiento and relevamiento.funcionamiento and "
                    "relevamiento.funcionamiento.modalidad_prestacion and "
                    f'relevamiento.funcionamiento.modalidad_prestacion.nombre == "{nombre}"',
                    relevamiento,
                ),
            }
            for nombre in SERVICIOS
        ],
        "espacio": [
            {
                "label": nombre,
                "marcado": _marcado(
                    "relevamiento and relevamiento.espacio and "
                    "relevamiento.espacio.tipo_espacio_fisico and "
                    f'relevamiento.espacio.tipo_espacio_fisico.nombre == "{nombre}"',
                    relevamiento,
                ),
            }
            for nombre in ESPACIOS
        ],
        "actividades_anexo": [
            etiqueta
            for campo, etiqueta in ANEXO
            if anexo and getattr(anexo, campo, False)
        ],
    }


def acordeon(context, comedor):
    """The four panels of the ficha accordion."""
    es_pnud = context["es_programa_pnud"]
    gestiona = context["puede_gestionar_actividades_espacio"]
    panel4 = {
        "titulo": "Actividades" if es_pnud else "Acompañamiento Territorial",
        "pnud": es_pnud,
    }
    if es_pnud:
        panel4.update(
            {
                "agregar": (
                    reverse("actividad_espacio_pwa_crear", args=[comedor.pk])
                    if gestiona
                    else None
                ),
                "actividades": [
                    {
                        **_actividad_pnud(a),
                        "editar": (
                            reverse(
                                "actividad_espacio_pwa_editar", args=[comedor.pk, a.pk]
                            )
                            if gestiona and a.activo
                            else None
                        ),
                    }
                    for a in context["actividades_pnud_legajo"]
                ],
                "puede_gestionar": bool(gestiona),
            }
        )
    else:
        panel4.update(_territorial(context))
    return {
        "ubicacion": _ubicacion(comedor),
        "responsables": _responsables(context, comedor),
        "prestaciones": _prestaciones(context),
        "relevamientos": panel4,
    }
