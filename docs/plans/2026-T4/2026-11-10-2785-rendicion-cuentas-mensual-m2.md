# RM01.01, RM01.02, RM01.03: Rendición mensual y documentos

Estado M2 ejecutable: contrato escrito sobre la fuente HEAD 4ea95bcbe y refrescado sobre 82cfd28a1 (2026-11-11). Lo marcado «[82cfd28a1]» cambió respecto de la versión original; el resto se volvió a verificar contra la fuente.
Entregas del catálogo (`2026-10-27-2785-entregas-por-flujo.json`, flujo RM01): RM01.01 Consulta de rendición mensual [L: lectura y navegación], RM01.02 Acciones del circuito [W: acción o transición de circuito], RM01.03 Documentos y comprobantes [F: archivo, documento o exportación].
Owner: backend `comedores`, app `rendicioncuentasmensual`. [82cfd28a1] Implementado: solo el listado global de RM01.01 (listado, filtros y enlace al CSV nativo; registro `docs/registro/cambios/2026-T4/2026-11-11-2785-react-rendicion-mensual-listado.md`). Pendientes: lista por comedor y detalle de RM01.01, RM01.02 y RM01.03.
Regla rectora: paridad nativa (decisión S13 del usuario: "mantene la paridad"), incluidas las asimetrías de permisos y alcance que se documentan abajo.

## Entregas y orden

| ID | Título | Perfil | Rutas nativas cubiertas | Depende de |
| --- | --- | --- | --- | --- |
| RM01.01 | Consulta de rendición mensual | L | `rendicioncuentasmensual_global_list` (incluye `?export=csv`), `rendicioncuentasmensual_list`, `rendicioncuentasmensual_detail` (GET) | Setup compartido `api/web/comedores/` (padre), G1 v1 |
| RM01.02 | Acciones del circuito | W | `rendicioncuentasmensual_detail` (POST: transiciones, revisión de documentos, faltantes), `rendicioncuentasmensual_auditoria_nueva`, `rendicioncuentasmensual_auditoria`, `rendicioncuentasmensual_update`, `rendicioncuentasmensual_delete` | RM01.01 (detalle y su JSON) |
| RM01.03 | Documentos y comprobantes | F | `rendicioncuentasmensual_documento_ver`, `rendicioncuentasmensual_download_pdf`, `rendicioncuentasmensual_create` (alta con adjuntos), `eliminar_archivo`; enlaces a `acta_auditoria` y `documento_regularizacion` | RM01.01; caracterización previa del alta (ver RM01.03 Riesgos) |

Montaje real (verificado): `comedores_runtime/urls.py:17` incluye `rendicioncuentasmensual.urls` bajo `rendicioncuentasmensual/`, y cada patrón de `urls.py` vuelve a empezar con `rendicioncuentasmensual/`. Por eso las URL publicadas tienen el prefijo duplicado (`config/url_registry.json:3813-3870`), salvo `eliminar_archivo`, que queda en `/rendicioncuentasmensual/eliminar-archivo/<id>/` (`url_registry.json:2158-2160`). El core las reenvía al runtime Comedores por el prefijo `rendicioncuentasmensual/` de `config/backends.json:272`. Las URL nativas se conservan tal cual, con el prefijo duplicado.

