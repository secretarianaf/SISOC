"""Papelera para React (T06, G1 v1): ``/api/web/core/papelera/``.

Solo superusuarios, como ``SuperAdminRequiredMixin`` (``403`` para el resto, también el
``POST``). El listado reutiliza los helpers de ``core.trash_views`` (formulario de
filtros, búsqueda, rango de fechas, orden y paginación); la restauración es la vista
nativa ``TrashRestoreView.post`` (cascada, mensaje en cola, redirección), nunca un
update directo.
"""

# pylint: disable=protected-access

from urllib.parse import quote

from django.template import Context, Template
from django.urls import reverse
from django.utils.timezone import localtime
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from core.soft_delete.preview import build_restore_preview
from core.soft_delete.registry import get_soft_delete_model_choices
from core.trash_views import (
    TrashListView,
    TrashRestoreView,
    _build_active_filters,
    _build_deleted_queryset,
    _build_filter_form_and_data,
    _build_pagination_querystring,
    _get_models_to_scan,
    _get_safe_next_url,
    _instance_details,
    _model_key,
    _paginate_trash_items,
    _resolve_model_or_404,
    _rows_from_items,
    _soft_models_by_key,
)
from core.web_api_core_base import (
    DETAIL_FORBIDDEN,
    CoreWebView,
    native_view,
    native_attrs,
    pending_messages,
)

_VALOR = Template("{{ value|default:'-' }}")
CAMPOS_FILTRO = ("model", "q", "deleted_by", "deleted_from", "deleted_to")


def _valor(value):
    """``{{ item.value|default:"-" }}`` de la plantilla, sin escapar HTML."""
    return _VALOR.render(Context({"value": value}, autoescape=False))


def _solo_superusuario(request):
    if not request.user.is_superuser:
        raise PermissionDenied(DETAIL_FORBIDDEN)


def _fila(row, siguiente):
    objeto = row["obj"]
    quien = objeto.deleted_by
    url = reverse(
        "papelera_preview_restore",
        kwargs={
            "app_label": row["app_label"],
            "model_name": row["model_name"],
            "pk": objeto.pk,
        },
    )
    return {
        "id": objeto.pk,
        "label": str(objeto),
        "model_label": row["model_label"],
        "deleted_at": localtime(objeto.deleted_at).strftime("%d/%m/%Y %H:%M"),
        "deleted_by": (quien.get_full_name() or quien.username) if quien else None,
        "restore_url": f"{url}?next={siguiente}",
    }


def _campos(filter_form):
    campos = {
        nombre: {
            "id": filter_form[nombre].id_for_label,
            "label": str(filter_form[nombre].label),
            "value": filter_form[nombre].value() or "",
            "attrs": native_attrs(filter_form[nombre]),
        }
        for nombre in CAMPOS_FILTRO
    }
    campos["model"]["choices"] = [
        {"value": str(valor), "label": str(texto)}
        for valor, texto in filter_form.fields["model"].choices
    ]
    return campos


def _errores(filter_form):
    lineas = []
    if filter_form.errors:
        for campo in filter_form:
            lineas.extend(f"{campo.label}: {error}" for error in campo.errors)
        lineas.extend(str(error) for error in filter_form.non_field_errors())
    return lineas


class PapeleraWebView(CoreWebView):
    """``TrashListView``: mismos filtros, orden y paginación."""

    def get(self, request):
        _solo_superusuario(request)
        model_choices = get_soft_delete_model_choices()
        if not model_choices:
            raise NotFound("No hay modelos con borrado lógico registrados.")
        django_request = request._request
        models_by_key = _soft_models_by_key()
        order_keys = [key for key, _ in model_choices]
        filter_form, selected_key, filter_data = _build_filter_form_and_data(
            request=django_request,
            model_choices=model_choices,
            models_by_key=models_by_key,
        )
        selected_key = filter_data.get("model", selected_key or "")
        selected_label = (
            str(models_by_key[selected_key]._meta.verbose_name_plural).title()
            if selected_key
            else "Todos los modelos"
        )
        queryset = _build_deleted_queryset(
            models_to_scan=_get_models_to_scan(
                selected_key=selected_key,
                models_by_key=models_by_key,
                order_keys=order_keys,
            ),
            filter_data=filter_data,
        )
        page = _paginate_trash_items(
            queryset_or_items=queryset,
            page_number=request.GET.get("page") or 1,
            paginate_by=TrashListView.paginate_by,
        )
        rows = _rows_from_items(page.object_list, models_by_key)
        active = (
            _build_active_filters(
                filter_data, selected_model_label=selected_label, default_model_key=""
            )
            if filter_data
            else []
        )
        # ``{{ current_full_path|urlencode }}`` de la plantilla.
        siguiente = quote(django_request.get_full_path(), safe="/")
        return Response(
            {
                "filters": _campos(filter_form),
                "filter_errors": _errores(filter_form),
                "active_filters": active,
                "selected_model_label": selected_label,
                "show_all_models": not selected_key,
                "deleted_count": page.paginator.count,
                "rows": [_fila(row, siguiente) for row in rows],
                "pagination": {
                    "num_pages": page.paginator.num_pages,
                    "number": page.number,
                    "previous": (
                        page.previous_page_number() if page.has_previous() else None
                    ),
                    "next": page.next_page_number() if page.has_next() else None,
                    "querystring": _build_pagination_querystring(django_request),
                },
                "urls": {"list": reverse("papelera_list"), "home": reverse("inicio")},
                "messages": pending_messages(request),
            }
        )


class PapeleraRestaurarWebView(CoreWebView):
    """``TrashRestorePreviewView`` (``GET``) y ``TrashRestoreView`` (``POST``)."""

    def get(self, request, app_label, model_name, pk):
        _solo_superusuario(request)
        modelo = _resolve_model_or_404(app_label, model_name)
        instancia = modelo.all_objects.filter(pk=pk, deleted_at__isnull=False).first()
        if instancia is None:
            raise NotFound("El registro no está en papelera.")
        preview = build_restore_preview(instancia)
        siguiente = _get_safe_next_url(request._request)
        volver = f"{reverse('papelera_list')}?model={_model_key(modelo)}"
        return Response(
            {
                "id": instancia.pk,
                "label": str(instancia),
                "model_identifier": f"{modelo._meta.app_label}.{modelo._meta.model_name}",
                "total_afectados": preview["total_afectados"],
                "details": [
                    {"label": str(item["label"]), "value": _valor(item["value"])}
                    for item in _instance_details(instancia)
                ],
                "breakdown": [
                    {
                        "modelo": str(item["modelo"]),
                        "cantidad": item["cantidad"],
                        "ejemplos": [str(e) for e in item["ejemplos"]],
                    }
                    for item in preview["desglose_por_modelo"]
                ],
                "restore_url": reverse(
                    "papelera_restore",
                    kwargs={
                        "app_label": app_label,
                        "model_name": modelo._meta.model_name,
                        "pk": pk,
                    },
                ),
                "back_url": siguiente or volver,
                "next_url": siguiente,
                "urls": {"home": reverse("inicio"), "list": reverse("papelera_list")},
                "messages": pending_messages(request),
            }
        )

    def post(self, request, app_label, model_name, pk):
        _solo_superusuario(request)
        vista = native_view(
            TrashRestoreView, request, app_label=app_label, model_name=model_name, pk=pk
        )
        respuesta = vista.post(request._request, app_label, model_name, pk)
        return Response({"ok": True, "redirect": respuesta["Location"]})
