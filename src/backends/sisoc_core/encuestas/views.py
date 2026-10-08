import csv
import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.services.csv_export import build_csv_response

from .forms import EncuestaForm, RechazoEncuestaForm
from .filters import FILTER_ENGINE, get_filters_config
from .models import (
    Encuesta,
    EstadoEncuesta,
    OperadorCondicion,
    RondaEncuesta,
    TipoPregunta,
    TipoSegmentacion,
)
from .services import (
    actualizar_encuesta,
    actualizar_segmentacion,
    agregar_destinatario,
    cerrar_ronda,
    crear_encuesta,
    descartar_ronda,
    exportar_encuesta,
    get_encuestas_queryset,
    importar_encuesta,
    posponer_ronda,
    publicar,
    solicitar_publicacion,
    rechazar_publicacion,
    quitar_destinatario,
    registrar_respuesta,
    reemplazar_preguntas,
    serializar_preguntas,
)
from .services_resultados import (
    build_resultados_csv_rows,
    build_resultados_excel,
    build_resultados_filename,
    get_puntajes_ronda,
    get_resultados_ronda,
)
from .validators import (
    LISTADO_TEMPLATE_FILENAME,
    TIPOS_PREGUNTA_CON_OPCIONES,
    TIPOS_PREGUNTA_PONDERABLES,
    generar_plantilla_listado,
)

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _mensaje_error(exc: ValidationError) -> str:
    if hasattr(exc, "messages"):
        return " ".join(exc.messages)
    return str(exc)


def _anotar_presentacion_resultado(resultado):
    """Agrega al ``ResultadoPregunta`` (encuestas/services_resultados.py) un
    par de atributos que solo hacen falta para pintar el dashboard de
    resultados (encuesta_resultados.html): a qué opción destacar como líder
    y en qué posición del 0-100% cae el promedio dentro del rango
    mínimo-máximo. Es presentación pura, por eso vive acá y no en el
    servicio, que no sabe nada de cómo se dibuja."""
    resultado.opcion_lider_texto = None
    if resultado.opciones and resultado.total_respuestas:
        lider = max(resultado.opciones, key=lambda opcion: opcion.cantidad)
        resultado.opcion_lider_texto = lider.texto

    resultado.posicion_promedio = None
    if resultado.promedio is not None:
        rango = resultado.maximo - resultado.minimo
        resultado.posicion_promedio = (
            round((resultado.promedio - resultado.minimo) / rango * 100, 1)
            if rango
            else 50
        )


def _redirect_next(request, fallback_url_name="inicio"):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return HttpResponseRedirect(reverse(fallback_url_name))