[82cfd28a1] El setup compartido ya existe: `comedores_runtime/urls.py:24-25` monta `api/web/comedores/` con el agregador `comedores_runtime/web_api_urls.py`, donde cada app suma su `include`, y `config/backends.json` publica el prefijo `api/web/comedores/`. [82cfd28a1] Rutas nativas nuevas (#2845, descarga asincrónica del PDF): `rendicioncuentasmensual_download_pdf_solicitar` (`detalle/<pk>/descargar-pdf/solicitar/`, POST) y `rendicioncuentasmensual_download_pdf_estado` (`detalle/<pk>/descargar-pdf/estado/`, GET), las dos con el decorador de los cinco permisos (`urls.py:70-83`). Ver RM01.03.

## RM01.01 Consulta de rendición mensual

### Rutas nativas

| Método | URL | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/listado/` | `rendicioncuentasmensual_global_list` | `views.py:111` `RendicionCuentaMensualGlobalListView` | `rendicioncuentasmensual_global_list.html:1-65`, celda `components/rendicion_global_list_cell.html:1-35` |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/listado/?export=csv` | (misma) | `views.py:168-171`, `kernel/core/mixins.py:13` `CSVExportMixin` | (descarga) |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/<comedor_id>/` | `rendicioncuentasmensual_list` | `views.py:89` `RendicionCuentaMensualListView` | `rendicioncuentasmensual_list.html:1-60` |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/` | `rendicioncuentasmensual_detail` | `views.py:279` `RendicionCuentaMensualDetailView` (`get_context_data` 570-691) | `rendicioncuentasmensual_detail.html:1-567`, `components/auditoria_documentacion.html:1-35` |

Consumidores indirectos que enlazan a estas rutas y no cambian: sidebar `kernel/templates/includes/sidebar/opciones.html:419-426` y `sisoc_core/usuarios/web_navigation.py:214-215` («Rendiciones»); `acompañamiento_detail.html:35` (lista por comedor); `admisiones/admisiones_detalle.html:685` y `gestion_organizaciones/templates/organizacion_rendicion_detail.html:14` (detalle). La ficha de comedor no enlaza a rendiciones mensuales: solo muestra el paso «Rendición» de la línea de tiempo (`comedor_detail.html:1135-1136`, `timeline_rendicion_circle` fijo en "3" en `comedor_service/impl.py:782,818`) y precarga ids (`impl.py:630-632`). El contrato de ficha (`2026-10-28-2785-comedores-legajo-base-m2.md`) no menciona rendiciones; no se agrega nada a la ficha.

### Acceso

- Las cuatro rutas: decorador `permissions_any_required(_RENDICION_ACCESS_PERMS)` (`urls.py:18-25,42-62`): superusuario o cualquiera de `rendicioncuentasmensual.view_rendicioncuentamensual`, `rendicioncuentasmensual.manage_territorial_stage`, `rendicioncuentasmensual.manage_auditoria_review_stage`, `rendicioncuentasmensual.manage_auditoria_stage`, `rendicioncuentasmensual.manage_regularizacion_stage`. Sin permiso: `PermissionDenied` (403). Anónimo: el decorador también responde 403 antes que `LoginRequiredMixin` (el decorador envuelve la vista; `kernel/core/decorators.py:8-20,35-47`).
- Grupos que reciben permisos de etapa (`migrations/0018_stage_permissions.py`): «Rendición Territorial» (`manage_territorial_stage`), «Rendición Auditoría» (`manage_auditoria_review_stage`, `manage_auditoria_stage`, `manage_regularizacion_stage`), «Administrador Auditoría» (los cuatro). La asignación ocurre solo si el grupo existe.
- Exportación CSV: además del decorador, `check_export_permission` exige superusuario o `auth.role_exportar_a_csv`; si no, 403 (`mixins.py:22-32`).
- Alcance de objeto: no hay. Ninguna vista filtra por comedor, organización, dupla ni usuario: cualquier actor con uno de los cinco permisos ve el listado global completo, la lista de cualquier comedor y el detalle de cualquier rendición activa. Conservar y documentar; no endurecer en esta migración.
- Capacidades del detalle (calculadas en `views.py:588-671`, con `iam.services.user_has_permission_code`, que concede todo al superusuario): `puede_revisar_documentos`, `puede_solicitar_faltantes`, `puede_revision_territorial`, `puede_revision_auditoria`, `puede_auditoria`, `puede_regularizacion` (además `rendicion.es_origen_acta`), `puede_editar_datos` (`rendicioncuentasmensual.edit_rendicion_data`), `puede_gestionar_auditoria`, `mostrar_acciones_proceso`, `mostrar_documentacion_auditoria`, `puede_descargar_pdf`.
- Botón «Nueva Auditoría» del listado: `perms.rendicioncuentasmensual.manage_auditoria_stage` en template (`global_list.html:17`), es decir, `has_perm` de Django.

### Datos y reglas

Listado global (`views.py:111-276`):

- Queryset `RendicionCuentaMensualService.obtener_todas_rendiciones_cuentas_mensuales()` (`services.py:1462-1501`): `deleted_at` nulo, orden `-ultima_modificacion, -id`, anotaciones `region_abordaje_id` y `subzona_abordaje_id` (de la organización del proyecto o, sin proyecto, de la del comedor).
- Paginación 25 (`paginate_by`); `page` inválido o fuera de rango: 404 de `ListView`. Componente de paginación con textos «Volver» y «Continuar».
- Filtros: parámetro `filters` (JSON) con `AdvancedFilterEngine` sobre `FIELD_MAP` y `FIELD_TYPES` (`filter_config.py:17-55`); operadores texto `contains, ncontains, eq, ne, empty`; número y fecha `eq, ne, gt, lt, empty`; choice y boolean `eq, ne` (`filter_config.py:62-66`). Dos filtros propios: `territorial_asignado` (`eq`/`ne`, valor id de usuario, varios se combinan con OR, `views.py:192-216`, `services.py:1504-1539`) y `estado_proceso` (valor `etapa:subestado` validado contra los choices del modelo, `views.py:218-247`). JSON inválido: se ignora sin error (`views.py:193-247`).
- Campos del buscador (`filter_config.py:102-160`, campo por defecto `codigo_proyecto`): Proyecto, Región, Subzona, Espacio, Organizacion, Territorial asignado, Convenio, Numero de rendicion, Mes (1-12), Anio, Periodo inicio, Periodo fin, Linea programatica, Estado (15 combinaciones de `ESTADO_PROCESO_CHOICES`, `filter_config.py:74-99`), Estado general, Etapa, Documento adjunto, Fecha de creacion, Ultima modificacion. Configuración cacheada 15 min con clave `rendiciones:filters_ui_config:v6`; las opciones de territoriales, región y subzona se recalculan por request.
- Filtros favoritos: sección `SeccionesFiltrosFavoritos.RENDICIONES` = `"rendiciones"` (`kernel/core/services/favorite_filters/config.py:25`), registrada en `favorite_filters.py:19-32` con `FIELD_TYPES` + `CUSTOM_FIELD_TYPES`; el core enruta la sección al runtime Comedores (`kernel/core/backend_proxy.py:375-393`) desde `ajax/filtros-favoritos/` (`kernel/core/urls.py:53-58`). React reutiliza ese endpoint sin cambios.
- Columnas (`views.py:120-150`), con preferencias por usuario bajo `rendiciones_global_list`; `proyecto` obligatoria en la resolución (`required_keys`): se agrega a cualquier selección guardada. [82cfd28a1, verificado con pruebas] El modal no la marca: `build_columns_context_from_fields` deja `required: false` en todas las columnas de `available`, así que el checkbox de «Proyecto» no está deshabilitado y no muestra «Obligatoria». `territorial_asignado` queda fuera de las columnas por defecto. Claves y títulos: `proyecto` «Proyecto» (`comedor.codigo_de_proyecto`, vacío «Sin proyecto»), `organizacion` «Organización» (`comedor.organizacion.nombre`, «Sin organización»), `territorial_asignado` «Territorial asignado» («-»), `convenio` «Convenio» («-»), `numero_rendicion` «Rendición» (fallback `id`), `periodo` «Período» (`d/m/Y - d/m/Y` o `mes/anio`), `etapa` «Etapa» (badge `etapa_badge_class`), `estado` «Estado» (`estado_proceso_display`, clase `validado` si subestado `finalizada`, `no-validado` si `pendiente_correcciones`, si no `pendiente`), `ultima_modificacion` «Última modificación» (`d/m/Y H:i`). Más la columna fija «Acciones» con «Ver».
- Vacío: «No hay rendiciones registradas.».

Lista por comedor (`views.py:89-108`, asimetría conservada):

- `paginate_by = 10` se aplica a `RendicionCuentaMensual.objects.order_by("-id")` (todas las rendiciones activas), pero el contexto reemplaza `rendiciones_cuentas_mensuales` por el queryset completo de `obtener_rendiciones_cuentas_mensuales(comedor)` (`services.py:1451-1459`, alcance de proyecto de `_get_project_queryset`, `services.py:344-360`). Resultado observable: la tabla muestra todas las rendiciones del alcance sin paginar y sin orden explícito; un `page` mayor que las páginas del total global responde 404.
- `Comedor.objects.get(id=comedor_id)` sin manejo: comedor inexistente responde 500.
- Columnas «#» (contador), «Mes», «Año», «Observaciones», «Acciones» (`list.html:30-34`); sin fila vacía.
- El template usa `comedor.nombre` y `object.rendicion_cuenta_mensual`, que no están en el contexto: el título se ve «Seguimiento mensual - » y la segunda miga queda vacía. Paridad: reproducir.

Detalle (`views.py:570-691`, template completo):

- Objeto por `get_object` (manager `objects`, excluye borrados lógicos) y `obtener_rendicion_cuenta_mensual(pk)` (`services.py:1582-1590`); borrado o inexistente: 404.
- Encabezado: «Rendicion {numero_rendicion|id}» y badge de `estado_proceso_display` (`models.py:789-811`, textos «Auditoría validada sin acta», «Auditoría finalizada sin observaciones», «Auditoría finalizada con observaciones», «Rendición regularizada tras Auditoría» o «{etapa} {subestado en minúsculas}»).
- Datos (`detail.html:53-134`): «Nombre de rendición», «Proyecto» (`scope_proyecto.proyecto_codigo`), «Organizacion», «Convenio», «Linea Programatica», «Mes / Ano», «Periodo», «Fecha de creacion», «Ultima modificacion», «Comedores relacionados con el proyecto» (badges o «Sin comedores relacionados»), «Usuario creador», «Usuario ultima modificacion» (nombre completo o username), «Observaciones» solo si hay. Vacíos «Sin dato», «Sin proyecto», «Sin organizacion». `scope_proyecto` sale de `services.py:1009-1054` (organización del proyecto o del comedor; comedores por proyecto o por código+organización).
- Aviso si subestado `pendiente_correcciones`: «La rendición tiene documentación pendiente de correcciones.».
- Tarjeta «Auditoría» solo en etapas `auditoria` o `regularizacion` (`detail.html:209-253`): «Validada» (`Sí,No,No`), «¿Se genera acta de auditoría?» (`Sí,No,Sin definir`), y si hay acta «Resultado de la Auditoría», enlaces «Acta de Auditoría» y «Acta Complementaria» (ver RM01.03). Si `mostrar_documentacion_auditoria`, «Documentación de las rendiciones incluidas» con `resumenes` (la rendición y sus `rendiciones_incluidas`).
- Tabla «Documentacion asociada» (`detail.html:255-565`): categorías de `obtener_documentacion_para_detalle(rendicion, incluir_borradores=True)` (`services.py:874-913`), visibles según línea programática (`models.py:440-453`: «Planilla de Seguros II» solo Tradicional, salvo que ya tenga documentos). Por categoría: etiqueta, «Obligatorio»/«Opcional», «{n} archivo(s)», badge «Documento faltante solicitado» y su fila «Observaciones:». Por archivo: nombre, estado (borrador de revisión de la etapa vigente si el subestado es `en_curso`), revisión, fecha `d/m/Y H:i`, «Ver» y «Visualizado»/«Sin visualizar». Historial de subsanaciones bajo cada archivo. Vacío por categoría: «No hay archivos cargados en esta categoria.».
- Botón «Editar Datos de Rendición» si `puede_editar_datos`; «Generar descarga» si `puede_descargar_pdf` (todos los documentos vigentes validados, `services.py:916-925`). [82cfd28a1] El botón ya no es un enlace a `./descargar-pdf/`: es el formulario `components/pdf_descarga_action.html` (POST a `descargar-pdf/solicitar/` con polling a `descargar-pdf/estado/`, ver RM01.03).

### Acciones y efectos

Solo lectura, con dos excepciones que no son de esta entrega: el POST del detalle (RM01.02) y el registro de visualización al abrir un documento (RM01.03). El CSV no escribe.

### Exportaciones

`GET ...listado/?<filtros>&export=csv` (`views.py:168-171`): mismo `get_queryset()` filtrado y sin paginar; columnas activas del usuario en su orden (`views.py:151-156`); valores con `resolve_field` (período `dd/mm/aaaa - dd/mm/aaaa` o `mes/anio`, territoriales como en la grilla, booleanos «Si»/«No», fechas `%Y-%m-%d %H:%M:%S`). `StreamingHttpResponse` con BOM UTF-8, delimitador `;`, `Content-Disposition: attachment; filename="exportacion_rendiciones_YYYYMMDD_HHMM.csv"` (`mixins.py:34-39,91-119`). React enlaza esta URL nativa (`export_url` del contexto, `views.py:256-262`); no se reimplementa en JSON. El nombre sale de `get_export_filename` (`mixins.py:34-39`) a partir de `export_filename = "listado_rendiciones.csv"`. Botón «Exportar búsqueda» (`search_bar.html`): superusuario o `auth.role_exportar_a_csv`; la descarga además pasa por `check_export_permission`.

### API web del runtime

[82cfd28a1] Archivos: `src/backends/comedores/rendicioncuentasmensual/web_api.py` y `web_api_urls.py` (incluido desde `comedores_runtime/web_api_urls.py` bajo `rendicioncuentasmensual/`), con el patrón de las otras pantallas de Comedores (`expedientespagos/web_api.py`, `duplas/web_api.py`). Entrada React local sin montar: `rendicioncuentasmensual/web_preview.py` (`rendicion_preview_patterns`, assets en `/rendicioncuentasmensual/react/assets/`). Prefijo de esta app: `/api/web/comedores/rendicioncuentasmensual/`. Las entregas siguientes suman sus rutas a esos mismos módulos.

Base común (G1 v1): `SessionAuthentication`, `core.web_gate.WebGatePermission` (401 sin sesión con `detail`; 403 con `state` si hay un requisito web pendiente), `JSONRenderer`, `Cache-Control: private, no-store` y `Vary: Cookie`. Permiso de cada endpoint: el mismo `_has_any_permissions` del decorador nativo con la misma lista (`_RENDICION_ACCESS_PERMS` importada de `urls.py`); nunca uno más amplio.

| Método | Path | Request | Respuesta 200 | Errores |
| --- | --- | --- | --- | --- |
| GET | `listado/` [82cfd28a1, implementado] | `filters`, `page` (entero o `last`); `sort` no existe | `{breadcrumb, filters_config, favorites: {section: "rendiciones", url, detail_url_template}, urls: {list, reset, export, nueva_auditoria}, can_export, can_nueva_auditoria, columns (column_config nativo), headers, results: [{id, cells: [{text, badge}], detail_url}], page: {is_paginated, number, count, previous, next, range, query_without_page}, messages}` | 401, 403, 404 (página inválida, como `ListView`) |
| GET | `comedor/<comedor_id>/` | ninguno | `{comedor_id, results: [{id, mes, anio, observaciones, detail_url, update_url, delete_url}]}` | 401, 403, 404 comedor inexistente |
| GET | `<pk>/` | ninguno | `{rendicion: {...}, scope_proyecto: {organizacion_nombre, proyecto_codigo, comedores_relacionados: [{id, nombre}]}, documentacion_por_categoria: [...], resumenes, capabilities: {...}, urls: {volver, update, download_pdf, auditoria}}` | 401, 403, 404 |

Fila del listado [82cfd28a1]: `id`, `detail_url` y una celda por columna activa, en el orden de la preferencia del usuario. Cada celda se arma renderizando el include nativo `components/rendicion_global_list_cell.html`: `text` es el texto visible (espacios colapsados, entidades resueltas) y `badge` la clase del `<span>` (`badge etapa-badge <clase>` en Etapa; `badge-validacion validado|no-validado|pendiente` en Estado) o `null`. `export` es la ruta nativa del listado con la misma query y `export=csv`, como `export_url` del contexto; `can_export` es la regla del botón de `search_bar.html`; `can_nueva_auditoria` es `user.has_perm("rendicioncuentasmensual.manage_auditoria_stage")`, como `perms.` del template. `messages` consume los mensajes pendientes, como la página. `rendicion` del detalle: `id`, `numero_rendicion`, `nombre`, `convenio`, `linea_programatica` y su display, `mes`, `anio`, `periodo_inicio`, `periodo_fin` (ISO o null), `fecha_creacion`, `ultima_modificacion`, `usuario_creador_nombre`, `usuario_ultima_modificacion_nombre`, `observaciones`, `etapa_proceso`, `subestado_proceso`, `estado_proceso_display`, `estado`, `validada`, `genera_acta_auditoria`, `acta_auditoria_url`, `documento_regularizacion_url`, `es_origen_acta`. Categoría: `codigo`, `label`, `description`, `required`, `multiple`, `solicitud_faltante: {observaciones}|null`, `archivos: [{id, nombre, estado, estado_display, estado_visual, estado_visual_display, observaciones, fecha_creacion, visualizacion_confirmada, visualizacion_usuario, visualizacion_fecha, ver_url, subsanaciones_historial: [...]}]`. `capabilities`: los once booleanos de `get_context_data`, con el mismo cálculo.

Reglas: el listado instancia la vista nativa (`setup`, `get_queryset`, `get_context_data`), sin extraer ni duplicar nada; el detalle reutilizará el `get_context_data` nativo serializado; no se reimplementan filtros ni capacidades. `comedor/<id>/` devuelve el queryset de `obtener_rendiciones_cuentas_mensuales` sin paginar e ignora `page` (decisión técnica abajo). Solo lectura: GET, HEAD, OPTIONS.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/rendicionMensual.tsx` + `rendicionMensual.test.tsx`. [82cfd28a1] Hoy posee solo el listado global, con el marco de `MainFrame.tsx`; el buscador por tipos (número, fecha, choice y booleano), el modal de columnas, la paginación y el botón de CSV están en el mismo módulo.
- Paths que posee (pathname nativo, al completar RM01.01): `/rendicioncuentasmensual/rendicioncuentasmensual/listado/`, `/rendicioncuentasmensual/rendicioncuentasmensual/<comedor_id>/`, `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/`. Regex con `[0-9]+`; `listado`, `detalle`, `nuevo`, `editar`, `eliminar`, `auditoria` y `documento` no deben capturarse como `<comedor_id>`.
- Registro en `ROUTES` de `routes/index.ts`, antes de `businessRoute(SHELL_ROUTES)`.
- Volver nativo (`kernel/templates/components/back_button.html:17-26`): listado global y lista por comedor sin `volver_url`, `href="/"`; detalle `volver_url = reverse("rendicioncuentasmensual_global_list")` (`views.py:621`), es decir `/rendicioncuentasmensual/rendicioncuentasmensual/listado/`.
- La descarga CSV y «Ver» son navegación nativa completa, no llamadas del cliente. [82cfd28a1] «Generar descarga» ya no es un enlace: ver RM01.03.

### Criterios de aceptación

- Listado: título de página «Rendiciones», buscador «Buscar Rendiciones», migas «Organizaciones» (enlace a `/organizaciones/listar`) › «Rendiciones», botón «Exportar búsqueda» con superusuario o `role_exportar_a_csv`, «Resetear», «Configurar columnas», botón «Nueva Auditoría» solo con `manage_auditoria_stage`, botón «Ver», vacío «No hay rendiciones registradas.», paginación «Volver»/«Continuar», columnas y fallbacks literales de arriba.
- Lista por comedor: título de pestaña «Acciones», encabezado «Seguimiento mensual - », botón «Nuevo seguimiento mensual», acciones «Ver Detalle», «Editar», «Dar de baja»; miga «Rendición de cuenta mensual», «Lista».
- Detalle: título «Detalle de Rendicion de Cuenta», miga «Rendiciones» › «Detalle», todos los rótulos literales sin tildes donde la fuente no las tiene («Organizacion», «Linea Programatica», «Mes / Ano», «Documentacion asociada», «Revision», «Seleccionar accion»), texto «Cada documento presentado puede validarse o enviarse a subsanacion de forma independiente.» y, con revisión habilitada, «Podés cambiar las selecciones guardadas hasta presionar Finalizar Revisión.».
- Paridad: misma estructura de tarjetas y tabla, orden de Tab igual al nativo (Volver, buscador/acciones, cabeceras, filas en orden de documento), regla visual S13 (paridad estructural + diff perceptual <= 1 % sin antialiasing, 2 CSS px) por URL, rol (lector, territorial, auditoría, superusuario) y viewport escritorio/móvil.

### Casos de prueba

- Backend [82cfd28a1: el listado está cubierto por `rendicioncuentasmensual/test_web_rendicion_listado_api.py` y `test_web_preview_rendicion_listado.py`; el resto, con nombre único en la misma app]: permitido con cada uno de los cinco permisos; denegado sin ninguno 403; anónimo 401; prerrequisito web pendiente 403 con `state`; rendición borrada o inexistente 404; comedor inexistente 404; `page` inválido 404; filtros (`territorial_asignado` eq/ne, `estado_proceso` válido e inválido, JSON roto ignorado) idénticos al queryset nativo; columnas activas y obligatoria `proyecto`; capacidades por etapa/subestado y por permiso iguales al contexto nativo; nulls (sin proyecto, sin comedor, sin período).
- Frontend (vitest): estados loading/error/forbidden, render de fallbacks, enlace CSV con los filtros vigentes, ausencia de «Nueva Auditoría» sin capacidad, Volver por pantalla.
- Diferencial: rutas nativas (HTML y `?export=csv`) sin cambios en stdout/estado/contenido contra la base; `test_rendicioncuentasmensual_views_unit.py`, `test_issue_2445_territorial_filtro_rendiciones.py` y `test_rendicioncuentasmensual_visualizacion.py` siguen verdes.
- Visual: S13 por las tres rutas, roles y viewports; datos sintéticos.

### Riesgos

- Sin alcance de objeto: la API hereda la visibilidad global. Cualquier endurecimiento es un cambio de producto aparte.
- El listado carga `prefetch_related` de territoriales por fila; el JSON no debe agregar consultas por fila.
- Textos sin tildes en la fuente: corregirlos rompe la paridad visual.

## RM01.02 Acciones del circuito

### Rutas nativas

| Método | URL | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| POST | `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/` | `rendicioncuentasmensual_detail` | `views.py:361-568` | `detail.html:142-207` (acciones), `296-319` (faltantes), `347-449` (revisión) |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/` | `rendicioncuentasmensual_auditoria_nueva` | `views.py:697-742` `RendicionAuditoriaView.get` | `rendicioncuentasmensual_auditoria.html:30-121` |
| GET, POST | `/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/<pk>/` | `rendicioncuentasmensual_auditoria` | `views.py:744-801` | `auditoria.html:122-266` |
| GET, POST | `/rendicioncuentasmensual/rendicioncuentasmensual/editar/<pk>/` | `rendicioncuentasmensual_update` | `views.py:998-1042` | `rendicioncuentasmensual_datos_form.html:1-41` |
| GET, POST | `/rendicioncuentasmensual/rendicioncuentasmensual/eliminar/<pk>/` | `rendicioncuentasmensual_delete` | `views.py:1045-1058`, `kernel/core/soft_delete/view_helpers.py:90-118` | `rendicioncuentasmensual_confirm_delete.html:1-20` |

### Acceso

- POST del detalle: el decorador de la URL (cinco permisos) y después una rama por tipo de POST, evaluadas en este orden (`views.py:361-568`):
  1. `solicitar_categoria` no vacío: subestado `en_curso` y (etapa `revision_documentacion` con `manage_territorial_stage`) o (etapa `revision_auditoria` con `manage_auditoria_review_stage`); si no, 403, también para AJAX.
  2. `accion_proceso` no vacío: permiso por acción de `_permission_for_action` (`views.py:340-353`): `iniciar_revision_territorial`/`finalizar_revision_territorial` → `manage_territorial_stage`; `iniciar_revision_auditoria`/`finalizar_revision_auditoria` → `manage_auditoria_review_stage`; `iniciar_auditoria`/`finalizar_sin_observaciones`/`finalizar_con_observaciones` → `manage_auditoria_stage`; `iniciar_regularizacion`/`finalizar_regularizacion` → `manage_regularizacion_stage`. Acción desconocida: permiso `None`, `user_has_permission_code` falso, 403 (el superusuario pasa y recibe «Acción de proceso inválida.»).
  3. Si no: revisión de documento con `_user_can_review_documentos` (`views.py:305-321`); sin permiso, AJAX 403 JSON «No tiene permisos para revisar documentos.», no AJAX 403.
- Auditoría (ambas URL): `permissions_any_required(["rendicioncuentasmensual.manage_auditoria_stage"])` (`urls.py:28-41`) + `LoginRequiredMixin`. Objeto por `AuditoriaService.disponibles()` (`auditoria.py:226-243`): no borrada, sin `fecha_gestion_auditoria` ni `fecha_auditada`, etapa `auditoria`, subestado `pendiente`/`en_curso`, `genera_acta_auditoria` distinto de True y sin acta; fuera de eso, 404. `?rendicion=<no decimal>`: 404.
- Editar datos: decorador solo con `rendicioncuentasmensual.view_rendicioncuentamensual` (`urls.py:105-111`) y además `edit_rendicion_data` en `dispatch` (`views.py:1003-1009`); asimetría conservada: un actor con solo permisos de etapa y `edit_rendicion_data` recibe 403 en la URL aunque el detalle le muestre el botón.
- Baja: solo `rendicioncuentasmensual.view_rendicioncuentamensual` (`urls.py:91-97`); sin regla de etapa ni de estado. GET muestra la confirmación; POST da de baja.
- Ninguna de estas vistas tiene alcance de objeto por comedor u organización.

### Datos y reglas

Transiciones (`services.py:1668-2083`, `RendicionProcesoService.ejecutar`, `@transaction.atomic`), origen y efecto:

| Acción | Estado de origen | Efecto |
| --- | --- | --- |
| `iniciar_revision_territorial` | `revision_documentacion` + `pendiente`/`subsanado` | bloquea organización (o comedor) y rendición; cupo: otra rendición del mismo proyecto (código + organización, incluidas históricas) en `en_curso`, `pendiente_correcciones` o `subsanado` (una `subsanado` solo cede ante más antiguas) → error «No se puede iniciar la revisión territorial: la rendición #{pk} del mismo proyecto está en revisión territorial en curso, pendiente de correcciones o subsanada. Debe pasar a Revisión para Carga pendiente para iniciar otra.»; si no, `en_curso`, estado `revision` |
| `finalizar_revision_territorial` | `revision_documentacion` + `en_curso` | aplica borradores; con documentos «Presentado»: «No se puede finalizar la etapa mientras existan documentos sin revisar.»; con observados o faltantes activos: estado `subsanar`, `pendiente_correcciones` y comunicado por documento; si no, `fecha_validacion_territorial`, etapa `revision_auditoria` `pendiente` |
| `iniciar_revision_auditoria` | `revision_auditoria` + `pendiente`/`subsanado` | `en_curso`; en el primer inicio, los documentos validados vuelven a «Presentado» |
| `finalizar_revision_auditoria` | `revision_auditoria` + `en_curso` | igual que territorial; sin observaciones: `fecha_validacion_auditoria`, etapa `auditoria` `pendiente`, estado `finalizada` |
| `iniciar_auditoria`, `finalizar_sin_observaciones`, `finalizar_con_observaciones` | (desde el detalle no se ejecutan) | la vista redirige: si la rendición está en `disponibles()`, mensaje «Gestioná la Auditoría desde su pantalla específica.» y redirect a `rendicioncuentasmensual_auditoria`; si no, «Esta rendición ya no admite gestionar su Auditoría.» y redirect al detalle (`views.py:422-445`) |
| `iniciar_regularizacion` | `auditoria` + `finalizada_con_observaciones`, rendición origen del acta | etapa `regularizacion` `en_curso`, propagado a las rendiciones con ese origen |
| `finalizar_regularizacion` | `regularizacion` + `en_curso` | exige `documento_regularizacion` («Adjuntá la documentación de regularización.»); guarda archivo, `fecha_regularizacion`, `finalizada`; propaga al grupo |

Errores comunes: «La acción no corresponde al estado actual de la rendición.», «La gestión de auditoría está cerrada y no admite nuevas acciones.», «La regularización debe gestionarse desde la rendición que originó el acta de auditoría.», «Acción de proceso inválida.». Cambio de etapa: `resetear_visualizaciones_rendicion`. `RendicionProcesoForm` (`forms.py:187-276`): `accion_proceso` oculto; `monto_rendido`/`monto_observado` decimal 15,2 mínimo 0; `genera_acta_auditoria` Sí/No; `rendiciones_incluidas` (solo Tradicional, `rendiciones_elegibles_para_acta`); `observaciones`; `acta_auditoria`; `documento_regularizacion` «Acta Complementaria».

Revisión de documento (`services.py:1306-1373`): `estado` en `validado`/`subsanar` o «El estado seleccionado es inválido.»; rendición bloqueada con `select_for_update`, en `en_curso` y etapa de revisión, o «La rendición no admite revisión de documentos en su estado actual.»; documento vigente o «Solo se pueden revisar documentos vigentes.»; `subsanar` sin observaciones: «Debe ingresar observaciones para enviar el documento a subsanar.». Escribe solo el borrador (`revision_estado`, `revision_etapa`, `revision_observaciones`) y el actor de la rendición. Documento inexistente o borrado en la rendición: «El documento seleccionado no existe.» (AJAX 404).

Documento faltante (`services.py:1200-1225`): categoría válida para la línea o «La categoría de documentación es inválida.»; categoría de documento único ya cargada: «Esta categoría admite un único documento activo por rendición.»; observaciones vacías: «Debe ingresar observaciones.». `update_or_create` de `SolicitudDocumentoFaltante` activa por categoría (repetir actualiza, no duplica).

Auditoría conjunta (`auditoria.py`):

- Búsqueda `AuditoriaBusquedaForm` (`auditoria.py:22-80`): `filtro` en `proyecto` (por defecto), `organizacion`, `periodo`; `busqueda` requerida, máximo 120, normalizada sin tildes; vacía «Ingresá un texto para realizar la búsqueda.»; período en `%d/%m/%Y`, `%Y-%m-%d`, `%m/%Y`, `%Y-%m`, `%Y`, o «Ingresá un período como MM/AAAA, DD/MM/AAAA o AAAA.». Sin `busqueda` no hay consulta. Resultados paginados de a 20, orden `proyecto__codigo, periodo_inicio, pk`.
- `AuditoriaForm` (`auditoria.py:83-173`): `validada` requerida («Marcá Validada para poder guardar la auditoría.», deshabilitada si ya validada); [82cfd28a1] `genera_acta_auditoria` siempre requerida, con opciones «No» / «Sí» e inicial «No» (antes: opcional con «Seleccioná una opción» salvo ya validada); `rendiciones_incluidas` de `rendiciones_elegibles_para_auditoria` (`services.py:378-419`: mismo código + organización, Tradicional, validadas, sin acta, gestionadas); `acta_auditoria`; `resultado` («Finalizada Sin Observaciones», «Finalizada con Observaciones»); `observaciones`; `documento_regularizacion`. Reglas: con acta, resultado requerido («Seleccioná el resultado de la auditoría.») y observaciones si hay observaciones («Ingresá las observaciones de auditoría.»); sin acta, cualquier campo de acta da «Este campo requiere seleccionar que se genera un acta.»; acta complementaria sin observaciones: «El acta complementaria corresponde a un resultado con observaciones.».
- `AuditoriaService.guardar` (`auditoria.py:245-332`): transacción, bloqueo ordenado de la actual y las seleccionadas, revalidación del form, «La rendición ya no está disponible para gestionar su auditoría.» si dejó de estar disponible; con acta copia estado, fechas, archivos y vínculos a todas las incluidas. Mensaje: «Auditoría guardada. La gestión de esta rendición quedó cerrada.» o «Rendición validada. La auditoría continúa en curso para decidir sobre el acta.».

Editar datos (`forms.py:82-184`): `convenio` (vacío, `P01`, `P02`, `P03`), `numero_rendicion` (vacío, 1-6), `periodo_inicio`, `periodo_fin` (fecha ISO), `nombre`; ninguno requerido; vacío conserva el valor salvo `nombre`, que se limpia. Con convenio y número, `validar_datos_generales` (`services.py:516-673`) dentro de la transacción del POST: «El convenio debe ser P01, P02 o P03.», «El número de rendición debe estar entre 1 y 6.», «La fecha de fin debe ser posterior o igual a la fecha de inicio.», período Secos hasta tres meses («Para Abordaje Comunitario - Línea Secos el período puede abarcar hasta tres meses: la fecha de fin no puede superar el {dd/mm/aaaa}.») o mensual Tradicional («Las fechas deben pertenecer al mismo período mensual.»), «No se pueden cargar períodos anteriores a los ya gestionados.», «Ya existe una rendición con ese número dentro del mismo convenio.», «Ya se registraron las 6 rendiciones posibles para este convenio.», «El número de rendición debe ser {n}: debe continuar la secuencia del convenio dentro del proyecto.», «El período no puede repetirse ni solaparse dentro del mismo convenio.». Errores de `periodo` van a no-campo.

### Acciones y efectos

- POST con `accion_proceso` (no AJAX): éxito «Estado de la rendición actualizado.»; error de form: mensajes unidos por espacio; error de servicio: `format_validation_error` (`views.py:290-303`); siempre redirect 302 al detalle.
- POST de revisión y de faltante: con `X-Requested-With: XMLHttpRequest` responden JSON (`views.py:393-413,478-561`); éxito de revisión «Selección guardada. Se confirmará al finalizar la revisión.» con `documento` y `rendicion` (incluye `download_url` = detalle + `descargar-pdf/`); éxito de faltante «Solicitud de documento faltante registrada.» con `solicitud`. Sin AJAX: mensaje y redirect al detalle.
- Efectos externos: `_crear_notificacion_mobile_revision_documento` (`services.py:246-325`) archiva comunicados previos de la rendición, crea un `Comunicado` externo publicado para los comedores del proyecto y envía web push síncrono por suscripción (`pwa/services/push_service.py:123-150,181-221`, sin job). Ocurre al finalizar una revisión con documentos a subsanar y al solicitar un faltante. El cuerpo contiene el literal «Se actualiz? el estado de un documento de la rendici?n» (sin cambios).
- Auditoría: POST válido redirect al detalle con el mensaje; inválido re-render con errores (sin redirect). `volver_url` del formulario: `rendicioncuentasmensual_auditoria_nueva` si `?origen=busqueda`, si no el detalle; `volver_transitoria = True`.
- Editar: éxito redirect al detalle, sin mensaje; conserva `comedor`, `usuario_creador`, `fecha_creacion`; recalcula `mes`/`anio` solo con `periodo_inicio`; actor en `usuario_ultima_modificacion`.
- Baja: GET con `cascade_preview` (`build_delete_preview`) y botones «Dar de baja»/«Cancelar» (componente `delete_confirm.html`, cancelar al detalle); POST hace `delete(user=..., cascade=True)` (baja lógica en cascada), mensaje «Rendición dada de baja correctamente.» y redirect a `rendicioncuentasmensual_list` del comedor. Con `comedor` nulo (`on_delete=SET_NULL`), `self.object.comedor.id` falla después de la baja: 500 con la baja ya aplicada (por lectura de fuente).

### API web del runtime

| Método | Path | Request | Respuesta | Códigos |
| --- | --- | --- | --- | --- |
| POST | `<pk>/acciones/` | multipart: `accion_proceso` + campos de `RendicionProcesoForm` | `{ok: true, message, redirect}` (`redirect` = detalle o pantalla de auditoría, como la vista) | 200; 400 `{errors}` del form; 403; 404; 409 `{detail, errors?}` de `ValidationError` del servicio |
| POST | `<pk>/documentos/<documento_id>/revision/` | `estado`, `observaciones` | cuerpo JSON idéntico al AJAX nativo | 200; 400; 403 con «No tiene permisos para revisar documentos.»; 404 «El documento seleccionado no existe.» |
| POST | `<pk>/faltantes/` | `categoria`, `observaciones` | `{success, message, solicitud}` | 200; 400; 403; 404 |
| GET | `auditoria/` | `filtro`, `busqueda`, `page`, `rendicion` | `{form: {values, errors}, busqueda_realizada, busqueda_valida, results: [...], page}`; con `rendicion` válido `{redirect}` | 200; 403; 404 |
| GET, POST | `auditoria/<pk>/` | POST multipart de `AuditoriaForm`; `origen` | GET `{rendicion, scope_proyecto, form: {fields, initial, ya_validada}, elegibles, resumenes, volver_url}`; POST `{ok, message, redirect}` | 200; 400 `{errors, non_field_errors}`; 403; 404 |
| GET, POST | `<pk>/datos/` | `convenio`, `numero_rendicion`, `periodo_inicio`, `periodo_fin`, `nombre` | GET `{initial, choices}`; POST `{ok, redirect}` | 200; 400 `{errors, non_field_errors}`; 403; 404 |
| GET, POST | `<pk>/baja/` | ninguno | GET `{object_name, cascade_preview}`; POST `{ok, message, redirect}` | 200; 403; 404 |

Reglas: cada endpoint llama exactamente el form y el servicio de la vista nativa (`RendicionProcesoForm` + `RendicionProcesoService.ejecutar`, `actualizar_estado_documento_revision`, `solicitar_documento_faltante`, `AuditoriaBusquedaForm`/`AuditoriaForm`/`AuditoriaService.guardar`, `RendicionDatosForm` bajo `transaction.atomic`, `SoftDeleteDeleteViewMixin`), con el mismo orden de chequeos y los mismos permisos. Las ramas del POST del detalle se separan en tres endpoints sin cambiar sus reglas. CSRF por `SessionAuthentication` (header `X-CSRFToken`). Sin reintento automático; un 504 `uncertain: true` del core se muestra como resultado incierto («No se pudo confirmar el resultado. Revise la rendición antes de volver a intentar.») y nunca se reenvía. Las acciones de auditoría por `acciones/` devuelven el mismo redirect a la pantalla específica.

### Módulo React

- `src/frontends/apps/sisoc/src/routes/rendicionMensualCircuito.tsx` + test. Posee `/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/`, `/rendicioncuentasmensual/rendicioncuentasmensual/auditoria/<pk>/`, `/rendicioncuentasmensual/rendicioncuentasmensual/editar/<pk>/` y `/rendicioncuentasmensual/rendicioncuentasmensual/eliminar/<pk>/`; exporta el panel «Acciones del proceso», la revisión por documento y el formulario de faltante que `rendicionMensual.tsx` monta en el detalle.
- Registro en `ROUTES`, antes de `rendicionMensual` (paths más específicos primero) y de `businessRoute`.
- Volver nativo: búsqueda de auditoría `volver_url` = listado global; formulario de auditoría `volver_url` según `origen` (botón propio «Volver a resultados»/«Volver al detalle» con `data-sisoc-volver`); editar y baja sin `volver_url`, `href="/"`.
- Tras una mutación confirmada: navegación completa al `redirect`, como el redirect nativo (los mensajes se muestran en la página destino). La revisión de documento recarga el detalle, igual que `rendicioncuentasmensual_detail.js:117-137`.

### Criterios de aceptación

- Botones literales: «Iniciar revisión territorial», «Finalizar revisión territorial», «Iniciar revisión para carga», [82cfd28a1] «Finalizar revisión para Carga» (antes «Finalizar revisión de Auditoría», `detail.html:178`), «Gestionar Auditoría», «Iniciar regularización», «Finalizar regularización», «Solicitar documento faltante» (placeholder «Observaciones»), opciones «Seleccionar accion», «Validar», «A subsanar», placeholder «Observaciones para subsanacion», botón «Guardar revision» (solo ícono). Encabezado «Acciones del proceso».
- Auditoría: «Auditoría de rendiciones», «Validá la rendición y, si corresponde, generá un acta compartida entre los períodos seleccionados.», «Buscar una rendición para auditar», «Buscá por el código o el nombre del proyecto.», «Buscar», «Limpiar», «Rendiciones disponibles», «Seleccioná un filtro e ingresá un texto para buscar rendiciones.», «Solo se muestran rendiciones que todavía permiten gestionar su auditoría. Elegí una con el botón Gestionar.», «No hay rendiciones disponibles para esta búsqueda. Probá otro texto o filtro.», «Información general · Rendición {n}», «Confirmar validación», «Validación guardada. No se puede modificar.», «Rendiciones incluidas en el acta», «Actual · Inclusión fija», «No hay otras rendiciones elegibles para incluir.», [82cfd28a1] siempre «Al guardar la decisión sobre el acta, la gestión de esta rendición se cierra.» con el candado visible y el botón «Guardar y cerrar Auditoría» (`auditoria.html:238-241`; se retiraron «Podés guardar la validación y decidir sobre el acta más adelante.» y «Guardar»), «Documentación de las rendiciones seleccionadas». Los mensajes de guardado siguen siendo los dos de `AuditoriaService.mensaje_guardado` (`auditoria.py:177-181`).
- Editar: «Editar datos de rendición», «Los datos vienen precargados. Lo que dejes igual conserva su valor; no hace falta completar de nuevo los campos que no cambian.», «Guardar», «Cancelar»; miga «Rendición {n}» › «Editar datos».
- Baja: confirmación con «Dar de baja» y «Cancelar» y el preview de cascada.
- Paridad S13 por estado (cada etapa/subestado con y sin permiso), orden de Tab nativo, foco visible y mensajes de error asociados al campo.

### Casos de prueba

- Backend: cada acción permitida con su permiso y denegada con otro permiso de etapa (403); anónimo 401; acción desconocida 403 y superusuario 409 «Acción de proceso inválida.»; transición inválida y repetida (409, estado sin cambios); estado cambiado entre lectura y envío (409 bajo `select_for_update`); cupo territorial con históricas; finalizar con documentos sin revisar; finalizar con faltantes (comunicado y push simulados con mock, sin proveedor real); acciones de auditoría redirigidas; revisión 400/403/404; faltante repetido actualiza; auditoría búsqueda inválida, no disponible 404, concurrencia de actas, mensajes; editar con conservación de vacíos y cada mensaje de `validar_datos_generales`; asimetría de editar (403 sin `view_rendicioncuentamensual`); baja lógica con actor y cascada.
- Frontend: no reenvío tras 504 `uncertain`, CSRF presente, deshabilitado mientras envía, errores por campo, redirect solo a ruta interna esperada.
- Diferencial: POST nativos (con y sin AJAX) idénticos; `test_rendicioncuentasmensual_domain_rules.py`, `test_rendicioncuentasmensual_acta_auditoria.py`, `test_rendicion_auditoria_issue_2673.py`, `test_rendicioncuentasmensual_services_unit.py` verdes.
- Visual: S13 por pantalla y estado.

### Riesgos

- Web push síncrono dentro de la transacción de `ejecutar` y del faltante: con muchas suscripciones puede acercarse a la ventana G1 de 60 s. Hoy la ruta nativa corre con la lectura de 25 s del proxy, así que la API no empeora el margen; el resultado incierto se informa sin reintentar.
- `finalizar_*` aplica borradores y notifica: un reenvío manual tras 504 puede notificar dos veces; por eso la UI pide revisar antes de reintentar.
- La baja no tiene regla de etapa ni estado: cualquier lector puede dar de baja (paridad).

## RM01.03 Documentos y comprobantes

### Rutas nativas

| Método | URL | Nombre | Vista | Template o consumidor |
| --- | --- | --- | --- | --- |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/documento/<pk>/ver/` | `rendicioncuentasmensual_documento_ver` | `views.py:930-954` | enlaces «Ver» del detalle y de `auditoria_documentacion.html` |
| POST | `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/descargar-pdf/solicitar/` [82cfd28a1] | `rendicioncuentasmensual_download_pdf_solicitar` | `views.py:895-916` | `components/pdf_descarga_action.html` (`detail.html:45`; `gestion_organizaciones/templates/organizacion_rendicion_detail.html:88` con etiqueta «Descargar»), `static/custom/js/rendicioncuentasmensual_pdf_descarga.js` |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/descargar-pdf/estado/` [82cfd28a1] | `rendicioncuentasmensual_download_pdf_estado` | `views.py:919-927` | polling del mismo JS |
| GET | `/rendicioncuentasmensual/rendicioncuentasmensual/detalle/<pk>/descargar-pdf/` | `rendicioncuentasmensual_download_pdf` | `views.py:804-881` [82cfd28a1: entrega el archivo ya generado] | `url_descarga` del estado `listo` |
| GET, POST | `/rendicioncuentasmensual/rendicioncuentasmensual/nuevo/<comedor_id>/` | `rendicioncuentasmensual_create` | `views.py:957-995` | `rendicioncuentasmensual_form.html:1-72`, `static/custom/js/rendicioncuentasmensual_form.js` |
| POST | `/rendicioncuentasmensual/eliminar-archivo/<archivo_id>/` | `eliminar_archivo` | `views.py:64-86` | `rendicioncuentasmensual_form.js:25-70` |
| GET (media) | `rendicion.acta_auditoria.url`, `rendicion.documento_regularizacion.url` | (sin vista) | `models.py:667-679` | `detail.html:231-244` |

### Acceso

- Ver documento, PDF, solicitud y estado del PDF: decorador con los cinco permisos (`urls.py:63-90`) + `LoginRequiredMixin`; sin alcance de objeto. [82cfd28a1] La solicitud es un POST con CSRF de Django.
- Alta: decorador solo `rendicioncuentasmensual.view_rendicioncuentamensual` (`urls.py:98-104`).
- `eliminar_archivo`: solo `@login_required` y `@require_POST`; sin permiso de código, sin alcance y sin regla de estado; CSRF de Django activo (no tiene `csrf_exempt`). Asimetría conservada y documentada; no se expone en la API.
- Actas: URL de media directa; el acceso depende del servido de media, no de una vista de permisos.

### Datos y reglas

- Ver documento: `DocumentacionAdjunta` no borrada y con rendición, si no 404; `archivo.open("rb")` falla → 404 «El archivo del documento no está disponible.». `FileResponse` inline (`as_attachment=False`), nombre `basename(archivo.name)`, content-type inferido por el nombre. No verifica que la rendición esté activa.
- [82cfd28a1] PDF consolidado asincrónico (#2845: `services_pdf_descarga.py`, modelo `RendicionPdfDescarga` en `models.py:840-900`, migraciones `0027` y `0029`, tarea Celery `rendicioncuentasmensual.tasks.generar_pdf_descarga` en la cola `comedores`, purga diaria `purgar_pdfs_descarga` en `config/celery.py:38`):
  - Solicitar (`solicitar_pdf_descarga`): exige todos los documentos vigentes validados, si no «La descarga consolidada solo está disponible cuando la rendición está finalizada.»; sin documentos validados «La rendición no tiene documentación para descargar.» (los dos como 400 `{"estado": "error", "mensaje"}`). Reutiliza la solicitud si la huella de los documentos no cambió (lista con archivo, o en curso hace menos de 15 min); si no, la reinicia en `pendiente` con un token nuevo y la encola al confirmar la transacción. Si el broker no responde (3 s, sin reintentos) la solicitud queda en `error` con «No se pudo generar el PDF. Intentá nuevamente.».
  - Estado (`obtener_estado_pdf_descarga`): `{"estado": "sin_solicitar", "mensaje": ""}` sin solicitud; si no `{estado, mensaje}`, con `url_descarga` en `listo`. Una solicitud en curso de más de 15 min se informa como `error` con «La generación del PDF tardó demasiado. Intentá nuevamente.»; una lista sin archivo, con el mensaje genérico. El GET de estado no escribe.
  - Descarga (`descargar-pdf/`): con el PDF vigente, `FileResponse` attachment `application/pdf` con el nombre de abajo; sin PDF listo, mensaje informativo «El PDF todavía no está listo. Usá «Generar descarga» y esperá a que termine.» y redirect al detalle; rendición no finalizada, el mensaje de error y redirect.
  - JS: botón con spinner y «Generando PDF…» mientras espera; textos «Generando el PDF. Puede tardar unos minutos.», «PDF listo. La descarga comienza en unos segundos.», error «No se pudo generar el PDF.» o el `mensaje` del servidor; consulta cada 3 s hasta 15 min y entonces «La generación del PDF tardó demasiado. Intentá nuevamente.».
  - Generación (en el worker): `RendicionCuentaMensualService.generar_pdf_descarga_rendicion` (`services.py:916-1006`), sin cambios de reglas: Anexa en orden de categorías: PDF tal cual, imágenes convertidas, Office por LibreOffice (`service_helpers.py:154-183`, timeout 120 s por documento), resto o ilegible como página placeholder. Nombre (`views.py:827-848`): `{PROYECTO}-{CONVENIO}-RENDICION_{n}-{MES}{AAAA}.pdf` con partes normalizadas (`SIN_PROYECTO`, `SIN_CONVENIO`, meses `ENE`..`DIC` o `MES`).
- Alta (`RendicionCuentaMensualForm`, `forms.py:28-64`): `fields="__all__"` menos los excluidos, es decir `proyecto`, `mes` (choices 1-12, requerido), `anio` (requerido), `convenio`, `nombre`, `numero_rendicion`, `periodo_inicio`, `periodo_fin`, `linea_programatica` (requerido, default Tradicional), `estado` (requerido, default `elaboracion`), `documento_adjunto`, `observaciones`, `monto_observado`, `usuario_creador`, `usuario_ultima_modificacion`. El template solo renderiza `mes`, `anio`, `observaciones` y, de `DocumentacionAdjuntaForm`, `nombre` y `archivo`. Adjuntos: `request.FILES.getlist("archivo")`, un `DocumentacionAdjunta` por archivo (nombre = nombre del archivo, categoría por defecto `comprobantes_alimentario`), storage `rendicioncuentasmensualdocumentos_adjuntos/` con nombre acotado a 100 (`models.py:14-32`).
- `eliminar_archivo`: `?preview=1` o `preview=1|true|True` en POST devuelve `{success: true, preview}`; si no, baja lógica en cascada con actor y `{"success": true, "message": "Archivo eliminado correctamente."}`; inexistente 404 HTML.

### Acciones y efectos

- Ver documento escribe en un GET: `registrar_visualizacion_documento` (`services.py:142-161`) guarda `visualizacion_etapa`, `visualizacion_usuario`, `visualizacion_fecha` solo si el actor tiene el permiso de la etapa vigente. El detalle recarga al volver del visor (`rendicioncuentasmensual_detail.js:208-258`) salvo revisiones sin guardar.
- [82cfd28a1] PDF: la solicitud escribe (`RendicionPdfDescarga`, archivo en `rendicioncuentasmensual_pdf_consolidado/`, borrado del anterior) y encola; el estado y la descarga no escriben. Retención de 7 días.
- Alta: guarda rendición con `comedor`, `usuario_creador`, `usuario_ultima_modificacion` y adjuntos; éxito redirect a `rendicioncuentasmensual_list`. Inválido: `get_context_data` reemplaza el form ligado por uno vacío (`views.py:938`), así que los errores no se muestran.
- No hay correo en estas rutas. [82cfd28a1] Hay un job Celery: la generación del PDF.

### API web del runtime

| Método | Path | Request | Respuesta | Códigos |
| --- | --- | --- | --- | --- |
| GET, POST | `comedor/<comedor_id>/nuevo/` | POST multipart de `RendicionCuentaMensualForm` + `archivo` múltiple | GET `{fields, initial}`; POST `{ok, redirect}` | 200; 400 `{errors}`; 403; 404 comedor inexistente. Condicionado (ver Riesgos) |

Sin endpoints JSON para ver documento ni actas: se conservan como GET nativos enlazados desde React (`ver_url`, `acta_auditoria_url`, `documento_regularizacion_url` del JSON de RM01.01). [82cfd28a1] El PDF largo sigue fuera de la API web: React reproduce el flujo nativo contra las URL nativas `descargar-pdf/solicitar/` (POST con CSRF), `descargar-pdf/estado/` (polling, mismo intervalo y tope) y `descargar-pdf/` (navegación completa), que ya responden JSON y nunca esperan la generación. No se agrega un endpoint G1 para eso. `eliminar_archivo` no se expone: no tiene llamador vivo en HEAD (solo el JS del alta, cuyo bloque `archivos_adjuntos` nunca llega al contexto de `CreateView`).

### Módulo React

- `src/frontends/apps/sisoc/src/routes/rendicionMensualDocumentos.tsx` + test. Posee `/rendicioncuentasmensual/rendicioncuentasmensual/nuevo/<comedor_id>/` solo si la caracterización lo habilita; exporta la celda «Ver» con estado de visualización y el botón «Generar descarga» que monta el detalle.
- `ver/` y `descargar-pdf/` no son paths React: el navegador los abre directo (pestaña nueva para «Ver», como `target="_blank"`). [82cfd28a1] «Generar descarga» es el formulario asincrónico descripto arriba (sin reintento automático del POST; el polling solo repite el GET de estado).
- Registro en `ROUTES` antes de `rendicionMensual`.
- Volver nativo del alta: sin `volver_url`, `href="/"`; botón «Cancelar» a `rendicioncuentasmensual_list`.

### Criterios de aceptación

- «Ver», «Visualizado» (con título «Por {usuario} el {fecha}»), «Sin visualizar», «Generar descarga» y [82cfd28a1] los textos del flujo asincrónico citados arriba.
- Alta: título de pestaña «Detalle de Rendición de Cuenta», encabezado «Crear Seguimiento mensual», tarjetas «Datos asociados» y «Documentación Adjunta», «Agregar Archivo», «Eliminar Archivo», «Guardar», «Cancelar», miga «Rendiciones de Cuenta» › «Crear Rendición».
- Paridad S13 y orden de Tab nativo; los binarios no se comparan visualmente sino por cabeceras y bytes.

### Casos de prueba

- Backend: ver documento permitido/denegado/anónimo, borrado 404, archivo ausente 404 con el texto, registro de visualización solo con permiso de etapa; [82cfd28a1] PDF: `comedores/tests/test_rendicion_pdf_descarga_issue_2845.py` sigue verde y React no cambia sus respuestas; nombre de archivo, content-type, placeholder ante PDF ilegible (LibreOffice simulado); caracterización del alta nativa (POST con solo `mes`, `anio`, `observaciones`); `eliminar_archivo` sin cambios.
- Frontend: enlaces con `href` nativo exacto, `target="_blank"` en «Ver», sin fetch de binarios.
- Diferencial: bytes y cabeceras de PDF y documento iguales a la base.

### Riesgos

- Alta probablemente inoperante hoy (por lectura de fuente, sin ejecución): el form exige `linea_programatica` y `estado`, que el template no envía, y el contexto descarta los errores. Antes de migrar se corre la caracterización; si se confirma, el path `nuevo/` queda nativo y el defecto se registra aparte. No se corrige dentro de M2.
- [82cfd28a1] El PDF consolidado ya no corre en el request: lo genera Celery (cola `comedores`). Sin worker o sin broker, la solicitud queda en error o vence a los 15 min; React debe mostrar esos mensajes, no reintentar el POST por su cuenta.
- Actas por URL de media directa: mismo acceso que hoy; la API las expone tal cual el template.
- `eliminar_archivo` sin permiso ni alcance: hallazgo de seguridad existente; no se amplía su superficie.

## Decisiones técnicas tomadas

1. Partición: RM01.01 toda la lectura (listado, lista por comedor, detalle GET y CSV); RM01.02 todas las mutaciones del circuito y de la rendición (transiciones, revisión, faltantes, auditoría, edición de datos y baja); RM01.03 binarios, archivos y alta con adjuntos. Fundamento: separa documentos, auditoría y transiciones como pide el riesgo del catálogo, y cada pathname tiene un solo módulo dueño.
2. El POST único del detalle se divide en `acciones/`, `documentos/<id>/revision/` y `faltantes/`, conservando el orden de chequeos y permisos de cada rama. Fundamento: un solo endpoint con tres significados impide validar request y respuesta.
3. `ValidationError` del servicio → 409; errores de form → 400. Fundamento: los servicios evalúan estado bajo bloqueo; el 409 deja claro que el cambio no se aplicó por estado o regla.
4. Binarios (documento, PDF, CSV, actas) quedan como GET nativos enlazados. Fundamento: regla del brief. [82cfd28a1] El PDF ya no excede la ventana G1 (es asincrónico), pero su solicitud y su estado siguen en las URL nativas porque ya devuelven JSON; envolverlos no agrega nada.
5. `comedor/<id>/` responde 404 ante comedor inexistente e ignora `page`. Fundamento: el 500 y el 404 por paginación global son artefactos sin salida visible; la ruta nativa los conserva.
6. `eliminar_archivo` no se publica en la API. Fundamento: no tiene llamador vivo y publicarlo ampliaría una superficie sin permiso.
7. El alta solo migra si la caracterización muestra que funciona. Fundamento: paridad sin reproducir un defecto en un cliente nuevo.
8. Reglas por organización y línea (cupo territorial por código + organización, elegibles de acta y auditoría, categorías y períodos por línea) se usan solo a través de los servicios existentes; nada se recalcula en la API ni en React.
9. API PWA existente (`comedores/api_views.py:1273-1960`, acciones `rendiciones`, `rendiciones/validar`, `rendiciones/<id>`, `modelos/.../download`, `documentacion`, `comprobantes`, `presentar`, `eliminar` bajo `/api/comedores/<pk>/`, con `IsPWAUserForComedor`, `CanViewPwaRendicionesPermission`, `IsPWARepresentativeForComedor`, `HasMobileRendicionPermission`, `IsPWAWriteAllowed`) y el legajo de Organización (`gestion_organizaciones/urls.py:85-89`) son consumidores existentes que no cambian. La API web no reutiliza sus permisos de token.

## Puntos estrictamente humanos

Ninguno. Los hallazgos de acceso (sin alcance de objeto, `eliminar_archivo` sin permiso, baja sin regla de estado) se conservan por la decisión de paridad S13; cambiarlos es un trabajo aparte que sí requeriría decisión de producto.

## Incertidumbres

- [sin ejecutar] Que el alta nativa nunca persista: deducido de `forms.py:28-49`, `views.py:934-940` y el template; requiere la prueba de caracterización.
- [sin ejecutar] 500 de la baja con `comedor` nulo después de aplicar la baja lógica.
- [resuelto 82cfd28a1] El marco y la sesión salen de `/api/web/session/` (`routes/MainFrame.tsx`); la entrada React local es el `web_preview.py` de cada app, sin montar en producción.
- [resuelto 82cfd28a1] Preferencias de columnas: POST JSON a `/ajax/columnas-preferencias/` (`column_config.js`), reutilizado sin cambios.
- [no confirmado] Que `webpush` tenga timeout propio; no se inspeccionó la librería.
- [no confirmado] Servido y protección de media para actas en cada entorno.

## Fuente

Refresco [82cfd28a1]: `rendicioncuentasmensual/urls.py:1-115`, `views.py:1-1058`, `auditoria.py:83-183`, `services_pdf_descarga.py:1-288`, `tasks.py`, `models.py:840-900`, `templates/components/pdf_descarga_action.html`, `templates/rendicioncuentasmensual_auditoria.html:230-245`, `templates/rendicioncuentasmensual_detail.html:40-50,170-185`, `static/custom/js/rendicioncuentasmensual_pdf_descarga.js`, `kernel/core/services/column_preferences/builders.py:15-100`, `comedores_runtime/urls.py`, `comedores_runtime/web_api_urls.py`, `config/url_registry.json`.

HEAD 4ea95bcbe (versión original):

- `src/backends/comedores/rendicioncuentasmensual/urls.py:1-99`; `views.py:1-1003`; `forms.py:1-276`; `auditoria.py:1-330`; `models.py:1-846`; `services.py:1-680,824-1060,1200-1230,1306-1666,1668-2083`; `filter_config.py:1-253`; `favorite_filters.py:1-32`; `service_helpers.py:154-183`.
- Templates: `rendicioncuentasmensual_list.html:1-60`, `rendicioncuentasmensual_global_list.html:1-65`, `components/rendicion_global_list_cell.html:1-35`, `rendicioncuentasmensual_detail.html:1-567`, `rendicioncuentasmensual_auditoria.html:1-281`, `components/auditoria_documentacion.html:1-35`, `rendicioncuentasmensual_form.html:1-72`, `rendicioncuentasmensual_datos_form.html:1-41`, `rendicioncuentasmensual_confirm_delete.html:1-20`; JS `rendicioncuentasmensual_form.js:1-70`, `rendicioncuentasmensual_detail.js:100-170,205-258`.
- `src/backends/comedores/rendicioncuentasmensual/migrations/0018_stage_permissions.py:1-60`.
- `src/backends/comedores/comedores_runtime/urls.py:1-35`; `src/backends/config/backends.json:240-300`; `src/backends/config/url_registry.json:2008-2020,3523-3555`.
- `src/backends/kernel/core/decorators.py:1-67`; `kernel/core/mixins.py:1-119`; `kernel/core/soft_delete/view_helpers.py:80-118`; `kernel/core/soft_delete/base.py:74-91`; `kernel/iam/services.py:90-115`; `kernel/core/backend_proxy.py:355-420`; `kernel/core/urls.py:53-58`; `kernel/templates/components/back_button.html:1-27`; `kernel/templates/includes/sidebar/opciones.html:400-430`.
- `src/backends/sisoc_core/usuarios/web_navigation.py:190-222`; `sisoc_core/insumos/web_api_urls.py`, `web_api_views.py:1-120`; `sisoc_core/usuarios/web_api_urls.py`.
- `src/backends/comedores/comedores/api_views.py:1268-1300,1350-1360,1430-1440,1536-1545,1700-1716`; `comedores/api_urls.py:1-9`; `comedores/templates/comedor/comedor_detail.html:1135-1136`; `comedores/services/comedor_service/impl.py:630-632,782,818`; `pwa/services/push_service.py:123-150,181-221`.
- `src/frontends/apps/sisoc/src/routes/index.ts`, `types.ts`, `insumos.tsx:1-30`, `userImport.tsx:1-90,231,260,317-320`.
- `docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md`; commit `668c61fe4` (timeouts de gunicorn 75 s core y 65 s runtimes).
- Fuera de HEAD (disco): `docs/plans/2026-T4/2026-10-27-2785-entregas-por-flujo.json` (flujo RM01 y `contract_profiles`), `2026-10-28-2785-comedores-legajo-base-m2.md`, `2026-10-28-2785-comedores-certificaciones-montos-m2.md`.
