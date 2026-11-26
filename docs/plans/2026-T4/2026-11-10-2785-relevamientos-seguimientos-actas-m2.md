# R01, R02, R03: relevamientos, seguimientos y actas complementarias

Estado M2 ejecutable: contrato basado en fuente HEAD 4ea95bcbe, sin ejecución de app, DB, correo, proveedores ni capturas.
Entregas: R01.01 Relevamiento y seguimiento [L], R01.02 Captura y edición de datos [M], R01.03 Documentos y descargas [F],
R02.01 Consulta de actas [L], R02.02 Operaciones y evidencias del acta [W], R03.01 Seguimientos y PNUD [L],
R03.02 Acciones y estados asociados [W]. Perfiles del catálogo (`contract_profiles`): L «Lectura y navegación»,
M «Mutación de datos», W «Acción o transición de circuito», F «Archivo documento o exportación».
Dueño: backend `comedores`, app `relevamientos` (`src/backends/comedores/relevamientos`). Las APIs GESTIONAR existentes no cambian.

## Entregas y orden

| ID | Título | Perfil | Rutas nativas cubiertas (`web_urls.py`) | Depende de |
| --- | --- | --- | --- | --- |
| R01.01 | Relevamiento y seguimiento | L | `relevamientos` (28), `relevamiento_detalle` (42) | setup compartido `api/web/comedores/` |
| R01.02 | Captura y edición de datos | M | POST de `relevamientos` (28), `relevamiento_eliminar` (63), `relevamiento_revision_coordinador` (84); `relevamiento_crear` (35) y `relevamiento_editar` (56) quedan nativas (D2) | R01.01 |
| R01.03 | Documentos y descargas | F | `relevamiento_pdf` (49) como GET nativo enlazado | R01.01 |
| R02.01 | Consulta de actas | L | `acta_complementaria_detalle` (157) | R01.01 (el listado de actas vive en la pantalla de R01.01) |
| R02.02 | Operaciones y evidencias del acta | W | `acta_complementaria_crear` (150), `acta_complementaria_editar` (164), `acta_complementaria_revision_coordinador` (171), `acta_complementaria_eliminar` (178) | R02.01 |
| R03.01 | Seguimientos y PNUD | L | `seguimiento_detalle` (92), `primer_seguimiento_detalle` (70, alias histórico), `seguimiento_pnud_detalle` (128); enlaces GET nativos `seguimiento_pdf` (106) y `seguimiento_pnud_pdf` (142) | R01.01 |
| R03.02 | Acciones y estados asociados | W | `seguimiento_editar` (99), `seguimiento_eliminar` (113), `primer_seguimiento_eliminar` (77, alias histórico), `seguimiento_revision_coordinador` (120), `seguimiento_pnud_revision_coordinador` (135) | R03.01 |

Orden recomendado: R01.01 → R01.03 → R03.01 → R02.01 → R01.02 → R03.02 → R02.02. Las rutas 70 y 77 figuran en
el catálogo bajo R01, pero usan las mismas vistas que 92 y 113; se asignan a R03 (decisión D1).

### Montaje real de las rutas

- `src/backends/comedores/comedores_runtime/urls.py:16` incluye `path("", include("relevamientos.urls"))` en el runtime
  `backend_comedores`. `relevamientos.urls` resuelve al paquete `relevamientos/urls/__init__.py:1-4`
  (`api_urlpatterns + web_urlpatterns`); el módulo `relevamientos/urls.py:1-9`, que incluye los mismos dos archivos,
  queda sombreado por el paquete (regla de importación de Python: el directorio con `__init__.py` gana). No se toca.
- `relevamientos/` no figura en `backends.json`; las rutas web se publican porque empiezan con `comedores/`
  (`src/backends/config/backends.json:257`) y las API GESTIONAR por `api/relevamiento` (`backends.json:275`).
  URL pública = `/comedores/<comedor_pk>/...` y `/api/relevamiento...`; el core las reenvía al runtime con
  5 s de conexión y 25 s de lectura (`src/backends/kernel/core/backend_proxy.py:47-49,248-258`).
- El prefijo nuevo `api/web/comedores/` en `backends.json`, su `include` en el agregador de URLs del runtime
  (`comedores_runtime/urls.py`) y la regeneración de `src/backends/config/url_registry.json` son setup compartido
  del padre. Este contrato propone montar `path("api/web/comedores/relevamientos/", include("relevamientos.web_api_urls"))`.

### Consumidores existentes que no cambian

- API GESTIONAR/app territorial (`urls/api_urls.py:13-38`, todas con `HasAPIKeyOrToken`):
  `PATCH /api/relevamiento` (`api_relevamiento`, `views/api_views.py:109,113`),
  `PATCH /api/relevamiento/primer-seguimiento` (`api_primer_seguimiento`, `api_views.py:197,281`),
  `PATCH /api/relevamiento/seguimiento` (`api_seguimiento`, `api_views.py:370`, hereda de la anterior),
  `POST /api/relevamiento/pdf-oficial` (`api_relevamiento_pdf_oficial`, `api_views.py:422,432`),
  `POST /api/relevamiento/seguimiento/pdf-oficial` (`api_seguimiento_pdf_oficial`, `api_views.py:454,465`).
  Aplican `_scope_relevamientos_for_authenticated_user` (`api_views.py:22-46`) y el 409 de `_validado_bloquea_edicion`
  (`api_views.py:49-70`). No se reutilizan como API web de React ni se modifican sus contratos.
- Popup de alta y reasignación de territorial: `POST /comedores/ajax/<int:pk>/relevamiento/`
  (`relevamiento_create_edit_ajax`, `src/backends/comedores/comedores/urls.py:416-419`,
  `comedores/views/relevamientos.py:267-300`), dueño CO07 (catálogo). Lo invocan los modales de
  `relevamiento_list.html:262-353` y `relevamiento_detail.html:147-186`.
- Autocompletado de territoriales: `GET /comedores/<id>/territoriales/` y `POST /comedores/<id>/territoriales/sincronizar/`
  (`relevamientos/static/custom/js/comedordetail_territorial_cache.js:307,347`).
- Ficha del comedor (CO07, `docs/plans/2026-T4/2026-10-28-2785-comedores-legajo-base-m2.md:51-52`): botón
  «Acompañamiento Territorial» a `relevamientos` (`comedores/templates/comedor/comedor_detail.html:28-31`) y datos de
  `relevamientos.0` en el legajo (`comedor_detail.html:395,928-1060`). Esa lectura es de CO07 y no cambia aquí.
- Señales: alta → `AsyncSendRelevamientoToGestionar` (`signals.py:15-21`); baja física o lógica de relevamiento →
  `AsyncRemoveRelevamientoToGestionar` (`signals.py:39-42`); baja de seguimiento con `gestionar_id` →
  `AsyncRemovePrimerSeguimientoToGestionar` (`signals.py:45-51`); auditoría de alta (`audit_signals.py:10-25`).
  Son hilos (`tasks.py:83,161,295`) que no bloquean la respuesta.

### Acceso común a todas las rutas nativas

- Cada ruta está envuelta por `permissions_any_required([...])` (`kernel/core/decorators.py:35-47`): superusuario pasa;
  si no, `iam.services.user_has_permission_code`. Sin sesión o sin permiso lanza `PermissionDenied` → **403**,
  antes de que `LoginRequiredMixin` de la vista pueda redirigir al login. Se conserva en las rutas nativas.
- Permisos literales usados: `relevamientos.view_relevamiento`, `relevamientos.add_relevamiento`,
  `relevamientos.change_relevamiento`, `relevamientos.delete_primerseguimiento`, `relevamientos.change_primerseguimiento`,
  `relevamientos.review_relevamiento` («Puede revisar y finalizar relevamientos», `models.py:1259-1261`),
  `relevamientos.add_actacomplementaria`, `relevamientos.change_actacomplementaria`, `relevamientos.delete_actacomplementaria`.
- Grupos semilla con `view_relevamiento` (`kernel/users/bootstrap/groups_seed.py:17-141`): «Tecnico Comedor»,
  «Abogado Dupla», «Area Contable», «Revisor Relevamientos» (además `review_relevamiento`, líneas 107-117) y
  «Area Legales». Nombres legacy en `kernel/core/permissions/registry.py:57-60`: «Comedores Relevamiento Ver»,
  «Comedores Relevamiento Crear», «Comedores Relevamiento Detalle», «Comedores Relevamiento Editar».
- Los botones de las plantillas usan `perms.relevamientos.*` (permisos Django), no el resolvedor IAM de la ruta.
- **Sin alcance de objeto por usuario**: ninguna vista web de la app filtra por comedores visibles del usuario
  (no hay llamadas a `ComedorService.get_scoped_comedor_or_404`; sí las usa el popup de CO07,
  `comedores/views/relevamientos.py:44-52`). El único filtro es el `comedor_pk` de la URL, y no en todas las vistas
  (ver cada entrega). Se conserva por paridad y se eleva como punto humano H1.

### Reglas comunes de la API web

