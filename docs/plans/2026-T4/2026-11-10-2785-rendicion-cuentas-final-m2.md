# RF01.01, RF01.02, RF01.03: rendición de cuentas final y documentos

Estado M2 ejecutable: contrato basado en fuente HEAD 4ea95bcbe, sin ejecución de app, DB, correo, proveedores ni capturas.
Entregas del catálogo `2026-10-27-2785-entregas-por-flujo.json` (flujo RF01, app `rendicioncuentasfinal`, owner `comedores`):
RF01.01 «Consulta de rendición final» perfil L (lectura y navegación), RF01.02 «Acciones del circuito» perfil W
(acción o transición de circuito) y RF01.03 «Documentos y comprobantes» perfil F (archivo, documento o exportación).
Riesgo del catálogo: «No sustituir validación/subsanación por update de estado; archivos privados.»

Hallazgo de entrada: en HEAD ninguna pantalla viva enlaza a este circuito. El ítem del sidebar está dentro de
`{% comment %}` (`kernel/templates/includes/sidebar/opciones.html:387-397`), `new_opciones.html` no se usa,
`usuarios/web_navigation.py:199` lo excluye a propósito y la ficha del comedor solo pone
`rendicion_cuentas_final_activo: True` en el contexto (`comedores/views/comedor.py:1448`) sin que ningún template lo lea.
Hoy se entra solo por URL directa. La migración conserva eso: no agrega enlaces nuevos.

## Entregas y orden

| ID | Título | Perfil | Rutas nativas cubiertas | Depende de |
| --- | --- | --- | --- | --- |
| RF01.01 | Consulta de rendición final | L | `rendicion_cuentas_final` (urls.py:19), `rendicion_cuentas_final_listar` (urls.py:56), `documentos_rendicion_cuentas_final_ajax` (urls.py:64) | setup compartido `api/web/comedores/` (padre) |
| RF01.02 | Acciones del circuito | W | `validar_documento_rendicion_cuentas_final` (urls.py:46), `subsanar_documento_rendicion_cuentas_final` (urls.py:51), `switch_rendicion_final_fisicamente_presentada` (urls.py:36) | RF01.01 (pantallas que alojan las acciones) |
| RF01.03 | Documentos y comprobantes | F | `adjuntar_documento_rendicion_cuenta_final` (urls.py:26), `crear_documento_rendicion_cuentas_final` (urls.py:31), `eliminar_documento_rendicion_cuentas_final` (urls.py:41), enlaces «Visualizar» a media | RF01.01 |

RF01.02 y RF01.03 son independientes entre sí; ambas montan botones dentro de los módulos React de RF01.01.

## Montaje y piezas comunes

- Runtime: `comedores_runtime/urls.py:15` incluye `rendicioncuentasfinal.urls` en `""`. El core reenvía por los prefijos
  `comedores/` y `rendicion_cuentas_final/` de `config/backends.json:257,266` (`core.backend_proxy`, `config/urls.py:27`).
  URLs públicas: `/comedores/<pk>/rendicion_cuentas_final/` y `/rendicion_cuentas_final/...`.
- Permiso único del módulo: `_RENDICION_FINAL_PERM = ["rendicioncuentasfinal.view_rendicioncuentasfinal"]` (urls.py:16).
  Grupos que lo reciben por migración (`kernel/users/migrations/0034_bootstrap_rendicion_final_permission.py:4-10`):
  «Tecnico Comedor», «Area Contable», «Coordinador Equipo Tecnico», «Coordinador general», «Coordinador Gestion».
- `permissions_any_required` (`kernel/core/decorators.py:35-47`): sin sesión o sin permiso levanta `PermissionDenied`
  (403, no redirige a login); superusuario pasa (`iam/services.py:96`). En urls.py:21 y 58 envuelve por fuera de
  `LoginRequiredMixin`, así que el anónimo recibe 403 antes de que el mixin redirija.
- Modelos (`rendicioncuentasfinal/models.py`):
  - `TipoDocumentoRendicionFinal` (7-33): `nombre` Char 255 único; `validador` Char 255 null, default «Dupla»;
    `personalizado` bool default False.
  - `EstadoDocumentoRendicionFinal` (36-48): `nombre` Char 255 único. Fixture
    `comedores/fixtures/EstadoDocumentoRendicionFinal.json`: 1 «No presentado», 2 «En análisis», 3 «Validado», 4 «Subsanar».
  - `RendicionCuentasFinal` (51-82): `comedor` FK CASCADE `related_name="rendiciones"` (no único);
    `fisicamente_presentada` bool default False. `add_documento_personalizado(nombre)` (71-78).
  - `DocumentoRendicionFinal` (85-135): `rendicion_final` FK CASCADE; `documento` FileField
    `upload_to="rendicion_cuentas_final/"` null/blank; `tipo` FK PROTECT null; `estado` FK PROTECT default=1;
    `observaciones` Char 255 null/blank; `fecha_modificacion` DateTime null. Propiedades `editable`
    (estado en «No presentado», «Subsanar»), `validable` (`tipo.validador == "Dupla"` y estado «En análisis»),
    `eliminable` (estado «En análisis»). `unique_together = [["rendicion_final", "tipo"]]`.
