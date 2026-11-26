# CO01: historial React y productor mensual PWA conservado

Estado E2. CO01.03 Carga/corrección no autoriza inventar una pantalla web nueva:
la escritura está en API PWA; el backoffice inspeccionado tiene historial. Migrar
su presentación a React y probar regresión de productor existente, sin reescribir
PWA externa o mover PDF/DOCX al cliente. Nada ejecutado en esta preparación.

## Contratos token existentes

Montaje PWA: POST espacios/<comedor_id>/nomina/asistencia-alimentaria/;
GET asistencias-periodos y asistencias-periodo;
POST nomina/<pk>/registrar-asistencia y GET historial-asistencia.
TokenAuthentication+IsAuthenticated+IsPWAUserForComedor; escrituras además
IsPWAWriteAllowed+HasPwaNominaPermission. No reemplazar por cookies/ChangeNomina.
Objeto individual activo/no softdeleted del espacio, ausente404; histórico
individual no da acceso universal a todas las filas antiguas por ID.

## Registro individual: periodo actual, respuesta repetida

Sin payload de periodo/edición: primer día del mes local actual. Ventana día≥25
o≤10; no convertir automáticamente al mes anterior por interpretación del texto.
Get_or_create nómina/periodicidadmensual/periodo. Nuevo actor/mobile/auditoría;
repetido existente sin nueva fila.201/200 con created y registro:
id,periodicidad,periodo_referencia,periodo_label,fecha_toma_asistencia,tomado_por.
La vista no tiene el catch explícito del bulk; no errorJSON idéntico prometido
sin caracterizar manejo global. No controles de fecha que backend no expone.

## Bulk alimentario y cierre documental

Body nomina_ids lista requerida enteros≥1, permite []; periodoYYYY-MM oYYYY-MM-DD
normalizado al día1. Serializer deduplica manteniendo primer orden; service set.
No exige periodo=mesactual en ramas inspeccionadas, ventana depende de hoy.
Preservar y caracterizar, no limitar por nombre de función.

Atomic: ventana→rechazo si documento existente→poblaciónactiva elegible del espacio
(fueraAlimentar, perfilalimentarioTrue o sinperfil)→IDsajenos error→crea registros
faltantes elegidos→borra mensuales no seleccionados de población elegible/periodo
→audita→genera PDF. Error generación se transforma a ValidationError documento,
rollbackDB; no garantía de revertir bytes por transacción. No reintentar bulk a ciegas.

Resultado200 periodo_referencia/periodo_label/selected_nomina_ids/created_count/
deleted_count/nomina_destinatarios_documento. ValidationError400 detail dict/list.
Documento existente rechaza «Ya existe una nómina PDF generada para este período.»:
no edición indefinida o «corregir y regenerar» React añadida por nombre de slice.

## PDF: población distinta de selección y versión

Productor usa **nómina alimentaria activa al generar**, no selected_nomina_ids ni
solo asistentes históricos. Filtro alimentario según programa, exige sin documento
previo, version1/cantidad/metadataIDs. Sin regeneraciónv2 en productor; lookup último
porperiodo ordena versión/fecha/ID. Esa aparente diferencia no se arregla para que
PDF coincida con selección, se prueba contra fuente.

Documento serializer id,periodo_referencia,periodo_label,version,
cantidad_destinatarios,fecha_generacion,archivo_url,archivo_nombre. URL de FileField,
no downloadscoped nuevo; no extender CDI-F2 o afirmar protección por el historial.
PDF backend desde pwa/files/varios/NOMINA.DE.DESTINATARIOS.docx, LibreOfficeheadless,
perfil temporal/timeout120s. Espacio/domicilio/periodo/actor; rótulo «DNI» se rellena
con username, no DNIcertificado. No firma electrónica/consentimiento nuevo en payload;
no llamar firmado ni añadir aceptación obligatoria. Contenido fijo de plantilla y
constraints se inspeccionan aparte antes de cerrar esquema/bytes; no inventarlos.

## Historiales distintos y consumidores web

PWA GETperiodos tab defaultconsolidada→tab/results, documento solo alimentaria.
GETperiodo exige parseable,400inválido; resultado tab/resumenperiodo/documento/
asistentes. Individual orden periodo/fecha/ID descendentes. DTO exacto se precisa en suplemento inferior; sigue sin validación runtime o
aceptación del contrato nuevo por esa extracción.

