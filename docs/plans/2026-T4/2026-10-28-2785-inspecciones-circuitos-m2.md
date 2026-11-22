# Inspecciones: circuitos completos M2 y contratos de preparación

E2: fuente estática y propuestas, sin implementación, contratos API generados o
capturas aceptadas. Cinco familias/once entregas conservan sus IDs del catálogo.
J2 aplica a selectores; D1/CR1 CDF no se extienden a Inspecciones.

## Circuitos y activación

| Familia/entregas existentes | Circuito y dependencias |
|---|---|
| IN01.01/IN01.02 | Importar escuelas/asignaciones: archivo→revisión→confirmar/resultados o cancelar + CSV observaciones; no upload→éxito ficticio |
| IN02.01/IN02.02 | Consulta/jornada + alta modal/página + quitar + retorno con fecha; mensajes y filtros React juntos |
| IN03.01/IN03.02 | Tablero/polling/filtros + CSV y PDF/ZIP backend; métricas coherentes en todos consumidores |
| IN04.01/IN04.02/IN04.03 | Lista/ficha actas + anular/prueba + archivos privados; notificación requiere trazar productor, no inventar botón |
| IN05.01/IN05.02 | Escuelas: panel + crear/editar modal y página directa + otra/retorno/búsqueda |

Guard backoffice: sesión + puede_gestionar, anónimo login/autenticado no autorizado403.
No usar permiso inspector PWA como backoffice. Layout claro propio PanelMixin,
breadcrumb/iniciales, totales generales solo pestaña escuelas y query paginación.
No adoptar shell oscuro Insumos ni apariencia MUI genérica.

## Escuelas IN05

Panel25/página; EscuelaForm requeridos provincia/localidad/cueanexo9/nombre255/
domicilio255; opcionales cp20/telefono255/mail255. Cueanexo string sin espacios,
nueve dígitos preservando ceros; duplicado identifica escuela. Nombre/domicilio
compactan whitespace; CP mayúsculas/espacios y formato1754/B1754ABC; mail admite
varios separados por ; o ,. Localidad pertenece a provincia. Inicial edición
conserva opción actual, no selecciona primera de búsqueda remota.

Header XMLHttpRequest selecciona fragmento modal actual: inválido HTML400, éxito
{ok,mensaje,otra}. React requiere errores DTO y contexto modal/página, no inyectar
HTML. otra es presencia de clave, no conversión booleana genérica. Éxito normal
panel?q=cueanexo; otra→alta vacía. Mensajes «Se agregó la escuela …» / «Se guardaron
los cambios de …». Guardar cambios y retorno son parte de circuito M2.

## Asignaciones IN02

Rutas inspecciones_asignaciones, inspecciones_asignacion_nueva/quitar. Fecha,
inspector y escuela requeridos; fecha hoy o GETfecha; inspector del programa y
validación de servicio. J2 distingue opciones de filtro frente a asignación.

Misma escuela+inspector+fecha activa rechaza «Esa escuela ya está asignada a ese
inspector en esa jornada.»; soft-deleted se restaura. Otro inspector es visita
adicional permitida con aviso, no conflicto. Modal/página y otra conservan fecha;
normal→listado?fecha=, otra→nuevo Form misma fecha. Quitar soloPOST, rechaza si
existe acta según búsqueda fuente; soft-delete, retorno jornada. Totales jornada
ignoran filtros estado/estado_acta aunque filas sí filtren: no derivarlos de página.

## Importaciones IN01

Por escuelas/asignaciones: inspecciones_importar_<tipo>, _revision, _confirmar,
_cancelar, _observaciones. ImportarArchivoForm xlsx/csv, máximo25MB. Upload persiste
archivo/análisis/filas normalizadas privados y token propietario32hex. Revisión
primeras50 observaciones + cuenta completa; CSV completo privado/no-store.
Confirmar soloPOST reaplica contra estado actual, borra subida y muestra resultado;
cancelar soloPOST borra temporal/retorna lista. Ajeno/inaccesible/terminado devuelve
mensaje/retorno sin revelar existencia.

Vigencia «24h» es limpieza al subir otro archivo, cargar_subida no comprueba edad:
no prometer expiración precisa ni uso único concurrente. Asignaciones aplica filas
válidas aunque otras fallen; distingue repetidas/restauradas/rechazadas/otra visita,
no borra. Escuelas usa clasificación/upsert SQL; no imponer todo-o-nada por rutina.
Confirmación repetida/cambio concurrente requiere pruebas: token no acredita retry
seguro. No reintentar POST automáticamente por pérdida de respuesta.