- Señal `comedores/signals.py:184-188`: al crear una `RendicionCuentasFinal` crea un documento por cada tipo con
  `personalizado=False` (fixture `TipoDocumentoRendicionFinal.json`: 14 tipos base con validador «Dupla»,
  «Contable» o «Legales», más dos registros de prueba pk 15-16).
- Historial: `HistorialService.registrar_historial` (`historial/services/historial_service/impl.py:58-99`) toma el
  usuario de `config.middlewares.threadlocals.get_current_user`; lectura por rendición en 101-130 (orden `-fecha`).
- Redirecciones nativas: `core.security.safe_redirect` (`kernel/core/security.py:5-31`) a `HTTP_REFERER` o `next`
  del mismo host; si no, `rendicion_cuentas_final_listar`.
- Volver: ninguna vista define `volver_url`; `components/back_button.html:19` cae a `href="/"` y `volver.js` usa el
  historial. React usa `backHref: "/"` (default de `SisocShell`, `routes/SisocShell.tsx:204`).

## RF01.01 Consulta de rendición final

### Rutas nativas

- `GET /comedores/<int:pk>/rendicion_cuentas_final/`, nombre `rendicion_cuentas_final` (urls.py:19-25),
  `RendicionCuentasFinalDetailView` (views.py:176-212), template
  `comedores/templates/comedor/rendicion_cuentas_final_detail.html:1-258`, JS
  `comedores/static/custom/js/rendicioncuentasfinaldetail.js:1-28`.
- `GET /rendicion_cuentas_final/listar/`, nombre `rendicion_cuentas_final_listar` (urls.py:56-62),
  `DocumentosRendicionCuentasFinalListView` (views.py:53-73), template
  `comedores/templates/comedor/rendicion_cuentas_final_list.html:1-130`, JS
  `comedores/static/custom/js/rendicioncuentasfinallist.js:1-31`, buscador `kernel/templates/components/search_bar.html:78-108,273-450`.
- `GET /rendicion_cuentas_final/ajax/?busqueda=&page=`, nombre `documentos_rendicion_cuentas_final_ajax`
  (urls.py:64-69), función `documentos_rendicion_cuentas_final_ajax` (views.py:231-273), filas
  `rendicioncuentasfinal/templates/partials/rendicion_cuentas_final_rows.html:1-46` y `components/pagination.html`.

### Acceso

- Detalle: login más `view_rendicioncuentasfinal` (403 anónimo o sin permiso). Sin scope de objeto: cualquier `pk`
  de comedor existente; inexistente → 404 (`get_object_or_404`, views.py:182-185).
- Listado: igual permiso. Scope por área en `RendicionCuentasFinalService.filter_documentos_por_area`
  (`rendicion_cuentas_final_service.py:89-163`):
  - superusuario: validador en «Contable», «Legales», «Dupla»;
  - «Contable» si tiene `comedores.view_comedor` o `expedientespagos.view_expedientepago`;
  - «Legales» si tiene `comedores.view_comedor`, `admisiones.view_admision`, `acompanamientos.view_informacionrelevante`
    o `expedientespagos.view_expedientepago`;
  - «Dupla» si tiene `comedores.view_comedor`, `admisiones.view_admision` o `acompanamientos.view_informacionrelevante`,
    o si `UserPermissionService.get_coordinador_duplas` (`kernel/users/services.py:385-420`) indica coordinador;
  - coordinador no superusuario: además `rendicion_final__comedor__dupla_id__in=duplas_ids`; sin duplas → vacío.
  - Asimetría a conservar: un usuario sin ninguno de esos permisos y no coordinador queda con `Q()` vacío y ve
    documentos de todos los validadores (service:95,136).
- AJAX: sin `login_required`; el decorador interno (views.py:234) da 403 a anónimo o sin permiso. No restringe método.

### Datos y reglas

- Detalle: `get_or_create(comedor=comedor)` (views.py:186-188). Efecto en GET: crea la rendición y, por la señal, sus
  documentos base. Si hubiera dos rendiciones del mismo comedor, `MultipleObjectsReturned` (500).
  Documentos: `get_documentos_rendicion_cuentas_final` (service:58-87), orden `id`. Historial: todos los registros de
  los documentos de la rendición, orden `-fecha`, sin paginación.
  - Columnas de documentos: «Tipo de Documento» (`tipo.nombre`), «Estado», «Validador» (`tipo.validador`),
    «Observaciones» (enlace «Ver» si hay texto; si no «-»), «Última Modificación» (`d/m/Y H:i` o «-»), y cuatro columnas
    sin título: Adjuntar, Visualizar, Validar y eliminar. Sin fila de vacío.
  - Columnas de historial: «Tipo de Documento» (`registro.objeto.tipo.nombre`, «Desconocido» si no hay nombre,
    «No disponible» si el objeto no existe), «Acción», «Usuario» (`get_full_name` o `username`), «Fecha»
    (`d/m/Y H:i` o «-»). Vacío: «No hay registros aun.».
  - Breadcrumb: «Espacios Comunitarios» → `comedores`; enlace a `comedor_detalle` con texto
    `{{ rendicion.comedor_nombre }}`, atributo inexistente en el modelo, así que hoy el texto sale vacío
    (template:14); activo «Rendicion de Cuentas Final». Paridad: reproducir el enlace vacío.