- Archivos propuestos: `src/backends/comedores/relevamientos/web_api_urls.py`, `web_api_views.py`,
  `web_api_serializers.py` (+ `src/backends/comedores/tests/test_relevamientos_web_api.py`).
- Base de cada vista: `authentication_classes = [SessionAuthentication]`, `permission_classes = [WebGatePermission,
  IsAuthenticated]` (`kernel/core/web_gate.py:308-328`), `renderer_classes = [JSONRenderer]`,
  `Cache-Control: private, no-store` y `Vary: Cookie` como `sisoc_core/insumos/web_api_views.py:51-87,163-201`.
  En `initial()` se ejecuta el mismo decorador nativo `permissions_any_required(<códigos de la ruta nativa>)` sobre
  una función vacía (D6), así el permiso es idéntico y el anónimo recibe 401 del gate y no 403.
- Errores: 401 `{"detail": "Inicie sesión para continuar."}`, 403 `{"detail": ...}`, 404 `{"detail": ...}`,
  400 `{"errors": form.errors.get_json_data()}` o `{"errors": {"__all__": [{"message": ..., "code": ...}]}}`,
  409 `{"detail": <texto nativo>}`. Éxito de mutación: 200 `{"ok": true, "message": <texto nativo>, "redirect": <URL nativa>}`.
- Mutaciones: POST con `X-CSRFToken` (CSRF de `SessionAuthentication`), `FormParser`/`MultiPartParser` con los mismos
  nombres de campo que el POST nativo; sin reintento automático; un 504 `{"uncertain": true}` del proxy se muestra como
  «No se pudo confirmar el resultado.» con un botón para recargar el detalle por GET, nunca para reenviar.
- Ninguna operación de la API supera los 60 s de G1: todas son lecturas o escrituras de filas; las integraciones con
  GESTIONAR corren en hilos. Las descargas PDF no pasan por la API (D3, D4).

## R01.01 Relevamiento y seguimiento

### Rutas nativas

- GET `/comedores/<comedor_pk>/relevamiento/listar`, nombre `relevamientos` (`web_urls.py:28-34`, convertidor sin
  `int`), vista `RelevamientoListView` (`views/web_views.py:98-190`), plantilla `relevamiento_list.html:1-412`.
- GET `/comedores/<comedor_pk>/relevamiento/<int:pk>`, nombre `relevamiento_detalle` (`web_urls.py:42-48`), vista
  `RelevamientoDetailView` (`web_views.py:193-385`), plantillas `relevamiento_detail.html:1-352` y
  `relevamiento_detail_secciones.html:1-1235` (incluida en `relevamiento_detail.html:233`).

### Acceso

- Ambas: `relevamientos.view_relevamiento` + `LoginRequiredMixin`.
- Listado: relevamientos `filter(comedor=<comedor_pk>)`; comedor inexistente → 404 (`web_views.py:127-136`). Un
  `comedor_pk` no numérico no lo rechaza la URL (sin `int`) y falla al filtrar (incertidumbre U2).
- Detalle: `get_object_or_404(Relevamiento..., pk=pk)` (`web_views.py:337-385`) **ignora `comedor_pk`**: un relevamiento
  de otro comedor se ve con cualquier `comedor_pk`. Se conserva (H1). `Relevamiento.objects` excluye bajas lógicas
  (`kernel/core/soft_delete/base.py:90-91`) → relevamiento dado de baja = 404.

### Datos y reglas

- Listado, bloque «Acompañamiento Territorial» (`relevamiento_list.html:23-145`): relevamientos del comedor ordenados
  `-estado, -id`, sin paginación (`web_views.py:103-109`). Por relevamiento: `id`, `fecha` (`fecha_visita`),
  `estado` = `RelevamientoService.estado_para_mostrar(estado, estado_validacion)` (`service.py:656-670`: «Finalizado» o
  «Finalizado/Excepciones» con «Pendiente validación coordinador» se muestra «Pendiente de validación»), `numero_if`,
  `origen`, `sincronizado_gestionar`, `has_seguimiento`. Debajo, cada instancia de `seguimientos` ordenada por
  `numero_orden` (`web_views.py:144-178`): `id`, `fecha_hora`, `estado` (sin traducir), `tipo` (`get_tipo_display`:
  «Primer seguimiento», «Seguimiento posterior», «Seguimiento virtual», «Acta de excepción», `models.py:1797-1802`),
  `numero_orden`, `origen`, `sincronizado_gestionar`.
- Color del estado (`relevamiento_list.html:54`): «Pendiente» amarillo, «Visita pendiente» verde, resto blanco.
- Bloque «Actas complementarias extraordinarias» (`relevamiento_list.html:147-203`): `ActaComplementaria` del comedor
  en el orden del modelo `-fecha_hora, -id` (`models.py:2073`): `id`, `fecha_hora`, `tecnico`, `origen`,
  cantidad de `prestaciones`, `estado_validacion`.
- Bloque «Seguimientos PNUD» (`relevamiento_list.html:205-252`): `SeguimientoPnud` del comedor, orden `-fecha_hora, -id`
  (`models.py:2184`): `id`, `get_formulario_display` (seis opciones literales de `models.py:2145-2161`), `fecha_hora`,
  `tecnico`, `estado_validacion`, `asignado_desde_sisoc`, `origen`.
- Opciones de los modales según programa: `opciones_alta(comedor)` y `opciones_seguimiento_pac(comedor)`
  (`alta_backoffice.py:74-93`, `web_views.py:90-95,137-140`).
- Detalle: `pdf_oficial = documento_de(relevamiento=...)` (`pdf_oficial.py:112-114`), línea de tiempo de hasta tres
  relevamientos del comedor alrededor del actual con `card_class`/`status_class` (`web_views.py:206-259`),
  `relevamiento_data` con listas separadas por coma (`web_views.py:261-324`), `estado_visible`, `seguimientos`
  ordenados por `numero_orden` (`web_views.py:330-333`). `ejecucion_inicio`, `ejecucion_fin` y `plazo_ejecucion`
  no están en el contexto: la cabecera muestra siempre «-» (`relevamiento_detail.html:198-211`); se conserva.
- Secciones del detalle, en orden (`relevamiento_detail_secciones.html`): «Acompañamiento Territorial» (7),
  «Información» (37), «Datos del referente del Comedor/Merendero» (87), «Domicilio del Comedor/Merendero» (136),
  «Datos del responsable del acompañamiento territorial» (210), secciones de espacio (260) y personas (453),
  «Datos sobre recursos del Comedor/Merendero» (505), compras (609), «Datos sobre la prestacion alimentaria» (687),
  «Datos sobre el Anexo» (821), «Punto Entrega» (993), «Observacion» (1093), «Excepcion» (1112, adjuntos y firma),
  «Fotos» (1178, `relevamiento.imagenes`). Los textos sin tilde se conservan tal cual.
- Tabla «Ciclo de seguimiento» (`relevamiento_detail.html:234-311`): columnas «Tipo», «Fecha», «Estado», «Validación»,
  «Origen», «GESTIONAR», «Acciones».

### Acciones y efectos

- Solo lectura. El POST del listado pertenece a R01.02. Enlaces: detalle de relevamiento y de seguimiento, detalle de
  acta, editar acta (si `change_actacomplementaria`), alta de acta (si `add_actacomplementaria`), detalle PNUD,
  «Historial» (`audittrail:log_instance`, solo con `perms.auditlog.view_logentry`, `relevamiento_detail.html:79-82`).
- Modales del listado «Nuevo acompañamiento territorial» y «Agregar seguimiento» y el modal del detalle
  «Asignar territorial» se renderizan en React y envían un **POST de formulario nativo** a
  `/comedores/ajax/<id>/relevamiento/` con `csrfmiddlewaretoken` y los mismos campos (`tipo_relevamiento`,
  `territorial`, `relevamiento_id`, `territorial_editar`), igual que hoy (D5). El efecto y los mensajes son de CO07.

### API web del runtime

- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/` (`web_api_relevamientos_listado`), permiso
  `view_relevamiento`. 200:
  `{"comedor": {"id", "nombre", "provincia", "municipio", "localidad"}, "relevamientos": [{"id", "fecha", "estado",
  "numero_if", "origen", "sincronizado_gestionar", "has_seguimiento", "detalle_url", "seguimientos": [{"id", "fecha",
  "estado", "tipo", "numero_orden", "origen", "sincronizado_gestionar", "detalle_url"}]}], "actas": [{"id",
  "fecha_hora", "tecnico", "origen", "prestaciones_count", "estado_validacion", "detalle_url", "editar_url"}],
  "seguimientos_pnud": [{"id", "formulario_display", "fecha_hora", "tecnico", "estado_validacion",
  "asignado_desde_sisoc", "origen", "detalle_url"}], "opciones_alta": [{"value", "label"}],
  "opciones_seguimiento": [{"value", "label"}], "capabilities": {"add_relevamiento", "change_relevamiento",
  "add_actacomplementaria", "change_actacomplementaria"}, "alta_url": "/comedores/ajax/<id>/relevamiento/"}`.
  Fechas como texto con el mismo formato que la plantilla (`DATETIME_FORMAT` activo) y `null` cuando la plantilla
  muestra «Sin fecha»/«Sin información». 404 si el comedor no existe; 403 sin permiso; 401 sin sesión.
  El queryset y el armado de ítems se extraen de `RelevamientoListView.get_context_data` a una función compartida
  (`relevamientos_items(comedor_pk)`) que usan la vista nativa y la API (refactor chico, mismo resultado).
- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/<int:pk>/` (`web_api_relevamiento_detalle`),
  permiso `view_relevamiento`, búsqueda por `pk` solamente (paridad). 200: `{"relevamiento": {"id", "comedor":
  {"id", "nombre"}, "fecha_visita", "estado", "estado_visible", "estado_validacion", "esta_validado", "sin_cargar",
  "origen", "sincronizado_gestionar", "observaciones_coordinador", "coordinador", "fecha_revision_coordinador"},
  "timeline": [{"id", "step", "fecha", "estado", "card_class", "status_class"}], "secciones": [{"titulo",
  "filas": [{"etiqueta", "tipo": "texto|imagen|lista", "valor"}]}], "seguimientos": [{"id", "tipo", "numero_orden",
  "fecha_hora", "estado", "estado_validacion", "origen", "sincronizado_gestionar", "detalle_url", "editar_url",
  "eliminar_api"}], "pdf": {"disponible", "url", "oficial", "fecha_oficial"}, "capabilities": {"change_relevamiento",
  "review_relevamiento", "change_primerseguimiento", "delete_primerseguimiento", "view_logentry"},
  "historial_url"}`. `secciones` lo arma un presentador en `web_api_serializers.py` que replica, en orden y con las
  mismas etiquetas, `relevamiento_detail_secciones.html` (D8). 404 inexistente o dado de baja.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/relevamientos.tsx` + `relevamientos.test.tsx`; registrar `relevamientosRoute`
  en `ROUTES` de `routes/index.ts` antes de `businessRoute` y agregar los paths a `routes/index.test.ts`.
- Paths exactos: `^/comedores/([0-9]+)/relevamiento/listar$` y `^/comedores/([0-9]+)/relevamiento/([0-9]+)$`
  (sin barra final, como la URL nativa). Marco SISOC desde `identityFrames.tsx` (agregar `comedoresFrame` si no hay uno).
- Volver nativo: no hay botón «Volver»; la navegación es por migas «Comedores» (`/comedores/listar`, `url 'comedores'`)
  y el nombre del comedor (`/comedores/<id>`, `url 'comedor_detalle'`) en el detalle (`relevamiento_detail.html:35-48`).
  El listado no tiene migas (`relevamiento_list.html:12`).

### Criterios de aceptación

- Listado: título de pestaña «Acompañamiento Territorial - Comedor: <nombre>»; encabezado
  «<nombre> | <provincia>, <municipio>, <localidad>»; tarjetas «Acompañamiento Territorial» (botón «Agregar» solo con
  `add_relevamiento`), «Actas complementarias extraordinarias» (botón «Agregar» con `add_actacomplementaria`) y
  «Seguimientos PNUD». Fila de relevamiento «<id> - <fecha>» o «Sin fecha»; estado o «Sin información»; badges
  «Sincronizado»/«No sincronizado», «App»; «Número de IF:» con valor o «Sin número de IF»; botón «Actualizar IF» con
  `change_relevamiento`; botón «Agregar» por relevamiento si `add_relevamiento` y hay opciones de seguimiento.
  Fila hija con «└─», badge «<tipo> #<orden>», «App», «Sincronizado»/«No sincronizado», «Completado»/«No completado».
  Acta: «Sin técnico», «App»/«SISOC», «<n> prestación»/«<n> prestaciones», badge de validación, «Editar».
  Vacíos: «No hay actas complementarias cargadas para este comedor.» y «No hay seguimientos PNUD cargados para este
  comedor.»; el bloque de relevamientos sin ítems queda vacío, sin texto (paridad). PNUD: badge «Asignado» con title
  «Asignado desde SISOC, el territorial todavía no lo envió».
- Modales: «Nuevo acompañamiento territorial», «Tipo», «Territorial asignado», placeholder «Escribí el nombre del
  territorial», ayuda «El acompañamiento territorial se crea asignado al territorial seleccionado. Las opciones dependen
  del programa del comedor.», «Cancelar», «Crear acompañamiento territorial»; «Agregar seguimiento», «El seguimiento se
  agrega a este acompañamiento territorial y hereda su territorial asignado.», «Crear seguimiento».
- Detalle: título «<nombre> | Acompañamiento Territorial | <fecha> | <estado visible>», badges «Sincronizado con
  GESTIONAR», estado de validación, «App»; botones en orden «Reasignar territorial» (no finalizado y
  `change_relevamiento`), «Descargar PDF» (R01.03), «Ver seguimientos», «Revisar» (R01.02), «Historial», «Eliminar»
  (siempre visible, paridad con `relevamiento_detail.html:83-84`). Alerta «Observaciones del coordinador». Modal
  «Asignar territorial»: «Seleccionar territorial», «Al confirmar, el acompañamiento territorial pasará a estado Visita
  pendiente.», «Asignar». Cabecera «Inicio de Ejecución», «Final de Ejecución», «Plazo de Ejecución» con «-».
  Tabla «Ciclo de seguimiento» con «Ver», «Editar», «Eliminar» según permisos y badges «Completado», «SISOC», «App»,
  «Sincronizado»/«Pendiente».
- Paridad: estructura de tarjetas y orden de Tab igual al nativo (botones de cabecera, filas en orden, acciones por
  fila, modales con foco inicial en el primer control y retorno al disparador); regla visual S13: paridad estructural y
  diff perceptual <= 1 % sin antialiasing, tolerancia 2 CSS px, desktop y móvil.

### Casos de prueba

- Backend: permitido con `view_relevamiento`; 403 sin permiso; 401 anónimo; 404 comedor inexistente; detalle de otro
  comedor con `comedor_pk` ajeno responde 200 igual que la vista nativa (pin de paridad H1); relevamiento con baja
  lógica 404; `estado_visible` «Pendiente de validación»; orden `-estado,-id` e instancias por `numero_orden`;
  `capabilities` según `perms`; `secciones` con las mismas etiquetas que el HTML nativo renderizado (comparación de
  textos de `<h3>` y etiquetas sobre fixture completa).
- Frontend (vitest): render de listado con y sin ítems, vacíos de actas y PNUD, botones por capability, modal con POST
  nativo a la URL de CO07 y CSRF, detalle con y sin seguimientos, 403/401/404 con pantallas existentes.
- Diferencial: GET nativo de `relevamientos` y `relevamiento_detalle` antes y después devuelve el mismo status y HTML;
  `/api/relevamiento*` sin cambios.
- Visual: por URL × estado (vacío, con seguimientos, finalizado, validado, a subsanar) × rol (lector, revisor) ×
  viewport.

### Riesgos

- El presentador de `secciones` puede desalinearse de la plantilla de 1235 líneas, que sigue alimentando el PDF;
  mitigación: prueba de igualdad de etiquetas contra el render nativo.
- Sin alcance por usuario ni filtro por comedor en el detalle (H1).

## R01.02 Captura y edición de datos

### Rutas nativas

- POST `/comedores/<comedor_pk>/relevamiento/listar` (actualizar Número de IF), `RelevamientoListView.post`
  (`web_views.py:111-123`), formulario en `relevamiento_list.html:98-118`.
- GET y POST `/comedores/<comedor_pk>/relevamiento/<int:pk>/eliminar`, `relevamiento_eliminar`
  (`web_urls.py:63-69`), `RelevamientoDeleteView` (`web_views.py:496-509`) con `SoftDeleteDeleteViewMixin`
  (`kernel/core/soft_delete/view_helpers.py:90-118`), plantilla `relevamiento_confirm_delete.html:1-24` +
  `kernel/templates/components/delete_confirm.html`.
- POST `/comedores/<int:comedor_pk>/relevamiento/<int:pk>/revision`, `relevamiento_revision_coordinador`
  (`web_urls.py:84-90`), `RelevamientoRevisionCoordinadorView` (`web_views.py:632-667`), modal en
  `relevamiento_detail.html:98-146`.
- Quedan nativas sin React (D2): GET/POST `/comedores/<comedor_pk>/relevamiento/crear` (`relevamiento_crear`,
  `web_urls.py:35-41`, `RelevamientoCreateView` `web_views.py:42-87`) y `/comedores/<comedor_pk>/relevamiento/<int:pk>/editar`
  (`relevamiento_editar`, `web_urls.py:56-62`, `RelevamientoUpdateView` `web_views.py:433-493`), plantilla
  `relevamiento_form.html:1-441`.

### Acceso

- Número de IF: ruta `view_relevamiento` y además `request.user.has_perm("relevamientos.change_relevamiento")`
  (permiso Django, `web_views.py:112`). Filtra `id=relevamiento_id, comedor_id=comedor_pk`.
- Eliminar: ruta `change_relevamiento` (no `delete_*`); el botón «Eliminar» se muestra a todos (asimetría conservada).
  `DeleteView.get_object` busca por `pk` sin `comedor_pk`.
- Revisión: `review_relevamiento`; `select_for_update` por `pk` y `comedor_id` (`web_views.py:645-647`). El botón y el
  modal solo con `review_relevamiento`, no validado y no `sin_cargar` (`relevamiento_detail.html:73,98`).

### Datos y reglas

- Número de IF: `relevamiento_id` (texto, sin validar), `numero_if` strip; vacío → `NULL`. Modelo `CharField`
  «Número de IF» `max_length=255`, `null/blank` (`models.py:1169-1174`); el input HTML tiene `maxlength="255"`.
- Eliminar: confirmación con vista previa de cascada (`build_delete_preview`), `confirm_text` «Dar de baja».
- Revisión (`views/seguimiento_helpers.py:63-113`): campos `estado_validacion` ∈ {«Validado», «A subsanar»} y
  `observaciones_coordinador` (strip). Reglas en orden: validado → «El acompañamiento territorial ya está validado: no
  admite otra revisión.»; `sin_cargar` (`models.py:1224-1235`) → «Todavía no hay nada que revisar en el acompañamiento
  territorial: falta la carga del territorial desde la app.»; estado inválido → «Seleccione un resultado de revisión
  válido.»; «A subsanar» sin observaciones → «Para devolver el acompañamiento territorial debe indicar qué corregir.».
- Crear/editar (nativo, referencia): `RelevamientoForm` (`form.py:407-471`) + 11 formularios de
  `RelevamientoFormManager.FORM_CLASSES` (`helpers.py:25-37`).

### Acciones y efectos

- Número de IF: `Relevamiento.objects.filter(...).update(numero_if=...)` sin `save()`, sin señales ni auditoría; mensaje
  «Número de IF actualizado correctamente.» aunque no se actualice ninguna fila; sin permiso «No tiene permisos para
  editar el Número de IF.»; redirect a `relevamientos`.
- Eliminar: `instance.delete(user=request.user, cascade=True)` (baja lógica en cascada); señal `post_soft_delete` →
  baja en GESTIONAR (`signals.py:39-42`); mensaje «Acompañamiento Territorial dado de baja correctamente.»; redirect a
  `comedor_detalle` del comedor del objeto (`web_views.py:506-509`).
- Revisión: transacción con bloqueo de fila; guarda `estado_validacion`, `observaciones_coordinador` (vacío → `NULL`),
  `coordinador`, `fecha_revision_coordinador` con `update_fields`; mensajes «Acompañamiento Territorial validado
  correctamente.» o «Acompañamiento Territorial devuelto al territorial para subsanar.»; error como `messages.error`;
  siempre redirect a `relevamiento_detalle`.

### API web del runtime

- POST `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/numero-if/`: request `relevamiento_id`,
  `numero_if`. Permiso de ruta `view_relevamiento`; sin `has_perm(change_relevamiento)` → 403 `{"detail": "No tiene
  permisos para editar el Número de IF."}`. `numero_if` de más de 255 caracteres → 400 con el error de `max_length` del
  campo del modelo (D11). 200 `{"ok": true, "message": "Número de IF actualizado correctamente.", "redirect":
  "/comedores/<id>/relevamiento/listar", "numero_if": <valor|null>}` con el mismo `update()` nativo.
- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/<int:pk>/eliminar/`: permiso
  `change_relevamiento`; 200 `{"id", "nombre": str(relevamiento), "cascade_preview": build_delete_preview(obj),
  "confirm_text": "Dar de baja", "cancel_text": "Cancelar", "cancel_url": "/comedores/<id>/relevamiento/<pk>"}`; 404.
- POST misma ruta: baja con `SoftDeleteDeleteViewMixin._soft_delete_instance`; 200 `{"ok", "message":
  "Acompañamiento Territorial dado de baja correctamente.", "redirect": "/comedores/<comedor_del_objeto>"}`; repetido →
  404 (ya excluido por el manager).
- POST `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/<int:pk>/revision/`: permiso
  `review_relevamiento`; misma transacción y `aplicar_revision_coordinador`; 200 con el mensaje de éxito y
  `redirect` al detalle; 409 para «ya está validado» y «Todavía no hay nada que revisar…»; 400 para «Seleccione un
  resultado de revisión válido.» y «Para devolver… debe indicar qué corregir.» (D10); 404 si no coincide `comedor_id`.

### Módulo React

- Mismo módulo `relevamientos.tsx`; agrega el path `^/comedores/([0-9]+)/relevamiento/([0-9]+)/eliminar$`.
- No registra `/relevamiento/crear` ni `/relevamiento/<pk>/editar`: el match devuelve `null` y la vista nativa sigue
  atendiendo esas URLs (D2).
- Volver nativo: «Cancelar» de la baja a `/comedores/<id>/relevamiento/<pk>` (`relevamiento_confirm_delete.html:22-23`);
  migas «Comedores», comedor, «Acompañamiento Territorial <fecha>», «Eliminar».

### Criterios de aceptación

- Edición de IF en línea: «Número de IF», «Guardar», «Cancelar», foco en el input al abrir; toast de éxito o error con
  el texto literal.
- Baja: título de pestaña «Acompañamiento Territorial - <id>»; «Atención!», «¿Estás seguro que deseas realizar una baja
  lógica en cascada del registro <NOMBRE EN MAYÚSCULAS>?», «Total de registros afectados:», «Bajas lógicas:»,
  «Borrados físicos técnicos:», tabla «Modelo», «Cantidad», «Acción», «Ejemplos» con «Baja lógica»/«Borrado físico
  técnico», botones «Dar de baja» y «Cancelar».
- Modal de revisión: «Revisión del coordinador», «Resultado», «Seleccionar resultado», «Validado», «A subsanar
  (devolver al territorial)», «Observaciones», placeholder «Qué debe corregir el territorial (obligatorio si devuelve
  el acompañamiento territorial)», «Si valida, el territorial ya no podrá modificar el acompañamiento territorial desde
  la app.», «Cancelar», «Guardar revisión».
- Paridad estructural, orden de Tab y regla visual S13.

### Casos de prueba

- Backend: IF con y sin `change_relevamiento`, vacío a `NULL`, id de otro comedor (200 y sin cambio, paridad), 256
  caracteres → 400, CSRF faltante → 403, anónimo 401; baja con permiso, sin permiso 403, repetida 404, señal de baja
  simulada (sin red), redirect al comedor del objeto; revisión: validar, devolver sin observaciones 400, validado 409,
  `sin_cargar` 409, estado inválido 400, comedor ajeno 404, `coordinador` y fecha guardados.
- Frontend: edición en línea, confirmación de baja con preview, modal de revisión, 504 `uncertain` sin reenvío.
- Diferencial: POST nativos de IF, baja y revisión con mismas entradas producen mismos efectos y redirects; GET nativo
  de crear/editar sin cambios.
- Visual: confirmación de baja con y sin preview; modal de revisión.

### Riesgos

- El POST de IF hace `update()` sin auditoría y confirma aunque no exista el id (paridad).
- La baja exige `change_relevamiento`, no `delete_relevamiento` (paridad).

## R01.03 Documentos y descargas

### Rutas nativas

- GET `/comedores/<comedor_pk>/relevamiento/<int:pk>/pdf`, `relevamiento_pdf` (`web_urls.py:49-55`),
  `RelevamientoPdfView` (`web_views.py:394-430`), plantilla `relevamiento_pdf.html:1-92` (incluye
  `relevamiento_detail_secciones.html:90`) y `relevamiento_imagen.html:1-16`.

### Acceso

- `view_relevamiento` + login; búsqueda por `pk` sin `comedor_pk` (hereda `get_object` del detalle).
- El botón solo aparece con estado «Finalizado» o «Finalizado/Excepciones» (`relevamiento_detail.html:63-68`); la ruta
  no valida el estado (asimetría conservada).

### Datos y reglas

- Si existe `PdfOficialGestionar` del relevamiento se sirve ese PDF; si no, SISOC arma el suyo con weasyprint
  (`pdf_service.py:113-120`) y `RecursosLocalesURLFetcher` (sin red). El PDF oficial se convierte la primera vez y se
  guarda en `pdf` (`pdf_oficial.py:97-109`); el de SISOC se genera en cada descarga.

### Acciones y efectos

- Respuesta `application/pdf`, `Content-Disposition: attachment; filename="relevamiento-<id>.pdf"` en ambos caminos
  (`web_views.py:388-391,416-430`). Única escritura: cache del PDF oficial con control por `fecha_actualizacion`.
- Productor: `POST /api/relevamiento/pdf-oficial` de GESTIONAR (consumidor existente, sin cambios); valida HTML
  UTF-8 con `<!doctype html` y hasta 20 MB (`pdf_oficial.py:27,35-54`).

### Exportaciones

- Solo el PDF anterior. No hay XLSX ni exportación de listado en esta app.

### API web del runtime

- Sin endpoint nuevo: el detalle de R01.01 expone `pdf: {"disponible": estado finalizado, "url":
  "/comedores/<id>/relevamiento/<pk>/pdf", "oficial": bool, "fecha_oficial": "d/m/Y H:i"|null}`. La descarga sigue
  siendo el GET nativo (D3).

### Módulo React

- En `relevamientos.tsx`: `<a href>` nativo al PDF, sin `fetch`, sin `download` forzado y sin reintento.

### Criterios de aceptación

- «Descargar PDF» (oculto en pantallas chicas como el nativo `d-none d-sm-inline`), con title «Formato oficial de
  Gestionar, enviado el <d/m/Y H:i>» y texto «Formato oficial de Gestionar» cuando hay PDF oficial.

### Casos de prueba

- Backend existente: `src/backends/comedores/tests/test_relevamiento_pdf_2630.py`; agregar: `pdf` del detalle con y sin
  oficial, `disponible` falso si no finalizado.
- Frontend: enlace presente o ausente según estado; href exacto.
- Diferencial: GET nativo del PDF devuelve el mismo content-type y nombre.
- Visual: botón con y sin leyenda de formato oficial.

### Riesgos

- weasyprint sobre un HTML oficial de hasta 20 MB puede superar los 25 s de lectura del proxy para rutas nativas
  (`backend_proxy.py:49`); es el comportamiento actual y no cambia (D4).

## R02.01 Consulta de actas

### Rutas nativas

- GET `/comedores/<int:comedor_pk>/acta-complementaria/<int:pk>`, `acta_complementaria_detalle` (`web_urls.py:157-163`),
  `ActaComplementariaDetailView` (`views/backoffice_views.py:184-200`), plantilla `acta_complementaria_detail.html:1-220`.

### Acceso

- Ruta `view_relevamiento` (no hay permiso `view_actacomplementaria` en la ruta) + login. Queryset
  `filter(comedor_id=comedor_pk)` → acta de otro comedor 404.

### Datos y reglas

- `id`, `fecha_hora`, `tecnico`, `fecha_creacion`, `observaciones` («Motivo / observaciones del cambio de prestación»),
  `origen`, `estado_validacion`, `observaciones_coordinador`, `coordinador.username`, `fecha_revision_coordinador`,
  `esta_validado`, `sin_cargar` (`models.py:2042-2095`). Prestaciones: `dias_prestacion`, `tipo_prestacion`,
  `cantidad_actual`, `cantidad_espera` (`models.py:2098-2116`), `-` si nulo.

### Acciones y efectos

- Solo lectura; enlaces a editar, revisar y eliminar (R02.02).

### API web del runtime

- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/actas/<int:pk>/` (`web_api_acta_detalle`), permiso
  `view_relevamiento`; 200 `{"acta": {"id", "comedor": {"id", "nombre"}, "fecha_hora", "tecnico", "fecha_creacion",
  "observaciones", "origen", "estado_validacion", "esta_validado", "sin_cargar", "observaciones_coordinador",
  "coordinador", "fecha_revision_coordinador"}, "prestaciones": [{"dias_prestacion", "tipo_prestacion",
  "cantidad_actual", "cantidad_espera"}], "capabilities": {"change_actacomplementaria", "review_relevamiento",
  "delete_actacomplementaria"}}`; 404 acta ajena o inexistente.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/actasComplementarias.tsx` + test; registrar `actasComplementariasRoute` en `ROUTES`
  antes de `businessRoute`; path `^/comedores/([0-9]+)/acta-complementaria/([0-9]+)$`.
- Volver nativo: migas «Comedores», comedor, «Acompañamiento Territorial» (`/comedores/<id>/relevamiento/listar`),
  «Acta complementaria» (`acta_complementaria_detail.html:22-33`).

### Criterios de aceptación

- Pestaña «Acta complementaria - Comedor: <nombre>»; título «<nombre> | Acta complementaria extraordinaria | <fecha o
  Sin fecha>»; badges «App» o «SISOC» y validación; botones «Editar», «Revisar», «Eliminar» según permisos y estado;
  «Observaciones del coordinador»; «Resumen» con «ID SISOC», «Fecha y hora», «Técnico» («Sin asignar»), «Cargada el»,
  «Motivo / observaciones del cambio de prestación» («Sin observaciones»); «Prestaciones» con «Días», «Tipo»,
  «Cantidad actual», «Cantidad en espera»; vacío «El acta no tiene prestaciones cargadas.».
- Paridad estructural, orden de Tab y regla visual S13.

### Casos de prueba

- Backend: permitido, 403, 401, acta de otro comedor 404, `sin_cargar` según contenido, prestaciones vacías.
- Frontend: botones por capability, vacío, observaciones.
- Diferencial: GET nativo sin cambios. Visual: acta app/SISOC, validada, a subsanar, sin prestaciones.

### Riesgos

- Ver un acta solo exige `view_relevamiento` (paridad).

## R02.02 Operaciones y evidencias del acta

### Rutas nativas

- GET/POST `/comedores/<int:comedor_pk>/acta-complementaria/crear` (`acta_complementaria_crear`, `web_urls.py:150-156`) y
  `/comedores/<int:comedor_pk>/acta-complementaria/<int:pk>/editar` (`acta_complementaria_editar`, `web_urls.py:164-170`),
  `ActaComplementariaFormView` (`backoffice_views.py:241-283`), plantilla `acta_complementaria_form.html:1-106`.
- POST `/comedores/<int:comedor_pk>/acta-complementaria/<int:pk>/revision` (`web_urls.py:171-177`,
  `backoffice_views.py:203-238`).
- POST `/comedores/<int:comedor_pk>/acta-complementaria/<int:pk>/eliminar` (`web_urls.py:178-184`,
  `backoffice_views.py:286-295`), modal en `acta_complementaria_detail.html:189-218`.

### Acceso

- Crear `add_actacomplementaria`; editar `change_actacomplementaria`; revisar `review_relevamiento`; eliminar
  `delete_actacomplementaria`. Comedor `get_object_or_404(Comedor, pk)`, acta por `pk` y `comedor` (404 ajena).
- La edición no verifica `estado_validacion`: se puede editar un acta validada desde el backoffice (paridad).

### Datos y reglas

- `ActaComplementariaForm` prefijo `acta` (`forms_backoffice.py:181-201`): `fecha_hora` (`datetime-local`, formato
  `%Y-%m-%dT%H:%M`, opcional), `tecnico` (opcional, label «Técnico territorial», usuarios activos con
  `profile__es_territorial_comedor=True` por `username`, ayuda «Si se deja vacío queda registrado el usuario que carga el
  acta.»), `observaciones` (textarea 4 filas, opcional).
- `PrestacionActaFormSet` prefijo `prestaciones` (`forms_backoffice.py:204-211`): `dias_prestacion`, `tipo_prestacion`
  (texto 255 opcional), `cantidad_actual`, `cantidad_espera` (enteros positivos opcionales), `extra=1`,
  `can_delete=True`, con management form.
- Revisión: igual que R01.02 con etiqueta «el acta complementaria» y mensaje de validado «El acta complementaria ya
  está validada: no admite otra revisión.»; `sin_cargar` en `models.py:2079-2095`.

### Acciones y efectos

- Guardar (`forms_backoffice.py:214-236`): transacción; si no hay técnico, el usuario actual; guarda acta y formset;
  `origen` toma el default `sisoc` (`models.py:114-118`). Mensajes «Acta complementaria guardada correctamente.» →
  detalle; inválido «Revise los campos marcados en rojo.» y re-render.
- Revisión: bloqueo de fila; «Acta complementaria validada correctamente.» o «Acta complementaria devuelta al
  territorial para subsanar.»; redirect al detalle.
- Eliminar: borrado físico, cascada de prestaciones; «Acta complementaria eliminada correctamente.»; redirect a
  `relevamientos`. Sin señal GESTIONAR ni auditoría propia.
- Evidencias: el campo `firma` (URL, 600) lo carga la app; el backoffice no sube archivos (ver U5).

### API web del runtime

- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/actas/crear/` y `.../actas/<int:pk>/editar/`: 200
  `{"form": <descriptor>, "prestaciones": <descriptor de formset>, "comedor": {"id", "nombre"}, "acta_id"|null}`.
  Descriptor (D7): por campo `{"name" (con prefijo), "label", "widget", "required", "value", "choices"?, "help_text",
  "errors"}`; formset `{"management": {"TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS"},
  "forms": [[campos]], "non_form_errors"}`.
- POST mismas rutas con los mismos nombres del POST nativo (`acta-*`, `prestaciones-*`); 200 `{"ok", "message":
  "Acta complementaria guardada correctamente.", "redirect": "/comedores/<id>/acta-complementaria/<pk>"}`; 400 con el
  descriptor ligado (errores por campo) y `detail: "Revise los campos marcados en rojo."`.
- POST `.../actas/<int:pk>/revision/` (códigos como R01.02) y POST `.../actas/<int:pk>/eliminar/` (200 con
  «Acta complementaria eliminada correctamente.» y `redirect` al listado; repetido 404).

### Módulo React

- `actasComplementarias.tsx`: paths `^/comedores/([0-9]+)/acta-complementaria/crear$` y
  `^/comedores/([0-9]+)/acta-complementaria/([0-9]+)/editar$`.
- Volver nativo: «Cancelar» a `/comedores/<id>/relevamiento/listar` (`acta_complementaria_form.html:102`).

### Criterios de aceptación

- Pestaña «Nueva acta complementaria - Comedor: <nombre>» o «Editar acta complementaria - Comedor: <nombre>»; título
  «<nombre> | Nueva acta complementaria extraordinaria» o «Editar …»; tarjeta «Datos del acta» con «Registra, fuera del
  ciclo de visitas, un cambio en la prestación del comedor.»; «Prestaciones (día × tipo)» con «Días», «Tipo», «Cantidad
  actual», «Cantidad en espera», «Eliminar» y «La última fila vacía permite agregar una prestación. Guarde y vuelva a
  editar para agregar más.»; botones «Cancelar» y «Guardar».
- Modal de baja: «Eliminar acta complementaria», «Esta acción elimina el acta y sus prestaciones.», «No se puede
  deshacer.», «Cancelar», «Eliminar». Modal de revisión con placeholder «Qué debe corregir el territorial (obligatorio si
  devuelve el acta)».
- Paridad estructural, orden de Tab y regla visual S13.

### Casos de prueba

- Backend: alta sin técnico asigna usuario; con técnico no territorial 400; cantidades negativas 400; borrar fila de
  formset; edición de acta ajena 404; permisos 403/401; CSRF; revisión validada 409; eliminar y repetir 404.
  Existentes: `test_acta_complementaria_validacion.py`, `test_backoffice_seguimientos_actas.py`,
  `test_popup_acta_complementaria.py`, `test_territorial_actas_sin_cargar.py`.
- Frontend: render del descriptor, errores por campo, formset con fila extra, 504 sin reenvío.
- Diferencial: POST nativo con los mismos datos produce el mismo acta y prestaciones.
- Visual: alta vacía, edición con errores, modal de baja.

### Riesgos

- Borrado físico irreversible (paridad). El selector de técnico puede ser largo; se conserva sin paginación.

## R03.01 Seguimientos y PNUD

### Rutas nativas

- GET `/comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimiento/<int:pk>/` (`seguimiento_detalle`,
  `web_urls.py:92-98`) y alias histórico GET `/comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/primer-seguimiento/`
  (`primer_seguimiento_detalle`, `web_urls.py:70-76`), ambos `PrimerSeguimientoDetailView` (`web_views.py:570-610`),
  plantilla `primer_seguimiento_detail.html:1-272`.
- GET `/comedores/<int:comedor_pk>/seguimiento-pnud/<int:pk>` (`seguimiento_pnud_detalle`, `web_urls.py:128-134`),
  `SeguimientoPnudDetailView` (`backoffice_views.py:108-127`), plantilla `seguimiento_pnud_detail.html:1-194`.
- Enlaces GET nativos: `/comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimiento/<int:pk>/pdf`
  (`seguimiento_pdf`, `web_urls.py:106-112`, `SeguimientoPdfView` `web_views.py:613-629`) y
  `/comedores/<int:comedor_pk>/seguimiento-pnud/<int:pk>/pdf` (`seguimiento_pnud_pdf`, `web_urls.py:142-148`,
  `SeguimientoPnudPdfView` `backoffice_views.py:130-149`).

### Acceso

- Todas `view_relevamiento` + login. Seguimiento resuelto por `resolver_seguimiento` (`seguimiento_helpers.py:42-60`):
  filtra `id_relevamiento_id` y `id_relevamiento__comedor_id`; sin `pk` toma la primera instancia por
  `numero_orden, id` o 404 «El relevamiento no tiene seguimientos.». PNUD filtra `comedor_id`.
- PDF de seguimiento: 404 sin PDF oficial. PDF PNUD: solo `formulario="siph"`, otro formulario 404.

### Datos y reglas

- Seguimiento: `tipo`, `numero_orden`, `fecha_hora`, `estado` («Asignado», «En Proceso», «Completo»), validación,
  `origen`, `sincronizado_gestionar`, `gestionar_id`, `tecnico`, `referente`, `motivo_diferencia_aprobado_declarado`
  (`models.py:1781-1953`); instancias del ciclo; bloques de `BLOQUES_SEGUIMIENTO` (`models.py:1760-1778`) con filas
  `label`/`value`/`es_imagen` de `_bloque_campos` (`web_views.py:516-567`: omite vacíos, `id_*` y OneToOne; booleanos
  «Sí»/«No»; choices con display); prestaciones (`models.py:1980-1992`) e ítems de receta del menú
  (`models.py:2004-2013`).
- PNUD: `formulario` display, `fecha_hora`, `tecnico`, `fecha_creacion`, encabezado `titulos(formulario)` (`linea`,
  `titulo`) y `secciones` de `respuestas_por_seccion` (`pnud_formularios.py:137-174`: `{titulo, filas: [{etiqueta,
  tipo: texto|imagen|tabla, valor|columnas+filas}]}`, más «Otros datos»).

### Acciones y efectos

- Solo lectura. PDFs: `application/pdf`, attachment `seguimiento-<id>.pdf` (oficial cacheado) y
  `seguimiento-siph-<pk>.pdf` (LibreOffice headless, `timeout=120`, `siph_docx.py:249-282`, sin cache).

### API web del runtime

- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimientos/<int:pk>/` y
  GET `.../seguimientos/primero/` (alias): permiso `view_relevamiento`; misma resolución; 200 `{"seguimiento": {"id",
  "tipo", "tipo_display", "numero_orden", "fecha_hora", "estado", "estado_validacion", "esta_validado", "sin_cargar",
  "origen", "sincronizado_gestionar", "gestionar_id", "tecnico", "referente", "motivo_diferencia_aprobado_declarado",
  "observaciones_coordinador", "coordinador", "fecha_revision_coordinador"}, "relevamiento": {"id", "fecha_visita"},
  "comedor": {"id", "nombre"}, "instancias": [{"id", "numero_orden", "tipo_display", "detalle_url"}], "bloques":
  [{"key", "label", "campos": [{"label", "value", "es_imagen"}]}], "prestaciones": [...], "receta_items": [...],
  "pdf": {"url"|null, "fecha_oficial"}, "capabilities": {"change_primerseguimiento", "review_relevamiento",
  "delete_primerseguimiento"}}`. Reutiliza `_bloque_campos` y `seguimiento_queryset`. 404 como la vista nativa.
- GET `/api/web/comedores/relevamientos/<int:comedor_pk>/pnud/<int:pk>/`: 200 `{"seguimiento": {...,
  "formulario", "formulario_display"}, "encabezado_formulario": {"linea", "titulo"}, "secciones": <respuestas_por_seccion>,
  "pdf_url": "/comedores/<id>/seguimiento-pnud/<pk>/pdf"|null, "capabilities": {"review_relevamiento"}}`; `pdf_url` solo
  si `formulario == "siph"`. Las URLs de imagen se exponen solo si `_es_url_mostrable` ya las aceptó.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/seguimientos.tsx` + test; `seguimientosRoute` en `ROUTES` antes de
  `businessRoute`; paths `^/comedores/([0-9]+)/relevamiento/([0-9]+)/seguimiento/([0-9]+)/$`,
  `^/comedores/([0-9]+)/relevamiento/([0-9]+)/primer-seguimiento/$`, `^/comedores/([0-9]+)/seguimiento-pnud/([0-9]+)$`.
- Volver nativo: migas «Comedores», comedor, «Acompañamiento Territorial <fecha>» (al detalle del relevamiento) y tipo
  (`primer_seguimiento_detail.html:33-46`); PNUD: «Acompañamiento Territorial» al listado y «Seguimiento PNUD».

### Criterios de aceptación

- Seguimiento: pestaña «<tipo> - Comedor: <nombre>»; título «<nombre> | <tipo> #<orden> | <fecha o Sin información> |»;
  badges «Completado»/«No completado», validación, «App», «Sincronizado con GESTIONAR»/«Pendiente sincronización»;
  grupo de instancias «#<orden> <tipo>» si hay más de una; «Descargar PDF» o «El PDF se genera cuando el territorial lo
  envía desde Gestionar.»; «Editar», «Revisar»; «Resumen» con «ID SISOC», «ID GESTIONAR», «Técnico», «Referente»
  («Sin asignar») y «Motivo de la diferencia entre lo aprobado y lo declarado»; vacío «Todavía no se cargaron bloques
  para este seguimiento.»; «Prestaciones» («Días», «Tipo», «AP presencial», «AP vianda», «DE presencial», «DE vianda»);
  «Items de receta del menú» («Ingrediente», «Unidad de medida», «Cantidad»).
- PNUD: pestaña «Seguimiento PNUD - Comedor: <nombre>»; título «<nombre> | <formulario> | <fecha o Sin fecha>»;
  «Descargar PDF» solo SIPH; «Revisar»; «Resumen» con «ID SISOC», «Fecha y hora», «Técnico» («Sin técnico»), «Cargado
  el»; secciones con tablas e imágenes; vacío «El seguimiento no tiene respuestas cargadas.».
- Paridad estructural, orden de Tab y regla visual S13.

### Casos de prueba

- Backend: alias sin seguimientos 404; seguimiento de otro relevamiento o comedor 404; bloques vacíos omitidos; firma
  como imagen; PNUD de otro comedor 404; SIPH con `pdf_url`, otros sin; permisos 403/401.
  Existentes: `test_detalle_seguimiento_2643.py`, `test_instancias_seguimiento_n14.py`, `test_seguimientos_pnud_n22.py`,
  `test_seguimiento_siph_2651.py`, `test_primer_seguimiento_relevamientos.py`.
- Frontend: navegación entre instancias, enlace PDF o leyenda, tablas PNUD.
- Diferencial: GET nativos de detalle y PDF sin cambios. Visual: seguimiento completo, sin bloques, PNUD SIPH y no SIPH.

### Riesgos

- La conversión SIPH (hasta 120 s internos) puede exceder los 25 s del proxy nativo (D4, preexistente).
- No unificar variantes PAC y PNUD ni sus etapas (riesgo del catálogo): son vistas, modelos y endpoints separados.

## R03.02 Acciones y estados asociados

### Rutas nativas

- GET/POST `/comedores/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimiento/<int:pk>/editar`
  (`seguimiento_editar`, `web_urls.py:99-105`), `SeguimientoUpdateView` (`backoffice_views.py:48-75`), plantilla
  `seguimiento_form.html:1-131`.
- POST `.../seguimiento/<int:pk>/eliminar` (`seguimiento_eliminar`, `web_urls.py:113-119`) y alias POST
  `.../primer-seguimiento/eliminar` (`primer_seguimiento_eliminar`, `web_urls.py:77-83`), `PrimerSeguimientoEliminarView`
  (`web_views.py:670-692`, solo POST), modal en `relevamiento_detail.html:312-350`.
- POST `.../seguimiento/<int:pk>/revision` (`web_urls.py:120-126`, `backoffice_views.py:78-98`).
- POST `/comedores/<int:comedor_pk>/seguimiento-pnud/<int:pk>/revision` (`web_urls.py:135-141`,
  `backoffice_views.py:152-181`).

### Acceso

- Editar `change_primerseguimiento`; eliminar `delete_primerseguimiento`; revisiones `review_relevamiento`. Resolución
  por `resolver_seguimiento` (seguimiento) o `pk`+`comedor_id` con `select_for_update` (PNUD).
- La edición no bloquea seguimientos validados (paridad).

### Datos y reglas

- `SeguimientoEditor` (`forms_backoffice.py:119-173`): `SeguimientoRootForm` prefijo `seg` con `fecha_hora`
  (`datetime-local`), `estado` (choices del modelo), `tecnico` (texto 255), `motivo_diferencia_aprobado_declarado`;
  `referente` excluido; un `ModelForm` `__all__` por bloque con prefijo = clave del bloque; `PrestacionSeguimientoFormSet`
  prefijo `prestaciones` (`dias_prestacion`, `tipo_prestacion`, `ap_presencial`, `ap_vianda`, `de_presencial`,
  `de_vianda`, `extra=1`, `can_delete=True`). Un bloque inexistente solo se valida y crea si tiene datos
  (`_bloque_con_datos`, valores vacíos `None`, `""`, `"unknown"`).
- Revisión seguimiento: etiqueta «el seguimiento»; PNUD: «el seguimiento PNUD» y `sin_cargar` = sin validación y sin
  `datos` (`models.py:2190-2195`).

### Acciones y efectos

- Editar: transacción, guarda raíz, bloques y prestaciones; «Seguimiento actualizado correctamente.» → detalle;
  inválido «Revise los campos marcados en rojo.».
- Eliminar: `seguimiento.delete()` borra bloques (`models.py:1955-1965`), prestaciones e ítems por cascada y el PDF
  oficial (`models.py:2216-2222`); señal de baja a GESTIONAR si hay `gestionar_id`; «Seguimiento eliminado
  correctamente.» → detalle del relevamiento.
- Revisión seguimiento: «Seguimiento validado correctamente.» / «Seguimiento devuelto al territorial para subsanar.».
  PNUD: además `save(update_fields=["fecha_actualizacion"])`; «Seguimiento PNUD validado correctamente.» /
  «Seguimiento PNUD devuelto al territorial para subsanar.».

### API web del runtime

- GET/POST `/api/web/comedores/relevamientos/<int:comedor_pk>/relevamiento/<int:relevamiento_pk>/seguimientos/<int:pk>/editar/`:
  GET 200 `{"root": <descriptor>, "bloques": [{"key", "label", "existe", "form": <descriptor>}], "prestaciones":
  <descriptor de formset>}`; POST con los nombres nativos (`seg-*`, `<bloque>-*`, `prestaciones-*`) → 200 `{"ok",
  "message": "Seguimiento actualizado correctamente.", "redirect": <detalle>}` o 400 con descriptores ligados.
- POST `.../seguimientos/<int:pk>/eliminar/` y POST `.../seguimientos/primero/eliminar/`: 200 `{"ok", "message":
  "Seguimiento eliminado correctamente.", "redirect": "/comedores/<id>/relevamiento/<relevamiento_pk>"}`; repetido 404.
- POST `.../seguimientos/<int:pk>/revision/` y POST `/api/web/comedores/relevamientos/<int:comedor_pk>/pnud/<int:pk>/revision/`:
  códigos y textos como R01.02 con sus etiquetas (D10).

### Módulo React

- `seguimientos.tsx`: path `^/comedores/([0-9]+)/relevamiento/([0-9]+)/seguimiento/([0-9]+)/editar$`. La baja y las
  revisiones son modales en los detalles de R01.01 y R03.01.
- Volver nativo: «Cancelar» a `/comedores/<id>/relevamiento/<relevamiento_pk>/seguimiento/<pk>/`
  (`seguimiento_form.html:126-127`).

### Criterios de aceptación

- Pestaña «Editar <tipo en minúsculas> - Comedor: <nombre>»; título «<nombre> | Editar <tipo> #<orden>»; tarjetas
  «Datos de la instancia», una por bloque con badge «Sin cargar» (title «Se crea solo si se completa algún campo»),
  «Prestaciones» con columna «Eliminar» y «La última fila vacía permite agregar una prestación. Guarde y vuelva a
  editar para agregar más.»; «Cancelar», «Guardar».
- Modal de baja: «Eliminar <tipo en minúsculas> #<orden>», «Esta accion eliminara la instancia del ciclo de seguimiento
  y dara de baja el registro asociado en GESTIONAR.» (sin tildes, literal), «No se puede deshacer.», «Cancelar»,
  «Eliminar». Modales de revisión: «Revisión del coordinador», «Resultado», «Validado», «A subsanar (devolver al
  territorial)», «Observaciones», «Qué debe corregir el territorial (obligatorio si devuelve el seguimiento)»,
  «Guardar revisión» (sin opción «Seleccionar resultado», a diferencia del relevamiento).
- Paridad estructural, orden de Tab y regla visual S13.

### Casos de prueba

- Backend: edición válida e inválida, bloque vacío no creado, bloque con datos creado, borrar prestación; baja con y sin
  `gestionar_id` (hilo simulado, sin red), bloques borrados, repetida 404, alias primera instancia; revisión PNUD
  actualiza `fecha_actualizacion`; validado 409; permisos 403/401; CSRF. Existentes:
  `test_seguimiento_instancias_backoffice.py`, `test_backoffice_seguimientos_actas.py`, `test_huecos_seguimiento_n19.py`.
- Frontend: formulario con 17 bloques plegables, errores, 504 sin reenvío.
- Diferencial: POST nativos con mismas entradas producen mismas filas y redirects.
- Visual: edición sin bloques, con errores; modales de baja y revisión.

### Riesgos

- Formulario largo (17 bloques `__all__`): el descriptor genérico debe preservar widgets `NullBooleanSelect`
  (`"unknown"`), selects y `datetime-local`.
- La baja dispara efecto externo en GESTIONAR y es irreversible (paridad).

## Decisiones técnicas tomadas

- **D1 Partición de rutas.** `primer_seguimiento_detalle` (70) y `primer_seguimiento_eliminar` (77) pasan a R03.01 y
  R03.02 porque usan las mismas vistas que `seguimiento_detalle` y `seguimiento_eliminar`; separarlas duplicaría el
  componente. El catálogo marca la partición como «confirmar_rutas_del_slice_con_la_fuente».
- **D2 Crear/editar relevamiento quedan nativos.** Ninguna plantilla enlaza `relevamiento_crear` y el enlace a
  `relevamiento_editar` está comentado (`relevamiento_detail.html:56`); el alta real ocurre por el popup de CO07 y por la
  app. El formulario combina 12 formularios (`helpers.py:25-37`, `form.py:407-471`) y tiene efectos que migrar
  replicaría: la edición reescribe `fecha_visita` con `timezone.now()` (`service.py:875`) y el `referente_form` se
  guarda sin vincularse (`service.py:867-868` asigna `relevamiento.responsable`, que no es campo del modelo). Se conservan
  como rutas nativas, sin módulo React; React no matchea esos paths. Retirarlas requiere una decisión aparte.
- **D3 Descargas binarias por GET nativo.** Los tres PDF (`relevamiento_pdf`, `seguimiento_pdf`, `seguimiento_pnud_pdf`)
  se enlazan con `<a href>`; no pasan por JSON ni por `/api/web/`.
- **D4 Ventana de 60 s.** Las descargas quedan fuera de G1: usan el read timeout de 25 s de las rutas nativas
  (`backend_proxy.py:49`), igual que hoy. La conversión SIPH (LibreOffice, `timeout=120`) y weasyprint pueden superarlo;
  no existe job asíncrono para estos PDF y crear uno excede la migración. Ninguna operación de la API nueva es larga
  (las llamadas a GESTIONAR son hilos posteriores, `tasks.py:83,161,295`). Gunicorn ya corre por encima de 60 s
  (`docker/django/entrypoint.py:320-329`).
- **D5 Popup de CO07.** Los modales de alta, alta de seguimiento y reasignación se renderizan en React y envían un POST
  de formulario nativo (sin `X-Requested-With`) a `relevamiento_create_edit_ajax`, que responde con mensaje y redirect
  como hoy; el autocompletado reutiliza `GET /comedores/<id>/territoriales/`. No se crea API para algo que es de CO07.
- **D6 Guard de permisos.** Las vistas API invocan `permissions_any_required(<códigos>)` (el mismo decorador de
  `web_urls.py`) dentro de `initial()` tras `WebGatePermission` e `IsAuthenticated`, para no reimplementar la regla
  (superusuario + IAM). El anónimo recibe 401 por G1, mientras la ruta nativa responde 403; la diferencia es del
  transporte y se documenta.
- **D7 Descriptor genérico de formularios.** Para `SeguimientoEditor` y `ActaComplementariaEditor` la API serializa los
  formularios Django ligados (nombre con prefijo, label, widget, required, value, choices, help_text, errors) y acepta en
  POST los mismos nombres; valida y guarda con los editores nativos. Evita duplicar 17 esquemas de bloques.
- **D8 Presentador del detalle de relevamiento.** `secciones` se arma en `web_api_serializers.py` replicando el orden y
  las etiquetas de `relevamiento_detail_secciones.html`; la plantilla sigue para el PDF. Una prueba compara etiquetas
  contra el render nativo.
- **D9 Listado compartido.** El armado de ítems de `RelevamientoListView.get_context_data` se extrae a una función que
  usan la vista y la API (refactor chico, mismo HTML).
- **D10 Códigos de revisión.** El helper devuelve solo texto; la API mapea con los mismos predicados en el mismo orden:
  `esta_validado` o `sin_cargar` → 409, el resto → 400. La transacción y `select_for_update` se repiten igual que la
  vista nativa alrededor del helper compartido.
- **D11 Largo del Número de IF.** La API rechaza más de 255 caracteres con 400 (validador del campo del modelo); la UI
  nativa ya lo impide con `maxlength="255"`. Solo cambia el POST directo, que hoy terminaría en error de base.
- **D12 Paridad de asimetrías.** Se conservan: detalle, PDF y baja de relevamiento sin filtro por `comedor_pk`; botón
  «Eliminar» siempre visible; baja con `change_relevamiento`; IF con permiso Django; edición de registros validados;
  confirmación de IF aunque no exista el id.

## Puntos estrictamente humanos

- **H1 Alcance por comedor (privacidad).** Hoy cualquier usuario con `view_relevamiento` ve relevamientos, seguimientos,
  actas y PNUD de cualquier comedor por URL directa, y el detalle de relevamiento ignora el `comedor_pk`; el popup de
  CO07 sí aplica el alcance de comedores del usuario. Opciones: (a) paridad en M2 y abrir un issue aparte para aplicar
  `ComedorService.get_scoped_comedor_or_404` a la vista nativa y a la API a la vez; (b) aplicar el alcance ya en la API y
  en las vistas nativas dentro de M2; (c) aplicarlo solo en la API (React y HTML quedarían distintos). Recomendada: (a),
  porque la decisión de paridad S13 ya cubre M2 y el cambio de alcance afecta a roles que hoy trabajan sin él.

## Incertidumbres

- U1 [no confirmado] No se revisaron logs de acceso: no se sabe si alguien usa por URL directa `relevamiento_crear` o
  `relevamiento_editar` (D2).
- U2 [no confirmado] Respuesta exacta de `relevamientos`, `relevamiento_crear` y `relevamiento_detalle` ante un
  `comedor_pk` no numérico (sin convertidor `int`); se espera error 500 de conversión, no ejecutado.
- U3 [no confirmado] Formato de fecha mostrado (`DATETIME_FORMAT` y localización activa) para replicarlo en JSON; debe
  tomarse del render nativo en la prueba.
- U4 [no confirmado] Mecanismo de activación que hace que un pathname servido hoy por `backend_comedores` lo atienda
  React; es setup compartido del padre (grupo de activación).
- U5 [no confirmado] El catálogo nombra «evidencias del acta»; en la fuente el backoffice no sube archivos y la `firma`
  la carga la app. No se encontró otra evidencia en las rutas de R02.
- U6 [no confirmado] Duración real de weasyprint y LibreOffice con datos reales frente a los 25 s del proxy nativo.

## Fuente

Leído en HEAD 4ea95bcbe:
`src/backends/comedores/relevamientos/urls/__init__.py:1-4`; `urls/api_urls.py:1-39`; `urls/web_urls.py:1-185`;
`urls.py:1-9`; `views/web_views.py:1-692`; `views/backoffice_views.py:1-295`; `views/seguimiento_helpers.py:1-113`;
`views/api_views.py:1-60,109-113,197-205,281,370,381,422-465`; `models.py:1-138,1125-1275,1760-2251`;
`form.py:1-120,380-471`; `forms_backoffice.py:1-236`; `helpers.py:1-102`; `service.py:650-672,837-890`;
`signals.py:1-83`; `audit_signals.py:1-25`; `tasks.py:4-25,83-123,161-198,213-254,295`; `pdf_oficial.py:1-114`;
`pdf_service.py:1-120`; `siph_docx.py:195-282`; `pnud_formularios.py:90-174`; `alta_backoffice.py:41-187`;
`static/custom/js/comedordetail_territorial_cache.js:307,347`;
`templates/relevamiento_list.html:1-412`; `relevamiento_detail.html:1-352`; `relevamiento_detail_secciones.html`
(encabezados); `relevamiento_confirm_delete.html:1-24`; `relevamiento_form.html` (encabezados y botones);
`relevamiento_pdf.html:5,90`; `relevamiento_imagen.html:1-16`; `primer_seguimiento_detail.html:1-272`;
`seguimiento_form.html:1-131`; `seguimiento_pnud_detail.html:1-194`; `acta_complementaria_detail.html:1-220`;
`acta_complementaria_form.html:1-106`;
`src/backends/comedores/comedores_runtime/urls.py:1-35`; `src/backends/config/backends.json:239-275`;
`src/backends/kernel/core/backend_proxy.py:27-52,236-260`; `src/backends/kernel/core/web_gate.py:300-328`;
`src/backends/kernel/core/decorators.py:1-67`; `src/backends/kernel/core/soft_delete/view_helpers.py:60-118`;
`src/backends/kernel/core/soft_delete/base.py:74-91`; `src/backends/kernel/core/templatetags/custom_filters.py:53-57`;
`src/backends/kernel/core/permissions/registry.py:50-64`; `src/backends/kernel/users/bootstrap/groups_seed.py:1-160`;
`src/backends/kernel/templates/components/delete_confirm.html`;
`src/backends/comedores/comedores/urls.py:40,416-419`; `comedores/views/relevamientos.py:40-60,117-160,267-300`;
`comedores/templates/comedor/comedor_detail.html:20-40,395,826-1060`;
`src/backends/sisoc_core/insumos/web_api_urls.py:1-22`; `web_api_views.py:1-369`;
`src/frontends/apps/sisoc/src/routes/index.ts:1-47`; `routes/types.ts:1-68`; `routes/userImport.tsx` (transporte,
CSRF, `uncertain`, registro); `docs/implementaciones/frontend_v2.md:480-520`;
`docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md:1-113`; `docker/django/entrypoint.py:320-329`;
`src/backends/config/url_registry.json:790-810`.
Disco (untracked): `docs/plans/2026-T4/2026-10-27-2785-entregas-por-flujo.json` (flujos R01, R02, R03 y
`contract_profiles`); `docs/plans/2026-T4/2026-10-28-2785-comedores-legajo-base-m2.md`;
`docs/plans/2026-T4/2026-10-28-2785-comedores-certificaciones-montos-m2.md`.