class EncuestaListView(LoginRequiredMixin, ListView):
    model = Encuesta
    template_name = "encuestas/encuesta_list.html"
    context_object_name = "encuestas"
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        # Conserva los enlaces anteriores y muestra sus filtros en el buscador.
        if "filters" not in request.GET:
            items = []
            if request.GET.get("busqueda", "").strip():
                items.append(
                    {
                        "field": "titulo",
                        "op": "contains",
                        "value": request.GET["busqueda"].strip(),
                    }
                )
            if request.GET.get("estado") in EstadoEncuesta.values:
                items.append(
                    {"field": "estado", "op": "eq", "value": request.GET["estado"]}
                )
            if items:
                params = request.GET.copy()
                params.pop("busqueda", None)
                params.pop("estado", None)
                params["filters"] = json.dumps({"logic": "AND", "items": items})
                return HttpResponseRedirect(
                    f"{reverse('encuestas_listar')}?{params.urlencode()}"
                )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = get_encuestas_queryset()
        return FILTER_ENGINE.filter_queryset(queryset, self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["puede_gestionar"] = self.request.user.has_perm(
            "encuestas.add_encuesta"
        )
        if context["puede_gestionar"]:
            context["leading_buttons"] = [
                {
                    "type": "button",
                    "id": "importar-encuesta-btn",
                    "label": "Importar",
                    "icon": "fas fa-file-import",
                    "class": "poncho-btn poncho-btn--cta",
                }
            ]
        context["puede_ver_resultados"] = self.request.user.has_perm(
            "encuestas.ver_resultados"
        )
        context["busqueda"] = (self.request.GET.get("busqueda") or "").strip()
        context["puede_aprobar"] = self.request.user.has_perm(
            "encuestas.aprobar_encuesta"
        )
        context["puede_editar"] = self.request.user.has_perm(
            "encuestas.change_encuesta"
        )
        context["pendientes_aprobacion"] = Encuesta.objects.filter(
            estado=EstadoEncuesta.PENDIENTE_APROBACION
        ).count()
        context["filters_config"] = get_filters_config()
        context["pendientes_url"] = (
            reverse("encuestas_listar")
            + "?"
            + urlencode(
                {
                    "filters": json.dumps(
                        {
                            "logic": "AND",
                            "items": [
                                {
                                    "field": "estado",
                                    "op": "eq",
                                    "value": EstadoEncuesta.PENDIENTE_APROBACION,
                                }
                            ],
                        }
                    )
                }
            )
        )
        return context


class EncuestaFormMixin:
    """Combina EncuestaForm (campos generales) con el editor dinámico de
    preguntas, que viaja en el campo oculto ``preguntas_json`` (ver
    encuestas/validators.py: parse_preguntas_payload)."""

    model = Encuesta
    form_class = EncuestaForm
    template_name = "encuestas/encuesta_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            try:
                preguntas_data = json.loads(
                    self.request.POST.get("preguntas_json", "[]")
                )
            except (TypeError, ValueError):
                preguntas_data = []
        elif getattr(self, "object", None) is not None:
            preguntas_data = serializar_preguntas(self.object)
        else:
            preguntas_data = []
        # json_script serializa y escapa el objeto de forma segura para el
        # <script type="application/json">; no pasarle un string ya volcado.
        context["preguntas_json_inicial"] = preguntas_data
        context["tipos_pregunta"] = TipoPregunta.choices
        context["operadores_condicion"] = OperadorCondicion.choices
        context["tipos_pregunta_con_opciones"] = ",".join(TIPOS_PREGUNTA_CON_OPCIONES)
        context["tipos_pregunta_ponderables"] = ",".join(TIPOS_PREGUNTA_PONDERABLES)
        return context

    def get_success_url(self):
        return reverse("encuestas_listar")

    def _guardar_encuesta_y_preguntas(self, form, guardar_encuesta):
        preguntas_raw = self.request.POST.get("preguntas_json", "[]")
        try:
            with transaction.atomic():
                encuesta = guardar_encuesta()
                reemplazar_preguntas(encuesta, preguntas_raw)
        except ValidationError as exc:
            form.add_error(None, _mensaje_error(exc))
            return None
        return encuesta


class EncuestaCreateView(LoginRequiredMixin, EncuestaFormMixin, CreateView):
    def form_valid(self, form):
        encuesta = self._guardar_encuesta_y_preguntas(
            form,
            lambda: crear_encuesta(usuario=self.request.user, **form.cleaned_data),
        )
        if encuesta is None:
            return self.form_invalid(form)
        self.object = encuesta
        messages.success(self.request, "Encuesta creada correctamente.")
        return HttpResponseRedirect(self.get_success_url())


class EncuestaUpdateView(LoginRequiredMixin, EncuestaFormMixin, UpdateView):
    def get(self, request, *args, **kwargs):
        encuesta = self.get_object()
        if encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION:
            return HttpResponseRedirect(
                reverse("encuestas_revision", args=[encuesta.pk])
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return get_encuestas_queryset()

    def form_valid(self, form):
        original = self.object
        encuesta = self._guardar_encuesta_y_preguntas(
            form,
            lambda: actualizar_encuesta(
                original, usuario=self.request.user, **form.cleaned_data
            ),
        )
        if encuesta is None:
            return self.form_invalid(form)
        self.object = encuesta
        messages.success(self.request, "Encuesta actualizada correctamente.")
        return HttpResponseRedirect(self.get_success_url())


class EncuestaExportarView(LoginRequiredMixin, View):
    def get(self, request, pk):
        encuesta = get_object_or_404(get_encuestas_queryset(), pk=pk)
        response = JsonResponse(
            exportar_encuesta(
                encuesta,
                incluir_segmentacion=request.GET.get("incluir_segmentacion") == "1",
            ),
            json_dumps_params={"ensure_ascii": False, "indent": 2},
        )
        response["Content-Disposition"] = (
            f'attachment; filename="encuesta-{encuesta.pk}.json"'
        )
        return response


class EncuestaImportarView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            encuesta = importar_encuesta(
                request.FILES.get("archivo"), usuario=request.user
            )
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
            return HttpResponseRedirect(reverse("encuestas_listar"))
        if hasattr(encuesta, "segmentacion"):
            mensaje = (
                "Encuesta importada en borrador con su segmentación. "
                "Revisá los destinatarios antes de publicarla."
            )
        else:
            mensaje = (
                "Encuesta importada en borrador sin segmentación. "
                "Configurá los destinatarios antes de publicarla."
            )
        messages.success(request, mensaje)
        return HttpResponseRedirect(reverse("encuestas_listar"))


class EncuestaPublicarView(LoginRequiredMixin, View):
    accion = staticmethod(solicitar_publicacion)
    mensaje = "Publicación solicitada. La encuesta está pendiente de aprobación."

    def post(self, request, pk):
        encuesta = get_object_or_404(get_encuestas_queryset(), pk=pk)
        try:
            self.accion(encuesta, usuario=request.user)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, self.mensaje)
        return HttpResponseRedirect(reverse("encuestas_listar"))


class EncuestaAprobarView(EncuestaPublicarView):
    accion = staticmethod(publicar)
    mensaje = "Encuesta aprobada y publicada correctamente."


class EncuestaRevisionView(LoginRequiredMixin, DetailView):
    model = Encuesta
    template_name = "encuestas/encuesta_revision.html"
    context_object_name = "encuesta"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["preguntas"] = (
            self.object.preguntas.select_related("pregunta_condicion")
            .prefetch_related("opciones")
            .order_by("orden")
        )
        context["segmentacion"] = getattr(self.object, "segmentacion", None)
        context.setdefault("rechazo_form", RechazoEncuestaForm())
        return context


class EncuestaRechazarView(EncuestaRevisionView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = RechazoEncuestaForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(
                self.get_context_data(rechazo_form=form, abrir_modal_rechazo=True),
                status=400,
            )
        try:
            rechazar_publicacion(
                self.object, usuario=request.user, motivo=form.cleaned_data["motivo"]
            )
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
            return HttpResponseRedirect(
                reverse("encuestas_revision", args=[self.object.pk])
            )
        messages.success(
            request,
            "Solicitud rechazada. El gestor podrá ver el motivo y corregir la encuesta.",
        )
        return HttpResponseRedirect(reverse("encuestas_listar"))


class RondaCerrarView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ronda = get_object_or_404(RondaEncuesta, pk=pk)
        try:
            cerrar_ronda(ronda, manual=True)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "Ronda cerrada correctamente.")
        return HttpResponseRedirect(reverse("encuestas_listar"))


class ResponderRondaView(LoginRequiredMixin, View):
    """Recibe el POST del modal de encuesta pendiente (ver
    src/backends/kernel/templates/includes/base.html + encuestas/partials/responder_modal.html).
    No requiere permisos de encuestas: cualquier usuario logueado segmentado
    puede responder."""

    def post(self, request, pk):
        ronda = get_object_or_404(RondaEncuesta, pk=pk)
        try:
            registrar_respuesta(ronda, request.user, request.POST)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "¡Gracias por responder la encuesta!")
        return _redirect_next(request)


class DescartarRondaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ronda = get_object_or_404(RondaEncuesta, pk=pk)
        try:
            descartar_ronda(ronda, request.user)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "No volveremos a mostrarte esta ronda.")
        return _redirect_next(request)


class PosponerRondaView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ronda = get_object_or_404(RondaEncuesta, pk=pk)
        try:
            posponer_ronda(ronda, request.user)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        return _redirect_next(request)


class EncuestaResultadosView(LoginRequiredMixin, DetailView):
    model = Encuesta
    template_name = "encuestas/encuesta_resultados.html"
    context_object_name = "encuesta"

    def get_queryset(self):
        return get_encuestas_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        encuesta = self.object
        rondas = list(encuesta.rondas.order_by("-numero_ronda"))

        ronda_pk = self.request.GET.get("ronda")
        ronda_actual = None
        if ronda_pk:
            ronda_actual = next(
                (ronda for ronda in rondas if str(ronda.pk) == ronda_pk), None
            )
        elif rondas:
            ronda_actual = rondas[0]

        resultados = get_resultados_ronda(ronda_actual) if ronda_actual else []
        for resultado in resultados:
            _anotar_presentacion_resultado(resultado)

        context["rondas"] = rondas
        context["ronda_actual"] = ronda_actual
        context["resultados"] = resultados
        context["puntajes"] = get_puntajes_ronda(ronda_actual) if ronda_actual else []
        return context