- Listado: queryset del service con `busqueda` (icontains sobre `rendicion_final__comedor__nombre` o `tipo__nombre`),
  estados «En análisis», «Subsanar», «Validado», orden `-fecha_modificacion` sin desempate.
  - Carga inicial: `ListView` sin `paginate_by`, todas las filas, sin paginación (template:86-90 no renderiza nada).
  - Tras escribir (debounce 300 ms), la lupa, Escape o un clic de página, el JS llama al AJAX: 25 por página,
    `paginator.get_page` (página inválida no falla, cae a la primera o la última).
  - AJAX responde `{html, pagination_html, count, num_pages, has_previous, has_next, current_page}`.
  - Columnas: «Nombre», «Comedor», «Fecha de modificacion», «Estado», «Acciones», «Validar», «Subsanar».
  - «Validar»/«Subsanar» activos solo si estado == «En análisis» (sin mirar el validador; el detalle sí usa `validable`).
  - Clase de fila `estado-<slug>`. El JS de «Ocultar analizados» busca `#toggle-validados`, que no existe porque
    `additional_search_buttons` no está en el contexto: la función está muerta y el script tira un TypeError
    después de enlazar el modal (list.js:14-17). React no la muestra.
  - `breadcrumb_items` no está en el contexto: breadcrumb vacío. Título del bloque `title`: «Espacios Comunitarios».

### Acciones y efectos

Solo lectura, salvo el `get_or_create` del detalle (crea la rendición y los documentos base, sin historial ni mensaje).

### API web del runtime

Archivos propuestos: `src/backends/comedores/rendicioncuentasfinal/web_api_urls.py`, `web_api_views.py`,
`web_api_serializers.py`. El montaje en `comedores_runtime/urls.py` bajo `api/web/comedores/` y el prefijo en
`backends.json` es setup compartido del padre.

Base común (`RendicionFinalWebView`): `SessionAuthentication`, `permission_classes = [WebGatePermission]`
(`kernel/core/web_gate.py:308-328`), `JSONRenderer`, `Cache-Control: private, no-store` y `Vary: Cookie` como en
`insumos/web_api_views.py:51-87`. Después de G1, `iam.services.user_has_permission_code(user,
"rendicioncuentasfinal.view_rendicioncuentasfinal")`; si falla, 403 `{"detail": ...}`. 401 y 403 de requisito los da G1.

- `GET /api/web/comedores/rendicion_cuentas_final/comedor/<pk>/`
  - 200: `{rendicion: {id, fisicamente_presentada}, comedor: {id, nombre}, documentos: [...], historial: [...]}`.
  - `documentos[]`: `{id, tipo_nombre, estado, validador, observaciones (null), fecha_modificacion ("d/m/Y H:i" o null),
    archivo_url (null), editable, validable, eliminable}`.
  - `historial[]`: `{tipo_nombre (null si no hay objeto), accion, usuario, fecha}`.
  - 404 si el comedor no existe. Conserva el `get_or_create`: se mueve a
    `RendicionCuentasFinalService.obtener_o_crear_rendicion(comedor_pk)` y la usan la vista nativa y la API.
- `GET /api/web/comedores/rendicion_cuentas_final/documentos/?busqueda=&page=`
  - Sin `busqueda` ni `page`: todas las filas, `page_size: null`, `pages: 1` (paridad con `ListView`).
  - Con cualquiera de los dos (aunque `busqueda` venga vacía): `Paginator(qs, 25).get_page(page)` como el AJAX.
  - 200: `{count, page, page_size, pages, has_previous, has_next, filters: {busqueda}, results: [{id, tipo_nombre,
    comedor_nombre, fecha_modificacion, estado, estado_slug, archivo_url, accionable}]}`.
  - `accionable` = estado == «En análisis».
  - Reutiliza `filter_documentos_por_area`.
- Las rutas nativas (`listar`, `ajax`, detalle) no cambian.

### Módulo React

`src/frontends/apps/sisoc/src/routes/rendicionCuentasFinal.tsx` y `rendicionCuentasFinal.test.tsx`. Paths que posee:
`/comedores/<pk>/rendicion_cuentas_final/` (regex `^/comedores/([0-9]+)/rendicion_cuentas_final/$`) y
`/rendicion_cuentas_final/listar/`. Se registra en `ROUTES` de `routes/index.ts` antes de `businessRoute`, igual que
`userImportRoute`. `backHref: "/"`. Usa `useWebResource` y `postOnce` de `routes/userImport.tsx:36-60` (un GET por
montaje, sin polling).

### Criterios de aceptación

- Detalle:
  - Título y `titulo-pagina` «Rendicion de Cuentas Final» (sin tilde, literal).
  - Breadcrumb «Espacios Comunitarios» / (enlace vacío al comedor) / «Rendicion de Cuentas Final».
  - Botón «Añadir documento personalizado» y switch «Revisión físicamente presentada» (RF01.02).
  - Encabezado «Historial de Documentos».
  - Modal de observaciones: título «Observaciones del documento {tipo}» (fallback «Observaciones»), cuerpo como texto
    plano (fallback «Sin observaciones»), botón «Cerrar».
