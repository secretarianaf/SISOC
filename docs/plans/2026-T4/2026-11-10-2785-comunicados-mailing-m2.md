# CM01.01, CM01.02, CM02.01, CM02.02, CM02.03, CM03.01: comunicados, publicación y mailing masivo

Estado M2 ejecutable: contrato basado en fuente HEAD 4ea95bcbe, sin ejecución de app, DB, correo, proveedores ni capturas.
Entregas del catálogo `2026-10-27-2785-entregas-por-flujo.json` (flujos CM01, CM02 y CM03, app `src/backends/comedores/comunicados`):
CM01.01 Audiencia y seguimiento de envío [L], CM01.02 Solicitud y estado del mailing sin envíos reales en pruebas [J],
CM02.01 Consulta y ficha de comunicado [L], CM02.02 Edición y gestión [M], CM02.03 Publicación y estados [W],
CM03.01 Lectura publicada por destinatario [L].
Perfiles según `contract_profiles` del catálogo: L = «Lectura y navegación», M = «Mutación de datos», W = «Acción o transición de circuito», J = «Job importación o envío».
Regla transversal: paridad nativa (S13: «mantene la paridad»). La API PWA existente (`/api/comunicados/...`) es un consumidor que no cambia y no se reutiliza como API web de React.

## Entregas y orden

| ID | Título | Perfil | Rutas nativas cubiertas | Depende de |
| --- | --- | --- | --- | --- |
| CM03.01 | Lectura publicada por destinatario | L | GET `/comunicados/`, GET `/comunicados/ver/<pk>/` (variante sin gestión) | Setup compartido `api/web/comedores/` (padre) |
| CM02.01 | Consulta y ficha de comunicado | L | GET `/comunicados/gestion/`, GET `/comunicados/ver/<pk>/` (variante con gestión) | CM03.01; se activa junto con CM02.03 |
| CM02.03 | Publicación y estados | W | POST `/comunicados/publicar/<pk>/`, POST `/comunicados/archivar/<pk>/`, POST `/comunicados/toggle-destacado/<pk>/` | CM02.01 (misma unidad de activación) |
| CM02.02 | Edición y gestión | M | GET/POST `/comunicados/crear/`, GET/POST `/comunicados/editar/<pk>/`, GET/POST `/comunicados/eliminar/<pk>/`, GET `/comunicados/destinatarios/<universo>/buscar/`, GET `/comunicados/destinatarios/<universo>/todos/` | CM02.01 |
| CM01.01 | Audiencia y seguimiento de envío | L | GET `/comunicados/mailing/`, GET `/comunicados/mailing/lotes/<pk>/`, GET `/comunicados/mailing/plantilla/` (binario nativo enlazado) | Setup compartido; independiente de CM02 |
| CM01.02 | Solicitud y estado del mailing sin envíos reales en pruebas | J | POST `/comunicados/mailing/`, POST `/comunicados/mailing/lotes/<pk>/reanudar/` | CM01.01 |

Montaje real: `comunicados.urls` se incluye con prefijo vacío en `src/backends/comedores/comedores_runtime/urls.py:25`, por lo que las URL públicas son exactamente las de `urls.py` con `/` inicial. El core reenvía al runtime Comedores porque `comunicados/` figura en `url_prefixes` de `src/backends/config/backends.json:269`. La API PWA se monta en `api/comunicados/` (`comedores_runtime/urls.py:22`, `backends.json:273`).

Un único módulo React `comunicados.tsx` posee los pathname de CM03/CM02 (comparten `/comunicados/ver/<pk>/`) y un módulo `comunicadosMailing.tsx` posee los de CM01. Cada entrega agrega capacidad al módulo; un pathname solo se activa en React cuando su entrega está aceptada.

## Base común de acceso y API

### Permisos reales (sin inventar códigos)

`src/backends/comedores/comunicados/permissions.py`:

- `is_admin(user)` (`:28-32`): `user.is_superuser` o alguno de `auth.role_admin`, `auth.role_administrador`, `auth.role_superadmin` (`ADMIN_PERMISSION_CODES`, `:15-19`). En el registro `src/backends/kernel/core/permissions/registry.py:33-34`, el grupo «Administrador» da `auth.role_administrador` y el grupo «Admin» da `auth.role_admin`.
- `COMUNICADO_CREATE_CODE = "comunicados.add_comunicado"` y `COMUNICADO_EDIT_CODE = "comunicados.change_comunicado"` (`:20-21`). Grupos que los otorgan (`registry.py:192-203`): «Comunicado Crear», «Comunicado Interno Crear» y «Comunicado Comedores Crear» → `comunicados.add_comunicado`; «Comunicado Editar», «Comunicado Publicar», «Comunicado Archivar», «Comunicado Interno Editar», «Comunicado Interno Publicar», «Comunicado Interno Archivar», «Comunicado Comedores Editar», «Comunicado Comedores Publicar» y «Comunicado Comedores Archivar» → `comunicados.change_comunicado`.
- `es_tecnico(user)` (`:155-159`) usa `UserPermissionService.es_tecnico_o_abogado`, que exige `auth.role_tecnico_comedor` o `auth.role_abogado_dupla` (`src/backends/kernel/users/services.py:30-33,453-457`).
- `can_manage_comunicados` (`:95-107`): admin, `add_comunicado` o `change_comunicado`. Ser técnico sin esos códigos no da gestión.
- `can_create_comunicado` (`:35-39`): admin o `add_comunicado`.
- `can_edit_comunicado(user, comunicado)` (`:42-60`): admin siempre; si no, `change_comunicado` y, con objeto, solo `estado == "borrador"`.
- `can_publish_comunicado`, `can_archive_comunicado`, `can_toggle_destacado` (`:63-74,134-141`): admin o `change_comunicado`.
- `can_delete_comunicado(user, comunicado)` (`:77-92`): solo admin y, con objeto, solo borrador.
- `can_seleccionar_destinatarios` (`:174-185`): `can_create_comunicado` o `can_edit_comunicado(user)` sin objeto.
- Alcance de destinatarios: `tiene_alcance_total_destinatarios` (`:168-171`) = admin o `add_comunicado`; si no, técnico → comedores de sus duplas activas (`src/backends/comedores/comedores/api.py:71-75`) y organizaciones de esos comedores; si no, vacío (`:197-216`).
- Las funciones v2 `can_*_comunicado_comedores` e `*_interno` (`:219-290`) no las usa ninguna vista; solo `can_create_comunicado_interno` la usa el formulario (`forms.py:157`). No se incorporan a la API.

Todas las vistas nativas usan `LoginRequiredMixin` (anónimo → redirect a login) y las denegaciones son `PermissionDenied` (403).

### Transporte web común (setup del padre y piezas de este contrato)

- Setup compartido del padre (solo se enuncia): agregar `api/web/comedores/` a `url_prefixes` de `comedores` en `src/backends/config/backends.json` y montar un agregador `path("api/web/comedores/", include(...))` en `src/backends/comedores/comedores_runtime/urls.py` que incluya `path("comunicados/", include("comunicados.web_api_urls"))`. En HEAD no existe ninguna API web de vertical: `config/urls.py:76-77` solo monta `api/web/insumos/` y `api/web/` del core.
- Archivos propuestos: `src/backends/comedores/comunicados/web_api_urls.py`, `web_api_views.py`, `web_api_serializers.py`.
- Cada vista: `authentication_classes = [SessionAuthentication]`, `permission_classes = [WebGatePermission]` (`src/backends/kernel/core/web_gate.py:308-327`) y, después, el chequeo de acción nativo exacto (mismas funciones de `permissions.py`). Sin sesión: 401 JSON del middleware o de `WebGateUnauthenticated`; requisito web pendiente: 403 JSON con `state` y `required_action_url` (lo emite el core por G1 antes de reenviar). Respuestas con `Cache-Control: private, no-store` y `Vary: Cookie` (el middleware las marca, `web_gate.py:281-283`).
- Patrón de reutilización: como `WebJobTransportMixin` del core (`src/backends/sisoc_core/usuarios/web_user_import.py:60-102`), las vistas web heredan o llaman a la vista/servicio nativo, convierten un 302 nativo en `{"ok": true, "redirect": "<Location>"}` y dejan el mensaje de Django en cola; el GET siguiente lo consume y lo devuelve en `messages: [{message, level}]` con la misma semántica que `pending_messages` (`web_user_import.py:49-57`). Como un vertical no importa código de `sisoc_core`, el helper se replica en `comunicados/web_api_views.py` con el mismo contrato (decisión técnica 3).
- `PermissionDenied` nativo → 403 `{"detail": "<mensaje nativo>"}`; `Http404`/objeto fuera del queryset → 404 `{"detail": "No encontrado."}`.
- Mutaciones: CSRF obligatorio (`csrf_protect`, cookie `csrftoken`, header o campo `csrfmiddlewaretoken`), `POST` multipart o urlencoded según la acción, sin reintento automático en el cliente. Un 504 con `uncertain: true` del proxy se presenta sin reenviar.
- No hay 409 en el comportamiento nativo: transiciones repetidas devuelven redirect con mensaje de advertencia o error (ver CM02.03). La API conserva esa semántica (200 `ok` + `redirect` + mensaje en cola) y no inventa conflictos.

