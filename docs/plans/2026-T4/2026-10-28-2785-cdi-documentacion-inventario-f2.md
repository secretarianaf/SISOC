# CDI-F2: inventario de consumidores y contrato de descarga por objeto

E2: preparación estática, F2 aceptada pero no implementada ni técnicamente cerrada.
No archivos reales/metadataBD/servidor inspeccionados, sin transferencia o movimiento.

## Resultado: documentacion/ no es exclusivo CDI

| Dueño | Declaración y consumidor identificado |
|---|---|
| CDI | IntervencionCentroInfancia.documentacion, models_cdi_relaciones.py:47; detalle usa name/url |
| Comedores | Intervencion.documentacion, models/intervenciones.py:75–79; detalle usa name/url; API documentos devuelve url y path |

Prefijos organizaciones/documentacion/ y dispositivos/documentacion/ son distintos,
no se incluyen por coincidencia de palabra. Recorrido AST de Python no-migración
halló dos declaraciones literales exactas upload_to=documentacion/. No prueba todos
los uploads callable, asignaciones dinámicas o referencias históricas.

API Comedores devuelve id intervencion-<id>, origen/tipo/nombre/fecha/url/path:
es contrato consumidor además del HTML. No cambiarlo ni bloquear todo prefijo para
resolver CDI. Creación/reemplazo por Form/upload, eliminación física FieldFile.delete.
No se identificó export/email del campo en búsqueda focalizada, no ausencia absoluta.
Admin/generados pueden consumir FileField; #2789 permanece fuera de cambios.

## Contrato propuesto de descarga CDI, no endpoint implementado

Resolver intervención por PK y queryset/política existente del dueño. El servidor
obtiene FieldFile.name/storage del objeto autorizado, no path/basename de entrada.
Abrir bytes existentes, FileResponse y nombre controlado; private,no-store/nosniff.
Fuera de scope/softdelete/adjuntoausente/missingfile produce rechazo/404 según
política de objeto sin revelar otros archivos. Mantener botón/apariencia.

Patrón Inspecciones views_actas.py:31–41 muestra resolver service→FieldFile.open(rb)
→FileResponse/cabeceras; replicar patrón dentro CDI, no importar otro backend.
PAS confirma cierre directo + descarga porPK como dos capas; su namespace único
no justifica bloquear el compartido de CDI/Comedores.

Esta parte permite servir bytes sin mover/cambiar FK/copiar, pero **no cierra F2**
si /media/documentacion/<nombre> sigue operativo. No llamar protegido al conjunto
porque el enlace React pase por una vista.

## Preflight futuro de ownership y compatibilidad

Requiere autorización de entorno/operación antes de ejecutar; solo metadata mínima,
no contenido. Comparar claves storage de registros CDI/Comedores por dueño y manager
adecuado, incluidos softdeleted y referencias reemplazadas/históricas relevantes;
inventariar claves sin dueño/referencias compartidas. No guardar nombres sensibles
reales en docs/logs, usar conteos/agregados e IDs sintéticos para pruebas.

Un basename/PKgenérico no identifica dueño; IDs de ambos modelos pueden coincidir.
Mismo path puede estar referenciado por ambos por historia/manual, no se presume
exclusividad por naming actual de storage. No borrar huérfanos ni mover archivos
como parte del diagnóstico. Incluir enlaces/documentos emitidos si existen.

## Capa de cierre: opciones técnicas aún por contrastar

- Mantener ubicaciones + cierre selectivo por ownership: requiere clasificación
  autoritativa, consistencia uploads/reemplazo/baja, softdeleted/históricos,
  falloclasificador y pathcompartido. No interceptor existente identificado aún;
  denylist manual/estática insuficiente como garantía final.
- Aislar namespace/storage CDI: prefijo propio facilita cierre, pero cambiar
  upload_to no mueve históricos ni cierra enlaces viejos. Copias públicas por
  compatibilidad mantienen bypass. Cualquier traslado/copia/referencia o cambio
  APIComedores será alcance para decidir, no autorizado implícitamente por F2.