## Tablero IN03 y actas IN04

Tablero/datos/CSV/descarga actas conservan filtros/métricas/alcance; polling5000ms.
Datos/CSV soloGET/no-store; descarga GET privado/no-store/nosniff. Una acta→PDF,
varias→ZIP; límites100actas/250MB. SinDescarga warning→tablero con filtros, no archivo
vacío ni ocultar error como descarga exitosa. No inferir totales desde filas cliente.

Actas lista25/página, ficha/PDF/imagenUUID/archivo-notificaciónUUID; service resuelve
archivo desde acta, no media público. Anular/prueba soloPOST+guard gestión;
next validado host/esquema, fallback detalle. Anular motivo mínimo MIN_MOTIVO,
atomic/lock, registra actor/fecha/estado/evento; repetida rechaza. Prueba solo1/0,
anulada rechaza, mismo valor no duplica evento. No borra PDF/imágenes/notificaciones/
historial ni reenvía correo al anular.

IN04.02 refiere constancia física de notificación: productor API token/PWA ya
rastreado en suplemento inferior; backoffice solo consulta archivos. No crear
botón de envío, email/push ni copiar mutaciones PWA como nuevas acciones web.
APIs token siguen contratos existentes, no sustituto automático de APIweb sesión.

## Casos visuales y de contrato propuestos

- Modal/página/otra, inválidos con iniciales, foco/teclado/cerrar/retornos/mensajes.
- Cueanexo ceros/duplicado, localidad ajena, mail múltiple, CP y J2 opciones.
- Alta/restauración/duplicado/otra visita/quitar con acta; totales frente a filtros.
- Import inválida/mixta, revisión50/CSVcompleto, cancelar, token ajeno/terminado,
  dobleconfirmación/cambio entre preview y aplicación. Sin efectos reales externos.
- Polling éxito/fallo/recuperación/unmount, filtros/CSV/ZIP y límites, mensajes.
- Acta válida/anulada/prueba, next externo, archivo ajeno/inexistente, denegación
  sin efectos. No entrega real email/push; fixtures sintéticas.

Por cada URL/estado/rol: referencia/candidato/diff desktop/móvil y acumulado del
conjunto integrado. Formularios/acciones/feedback/retornos completos antes de
activar; archivos/PDF permanecen backend autorizados. Ningún caso ejecutado.

## Fuente y brechas

Prefijo src/backends/inspecciones/inspecciones/:
urls.py:44–156; views.py:21–74; forms.py:27–157;
views_escuelas.py:21–151; views_asignaciones.py:83–172;
services/asignaciones.py:170–273; views_importacion.py:110–232;
services/subidas.py:25–81; services/importacion.py:1–11;
services/importacion_escuelas.py:394–465;
views_tablero.py:28–84; services/descarga_actas.py:19–20,94–114;
views_actas.py:31–127; views_anulacion.py:23–67; services/anulacion.py:27–90.

Exploración CodeGraph sincronizada; URLs/Forms/vistas asignaciones-importación-
actas-tablero-escuelas y services subidas/asignaciones/anulación contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa. Otros services checkout, sin atribuir ese SHA.
Padre contrastó EscuelaFormView parcial/otra/retorno. Payload tablero, clasificación import y productor notificación se precisan
en suplemento inferior; siguen sin contratos ejecutados ni once entregas listas.

- [Selectores J2](2026-10-27-2787-selectores-contratos-j2.md).
- [Catálogo existente](2026-10-27-2785-entregas-por-flujo.json).

## Suplemento: productores y payloads reconciliados

### Constancia física y consumidor PWA externo

POST /api/inspecciones/actas/<numero>/notificaciones/ es token/programa/rol,
no sesión backoffice. Carga uuid,notificada_at,receptor_nombre,receptor_cargo,
condicion_firma,motivo,observaciones,numero_confirmado,reemplaza_uuid,
motivo_correccion y archivos multipart repetidos. Service bloquea acta propia,
valida fotos reales entre1 y límite vigente, número coincidente, fecha/receptor,
condición firmada/negativa/sin_receptor y motivo para no firmada. Corrección exige
carga de esa acta y motivo; crea versión conservando anterior/archivos/hashes/evento.