- Listado:
  - Buscador «Buscar Documento», placeholder «Buscar por comedor o tipo de documento», ayuda
    «Ingresar comedor o tipo de documento.» (title y aria-label del input), botón de lupa con aria-label «Buscar».
  - Contador «N resultado(s) encontrado(s)» solo con búsqueda no vacía; carga «Cargando...»; error
    «Error al cargar los datos. Intente nuevamente.»; vacío «No se encontraron documentos.» (colspan 7).
  - Paginación con «Volver» y «Continuar» (`components/pagination.html`), solo tras búsqueda y con más de una página.
  - «Visualizar» activo con archivo (abre en pestaña nueva), deshabilitado sin archivo.
- Paridad: misma estructura DOM visible, mismo orden de Tab (Volver, buscador, lupa, filas por columna, paginación),
  regla S13 (paridad estructural más diff perceptual ≤ 1 % sin antialiasing, 2 CSS px) en desktop y móvil, con estados
  con datos, vacío y error.

### Casos de prueba

- Backend (pytest, `src/backends/comedores/tests/test_rendicion_final_web_api.py`):
  - permitido con el permiso; 403 sin permiso; 401 anónimo vía G1 (monolito: `WebGatePermission` local);
  - detalle de comedor inexistente 404; detalle de un comedor sin rendición la crea con los documentos base, con
    paridad nativa;
  - listado por área: superusuario, `view_comedor`, coordinador con y sin duplas, usuario solo con
    `view_rendicioncuentasfinal` (ve todos los validadores);
  - búsqueda por comedor y por tipo; carga inicial sin paginar; `page=abc` y `page=999` no fallan; orden
    `-fecha_modificacion`; filtro de estados.
- Frontend (vitest): render de filas, vacío, error, contador, «Visualizar» deshabilitado, botones habilitados solo en
  «En análisis», breadcrumb y `backHref`.
- Diferencial: GET de `rendicion_cuentas_final_listar`, del AJAX y del detalle antes y después con la misma DB
  sintética: mismo status y mismo HTML o JSON.
- Visual: por URL y estado, con roles superusuario, Area Contable y coordinador, en desktop y móvil.

### Riesgos

- El GET del detalle escribe (crea la rendición). Una carrera entre dos GET puede duplicar la rendición y romper el
  detalle con 500. Se conserva y se documenta.
- Listado inicial sin límite: costo con muchos documentos. Existe escenario de benchmark `rendicioncuentasfinal:list`
  (`kernel/core/benchmarks/scenarios.py:171-174`).
- Orden sin desempate: la paginación puede repetir o saltar filas con fechas iguales (igual que hoy).

## RF01.02 Acciones del circuito

### Rutas nativas

- `POST /rendicion_cuentas_final/documento/<int:documento_id>/validar/`, nombre `validar_documento_rendicion_cuentas_final`,
  views.py:76-96. Formularios en detail.html:98-104 (solo si `validable`), list.html:56-61 y rows.html:19-24 (si
  «En análisis»).
- `POST /rendicion_cuentas_final/documento/<int:documento_id>/subsanar/`, nombre `subsanar_documento_rendicion_cuentas_final`,
  views.py:29-50. Modal `#modalSubsanar` en list.html:95-125; la URL se arma con `SUBSANAR_URL.replace("0", id)`
  (list.html:128, list.js:5-12). No hay botón de subsanar en el detalle.
- `POST /rendicion_cuentas_final/<int:rendicion_id>/fisicamente_presentada/`, nombre
  `switch_rendicion_final_fisicamente_presentada`, views.py:215-228. Switch en detail.html:31-43, con
  `data-auto-submit-on-change="disable"` (`kernel/static/custom/js/base.js:400-408`).

### Acceso

- Las tres: `login_required` (anónimo → 302 a login) y `require_POST` (GET → 405). Sin permiso de acción ni scope de
  objeto: cualquier usuario autenticado puede hacerlo por ID. Documento o rendición inexistente → 404.
- Backend sin guarda de estado: validar y subsanar se aplican en cualquier estado; la UI solo los ofrece en
  «En análisis» (y el detalle, además, con validador «Dupla»).

### Datos y reglas

- Validar: sin campos. Lee `next` del POST o `HTTP_REFERER` para volver.
- Subsanar: `observacion` (textarea `maxlength="150"` y `required` en el cliente; backend `POST.get("observacion", "")`
  sin validar, y el modelo admite 255). Hidden `next` enviado pero ignorado (vuelve por referer).
- Switch: sin campos; invierte el valor actual (el checkbox deshabilitado no viaja).

### Acciones y efectos

| Acción | Escritura | Historial (`accion`) | Mensaje | Redirect |
| --- | --- | --- | --- | --- |
| Validar | `estado` = «Validado», `fecha_modificacion` = now | «Validar documento» | success «Documento validado correctamente.» | `next` o referer, default listado |
| Subsanar | `observaciones` = texto, `estado` = «Subsanar», `fecha_modificacion` = now | «Enviar a subsanar documento» | success «Documento enviado a subsanar correctamente.» | referer, default listado |
| Switch | `fisicamente_presentada = not valor` | ninguno | success «Estado de revisión actualizado.» | referer, default listado |

