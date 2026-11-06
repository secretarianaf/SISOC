# Encuestas: rondas, privacidad y resultados

## Alcance

`encuestas` permite crear encuestas periódicas para usuarios autenticados de
SISOC. Una encuesta se publica en rondas; cada ronda abre y cierra en fechas
propias y conserva el resultado histórico de esa versión.

El módulo admite preguntas de texto, opciones, escala, Sí/No, número y fecha.
Las preguntas pueden ser obligatorias, depender de una respuesta anterior y,
cuando tienen un conjunto cerrado de respuestas, participar de un puntaje
ponderado. El puntaje se calcula al consultar resultados; no se persiste como
un dato independiente.

## Ciclo y segmentación

- Las encuestas pueden ser únicas o recurrentes. El worker ejecuta
  `process_encuestas_rondas` para abrir y cerrar rondas por fecha.
- La segmentación puede ser todos los usuarios, un listado de documentos, de IDs de usuarios o grupos. Los
  cambios de destinatarios se aplican a la ronda abierta.
- Editar una encuesta con respuestas crea una nueva versión; no se permite
  editarla mientras tenga una ronda abierta.
- Modalidades de respuesta:
  - **Obligatoria:** bloquea la navegación hasta responder.
  - **Postergable:** permite responder más tarde y exige un intervalo de
    recordatorio mayor a cero.
  - **Opcional:** permite elegir «Prefiero no responder». El descarte aplica
    al usuario y a la ronda actual; no cuenta como respuesta ni cumplimiento.
    Una ronda recurrente posterior vuelve a ofrecerse.
- El selector del editor deriva `es_obligatoria` y `es_opcional`. El intervalo
  de recordatorio se muestra y conserva solo para postergables. Ambas banderas
  no pueden estar activas a la vez. Las solicitudes anteriores sin selector
  siguen admitiendo las banderas originales.
- El descarte se guarda en `RecordatorioUsuario.descartada`. Se comprueba que
  la ronda esté abierta y vigente, el usuario sea destinatario y no haya
  respondido. El cierre visual del modal no equivale a descartar la ronda.

La segmentación por IDs admite carga manual y archivos Excel/CSV UTF-8 de hasta
5 MB, con columna `usuario_id` y un ID por fila. **Descargar plantilla** se adapta
al tipo seleccionado. Los IDs deben existir en SISOC; se deduplican y los errores
rechazan el archivo completo sin reemplazar los destinatarios previos. El listado
muestra ID, usuario y nombre para revisar la selección. Cambiar de tipo elimina
los destinatarios del tipo anterior. Los usuarios no necesitan DNI para recibir
una encuesta segmentada por ID.

**Grupos de usuarios** permite buscar y seleccionar varios grupos existentes de
SISOC. Se requiere al menos uno. Basta pertenecer a cualquiera de los elegidos,
sin duplicar la encuesta por pertenecer a más de uno. La pertenencia se evalúa
al acceder y responder: las altas y bajas en los grupos aplican a rondas abiertas.
La revisión del aprobador muestra los nombres seleccionados. Elegir este tipo
reemplaza los listados individuales y cambiar a otro tipo limpia los grupos.

## Exportación e importación de configuración

- Desde edición, **Exportar JSON** ofrece **Solo encuesta** o **Con segmentación**.
  Descarga los datos guardados; los cambios sin guardar no se incluyen.
- El archivo usa `formato: "sisoc.encuesta"` y `version_formato: 3` (4 al incluir segmentación por IDs, 5 por grupos). Incluye
  título, descripción, anonimato, modalidad, recurrencia, plazos y preguntas
  con opciones, puntajes y condiciones referenciadas por orden.
- La segmentación es optativa: tipo «todos los usuarios», documentos o IDs de los
  destinatarios. Los IDs se exportan como `destinatarios: [{"usuario_id": 123}]`;
  se valida su existencia al importar. Pueden identificar a personas distintas
  entre ambientes: para trasladar encuestas entre ambientes, preferir documentos
  o exportar sin segmentación y configurarla en destino. No se incluyen archivos
  de origen, cuentas completas, respuestas, rondas ni historial de versiones.
