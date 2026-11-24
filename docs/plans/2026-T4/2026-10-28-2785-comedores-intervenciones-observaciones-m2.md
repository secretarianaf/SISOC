# CO02/CO06: intervenciones, documentos y observaciones

E2: contrato fuente/paridad, sin APIweb implementada, ejecución o prueba de seguridad.
CO-I2 solo imágenesComedor, CDI-F2 solo documentosCDI: no endurecimiento global
implícito de Intervenciones. Hallazgosresiduales no equivalen a seguridad certificada.

## CO02.01/02/03: permisos y objetos distintos de ficha

Catálogo consulta/alta-edición-baja/«adjuntos y descargas protegidas»: el título es
propuesta, no downloadprivado existente acreditado. Rutas login:
comedor_intervencion_ver GET ViewIntervencion;
comedor_intervencion_crear GET/POST AddIntervencion;
comedores_intervencion_editar GET/POST ChangeIntervencion;
comedor_intervencion_borrar confirmación/POST **comedores.delete_nomina**;
intervencion_detalle GET ViewIntervencion;
upload/eliminar documentacion POST ANYlecturaficha;
ajax_load_subestadosintervenciones GETlogin. No sustituir permiso atípico por nombre.

Lista obtiene comedor porget_comedor(pk) sinactor; filascomedor, filtrosfecha/tipo/
destinatario/admision_id; fechaválida rangodíalocal, inválidaignorada. AdmisiónGET
solo actualcomedor y enviado_acompaniamientoTrue; inválidaignorada. Sin paginación
explícita en vista. Alta comedorPKglobal; admisiónPOSTincorrecta errornofield; guarda
relaciones y safe_redirect nextPOST/GET, fallbacklista+admision_id si corresponde.

Edición intervenciónquerysetglobal, pk2comedor paraopciones/contexto/retorno sin
comprobación relación en vista. Baja interventglobalID, comedor_id deretorno;
previewcomún/bajalógica y «Intervención dada de baja correctamente.». No scopeficha
atribuido a estas rutas. No se reproducen casosni se agregan restricciones por API.
Las diferencias se caracterizan antes de declarar paridad, no solo ocultarbotones.

## Form, archivos y efectos

Campos tipo_intervencion,subintervencion,destinatario,fecha,forma_contacto,
observaciones,tiene_documentacion,documentacion. Requeridostipo/destinatario/fecha/
contacto; restoopcional. Tipo aliasesComedores+programa y selecciónhistórica;
subtipopertenece/tipoconsubtipos exige/sinlimpia. Fecha2000..2100 datewidget sobre
DateTime; no conversiónzona/hora por conveniencia. Checkbox no exigearchivo ni
Formlímite/extensión acreditados. SubtipoGETarray id/text, sinid→[].

FileField documentacion/ compartidoCDI; enlaceurl directo download. UploadglobalID
sinForm/full_clean, asignaflagTrue/archivo; JSON200successTrue/mensaje o sinarchivo
200successFalse «No se proporcionó un archivo.». EliminarFieldFile.delete/storage,
flagFalse y messages/redirectdetalleindividual. BotónsoloSuperuser, endpoint no
loexige sinoANYlectura: conservar diferenciaUI/endpoint y residual explícito.
No bloquearprefix, moverfiles o aplicarprotecciónCDI por título del catálogo.

No replicar archivo real en JSON, ni extender el servicio de imágenesCO-I2 a este
FileFielddistinto. Futuro uploadweb debe conservar contrato públicoPWA existente,
consumidoreslegacy de capacitaciones y dominiodueño; no refactor transversal tácito.

## CO06.01/02: observaciones sí scoped

observacion_crear AddObservacion, _detalle View, _editar Change, _eliminar Delete.
Alta centro scoped; resto comedor__in=scoped, no heredar IDs globalesCO02.
Formobservacion único requerido textarea, sin validacióncustom. Autor/fechaservidor.
Alta/edición actualizan observador first_name+espacio+last_name y fecha_visita now;
**editar cambia autorvisible/fecha**, no solo texto. Alta safe_redirect next/fallback
observacion_detalle; editar conserva comedor→detalle; baja softdelete+preview,
«Observación dada de baja correctamente.»→fichaComedor. Sinarchivo/email/integración.

Detalle produce id/fecha_visita/observacion/comedor__id/comedor__nombre/observador,
.get directo trasfiltro; no HTTP404uniforme supuesto sin prueba. Next externo
rechazado segúnhelper existente, no redirectabierto para mantener link.

## Casos propuestos y residuales

Lista/filtros/modalficha/alta dedicada/edición/detalle/archivos-confirmación; permisos
reales incluyendoDeleteNomina y ANYlecturaUpload, UIvsendpoint. Admisiónpropia-ajena-
noenviada; pk2comedor distinto/borra conretornootro como caracterizaciónfuente,
sin nueva política. Subtipohistórico/sinopciones/fechas/checkboxsinfile/uploadsinfile/
eliminarrepetido/next externo. Observaciónscope/autor-fechaeditada/retornoficha/baja.

Registrar positivos y negativos/residuales por acción; no decir aislado/privado si
no cumple. Si implementación desea corregirlos, obtener decisión específica antes.
No pregunta repetida por cadaquirk como requisito de seguir planificando. Sintéticos,
referencia-candidato-diff porURL/estado/rol desktop/móvil/foco y acumulado, sin pruebas.

## Fuente

src/backends/comedores/comedores/urls.py:155–159,197–243,311–344;
src/backends/comedores/intervenciones/views.py:65–85,103–318;
forms.py:42–135; models/intervenciones.py:39–80;
templates/intervencion_detail_view.html:36–41;
src/backends/comedores/comedores/views/observacion.py:19–123;
forms/observacion_form.py:6–20; models.py:1435–1436.
Vistas/Formintervenciones y vistaobservación contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; modelos/templatesauxiliarescheckout.
Padre contrastó upload sinForm/JSON200. CodeGraphsync, sin runtime/DB/storage/capturas.

- [Ficha y dependencias](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Imágenes CO-I2 distinta](2026-10-28-2785-comedores-imagenes-i1-i2.md).
- [Prefijo documental compartido](2026-10-28-2785-cdi-documentacion-inventario-f2.md).