Mapa posterior de forwarding/media se detalla abajo: transporte disponible no
equivale a clasificador implementado. Falta preflight real antes de elegir transición. No extender seguridad de todo Comedores
ni declarar una solución elegida antes de evidencia. Mismo riesgo de ownership en
cualquiera de las capas: ambas deben probar que alias viejo no devuelve bytes CDI.

## Negativos y visuales futuros

Actorajeno/PKajeno/pathinyectado/softdeleted/archivoausente; alias antiguoCDI deniega;
Comedores URL/API conservan comportamiento aprobado; pathcompartido, histórico,
upload/reemplazo/borrado concurrentes, fallo clasificador/serving; caché/headers y
mismo botón. No prueba con archivos personales. Contrato, autorizaciónbytes y
capturas porURL/estado/rol/viewport se registran separadamente.

## Fuente y límites

src/backends/cdi/centrodeinfancia/models_cdi_relaciones.py:47;
src/backends/comedores/intervenciones/models/intervenciones.py:75–79;
src/backends/comedores/intervenciones/templates/intervencion_detail_view.html:36–43;
src/backends/comedores/comedores/api_views.py:592–613;
src/backends/comedores/intervenciones/forms.py:71–81; views.py:271–318;
src/backends/inspecciones/inspecciones/views_actas.py:31–41;
src/backends/pas/pas/views.py:443–464.
Ambos modelos/detalles y APIComedores contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
otros consumidores checkout. Padre contrastó proyección url/path Comedores.
CodeGraph sync, sin DB/media/app/tests/navegador/remoto o configuración aplicada.

- [CDI-F2 aceptada](../../registro/decisiones/2026-10-28-2785-cdi-documentacion-f2.md).
- [Fuente original](2026-10-28-2785-cdi-usuarios-reportes-documentacion.md).

## Serving/forwarding: requisito aprobado, estrategia no cerrada

Receta Nginx /media/documentacion→aliasfilesystem evita Django. Desarrollo conDEBUG
fuera de tests agrega static(MEDIA_URL,MEDIA_ROOT): descarga protegida no intercepta
ese fallback. Cualquier cierre debe cubrir ambas rutas y otras vías habilitadas,
no solo el botón React. No se verificó configuración desplegada.

Core reenvía prefijo a dueño único; CDI posee centrodeinfancia/simepi/ticketera,
Comedores intervencion/comedores/api. No registrar media/documentacion como exclusivo
CDI: sería reasignar archivos Comedores. Kernel no importa modelos de dueños ni usa
SQL cruzado por compartir DB. Descarga porPK bajo prefijoCDI usa proxy actual.

Transporte pedir_json_interno/registrohandler y reenviar_a_backend existe: timeout4s,
sinretry y503 ante fallo para JSON. Puede transportar respuestaarchivo, pero no
clasifica ownership. Endpoints internos del dueño serían contratos nuevos, no se
presentan como implementados; requieren identidad/permisos/tipos/error definidos.

Estados mínimos de clasificador para futura evaluación: CDI,Comedores,compartido,
desconocido,indisponible. Fallo no se interpreta como «noCDI» para servir público;
fallclosed puede afectar disponibilidad Comedores y debe evaluarse, no ocultarse.
Claves reemplazadas/harddeleted/huérfanas o fuera de prefijo no se resuelven por el
modelo vivo; preflight debe aclarar alcance de historia antes de prometer cobertura.

F2 permanece requisito aprobado no listo para activar. No elegir ahora entre mover
históricos y clasificación transversal sin metadata de huérfanos/compartidos y serving
real. Ambas estrategias pueden cambiar disponibilidad; cualquier autorización para
investigación remota/mutación requiere destino/operación/sesión explícitos después.
Esta incertidumbre técnica no bloquea definir otros circuitos ni autoriza un atajo.

Fuente checkout adicional: docs/operacion/nginx/sisoc-produccion.conf:55–81;
src/backends/config/urls.py:79; urls_dev.py:13–20; backends.json;
src/backends/kernel/core/backend_proxy.py:253–281;
src/backends/kernel/core/internal_services.py:24–59;
docs/desarrollo/verticales_independientes.md:45–60. Padre contrastó fallbackdev.
No se comparan estos archivos adicionales al snapshot congelado en esta continuación.