- Los grupos se exportan por nombre como `destinatarios: [{"grupo": "Gestor de Encuestas"}]`.
  Deben existir con el mismo nombre en destino; si falta alguno se rechaza toda
  la importación. No se crean grupos ni se modifican permisos o pertenencias.
- Desde el listado, **Importar** abre el selector y envía el archivo al elegirlo,
  mostrando un spinner. Admite `.json` UTF-8 (con o sin BOM), hasta 5 MB.
- La importación siempre crea una encuesta nueva en borrador, versión 1 y
  atribuida al usuario importador. No sobrescribe encuestas existentes.
  Si el archivo incluye segmentación, la restaura; si no, queda pendiente.
  Después vuelve al listado y muestra el mensaje correspondiente. El flujo
  continúa con revisión/configuración de segmentación y publicación manual.
- Se admiten versiones 1 y 2 del JSON; sin `es_opcional`, se conserva el
  comportamiento anterior (obligatoria o postergable). Los consumidores
  antiguos deben actualizarse para importar el formato 3.
- Formato, tipos, reglas de preguntas y documentos se validan en el servidor.
  Los errores revierten la operación completa y se muestran en un toast rojo.

## Presentación

El listado usa el mismo buscador combinable de Usuarios (`search_bar.html` y
`advanced_filters.js`): título, estado, anónima y recurrente. El contrato `filters`
se valida con `AdvancedFilterEngine` y un mapa cerrado en `src/backends/sisoc_core/encuestas/filters.py`.
Los enlaces anteriores con `busqueda` y `estado` se redirigen a filtros visibles;
la paginación conserva los filtros. Resetear vuelve al listado completo.
La bandeja del aprobador ofrece un acceso a pendientes usando ese mismo filtro.

La revisión sigue las tarjetas y botones de Editar usuario: datos de la encuesta,
destinatarios desplegables y preguntas con sus opciones. Un panel lateral reúne
solicitante, fecha y consecuencias de aprobar o rechazar; en móvil aparece debajo
del contenido. Se mantiene la autorización y el envío POST con CSRF.

El botón «Agregar pregunta» permanece al pie del listado, a la derecha.
El editor permite reordenar preguntas desde el ícono de arrastre junto al
número. Al arrastrar se ve la tarjeta completa, se atenúa su lugar de origen
y se marca el destino. El mismo ícono admite las flechas del teclado al
enfocarlo. Para intercalar una pregunta se usa «Agregar pregunta» y luego
se arrastra a la posición deseada. El botón «Quitar» es rojo y compacto;
pide confirmación en un modal con «Cancelar» y «Quitar pregunta» antes de
retirar una pregunta. Cancelar o cerrar el modal conserva todo su
contenido. Si hay preguntas dependientes, advierte que quedarán siempre
visibles al quitar la referencia. La eliminación se persiste al guardar.
Al reordenar se mueve únicamente la tarjeta elegida y se conserva la
posición de scroll. Las tarjetas se acomodan con una animación breve,
desactivada si el usuario tiene preferencia por movimiento reducido.
El mensaje de posición y recordatorio de guardar aparece en un toast de
3 segundos abajo a la derecha, sin ocupar espacio entre las preguntas.
Durante el arrastre, acercarse a los 100 px superiores o inferiores de la
pantalla activa desplazamiento automático continuo, más rápido cuanto más
cerca está el puntero del borde. Se detiene al alejarse, soltar, cancelar
o salir de la ventana, permitiendo mover varias posiciones sin soltar.
El orden se conserva al guardar y reabrir. Las opciones, puntajes,
obligatoriedad y condiciones permanecen ligados a la misma pregunta.
Una pregunta condicional debe seguir después de su referencia: el editor
rechaza un movimiento que invierta esa dependencia y muestra el motivo.
Crear/editar, segmentación y el modal de respuesta comparten tokens y botones
Poncho. El modal agrupa preguntas, resalta opciones seleccionadas e informa la
modalidad y el anonimato. Conserva preguntas condicionales y dispone de scroll
interno y adaptación a pantallas pequeñas.