## CM03.01 Lectura publicada por destinatario

### Rutas nativas

- GET `/comunicados/` · nombre `comunicados` (`urls.py:6-10`) · `ComunicadoListView` (`views.py:69-110`) · template `comunicados/comunicado_list.html:1-76`.
- GET `/comunicados/ver/<int:pk>/` · nombre `comunicados_ver` (`urls.py:23-27`) · `ComunicadoDetailView` (`views.py:184-211`) · template `comunicados/comunicado_detail.html:1-143`. Esta entrega cubre la variante para usuarios sin `can_manage_comunicados`.

### Acceso

- Login obligatorio (`LoginRequiredMixin`). Sin permiso adicional: cualquier usuario autenticado lee.
- Listado: solo `tipo = interno`, `estado = publicado` y `fecha_vencimiento` nula o futura (`views.py:77-86`). El contenido externo (institucional, comedores, organizaciones) no se muestra en web; su destinatario lo lee por la API PWA.
- Detalle sin gestión: mismo filtro (`views.py:197-202`); otro objeto → 404 (queryset vacío de `DetailView`).
- Con `can_manage_comunicados` el detalle no filtra (`views.py:195-196`): ver CM02.01.

### Datos y reglas

- Listado: `paginate_by = 20` (`views.py:74`); `ListView` estándar, `page` inválido o fuera de rango → 404 nativo, `page=last` válido. Orden `-destacado, -fecha_publicacion` (`views.py:92`). Búsqueda `titulo` por `icontains` (`views.py:88-90`). Anotación `adjuntos_count` (`Count("adjuntos", distinct=True)`, `views.py:79`).
- Contexto: `can_manage`, `filtro_titulo` y `additional_buttons` con «Gestionar» (`url` `/comunicados/gestion/`, clase `poncho-btn poncho-btn--neutro`, title «Gestionar comunicados») solo si `can_manage` (`views.py:94-110`).
- Tarjeta (`comunicado_list.html:22-61`): marca «Destacado» si `destacado`, título enlazado al detalle, `fecha_publicacion` `d/m/Y H:i`, creador `get_full_name` con fallback `username`, «N adjunto(s)» si `adjuntos_count`, cuerpo `truncatewords:50`, botón «Leer más».
- Detalle (`comunicado_detail.html`): título, badge de estado («Borrador», «Publicado», «Archivado»), cabecera «Comunicado Destacado» si corresponde, creador, «Publicado: d/m/Y H:i» si hay fecha, «Vence: d/m/Y H:i» y badge «Vencido» si `esta_vencido`, cuerpo con `linebreaks`, lista «Archivos Adjuntos» con enlace a `adjunto.archivo.url` (`target="_blank"`) y `nombre_original`. El pie de acciones solo aparece con permisos (CM02.01).
- Campos del modelo (`models.py:23-87`): `titulo` CharField 255, `cuerpo` TextField, `estado` choices `borrador|publicado|archivado`, `destacado` bool, `tipo` `interno|externo`, `subtipo` `""|institucional|comedores|organizaciones`, `fecha_publicacion` y `fecha_vencimiento` nulos, `usuario_creador` FK, `usuario_ultima_modificacion` FK nula, `fecha_creacion`, `fecha_ultima_modificacion`.

### Acciones y efectos

Solo lectura. Sin escrituras, correos ni jobs. Los adjuntos se descargan del enlace de media existente (`MEDIA_URL = "/media/"`, `src/backends/config/settings.py:275`), no por JSON.

### API web del runtime

- GET `/api/web/comedores/comunicados/?titulo=&page=` → 200:
  `{"results": [{"id", "titulo", "cuerpo_resumen", "destacado", "fecha_publicacion", "creador", "adjuntos_count", "detail_url"}], "page": {"number", "num_pages", "count", "previous", "next"}, "filtro_titulo", "can_manage", "gestion_url": "/comunicados/gestion/" | null, "messages"}`.
  `cuerpo_resumen` lo produce el backend con `django.utils.text.Truncator(cuerpo).words(50)` (mismo efecto que `truncatewords:50`); fechas ya formateadas `d/m/Y H:i` en hora local. Página inválida → 404 `{"detail": "Página no válida."}` (paridad con el 404 nativo).
- GET `/api/web/comedores/comunicados/<pk>/` → 200 `{"id", "titulo", "cuerpo", "estado", "estado_label", "destacado", "fecha_publicacion", "fecha_vencimiento", "esta_vencido", "creador", "adjuntos": [{"id", "nombre_original", "url"}], "permisos": {...}, "messages"}`; fuera del queryset nativo → 404. Mismo queryset de `ComunicadoDetailView.get_queryset` (se llama a la vista o se extrae el queryset a un helper compartido sin cambiar su lógica).
- Serializers en `web_api_serializers.py` (no reutilizar `serializers.ComunicadoSerializer` de la PWA).

### Módulo React

- `src/frontends/apps/sisoc/src/routes/comunicados.tsx` + `comunicados.test.tsx`; pathname `/comunicados/` y `/comunicados/ver/<pk>/`. Registro en `ROUTES` de `routes/index.ts` antes de `businessRoute(SHELL_ROUTES)` (navegación de página completa como `userImport`, porque el nativo navega por redirects y mensajes de Django).
- Volver: ninguna de las dos vistas define `volver_url`, así que el destino nativo es `href="/"` con historial de `volver.js` (`src/backends/kernel/templates/components/back_button.html`). React usa `backHref: "/"` y conserva el retorno por historial.

### Criterios de aceptación

- Título de página «Comunicados»; barra de búsqueda con título «Buscar comunicado», placeholder «Buscar por título...», ayuda «Buscar por título.», «Resetear» a `/comunicados/` (`comunicado_list.html:19`).
- Vacío: «No hay comunicados publicados.» (`comunicado_list.html:66`). Botón «Leer más». Marca «Destacado». «adjunto(s)».
- Detalle: «Comunicado Destacado», «Publicado:», «Vence:», «Vencido», «Archivos Adjuntos».
- Orden de Tab: Volver → búsqueda → botón buscar → «Resetear» → «Gestionar» (si aplica) → por tarjeta: título y «Leer más» → paginación.
- Regla visual S13: paridad estructural y diff perceptual ≤ 1 % sin antialiasing, tolerancia 2 CSS px, desktop y móvil, por estado (con datos, vacío, destacado, con adjuntos, vencido en detalle de gestión).

### Casos de prueba

- Backend (`src/backends/comedores/tests/test_comunicados_web_api.py`): anónimo 401; usuario sin permisos ve solo internos publicados vigentes; externo, borrador, archivado y vencido → no listados y detalle 404; filtro `titulo`; orden destacados primero; `page` inválido 404; `adjuntos_count` sin N+1 (análogo a `test_listado_publico_no_hace_consultas_n_mas_1_para_adjuntos`).
- Frontend (vitest): render de tarjetas, vacío, error de carga, 403 con requisito web, enlaces a detalle y a gestión solo con `can_manage`.
- Diferencial: `test_comunicados_views_unit.py`, `test_comunicados_acciones_unit.py` (listado público) y `test_comunicados_api_unit.py` pasan sin cambios; las rutas nativas responden igual.
- Visual: capturas pareadas nativo/React por estado.

