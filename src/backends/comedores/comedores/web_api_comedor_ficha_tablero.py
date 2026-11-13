"""Board of the comedor ficha for the web API (CO07.01): ``tablero`` key.

Projects, from the native ``ComedorDetailView`` context, the blocks of
``comedor_detail.html`` between the accordion and the nómina card: the timeline,
the four summary boxes, the age-range chart data, the «Detalles de Admisión» /
«Datos del Convenio» card and the card-holder card. Values are rendered with the
template's own expressions (defaults, ``date``/``floatformat``), so the JSON shows
what the page shows. The nómina, certificaciones, colaboradores,
intervenciones, observaciones, historial and capacitaciones blocks are other keys
or other screens.
"""

import html

from django.urls import reverse

from comedores.web_api_comedor_ficha_datos import _render

SIN_INFO = "Sin información"
RANGOS = (
    ("Sin dato", "nomina_pct_sin_dato"),
    ("0-13 años", "nomina_pct_ninos"),
    ("14-17 años", "nomina_pct_adolescentes"),
    ("18-49 años", "nomina_pct_adultos"),
    ("50-65 años", "nomina_pct_adultos_mayores"),
    ("+66 años", "nomina_pct_adulto_mayor_avanzado"),
)


def _txt(source, **context):
    """A template expression whose literals carry HTML entities (``&oacute;``)."""
    return html.unescape(_render(source, **context))


def _fecha(valor):
    return valor.strftime("%d/%m/%Y") if valor else None


def _timeline(context):
    admision = context["selected_admision"] or context.get("admision_activa")
    circulo = context.get("timeline_admision_circle_html") or "1"
    return {
        "admision": {
            "clase": context.get("timeline_admision_step_class") or "step active",
            # The native circle is ``<i class="bi bi-check-lg">`` once the admission is sent.
            "completada": "bi-check-lg" in str(circulo),
            "circulo": "1" if "bi-check-lg" in str(circulo) else str(circulo),
            "fecha": _render(
                "{% if a and a.fecha_estado_mostrar %}{{ a.fecha_estado_mostrar|date:'d/m/Y' }}"
                "{% else %}{{ d|date:'d/m/Y'|default:'-' }}{% endif %}",
                a=admision,
                d=context.get("timeline_admision_date"),
            ),
        },
        "conector": context.get("timeline_connector_class") or "connector",
        "ejecucion": {
            "clase": context.get("timeline_ejecucion_step_class") or "step",
            "circulo": context.get("timeline_ejecucion_circle") or "2",
        },
        "rendicion": {"circulo": context.get("timeline_rendicion_circle") or "3"},
    }


def _resumen(context):
    pnud = context["es_programa_pnud"]
    return [
        {
            "icon": "bi bi-cup-hot",
            "valor": _render(
                "{% if sin_linea %}-{% else %}"
                '{{ total|default_if_none:"0" }}{% endif %}',
                sin_linea=context["es_linea_secos"] or context["es_linea_tradicional"],
                total=context["prestaciones_aprobadas_total"],
            ),
            "label": "Prestaciones mensuales",
        },
        {
            "icon": "bi bi-person-walking",
            "valor": _render(
                '{{ n|default_if_none:"0" }}',
                n=context["actividades_comunitarias_count"],
            ),
            "label": "Actividades Comunitarias",
        },
        {
            "icon": "bi bi-clipboard-check",
            "valor": _render(
                '{{ n|default_if_none:"0" }}',
                n=(
                    context["actividades_pnud_legajo_count"]
                    if pnud
                    else context["count_relevamientos"]
                ),
            ),
            "label": "Actividades" if pnud else "Acompañamiento Territorial",
        },
        {
            "icon": "bi bi-graph-up-arrow",
            "valor": _txt(
                '{% with numero|default_if_none:"" as n %}'
                "{% with total|default_if_none:0 as t %}"
                '{% if t %}{% if n != "" %}{{ n }}&deg; / {{ t }}{% else %}- / {{ t }}'
                "{% endif %}{% else %}0{% endif %}{% endwith %}{% endwith %}",
                numero=context["selected_convenio_numero"],
                total=context["total_admisiones"],
            ),
            "label": "Numero de Convenio",
        },
    ]


