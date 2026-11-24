# DC01-DC02: DataCalle en React (operativos, casos y lookups del backoffice)

Contrato ejecutable de #2785 para los flujos DC01 y DC02 del catálogo
[entregas por flujo](2026-10-27-2785-entregas-por-flujo.json). Fuente leída en
`HEAD 4ea95bcbe` con `git show`; las líneas del catálogo quedaron viejas y acá se
citan las vigentes. Alcance: **solo el backoffice web**. La app de campo
(SISOC - Mobile), su cola offline y la API por token `api/datacalle/` no se migran
ni se usan desde el navegador. Regla general: paridad nativa; quirks documentados,
no corregidos.

## Decisiones comunes

- Dueño: runtime `dispositivos` (apps `dispositivos` y `datacalle`,
  `src/backends/config/backends.json`). Endpoints bajo
  `/api/web/dispositivos/datacalle/`: un solo prefijo por runtime
  (`api/web/dispositivos/`, el mismo que DS01-DS02), porque G1 exige que el
  segmento después de `api/web/` sea la clave del vertical (`backend_proxy.py`
  rechaza `api/web/<otro>/` al arrancar). Setup compartido del padre.
- Transporte G1 v1 ([decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md)):
  `APIView` con `SessionAuthentication` + `core.web_gate.WebGatePermission`, luego
  el permiso de acción y el alcance nativos en la vista del dueño. CSRF en POST.
  `Cache-Control: private, no-store`. Sin reintento automático.
- Reutilización obligatoria (`src/backends/dispositivos/datacalle/services/__init__.py`):
  `get_relevamientos_queryset`, `apply_relevamientos_scope`, `resumen_por_estado`,
  `save_relevamiento_from_form`, `delete_relevamiento`, `cerrar_relevamiento`,
  `get_encuestas_queryset`, `get_encuestas_para_listado`, `resumen_de_casos`,
  `respuestas_legibles`, `observacion_asentamiento_legible`,
  `get_dispositivos_para_provincia`, `get_entrevistadores_para_provincia`;
  `RelevamientoForm` (`forms.py:14-161`) con `actor=request.user`.
- La API por token (`api_urls.py:1-19`, `api_views.py:1-225`) queda intacta: mismo
  contrato, mismos 409 y mismo permiso `TieneAccesoDataCalle`. No se le agrega
  `SessionAuthentication`.
- Geografía en cascada: endpoints JSON del core `/ajax/load-municipios/` y
  `/ajax/load-localidades/` (ya acotados por alcance, `kernel/core/views.py:67-84`),
  igual que el template nativo (`relevamiento_form.html:235-236`).
- Sobre de página como `InsumoPageSerializer` (`count`, `page`, `page_size`,
  `pages`, `filters`, `results`); página inválida 404 «Página no válida.»; errores
  de form 400 `{"errors": ...get_json_data()}`.
- Módulos React: `src/frontends/apps/sisoc/src/routes/datacalleRelevamientos.tsx`
  (listado, ficha, alta, edición, cierre, baja) y
  `src/frontends/apps/sisoc/src/routes/datacalleCasos.tsx` (ficha de caso). Rutas de
  pantalla iguales a las nativas. Entrada React por runtime según el piloto de
  Inspecciones (L134).
