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
se valida con `AdvancedFilterEngine` y un mapa cerrado en `encuestas/filters.py`.
Los enlaces anteriores con `busqueda` y `estado` se redirigen a filtros visibles;
la paginación conserva los filtros. Resetear vuelve al listado completo.
La bandeja del aprobador ofrece un acceso a pendientes usando ese mismo filtro.

La revisión sigue las tarjetas y botones de Editar usuario: datos de la encuesta,
destinatarios desplegables y preguntas con sus opciones. Un panel lateral reúne
solicitante, fecha y consecuencias de aprobar o rechazar; en móvil aparece debajo
del contenido. Se mantiene la autorización y el envío POST con CSRF.

El botón «Agregar pregunta» permanece al pie del listado, a la derecha.
Crear/editar, segmentación y el modal de respuesta comparten tokens y botones
Poncho. El modal agrupa preguntas, resalta opciones seleccionadas e informa la
modalidad y el anonimato. Conserva preguntas condicionales y dispone de scroll
interno y adaptación a pantallas pequeñas.

## Permisos y privacidad

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

- Dominio y reglas: `encuestas/models.py`, `encuestas/services.py` y
  `encuestas/services_resultados.py`.
- Portabilidad: `exportar_encuesta` / `importar_encuesta` en `services.py`;
  `/encuestas/<pk>/exportar/` y `/encuestas/importar/`.
- Descarte: `/encuestas/responder/<pk>/descartar/` (identificador de ronda).
- Presentación: `src/backends/sisoc_core/encuestas/static/custom/css/encuestaForm.css`,
  `src/backends/sisoc_core/encuestas/static/custom/css/encuestaResponder.css` y templates en `encuestas/templates/`.
- Regresiones de portabilidad/modalidad: `encuestas/tests/test_encuestas_portabilidad.py`
  y `encuestas/tests/test_encuestas_opcionales.py`.
- Bloqueo transversal: `encuestas/middleware.py`.
- Operación de rondas: `encuestas/management/commands/process_encuestas_rondas.py`
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