def _grafico(context):
    return [
        {"label": etiqueta, "valor": float(context.get(clave) or 0)}
        for etiqueta, clave in RANGOS
    ]


def _convenio_pnud(context, comedor):
    datos = context["datos_convenio_pnud"]
    secos = context["es_linea_secos"]
    tradicional = context["es_linea_tradicional"]

    def fila(label, expresion):
        return {
            "label": label,
            "value": _txt(
                expresion,
                comedor=comedor,
                c=datos,
                dom=context["domicilio_completo_comedor"],
            ),
        }

    def sin(expresion_campo):
        return "{{ " + expresion_campo + '|default_if_none:"Sin informaci&oacute;n" }}'

    def monto(campo):
        return '{{ c.%s|floatformat:"0g"|default:"Sin informaci&oacute;n" }}' % campo

    filas = [
        fila("Organización solicitante", sin("comedor.organizacion")),
        fila("Código del proyecto", sin("comedor.codigo_de_proyecto")),
        fila("Monto total conveniado", monto("monto_total_conveniado")),
        fila("Nro convenio", sin("c.nro_convenio")),
        fila("Estado general", sin("comedor.get_estado_general_display")),
        fila(
            "Subestado",
            "{% if comedor.ultimo_estado and comedor.ultimo_estado.estado_general and "
            "comedor.ultimo_estado.estado_general.estado_proceso %}"
            "{{ comedor.ultimo_estado.estado_general.estado_proceso.estado }}"
            "{% else %}Sin informaci&oacute;n{% endif %}",
        ),
        fila("Nombre del espacio comunitario", sin("comedor.nombre")),
        fila("ID externo", sin("comedor.id_externo")),
        fila("Domicilio completo", sin("dom")),
        fila(
            "Monto total de convenio por Espacio - Prestaciones Alimentarias",
            monto("monto_convenio_prestaciones_alimentarias"),
        ),
        fila(
            "Monto total de convenio por Espacio - Servicio Integral de Promoción Humana",
            monto("monto_convenio_siph"),
        ),
    ]
    if not secos and not tradicional:
        filas.append(
            fila(
                "Prestaciones financiadas mensuales",
                sin("c.prestaciones_financiadas_mensuales"),
            )
        )
    if tradicional:
        for etiqueta, campo in (
            ("Desayuno", "desayuno"),
            ("Almuerzo", "almuerzo"),
            ("Merienda", "merienda"),
            ("Merienda Reforzada", "merienda_reforzada"),
            ("Cena", "cena"),
        ):
            filas.append(
                fila(
                    f"Prestaciones Financiadas Diarias - {etiqueta}",
                    sin(f"c.prestaciones_financiadas_diarias_{campo}"),
                )
            )
    filas.append(fila("Personas conveniadas", sin("c.personas_conveniadas")))
    if not tradicional:
        filas.append(fila("Cantidad Módulos Mensuales", sin("c.cantidad_modulos")))
    return {
        "tipo": "convenio",
        "titulo": "Datos del Convenio",
        "territoriales": [
            {"territorial": str(t["territorial"]), "codigo": str(t["codigo"])}
            for t in context["territoriales_por_proyecto"]
        ],
        "filas": filas,
        "accion": {
            "label": "Editar datos del Convenio",
            "url": reverse("comedor_convenio_pnud", args=[comedor.pk]),
        },
    }


