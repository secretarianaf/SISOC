"""Read-only projection of the native monthly list reached from Acompañamiento."""

from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from comedores.models import Comedor
from core.decorators import _has_any_permissions
from core.web_gate import WebGatePermission
from iam.services import user_has_permission_code
from rendicioncuentasmensual.urls import _RENDICION_PERM
from rendicioncuentasmensual.views import RendicionCuentaMensualListView
from rendicioncuentasmensual.web_api import RendicionAccess


@method_decorator(never_cache, name="dispatch")
class RendicionPorComedorWebView(APIView):
    """The same list guard, project scope and links as the canonical circuit."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, RendicionAccess]
    renderer_classes = [JSONRenderer]
    http_method_names = ["get", "head"]

    def get(self, request, comedor_id):
        view = RendicionCuentaMensualListView()
        native_request = request._request  # pylint: disable=protected-access
        view.setup(native_request, comedor_id=comedor_id)
        view.object_list = view.get_queryset()
        try:
            context = view.get_context_data()
        except (Comedor.DoesNotExist, Http404) as exc:
            raise NotFound() from exc

        can_create_or_delete = _has_any_permissions(request.user, _RENDICION_PERM)
        can_edit = can_create_or_delete and user_has_permission_code(
            request.user, "rendicioncuentasmensual.edit_rendicion_data"
        )
        rows = []
        for rendicion in context["rendiciones_cuentas_mensuales"]:
            args = [rendicion.pk]
            rows.append(
                {
                    "id": rendicion.pk,
                    "mes": rendicion.mes,
                    "anio": rendicion.anio,
                    "observaciones": rendicion.observaciones or "",
                    "detail_url": reverse("rendicioncuentasmensual_detail", args=args),
                    "edit_url": (
                        reverse("rendicioncuentasmensual_update", args=args)
                        if can_edit
                        else None
                    ),
                    "delete_url": (
                        reverse("rendicioncuentasmensual_delete", args=args)
                        if can_create_or_delete
                        else None
                    ),
                }
            )
        return Response(
            {
                "comedor": view.comedor.nombre,
                "back_url": reverse("detalle_acompanamiento", args=[comedor_id]),
                "new_url": (
                    reverse("rendicioncuentasmensual_create", args=[comedor_id])
                    if can_create_or_delete
                    else None
                ),
                "rows": rows,
            }
        )