## Publicación en la PWA de Espacios Comunitarios

- Segmentación ofrece **Disponible en la PWA de Espacios Comunitarios**,
  desactivada por defecto. No sustituye la segmentación ni la aprobación:
  solo se ofrecen rondas abiertas y vigentes de encuestas publicadas,
  habilitadas para PWA, a usuarios destinatarios con acceso móvil activo.
- La opción se guarda con el botón «Guardar» de Segmentación, junto con el
  tipo y los destinatarios; no aparece en Crear/editar. Se puede cambiar con
  una ronda abierta, igual que la segmentación, pero no durante la aprobación.
  Un error de segmentación revierte también el cambio de disponibilidad. Los
  formularios anteriores que no envían ese control conservan su valor.
- La pantalla de revisión informa si la encuesta se habilitará en la PWA.
  Nuevas versiones conservan la opción, pero nacen en borrador. Importar JSON
  no activa automáticamente este canal; requiere habilitarlo en destino.
- Cada pregunta puede definir un **Bloque** opcional (hasta 120 caracteres)
  y, para texto, un **Máximo de caracteres** de 1 a 10000. Están en el
  desplegable «Presentación en la PWA». Se conservan al reordenar, clonar y
  exportar/importar preguntas; sin valores se mantiene el comportamiento previo.
- `GET /api/encuestas/pwa/` devuelve configuración y estado de cumplimiento
  por ronda. `POST /api/encuestas/pwa/<ronda_id>/responder/` recibe
  `response_id` (UUID) y `respuestas`, un objeto por ID de pregunta. En opción
  múltiple, los valores son listas; en los otros tipos son valores simples.
  No se acepta la identidad del respondiente desde el cuerpo: sale del token.
- Ambas rutas usan Token DRF y comprueban el acceso mediante el contrato
  existente `/interno/espacios/contexto/`, a través de
  `core.internal_services.pedir_json_interno`. Sin acceso: 403; si no puede
  confirmarse el contexto del dueño: 503. No se importan modelos de `pwa`
  desde Encuestas. La API pertenece al core, fuera del prefijo remoto `/api/pwa/`.
- Guardar reutiliza `registrar_respuesta`: validación de tipos, opciones,
  obligatoriedad y condiciones, rollback de parciales y separación entre
  respuesta anónima y cumplimiento. Una pregunta cuya referencia está oculta
  también queda oculta, incluso si usa «distinto de».
- La clave de idempotencia de negocio es **usuario y ronda**. Se bloquea la
  ronda durante el envío y un reintento ya cumplido devuelve 200 sin crear
  otra respuesta. El UUID del cliente identifica la cola móvil; no se guarda
  un enlace adicional entre identidad y contenido anónimo. Se conserva la
  recurrencia existente: una nueva ronda puede volver a responderse.
- El frontend vive en el repositorio satélite **Espacios-Comunitarios**.
  Muestra invitación en el Hub de Espacios y acceso en Ajustes → Tu opinión;
  una pregunta por pantalla, progreso por bloques, avance a los 350 ms para
  opciones simples, navegación anterior y todos los tipos de preguntas de SISOC.
  Con teclado, las flechas seleccionan sin avanzar; espacio/Enter confirma.
- Configuración, borrador y envío pendiente se guardan en IndexedDB separados
  por usuario. La outbox existente suma pendientes y sincroniza al reconectar.
  Errores conservan las respuestas y permiten corregir o reintentar. El toast
  informa cuando se sincroniza un envío que estaba pendiente.
- La PWA puede retomar offline una sesión de Espacios previamente validada y
  sin cambio de contraseña pendiente. Al reconectar revalida con el servidor;
  cada envío sigue requiriendo token, acceso activo y segmentación. No hay login
  nuevo sin red. El service worker permite reabrir la app y excluye estas APIs
  del caché HTTP común: se usa únicamente el caché local separado por usuario.

