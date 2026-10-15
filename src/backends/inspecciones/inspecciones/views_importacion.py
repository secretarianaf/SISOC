"""Importación masiva en tres pasos (archivo → revisión → resultado).

Sirve para escuelas y para asignaciones. El archivo queda en almacenamiento
privado con un token entre la revisión y la confirmación
(``services.subidas``) y se borra al confirmar o cancelar.
"""

import csv
import logging
import time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from core.services.csv_export import build_csv_response
from inspecciones.forms import ImportarArchivoForm
from inspecciones.services.importacion import (
    analizar_asignaciones,
    aplicar_asignaciones,
)
from inspecciones.services.importacion_escuelas import (
    MAX_OBSERVACIONES_PANTALLA,
    analizar_escuelas,
    aplicar_escuelas,
)
from inspecciones.services.subidas import (
    SubidaInexistente,
    borrar_subida,
    cargar_filas,
    cargar_subida,
    guardar_subida,
)
from inspecciones.views import PanelMixin

logger = logging.getLogger("django")

IMPORTACIONES = {
    "escuelas": {
        "titulo": "Importar escuelas",
        "pestana": "escuelas",
        "volver": "inspecciones_panel",
        "analizar": analizar_escuelas,
        "aplicar": lambda datos, user: aplicar_escuelas(datos),
        "ayuda": "inspecciones/partials/ayuda_importar_escuelas.html",
    },
    "asignaciones": {
        "titulo": "Importar asignaciones",
        "pestana": "asignaciones",
        "volver": "inspecciones_asignaciones",
        "analizar": analizar_asignaciones,
        "aplicar": lambda datos, user: aplicar_asignaciones(datos, actor=user),
        "ayuda": "inspecciones/partials/ayuda_importar_asignaciones.html",
    },
}


class _ImportacionMixin(PanelMixin):
    tipo = ""

    @property
    def config(self):
        return IMPORTACIONES[self.tipo]

    @property
    def titulo(self):
        return self.config["titulo"]

    @property
    def pestana(self):
        return self.config["pestana"]

    def url(self, accion):
        return f"inspecciones_importar_{self.tipo}{accion}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            tipo=self.tipo,
            config=self.config,
            url_subir=self.url(""),
            url_confirmar=self.url("_confirmar"),
            url_cancelar=self.url("_cancelar"),
            url_observaciones=self.url("_observaciones"),
        )
        return context

    def _subida(self):
        return cargar_subida(self.tipo, self.kwargs["token"], user=self.request.user)

    def _vencida(self):
        messages.warning(
            self.request,
            "La importación ya terminó o venció. Subí el archivo de nuevo.",
        )
        return redirect(self.config["volver"])


class SubirArchivoView(_ImportacionMixin, TemplateView):
    """Paso 1: el archivo. Si se puede leer, guarda y pasa a la revisión."""

    template_name = "inspecciones/importar_archivo.html"

    def get_context_data(self, **kwargs):
        kwargs.setdefault("form", ImportarArchivoForm())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        form = ImportarArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data["archivo"]
            inicio = time.monotonic()
            try:
                analisis = self.config["analizar"](archivo)
            except ValidationError as exc:
                form.add_error("archivo", exc)
            else:
                token = guardar_subida(
                    self.tipo,
                    archivo,
                    user=request.user,
                    analisis={
                        "resumen": analisis["resumen"],
                        "observaciones": analisis["observaciones"],
                    },
                    filas=analisis["datos"],
                )
                logger.info(
                    "inspecciones: revisión de %s (%s filas) en %.1f s",
                    self.tipo,
                    analisis["resumen"]["total"],
                    time.monotonic() - inicio,
                )
                return redirect(self.url("_revision"), token=token)
        return self.render_to_response(self.get_context_data(form=form))


class RevisionView(_ImportacionMixin, TemplateView):
    """Paso 2: qué se va a importar, antes de confirmar."""

    template_name = "inspecciones/importar_revision.html"
    subida = None

    def get(self, request, *args, **kwargs):
        try:
            self.subida = self._subida()
        except SubidaInexistente:
            return self._vencida()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        analisis = self.subida["analisis"]
        context.update(
            token=self.kwargs["token"],
            nombre_archivo=self.subida["nombre"],
            resumen=analisis["resumen"],
            observaciones=analisis["observaciones"][:MAX_OBSERVACIONES_PANTALLA],
            total_observaciones=len(analisis["observaciones"]),
            paso=2,
        )
        return context


class ConfirmarView(_ImportacionMixin, TemplateView):
    """Paso 3: guarda, borra el archivo y muestra el resultado."""

    template_name = "inspecciones/importar_resultado.html"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        token = self.kwargs["token"]
        try:
            subida = self._subida()
        except SubidaInexistente:
            return self._vencida()
        inicio = time.monotonic()
        datos = cargar_filas(self.tipo, token)
        resumen, observaciones = self.config["aplicar"](datos, request.user)
        borrar_subida(self.tipo, token)
        logger.info(
            "inspecciones: importación de %s (%s filas) en %.1f s",
            self.tipo,
            resumen["total"],
            time.monotonic() - inicio,
        )
        context = self.get_context_data(
            resumen=resumen,
            nombre_archivo=subida["nombre"],
            observaciones=observaciones[:MAX_OBSERVACIONES_PANTALLA],
            total_observaciones=len(observaciones),
            paso=3,
        )
        return self.render_to_response(context)


class CancelarView(_ImportacionMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            self._subida()
        except SubidaInexistente:
            return redirect(self.config["volver"])
        borrar_subida(self.tipo, self.kwargs["token"])
        messages.info(request, "Se canceló la importación. No se guardó nada.")
        return redirect(self.config["volver"])


class ObservacionesCSVView(_ImportacionMixin, View):
    """Las observaciones de la revisión (rechazos, a revisar y avisos) en CSV."""

    def get(self, request, *args, **kwargs):
        try:
            subida = self._subida()
        except SubidaInexistente:
            return self._vencida()
        respuesta = build_csv_response(f"observaciones-{self.tipo}.csv")
        respuesta["Cache-Control"] = "private, no-store"
        escritor = csv.writer(respuesta, delimiter=";")
        escritor.writerow(["Fila", "Cueanexo", "Nombre", "Tipo", "Motivo", "Detalle"])
        for obs in subida["analisis"]["observaciones"]:
            escritor.writerow(
                [
                    obs["fila"],
                    obs["cueanexo"],
                    obs["nombre"],
                    obs["tipo"],
                    obs["motivo"],
                    obs["detalle"],
                ]
            )
        return respuesta
