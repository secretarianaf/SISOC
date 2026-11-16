# E02, E03, E04 y D01: gestión de encuestas y tableros en React sobre G1 v1

Estado M2 ejecutable: contrato basado en la fuente HEAD `b920d91d8`, sin ejecución de datos reales, correo, proveedores
externos ni la ronda programada.
Entregas del catálogo `2026-10-27-2785-entregas-por-flujo.json`, en el orden de implementación: E02 «Segmentación e
importación» (app `src/backends/sisoc_core/encuestas`), E03 «Resultados y exportación», E04 «Gestión, revisión y rondas» y
D01 «Dashboards y tableros» (app `src/backends/sisoc_core/dashboard`). E01 (responder encuestas) ya está en React y no
cambia: ver `docs/registro/cambios/2026-T4/2026-11-04-2785-react-respuesta-encuestas.md`.
Regla transversal: paridad nativa (S13: «mantene la paridad»). Las rutas HTML nativas no cambian; React las atiende solo
desde la vista previa local hasta la activación acordada.

## Entregas y orden

| ID | Título | Rutas nativas cubiertas | Depende de |
| --- | --- | --- | --- |
| E02 | Segmentación e importación | GET `/encuestas/<pk>/segmentacion/`, POST `.../segmentacion/tipo/`, `.../agregar/`, `.../<destinatario_pk>/quitar/`, POST `/encuestas/importar/`, GET `.../segmentacion/plantilla/` (binario nativo enlazado) | Transporte común (abajo) |
| E03 | Resultados y exportación | GET `/encuestas/<pk>/resultados/`, GET `.../resultados/rondas/<ronda_pk>/exportar/` y GET `/encuestas/<pk>/exportar/` (binarios nativos enlazados) | E02 |
| E04 | Gestión, revisión y rondas | GET `/encuestas/`, GET/POST `/encuestas/crear/`, `/encuestas/<pk>/editar/`, POST `.../publicar/`, GET `.../revision/`, POST `.../aprobar/`, `.../rechazar/`, POST `/encuestas/rondas/<pk>/cerrar/` | E02, E03 |
| D01 | Dashboards y tableros | GET `/dashboard/centro-de-familia`, GET `/dashboard/<slug>/` | transporte común |

La ronda programada de encuestas (apertura y cierre por fecha) sigue en el worker nativo: no se invoca ni se replica desde la
API. Cerrar una ronda a mano (`encuestas_ronda_cerrar`) corre `cerrar_ronda(ronda, manual=True)` sin cambios.

## Transporte común

- Montaje: `path("api/web/encuestas/", include("encuestas.web_api_urls"))` en `src/backends/config/urls.py`, hermano de
  `api/web/auditoria/`. Lo sirve el core: la app vive en `sisoc_core` y no se reenvía a un backend de vertical.
- Cada vista es una `APIView` con `SessionAuthentication`, `WebGatePermission` (401 sin sesión; 403 con `state` y
  `required_action_url` ante un requisito web pendiente) y, después, los **mismos códigos de permiso** que el decorador de
  `encuestas/urls.py`. Sin ese permiso: 403 `{"detail": "No tiene permisos para esta acción."}`. Respuestas
  `private, no-store` con `Vary: Cookie`. Las escrituras exigen CSRF (403) y cuerpo `application/x-www-form-urlencoded` o
  multipart (415 si el cuerpo es de otro tipo).
- Implementación: `web_transport_encuestas.py` ejecuta la vista nativa (`setup` + `dispatch`) sobre la misma petición. Los
  formularios, servicios, `ValidationError` y mensajes son los nativos, no se reimplementan. Un 302 nativo se convierte en
  `{"ok": true, "redirect": "<Location>", "messages": [{message, level}]}`: los mensajes en cola se consumen en esa respuesta,
  como los mostraría la página tras el redirect. Un rechazo del servicio (mensaje de error y redirect) conserva ese
  contrato: 200 con `ok`, el mensaje en `error` y **sin cambios persistidos**.
