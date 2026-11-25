"""Pantallas de la carga masiva de preinscriptos (issue #2939).

Todas las rutas exigen `centrodefamilia.view_centro` en `urls.py` (RN-01/RN-02).
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.views.generic import DetailView, ListView, View

from centrodefamilia.models import (
    CargaMasivaPreinscriptos,
    FilaCargaMasivaPreinscriptos,
)
from centrodefamilia.services.carga_masiva.columnas import (
    COLUMNAS,
    MAX_FILAS,
)
from centrodefamilia.services.carga_masiva.excel import (
    NOMBRE_PLANTILLA,
    generar_comprobante,
    generar_listado_errores,
    generar_plantilla,
)
from centrodefamilia.services.carga_masiva.lotes import (
    CargaNoDeshacible,
    CargaNoPendiente,
    VerificacionRenaperPendiente,
    confirmar_carga,
    crear_carga,
    deshacer_carga,
    editar_fila,
    eliminar_carga,
    DIAS_RETENCION_PENDIENTES,
    motivo_no_deshacer,
    purgar_lotes_pendientes_vencidos,
    quitar_fila,
    resumen_confirmacion,
    verificar_renaper,
)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FILTROS_ESTADO = {
    **dict(FilaCargaMasivaPreinscriptos.Estado.choices),
    "quitada": "Quitadas",
}
LOTE_CONFIRMADO = "El lote ya fue confirmado: no admite cambios."


class SubirArchivoForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo completado (.xlsx)",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )


def _respuesta_xlsx(contenido, nombre):
    respuesta = HttpResponse(contenido, content_type=XLSX_CONTENT_TYPE)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def _url_detalle(carga_id):
    return reverse("carga_masiva_detail", kwargs={"pk": carga_id})


class CargaMasivaListView(LoginRequiredMixin, ListView):
    """Historial de lotes y formulario de subida (RF-14)."""

    model = CargaMasivaPreinscriptos
    template_name = "carga_masiva/list.html"
    context_object_name = "cargas"
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        # Retención de datos de menores: sin depender de un cron del servidor,
        # cada vez que se abre el historial se eliminan los pendientes vencidos.
        purgar_lotes_pendientes_vencidos()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return CargaMasivaPreinscriptos.objects.select_related(
            "subido_por", "confirmado_por"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = SubirArchivoForm()
        context["max_filas"] = MAX_FILAS
        context["dias_retencion"] = DIAS_RETENCION_PENDIENTES
        return context


class CargaMasivaPlantillaView(LoginRequiredMixin, View):
    def get(self, request):
        return _respuesta_xlsx(generar_plantilla(), NOMBRE_PLANTILLA)


class CargaMasivaSubirView(LoginRequiredMixin, View):
    def post(self, request):
        form = SubirArchivoForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Seleccione un archivo .xlsx para subir.")
            return redirect("carga_masiva_list")
        try:
            carga = crear_carga(form.cleaned_data["archivo"], request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("carga_masiva_list")
        messages.success(
            request,
            f"Se subió el archivo con {carga.total_filas} filas. Revise la vista "
            "previa antes de confirmar.",
        )
        return redirect(_url_detalle(carga.pk))


class CargaMasivaDetailView(LoginRequiredMixin, DetailView):
    """Vista previa del lote con filtros y totales (RF-02, RF-03)."""

    model = CargaMasivaPreinscriptos
    template_name = "carga_masiva/detail.html"
    context_object_name = "carga"
    filas_por_pagina = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtro = self.request.GET.get("estado", "")
        filas = self.object.filas.all()
        if filtro == "quitada":
            filas = filas.filter(quitada=True)
        else:
            filas = filas.filter(quitada=False)
            if filtro in FilaCargaMasivaPreinscriptos.Estado.values:
                filas = filas.filter(estado=filtro)
            else:
                filtro = ""
        pagina = Paginator(filas, self.filas_por_pagina).get_page(
            self.request.GET.get("page")
        )
        context.update(
            {
                "page_obj": pagina,
                "filas": pagina.object_list,
                "filtro_estado": filtro,
                "filtros_estado": FILTROS_ESTADO,
                "total_quitadas": self.object.filas.filter(quitada=True).count(),
                "resumen": resumen_confirmacion(self.object),
                # Se cargan las filas sin error y se rechazan las demás.
                "puede_confirmar": self.object.esta_pendiente
                and not self.object.renaper_pendientes
                and self.object.total_validas + self.object.total_advertencias > 0,
                "motivo_no_confirmar": (
                    "Falta terminar la verificación con RENAPER"
                    if self.object.renaper_pendientes
                    else "No hay filas sin error para cargar"
                ),
                "motivo_no_deshacer": motivo_no_deshacer(self.object),
            }
        )
        return context


def _fila_de_carga(carga_id, fila_id):
    return get_object_or_404(
        FilaCargaMasivaPreinscriptos.objects.select_related("carga"),
        pk=fila_id,
        carga_id=carga_id,
    )


class CargaMasivaFilaEditarView(LoginRequiredMixin, DetailView):
    """Edición de las celdas de una fila (RF-04)."""

    template_name = "carga_masiva/fila_form.html"
    context_object_name = "fila"

    def get_object(self, queryset=None):
        return _fila_de_carga(self.kwargs["pk"], self.kwargs["fila_id"])

    def get(self, request, *args, **kwargs):
        fila = self.get_object()
        if not fila.carga.esta_pendiente:
            messages.error(request, LOTE_CONFIRMADO)
            return redirect(_url_detalle(fila.carga_id))
        if fila.quitada:
            messages.error(request, "La fila fue quitada del lote.")
            return redirect(_url_detalle(fila.carga_id))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        errores_por_columna = {}
        for mensaje in self.object.errores + self.object.advertencias:
            errores_por_columna.setdefault(mensaje["columna"], []).append(
                mensaje["mensaje"]
            )
        context["campos"] = [
            {
                "clave": columna.clave,
                "encabezado": columna.encabezado,
                "obligatoria": columna.obligatoria,
                "valor": self.object.datos.get(columna.clave, ""),
                "mensajes": errores_por_columna.get(columna.encabezado, []),
                "es_titular": columna.es_titular,
            }
            for columna in COLUMNAS
        ]
        return context

    def post(self, request, pk, fila_id):
        fila = _fila_de_carga(pk, fila_id)
        cambios = {
            columna.clave: request.POST[columna.clave]
            for columna in COLUMNAS
            if columna.clave in request.POST
        }
        try:
            cantidad = editar_fila(pk, fila.pk, cambios, request.user)
        except CargaNoPendiente:
            messages.error(request, LOTE_CONFIRMADO)
            return redirect(_url_detalle(pk))
        except FilaCargaMasivaPreinscriptos.DoesNotExist as exc:
            raise Http404 from exc
        if cantidad:
            messages.success(
                request, f"Fila {fila.numero_fila}: se guardaron {cantidad} cambios."
            )
        else:
            messages.info(request, f"Fila {fila.numero_fila}: no hubo cambios.")
        return redirect(_url_detalle(pk))


class CargaMasivaFilaQuitarView(LoginRequiredMixin, View):
    """Quita una fila del lote (RF-05)."""

    def post(self, request, pk, fila_id):
        fila = _fila_de_carga(pk, fila_id)
        try:
            quitar_fila(pk, fila.pk, request.user)
        except CargaNoPendiente:
            messages.error(request, LOTE_CONFIRMADO)
        except FilaCargaMasivaPreinscriptos.DoesNotExist as exc:
            raise Http404 from exc
        else:
            messages.success(request, f"Se quitó la fila {fila.numero_fila} del lote.")
        return redirect(_url_detalle(pk))


class CargaMasivaConfirmarView(LoginRequiredMixin, View):
    """Confirma el lote: todo o nada (RN-05 a RN-08, RF-10, RF-11)."""

    def post(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        try:
            confirmado = confirmar_carga(carga.pk, request.user)
        except CargaNoPendiente:
            messages.error(request, "El lote ya fue confirmado.")
            return redirect(_url_detalle(pk))
        except VerificacionRenaperPendiente:
            messages.error(
                request,
                "Todavía hay personas sin verificar contra RENAPER. Espere a que "
                "termine la verificación y vuelva a confirmar.",
            )
            return redirect(_url_detalle(pk))
        except DatabaseError:
            messages.error(
                request,
                "No se pudo confirmar el lote: otro usuario cargó datos de estas "
                "personas mientras tanto. No se cargó ninguna fila; vuelva a "
                "intentarlo para revalidar el lote.",
            )
            return redirect(_url_detalle(pk))
        if confirmado:
            carga.refresh_from_db()
            messages.success(
                request,
                "Lote confirmado: se cargaron "
                f"{carga.total_validas + carga.total_advertencias} filas y se "
                f"rechazaron {carga.total_errores}. Ya puede descargar el comprobante.",
            )
        else:
            messages.error(
                request,
                "No se confirmó el lote: después de revalidarlo no quedó ninguna "
                "fila sin error para cargar.",
            )
        return redirect(_url_detalle(pk))


class CargaMasivaRenaperView(LoginRequiredMixin, View):
    """Verifica contra RENAPER la próxima tanda de personas del lote (JSON)."""

    def post(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        try:
            avance = verificar_renaper(carga.pk)
        except CargaNoPendiente:
            return JsonResponse({"error": LOTE_CONFIRMADO}, status=409)
        return JsonResponse(avance)


class CargaMasivaDeshacerView(LoginRequiredMixin, View):
    """Deshace el último lote confirmado si nadie modificó sus preinscriptos."""

    def post(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        try:
            deshacer_carga(carga.pk, request.user)
        except CargaNoDeshacible as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                "Se deshizo el lote: SISOC quedó como antes de confirmarlo.",
            )
        return redirect(_url_detalle(pk))


class CargaMasivaEliminarView(LoginRequiredMixin, View):
    """Elimina un lote pendiente; los confirmados no se pueden eliminar."""

    def post(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        try:
            eliminar_carga(carga.pk, request.user)
        except CargaNoPendiente:
            messages.error(
                request,
                "No se puede eliminar un lote confirmado: sus preinscriptos ya "
                "fueron cargados.",
            )
            return redirect(_url_detalle(pk))
        messages.success(request, f"Se eliminó el lote «{carga.nombre_archivo}».")
        return redirect("carga_masiva_list")


class CargaMasivaErroresView(LoginRequiredMixin, View):
    """Descarga de filas con error y sus motivos (RF-07)."""

    def get(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        return _respuesta_xlsx(
            generar_listado_errores(carga), f"errores_carga_masiva_{carga.pk}.xlsx"
        )


class CargaMasivaComprobanteView(LoginRequiredMixin, View):
    """Comprobante del lote confirmado (RF-12)."""

    def get(self, request, pk):
        carga = get_object_or_404(
            CargaMasivaPreinscriptos,
            pk=pk,
            estado__in=[
                CargaMasivaPreinscriptos.Estado.CONFIRMADO,
                CargaMasivaPreinscriptos.Estado.DESHECHO,
            ],
        )
        return _respuesta_xlsx(
            generar_comprobante(carga), f"comprobante_carga_masiva_{carga.pk}.xlsx"
        )


class CargaMasivaArchivoView(LoginRequiredMixin, View):
    """Descarga del archivo original tal como se subió (RF-09, RNF-01)."""

    def get(self, request, pk):
        carga = get_object_or_404(CargaMasivaPreinscriptos, pk=pk)
        try:
            archivo = carga.archivo.open("rb")
        except FileNotFoundError as exc:
            raise Http404("El archivo original no está disponible.") from exc
        respuesta = FileResponse(
            archivo,
            as_attachment=True,
            filename=carga.nombre_archivo,
            content_type=XLSX_CONTENT_TYPE,
        )
        patch_cache_control(respuesta, private=True, no_store=True)
        return respuesta


class CargaMasivaEdicionesView(LoginRequiredMixin, DetailView):
    """Registro de ediciones y filas quitadas del lote (RF-08)."""

    model = CargaMasivaPreinscriptos
    template_name = "carga_masiva/ediciones.html"
    context_object_name = "carga"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ediciones"] = self.object.ediciones.select_related("fila", "usuario")
        return context
