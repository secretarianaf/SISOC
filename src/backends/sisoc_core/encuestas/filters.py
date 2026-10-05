"""Filtros del listado, compartidos con el buscador Poncho de SISOC."""

from core.services.advanced_filters import AdvancedFilterEngine

from .models import EstadoEncuesta


FIELDS = [
    {"name": "titulo", "label": "Título", "type": "text"},
    {
        "name": "estado",
        "label": "Estado",
        "type": "choice",
        "choices": [
            {"value": value, "label": label} for value, label in EstadoEncuesta.choices
        ],
    },
    {"name": "es_anonima", "label": "Anónima", "type": "boolean"},
    {"name": "es_recurrente", "label": "Recurrente", "type": "boolean"},
]

FILTER_ENGINE = AdvancedFilterEngine(
    field_map={field["name"]: field["name"] for field in FIELDS},
    field_types={field["name"]: field["type"] for field in FIELDS},
    allowed_ops={"text": {"contains"}, "choice": {"eq"}, "boolean": {"eq"}},
)


def get_filters_config():
    return {"fields": FIELDS, "defaultField": "titulo"}