- Lectura: la vista nativa de detalle corre su `get` y el JSON proyecta el contexto de la plantilla tal como la imprime
  (textos, fechas en hora local, números con la localización de Django). Un objeto fuera del queryset nativo da 404; un
  redirect nativo (encuesta pendiente de aprobación) se devuelve como `{"redirect": "<Location>"}`.
- Vista previa: `web_preview_encuestas.py` (nunca montado por un URLconf de producción) conserva la URL nativa, el mismo
  decorador `permissions_any_required` y el `dispatch` nativo (login, 404, redirect); solo el GET sirve el `index.html`
  congelado. Los activos viajan por la entrada de `ciudadanos.web_preview`, como en auditoría.
- `config/middlewares/admindocs.py` agrega las rutas propias para que admindocs no responda metadatos (HEAD desde IP
  interna) antes de los controles de sesión y permiso. `url_registry.json` se actualiza con `generar_registro_urls`.

## E02 Segmentación e importación

### Acceso (conservado)

- `encuestas/<pk>/segmentacion/` y sus tres POST: `encuestas.change_encuesta`. `encuestas/importar/`: `encuestas.add_encuesta`.
  La plantilla de segmentación es el GET nativo `.../plantilla/?tipo=` (`change_encuesta`), enlazado como descarga.
- Una encuesta pendiente de aprobación no se segmenta: el GET redirige a la revisión (nativo y API).

### API

- `GET /api/web/encuestas/<pk>/segmentacion/` → `{id, titulo, disponible_pwa, tipo ("" sin segmentación), grupos:
  [{id, name, selected}], destinatarios: [{id, tipo_label, numero_documento}], usuarios: [{id, username, full_name}],
  urls: {plantilla}, messages}`.
- `POST .../segmentacion/tipo/` (multipart: `tipo`, `disponibilidad_pwa_presente`, `disponible_pwa`, `grupos`,
  `archivo_listado`), `.../agregar/` (`tipo_documento` y `numero_documento`, o `usuario_id`), `.../<destinatario_pk>/quitar/`
  y `POST /api/web/encuestas/importar/` (`archivo`). Cada uno corre su vista nativa y responde el contrato común. La
  importación solo expone el endpoint: su botón es de la lista (E04) y no se dibuja antes.

### Pantalla React (`encuestasSegmentacion.tsx`)

- Se dibujan los cuatro tipos como tarjetas de opción, el interruptor PWA, la lista de grupos con búsqueda y chips, el campo de
  archivo (solo con los tipos de listado), «Descargar plantilla» con el `?tipo=` del tipo marcado, «Agregar destinatario» y la
  lista de destinatarios, con los textos y el orden de la plantilla.
- Se envía lo que envía el formulario nativo (`FormData` del propio formulario: el grupo y el archivo deshabilitados no
  viajan). Tras cada POST se leen de nuevo los datos, se muestran los mensajes verbatim como toasts al final de `<body>` y
  se reinicia scroll y foco, como la recarga nativa.

## E03 Resultados y exportación

- Acceso: `encuestas.ver_resultados` (lista de resultados y exportación por ronda); `encuestas.change_encuesta` para exportar la
  encuesta (`encuestas_exportar`). Solo lectura: las exportaciones CSV, Excel y JSON son los GET nativos enlazados, sin
  reimplementarlos en la API.
- `GET /api/web/encuestas/<pk>/resultados/?ronda=` proyecta el contexto de `encuesta_resultados.html` (rondas, ronda actual,
  tarjetas, puntajes y resultados por pregunta con `opcion_lider_texto` y `posicion_promedio`). El selector de ronda hace un GET
  de la página con `?ronda=`, como el `onchange` nativo.
- Riesgo de confidencialidad: el JSON no agrega campos que la plantilla no imprime (identificadas y anónimas se proyectan
  igual que hoy); los filtros de ronda son los de la vista.

## E04 Gestión, revisión y rondas