Sin transacción explícita; `EstadoDocumentoRendicionFinal.objects.get(nombre=...)` da 500 si falta el estado. Sin
correos ni jobs. Repetir el POST repite el efecto: el switch vuelve a invertir y validar o subsanar agregan otro
registro de historial.

### API web del runtime

Base de mutación: la de RF01.01 más `MultiPartParser`/`FormParser`, `http_method_names = ["post", "options"]` y
CSRF de `SessionAuthentication`. Mismo permiso de pantalla `view_rendicioncuentasfinal` (ver Decisiones técnicas).
Sin guarda de estado nueva. Cada vista delega en una función de service nueva que mueve la lógica actual de la vista,
y la vista nativa pasa a llamarla con los mismos textos:
`RendicionCuentasFinalService.validar_documento(documento)`, `.subsanar_documento(documento, observacion)` y
`.alternar_fisicamente_presentada(rendicion)`.

- `POST /api/web/comedores/rendicion_cuentas_final/documentos/<id>/validar/`: 200
  `{ok: true, message: "Documento validado correctamente.", documento: {id, estado, fecha_modificacion}}`.
- `POST .../documentos/<id>/subsanar/` con `observacion`: 200 `{ok, message: "Documento enviado a subsanar correctamente.", documento}`.
- `POST .../rendicion_cuentas_final/<rendicion_id>/fisicamente_presentada/`: 200
  `{ok, message: "Estado de revisión actualizado.", fisicamente_presentada}`.
- Comunes: 401 y 403 de G1 o de permiso, 403 CSRF, 404 por ID inexistente, 405 en GET. No hay 400 ni 409 porque el
  nativo no valida. Un 504 `uncertain: true` muestra «No se pudo confirmar el resultado.», recarga el detalle o el
  listado con GET y no reenvía.

### Módulo React

Dentro de `rendicionCuentasFinal.tsx`:
- botón «Validar» con `window.confirm` y el texto nativo;
- modal de subsanar con su textarea;
- switch del detalle que se deshabilita al enviar.

Después de un 200: toast con `message` y GET de la pantalla (equivale a volver a la misma URL por referer).
Sin reintento automático.

### Criterios de aceptación

- Confirmación «¿Estás seguro de que querés validar este documento?»; botón «Validar» (`btn-warning`), deshabilitado
  fuera de «En análisis» (listado) o si no es `validable` (detalle).
- Modal «Subsanar Documento», etiqueta «Observación», textarea requerido de 150 caracteres como máximo, botones
  «Cancelar» y «Enviar a Subsanar»; el textarea se vacía al abrir.
- Mensajes literales de la tabla anterior. Switch con el estado actual y etiqueta «Revisión físicamente presentada».
- Paridad S13 del modal abierto y del toast; foco dentro del modal y Escape lo cierra, como Bootstrap.

### Casos de prueba

- Backend:
  - por acción: éxito con efectos en DB e historial (usuario correcto vía threadlocal en DRF), 404, 401 y 403, CSRF
    ausente 403, GET 405;
  - validar un documento en «No presentado» también valida (paridad);
  - subsanar con observación vacía se acepta;
  - el switch invierte dos veces y no registra historial.
- Frontend: confirm cancelado no envía; 504 `uncertain` sin reenvío; doble clic envía una vez.
- Diferencial: POST nativos antes y después del refactor a service con los mismos mensajes, redirects y filas.
- Visual: modal y estado del switch en desktop y móvil.

### Riesgos

- Autorización de acción débil en nativo (solo login). La API exige el permiso de pantalla. Ampliar a scope por área
  es decisión humana (ver Puntos estrictamente humanos).
- Sin control de concurrencia: dos usuarios pueden validar y subsanar el mismo documento y gana el último, como hoy.

## RF01.03 Documentos y comprobantes

### Rutas nativas

- `POST /rendicion_cuentas_final/documento/adjuntar/` (multipart `documento_id`, `archivo`), nombre
  `adjuntar_documento_rendicion_cuenta_final`, views.py:154-173. Modal en detail.html:161-196 (JS detail.js:3-14).
- `POST /rendicion_cuentas_final/<int:rendicion_id>/crear/` (multipart `nombre`, `archivo` opcional), nombre
  `crear_documento_rendicion_cuentas_final`, views.py:128-151. Modal en detail.html:197-232.
- `POST /rendicion_cuentas_final/documento/<int:documento_id>/eliminar/`, nombre
  `eliminar_documento_rendicion_cuentas_final`, views.py:99-125. Formulario en detail.html:110-119 (solo `eliminable`).
- Visualizar: `GET /media/rendicion_cuentas_final/<archivo>` mediante `documento.url` (detail.html:89-95, list.html:46-52,
  rows.html:9-15). No hay vista Django de descarga.

### Acceso

- Mutaciones: `login_required` y `require_POST`, sin permiso ni scope, como en RF01.02. Adjuntar sin `documento_id` o
  con un ID inexistente → 404 (`get_object_or_404` en service:41).