- Navegación: `sidebar_access.py:9-28` registra el predicado `datacalle` (coordinador
  sin `comedores.view_comedor` ve solo Situación de Calle). El shell React lo toma del
  contexto web del core (#2798); no se reimplementa.
- Regla visual S13 por caso, escritorio y móvil.

## Rutas nativas y permisos

Fuente: `src/backends/dispositivos/datacalle/urls.py:16-76`; decoradores
`permissions_any_required` (403 por `PermissionDenied`) más `LoginRequiredMixin`.

| Nombre | Ruta | Permiso | Alcance |
|---|---|---|---|
| `datacalle_relevamientos_listar` | `GET /datacalle/relevamientos/` | `view_relevamiento` | provincial |
| `datacalle_relevamientos_crear` | `GET/POST .../crear/` | `add_relevamiento` | form acotado |
| `datacalle_relevamientos_detalle` | `GET .../<uuid>/` | `view_relevamiento` | provincial; 404 fuera |
| `datacalle_relevamientos_editar` | `GET/POST .../<uuid>/editar/` | `change_relevamiento` | provincial |
| `datacalle_relevamientos_cerrar` | `POST .../<uuid>/cerrar/` | `change_relevamiento` | provincial |
| `datacalle_relevamientos_eliminar` | `GET/POST .../<uuid>/eliminar/` | `delete_relevamiento` | provincial |
| `datacalle_casos_detalle` | `GET /datacalle/casos/<uuid>/` | `view_encuesta` | caso de relevamiento en alcance |
| `datacalle_ajax_dispositivos` | `GET /datacalle/ajax/dispositivos/` | `view_relevamiento` | provincia pedida ∩ alcance |
| `datacalle_ajax_relevadores` | `GET /datacalle/ajax/relevadores/` | `view_relevamiento` | provincia pedida ∩ alcance |

Alcance (`services/relevamientos.py:29-50`): anónimo vacío; superusuario o no
territorial sin restricción; territorial por `get_full_province_scope_ids` (solo
provincias completas); sin alcance vacío. Distinto del alcance de Dispositivos
(que baja a municipio): no unificar.

## Endpoints `/api/web/dispositivos/datacalle/`

| Método y ruta | Permiso y alcance | Respuesta |
|---|---|---|
| `GET relevamientos/` | `view_relevamiento`; scope | página de 15 + resumen |
| `GET relevamientos/<uuid>/` | `view_relevamiento`; scope | ficha del operativo |
| `GET relevamientos/formulario/` | `add_relevamiento` | esquema de alta |
| `POST relevamientos/crear/` | `add_relevamiento` | 201 / 400 |
| `GET relevamientos/<uuid>/formulario/` | `change_relevamiento`; scope | esquema + valores |
| `POST relevamientos/<uuid>/editar/` | `change_relevamiento`; scope | 200 / 400 |
| `POST relevamientos/<uuid>/cerrar/` | `change_relevamiento`; scope | 200 |
| `GET relevamientos/<uuid>/eliminar/` | `delete_relevamiento`; scope | confirmación |
| `POST relevamientos/<uuid>/eliminar/` | `delete_relevamiento`; scope | 200 |
| `GET casos/<uuid>/` | `view_encuesta`; caso en alcance | ficha del caso |
| `GET opciones/dispositivos/?provincia_id=` | `view_relevamiento` | `[{id, nombre}]` |
| `GET opciones/relevadores/?provincia_id=` | `view_relevamiento` | `[{id, nombre}]` |

`<uuid>` usa el conversor `uuid` como la ruta nativa; un id no UUID da 404.

## DC01.01 Consulta de operativos y relevamientos [L]

Fuente: `views.py:36-114`, `models.py:11-188`, `templates/datacalle/relevamiento_list.html:1-154`,
`templates/datacalle/relevamiento_detail.html:1-292`.

Listado:

- Orden de `Meta.ordering` `-fecha_inicio`, `denominacion` (`models.py:115-118`);
  15 por página. Filtros: `estado` (solo valores de `Relevamiento.Estado`), `fase`
  (solo `Relevamiento.Fase`), `busqueda` (trim) `icontains` sobre `denominacion`,
  `area_operativa`, `provincia__nombre`, `localidades__nombre`, nombre, apellido,
  usuario y `profile__dni` del equipo, con `distinct()`. Valores inválidos de
  `estado`/`fase` se ignoran (no 400).
- `resumen` (`resumen_por_estado`): total y conteo por estado sobre **todo el alcance
  del usuario, sin filtros** (quirk a conservar).
- Fila: `denominacion`, `fase_display`, `lugar` (nombre del dispositivo si la fase es
  alojamiento, si no `area_operativa`), `modalidad_papel` («papel»), `provincia`,
  `zonas` (localidades unidas por coma o municipio, «—» vacío), fechas `d/m/y`,
  `dias` con plural, cantidad de equipo, `estado` y `estado_display`; `can_change`
  según permiso.
- Textos: «Relevamientos DataCalle», «Operativos de situación de calle», «Le llegan
  como tarea al equipo en SISOC - Mobile», «Planificar relevamiento» (solo con
  `add_relevamiento`), «Total», placeholder «Buscar por denominación, área,
  provincia, localidad, encuestador o DNI», «Todos los estados», «Ambos tipos de
  operativo», «Filtrar»; columnas Operativo, Jurisdicción, Fechas, Equipo, Estado,
  Acciones; «Ver», «Editar»; vacío «Todavía no hay operativos» / «Planificá uno para
  que le aparezca como tarea al equipo en la app.»; paginación «Volver»/«Continuar»
  conservando filtros. `titulo` de contexto «Buscar Relevamientos» no se muestra en
  el template (no agregarlo).

Ficha:

- Encabezado: denominación, chip de estado, provincia, zonas, días. Acciones:
  «Editar» (`change`), «Cerrar relevamiento» (`change` y estado distinto de
  `finalizado`), «Eliminar» (`delete`).
- Secciones y textos: «Dónde se releva» (Fase; «Dispositivo» o «Área operativa»;
  Jurisdicción provincia · municipio; «Localidades / comunas» como chips o «—»);
  «Cuándo» («Período planificado» `d/m/Y → d/m/Y (n días)`, «Formato en papel»
  Sí/No, «Planificado por» nombre completo o usuario o «—»); contadores
  `resumen_de_casos` (Casos, Personas observadas, Entrevistas, Sin entrevista,
  Sin entrevista por edad); «Equipo asignado» con «{n} entrevistador(es)», iniciales,
  nombre, «DNI {dni}», vacío «Sin equipo asignado: nadie va a ver este operativo en
  la app.»; «Observaciones» solo si hay (saltos de línea); «Cierre en campo»
  («Cerrado» `d/m/Y H:i` «por {nombre}», «Punto GPS» `lat, lon` o «—»,
  «Observación del asentamiento» etiquetas unidas por coma o «—», «Otra observación»
  si hay) o vacío «Todavía sin cerrar» / «El equipo cierra el operativo desde la app y
  ahí llegan el punto GPS y la observación del asentamiento.».
- «Casos relevados» / «se cargan desde la app»: **máximo 50** casos
  (`get_encuestas_para_listado(...)[:50]`, orden `-fecha_inicio`), sin paginación ni
  aviso de truncado (quirk a conservar). Columnas Código, Persona, Lugar, Estado,
  Cargado, Acciones; chips «Sin entrevista (edad)» y «Menores (14 a 17)»; «Ver»;
  vacío «Todavía no llegaron casos» / «Aparecen acá a medida que el equipo sincroniza
  desde la app.». El enlace «Ver» se muestra sin chequear `view_encuesta` (la ruta del
  caso sí lo exige): conservar.
- Quirk de visualización: «Punto GPS» se muestra solo si `lat` es verdadero; `lat = 0`
  se ve como «—». Conservar.

Exportación: no hay export web nativo de DataCalle (las métricas viven en el admin,
`admin_metricas.py`, fuera de alcance).

## DC01.02 Captura y modificación [M]

Fuente: `views.py:117-157`, `forms.py:14-161`, `services/relevamientos.py:53-156`,
`models.py:154-187`, `templates/datacalle/relevamiento_form.html:1-310`,
`templates/datacalle/relevamiento_confirm_delete.html:1-27`.

Esquema (`formulario/`): campos en orden `denominacion`, `provincia`, `municipio`,
`localidades`, `fase`, `area_operativa`, `dispositivo`, `fecha_inicio`, `fecha_fin`,
`modalidad_papel`, `equipo`, `observaciones`; etiquetas y ayudas del modelo; secciones
«Identificación», «Dónde se releva» (ayuda «La fase define si el lugar es un área del
espacio público o un dispositivo de alojamiento.»), «Cuándo» («Puede durar un día o
varios.»), «Equipo» («Sólo los entrevistadores elegidos ven el operativo en la
app.»); encabezado «Planificar relevamiento» o «Editar relevamiento» con «El
operativo le llega como tarea a los entrevistadores del equipo»; botones «Guardar» y
«Cancelar» (al listado).

Reglas:

- `provincia` acotada a `get_provincias_para_usuario`; con una sola provincia el campo
  va deshabilitado con ayuda «Tu alcance territorial es esta provincia.» y el servidor
  ignora lo enviado (`disabled`). React lo muestra deshabilitado y no debe depender del
  cliente.
- `municipio` y `localidades` opcionales; `dispositivo` y `equipo` acotados a la
  provincia elegida dentro del alcance (`opciones/dispositivos/`,
  `opciones/relevadores/`, etiqueta «Nombre Apellido (DNI)» o usuario). Placeholders
  «Seleccionar municipio...», «Seleccionar dispositivo...».
- Con `dispositivos.add_dispositivo`: «¿No está en la lista? Dar de alta un
  dispositivo y volvé a elegir la provincia para recargarlo.» con enlace a
  `/dispositivos/crear` en pestaña nueva.
- Mensajes literales: «Elegí al menos un entrevistador para el equipo.»;
  «Hay integrantes que no son entrevistadores de DataCalle en esa provincia: {usuarios}.»;
  «Para elegir localidades primero elegí el municipio.»;
  «Hay localidades que no pertenecen al municipio elegido: {nombres}.»;
  «La fecha de fin no puede ser anterior a la de inicio.»;
  «El municipio no pertenece a la provincia seleccionada.»;
  «Indicá el área operativa del espacio público.»;
  «En espacio público no corresponde un dispositivo.»;
  «Elegí el dispositivo de alojamiento.»;
  «El dispositivo no pertenece a la provincia seleccionada.».
- La fase limpia el campo de lugar que no corresponde (`forms.py:156-160`).

Efectos:

- Alta: `save_relevamiento_from_form(form, user=...)` asigna `creado_por` si falta,
  corre `full_clean(exclude=["creado_por"])`, guarda y `save_m2m`. Destino: ficha.
  **Sin mensaje de éxito** (el nativo no emite ninguno; no agregarlo). 201.
- Edición: mismo servicio; conserva `creado_por`; destino ficha sin mensaje. 200.
- Baja: confirmación «Confirmar eliminación» / «¿Seguro que desea eliminar el
  relevamiento {denominación}?» / «Se da de baja de forma lógica: deja de verse como
  tarea en la app y queda recuperable desde la papelera.»; «Eliminar», «Cancelar» (a
  la ficha). `delete_relevamiento(obj, user=...)` (baja lógica,
  `SoftDeleteModelMixin`); destino listado **sin mensaje**. Incertidumbre: el efecto
  sobre los casos (`Encuesta`, también soft delete, FK `CASCADE`) depende del mixin;
  la prueba compara el estado de casos tras la baja nativa y la de API, sin
  reimplementar la cascada.
- Efecto indirecto: cambiar `equipo` cambia qué entrevistadores ven el operativo en la
  app (API por token `mis_relevamientos`, `api_views.py:68-84`). Probarlo.

## DC01.03 Cierre y reintento con contrato vigente [W]

Fuente: `views.py:160-181`, `services/encuestas.py:143-167`,
`relevamiento_detail.html:29-38`.

- Corrección del catálogo: el cierre web **no** devuelve 409. Los 409
  (`relevamiento_cerrado`, `relevamiento_no_iniciado`) son de la carga de casos por
  token (`api_views.py:43-57,190-193`), fuera del backoffice.
- `POST relevamientos/<uuid>/cerrar/` sin cuerpo: `cerrar_relevamiento(relevamiento,
  user)` atómico e idempotente. Primer cierre: estado `finalizado`, `fecha_cierre`
  ahora, `cerrado_por` el usuario; respuesta 200 `{"cerrado_ahora": true,
  "message": "El relevamiento quedó cerrado."}`. Repetido: sin cambios, 200
  `{"cerrado_ahora": false, "message": "El relevamiento ya estaba cerrado."}`
  (nativo: `messages.info`). React vuelve a la ficha con el mensaje y su nivel.
- Permiso web: `change_relevamiento` + alcance. **No** exige rol de coordinador
  DataCalle (a diferencia de la acción de la API por token, `api_views.py:126-134`);
  conservar la asimetría. GET al cierre: 405 (el nativo solo define `post`).
- Sin confirmación previa en el nativo (botón directo dentro de un form POST): no
  agregar diálogo.
- Reintento: nunca automático. Ante 504 `uncertain`, React recarga la ficha (GET) y
  muestra el estado real antes de ofrecer otra vez el botón (que desaparece si quedó
  `finalizado`). El reintento manual es seguro por idempotencia.

## DC02.01 Casos y catálogos [L]

Fuente: `views.py:184-254`, `services/encuestas.py:186-196`,
`services/instrumento.py:218-259`, `models.py:189-308`,
`templates/datacalle/encuesta_detail.html:1-92`.

Caso (`GET casos/<uuid>/`):

- Queryset: `get_encuestas_queryset()` filtrado por relevamientos en alcance; fuera de
  alcance o soft-deleted 404. Requiere `view_encuesta` (no `view_relevamiento`).
- Datos: `codigo_entrevistado` o id; estado (chip «finalizado» si `completa`, si no
  «planificado»), `origen_display`, relevador (nombre completo o usuario),
  `fecha_inicio` `d/m/Y H:i`, `variante_etiqueta`, `es_formulario_menores`,
  `sin_entrevista_por_franja`, `persona_entrevistada_etiqueta`; breadcrumb
  Relevamientos → denominación → código o id.
- `respuestas`: salida literal de `respuestas_legibles` (páginas con `titulo` e
  `items` `{etiqueta, valor, historico}`); claves desconocidas se muestran con su id
  crudo; «pregunta retirada» para históricas; vacío «—».
- Textos: título «Caso {código}»; aviso de menores «Formulario de menores (14 a 17
  años): se relevan el código de identificación y los vínculos, el documento, el nivel
  educativo, dónde duerme esta noche y desde cuándo está en situación de calle. Las
  demás preguntas del papel general no se le preguntan: no son datos faltantes.»;
  aviso de franja «Por su franja etaria no correspondía entrevistarla: fue observada y
  cuenta en el grupo ({etiqueta}).»; vacío «El caso no trae respuestas» / «Llegó desde
  la app sin contenido en el instrumento.».
- PII: el caso contiene datos sensibles de personas en situación de calle (incluidos
  menores). La API devuelve solo lo que hoy muestra la ficha; no se exponen
  `respuestas` crudas, `lat`/`lon` del caso ni `grupo_id` si la ficha no los muestra.

Lookups (`opciones/dispositivos/`, `opciones/relevadores/`): mismo cuerpo que
`cargar_dispositivos`/`cargar_relevadores` (`views.py:217-254`); `provincia_id`
inválido o ausente → lista vacía (200). Entrevistadores: activos con
`profile__datacalle_rol="entrevistador"` en la provincia, orden nombre, apellido,
usuario.

## DC02.02 Gestión autorizada [M]

No hay operación web nativa sobre casos: el backoffice no edita ni borra encuestas
(solo la API por token tiene `update`/`destroy`, `api_views.py:174-203`). Esta
entrega **no tiene alcance que migrar**; queda cerrada sin trabajo. No se inventa una
edición de casos. La gestión del operativo es DC01.02/DC01.03.

## DC02.03 Regresión del consumidor de campo [K]

Objetivo: probar que la migración no cambia la app de campo.

- `api/datacalle/` sin cambios de código; rutas, permisos, cuerpos y códigos
  (incluidos 403 `cierre_no_autorizado` y 409 con `reintentable`) iguales.
- Pruebas existentes en verde sin modificarlas: `src/backends/dispositivos/tests/test_datacalle_api.py`,
  `test_datacalle_relevamientos.py`, `test_datacalle_roles.py`,
  `test_datacalle_qa_usuarios.py`, `test_datacalle_repro_500.py`,
  `test_datacalle_instrumento_4_0_0.py`, `test_datacalle_instrumento_4_1_0.py`,
  `test_datacalle_instrumento_4_1_1.py`.
- Diferencial: misma secuencia de requests por token contra base y candidato,
  stdout/estado/cuerpo idénticos.
- Invariantes cruzadas: alta/edición/cierre/baja hechas desde la API web se ven en la
  app igual que si se hicieran desde el HTML nativo (`mis_relevamientos`, estado,
  `updated_at` para `?desde=`).

## Dependencias

- Setup compartido `api/web/dispositivos/` (DS01-DS02 lo comparte; un solo dueño).
- Patrón de entrada React por runtime (piloto Inspecciones, L134); shell y sidebar
  del contexto web del core (#2798).
- DS02.02 para el enlace «Dar de alta un dispositivo» (sigue apuntando a la ruta de
  pantalla).

## Riesgos

- Alcance provincial distinto del de Dispositivos (provincias completas): reutilizar
  `apply_relevamientos_scope`, no `apply_dispositivos_scope`.
- PII sensible y menores: proyección mínima igual a la ficha; sin logs de cuerpos.
- Baja lógica con efecto en la app; cierre que corta la jornada del equipo: sin
  reintento automático.
- Ficha con 50 casos como máximo: no "arreglar" con paginación sin decisión.

## Casos de prueba

Backend (`src/backends/dispositivos/datacalle/tests/` o `src/backends/dispositivos/tests/`):

1. Listado: superusuario, no territorial, provincial, provincial sin alcance (vacío);
   `estado`, `fase`, `busqueda` por cada campo del equipo; valores inválidos
   ignorados; `resumen` sin filtros; orden y página igual al nativo.
2. Permisos: cada endpoint con y sin su permiso (403); objeto de otra provincia 404;
   caso con `view_encuesta` sin `view_relevamiento` 200; sin `view_encuesta` 403.
3. Formulario: cada mensaje literal; provincia única deshabilitada ignora POST de otra
   provincia; equipo fuera de provincia; localidades sin municipio o de otro municipio;
   fase limpia el campo opuesto; `creado_por` se asigna solo en alta.
4. Cierre: primer cierre (campos), repetido (mensaje info, sin cambios), GET 405,
   usuario con `change` sin rol coordinador puede cerrar (paridad), otra provincia 404.
5. Baja: soft delete, relevamiento ausente del listado y de `mis_relevamientos`;
   estado de casos igual a la baja nativa.
6. Caso: menores, franja, sin respuestas, clave desconocida, pregunta retirada; soft
   deleted 404.
7. G1: sin constancia rechazado en runtime; sin sesión 401 desde el core.
8. DC02.03 completo.

Frontend: textos literales, botones por permiso, cierre oculto si `finalizado`,
504 `uncertain` recarga la ficha, cascadas provincia → municipio/dispositivo/equipo,
provincia única deshabilitada, orden de Tab.

Visual S13: listado (con/sin operativos, filtros), ficha (sin cerrar/cerrada, sin
equipo, sin casos, 50 casos), alta, edición con errores, confirmación de baja, caso
(normal, menores, franja, vacío); escritorio y móvil.

## Fuente

`src/backends/dispositivos/datacalle/urls.py:16-76`; `views.py:36-254`;
`forms.py:14-161`; `services/relevamientos.py:21-180`;
`services/encuestas.py:143-257`; `services/instrumento.py:218-259`;
`models.py:11-308`; `api_urls.py:1-19`; `api_views.py:43-225`;
`api_permissions.py:1-20`; `sidebar_access.py:1-28`;
`templates/datacalle/relevamiento_list.html:1-154`; `relevamiento_detail.html:1-292`;
`relevamiento_form.html:1-310`; `relevamiento_confirm_delete.html:1-27`;
`encuesta_detail.html:1-92`; `src/backends/kernel/core/views.py:67-84`;
`src/backends/dispositivos/dispositivos_runtime/urls.py:8-12`. Leído en
`HEAD 4ea95bcbe`; sin app, tests, DB, navegador ni remoto.

- [Dispositivos DS01-DS02](2026-11-10-2785-dispositivos-ds01-ds02-contratos.md).
- [Catálogo existente](2026-10-27-2785-entregas-por-flujo.json).