E04 se entrega en subunidades; cada una activa solo los pathname que cubre.

### E04.A Lista y acciones de fila (entregada)

- Lista (`EncuestaListView`, `GET /api/web/encuestas/lista/?filters=&page=`): `encuestas.view_encuesta` o
  `encuestas.ver_resultados`, igual que la URL nativa. Proyecta el contexto de `encuesta_list.html` y de la barra de búsqueda que
  incluye: `filters_config` y `favorites` (sección vacía, como la plantilla), filas ya formateadas (versión, fecha `d/m/Y`,
  estado, modalidad con `capfirst`, anónima o identificada, creador), banderas `puede_*`, bandeja de pendientes (`aprobar_encuesta`)
  y paginación de 20 con el prefijo de consulta de `pagination.html`. Los enlaces antiguos `busqueda`/`estado` devuelven el
  redirect nativo a `filters`; una página inválida es 404.
- «Solicitar publicación»: `POST /api/web/encuestas/<pk>/publicar/` corre `EncuestaPublicarView` (`solicitar_publicacion`).
  «Importar»: el archivo oculto se envía a `POST /api/web/encuestas/importar/` (E02). Ambos dejan el mensaje nativo **en cola** y
  la pantalla navega al redirect (recarga completa, como el formulario nativo): la lista siguiente muestra el mensaje una vez.
  Un rechazo del servicio no cambia nada y muestra su mensaje de error.
- `POST /api/web/encuestas/rondas/<pk>/cerrar/` (`encuestas.change_rondaencuesta`) corre `cerrar_ronda(ronda, manual=True)`.
  Ninguna plantilla ni pantalla nativa dibuja un control para esa ruta, así que la API queda probada (efecto persistido, repetir
  sin cambios, permisos) y React no agrega un botón.
- Los enlaces «Editar», «Segmentación», «Revisar solicitud», «Resultados», «Ver motivo del rechazo», «Crear encuesta» y
  «Ver pendientes» van a las rutas nativas o de React ya incorporadas.

### E04.B Revisión, aprobar y rechazar (pendiente)

- `EncuestaRevisionView` (`encuestas.aprobar_encuesta` o `encuestas.change_encuesta`), `EncuestaAprobarView` y
  `EncuestaRechazarView` (solo `aprobar_encuesta`; el rechazo con motivo inválido es 400 con el formulario). Sin implementar.

### E04.C Formulario de alta y edición (pendiente)

- `EncuestaCreateView` y `EncuestaUpdateView` (`add_encuesta` y `change_encuesta`): campos generales, editor de preguntas
  (`preguntas_json`, validado con `reemplazar_preguntas`), condiciones, opciones y ponderación, y el menú «Exportar JSON»
  (`encuestas_exportar`). Sin implementar: el editor dinámico (`encuestaPreguntasBuilder.js`, 571 líneas, con arrastre) es la
  parte de mayor riesgo de paridad.

## D01 Dashboards y tableros

- `DashboardView` y `TableroEmbedView` exigen sesión (`login_required`); el tablero además `usuario_puede_ver`.
  Las métricas de comedores y de Centro de Familia vienen de las mismas funciones nativas; un cero no prueba ausencia de datos
  cuando una fuente remota no responde (se conserva el aviso nativo).
- Los gráficos usan las mismas versiones de CDN que la plantilla nativa; el iframe del tablero conserva `title` y `src`.

## Criterios de aceptación y verificación

- Cada unidad: pruebas de acceso (401, 403, CSRF 403), efecto persistido y «sin cambios» ante rechazo; G1 de extremo a extremo;
  comparación visual nativo contra React en los estados clave (escritorio y móvil) y las guardas.
- Excepciones asumidas: página 2 de listas, menú móvil y el nombre accesible del logo del shell.

## Incertidumbres

- La activación de React en producción no forma parte de este contrato.
- El detalle de E03, E04 y D01 se amplía en cada unidad cuando se cierra su lectura de plantilla.
