"""Web API (G1 v1) de los listados y detalles de los catálogos de VAT (V07.01).

``/api/web/vat/catalogos/{sectores,subsectores,modalidades-cursado,titulos-referencia}/`` corre las vistas nativas
``{Sector,Subsector,ModalidadCursada,TituloReferencia}{List,Detail}View`` y proyecta su contexto. Acceso: la regla
de cada ruta nativa (``VAT.view_<modelo>``). Los textos salen del motor de plantillas, como en el HTML nativo.
"""

from django.urls import reverse
from rest_framework.response import Response

from VAT.views.catalogo import (
    ModalidadCursadaDetailView,
    ModalidadCursadaListView,
    SectorDetailView,
    SectorListView,
    SubsectorDetailView,
    SubsectorListView,
    TituloReferenciaDetailView,
    TituloReferenciaListView,
)
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_RESUMEN = '{{ v|truncatewords:10|default:"—" }}'
_SIN_DESCRIPCION = '{{ v|default:"Sin descripción" }}'


def _permisos(user, modelo):
    return {
        "editar": user.has_perm(f"VAT.change_{modelo}"),
        "eliminar": user.has_perm(f"VAT.delete_{modelo}"),
    }


def _urls_fila(prefijo, pk):
    return {
        "detail_url": reverse(f"vat_{prefijo}_detail", args=[pk]),
        "update_url": reverse(f"vat_{prefijo}_update", args=[pk]),
        "delete_url": reverse(f"vat_{prefijo}_delete", args=[pk]),
    }


class _CatalogoListView(VatNativeReadView):
    """``GET`` del listado de un catálogo: ``fila`` arma cada fila desde el objeto nativo."""

    modelo = ""
    prefijo = ""
    contexto = ""

    def fila(self, objeto):
        raise NotImplementedError

    def extra_contexto(self, context):  # pylint: disable=unused-argument
        return {}

    def get(self, request):
        def extra(context, _request):
            return {
                "results": [
                    {
                        "id": o.pk,
                        **self.fila(o),
                        **_urls_fila(self.prefijo, o.pk),
                    }
                    for o in context[self.contexto]
                ],
                "busqueda": request.GET.get("busqueda", ""),
                "permisos": _permisos(request.user, self.modelo),
                "urls": {
                    "list": reverse(f"vat_{self.prefijo}_list"),
                    "create": reverse(f"vat_{self.prefijo}_create"),
                },
                **self.extra_contexto(context),
            }

        return self.lista(extra)


class SectorListWebView(_CatalogoListView):
    """``GET .../catalogos/sectores/``: ``sector_list.html``."""

    native_class = SectorListView
    codigos = ["VAT.view_sector"]
    modelo, prefijo, contexto = "sector", "sector", "sectores"

    def fila(self, objeto):
        return {
            "nombre": objeto.nombre,
            "descripcion": texto(_RESUMEN, v=objeto.descripcion),
            "subsectores": objeto.subsectores.count(),
        }


class SubsectorListWebView(_CatalogoListView):
    """``GET .../catalogos/subsectores/``: ``subsector_list.html``."""

    native_class = SubsectorListView
    codigos = ["VAT.view_subsector"]
    modelo, prefijo, contexto = "subsector", "subsector", "subsectores"

    def fila(self, objeto):
        return {
            "sector": objeto.sector.nombre,
            "nombre": objeto.nombre,
            "descripcion": texto(_RESUMEN, v=objeto.descripcion),
        }


class ModalidadCursadaListWebView(_CatalogoListView):
    """``GET .../catalogos/modalidades-cursado/``: ``modalidadcursada_list.html`` (filtros combinables)."""

    native_class = ModalidadCursadaListView
    codigos = ["VAT.view_modalidadcursada"]
    modelo, prefijo, contexto = (
        "modalidadcursada",
        "modalidadcursada",
        "modalidades",
    )

    def fila(self, objeto):
        return {
            "nombre": objeto.nombre,
            "descripcion": texto(_RESUMEN, v=objeto.descripcion),
            "activo": objeto.activo,
        }

    def extra_contexto(self, context):
        return {
            "filters_config": context["filters_config"],
            "favorites": {
                "section": "",
                "url": reverse("filtros_favoritos"),
                "detail_url_template": reverse(
                    "detalle_filtro_favorito", kwargs={"pk": 0}
                ),
            },
        }