Despliegue coordinado: aplicar `0008_disponibilidad_pwa` en el migrador,
actualizar el core (API) y luego publicar la PWA. La migración no activa
encuestas existentes. Reiniciar el worker de encuestas con el código actualizado.

## Permisos y privacidad del módulo

`Gestor de Encuestas` administra encuestas, preguntas, segmentación y rondas.
`Encuestas Resultados` accede al listado y al permiso específico
`encuestas.ver_resultados`, sin adquirir acciones de gestión.

En encuestas anónimas, el sistema conserva el cumplimiento necesario para no
volver a mostrar la ronda, pero resultados y exportaciones no deben asociar el
contenido de una respuesta con una identidad. Los resultados son agregados y
la exportación sigue la política común de CSV/Excel.

La exportación **de configuración JSON** requiere `encuestas.change_encuesta`;
la importación requiere `encuestas.add_encuesta`. Ambas exigen autenticación;
importar y descartar son POST con protección CSRF. Exportar con segmentación
incluye documentos personales por elección explícita del gestor, incluso si
las respuestas de la encuesta son anónimas. No se registran esos documentos
en logs de importación/exportación.

## Despliegue

Aplicar `python manage.py migrate encuestas` (migración
`0003_encuesta_opcional`) antes de servir las nuevas versiones del módulo y
reiniciar el proceso web y `encuestas_worker`. Las banderas nuevas tienen
valor inicial `False`, preservando encuestas y recordatorios existentes.
No revertir esta migración sin considerar la pérdida de la modalidad opcional
y de los descartes almacenados.

## Puntos de entrada

- Dominio y reglas: `src/backends/sisoc_core/encuestas/models.py`, `src/backends/sisoc_core/encuestas/services.py` y
  `src/backends/sisoc_core/encuestas/services_resultados.py`.
- Portabilidad: `exportar_encuesta` / `importar_encuesta` en `services.py`;
  `/encuestas/<pk>/exportar/` y `/encuestas/importar/`.
- Descarte: `/encuestas/responder/<pk>/descartar/` (identificador de ronda).
- Presentación: `src/backends/sisoc_core/encuestas/static/custom/css/encuestaForm.css`,
  `src/backends/sisoc_core/encuestas/static/custom/css/encuestaResponder.css` y templates en `src/backends/sisoc_core/encuestas/templates/`.
- Regresiones de portabilidad/modalidad: `src/backends/sisoc_core/encuestas/tests/test_encuestas_portabilidad.py`
  y `src/backends/sisoc_core/encuestas/tests/test_encuestas_opcionales.py`.
- Bloqueo transversal: `src/backends/sisoc_core/encuestas/middleware.py`.
- Operación de rondas: `src/backends/sisoc_core/encuestas/management/commands/process_encuestas_rondas.py`
  y el servicio `encuestas_worker`.
- Diseño y decisiones históricas: `docs/registro/analisis/2026-08-28-modulo-encuestas.md`.

## Solicitud y aprobación de publicación (issue #2563, punto 5)

- El Gestor de Encuestas solicita publicación desde el listado. La ruta histórica
  `POST /encuestas/<pk>/publicar/` ahora solicita: Borrador → Pendiente aprobación.
  Requiere `encuestas.change_encuesta`, preguntas y segmentación configuradas.
- El grupo **Administrador de Encuestas** tiene `view_encuesta` y el nuevo permiso
  `aprobar_encuesta`. Puede revisar solicitudes, aprobarlas o rechazarlas; no
  recibe permisos de edición ni resultados. Se pueden combinar grupos si hace falta.
- El listado ofrece **Pendientes de aprobación** con contador. La revisión muestra
  configuración, preguntas, condiciones, puntajes y destinatarios, sin respuestas.
  Este listado es la bandeja de recepción; no se envían correos ni notificaciones externas.
- Aprobar (`POST /encuestas/<pk>/aprobar/`) publica y abre la primera ronda en la misma
  transacción. Rechazar (`POST /encuestas/<pk>/rechazar/`) devuelve a borrador sin rondas.
  Solo aceptan pendientes; solicitudes repetidas o resoluciones duplicadas se rechazan.