- Media: `STORAGES.default = FileSystemStorage` (`config/settings.py:736-739,757-760`), `MEDIA_URL = "/media/"`,
  `MEDIA_ROOT = BASE_DIR / "media"` (settings.py:275-276). Nginx sirve `/media/` sin autenticación y solo bloquea
  `/media/pas/ddjj/` y `/media/inspecciones/` (`docs/operacion/deploy_entornos_docker_nginx_mysql.md:378-392`).
  Hoy los comprobantes no son privados: cualquiera con la URL los descarga.
- Otros consumidores de los mismos archivos: el detalle de admisión, que lee «Rendicion de cuenta final» con
  «Descargar» (`admisiones/templates/admisiones/admisiones_detalle.html:699-747`, `admisiones/views/web_views.py:435-462`),
  y la API PWA de documentos del comedor (`comedores/api_views.py:616-635`, URL absoluta). Ninguno cambia.

### Datos y reglas

- Adjuntar: `archivo` requerido en el cliente; sin archivo el backend no escribe y responde con error. No valida tipo,
  extensión ni tamaño. El límite efectivo es el del proxy: `client_max_body_size 50m` en la guía de deploy (366) y 500M en
  `docs/operacion/nginx/sisoc-produccion.conf:39`. El backend tampoco valida estado: adjunta aunque el documento no sea
  `editable` (la UI solo ofrece el botón si lo es).
- Crear:
  - `nombre` con `strip()`, `required` solo en el cliente; vacío crea un tipo de nombre «».
  - `add_documento_personalizado` hace `get_or_create(nombre, personalizado=True)` y crea el documento en estado
    default (id 1, «No presentado»), con validador default «Dupla».
  - Con un nombre igual a un tipo base → `IntegrityError` (500). Con un tipo personalizado que la rendición ya tiene →
    `IntegrityError` de `unique_together` (500).
  - No es atómico: el tipo creado puede quedar huérfano.
- Eliminar: sin campos.

### Acciones y efectos

| Acción | Escritura | Archivo | Historial | Mensaje |
| --- | --- | --- | --- | --- |
| Adjuntar | `documento` = archivo, `estado` = «En análisis», `fecha_modificacion` (en `transaction.atomic`, service:18-36) | se guarda en `rendicion_cuentas_final/` dentro del atomic; si falla el historial, el archivo queda en disco | «Adjuntar documento» | success «Archivo adjuntado correctamente.» o error «No se seleccionó ningún archivo.» |
| Crear sin archivo | tipo (si no existe) y documento | ninguno | ninguno | ninguno |
| Crear con archivo | tipo, documento, luego lo mismo que Adjuntar | igual que Adjuntar | «Crear documento personalizado» y «Adjuntar documento» | ninguno |
| Eliminar | `documento` = null, `estado` = «No presentado», `fecha_modificacion` | borrado físico (`delete(save=False)`) antes del save, sin transacción | «Documento eliminado» | success «Documento eliminado correctamente.» |

No hay soft delete: el registro del documento sigue y el archivo se borra del storage. El archivo reemplazado al
adjuntar de nuevo no se borra (Django no lo elimina al reasignar el FileField). Redirect por referer, default listado.

### Exportaciones

No hay exportaciones ni archivos generados por backend. Solo archivos subidos.

### API web del runtime

Base de mutación de RF01.02 (multipart). Reutiliza `adjuntar_archivo_a_documento`, `actualizar_documento_con_archivo`
y `add_documento_personalizado`. La lógica de crear y eliminar se mueve a
`RendicionCuentasFinalService.crear_documento_personalizado(rendicion, nombre, archivo)` y `.eliminar_documento(documento)`,
que también usan las vistas nativas.

- `POST /api/web/comedores/rendicion_cuentas_final/documentos/<id>/adjuntar/` con `archivo`: 200
  `{ok, message: "Archivo adjuntado correctamente.", documento}`; 400 `{detail: "No se seleccionó ningún archivo."}`
  sin archivo; 404 si no existe.
- `POST .../rendicion_cuentas_final/<rendicion_id>/crear/` con `nombre` y `archivo` opcional: 201
  `{ok, message: null, documento}`; 404 si la rendición no existe; el `IntegrityError` se deja propagar (500, paridad).
- `POST .../documentos/<id>/eliminar/`: 200 `{ok, message: "Documento eliminado correctamente.", documento}`.
- `archivo_url` en las lecturas es `documento.url` tal cual (misma exposición que el HTML de hoy). Las descargas siguen
  siendo el GET nativo de media enlazado desde React, sin pasar por JSON.
- Comunes: 401, 403, 403 CSRF, 404, 405, y 504 `uncertain` sin reenvío; React recarga la pantalla y deja ver si el
  archivo quedó antes de que el usuario reintente.

### Módulo React

Dentro de `rendicionCuentasFinal.tsx`:
- modal «Adjuntar archivo» con «Documento: {tipo}» e input file requerido;
- modal «Nuevo Documento Personalizado»;
- botón de eliminar con confirmación nativa.

Cada uno envía un solo POST multipart y después recarga el detalle.

