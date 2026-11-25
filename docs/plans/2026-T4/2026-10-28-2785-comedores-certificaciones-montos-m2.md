# CO05: historial de certificaciones, documentos y montos

Estado E2: planificación basada en fuente, sin ejecución de PDF, aplicación, DB,
proveedores o capturas. IDs CO05.01 Prestaciones y certificaciones, CO05.02
Operaciones autorizadas y CO05.03 Documentos asociados. No agregar un formulario
web de conformidad porque exista una operación PWA con ese nombre.

## Historial y descarga web

certificaciones_prestaciones_historial y descargar_certificacion_prestaciones_web
usan ANY ViewComedor/ViewAdmision. Historial exige login y resuelve comedor con
scope; descarga obtiene conformidad por ID y comedor_id, pero no repite ese helper.
Conservar y documentar diferencia; no extender CDI-F2 ni afirmar aislamiento
completo por compartir el permiso de pantalla.

Historial20/página, orden -periodo,-creado. Filtros periodo YYYY-MM (inválido se
ignora), usuario solo dígitos y conforme=true|false. Generadores del propio comedor,
nombre con fallback username. Tabla periodo/generador/conforme/fecha/PDF; sin
archivo muestra «No disponible». No formulario de creación, retorno a ficha.

Descarga sin fichero404; FileResponse attachment application/pdf, nombre
certificacion-prestaciones-{pk}-{YYYY-MM}.pdf. No genera o muta al descargar.
GET es consumidor actual; función sin require_GET explícito, no prometer405 para
otros métodos sin caracterización. Mantener backend binario, no reconstruir PDF
ni leerlo como JSON para renderizar historial.

## Productor de conformidad: API PWA existente

ComedorDetailViewSet por token: GET prestacion-alimentaria, POST
prestacion-alimentaria/conformidad y GET conformidades/<id>/certificacion.
POST requiere IsPWAUserForComedor + HasPwaPrestacionesMensualesPermission +
IsPWAWriteAllowed y objeto del ViewSet. No sustituir por permisos de sesión web.

Payload conforme booleano real; observaciones strip requeridas si no conforme;
periodo YYYY-MM. Alimentar Comunidad exige dni_certificador de7–8dígitos. Fuente
convenio PNUD o informe; ausencia utiliza sentinel de prestaciones sin datos, no
cero inventado ni bloqueo nuevo de generación. Crea conformidad con actor/periodo/
fuente y PDF en transacción. Respuesta201, validación400 y generación fallida503:
«No se pudo generar la certificación PDF. Intente nuevamente.». Repetir puede crear
otra conformidad; no deduplicación mensual o idempotencia supuesta.

Serializer id,periodo,conforme,observaciones,creado,usuario_id,usuario_nombre,
informe_id,certificacion_pdf_url. URL apunta a descarga API, no media directo.
Storage comedores/certificaciones_prestaciones/, nombre con comedor/periodo/ID.
Atomicidad DB no demuestra reversión física de archivo si falla otra etapa.

Generador conserva plantillas PRESTACIONES.1/.2/.3/.54.docx según conformidad y
usuario principal, resueltas por app pwa. Conversión LibreOffice headless, perfil
temporal aislado y timeout120s, comprobación de salida/returncode. PDF/email quedan
backend según alcance aprobado; no cambiar aritmética, plantillas o dependencias.
No se inspeccionó todo rellenado de tablas/montos: reutilización no acredita
render correcto; comparación del documento requiere ejecución futura autorizada.

## ABM de montos por programa

montoprestacion_listar/crear/editar/eliminar/detalle bajo montoprestacion/. Login y
decorador con lista «Gestor prestaciones», «Prestacion»; mantener resolvedor real,
no crear códigos de permiso por intuición. Owner operativo Comedores, modelo/Form
compartidos kernel. No usar permiso de certificados para este ABM.

Form programa,desayuno_valor,almuerzo_valor,merienda_valor,cena_valor. Programa por
nombre, inputs step0.01. Precisión, requeridos y constraints requieren modelo
compartido antes de esquema final; no fijarlos desde apariencia del input.

Alta/edición transaccionales guardan historial con acción/cleaned_data; alta asigna
usuario_creador si falta; mensajes y retorno listado. Detalle programa/creador.
Baja usa DeleteView convencional, registra historial y elimina en transacción,
confirmación advierte irreversible. No aplicar automáticamente preview/softdelete
común. Revisar relaciones y constraints antes de afirmar efecto total de eliminación.
Sin archivos o correo en este ABM; no cambios de tarifas como parte de migración.

## Casos futuros y límites

- Historial vacío/con PDF/sin PDF, filtros inválidos, generador, páginas, badges,
  enlace y descarga; permisos y scope frente a ID/comedor de descarga, ausente404.
- Conformidad falsa sin observaciones, DNI requerido, fuente sin datos, periodo,
  error de conversión503 y repetición sin prometer idempotencia.
- Montos: permisos, decimales, inválidos, guardar/cancelar, detalle y eliminación
  irreversible con historial/relaciones según modelo.

Fixtures sintéticas, sin correo o PWA externa real. Cada URL/estado/rol requiere
referencia/candidato/diff desktop/móvil, foco/teclado, mensajes y retorno; documentos
backend con prueba render separada. Ningún caso ejecutado. Restricciones del modelo,
consumidores y formatos finales pendientes no convierten CO05 en tarea lista.

## Fuente

src/backends/comedores/comedores/urls.py:110–122;
views/comedor.py:95–166;
templates/comedor/certificaciones_prestaciones_historial.html:58–106;
api_views.py:1981–2158; api_serializers.py:1337–1369; models.py:1020–1049;
services/certificacion_prestaciones_service.py:192–250;
montos_urls.py:14–53; views/montos_prestacion.py:17–18,68–173;
src/backends/kernel/core/forms.py:40–68.
Servicio PDF y vistas montos contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
vista principal comparada antes; otros archivos checkout. Contraste puntual del
padre en descarga sin generación. CodeGraph sincronizado; sin ejecución o publicación.

- [Ficha y dependencias](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Revisión de capacitación, circuito distinto](2026-10-28-2785-comedores-dw-mes-capacitaciones.md).

## Modelo de montos: precisión y restricciones confirmadas

kernel/core/models.py:12–85: cuatro Decimal10,2 opcionales; programaFKPROTECT
requerido, creadorDO_NOTHING. Clean y CheckConstraint exigen≥1monto noNULL; cero
satisface y no mínimo nonegativo declarado. No UniqueConstraint porprograma,
no monto único inventado. Modelo convencional, baja delmonto física; PROTECT
protege programa referido, no demuestra que toda eliminaciónmonto sea bloqueada.
Evidencia checkout del explorador; no ejecución de constraints ni eliminación.