### Riesgos

- Reutilizar la API PWA ampliaría contenido: `ComunicadoInstitucionalViewSet` y `ComunicadoComedorViewSet` (`api_views.py:15-69`) aceptan `HasAPIKey | IsAuthenticated`, sirven comunicados externos y el de comedor no valida que el usuario pertenezca al comedor. Queda como consumidor PWA intacto.
- Adjuntos por URL de media directa: se conserva el comportamiento nativo; no se agrega protección nueva (ver Incertidumbres).

## CM02.01 Consulta y ficha de comunicado

### Rutas nativas

- GET `/comunicados/gestion/?titulo=&estado=&tipo=&page=` · `comunicados_gestion` (`urls.py:12-16`) · `ComunicadoGestionListView` (`views.py:113-181`) · `comunicado_gestion_list.html:1-246`.
- GET `/comunicados/ver/<pk>/` (variante con gestión) · `ComunicadoDetailView` (`views.py:184-211`) · `comunicado_detail.html:85-140`.

### Acceso

- Gestión: `can_manage_comunicados` en `dispatch`; si no, 403 «No tiene permisos para gestionar comunicados.» (`views.py:120-123`).
- Alcance del listado: si `es_tecnico` y no `is_admin`, solo `tipo = externo` con comedor u organización dentro de su alcance (`views.py:129-140`, `.distinct()`). Admin y demás gestores ven todo.
- Asimetría a conservar: el detalle para gestores no aplica ese alcance (`views.py:195-196`); un técnico gestor puede abrir por ID un comunicado fuera de su listado. Se documenta y no se corrige en la migración.
- Botones del detalle: `can_edit` (con objeto), `can_publish`, `can_archive`, `can_delete` (con objeto) (`views.py:206-210`).

### Datos y reglas

- `paginate_by = 20`, orden `-fecha_creacion` (`views.py:118,154`). Filtros: `titulo` `icontains`, `estado` exacto y `tipo` exacto, sin validar el valor (un valor desconocido devuelve lista vacía) (`views.py:143-152`).
- Contexto: `can_create`, `can_edit` (sin objeto), `can_publish`, `can_archive`, `can_toggle_destacado`, filtros, `estados`, `tipos`, `is_admin`, `es_tecnico` (técnico no admin) y botón adicional «Mailing masivo» (`/comunicados/mailing/`, title «Enviar mailing masivo») solo para admin (`views.py:156-181`).
- Columnas (`comunicado_gestion_list.html:79-89`): «ID», «Destacado», «Título», «Tipo», «Estado», «Creación», «Publicación», «Creador», «Acciones». Título `truncatewords:8`; tipo «Interno»/«Externo»; estado «Borrador», «Publicado» o «Vencido» (publicado vencido), «Archivado»; creación `d/m/Y`; publicación `d/m/Y` o «-».
- Acciones por fila (`:150-215`): «Ver» siempre; «Editar» y «Publicar» solo si borrador y `can_edit` (y `can_publish` para publicar); «Archivar» si publicado y `can_archive`; destacado si publicado, `tipo != externo` y `can_toggle_destacado`, con title «Quitar destacado» o «Marcar como destacado».
- Filtro «Tipo» oculto para técnico no admin (`:34-45`). «Limpiar búsqueda» conserva estado y tipo (`:50-54`). Contador `(N)` solo si hay paginación (`:63`). Enlace «Ver Vista Pública» a `/comunicados/`.
- Pie del detalle (`comunicado_detail.html:86-140`): «Creado: d/m/Y H:i», «| Modificado por: ...», «Editar», «Publicar», «Archivar», «Eliminar» según permisos y estado.

### Acciones y efectos

Solo lectura en esta entrega. Los botones de acción los atiende CM02.03 (misma unidad de activación) y los enlaces «Nuevo», «Editar» y «Eliminar» apuntan a pathname de CM02.02 (página nativa hasta que se active).

### API web del runtime

- GET `/api/web/comedores/comunicados/gestion/?titulo=&estado=&tipo=&page=` → 200 `{"results": [{"id", "titulo", "titulo_corto", "tipo", "estado", "esta_vencido", "destacado", "fecha_creacion", "fecha_publicacion", "creador", "acciones": {"editar", "publicar", "archivar", "destacado"}}], "page", "filtros": {"titulo", "estado", "tipo"}, "estados", "tipos", "flags": {"can_create", "is_admin", "es_tecnico"}, "mailing_url": "/comunicados/mailing/" | null, "messages"}`. Sin gestión → 403 con el mensaje nativo. `acciones` se calcula en backend con las mismas condiciones del template.
- El detalle es el mismo GET de CM03.01; para gestores agrega `permisos: {"editar", "publicar", "archivar", "eliminar"}`, `fecha_creacion` y `modificado_por`.

### Módulo React

Mismo `comunicados.tsx`; agrega `/comunicados/gestion/`. Volver nativo `href="/"` (sin `volver_url`). «Mailing masivo» y «Nuevo» son enlaces.

### Criterios de aceptación

- Título «Gestión de Comunicados»; barra con placeholder «Buscar comunicado...», «Nuevo» si `can_create`, «Mailing masivo» si admin; selects «Estado» (opciones «Todos», «Borrador», «Publicado», «Archivado») y «Tipo» («Todos», «Interno», «Externo»), con envío al cambiar.
- Encabezado «Comunicados», enlace «Ver Vista Pública», vacío «No hay comunicados.» (`:225`).
- Orden de Tab: Volver → búsqueda → buscar → «Resetear» → «Nuevo» → «Mailing masivo» → «Estado» → «Tipo» → «Limpiar búsqueda» → «Ver Vista Pública» → por fila: título, «Ver», «Editar», «Publicar», «Archivar», destacado → paginación.
- S13 por rol (admin, gestor `change`, gestor `add`, técnico gestor) y estado (vacío, filtros activos, vencido).

### Casos de prueba

- Backend: sin gestión 403; técnico gestor ve solo externos de su alcance (comedor y organización) sin duplicados; admin ve todo; filtros; botón destacado ausente para externos y borradores; «Mailing masivo» solo admin; detalle de gestor muestra borrador; detalle técnico fuera de alcance responde 200 (asimetría fijada).
- Frontend: render por flags, selects que navegan con query, «Limpiar búsqueda» que conserva filtros (análogo a `test_gestion_limpiar_busqueda_preserva_filtros_activos`).
- Diferencial y visual como CM03.01.

### Riesgos

- La API PWA solo cubre publicados: no acredita paridad de borradores ni de gestión; esta API se escribe sobre las vistas nativas.
- Activar CM02.01 sin CM02.03 dejaría botones sin destino web: por eso se activan juntos.

## CM02.03 Publicación y estados

### Rutas nativas

- POST `/comunicados/publicar/<pk>/` · `comunicados_publicar` (`urls.py:39-43`) · `ComunicadoPublicarView` (`views.py:428-443`).
- POST `/comunicados/archivar/<pk>/` · `comunicados_archivar` (`urls.py:44-48`) · `ComunicadoArchivarView` (`views.py:446-459`).
- POST `/comunicados/toggle-destacado/<pk>/` · `comunicados_toggle_destacado` (`urls.py:49-53`) · `ComunicadoToggleDestacadoView` (`views.py:462-484`).
- Disparadores: formularios en `comunicado_gestion_list.html:166-212` y `comunicado_detail.html:105-129`, con confirmación «¿Publicar este comunicado?» y «¿Archivar este comunicado?» (`data-confirm-click`). Sin template propio. GET → 405 (solo `post`).

### Acceso