### Criterios de aceptación

- Adjuntar:
  - Botón «Adjuntar» (`btn-success`) si `editable`; si no, deshabilitado.
  - Confirmación «¿Estás seguro de que querés adjuntar este documento?».
  - Modal: título «Adjuntar archivo», «Documento: {tipo}», etiqueta «Archivo», botones «Cancelar» y «Subir».
- Crear:
  - Confirmación «¿Estás seguro de que querés crear este documento?».
  - Modal «Nuevo Documento Personalizado» con «Nombre del documento» (requerido) y «Archivo» (opcional), botón «Crear»
    (sin botón cancelar).
- Eliminar: confirmación «¿Estás seguro de que querés eliminar este documento?». Botón ícono `bi-trash` sin texto
  (paridad; nombre accesible: ver Incertidumbres).
- «Visualizar» (`btn-primary`, `target="_blank"`) a la misma URL de media.
- Paridad S13 de los tres modales y estados.

### Casos de prueba

- Backend:
  - adjuntar con archivo: estado, historial y path `rendicion_cuentas_final/`, con `MEDIA_ROOT` temporal fuera del
    worktree;
  - adjuntar sin archivo → 400 con el texto literal; adjuntar sobre un documento «Validado» también funciona (paridad);
  - crear con y sin archivo (historiales correctos), con nombre de tipo base (500) y con nombre repetido en la misma
    rendición (500);
  - eliminar borra el archivo del storage y deja «No presentado»;
  - permisos: 401, 403 y 404 en todos.
- Frontend: confirmaciones, upload multipart de una sola vez, 400 visible, 504 sin reenvío.
- Diferencial: POST nativos de los tres antes y después del refactor a service.
- Visual: modales en desktop y móvil.

### Riesgos

- Uploads grandes con equipos lentos: el proxy del core transmite el cuerpo en stream (`kernel/core/backend_proxy.py:118-135`)
  y G1 verifica `iat` al llegar los headers. La ventana de 60 s se cuenta desde que el core firma y el read timeout
  desde que termina de enviar. Si Nginx no bufferiza el cuerpo, un upload lento lo mantiene ocupado. Decisión:
  upload por la API multipart, como insumos (`insumos/web_api_views.py:163-239`), sin job nuevo. Antes de cerrar hay
  que medir un upload de 50 MB en el entorno sintético.
- Archivos públicos por URL (ver Puntos estrictamente humanos). Los nombres originales pueden contener datos personales.
- Borrado físico no transaccional e IntegrityError con 500: se conservan.

## Decisiones técnicas tomadas

1. **API mutante con el permiso de pantalla.** El nativo solo pide login, pero la API es un consumidor nuevo y su
   única UI vive dentro de pantallas que exigen `view_rendicioncuentasfinal`. Pedirlo no le quita nada a un usuario
   legítimo de React y cierra la API a cualquier autenticado. Las rutas nativas no cambian.
2. **Sin guardas de estado nuevas** en validar, subsanar ni adjuntar. Cumple el riesgo del catálogo: cada acción
   llama a su service, nunca a un PATCH genérico de `estado`. Agregar guardas cambiaría el comportamiento.
3. **Lógica de vista a service.** `obtener_o_crear_rendicion`, `validar_documento`, `subsanar_documento`,
   `alternar_fisicamente_presentada`, `crear_documento_personalizado` y `eliminar_documento` se mueven sin cambiar el
   comportamiento, para que la vista nativa y la API compartan una sola implementación. Es un refactor chico y
   necesario, cubierto por el diferencial.
4. **Listado con dos modos**: completo en la carga inicial y de a 25 con `get_page` cuando hay búsqueda o página.
   Replica `ListView` más el AJAX, que son los dos estados que ve hoy el usuario.
5. **Media sin cambios.** `archivo_url` = `documento.url` y la descarga queda como el GET nativo. No se agrega vista de
   descarga ni base64 en JSON.
6. **Confirmaciones con `window.confirm`** y los textos nativos, igual que `base.js:331-337`.
7. **Upload multipart por la API**, siguiendo el precedente de insumos. Sin job asíncrono porque el nativo no tiene.
8. **Sin enlaces de navegación nuevos**: se conserva el acceso solo por URL.
9. **Fechas preformateadas** `d/m/Y H:i` en hora local en el JSON, como `insumos/web_api_views.py:127`.

## Puntos estrictamente humanos

1. **Privacidad de los comprobantes** (`/media/rendicion_cuentas_final/` se sirve público). Opciones:
   - A) paridad: la migración no lo cambia;
   - B) en esta familia, una vista autenticada de descarga más un bloqueo `location ^~ /media/rendicion_cuentas_final/`
     en Nginx, lo que cambia deploy y rompe las URLs de la API PWA y de admisiones;
   - C) A ahora y B como issue de endurecimiento aparte.

   Recomendada: C.
2. **Autorización por área en las acciones.** Hoy cualquier autenticado valida, subsana, adjunta o elimina por ID.
   Opciones:
   - A) mantener el permiso de pantalla en la API (decisión técnica 1);
   - B) exigir además que el documento esté en `filter_documentos_por_area` del usuario o que su comedor esté en el
     scope de la dupla.

   Recomendada: A en la migración y B como issue aparte, porque cambia quién puede operar.
