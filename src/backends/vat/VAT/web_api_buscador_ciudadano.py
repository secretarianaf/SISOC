"""Web API (G1 v1) del buscador por ciudadano de VAT (V03.02, U3).

``/api/web/vat/buscador-ciudadano/`` corre ``BuscadorCiudadanoView`` y proyecta su contexto
(``ciudadano.html``): el GET es el estado inicial y el POST ``{q, ciudadano_id}`` es la
búsqueda nativa (documento o CUIL/CUIT, candidatos, trayectoria con el alcance del usuario).
Las exportaciones CSV/XLSX siguen siendo el POST nativo de la página. Acceso:
``VAT.view_inscripcion`` o ``VAT.view_centro`` (la regla de la ruta nativa).
"""

from django.urls import NoReverseMatch, reverse
from rest_framework.response import Response

from VAT.views.buscador_ciudadano import BuscadorCiudadanoView
from VAT.web_api_common import VatNativeReadView, mensajes_pendientes, texto

_FECHA = "{{ v|date:'d/m/Y' }}"
_DEFECTO = "{{ v|default:'—' }}"
_VALOR = "{{ v }}"
_PORCENTAJE = "{% widthratio p t 100 %}%"
_INICIALES = "{{ n|slice:':1' }}{{ a|slice:':1' }}"


def _ciudadano(c):
    return {
        "id": c.pk,
        "iniciales": texto(_INICIALES, n=c.nombre, a=c.apellido),
        "apellido": c.apellido,
        "nombre": c.nombre,
        "tipo_documento": c.get_tipo_documento_display(),
        "documento": texto(_DEFECTO, v=c.documento),
        "cuil_cuit": texto(_DEFECTO, v=c.cuil_cuit),
        "email": texto(_DEFECTO, v=c.email),
        "telefono": texto(_DEFECTO, v=c.telefono),
    }


def _comision_url(user, i):
    if i.comision_curso_id and user.has_perm("VAT.view_comisioncurso"):
        return reverse("vat_comision_curso_detail", args=[i.comision_curso_id])
    if i.comision_id and user.has_perm("VAT.view_comision"):
        return reverse("vat_comision_detail", args=[i.comision_id])
    return None


def _inscripcion(user, i):
    total = i.presentes_ref + i.ausentes_ref
    return {
        "fecha": texto(_FECHA, v=i.fecha_inscripcion),
        "unidad": texto(_VALOR, v=i.unidad_formativa_nombre),
        "estado_curso": texto(_DEFECTO, v=i.estado_curso_ref),
        "comision_codigo": texto(_VALOR, v=i.comision_codigo_ref),
        "comision_nombre": texto(_VALOR, v=i.comision_nombre_ref),
        "comision_url": _comision_url(user, i),
        "periodo_inicio": (
            texto(_FECHA, v=i.periodo_inicio_ref) if i.periodo_inicio_ref else ""
        ),
        "periodo_fin": texto(_FECHA, v=i.periodo_fin_ref),
        "centro": texto(_VALOR, v=i.centro_nombre_ref),
        "cue": texto(_VALOR, v=i.cue_ref) if i.cue_ref else "",
        "provincia": texto(_VALOR, v=i.provincia_nombre_ref),
        "localidad": texto(_VALOR, v=i.localidad_ref),
        "direccion": texto(_VALOR, v=i.direccion_ref) if i.direccion_ref else "",
        "estado": i.estado,
        "estado_label": i.get_estado_display(),
        "estado_comision": texto(_DEFECTO, v=i.estado_comision_ref),
        "resultado": i.resultado_final or "",
        "asistencia_pct": (
            texto(_PORCENTAJE, p=i.presentes_ref, t=total) if total else ""
        ),
        "presentes": i.presentes_ref,
        "total_sesiones": total,
        "origen": i.get_origen_canal_display(),
    }


class BuscadorCiudadanoWebView(VatNativeReadView):
    """``GET|POST .../buscador-ciudadano/``: contexto de ``BuscadorCiudadanoView``."""

    http_method_names = ["get", "head", "post"]
    native_class = BuscadorCiudadanoView
    codigos = ["VAT.view_inscripcion", "VAT.view_centro"]

    def proyectar(self, request, q, ciudadano_id=""):
        vista = self.native()
        vista.request.POST = vista.request.POST.copy()
        vista.request.POST["ciudadano_id"] = ciudadano_id
        context = vista._build_context(  # pylint: disable=protected-access
            vista.request, q
        )
        user = request.user
        ciudadano = context["ciudadano"]
        legajo = None
        if ciudadano and user.has_perm("ciudadanos.view_ciudadano"):
            try:
                legajo = reverse("ciudadanos_ver", args=[ciudadano.pk])
            except NoReverseMatch:
                legajo = None
        return Response(
            {
                "q": context["q"],
                "estado": context["estado"],
                "scope_is_national": context["scope_is_national"],
                "candidatos": [
                    {
                        "ciudadano": _ciudadano(item["ciudadano"]),
                        "total_inscripciones": item["total_inscripciones"],
                    }
                    for item in context["candidatos"]
                ],
                "ciudadano": _ciudadano(ciudadano) if ciudadano else None,
                "legajo_url": legajo,
                "resumen": (
                    {k: texto(_VALOR, v=v) for k, v in context["resumen"].items()}
                    if context["resumen"]
                    else None
                ),
                "inscripciones": [
                    _inscripcion(user, i) for i in context["inscripciones"]
                ],
                "urls": {"buscador": reverse("vat_buscador_ciudadano")},
                "messages": mensajes_pendientes(
                    request._request  # pylint: disable=protected-access
                ),
            }
        )

    def get(self, request):
        return self.proyectar(request, "")

    def post(self, request):
        return self.proyectar(
            request,
            (request.POST.get("q") or "").strip(),
            request.POST.get("ciudadano_id") or "",
        )