- Publicar: `require_publish_permission` → 403 «No tiene permisos para publicar comunicados.»; archivar: 403 «No tiene permisos para archivar comunicados.»; destacado: 403 «No tiene permisos para modificar el estado destacado.» (`permissions.py:122-147`). El permiso se evalúa antes de buscar el objeto: sin permiso, un ID inexistente da 403, no 404.
- Objeto con `get_object_or_404(Comunicado, pk=pk)` sin alcance de técnico (asimetría con el listado, se conserva).

### Datos y reglas

- Publicar (`views.py:435-441`): publicado → warning «El comunicado ya está publicado.»; archivado → error «No se puede publicar un comunicado archivado.»; borrador → `Comunicado.publicar` (`models.py:97-102`): `estado = publicado`, `fecha_publicacion = now`, `usuario_ultima_modificacion`. No valida vencimiento ni destinatarios.
- Archivar (`views.py:453-457`): archivado → warning «El comunicado ya está archivado.»; borrador o publicado → `Comunicado.archivar` (`models.py:104-109`): `estado = archivado`, `destacado = False`, `usuario_ultima_modificacion`.
- Destacado (`views.py:469-482`): no publicado → error «Solo se puede modificar el destacado de comunicados publicados.»; publicado → invierte `destacado`, guarda modificador y responde «Comunicado marcado como destacado.» o «Comunicado desmarcado como destacado.». La vista acepta externos aunque el template no muestre el botón para ellos (asimetría a conservar).
- No hay transición de publicado o archivado a borrador.

### Acciones y efectos

- Escritura con `save()` completo sobre la fila; sin transacción explícita, sin historial ni auditoría adicional, sin correo ni notificación push en el código de estas vistas. Siempre redirect a `comunicados_gestion` (también desde el detalle).
- Mensajes literales ya citados; éxito «Comunicado publicado correctamente.» y «Comunicado archivado correctamente.».

### API web del runtime

- POST `/api/web/comedores/comunicados/<pk>/publicar/`, `/archivar/`, `/destacado/` (urlencoded, CSRF) → 200 `{"ok": true, "redirect": "/comunicados/gestion/"}` en los tres desenlaces nativos (éxito, advertencia o error de estado); el mensaje queda en cola y lo devuelve el siguiente GET de gestión. 403 con el mensaje nativo; 404 si el ID no existe y hay permiso; 401 sin sesión; 405 en GET.
- Implementación: delegar en las vistas nativas o en `Comunicado.publicar/archivar` con el mismo orden de chequeos; no agregar `select_for_update` ni 409 (decisión técnica 5).

### Módulo React

`comunicados.tsx`: los botones de fila y del detalle hacen un único POST con confirmación previa (mismos textos), deshabilitan el botón mientras esperan y navegan a `redirect`. Ante 504 `uncertain` o respuesta perdida muestran «No se pudo confirmar el resultado. Actualice la página antes de volver a intentar.» y no reenvían.

### Criterios de aceptación

- Confirmaciones «¿Publicar este comunicado?» y «¿Archivar este comunicado?»; titles «Publicar», «Archivar», «Quitar destacado», «Marcar como destacado».
- Mensajes nativos visibles tras el redirect, con el mismo nivel (success, warning, error).
- Tab: el botón de acción es enfocable y la confirmación devuelve el foco al disparador si se cancela.

### Casos de prueba

- Backend: borrador → publicado con fecha; publicado repetido → warning sin cambios; archivado → error; archivar borrador y publicado; archivar limpia destacado; destacado en borrador → error; alternancia; sin permiso 403 con ID inexistente; anónimo 401; GET 405; CSRF ausente 403. Paridad con `test_comunicados_acciones_unit.py`.
- Frontend: doble clic no genera dos POST; `uncertain` no reenvía; confirmación cancelada no envía.
- Diferencial: los POST nativos siguen respondiendo 302 a gestión.

### Riesgos

- Cambio de estado entre lectura y envío: resultado observable igual que el nativo (mensaje de advertencia o error), sin update arbitrario de estado.
- Efectos externos: ninguno en el código; si una señal futura notificara, no está en HEAD (ver Incertidumbres).

## CM02.02 Edición y gestión

### Rutas nativas

- GET/POST `/comunicados/crear/` · `comunicados_crear` (`urls.py:18-22`) · `ComunicadoCreateView` (`views.py:308-356`) · `comunicado_form.html:1-226`.
- GET/POST `/comunicados/editar/<pk>/` · `comunicados_editar` (`urls.py:28-32`) · `ComunicadoUpdateView` (`views.py:359-407`) · mismo template.
- GET/POST `/comunicados/eliminar/<pk>/` · `comunicados_eliminar` (`urls.py:33-37`) · `ComunicadoDeleteView` (`views.py:410-425`) · `comunicado_confirm_delete.html:1-58`.
- GET `/comunicados/destinatarios/<universo>/buscar/?<filtros>&page=` · `comunicados_destinatarios_buscar` (`urls.py:55-59`) · `DestinatariosBuscarView` (`views.py:595-616`).
- GET `/comunicados/destinatarios/<universo>/todos/?<filtros>` · `comunicados_destinatarios_todos` (`urls.py:60-64`) · `DestinatariosSeleccionarTodosView` (`views.py:619-632`). Panel `partials/destinatarios_panel.html:1-80`, JS `static/custom/js/comunicadosDestinatarios.js` y `comunicadosForm.js`.

### Acceso

- Crear: `require_create_permission` en `dispatch` → 403 «No tiene permisos para crear comunicados.» (GET y POST).
- Editar: `get_object` sin alcance (404 si no existe) y `require_edit_permission(user, objeto)` → 403 «No tiene permisos para editar este comunicado.»; no admin solo edita borradores. El técnico gestor puede editar por ID un borrador fuera de su alcance de listado (asimetría a conservar).
- Eliminar: `get_object` (404) y `can_delete_comunicado` → 403 «No tiene permisos para eliminar este comunicado.»; solo admin y solo borrador, tanto en GET como en POST.
- Destinatarios: `require_seleccionar_destinatarios_permission` → 403 «No tiene permisos para seleccionar destinatarios de comunicados.»; universo distinto de `comedores` u `organizaciones` → 404 `{"error": "Universo desconocido."}`. El alcance lo aplica siempre el servicio (`services_destinatarios.py:38-53`).

### Datos y reglas

`ComunicadoForm` (`forms.py:70-233`), campos: `titulo` (CharField 255, requerido), `cuerpo` (requerido, textarea 6 filas), `tipo` (choices), `subtipo` (opcional), `destacado` (switch), `para_todos_comedores` (switch), `comedores` y `organizaciones` (ModelMultipleChoice con `CommaSeparatedIdsInput`: un input oculto con IDs separados por coma, también acepta valores repetidos, `forms.py:21-47`), `fecha_vencimiento` (`datetime-local`, formato `%Y-%m-%dT%H:%M`), `archivos_adjuntos` (múltiple, opcional).

- Querysets acotados: `comedores` a `get_ids_comedores_del_usuario` y `organizaciones` a `get_ids_organizaciones_del_usuario` ordenadas por nombre (`forms.py:128-136`); un ID fuera de alcance produce el error estándar de `ModelMultipleChoiceField`.
- Técnico no admin: `tipo` solo «Comunicación Externa», `subtipo` solo «Comunicación a Comedores» y «Comunicación a Organizaciones» (inicial comedores), `destacado` oculto en `False` (`forms.py:139-154`). Sin `can_create_comunicado_interno`: `tipo` solo externo (`:157-161`).
- `clean` (`forms.py:186-215`): externo + comedores sin `para_todos_comedores` y sin comedores → error en `comedores` «Debe seleccionar al menos un comedor o marcar 'Enviar a todos los comedores'.»; externo + organizaciones sin organizaciones → «Debe seleccionar al menos una organización.».
- `clean_archivos_adjuntos` (`forms.py:217-233`): extensiones `.pdf .jpg .jpeg .png`; mensajes «El archivo '<nombre>' tiene una extensión no permitida.» y «El archivo '<nombre>' supera el tamaño máximo de 10 MB.» (10 × 1024 × 1024 bytes).
- Formset `ComunicadoAdjuntoFormSet` (`forms.py:246-252`): `extra=1`, `can_delete=True`, campo `archivo`; en edición lista «Archivos actuales» con casilla «Eliminar».
- Destinatarios: búsqueda paginada de 25 (`PAGE_SIZE`), «agregar todos» con tope `MAX_SELECCION_MASIVA = 2000` (`services_destinatarios.py:31-35`); respuesta `{"results": [{"id", "nombre", "detalle"}], "total", "has_more", "page", "max_seleccion_masiva"}` y, en todos, `{"results", "total", "truncado", "max_seleccion_masiva"}` con `results` vacío si supera el tope (`:68-124`). Filtros combinables por query de los motores `COMEDOR_ADVANCED_FILTER` y `ORGANIZACION_ADVANCED_FILTER`, orden `nombre, id` (`comedores/api.py:154-215`). Configuración de filtros: `get_filtros_destinatarios_config()`; etiquetas previas: `etiquetas_de_seleccion` (`:153-173`).

