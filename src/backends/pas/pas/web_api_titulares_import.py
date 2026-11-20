"""Web API (G1 v1) of the PAS titulares import: ``/api/web/pas/titulares/importar/``.

Same access as the native ``pas/titulares/importar`` route: G1 first
(``WebGatePermission``), then the native ``permissions_any_required`` rule for
``pas.add_paspersona``, evaluated with the same ``iam`` function. The POST runs
the native form and the same atomic service as ``PasTitularesImportView``.
"""

from django.core.exceptions import ValidationError
from django.utils.cache import patch_vary_headers
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.web_gate import WebGatePermission
from pas.forms import PasTitularesImportForm
from pas.services.titulares_import_service import importar_titulares_csv
from pas.views import _breadcrumb
from pas.web_api_informes import breadcrumb
from pas.web_api_views import native_rule

ADD = "pas.add_paspersona"


def _private(response):
    response["Cache-Control"] = "private, no-store"
    patch_vary_headers(response, ("Cookie",))
    return response


class PasTitularesImportWebView(APIView):
    """``GET``: the breadcrumb and the field of the native form; ``POST`` (multipart ``archivo``): the import."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [WebGatePermission, native_rule([ADD])]
    renderer_classes = [JSONRenderer]
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "head", "post"]

    def get(self, request):
        campo = PasTitularesImportForm()["archivo"]
        return _private(
            Response(
                {
                    "breadcrumb": breadcrumb(_breadcrumb("Importar titulares")),
                    "archivo": {
                        "label": campo.label,
                        "accept": campo.field.widget.attrs["accept"],
                    },
                }
            )
        )

    def post(self, request):
        form = PasTitularesImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                resultado = importar_titulares_csv(
                    form.cleaned_data["archivo"], usuario=request.user
                )
            except ValidationError as exc:
                form.add_error("archivo", exc)
            else:
                return _private(
                    Response(
                        {
                            "resultado": {
                                "total": resultado["total"],
                                "creados": resultado["creados"],
                                "duplicados": resultado["duplicados"],
                                "errores": list(resultado["errores"]),
                            }
                        }
                    )
                )
        errores = {campo: list(items) for campo, items in form.errors.items()}
        return _private(Response({"errors": errores}, status=400))