3. **Pantallas sin navegación.** El listado está comentado en el sidebar y la ficha no enlaza al detalle.
   Opciones:
   - A) migrar con paridad, solo por URL;
   - B) no migrar RF01 hasta que producto decida si el circuito sigue vivo.

   Recomendada: A. Ninguno de los tres puntos bloquea la implementación con paridad.

## Incertidumbres

- [sin confirmar] El buffering de cuerpo de Nginx en producción (`proxy_request_buffering`) no se leyó. Define el
  riesgo de uploads lentos.
- [sin confirmar] El nombre accesible del botón de eliminar: el nativo es un `<button>` solo con ícono `bi-trash` y sin
  texto. La paridad estricta lo deja sin nombre; agregar `aria-label` cambia el árbol de accesibilidad. Por defecto se
  conserva la paridad y se anota como brecha.
- [sin confirmar] Que `get_current_user` (threadlocal) devuelva el usuario de sesión dentro de vistas DRF del runtime.
  `ThreadLocalMiddleware` corre después de `AuthenticationMiddleware` (`settings.py:227,241`); hay que probarlo.
- [sin confirmar] Comportamiento real en MySQL de `observaciones` > 255 (error o truncado según el modo estricto).
- [sin confirmar] Los tipos pk 15 «documento rendición» y 16 «SADSAD TEST» del fixture parecen de prueba; si están
  en DB generan documentos base en cada rendición nueva. No se tocan.
- No existen tests de las vistas (`rendicioncuentasfinal/tests.py` está vacío en HEAD). Candidatos existentes:
  `comedores/tests/test_historial_rendicion_boundary.py`, `test_admisiones_web_views_unit.py:556-638`,
  `test_comedores_api_views_unit.py:135` y `sisoc_core/tests/test_web_navigation.py:293`.

## Fuente

HEAD 4ea95bcbe:
- `src/backends/comedores/rendicioncuentasfinal/urls.py:1-70`, `views.py:1-273`, `models.py:1-138`,
  `rendicion_cuentas_final_service.py:1-163`, `api.py:1-11`, `admin.py:1-56`,
  `templates/partials/rendicion_cuentas_final_rows.html:1-46`;
- `src/backends/comedores/comedores/templates/comedor/rendicion_cuentas_final_list.html:1-130` y
  `rendicion_cuentas_final_detail.html:1-258`; `static/custom/js/rendicioncuentasfinallist.js:1-31` y
  `rendicioncuentasfinaldetail.js:1-28`;
- `comedores/fixtures/EstadoDocumentoRendicionFinal.json` y `TipoDocumentoRendicionFinal.json`;
  `comedores/signals.py:184-188`; `comedores/views/comedor.py:1436-1455`; `comedores/api_views.py:616-635`;
- `src/backends/comedores/admisiones/views/web_views.py:424-463`;
  `admisiones/templates/admisiones/admisiones_detalle.html:699-760`;
- `src/backends/comedores/historial/services/historial_service/impl.py:1-130`, `historial/models.py:9-45`;
- `src/backends/comedores/comedores_runtime/urls.py:1-35`; `src/backends/config/backends.json:239-300`;
  `config/urls.py:11-80`; `config/settings.py:220-242,275-276,734-764`;
- `src/backends/kernel/core/decorators.py:1-67`, `core/security.py:5-31`, `core/web_gate.py:308-328`,
  `core/backend_proxy.py:115-262`, `core/templatetags/custom_filters.py:53-57`, `iam/services.py:90-105`;
- `kernel/users/services.py:381-420`, `kernel/users/migrations/0034_bootstrap_rendicion_final_permission.py:1-58`;
- `kernel/templates/components/search_bar.html:1-452`, `pagination.html:1-54`, `back_button.html:1-27`,
  `breadcrumb.html:1-13`; `kernel/templates/includes/sidebar/opciones.html:387-397`;
  `kernel/static/custom/js/base.js:331-337,400-408`;
- `src/backends/sisoc_core/usuarios/web_navigation.py:195-200`, `sisoc_core/insumos/web_api_views.py:43-330`,
  `insumos/web_api_urls.py:1-22`, `usuarios/web_api_urls.py:1-77`;
- `src/frontends/apps/sisoc/src/routes/index.ts:1-47`, `routes/types.ts:1-50`, `routes/userImport.tsx:1-60,260,318-320`,
  `routes/bulkCredentials.tsx:164,221-223`, `routes/SisocShell.tsx:204,386`;
- `docs/operacion/deploy_entornos_docker_nginx_mysql.md:366,378-392`, `docs/operacion/nginx/sisoc-produccion.conf:39`;
- `docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md`;
- commit `668c61fe4` (timeouts de gunicorn: 75 s en el core y 65 s en los runtimes).

Desde el disco (untracked): `docs/plans/2026-T4/2026-10-27-2785-entregas-por-flujo.json` (flujo RF01 y
`contract_profiles`) y `2026-10-28-2785-comedores-legajo-base-m2.md`, que no menciona la rendición final.