### Acciones y efectos

- Guardado (`views.py:299-305`) en `transaction.atomic()`: `form.save()`, formset de adjuntos, `_handle_comedores` y archivos nuevos `ComunicadoAdjunto(archivo, nombre_original)` en `comunicados/adjuntos/` (`models.py:248-251`).
- `_handle_comedores` (`views.py:267-297`): externo institucional limpia comedores y organizaciones y fuerza `para_todos_comedores = False`; externo comedores limpia organizaciones y, con «para todos», fija los comedores del alcance del usuario en ese momento, si no los elegidos; externo organizaciones limpia comedores; interno limpia todo y `subtipo = ""`.
- Crear fija `usuario_creador` y `estado = borrador`; éxito «Comunicado creado correctamente.». Editar fija `usuario_ultima_modificacion`; éxito «Comunicado actualizado correctamente.». Ambos redirigen a `/comunicados/gestion/`. Formset inválido re-renderiza sin guardar.
- Eliminar: GET muestra confirmación; POST elimina en cascada `ComunicadoAdjunto` (FK CASCADE), mensaje «Comunicado eliminado correctamente.», redirect a gestión. Eliminación física de filas; no se observó borrado de archivos en storage (ver Incertidumbres). No hay soft delete.
- Sin correo ni jobs. Un error al guardar un adjunto revierte todo (`test_create_rollbackea_todo_si_falla_guardado_de_adjunto`).

### API web del runtime

- GET `/api/web/comedores/comunicados/crear/` → 200 metadata del formulario: campos con `name`, `label`, `required`, `choices` efectivas para el usuario, `initial`, `hidden` (destacado del técnico), `filters_config`, `seleccionados` (etiquetas), `es_tecnico`, `max_adjunto_bytes`, `extensiones`, `messages`.
- POST `/api/web/comedores/comunicados/crear/` (multipart, CSRF): los mismos nombres de campo del formulario nativo (incluidos `comedores` y `organizaciones` como CSV y `archivos_adjuntos` repetido, más el management form del formset) → 200 `{"ok": true, "redirect": "/comunicados/gestion/"}` o 400 `{"errors": form.errors.get_json_data(), "formset_errors": [...]}`.
- GET/POST `/api/web/comedores/comunicados/<pk>/editar/`: idem, metadata con valores actuales y adjuntos `{"id", "nombre_original", "url"}` con su prefijo de formset; 403/404 nativos.
- GET/POST `/api/web/comedores/comunicados/<pk>/eliminar/`: GET → `{"titulo", "fecha_creacion", "creador", "adjuntos_count"}`; POST → 200 `{"ok": true, "redirect"}`; 403/404 nativos.
- GET `/api/web/comedores/comunicados/destinatarios/<universo>/buscar/` y `/todos/`: llaman a `buscar_comedores`, `buscar_organizaciones`, `seleccionar_todos_comedores` y `seleccionar_todas_organizaciones` con el mismo request y devuelven exactamente su JSON; mismos 403 y 404.
- Reutilización estricta: `ComunicadoForm(user=...)`, `ComunicadoAdjuntoFormSet` y `ComunicadoPersistMixin._save_comunicado_with_related` (extraer a función de servicio sin cambiar lógica si la vista web no puede heredar la vista nativa).

### Módulo React

`comunicados.tsx` agrega `/comunicados/crear/`, `/comunicados/editar/<pk>/` y `/comunicados/eliminar/<pk>/`. El panel de destinatarios se reimplementa en React con el mismo DOM y textos del partial y consume los endpoints web. «Cancelar» del formulario y de la confirmación apunta a `/comunicados/gestion/` (es cancelar de formulario, `test_boton_volver_unificado.py`); el Volver global usa `href="/"`.

### Criterios de aceptación

- Títulos «Crear Comunicado» y «Editar Comunicado»; paneles «Configuración», «Destinatarios», «Redacción», «Archivos Adjuntos», «Información» (solo edición); etiquetas «Tipo de Comunicado», «Subtipo», «Vencimiento», «Marcar como Destacado», «Enviar a todos los comedores», «Título», «Contenido»; ayudas «Interna: SISOC · Externa: App móvil (PWA)», «Institucional: broadcast · Comedores: dirigido», «Opcional. Deja de mostrarse en esa fecha.», «Aparece fijado arriba de la lista.», «Se enviará a todos los comedores que tiene asignados.», «Puedes agregar múltiples archivos haciendo clic varias veces.»; botones «Agregar archivos», «Cancelar», «Guardar Comunicado».
- Panel de destinatarios: «Filtro», «Limpiar», «Buscar», «Los filtros se combinan entre sí (AND). Buscá, elegí, y volvé a filtrar para seguir sumando destinatarios.», «Usá los filtros y presioná Buscar.», «Agregar todos los resultados», «Seleccionados (N)», «Quitar todos», «No hay destinatarios seleccionados.», «No se encontraron resultados con esos filtros.», «N resultado(s) encontrado(s).», «No se pudo completar la búsqueda. Intentá nuevamente.», mensaje de tope «Son N resultados y el máximo para agregar de una vez es M. Afiná los filtros.».
- Confirmación de baja: «Confirmar Eliminación», «¿Estás seguro de que deseas eliminar el siguiente comunicado?», «Este comunicado tiene N archivo(s) adjunto(s) que también serán eliminados.», «Esta acción no se puede deshacer.», «Cancelar», «Sí, Eliminar».
- Visibilidad condicional igual al nativo: subtipo oculto para interno salvo técnico; destacado oculto para externo o técnico; paneles de destinatarios según subtipo; selector oculto con «para todos».
- Tab: Volver → tipo → subtipo → vencimiento → destacado → destinatarios (switch, filtros, buscar, resultados, seleccionados) → título → contenido → «Agregar archivos» → adjuntos actuales → «Cancelar» → «Guardar Comunicado». S13 por rol (admin, técnico, editor sin alcance) y estado (errores, adjuntos, selección previa).

### Casos de prueba

- Backend: sin permiso 403 en GET y POST; editor no admin sobre publicado 403; admin edita publicado; eliminar no admin o no borrador 403; validaciones de `clean` y adjuntos; IDs fuera de alcance rechazados; técnico con choices limitadas; «para todos» guarda el alcance; interno limpia destinatarios; rollback ante fallo de adjunto; destinatarios con alcance de técnico, editor sin alcance vacío, universo desconocido 404, tope 2000; CSRF ausente 403; formato no multipart 415.
- Frontend: errores de campo con 400, conservación de la selección tras error, no duplicar POST, `uncertain` sin reenvío.
- Diferencial: `test_comunicados_views_unit.py`, `test_comunicados_forms_unit.py` y `test_comunicados_destinatarios_unit.py` sin cambios.

### Riesgos

- Subidas grandes: varios adjuntos de hasta 10 MB pueden superar los 60 s de la ventana G1 en equipos lentos. Decisión: mantener el POST JSON multipart y, ante 504 `uncertain`, mostrar «No se pudo confirmar el resultado. Revise la gestión de comunicados antes de volver a guardar.» sin reenviar (decisión técnica 6).
- Comportamiento nativo con JS al adjuntar archivos: si el POST devuelve el formulario con errores, `comunicadosForm.js:138-153` recarga la página y pierde los errores. React mostrará los errores 400 (equivale al envío sin JS); se registra como diferencia de comportamiento, no visual.
- Destinatarios masivos: la selección se envía como un único CSV para no superar `DATA_UPLOAD_MAX_NUMBER_FIELDS` (`forms.py:21-27`); React debe mantener ese formato.