class EncuestaResultadosExportarView(LoginRequiredMixin, View):
    def get(self, request, pk, ronda_pk):
        ronda = get_object_or_404(
            RondaEncuesta.objects.select_related("encuesta"),
            pk=ronda_pk,
            encuesta_id=pk,
        )
        formato = request.GET.get("formato", "csv")

        if formato == "xlsx":
            contenido = build_resultados_excel(ronda)
            response = HttpResponse(contenido, content_type=EXCEL_CONTENT_TYPE)
            filename = build_resultados_filename(ronda.encuesta, ronda, "xlsx")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        if formato != "csv":
            raise Http404("Formato de exportación no soportado.")

        headers, filas = build_resultados_csv_rows(ronda)
        filename = build_resultados_filename(ronda.encuesta, ronda, "csv")
        response = build_csv_response(filename)
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(filas)
        return response


class EncuestaSegmentacionView(LoginRequiredMixin, DetailView):
    """Gestión de destinatarios; los pendientes solo permiten revisión."""

    def get(self, request, *args, **kwargs):
        encuesta = self.get_object()
        if encuesta.estado == EstadoEncuesta.PENDIENTE_APROBACION:
            return HttpResponseRedirect(
                reverse("encuestas_revision", args=[encuesta.pk])
            )
        return super().get(request, *args, **kwargs)

    model = Encuesta
    template_name = "encuestas/encuesta_segmentacion.html"
    context_object_name = "encuesta"

    def get_queryset(self):
        return get_encuestas_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        segmentacion = getattr(self.object, "segmentacion", None)
        context["segmentacion"] = segmentacion
        context["destinatarios"] = (
            segmentacion.destinatarios.order_by("tipo_documento", "numero_documento")
            if segmentacion
            else []
        )
        context["usuarios_destinatarios"] = (
            segmentacion.usuarios.order_by("pk") if segmentacion else []
        )
        context["grupos_disponibles"] = Group.objects.order_by("name")
        context["grupos_seleccionados"] = (
            set(segmentacion.grupos.values_list("pk", flat=True))
            if segmentacion
            else set()
        )
        return context


class SegmentacionPlantillaDownloadView(LoginRequiredMixin, View):
    """Descarga la plantilla Excel de documentos o IDs de usuarios."""

    def get(self, request, pk):
        get_object_or_404(get_encuestas_queryset(), pk=pk)
        tipo = request.GET.get("tipo", TipoSegmentacion.LISTADO_DOCUMENTOS)
        if tipo not in (
            TipoSegmentacion.LISTADO_DOCUMENTOS,
            TipoSegmentacion.LISTADO_USUARIOS,
        ):
            raise Http404
        por_usuario = tipo == TipoSegmentacion.LISTADO_USUARIOS
        response = HttpResponse(
            generar_plantilla_listado(por_usuario=por_usuario),
            content_type=EXCEL_CONTENT_TYPE,
        )
        filename = (
            "plantilla_encuestas_usuarios.xlsx"
            if por_usuario
            else LISTADO_TEMPLATE_FILENAME
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SegmentacionTipoUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        encuesta = get_object_or_404(get_encuestas_queryset(), pk=pk)
        try:
            actualizar_segmentacion(
                encuesta,
                tipo=request.POST.get("tipo", ""),
                archivo=request.FILES.get("archivo_listado"),
                grupos_ids=request.POST.getlist("grupos"),
            )
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "Segmentación actualizada correctamente.")
        return HttpResponseRedirect(reverse("encuestas_segmentacion", args=[pk]))


class SegmentacionAgregarDestinatarioView(LoginRequiredMixin, View):
    def post(self, request, pk):
        encuesta = get_object_or_404(get_encuestas_queryset(), pk=pk)
        try:
            agregar_destinatario(
                encuesta,
                tipo_documento=request.POST.get("tipo_documento", ""),
                numero_documento=request.POST.get("numero_documento", ""),
                usuario_id=request.POST.get("usuario_id"),
            )
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "Destinatario agregado correctamente.")
        return HttpResponseRedirect(reverse("encuestas_segmentacion", args=[pk]))


class SegmentacionQuitarDestinatarioView(LoginRequiredMixin, View):
    def post(self, request, pk, destinatario_pk):
        encuesta = get_object_or_404(get_encuestas_queryset(), pk=pk)
        try:
            quitar_destinatario(encuesta, destinatario_pk)
        except ValidationError as exc:
            messages.error(request, _mensaje_error(exc))
        else:
            messages.success(request, "Destinatario eliminado correctamente.")
        return HttpResponseRedirect(reverse("encuestas_segmentacion", args=[pk]))
