# CDI06/CDI07: intervenciones, archivos y observaciones

E2: planificación fuente, sin código/entorno modificado. CDI06.01 consulta,
CDI06.02 gestión, CDI06.03 archivos; CDI07.01 consulta/CDI07.02 operaciones.
CDI-A2 aceptada para asistencia/derivaciónPOST; CDI-A3 elegida para las ocho
mutaciones adicionales enumeradas, sin implementación.

## Intervenciones CDI06

centrodeinfancia_intervencion_crear/editar/borrar requieren Add/Change/Delete
Intervención; _detalle ViewCentro, no ViewIntervención inventado. Login/scope;
editar/baja centro+intervención de ruta; detalle scope desde relación. Alta fija
centro/creado_por servidor. Lista fichaCentro10/página, creador histórico auditlog,
no usuario actual. Alta/edición/baja→centrodeinfancia_detalle según M2.

IntervencionCentroInfanciaForm: tipo_intervencion,subintervencion,destinatario,
fecha,forma_contacto,observaciones,tiene_documentacion,documentacion. Date widget
sobre DateTime: no cambiar zona/hora sin contraste. Observaciones/archivo opcionales;
checkbox no obliga archivo según clean. Tipos/subtipos desde configuración central.
Error subtipo ajeno «La subintervención seleccionada no corresponde al tipo de
intervención.»; con subtipos exige «Debe seleccionar una subintervención.»;
sin subtipos limpia opción. Alta fija/oculta Centro, servidor repone; si catálogo
falta «No existe el destinatario requerido: Centro.». Edición no pasa kwargs fijo/
oculto: destinatario general requerido. No armonizar incidentalmente.

Alta «Intervención creada correctamente.»; baja «Intervención dada de baja
correctamente.»; edición sin success explícito en clase, no inventar uno.

## Adjuntos: operación distinta de baja

_subir_archivo_intervencion soloPOST/ChangeIntervención; multipart documentacion,
scope. Dedicado valida presencia, extensión pdf/jpg/jpeg/png y≤5MB, no MIME real/
antivirus acreditados. ErroresJSON400 success:false/message; éxito asigna FileField,
flagTrue y {success:true,message:"Archivo subido correctamente."}.

_eliminar_archivo_intervencion soloPOST/DeleteIntervención: borra físico con
FileField.delete, pone None/flagFalse y retorna fichaCentro con «El archivo fue
eliminado correctamente.» o «No hay archivo para eliminar.». Baja de intervención
es softdelete distinto; reemplazo por asignación no prueba borrado del archivo
anterior ni rollback de storage con transacciónDB.

Modelo upload_to documentacion/; template usa FileField.url con download. No ruta
privada CDI específica identificada; no afirmar privado/público en producción sin
storage/serving efectivo. Preservar link operativo sin nueva exposición; no exportar
storage completo. Un proxy protegido sería cambio de seguridad/infra separado,
no deducción automática de JSX. Borrar botón visible solo superusuario aunque
endpoint usa DeleteIntervención: conservar diferencia UI/autorización actual.

## Observaciones CDI07

centrodeinfancia_observacion_crear/detalle/editar/eliminar: Add/ViewCentro/Change/
DeleteIntervención, no permisos Observacion nuevos. Form único observacion requerido,
textarea4rows, «Describa la observación». Centro/actor/fecha servidor, no DTO editable.

Alta actor nombre+apellido o username y timezone.now; safe_redirect con next host/
esquema seguro, fallback detalleObservación, no siempre fichaCentro. Editar conserva
centro→detalleObservación; borrar softdelete→fichaCentro «Observación dada de baja
correctamente.». Alta/edición sin success explícito, no uniformar mensajes. Lista
fichaCentro5/página observaciones_page y orden -fecha_visita, no nuevo listado.

## Decisión resuelta: CDI-A3 elegida, CDI-A2-only descartada

Estas ocho mutaciones carecen de veto auditor en ramas inspeccionadas:
crear/editar/borrar intervención; subir/eliminar archivo; crear/editar/borrar
observación. Auditoría+Centro de Infancia Total puede sumar Add/Change/Delete
Intervención, seguir es_auditor_simepi=True y tener scope auditor nacional.
IAM revisado agrega permisos sin veto. Caso estático condicional, no asignación
verificada en producción, explotación ni prueba de escritura.

| Alternativa | Alcance | Costo/riesgo |
|---|---|---|
| CDI-A3 — Ampliar plan de solo lectura a estas ocho operaciones (recomendación) | Coordinar legacy/API para rechazar mutaciones auditor con mismo predicado/excepciones, además de las dos ya aprobadas. Lecturas y otros actores conservan política | Amplía alcance/cambia acceso de roles mixtos; exige negativos sin cambio de registros/archivos e historia y positivos de excepciones |
| CDI-A2-only — Mantener solo las dos operaciones ya aprobadas | Asistencia/derivación se corrigen según CDI-A2; estas ocho conservan política fuente y riesgo separado | Menor alcance adicional, pero conserva inconsistencia de solo lectura en intervenciones/observaciones/archivos |

El responsable eligió «cdi-a3» el 2026-10-28. La ampliación es explícita, no
inferida de CDI-A2 cuyo alcance era dosPOST. Total: diez operaciones nombradas.
No quitar permisos de grupos, crear veto global o ampliar excepciones. CDI-A3 no
incluye corregir GET institucional que crea filas ni horarios u otros hallazgos;
permanecen documentados y pendientes de verificación antes de cualquier cambio.
Sin implementación y sin ampliar autoridad a publicar o modificar infraestructura.

## Casos pendientes

Tipo/subtipo/destinatario fijoalta-editableedición, fechas, objetosajenos/nestedID/
autor, invalidación y retorno; archivos falta/formato/5MB/reemplazo/borrar/sinarchivo,
UIendpoint diferente, descarga y accesoanónimo/rolajeno en entorno autorizado.
Observación desde ficha/nextinterno-externo, autor/fecha, editar/baja/lista5páginas.
Auditor puro/mixto/excepciones y negativos directos según elección; rechazos sin
mutación física/DB/historial cuando política deniega. Referencia/candidato/diff
porURL/estado/rol desktop/móvil/foco/avisos y acumulado. Todo sintético, no ejecutado.

## Evidencia

Prefijo src/backends/cdi/centrodeinfancia/: urls.py:272–339;
views.py:149–150,288–299,2201–2396; forms.py:2447–2580;
forms_observacion.py:6–19; models_cdi_relaciones.py:44–47;
templates/centrodeinfancia/intervencion_detail_view.html:46–63.
URLs/views/Forms/observación/modelorelaciones/template detalle contrastados por
explorador con59a8f797688c9e762d5a4e9eaa187698ffade8aa. Parent spot-check subida/
eliminación y kernel/users/bootstrap/groups_seed.py:142–167. Seed es checkout.
CodeGraph sync, sin app/tests/DB/navegador/remoto o aceptación visual.

- [CDI-A2 original](../../registro/decisiones/2026-10-28-2785-cdi-auditoria-a2.md).
- [FichaCentro y dependencias](2026-10-28-2785-cdi-centros-y-credenciales.md).
- [Institucional y trabajadores](2026-10-28-2785-cdi-formularios-trabajadores-m2.md).

Registro: [CDI-A3 aceptada](../../registro/decisiones/2026-10-28-2785-cdi-auditoria-a3.md).