class TituloReferenciaListWebView(_CatalogoListView):
    """``GET .../catalogos/titulos-referencia/``: ``titulorreferencia_list.html``."""

    native_class = TituloReferenciaListView
    codigos = ["VAT.view_tituloreferencia"]
    modelo, prefijo, contexto = (
        "tituloreferencia",
        "titulorreferencia",
        "titulos",
    )

    def fila(self, objeto):
        return {
            "nombre": objeto.nombre,
            "plan_estudio": texto('{{ v|default:"—" }}', v=objeto.plan_estudio),
            "codigo": texto('{{ v|default:"—" }}', v=objeto.codigo_referencia),
            "activo": objeto.activo,
        }


class _CatalogoDetailView(VatNativeReadView):
    """``GET`` del detalle de un catálogo: ``proyectar`` devuelve los campos propios del template."""

    prefijo = ""

    def proyectar(self, objeto, context):
        raise NotImplementedError

    def get(self, request, pk):
        vista, context = self.detalle(pk)
        objeto = vista.object
        django_request = request._request  # pylint: disable=protected-access
        return Response(
            {
                "id": objeto.pk,
                "nombre": objeto.nombre,
                **self.proyectar(objeto, context),
                "urls": {
                    "vat": reverse("vat_centro_list"),
                    "list": reverse(f"vat_{self.prefijo}_list"),
                    "update": reverse(f"vat_{self.prefijo}_update", args=[objeto.pk]),
                    "delete": reverse(f"vat_{self.prefijo}_delete", args=[objeto.pk]),
                },
                "messages": mensajes_pendientes(django_request),
            }
        )


class SectorDetailWebView(_CatalogoDetailView):
    """``GET .../catalogos/sectores/<pk>/``: ``sector_detail.html``."""

    native_class = SectorDetailView
    codigos = ["VAT.view_sector"]
    prefijo = "sector"

    def proyectar(self, objeto, context):
        return {
            "descripcion": texto(_SIN_DESCRIPCION, v=objeto.descripcion),
            "subsectores": [s.nombre for s in context["subsectores"]],
        }


class SubsectorDetailWebView(_CatalogoDetailView):
    """``GET .../catalogos/subsectores/<pk>/``: ``subsector_detail.html``."""

    native_class = SubsectorDetailView
    codigos = ["VAT.view_subsector"]
    prefijo = "subsector"

    def proyectar(self, objeto, context):
        return {
            "descripcion": texto(_SIN_DESCRIPCION, v=objeto.descripcion),
            "sector": {
                "nombre": objeto.sector.nombre,
                "url": reverse("vat_sector_detail", args=[objeto.sector_id]),
            },
        }


class ModalidadCursadaDetailWebView(_CatalogoDetailView):
    """``GET .../catalogos/modalidades-cursado/<pk>/``: ``modalidadcursada_detail.html``."""

    native_class = ModalidadCursadaDetailView
    codigos = ["VAT.view_modalidadcursada"]
    prefijo = "modalidadcursada"

    def proyectar(self, objeto, context):
        return {
            "descripcion": texto(_SIN_DESCRIPCION, v=objeto.descripcion),
            "activo": objeto.activo,
        }


class TituloReferenciaDetailWebView(_CatalogoDetailView):
    """``GET .../catalogos/titulos-referencia/<pk>/``: ``titulorreferencia_detail.html``."""

    native_class = TituloReferenciaDetailView
    codigos = ["VAT.view_tituloreferencia"]
    prefijo = "titulorreferencia"

    def proyectar(self, objeto, context):
        return {
            "plan_estudio": texto('{{ v|default:"-" }}', v=objeto.plan_estudio),
            "codigo": texto('{{ v|default:"-" }}', v=objeto.codigo_referencia),
            "activo": objeto.activo,
            "planes": [
                texto(
                    "{{ p.sector.nombre }} {% if p.subsector %}/ {{ p.subsector.nombre }} {% endif %}"
                    "- {{ p.modalidad_cursada.nombre }}",
                    p=plan,
                )
                for plan in context["planes"]
            ],
        }