Web usa mensuales, excluye softdeleted y relaciónadmisión/comedordirecto, selecciona
periodo y muestra asistentes+documento. No copiar bulk como escritura web nueva,
recortar historia a nóminaactual ni reemplazar denominadores históricos.
URL/estado histórico/selector/asistentes/enlace/retorno React son unidad M2; otras
APIs siguen sus permisos y productores, no dependencia de nuevo loginweb para PWA.

## Casos futuros

Días10/11/24/25; periodo noactual; individual nuevo/repetido201/200; token/scope/
writeblocked/filaajena-inactiva; bulk vacío/duplicados/IDsinválidos/borradonoseleccionado,
PDFfalloDBrollback/documentoyaexistente; poblaciónPDFvsselección, flagsprograma,
archivoausente, historia sin/con registros. Capturas web desktop/móvil/foco, PDF
renderizado por separado en fase autorizada, diffs acumulados, sintéticos. Ninguna
prueba, archivo o captura creado; no interoperabilidad/aceptación inferida de fuente.

## Evidencia

src/backends/comedores/pwa/api_urls.py:195–249;
api_views.py:738–781,1064–1185;
api_serializers.py:773–790,873–885;
services/nomina_service.py:204–224,999–1145;
services/nomina_destinatarios_pdf_service.py:236–265,307–416;
src/backends/comedores/comedores/views/nomina.py:150–195,274–297.
APIviews y ambosservicesPWA contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
serializers/rutascheckout; vistaweb comparadaantes. Padre contrastó bloqueo documento.
CodeGraphsync; sin render/documento/app/tests/DB/navegador o conexiones.

- [Alta y perfil PNUD](2026-10-28-2785-comedores-nomina-alta-ciudadano-pnud.md).
- [Estados y consulta](2026-10-28-2785-comedores-nomina-estados-derivacion.md).

## Suplemento de respuestas, unicidad y contenido fijo

Resumen: periodo_referencia,periodo_label(MM/YYYY),total_asistentes,
nomina_destinatarios_documento(objeto/null). Asistente: id deasistencia,nomina_id,
nombre,apellido,dni(stringvacío si falta),genero(sexo.sexo/vacío),
fecha_toma_asistencia,tomado_por(username/null). Se leen de Ciudadano actual, no
snapshot de identidad de ese periodo. Envoltorios tab/results o tab+resumen+asistentes;
registroindividual usa serializerreducido distinto, no ampliar por comodidad.

Constraints DB: uniq_pwa_asistencia_nomina_periodo(nomina,periodicidad,
periodo_referencia); no dedup de persona entre nóminas distintas. Documento
uniq_pwa_nomina_dest_doc_version(comedor,periodo_referencia,version), no unicidad
sinversión. Service bloquea cualquierdocumento previo/creav1, política más
restrictiva que esquema; columna versión no autoriza regeneración, IntegrityError
concurrente no éxitoidempotente supuesto. Upload pwa/nomina_destinatarios/.

Plantilla NOMINA.DE.DESTINATARIOS.docx leída como ZIP/XML sin extracción a disco,
render o generación. word/document.xml conserva ProgramaAlimentarComunidad,
reporte de gestión social/nómina, espacio/dirección/localidad/provincia/mes-año,
columnas orden/apellido/nombre/DNI/nacimiento/género y actorfinal. Párrafo48 (índice0
//w:p) dice «bajo carácter de DECLARACIÓN JURADA». word/header1.xml sintextoextraído.
No placeholders{{}}: productor reemplaza estructura de párrafo/tabla. No cambiar
leyenda o agregar checkbox por inferencia; no prueba firma, consentimiento API,
validezjurídica o layout final. Rótulo DNIactor sigueusername segúnproductor.

Casos adicionales: usuario/DNI/sexo ausentes, cambioCiudadano posterior visible en
historia; mismaclave/mes vsnóminadistinta, documentomismaversión frente distinta y
rechazoservice; PDFpreserva encabezado/tabla/leyenda. Todos futuros/sintéticos.
Fuenteadicional api_views.py:879–915; pwa/models.py:471–535. Modelocheckout, padre
contrastóconstraints; DOCXidéntico byteabyte al snapshot59a8f797688c9e762d5a4e9eaa187698ffade8aa.
Skilldocx cargada por explorador antes de inspección; XML no es prueba visual.