def _admision(context, comedor):
    admision = context["selected_admision"] or context.get("admision_activa")

    def fila(label, expresion, mayusculas=True):
        valor = _txt(expresion, a=admision, comedor=comedor)
        return {"label": label, "value": valor, "mayusculas": mayusculas}

    def campo(expresion):
        return (
            "{% if a and a." + expresion + " %}{{ a." + expresion + " }}"
            "{% else %}Sin informaci&oacute;n{% endif %}"
        )

    def display(campo_estado, getter):
        return (
            "{% if a and a." + campo_estado + " %}"
            "{{ a." + getter + '|default_if_none:"Sin informaci&oacute;n" }}'
            "{% else %}Sin informaci&oacute;n{% endif %}"
        )

    filas = [
        fila(
            "Fecha",
            "{% if a and a.creado %}{{ a.creado|date:'d/m/Y' }}"
            "{% else %}Sin informaci&oacute;n{% endif %}",
            False,
        ),
        fila("Número de expediente", campo("num_expediente")),
        fila(
            "Estado - técnicos",
            display("estado_admision", "get_estado_admision_display"),
        ),
        fila(
            "Estado - legales",
            display("estado_legales", "get_estado_legales_display"),
        ),
        fila("Estado actual", display("estado_mostrar", "estado_mostrar")),
        fila(
            "Fecha estado",
            "{% if a and a.fecha_estado_mostrar %}{{ a.fecha_estado_mostrar|date:'d/m/Y' }}"
            "{% else %}Sin informaci&oacute;n{% endif %}",
            False,
        ),
        fila("N° IF", campo("num_if")),
        fila("N° IF legales", campo("legales_num_if")),
        fila("N° IF técnico", campo("numero_if_tecnico")),
        fila("N° disposición", campo("numero_disposicion")),
        fila(
            "Dupla",
            '{{ comedor.dupla.nombre|default_if_none:"Sin informaci&oacute;n" }}',
        ),
        fila(
            "Tipo de convenio",
            "{% if a and a.tipo_convenio %}"
            '{{ a.tipo_convenio.nombre|default_if_none:"Sin informaci&oacute;n" }}'
            "{% else %}Sin informaci&oacute;n{% endif %}",
        ),
    ]
    return {
        "tipo": "admision",
        "titulo": "Detalles de Admisión",
        "filas": filas,
        "accion": {
            "label": "Ver detalles",
            "url": (
                reverse("admision_detalle", args=[comedor.pk, admision.pk])
                if admision
                else None
            ),
        },
    }


def _responsable_tarjeta(context, comedor):
    if not context["puede_gestionar_responsable_tarjeta"]:
        return None
    campos = (
        "responsable_tarjeta_nombre",
        "responsable_tarjeta_mail",
        "responsable_tarjeta_dni",
        "responsable_tarjeta_cuit",
        "responsable_tarjeta_domicilio",
        "responsable_tarjeta_provincia",
        "responsable_tarjeta_municipio",
        "responsable_tarjeta_localidad",
        "responsable_tarjeta_telefono",
    )
    hay = any(getattr(comedor, c, None) for c in campos)

    def v(expresion):
        return _render(expresion, comedor=comedor)

    return {
        "hay_datos": hay,
        "datos": (
            [
                ("Nombre", v('{{ comedor.responsable_tarjeta_nombre|default:"-" }}')),
                ("DNI", v('{{ comedor.responsable_tarjeta_dni|default:"-" }}')),
                (
                    "Domicilio",
                    v('{{ comedor.responsable_tarjeta_domicilio|default:"-" }}'),
                ),
                ("CUIT", v('{{ comedor.responsable_tarjeta_cuit|default:"-" }}')),
                (
                    "Correo electrónico",
                    v('{{ comedor.responsable_tarjeta_mail|default:"-" }}'),
                ),
                (
                    "Teléfono",
                    v('{{ comedor.responsable_tarjeta_telefono|default:"-" }}'),
                ),
                (
                    "Municipio",
                    v(
                        "{% firstof comedor.responsable_tarjeta_municipio.nombre "
                        'comedor.responsable_tarjeta_localidad.municipio.nombre "-" %}'
                    ),
                ),
                (
                    "Localidad",
                    v('{{ comedor.responsable_tarjeta_localidad.nombre|default:"-" }}'),
                ),
                (
                    "Provincia",
                    v('{{ comedor.responsable_tarjeta_provincia.nombre|default:"-" }}'),
                ),
            ]
            if hay
            else []
        ),
        "editar": reverse("comedor_responsable_tarjeta_editar", args=[comedor.pk]),
    }


def tablero(context, comedor):
    """Timeline, summary boxes, chart data, details card and card-holder card."""
    return {
        "timeline": _timeline(context),
        "resumen": _resumen(context),
        "grafico": _grafico(context),
        "detalles": (
            _convenio_pnud(context, comedor)
            if context["usa_convenio_pnud"]
            else _admision(context, comedor)
        ),
        "responsable_tarjeta": _responsable_tarjeta(context, comedor),
    }