- Durante la revisión se bloquean cambios de configuración, preguntas y segmentación.
  Los servicios usan bloqueo de fila compartido con las transiciones; también se
  protege la edición en Django admin. El estado no se edita manualmente allí.
- La última modificación registra quién solicitó o resolvió y cuándo.
- Rechazar abre un modal con motivo obligatorio (hasta 2000 caracteres, sin aceptar
  solo espacios). Se guardan `motivo_rechazo`, `usuario_rechazo` y `fecha_rechazo`.
  El gestor accede desde **Ver motivo del rechazo** en el listado y ve **Cambios
  solicitados** al editar. Se conserva el último rechazo al corregir y reenviar,
  visible también al revisor; un nuevo rechazo lo reemplaza. No es un historial
  completo. Los rechazos anteriores quedan sin motivo, sin inventar datos.
  La portabilidad JSON y las nuevas versiones no copian esta información.
- Las encuestas ya publicadas y sus rondas recurrentes mantienen su funcionamiento.
  Las nuevas versiones e importaciones nacen en borrador y recorren la aprobación.
- Despliegue: ejecutar `python manage.py migrate` y `python manage.py create_groups`;
  asignar **Administrador de Encuestas** a los revisores. No se elevan automáticamente
  los permisos de los gestores actuales.
  La migración `0005_motivo_rechazo` agrega los datos del último rechazo.

## API móvil selectiva de Espacios (2026-11-05)

Esta sección describe la entrega selectiva desplegada en PRD el 2026-11-05.
En development la activación ya existe en Segmentación (ver «Publicación en la
PWA de Espacios Comunitarios»); las restricciones de abajo aplican a ese corte.

El core publica `GET /api/encuestas/pwa/` (lista sin paginación) y
`POST /api/encuestas/pwa/<ronda_id>/responder/`. Ambos requieren TokenAuthentication
y acceso móvil confirmado por el servicio dueño de Espacios mediante el helper
HTTP interno existente; no importan módulos Python de otro backend. Contexto
indisponible o inválido falla cerrado con 503; usuario sin acceso recibe 403.

Solo se ofrecen encuestas publicadas, disponibles en PWA, segmentadas para el
usuario y con ronda abierta no vencida. La migración aditiva
`0008_disponibilidad_pwa` conserva el archivo ya publicado en development y agrega
`disponible_pwa=False`, `Pregunta.bloque` y `Pregunta.max_caracteres` opcional.
No se habilitan encuestas existentes ni se entrega aquí una interfaz de activación.

El envío acepta `{response_id: UUID, respuestas: {pregunta_id: valor}}`. La identidad
proviene del token, nunca de un campo del cliente. El UUID se valida pero no se
persiste como ledger: el bloqueo de ronda y CumplimientoRonda deduplican por
usuario/ronda. Los reintentos válidos devuelven `ya_registrada: true`; no se promete
replay luego del cierre o vencimiento (404). Las respuestas inválidas no dejan
contenido ni cumplimiento parcial. La respuesta anónima no referencia al usuario;
el cumplimiento separado sí permite saber que ya respondió, no qué respondió.

Se reutiliza registrar_respuesta para web y móvil, incluyendo límites de texto y
visibilidad recursiva: un descendiente de una pregunta oculta no se vuelve obligatorio.
Las versiones nuevas conservan metadatos y disponibilidad, pero nacen en borrador.
No se cambian editor, segmentación web, permisos de grupos ni contenido operativo.

Despliegue: migración normal del core y regeneración del registro de URLs (solo dos
entradas nuevas). El selector vigente interpreta el registro compartido como refresh
completo de backends. La composición productiva no define `encuestas_worker`;
este cambio no agrega worker/cron ni garantiza la operación automática de rondas.
No retirar columnas con datos para un rollback de código: conservar el esquema
aditivo y coordinar una reversión compatible. Ver el registro de cambio para pruebas
y límites de evidencia de esta entrega.