## CM01.01 Audiencia y seguimiento de envío

### Rutas nativas

- GET `/comunicados/mailing/` · `comunicados_mailing` (`urls.py:66-70`) · `MailingUploadView` (`views.py:504-520`) · `mailing_form.html:1-106`.
- GET `/comunicados/mailing/lotes/<pk>/?page=` · `comunicados_mailing_detalle` (`urls.py:76-80`) · `MailingJobDetailView` (`views.py:551-575`) · `mailing_job_detail.html:1-204`.
- GET `/comunicados/mailing/plantilla/` · `comunicados_mailing_plantilla` (`urls.py:71-75`) · `MailingTemplateView` (`views.py:487-501`).

### Acceso

- Las tres vistas exigen `is_admin`; si no, `PermissionDenied` sin mensaje (403).
- Asimetría a conservar: «Últimos lotes de mailing» muestra solo los lotes del propio usuario (`get_recent_mailing_jobs(requested_by=user)`, `services_mailing_jobs.py:83-87`), pero el detalle `get_mailing_job_or_404` no filtra por solicitante (`:90-94`): cualquier admin abre cualquier lote por ID. Inexistente → 404 «No existe el lote solicitado.».

### Datos y reglas

- Formulario (contexto): `form_title = "Envío de mailing masivo"`, `template_download_url`, `recent_jobs` (10 más recientes, orden `-requested_at, -id`).
- Tabla «Últimos lotes de mailing» (`mailing_form.html:47-97`): «Lote» (`#id`), «Fecha» (`d/m/Y H:i`), «Estado» (badge «Completado», «Fallido», «Procesando», «Pendiente»), «Asunto» (`truncatechars:30`), «Último mail enviado» (mail y «Fila N», o «-»), «Error» (o «-»), «Detalle» («Ver detalle»).
- Modelo `MailingJob` (`models.py:128-181`): `status` `pending|processing|completed|failed`, contadores `total_rows`, `processed_rows`, `sent_rows`, `rejected_rows`, `next_row_index`, `last_successful_row/mail`, `last_attempted_row/mail`, `last_error_message/at`, `resume_count`, `requested_at`, `started_at`, `finished_at`, `last_activity_at`; archivo en `comunicados/mailing/jobs/AAAA/MM/DD/`. `MailingJobRow` (`:184-219`): `fila`, `mail_destino`, `status` `sent|failed`, `mensaje`, `attempts`, `processed_at`, único por `job, fila`. `MailingJobAttachment` (`:222-238`) en `comunicados/mailing/attachments/%Y/%m/%d/`.
- Detalle: filas ordenadas `fila, id`, `Paginator` de 50 con `get_page` tolerante (valor inválido → página 1, fuera de rango → última) (`views.py:553,562-564`); `is_resume_available = status == failed` (`services_mailing_jobs.py:97-98`); `volver_url = /comunicados/mailing/`.
- Plantilla: XLSX en memoria con hoja `mailing` y encabezado `mail` (`services_mailing.py:171-179`).

### Acciones y efectos

- Lectura. La plantilla responde `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` con `Content-Disposition: attachment; filename="plantilla_mailing.xlsx"` (`views.py:492-500`); no persiste nada.
- Adjuntos del lote enlazados por `attachment.archivo.url` (media directa).

### Exportaciones

Solo la plantilla XLSX. Se conserva como GET nativo enlazado desde React; no se pasa por JSON.

### API web del runtime