UUID misma acta devuelve existente; otra acta conflicto. Replay existente se
resuelve antes de rechazo por anulación; nueva carga en anulada rechaza. Resultado
uuid/cargada_at/estado=cargada. No modifica respuestas/firma/PDF original ni envía
correo/push. Archivo de notificación exige scope propio/ve_todo. No crear mutador
backoffice que no existe por interpretar título «notificación» como envío.

PWA está en otro repositorio según docs/implementaciones/inspecciones_escolares.md
y ADR2026-10-14. Tecnología no verificada; no afirmar React ni pendiente de rewrite.
Conservar token/representación/offline como contrato de consumidor externo. Sin
inspección remota ni autorización para cambiar otro repositorio; no bloquear
contrato de paridad backoffice por suposiciones sobre su frontend.

### Tablero existente: sesión y cálculos backend

Filtros fecha/provincia/localidad/inspector/turno/notificacion. Fecha inválida→hoy;
IDs normalizados y valores turno/notificación inválidos→vacío. Actas base FINALIZADA
no prueba con fecha_visita y filtros para CSV/descarga. Borradores no aplican filtro
notificación inexistente todavía: no forzar igualdad artificial de indicadores.

JSON top-level: generado_at,filtros,indicadores,turnos,resultados,ausentismo,aulas,
presencia,mapa,ultimas,opciones. Indicadores: escuelas_unicas,actas_validas,
escuelas_con_mas_de_una_visita,inspectores,con_firma,sin_firma,
sin_firma_por_motivo,borradores_en_curso,notificacion_pendiente,notificacion_cargada.
inspectores tiene con_actividad/habilitados/sin_actividad.

Ausentismo/aulas: previsto,presente,computables,colegios,excluidas,
motivos_exclusion,porcentaje. Exclusión sin_constatacion/sin_dato/denominador_cero;
porcentaje null no es0. Presencia personal/estudiantes: categorias/denominador/total,
categorías si/no/no_constatado/sin_dato. Mapa puntos/con_gps/sin_coordenadas/manual/
sin_ubicacion, punto resumenacta+lat/lng/constatada. Ultimas máximo20 con resumen,
URL y estados; opciones.localidades desde actas filtradas. No recalcular negocio
en React ni exportar solo últimas20/puntos mapa.

Cache2s por combinación completa de filtros; pollingUI5s, generado_at puede
repetirse. CSV usa columnas estables/protección fórmulas. No afirmar cálculo nuevo
por request ni tratar sin dato como cero o éxito.

### Clasificación import y confirmación

Escuelas rechaza validación y Cueanexo duplicado de archivo. Nuevas/actualizadas/
sin_cambios; a_revisar transversal. Total disjunto nuevas_sin_observaciones +
actualizadas_sin_observaciones + sin_cambios + a_revisar + rechazadas. No sumar
nuevas+actualizadas+a_revisar. a_importar=nuevas+actualizadas incluye revisables;
resumen conserva columnas/renombrada/motivos/equivalencias.

Confirmación reclasifica BD actual y upsert nuevas/actualizadas transaccional,
restaura deleted_at/deleted_by al actualizar. Preview no garantiza mismo resumen
final. Asignaciones resumen total/fila_encabezado/columnas/nuevas/restauradas/
repetidas/otra_visita/rechazadas/a_importar; otra_visita aviso no excluyente.
Confirma reclasificando normalizadas, bulk_create1000 y restauración transaccional.
Temporal se elimina después de aplicar, fuera de transacción DB: no idempotencia
ni atomicidad DB+storage supuesta.

### Casos adicionales y fuente

Pruebas futuras: acta propia/ajena, replay UUID antes/después anulación, corrección,
fotos y PDF original sin cambio; null/0, doble visita/borrador, caché2s, exportmás20,
fórmulasCSV/GPS; revisables sin doble conteo, cambioBD entre preview/aplicación,
fallo al borrar temporal y dobleconfirmación. Solo propuestas sintéticas.

Prefijo src/backends/inspecciones/inspecciones/: api_urls.py:69–72;
api_views.py:62–64,175–188; api_permissions.py:6–16;
api_serializers.py:29–51; services/notificaciones.py:51–156;
services/tablero.py:130–175,333–398,448–640;
services/importacion_escuelas.py:271–365,394–472;
services/importacion.py:209–256; views_importacion.py:173–196.
Estos api_urls/views/serializers y services notificaciones/tablero/importacion/
importacion_escuelas contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
api_permissions y docs PWA son checkout. Padre contrastó validación de receptor/condición/corrección de notificación.