- GET `/api/web/comedores/comunicados/mailing/` → 200 `{"form_title", "fields": [{"name", "label", "help_text", "required", "accept"}], "template_download_url": "/comunicados/mailing/plantilla/", "recent_jobs": [{"id", "requested_at", "status", "asunto_corto", "last_successful_mail", "last_successful_row", "last_error_message", "detail_url"}], "messages"}`. No admin → 403.
- GET `/api/web/comedores/comunicados/mailing/jobs/<pk>/?page=` → 200 `{"job": {"id", "original_filename", "requested_at", "status", "asunto", "cuerpo", "resume_count", "total_rows", "processed_rows", "sent_rows", "rejected_rows", "last_successful_mail", "last_successful_row", "last_attempted_mail", "last_attempted_row", "last_error_message", "last_error_at", "attachments": [{"nombre_original", "url"}]}, "rows": [{"fila", "status", "mail_destino", "attempts", "mensaje"}], "page": {"number", "num_pages", "previous", "next"}, "is_resume_available", "resume_url", "upload_url": "/comunicados/mailing/", "messages"}`; 403 no admin; 404 inexistente.
- Lecturas puras: no reclaman lotes, no tocan `last_activity_at` y no envían correo.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/comunicadosMailing.tsx` + `comunicadosMailing.test.tsx`; pathname `/comunicados/mailing/` y `/comunicados/mailing/lotes/<pk>/`; registro en `ROUTES` de `index.ts` antes de `businessRoute`. Reutiliza `useWebResource`, `renderLoad`, `Pagination` y `ResumeButton` exportados por `userImport.tsx` (`jobWidgets`) en lugar de duplicarlos.
- Volver: formulario `href="/"` (sin `volver_url`); detalle `backHref: "/comunicados/mailing/"` (`views.py:573`). «Actualizar estado» es un enlace que recarga el detalle; no hay polling.

### Criterios de aceptación

- Formulario: título «Mailing masivo», breadcrumb «Gestión» › «Comunicados» › «Mailing masivo», encabezado «Envío de mailing masivo», texto de ayuda de `mailing_form.html:22-26`, botones «Descargar plantilla», «Crear lote de mailing», «Volver» (a `/comunicados/gestion/`), «Últimos lotes de mailing», vacío «Todavía no hay lotes creados para mailing masivo.».
- Detalle: título «Detalle de lote de mailing», breadcrumb con «Lote #N», «Actualizar estado», «Reanudar» solo si fallido, «Asunto:», «Reanudaciones:», tarjetas «Filas totales», «Filas procesadas», «Enviadas», «Rechazadas», «Último mail enviado correctamente» / «Todavía no hay envíos exitosos.», «Último mail intentado» / «Todavía no se intentó ninguna fila.», «Cuerpo del mensaje», «Archivos adjuntos», «Causa del error» y «Registrado el ...», aviso «El lote está en curso fuera de la request web. Use Actualizar estado para refrescar el detalle.», columnas «Fila», «Estado», «Mail destino», «Intentos», «Detalle», badges «Enviado» y «Fallido», vacío «Aún no hay filas procesadas para este lote.», paginación «Anterior», «Página N de M», «Siguiente».
- Tab: Volver → breadcrumb → «Actualizar estado» → «Reanudar» → adjuntos → paginación. S13 por estado: pendiente, procesando, completado, fallido con error, con y sin adjuntos, paginado.

### Casos de prueba

- Backend: no admin 403 en los dos GET y en la plantilla; anónimo 401; recientes solo propios; detalle de lote ajeno visible para otro admin (asimetría fijada); 404 inexistente; `page` inválido tolerado; plantilla con content-type, nombre y encabezado `mail`; ningún GET altera el lote ni llena `mail.outbox`.
- Frontend: badges por estado, «Reanudar» solo con `is_resume_available`, enlaces de detalle y plantilla.
- Diferencial: las rutas nativas siguen idénticas; `test_admin_operaciones_comedores.py` (reanudar desde admin) sin cambios.

### Riesgos

- El detalle expone asunto, cuerpo, destinatarios y adjuntos de lotes de otros admins: es el comportamiento nativo y se conserva.
- En HEAD no hay tests de vistas web de mailing ni de `process_mailing_job`; la entrega agrega tests propios.

## CM01.02 Solicitud y estado del mailing sin envíos reales en pruebas

### Rutas nativas

- POST `/comunicados/mailing/` · `comunicados_mailing` · `MailingUploadView.form_valid` (`views.py:522-548`) · `mailing_form.html:28-43`.
- POST `/comunicados/mailing/lotes/<pk>/reanudar/` · `comunicados_mailing_reanudar` (`urls.py:81-85`) · `MailingJobResumeView` (`views.py:578-592`) · `mailing_job_detail.html:28-34`.
- Worker: comando `process_mailing_jobs` (`management/commands/process_mailing_jobs.py`) ejecutado por el servicio `mailing_worker` (`backends.json:305-308`; `docker/compose/docker-compose.produccion.yml:60-79`, `DJANGO_SERVICE_ROLE: mailing_worker`, `comedores_runtime.settings`, volumen `./media`).

### Acceso

- Upload: `is_admin` en `dispatch` (GET y POST). Reanudar: `is_admin` en `post` y luego `get_mailing_job_or_404` sin filtro de solicitante (cualquier admin reanuda cualquier lote fallido).

### Datos y reglas

`MailingUploadForm` (`forms.py:255-280`):

- `asunto`: CharField 255 requerido, label «Asunto», ayuda «El asunto que tendrá el correo electrónico.».
- `cuerpo`: requerido, label «Cuerpo», ayuda «El contenido del correo electrónico.».
- `archivo`: requerido, label «Archivo Excel», `FileExtensionValidator(["xlsx"])`, `accept=".xlsx"`, ayuda «Cargue un archivo .xlsx con una columna 'mail'.».
- `archivos_adjuntos`: múltiple opcional, label «Archivos adjuntos», ayuda «Opcionalmente, seleccione uno o más archivos para adjuntar al correo.». Sin validación de extensión ni tamaño (a diferencia del formulario de comunicados); se conserva.
- `validate_mailing_workbook` (`services_mailing.py:96-135`): hoja `mailing` o la activa; encabezado normalizado `mail`; errores literales «No se pudo leer el archivo Excel cargado.», «El archivo Excel esta vacio.», «El archivo debe incluir una columna llamada 'mail'.», «El archivo Excel no contiene filas con datos para procesar.». Se agregan al campo `archivo` con `build_mailing_error_message` (`views.py:531-533`). No valida direcciones en la carga.

### Acciones y efectos

- Crear lote (`create_mailing_job`, `services_mailing_jobs.py:53-74`): valida el libro, guarda `MailingJob` en `pending` con archivo y luego crea cada `MailingJobAttachment`. Sin `transaction.atomic`. No envía correos en la request. Mensaje «Lote de mailing creado. El procesamiento continuará en background. Puede seguir el estado desde el detalle del lote.» y redirect a `/comunicados/mailing/lotes/<pk>/`.
- Worker (`run_mailing_jobs_worker`, `:530-547`): ciclo con `MAILING_JOB_POLL_SECONDS` (2 s por defecto); `mark_stale_mailing_jobs_as_failed` pasa a `failed` los `processing` sin actividad por `MAILING_JOB_STALE_SECONDS` (900 s) con «El lote se interrumpio antes de finalizar. Puede reanudarlo desde la ultima fila pendiente.» (`:25-28,124-149`); `claim_next_mailing_job` toma el `pending` más antiguo con update condicional (`:152-176`).
- Proceso (`process_mailing_job`, `:436-512`): lee todas las filas con mail, cachea adjuntos con MIME por extensión, recorre desde `next_row_index`; por fila marca intento, `get_or_create` del `MailingJobRow`, `validate_email` y `EmailMessage(subject=asunto, body=cuerpo, from_email=None → DEFAULT_FROM_EMAIL, to=[mail]).send(fail_silently=False)` (`services_mailing.py:138-168`). Una dirección inválida («El mail '<x>' no es valido.») o un error de envío («Error enviando mail: ...») marca la fila y el lote `failed` y detiene el lote; no salta a la fila siguiente. Éxito avanza `next_row_index` y, en la última fila, `completed`.
- Reanudar (`request_resume_mailing_job`, `:101-121`): solo `failed` («Solo se pueden reanudar lotes fallidos.» como error); pasa a `pending`, limpia error y `finished_at`, incrementa `resume_count`, actualiza `last_activity_at`. Mensaje de éxito «El lote ha sido reanudado.»; redirect al detalle. El worker reintenta desde `next_row_index`, es decir, la fila que falló (incrementa `attempts`).
- Backend de correo (`settings.py:319-331`): `EMAIL_BACKEND` del entorno; vacío o inválido → `console.EmailBackend`. El admin también reanuda (`admin.py:89-105`, operación «reanudar»).

### API web del runtime

- POST `/api/web/comedores/comunicados/mailing/` (multipart, CSRF; campos `asunto`, `cuerpo`, `archivo`, `archivos_adjuntos` repetido) → 200 `{"ok": true, "redirect": "/comunicados/mailing/lotes/<pk>/"}`; 400 `{"errors": ...}` con los mensajes nativos (incluidos los del libro en `archivo`); 403 no admin; 415 si no es multipart. Llama a `create_mailing_job` y nada más: nunca procesa ni envía en la request.
- POST `/api/web/comedores/comunicados/mailing/jobs/<pk>/resume/` (urlencoded, CSRF) → 200 `{"ok": true, "redirect": "/comunicados/mailing/lotes/<pk>/"}` en éxito y también cuando el lote no está fallido (el error queda en cola, como el nativo); 403; 404.
- Duración: la request solo valida el XLSX (lectura `read_only` hasta la primera fila con mail) y guarda archivos; el envío ocurre en el job asíncrono existente, por lo que el envío nunca depende de la ventana de 60 s.

### Módulo React

`comunicadosMailing.tsx`: formulario con `FileField` y `postOnce` de `userImport.tsx`; «Reanudar» con `ResumeButton`. Ante `uncertain`: en la carga «No se pudo confirmar el resultado. Revise los últimos lotes antes de volver a cargar el archivo.» y en reanudar «No se pudo confirmar el resultado. Use Actualizar estado.» (textos ya usados por `userImport.tsx:126,231`, aquí con tildes); sin reenvío. «Descargar plantilla» es un enlace a `/comunicados/mailing/plantilla/` (decisión técnica 8).

### Criterios de aceptación

- Labels, ayudas y botones nativos citados; errores de campo bajo el input con el mismo marcado de crispy (como `FileField` de `userImport.tsx`).
- Mensaje de éxito nativo visible en el detalle tras el redirect; «El lote ha sido reanudado.» o «Solo se pueden reanudar lotes fallidos.» tras reanudar.
- El botón de envío queda deshabilitado durante el POST; un segundo clic no crea otro lote.
- S13 sobre el formulario con errores y el detalle tras crear o reanudar.

### Casos de prueba

- Todos los tests usan `settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` (fixture explícita además del override de pytest-django) y verifican `mail.outbox`; nunca configuran SMTP ni arrancan `run_mailing_jobs_worker` en bucle.
- Backend API: no admin 403; anónimo 401; CSRF ausente 403; 415; XLSX sin columna `mail`, vacío, ilegible o sin filas → 400 con el mensaje literal; extensión distinta de `.xlsx` → 400; éxito crea un `MailingJob` `pending` con adjuntos y `len(mail.outbox) == 0`; reanudar fallido → `pending` y `resume_count + 1`; reanudar no fallido → error en cola sin cambios; 404.
- Servicio (sin red): `process_mailing_job` con locmem envía una vez por fila válida con adjuntos; mail inválido deja el lote `failed` en esa fila; reanudar reintenta la misma fila; lote stale pasa a `failed`; `claim_next_mailing_job` no toma dos veces el mismo lote.
- Frontend: doble envío bloqueado, `uncertain` sin reenvío, errores 400 renderizados.
- Diferencial: POST nativos siguen con 302 y mismos mensajes; `test_admin_operaciones_comedores.py` sin cambios.

### Riesgos

- Envío real en relevamiento o pruebas: la carga solo encola, pero cualquier entorno con `mailing_worker` y SMTP configurado enviaría. Regla: el entorno visual y de relevamiento corre sin `mailing_worker` y con `EMAIL_BACKEND` locmem o consola; los lotes de captura se crean por fixture directa en la DB con cada estado; nunca se envía el formulario contra un entorno con SMTP.
- Carrera existente: el lote queda `pending` antes de crear sus adjuntos (`services_mailing_jobs.py:65-73`); el worker puede tomarlo y enviar sin adjuntos. Se conserva por paridad; corregir (transacción o crear `pending` al final) es un cambio de comportamiento aparte.
- Duplicados: si el envío se completa pero falla el registro posterior, o el worker muere tras enviar, el lote pasa a stale y la reanudación reenvía esa fila. No hay idempotencia por fila; es el comportamiento actual.
- Una dirección inválida detiene el lote y reanudar sin corregir el archivo vuelve a fallar en la misma fila.
- Subidas grandes con conexiones lentas pueden superar 60 s: el resultado se informa como incierto y el usuario revisa «Últimos lotes de mailing» antes de reintentar.

## Decisiones técnicas tomadas

1. **Dos módulos React** (`comunicados.tsx` y `comunicadosMailing.tsx`) en `ROUTES`, con navegación de página completa. Fundamento: el nativo funciona por redirects y mensajes de Django, y `/comunicados/ver/<pk>/` es compartido por CM03 y CM02; `userImport.tsx` ya resuelve el mismo patrón de lote con detalle y reanudación.
2. **API propia en `/api/web/comedores/comunicados/`** y no la API PWA. Fundamento: la PWA (`api_views.py:15-69`) solo sirve publicados externos, acepta API key o cualquier sesión y no aplica el alcance web; reutilizarla ampliaría contenido y no cubre borradores ni gestión.
3. **Transporte replicado en el vertical**: las vistas web envuelven las vistas o servicios nativos, convierten 302 en `{"ok", "redirect"}` y devuelven mensajes en cola, igual que `WebJobTransportMixin`. Fundamento: misma semántica sin importar `sisoc_core` desde un vertical; si el padre crea un helper en kernel, se adopta sin cambiar el contrato JSON.
4. **Permisos idénticos**: `WebGatePermission` para sesión y requisitos web, y después las funciones de `permissions.py` en el mismo orden que la vista nativa (incluido 403 antes de 404 en las acciones). Las asimetrías de alcance (detalle, edición y acciones sin alcance de técnico; lote de mailing visible para cualquier admin) se conservan y se fijan con tests.
5. **Sin 409 ni bloqueo optimista**: las transiciones repetidas o inválidas responden como el nativo (mensaje y redirect). Fundamento: no inventar reglas; el estado observable ya es idempotente para publicar o archivar repetido.
6. **Mutaciones con archivos por POST multipart JSON** dentro de la ventana G1; ante 504 `uncertain`, mensaje sin reenvío que pide revisar el listado. Fundamento: el trabajo pesado del mailing ya es asíncrono (job existente) y el alta de comunicados es una transacción corta; mantener el formulario nativo partiría la experiencia.
7. **Sin envío real en pruebas**: locmem explícito en tests, worker nunca en bucle en tests, entorno visual sin `mailing_worker` y fixtures directas de `MailingJob`/`MailingJobRow` para cada estado.
8. **Plantilla como enlace nativo**: `<a class="btn btn-outline-primary" href="/comunicados/mailing/plantilla/">Descargar plantilla</a>`, como en `userImport.tsx:236`. El nativo usa `formaction` GET y agrega asunto y cuerpo a la query de la descarga; el enlace evita llevar el texto del correo a URLs y logs sin cambiar el archivo descargado. Diferencia estructural menor (botón por enlace) aceptada por precedente.
9. **Adjuntos y media**: enlaces directos a `archivo.url`, como el nativo; React no lee binarios por JSON.
10. **Lecturas sin efectos**: los GET de detalle de lote no reclaman, no tocan `last_activity_at` y no hacen polling; «Actualizar estado» recarga a demanda (precedente `useWebResource`).

## Puntos estrictamente humanos

Ninguno. Todo se resuelve manteniendo la paridad nativa (S13). Las asimetrías de alcance y la carrera de adjuntos del mailing quedan documentadas como comportamiento existente; cambiarlas sería una decisión de producto o un bugfix aparte, no parte de esta migración.

## Incertidumbres

- [No confirmado] Si `/media/` se sirve sin control de sesión en producción (Nginx). Afecta a los adjuntos de comunicados y de lotes; se conserva el comportamiento sin verificarlo.
- [No confirmado] Si existen señales o tareas fuera de la app que notifiquen a la PWA al publicar; no hay `signals.py` en `comunicados` en HEAD y las vistas no envían nada.
- [No confirmado] Borrado de archivos físicos al eliminar un comunicado: no hay código que lo haga en la app; probablemente quedan en storage.
- [No confirmado] Límite de tamaño de request en Nginx o proxy para subidas multipart grandes; no figura en `settings.py` revisado.
- [No confirmado] Cómo el core decide servir un pathname de vertical con React (mecanismo de activación de `frontend_v2`); es setup del padre.
- [No confirmado] Marcado HTML exacto de `components/search_bar.html` y `components/pagination.html` para la paridad S13; React debe calcarlo de esos componentes (precedente `InsumosList.tsx` y `Groups.tsx`).
- [No confirmado] Que pytest-django aplique locmem en todos los runners de CI; por eso la decisión 7 lo fija explícitamente.

## Fuente

Leído en HEAD 4ea95bcbe con `git show HEAD:<ruta>`:

- `src/backends/comedores/comunicados/urls.py:1-86`; `api_urls.py:1-20`; `api_views.py:1-69`; `serializers.py:1-33`.
- `src/backends/comedores/comunicados/views.py:1-632`; `permissions.py:1-290`; `forms.py:1-280`; `models.py:1-271`.
- `src/backends/comedores/comunicados/services_mailing.py:1-185`; `services_mailing_jobs.py:1-547`; `services_destinatarios.py:1-185`; `management/commands/process_mailing_jobs.py:1-27`; `admin.py:8-140` (búsqueda puntual).
- Templates `comunicados/comunicado_list.html:1-76`, `comunicado_gestion_list.html:1-246`, `comunicado_detail.html:1-143`, `comunicado_form.html:1-226`, `comunicado_confirm_delete.html:1-58`, `mailing_form.html:1-106`, `mailing_job_detail.html:1-204`, `partials/destinatarios_panel.html:1-80`; JS `static/custom/js/comunicadosForm.js:120-160`, `comunicadosDestinatarios.js:340-400` y textos por búsqueda.
- `src/backends/comedores/comedores/api.py:71-215`; `src/backends/comedores/comedores_runtime/urls.py:1-35`.
- `src/backends/config/backends.json:239-400`; `src/backends/config/settings.py:275-276,315-345`; `src/backends/config/urls.py:76-77`; `docker/compose/docker-compose.produccion.yml:60-79`.
- `src/backends/kernel/core/permissions/registry.py:33-34,185-203`; `src/backends/kernel/core/constants.py:10-75`; `src/backends/kernel/users/services.py:30-33,453-457`; `src/backends/kernel/core/web_gate.py:228-327`; `src/backends/kernel/templates/includes/main.html:1-40`; `components/back_button.html`; `src/backends/kernel/tests/test_boton_volver_unificado.py:40-75`.
- `src/backends/sisoc_core/insumos/web_api_urls.py:1-22`; `web_api_views.py:1-240`; `src/backends/sisoc_core/usuarios/web_api_urls.py:1-77`; `web_user_import_urls.py:1-23`; `web_user_import.py:49-104,159-195,270-273`.
- `src/frontends/apps/sisoc/src/routes/index.ts`, `types.ts`, `userImport.tsx:18-130,231-324`.
- Tests: `src/backends/comedores/tests/test_comunicados_{views_unit,acciones_unit,api_unit,permissions_unit,destinatarios_unit,forms_unit}.py` (nombres de casos), `test_admin_operaciones_comedores.py:372-403`.
- Decisión `docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md`; catálogo `docs/plans/2026-T4/2026-10-27-2785-entregas-por-flujo.json` (flujos CM01-CM03 y `contract_profiles`, leído del disco).
