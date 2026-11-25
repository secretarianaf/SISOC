# EX01.01, EX01.02, EX02.01, EX02.02: expedientes de pago e importación de expedientes

Estado M2 ejecutable: contrato basado en fuente HEAD 4ea95bcbe, sin ejecución de app, DB, correo, proveedores ni capturas.
Entregas del catálogo `2026-10-27-2785-entregas-por-flujo.json`: EX01.01 Consulta y ficha de expediente [L, lectura y navegación],
EX01.02 Operaciones sobre expediente [W, acción o transición de circuito], EX02.01 Preparación, validación e importación
[J, job de importación o envío] y EX02.02 Errores y resultado del procesamiento [L, lectura y navegación].
Riesgos del catálogo que este contrato hace operativos: «efectos financieros no se recalculan en React» (EX01) y
«Borrar datos importados no es limpieza de UI; acción sensible separada» (EX02).

## Entregas y orden

| ID | Título | Perfil | Rutas nativas cubiertas | Depende de |
| --- | --- | --- | --- | --- |
| EX01.01 | Consulta y ficha de expediente | L | `expedientespagos_list`, `expedientespagos_detail` | setup compartido `api/web/comedores/` (G1), marco legado React |
| EX01.02 | Operaciones sobre expediente | W | `expedientespagos_create`, `expedientespagos_update`, `expedientespagos_delete` | EX01.01 (retornos a listado y ficha) |
| EX02.02 | Errores y resultado del procesamiento | L | `importarexpedientes_list`, `importarexpediente_detail`; conserva `importarexpedientes_ajax`, `importarexpediente_detail_ajax`, `descargar_archivo_importado` | setup compartido; componente de filtros combinables (ver Riesgos) |
| EX02.01 | Preparación, validación e importación | J | `upload`, `importar_datos`, `borrar_datos_importados`, `importar_fechas_acreditacion` | EX02.02 (pantallas de destino y mensajes) |

Orden recomendado: EX01.01 → EX01.02 → EX02.02 → EX02.01. EX02 antes que EX01 solo si se prioriza el circuito de lotes;
no hay dependencia técnica de EX02 sobre EX01 más allá del modelo compartido `ExpedientePago`.

Montaje real (comprobado): el runtime Comedores (`config/backends.json:239-300`, `urlconf` `comedores_runtime.urls`) incluye
`expedientespagos.urls` bajo `expedientespagos/` (`comedores_runtime/urls.py:14`) y `importarexpediente.urls` bajo `""`
(`comedores_runtime/urls.py:24`). Por eso las URL nativas llevan `expedientespagos/` duplicado, confirmado por
`config/url_registry.json:2228-2250` (`^expedientespagos/expedientespagos/(?P<pk>[0-9]+)/...`). `importarexpedientes/upload`
no tiene barra final (`url_registry.json:3718`). Los prefijos `expedientespagos/` e `importarexpedientes/` ya están en
`url_prefixes` del runtime (`backends.json:265,268`), así que el core los reenvía con el proxy (5 s de conexión, 25 s de lectura
según la decisión G1).

Consumidores indirectos que no cambian y deben seguir enlazando las mismas URL:
- Ficha de comedor (CO07, `docs/plans/2026-T4/2026-10-28-2785-comedores-legajo-base-m2.md`): la tarjeta «Mes de ejecución»
  (`comedores/templates/comedor/comedor_mes_ejecucion_card.html:1-38`, incluida en `comedor_detail.html:1439-1450` solo si
  `mostrar_mes_ejecucion`) muestra el expediente más reciente por período (`views/comedor.py:1003-1045`: solo programa 2,
  `ordenar_expedientes_por_periodo_desc(...).first()`, cantidad = suma de prestaciones, monto = `total` o suma de montos) y
  su botón «Ver más» va a `expedientespagos_list comedor.id`. El contrato CO07 no enumera esta tarjeta: queda registrada aquí
  como dependencia de lectura; CO07 la migra, EX01 solo garantiza que el destino «Ver más» siga existiendo con el mismo path.
- La ficha también precarga `expedientes_pagos` (`comedor_service/impl.py:596-598`).
- Acompañamiento: botón «Expedientes de Pagos» → `expedientespagos_list comedor.id` (`acompanamientos/templates/acompañamiento_detail.html:31-34`).
- Admisiones: tabla de expedientes en el detalle (`admisiones/views/web_views.py:424-458`, `admisiones_detalle.html:626-660`), vía
  `ExpedientesPagosService.obtener_expedientes_pagos`.
- Menú: «Expedientes de Pago» → `importarexpedientes_list` con `importarexpediente.view_archivosimportados`
  (`kernel/templates/includes/sidebar/opciones.html:378-386`, `sisoc_core/usuarios/web_navigation.py:197-198`).
- Benchmarks por nombre de URL (`kernel/core/benchmarks/scenarios.py:160,199`).

## EX01.01 Consulta y ficha de expediente

### Rutas nativas

| Método | URL en runtime y core | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| GET | `/expedientespagos/expedientespagos/<pk>/` (`pk` = ID de comedor) | `expedientespagos_list` | `expedientespagos/views.py:47-94` `ExpedientesPagosListView` | `expedientespagos_list.html:1-25` |
| GET | `/expedientespagos/expedientespagos/<pk>/detalle/` (`pk` = ID de expediente) | `expedientespagos_detail` | `views.py:97-107` `ExpedientesPagosDetailView` | `expedientespagos_detail.html:1-194` |

Definición en `expedientespagos/urls.py:12-21`. Ninguna de las dos tiene decorador de permisos.

### Acceso

- Ambas: `LoginRequiredMixin` (anónimo → 302 al login). Sin permiso de acción: cualquier usuario autenticado lista y ve.
- Sin scope de objeto: el listado filtra solo `comedor=pk` (`services.py:139-150`) y la ficha busca por `pk` sin relación con el
  usuario; no se aplica el helper de scope de comedores de CO07. Comedor inexistente en el listado → 200 con tabla vacía.
  Expediente inexistente o dado de baja lógica → 404 (`DetailView` usa `ExpedientePago.objects`, que excluye `deleted_at`).
- Botón «Nuevo Expediente de Pago» del listado solo con `has_any_perm` sobre `comedores.view_comedor`,
  `admisiones.view_admision`, `acompanamientos.view_informacionrelevante`, `expedientespagos.view_expedientepago`
  (`expedientespagos_list.html:15-22`). Las acciones «Editar» y «Eliminar» de la ficha se muestran sin condición de permiso
  (`expedientespagos_detail.html:18-39`); el permiso lo aplica la ruta destino (403).
- Asimetrías a conservar y documentar: lectura sin permiso ni scope; acciones visibles sin permiso en la ficha.

### Datos y reglas

Modelo `ExpedientePago` (`expedientespagos/models.py:7-118`, con `SoftDeleteModelMixin`: `deleted_at`, `deleted_by`).

Listado:
- Orden `ordenar_expedientes_por_periodo_desc` (`services.py:24-36`): `-ano`, `-mes_pago` traducido a número por alias
  (enero…diciembre, «setiembre», 1-12 con y sin cero), `-fecha_creacion`, `-id`; meses no reconocidos valen 0.
- Columnas (`views.py:70-77`, celdas `views.py:27-44`): «Mes de Pago» (`mes_pago` o «-»), «Año» (`ano` o «-»),
  «Expediente de Pago» (o «-»), «Expediente del Convenio» (o «-»), «Total» (`$` + `monto_sin_decimales(total)`),
  «Fecha de creación» (`dd/mm/AAAA` o «-»). Texto escapado.
- Columnas configurables por usuario: `build_columns_context_for_custom_cells(request, "expedientes_pagos_list", ...)`
  (`views.py:79-87`, `kernel/core/services/column_preferences/builders.py:103-176`); el modal se incluye en
  `components/data_table.html:8-10` y persiste en `column_preferences` (`kernel/core/urls.py:63-66`).
- Acción por fila «Ver» → `expedientespagos_detail` con el `pk` del expediente (`views.py:90-92`).
- Paginación: la tabla visible no pagina (el include no pasa `include_pagination`, `expedientespagos_list.html:23`;
  `data_table.html:179-181`) y muestra todos los expedientes del comedor. `paginate_by = 10` se aplica a un queryset global sin
  uso visual (`views.py:52-56`): `?page=` fuera del rango global responde 404 (paginación estándar de `ListView`). Conservar.
- Sin búsqueda ni filtros. Vacío: «No hay expedientes de pagos registrados para este comedor.».

Ficha (`expedientespagos_detail.html:44-191`): tarjeta «Información del Expediente» con «Expediente de Pago»,
«Expediente del Convenio», «Mes de Pago», «Mes de Convenio», «Año», «Organización», «Anexo» (todos con «-» si vacío),
separador, «Total Prestaciones», «Gastos Accesorios 6%», «Total» (con `$` y `monto_sin_decimales`), separador,
«Número de Orden de Pago», «Fecha de Creación» (`d/m/Y`), «Fecha de Pago al Banco», «Fecha de Acreditación» (`d/m/Y` o «-»),
«Observaciones» solo si hay texto. Tarjeta «Prestaciones Mensuales»: tabla «Tipo», «Prestaciones», «Monto Mensual» con filas
Desayuno, Almuerzo, Merienda, Cena y pie «Total» / «—» / `$total`. El pie muestra `total` guardado, no la suma de filas.
Prestaciones `0` se muestran «-» por `default`.

### Acciones y efectos

Solo lectura. Efecto lateral: `ensure_csrf_cookie` en el listado (`views.py:47`). Breadcrumb del listado → `detalle_acompanamiento`
(`/acompanamientos/acompanamiento/<comedor_id>/detalle/`, que exige `acompanamientos.view_informacionrelevante`); breadcrumb de la
ficha → `expedientespagos_list expediente.comedor_id`. Si `comedor_id` es nulo (FK `SET_NULL`), el `{% url %}` de la ficha falla:
no caracterizado (ver Incertidumbres).

### Exportaciones

No aplica.

### API web del runtime

Archivos propuestos: `src/backends/comedores/expedientespagos/web_api_urls.py`, `web_api_views.py`, `web_api_serializers.py`.
El montaje bajo `api/web/comedores/` en el agregador del runtime y en `backends.json` es setup compartido del padre.

| Método | Path | Respuesta |
| --- | --- | --- |
| GET | `/api/web/comedores/expedientespagos/comedores/<comedor_id>/` | 200 `{comedor_id, can_create, rows[], column_config, breadcrumb_url}` |
| GET | `/api/web/comedores/expedientespagos/<pk>/` | 200 `{expediente{...}, comedor_id, list_url, update_url, delete_url}`; 404 |

- `rows[]`: `{id, mes_pago, ano, expediente_pago, expediente_convenio, total_display, fecha_creacion_display, detail_url}` con
  los mismos textos de celda que `_build_expediente_pago_list_item` (reusar esa función, no reimplementar formato), en el orden
  del servicio. `can_create` = la misma condición `has_any_perm` del template. `column_config` = salida de
  `build_columns_context_for_custom_cells` con la misma `list_key`.
- `page` en query se conserva: si llega, se valida contra el paginador global igual que la vista nativa y devuelve 404 JSON.
- Ficha: todos los campos del template como valores crudos más `*_display` para montos (`monto_sin_decimales`) y fechas
  (`d/m/Y`), para que React no formatee dinero.
- Acceso: `SessionAuthentication` + `WebGatePermission`; sin permiso de acción (paridad). Anónimo: 401 JSON del core (G1),
  no 302. Requisito web pendiente: 403 JSON con `state` y `required_action_url`. Comedor inexistente: 200 con `rows: []`.
- Cabeceras `Cache-Control: private, no-store` y `Vary: Cookie` (patrón `insumos/web_api_views.py`).

### Módulo React

`src/frontends/apps/sisoc/src/routes/expedientesPagos.tsx` + `expedientesPagos.test.tsx`, registrado en `ROUTES` antes de
`businessRoute` (mismo patrón que `userImportRoute`, con marco legado `userJobsFrame` o el equivalente compartido).
Paths que posee: `/expedientespagos/expedientespagos/<n>/` y `/expedientespagos/expedientespagos/<n>/detalle/`.
Volver nativo: no hay botón Volver; los retornos son los breadcrumbs literales (listado → `/acompanamientos/acompanamiento/<comedor_id>/detalle/`,
ficha → `/expedientespagos/expedientespagos/<comedor_id>/`). La entrada que sirve el SPA en esos paths es setup compartido.

### Criterios de aceptación

- Listado: título de pestaña «Listado de Expedientes de pagos», encabezado «Listado de Expedientes de Pagos», breadcrumb
  «Expedientes de pagos», botón «Nuevo Expediente de Pago» solo con los cuatro permisos, columnas y orden de arriba,
  acción «Ver», vacío «No hay expedientes de pagos registrados para este comedor.».
- Ficha: pestaña «Expediente de Pago», breadcrumb «Expedientes de pagos» › «Detalle», menú «Acciones» con «Editar» y «Eliminar»
  (este en rojo), tarjetas «Información del Expediente» y «Prestaciones Mensuales» con las etiquetas literales listadas.
- React no calcula `total`, `total_prestaciones` ni `gastos_accesorios`: muestra los valores guardados.
- Orden de Tab: breadcrumb, botón de acción, controles de columnas, tabla y acciones por fila, en el mismo orden DOM nativo.
- Regla visual S13: paridad estructural y diff perceptual ≤ 1 % sin antialiasing, tolerancia 2 CSS px, por URL, estado
  (vacío, con filas, con observaciones y sin ellas), rol (con y sin permiso de alta) y viewport (escritorio y móvil).

### Casos de prueba

- Backend (`src/backends/comedores/expedientespagos/tests/test_web_api.py` o junto a los tests existentes
  `src/backends/comedores/tests/test_expedientespagos_views_unit.py`): autenticado sin permisos → 200 en listado y ficha;
  anónimo → 401; requisito pendiente → 403 con `state`; `can_create` true/false según permisos; orden por período con alias de mes;
  celdas idénticas a `_build_expediente_pago_list_item`; comedor inexistente → `rows: []`; expediente inexistente y dado de baja → 404;
  `page` inválida → 404.
- Frontend (vitest): render de listado vacío y con filas, permiso de alta, ficha con y sin observaciones, 401/403/error de red.
- Diferencial: GET nativo de ambas rutas sin cambios (HTML, código y redirects), comparado contra la base.
- Visual: capturas de referencia nativa y candidato React por URL, estado, rol y viewport.

### Riesgos

- Lectura sin permiso ni scope expone expedientes de cualquier comedor a cualquier usuario autenticado: es el comportamiento
  actual; se conserva (ver Puntos estrictamente humanos).
- El paginador global inútil puede devolver 404 con `?page=` aunque el comedor tenga filas; se conserva por paridad.

## EX01.02 Operaciones sobre expediente

### Rutas nativas

| Método | URL | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| GET, POST | `/expedientespagos/expedientespagos/<pk>/nuevo/` (`pk` = comedor) | `expedientespagos_create` | `views.py:110-183` | `expedientespagos_form.html:1-57` |
| GET, POST | `/expedientespagos/expedientespagos/<pk>/editar/` (`pk` = expediente) | `expedientespagos_update` | `views.py:186-258` | `expedientespagos_form.html:1-57` |
| GET, POST | `/expedientespagos/expedientespagos/<pk>/eliminar/` (`pk` = expediente) | `expedientespagos_delete` | `views.py:261-275` + `kernel/core/soft_delete/view_helpers.py:90-118` | `expedientespagos_confirm_delete.html:1-19` |

### Acceso

- Las tres rutas: `permissions_any_required` con `comedores.view_comedor`, `admisiones.view_admision`,
  `acompanamientos.view_informacionrelevante`, `expedientespagos.view_expedientepago` (`urls.py:22-57`), envolviendo la vista
  completa: GET y POST igual. El decorador corre antes de `LoginRequiredMixin`: anónimo → 403, no redirect
  (`kernel/core/decorators.py:8-47`). Superusuario pasa siempre. Son permisos de **lectura** usados como permiso de escritura: conservar.
- Banderas de rol (`views.py:115-139` y `191-215`): `es_area_legales` = superusuario o cualquiera de los cuatro códigos, por lo
  tanto siempre verdadera para quien pasó el decorador; `es_tecnico_comedor` = superusuario o cualquiera de los tres primeros.
  Usuario solo con `expedientespagos.view_expedientepago` → técnico falso.
- Sin scope de objeto ni de comedor.

### Datos y reglas

`ExpedientePagoForm` (`expedientespagos/forms.py:7-110`): `ModelForm` con `fields = "__all__"` y `exclude = ["comedor", "mes_convenio"]`.
Por derivación de fuente también incluye `deleted_at` y `deleted_by` (campos editables del mixin, `kernel/core/soft_delete/base.py:77-88`),
que el template no renderiza. Campos renderizados, en este orden (`expedientespagos_form.html:28-50`):

| Campo | Tipo | Modelo |
| --- | --- | --- |
| `expediente_pago` | texto | CharField 255, opcional |
| `expediente_convenio` | texto | CharField 255, **requerido** en modelo |
| `anexo`, `if_cantidad_de_prestaciones`, `if_pagado` | texto | CharField 255, opcionales |
| `total_prestaciones`, `gastos_accesorios`, `total` | decimal | Decimal(10,2), opcionales |
| `mes_pago` | texto | CharField 20, opcional, sin choices |
| `ano` | texto | CharField 4, opcional en modelo |
| `organizacion_creacion`, `numero_orden_pago` | texto | CharField 255, opcionales |
| `fecha_pago_al_banco`, `fecha_acreditacion` | fecha (`type="date"`, formato `%Y-%m-%d`) | DateField, opcionales |
| `observaciones` | textarea | TextField, opcional |
| `prestaciones_mensuales_desayuno/almuerzo/merienda/cena` | entero | IntegerField, requeridos en modelo |
| `monto_mensual_desayuno/almuerzo/merienda/cena` | decimal | Decimal(10,2), requeridos en modelo |

Etiquetas: `verbose_name` del modelo (las `labels` del form refieren a campos inexistentes y no aplican).
Reglas de requerido (`forms.py:14-63`) con las banderas: técnico verdadero → `ano`, las cuatro prestaciones y los cuatro montos
requeridos; técnico falso → `total`, `total_prestaciones`, `gastos_accesorios`, `mes_pago`, `ano`, `organizacion_creacion`,
`numero_orden_pago`, fechas, `observaciones`, prestaciones y montos no requeridos y `clean` completa prestaciones vacías con `0`
y montos con `Decimal("0")` (`forms.py:74-90`). La rama legales falso (copia `expediente_pago` a `expediente_convenio`) es
inalcanzable desde estas vistas. `expediente_convenio` sigue requerido para todos.

Asimetría de alta (`views.py:157-169`): `get_context_data` reemplaza siempre el form por `ExpedientePagoForm()` sin banderas.
GET muestra los requeridos del modelo; POST inválido responde 200 con el formulario **vacío y sin errores**. Edición
(`views.py:238-258`) usa el form con banderas e instancia: errores y valores visibles.

Ninguna operación recalcula `total`, `total_prestaciones` ni `gastos_accesorios`: se guardan como se tipean.

### Acciones y efectos

- Alta POST: `Comedor.objects.get(pk=...)` (comedor inexistente → excepción no capturada, 500); si es válido,
  `ExpedientesPagosService.crear_expediente_pago(comedor, cleaned_data)` (`services.py:41-81`) crea con los 23 campos y `comedor`
  (sin `deleted_*`, sin `mes_convenio`); luego `form_valid` → redirect 302 a `expedientespagos_list` del comedor. Sin mensaje.
  Advertencia de fuente: `CreateView.form_valid` llama `form.save()` después del servicio; con `self.object` ya asignado por el
  servicio, el form conserva su `instance` nueva (sin `comedor`, excluido del form) y, por fuente, crearía un segundo registro con
  `comedor` nulo (ver Incertidumbres; caracterizar con un test antes de tocar).
- Edición POST: `form_valid` fija `instance.comedor` al comedor original (`views.py:233-236`) y guarda con `ModelForm.save()`
  (no usa `actualizar_expediente_pago`). Redirect a `expedientespagos_list` del comedor. Sin mensaje.
- Baja GET: confirmación con `cascade_preview = build_delete_preview(obj)`. `ExpedientePago` no tiene relaciones inversas
  `CASCADE` (`RegistroImportado` usa `DO_NOTHING`), así que el preview muestra un registro. Baja POST: `instance.delete(user=request.user, cascade=True)`
  → `deleted_at`, `deleted_by` (`base.py:100-128`), señal `post_soft_delete`, mensaje «Expediente dado de baja correctamente.»
  y redirect a `lista_comedores_acompanamiento` (`/acompanamientos/acompanamiento/`), no a la ficha ni al listado del comedor.
  Ya dado de baja → 404. El `except DoesNotExist` de `views.py:268-272` es inalcanzable (la vista base levanta `Http404`).
- Transacciones: ninguna explícita en alta y edición; la baja usa el plan de `cascade.py`. Sin archivos, correos ni jobs.
- Auditoría: `auditlog.middleware.AuditlogMiddleware` activo; registro del modelo en `audittrail` no encontrado en fuente.

### Exportaciones

No aplica.

### API web del runtime

| Método | Path | Request | Respuestas |
| --- | --- | --- | --- |
| GET | `/api/web/comedores/expedientespagos/comedores/<comedor_id>/crear/` | — | 200 `{fields[], initial{}, cancel_url}` |
| POST | ídem | multipart o form con los 23 campos | 200 `{ok, redirect}`; 400 `{errors, reset_form: true}`; 403; 404 comedor |
| GET | `/api/web/comedores/expedientespagos/<pk>/editar/` | — | 200 `{fields[], initial{}, comedor_id, cancel_url}`; 404 |
| POST | ídem | 23 campos | 200 `{ok, redirect}`; 400 `{errors}`; 403; 404 |
| GET | `/api/web/comedores/expedientespagos/<pk>/eliminar/` | — | 200 `{id, expediente_pago, cascade_preview, cancel_url}`; 404 |
| POST | ídem | vacío | 200 `{ok, message, redirect}`; 403; 404 |

- Permiso: el mismo `permissions_any_required` de cuatro códigos en GET y POST; anónimo 401 por G1.
- `fields[]` describe cada campo renderizado (`name`, `label`, `type`, `required`, `max_length`, `decimal_places`) derivado del
  form construido como la vista nativa: alta con form sin banderas para GET (paridad de asteriscos), edición con banderas.
- POST reutiliza `ExpedientePagoForm` con `get_form_kwargs` idénticos y, para alta, `ExpedientesPagosService.crear_expediente_pago`
  y el mismo camino de `form_valid`; edición usa el mismo `form_valid`. Los datos que se pasan al form se limitan a los 23 campos
  renderizados: `deleted_at`, `deleted_by`, `comedor` y `mes_convenio` nunca se aceptan desde la API.
- Alta inválida: 400 con `errors` (para diagnóstico y tests) y `reset_form: true`; React presenta el resultado nativo (form vacío
  sin errores). Comedor inexistente en POST: 404 JSON en lugar del 500 nativo (ver Decisiones).
- `redirect` es el path nativo de destino; `message` en baja es «Expediente dado de baja correctamente.».
- Mutaciones: CSRF obligatorio, sin reintento automático; 504 con `uncertain: true` se presenta sin reenviar.
  Duración esperada muy inferior a 60 s (un INSERT/UPDATE).

### Módulo React

Mismo módulo `routes/expedientesPagos.tsx`. Paths adicionales: `/expedientespagos/expedientespagos/<n>/nuevo/`,
`/editar/` y `/eliminar/`. Volver nativo: «Cancelar» del formulario → `expedientes_list_url`
(`/expedientespagos/expedientespagos/<comedor_id>/`, `views.py:166-168,246-248`); «Cancelar» de la baja →
`expedientespagos_detail object.id` (`/expedientespagos/expedientespagos/<pk>/detalle/`). Tras éxito, navegación completa a
`redirect` con el mensaje de baja mostrado en destino como toast/alerta igual que el mensaje Django.

### Criterios de aceptación

- Formulario: pestaña «Crear Expediente de Pago» en ambos casos (el bloque `title` no distingue), encabezado y breadcrumb
  «Crear Expediente de Pago» o «Editar Expediente de Pago» según la ruta, botones «Cancelar» y «Guardar» centrados.
- Baja: pestaña «Acciones», título «Dar de baja Expediente», texto «¿Estás seguro que deseas dar de baja lógica el expediente»
  seguido de `expediente_pago` en mayúsculas y «?», bloque «Total de registros afectados:», botones «Dar de baja» y «Cancelar».
  El breadcrumb «Expedientes de pagos» de la baja tiene `href=""` (enlace a la misma página): conservar.
- Éxito de baja: «Expediente dado de baja correctamente.» en `/acompanamientos/acompanamiento/`.
- Alta inválida: formulario vacío sin errores, foco reiniciado al inicio del documento (`restartKeyboardFromTop`).
- Orden de Tab igual al orden de campos de la tabla anterior. Regla visual S13 en alta vacía, alta inválida, edición con errores,
  confirmación de baja; escritorio y móvil.

### Casos de prueba

- Backend: permitido con cada uno de los cuatro códigos y superusuario; denegado sin ellos (403 en GET y POST); anónimo 401;
  técnico verdadero exige `ano`, prestaciones y montos; solo `view_expedientepago` acepta vacíos y guarda ceros; `expediente_convenio`
  vacío → 400; `max_length` de `ano` (4) y `mes_pago` (20); decimal con más de 2 decimales → 400; `deleted_at` enviado se ignora;
  edición conserva comedor aunque se envíe otro; baja deja `deleted_at`/`deleted_by` y la ficha responde 404; baja repetida → 404;
  alta crea exactamente un registro (fija la conducta real antes de declararla).
- Frontend (vitest): envío único con `postOnce`, 400 de edición pinta errores, 400 de alta resetea, 403, `uncertain` sin reenvío.
- Diferencial: POST nativo de alta, edición y baja con los mismos datos antes y después del cambio (status, redirect, filas).
- Visual: según criterios.

### Riesgos

- Efectos financieros: los totales no se recalculan en ningún lado; React no debe sumar ni sugerir valores.
- Permisos de lectura habilitan escritura y no hay scope: se conserva (ver Puntos estrictamente humanos).
- Posible doble creación en alta (Incertidumbres): si se confirma, es defecto nativo previo; no corregir en silencio dentro de M2.

## EX02.02 Errores y resultado del procesamiento

### Rutas nativas

| Método | URL | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| GET | `/importarexpedientes/listar` | `importarexpedientes_list` | `importarexpediente/views.py:317-344` | `importarexpediente_list.html:1-89`, `partials/importarexpediente_list_rows.html:1-51` |
| GET | `/importarexpedientes/ajax/` | `importarexpedientes_ajax` | `views.py:347-387` | partial de filas + `components/pagination.html` |
| GET | `/importarexpedientes/<id>/` | `importarexpediente_detail` | `views.py:400-444` | `importarexpediente_detail.html:1-117`, `partials/importarexpediente_detail_rows.html:1-22` |
| GET | `/importarexpedientes/<id>/ajax/` | `importarexpediente_detail_ajax` | `views.py:447-499` | partial de errores + paginación |
| GET | `/importarexpedientes/<id>/descargar/` | `descargar_archivo_importado` | `views.py:390-397` | — |

`importarexpediente/urls.py:17-51`. El listado también es destino de casi todas las acciones de EX02.01.

### Acceso

- Las cinco rutas: `permission_code_required("importarexpediente.view_archivosimportados")` (equivale a
  `permissions_all_required` de un código; anónimo → 403) más `LoginRequiredMixin` o `@login_required`.
- Sin scope: cualquier usuario con el permiso ve, descarga e interactúa con lotes de otros usuarios
  (fijado por `tests/test_ajax_endpoints.py:203-240`).
- Los botones del detalle «Completar Importación» y «Eliminar Archivo» se muestran a todo el que ve el detalle; «Actualizar
  fechas de acreditación» solo si `batch.importacion_completada` y `has_any_perm` sobre `importarexpediente.change_archivosimportados`,
  `expedientespagos.change_expedientepago` (`importarexpediente_detail.html:23-51`).

### Datos y reglas

Modelos (`importarexpediente/models.py:66-117`): `ArchivosImportados` (`archivo` FileField `upload_to="importados/"`, `delimiter`,
`fecha_subida`, `usuario`, `count_errores`, `count_exitos`, `importacion_completada`, `numero_expediente_pago`, `mes_pago`,
`ano_pago`; propiedad `periodo_pago` = `MM/AAAA` o `None`), `ErroresImportacion`, `ExitoImportacion`, `RegistroImportado`.

Listado:
- Orden `-fecha_subida`, 10 por página (`views.py:321-326`); página inválida → 404 de `ListView`.
- Filtros combinables: parámetro GET `filters` (JSON) del `AdvancedFilterEngine` (`filter_config.py:12-94`,
  `kernel/core/services/advanced_filters/engine.py:49`) con campos «Archivo», «Usuario», «Número de expediente», «Mes de pago»,
  «Año de pago» (texto: `contains`, `ncontains`, `eq`, `ne`, `empty`), «Cantidad de errores», «Cantidad de éxitos»
  (`eq`, `ne`, `gt`, `lt`, `empty`), «Importación completada?» (`eq`, `ne`; «Sí»/«No»), «Fecha de subida» (fecha sobre
  `fecha_subida__date`). Además `busqueda` sobre `archivo` o `usuario__username` (`views.py:331-335`). Barra con título
  «Buscar Expedientes de Pago».
- Columnas: «Nº Expediente de Pago» (o «Sin informacion»), «Archivo» (nombre guardado del FieldFile, enlace al detalle),
  «Periodo» (`periodo_pago` o «Sin informacion»), «Usuario», «Fecha de Subida» (render de datetime por defecto de Django),
  «Válidos», «Errores», «Importacion Completada» («Si»/«No»), «Acciones» con «Ver» y «Descargar». Vacío:
  «No hay expedientes disponibles.». Paginación con «Volver»/«Continuar». Encabezados con ícono de orden de `listSort.js`
  (orden en cliente sobre la página visible).
- Efecto en GET: `_completar_periodos_faltantes` (`views.py:118-131`) completa y **guarda** `mes_pago`/`ano_pago` de los lotes
  visibles sin período, leyendo primero `RegistroImportado` y luego el archivo en storage. La API debe conservarlo.
- AJAX histórico: solo `busqueda` (sin `filters`), JSON `{html, pagination_html, count, current_page, total_pages,
  has_previous, has_next}`; se conserva intacto para consumidores existentes.

Detalle:
- `get_object_or_404` del lote en `dispatch` (antes del método). Errores del lote ordenados por `fila`, 20 por página;
  `busqueda` numérica filtra `fila` exacta, si no `mensaje__icontains` (`views.py:411-421`).
- Contadores: «Registros Válidos» (`ExitoImportacion` del lote), «Registros con Errores» (`ErroresImportacion`, cuenta mensajes,
  no filas), «Con Acreditación» (expedientes importados con `fecha_acreditacion`). `expedientes_importados_count` y `volver_url`
  están en contexto pero el template no los usa.
- Tabla «Archivo» (`__str__` del lote: «Archivo importado … por … el …»), «Fila», «Error». Vacío: «No hay errores registrados para
  este archivo.». Barra AJAX «Buscar Errores», placeholder «Buscar por Fila», ayuda «Ingresar una Fila.».

### Acciones y efectos

- Descarga: `FileResponse(batch.archivo.open("rb"), as_attachment=True, filename=<basename>)`; lote inexistente → 404;
  archivo ausente en storage: excepción no capturada (no caracterizado). Content-type por nombre de archivo (inferido por Django).
- Sin otras escrituras salvo el completado de períodos.

### Exportaciones

La descarga del archivo original se conserva como GET nativo enlazado desde React; no pasa por JSON.

### API web del runtime

Archivos propuestos: `src/backends/comedores/importarexpediente/web_api_urls.py`, `web_api_views.py`, `web_api_serializers.py`.

| Método | Path | Respuesta |
| --- | --- | --- |
| GET | `/api/web/comedores/importarexpedientes/?filters=&busqueda=&page=` | 200 `{count, page, pages, page_size: 10, filters_config, results[], messages[]}`; 404 página |
| GET | `/api/web/comedores/importarexpedientes/<id>/?busqueda=&page=` | 200 `{batch{...}, counts{validos, errores, con_acreditacion}, can_update_acreditacion, errors_page{count, page, pages, page_size: 20, results[]}, messages[]}`; 404 |

- Ambos con `importarexpediente.view_archivosimportados` (403 sin él), `WebGatePermission`, anónimo 401.
- Listado: mismo queryset, mismo `IMPORTAREXPEDIENTE_ADVANCED_FILTER.filter_queryset` y misma `busqueda`; ejecuta
  `_completar_periodos_faltantes` sobre la página. `results[]`: `{id, numero_expediente_pago, archivo, periodo_pago, usuario,
  fecha_subida_display, count_exitos, count_errores, importacion_completada, detail_url, download_url}`; `fecha_subida_display`
  con el formato localizado que hoy renderiza el template (`DATETIME_FORMAT` y zona activa).
- Detalle: `batch` con `id`, `archivo`, `str`, `importacion_completada`; `can_update_acreditacion` = condición del template;
  `results[]` `{fila, mensaje, archivo_label}`. La búsqueda de errores reemplaza al AJAX en React; el AJAX nativo sigue vivo.
- `messages[]`: mensajes Django pendientes de la sesión (`{level, message}`), consumidos como lo haría el template, para mostrar
  resultados de EX02.01 en destino.

### Módulo React

`src/frontends/apps/sisoc/src/routes/importarExpedientes.tsx` + `importarExpedientes.test.tsx`, en `ROUTES` antes de
`businessRoute`. Paths que posee en esta entrega: `/importarexpedientes/listar` (sin barra final) y `/importarexpedientes/<n>/`.
No posee `/importarexpedientes/ajax/`, `/<n>/ajax/` ni `/<n>/descargar/`. Volver nativo: breadcrumb «Importar Expedientes»
→ `/importarexpedientes/listar` en el detalle; el listado no tiene Volver.

### Criterios de aceptación

- Listado: pestaña «Importar Expedientes», breadcrumb «Importar Expedientes» › «Listar», botón «Importar Nuevo Archivo»,
  barra «Buscar Expedientes de Pago», columnas y textos literales de arriba (incluidos «Sin informacion» e «Importacion Completada»
  sin tilde, como en fuente), vacío «No hay expedientes disponibles.», paginación «Volver»/«Continuar».
- Detalle: pestaña «Importar Expedientes - Detalle», breadcrumb «Importar Expedientes» › «Detalle», tres tarjetas de contadores,
  barra «Buscar Errores», tabla «Archivo», «Fila», «Error», vacío «No hay errores registrados para este archivo.».
- Orden de Tab: acciones de cabecera, barra de búsqueda/filtros, tabla, paginación. Regla visual S13 para listado vacío, con
  filas, filtrado y página 2; detalle con y sin errores, completado y no completado, con y sin permiso de fechas.

### Casos de prueba

- Backend: permiso 200 / sin permiso 403 / anónimo 401; lote ajeno visible (paridad); cada operador de filtro y `busqueda`;
  página inválida 404; período completado y persistido en GET; búsqueda de errores numérica y textual; lote inexistente 404;
  `can_update_acreditacion` según bandera y permisos. Reusar fixtures de `importarexpediente/tests/conftest.py`.
- Frontend (vitest): listado, filtros que serializan `filters` igual que la barra nativa, detalle, paginación, 403/401.
- Diferencial: `importarexpedientes_ajax`, `importarexpediente_detail_ajax` y descarga devuelven exactamente lo mismo que en la base
  (`tests/test_ajax_endpoints.py:100-112,169-200`).
- Visual: según criterios.

### Riesgos

- No existe en el frontend un componente de filtros combinables equivalente a `components/search_bar.html` en `filters_mode`;
  crearlo es setup compartido (lo usan otros listados). Sin él, EX02.02 no alcanza paridad.
- GET con escritura (períodos): una vista React que monte dos veces el listado repetirá el completado; es idempotente por campo.

## EX02.01 Preparación, validación e importación

### Rutas nativas

| Método | URL | Nombre | Vista | Template |
| --- | --- | --- | --- | --- |
| GET, POST | `/importarexpedientes/upload` | `upload` | `views.py:134-314` `ImportExpedientesView` | `upload.html:1-64`, `static/custom/js/importarexpedienteupload.js:1-11` |
| POST (GET 405) | `/importarexpedientes/<id>/importar_datos/` | `importar_datos` | `views.py:575-718` `ImportDatosView` | — (botón en detalle) |
| POST (GET 405) | `/importarexpedientes/<id>/borrar_datos_importados/` | `borrar_datos_importados` | `views.py:721-759` `BorrarDatosImportadosView` | — (botón en detalle) |
| GET, POST | `/importarexpedientes/<id>/fechas-acreditacion/` | `importar_fechas_acreditacion` | `views.py:502-572` `ImportarFechasAcreditacionView` | `importarexpediente_acreditacion_upload.html:1-56` |

`urls.py:16,52-71`. Los `template_name` de `ImportDatosView` y `BorrarDatosImportadosView` no existen como pantallas: no derivar
páginas de ellos (nota del catálogo).

### Acceso

- `upload`, `importar_datos`, `borrar_datos_importados`: solo `LoginRequiredMixin` (anónimo → 302 al login); **sin permiso**.
  Cualquier usuario autenticado puede subir, importar o borrar datos de cualquier lote.
- `importar_fechas_acreditacion`: `permissions_any_required` sobre `importarexpediente.change_archivosimportados`,
  `expedientespagos.change_expedientepago` (anónimo → 403), en GET y POST; el GET funciona aunque el lote no esté completo
  (el template del detalle oculta el enlace).
- Sin scope de lote por usuario. Conservar estas asimetrías.

### Datos y reglas

Formularios (`importarexpediente/forms.py:7-36`):
- `file`: «Archivo CSV o XLSX», extensiones `csv`, `xlsx`, `accept=".csv,.xlsx"`; tamaño máximo `FILE_UPLOAD_MAX_MEMORY_SIZE`
  (no definido en `config/settings.py`, por lo que rige el valor por defecto de Django, 2,5 MB; el fallback de 10 MB no se usa)
  con «El archivo supera el tamaño permitido.».
- `CSVUploadForm`: `delimiter` «Delimitador» con «Coma (,)» / «Punto y coma (;)», inicial `,`; `has_header` «Incluye cabecera»,
  opcional, inicial verdadero. `AcreditacionUploadForm`: solo `file`.

Parseo (`services.py:130-205`): CSV UTF-8-sig con fallback latin-1; el delimitador real se detecta por la primera línea (`;` si
aparece), no por el elegido; XLSX con openpyxl, filas vacías salteadas. Sin cabecera → «Archivo sin cabecera no soportado por
defecto.»; vacío → «El archivo está vacío.». Cabeceras mapeadas por `HEADER_MAP` (`services.py:39-78`), `id` → `comedor_id`.
Validación por fila `expediente_pago_from_row` (`services.py:400-454`): numéricos con mensaje
`Error en validación columna "<etiqueta>": Advertencia "El campo debe ser numérico"`, `mes_convenio` fuera de 1-6 →
`Advertencia "Debe ser un número entre 1 y 6"`; fechas `%Y-%m-%d`, `%d/%m/%Y`, `%d-%m-%Y` o ISO (inválida → `None` sin error).

### Acciones y efectos

Subida y validación (`views.py:147-314`), sin escribir `ExpedientePago`:
1. Form inválido → cada error como `messages.error` y redirect a `upload`.
2. Parseo fallido → mensaje de la excepción o «No se pudo leer el archivo: {e}» y redirect a `upload`.
3. Número de expediente del archivo ya cargado (en `ExpedientePago.expediente_pago` o en otro `ArchivosImportados`, sin
   distinguir mayúsculas) → «No se puede adjuntar el archivo ya que el expediente de pago se encuentra cargado anteriormente» y
   redirect a `upload`, sin guardar archivo.
4. Guarda `ArchivosImportados` y el archivo en storage `importados/`; error → «No se pudo guardar el archivo: {e}».
5. Delimitador distinto → advertencia «El delimitador seleccionado fue '{x}', pero el archivo parece usar '{y}'. Se usará '{y}'.»
   y actualiza `delimiter`.
6. En `transaction.atomic()`, por fila: duplicado de otro expediente → `ErroresImportacion`; errores específicos → un
   `ErroresImportacion` por mensaje, mensaje visible «Fila {n} (Excel): {msg}»; si no, `full_clean()` y `ExitoImportacion`
   «Fila válida». Excepción → `friendly_error_message`. Solo los primeros 20 errores se muestran (`MAX_ERROR_MESSAGES`), todos
   se persisten.
7. Guarda `count_errores`/`count_exitos`; mensaje «Validación parcial: {ok} filas válidas, {err} errores.» o «{ok} filas
   válidas.»; redirect a `importarexpedientes_list`.
El JS nativo deshabilita el botón y muestra «Procesando…» al enviar (anti doble envío en cliente).

Importación (`views.py:584-715`):
- Lote con `get_object_or_404`; lee y parsea el archivo guardado (`has_header=True`); errores → mensaje y redirect al listado.
- En `transaction.atomic()` con `select_for_update` del lote: si `importacion_completada` → «Este archivo ya fue importado.
  Primero borre los datos importados para reintentar.» y redirect (guarda de doble envío). Por fila válida:
  `ensure_import_required_defaults` (ceros), `full_clean`, `save` de `ExpedientePago`, `ExitoImportacion` reutilizado o creado
  «Importado» y `RegistroImportado`. Errores de fila: crea `ErroresImportacion` solo para errores específicos; las excepciones
  solo se muestran.
- Si hubo al menos una fila importada: `importacion_completada = True` y `aplicar_estados_por_lote(batch, request.user)`
  (`services.py:626-728`): para comedores de programa 2 presentes en el lote registra estado (Activo / En ejecución, con detalle
  «En plazo de renovación» si `mes_convenio` 4-6) y `mes_ejecucion = mes_convenio`; para **todos** los comedores de programa 2
  ausentes calcula ausencias consecutivas contra lotes previos y registra «Inactivo / Baja / No renovación (Comedor)» con
  `mes_ejecucion = None` (si ya inactivo o 3+ ausencias) o «Activo / En proceso - Renovación» con `mes_ejecucion = -ausencias`.
  Usa `registrar_cambio_estado` (historial de estados).
- Excepción del bloque → «No se pudo completar la importación: {e}». Final: «Importación finalizada: {n} registros importados,
  {e} errores.» o «Importación completada: {n} registros importados. Estados actualizados: {m}.». Redirect al listado.

Borrado de datos importados (`views.py:729-756`), acción destructiva separada:
- En `transaction.atomic()`: borra `RegistroImportado` del lote y hace **borrado físico** (`all_objects...hard_delete()`) de los
  `ExpedientePago` vinculados, incluidos los dados de baja lógica. Fuera de la transacción: `importacion_completada = False`
  (error → «No se pudo resetear importacion_completada: {e}»).
- No borra el archivo, `ArchivosImportados`, `ErroresImportacion` ni `ExitoImportacion`, y **no revierte** estados de comedor
  ni `mes_ejecucion` aplicados por la importación. Mensaje «Borrado completado: {r} registros y {x} expedientes eliminados.»;
  redirect al listado. Repetirlo borra cero.
- Confirmación nativa en cliente: `window.confirm` con «¿Confirmar borrado de datos importados del lote?» (`base.js:323-329`).

Fechas de acreditación (`views.py:526-572`, `services.py:293-397`):
- Requiere lote completado («Primero se debe completar la importación del lote.»), columnas «ID» y «Fecha de acreditación»
  («El archivo debe incluir las columnas: …»), ID numérico («Fila {n}: ID debe ser numérico.»), fecha válida («Fila {n}: Fecha de
  acreditación debe tener formato DD/MM/AAAA.»), sin repetidos con fechas distintas, al menos una fecha («No se encontraron fechas
  de acreditación para procesar.»), una única fecha («El archivo debe informar una única fecha de acreditación para el lote.»),
  IDs pertenecientes al lote («Los siguientes ID no corresponden a expedientes importados en este lote: …»).
- `UPDATE` de `fecha_acreditacion` en una transacción con `select_for_update` solo para expedientes del lote de esos comedores.
- Éxito: «Fechas de acreditación actualizadas: {x} expedientes de {c} comedores.» y redirect al listado. Errores: mensajes
  (hasta 20 más «Se omitieron {n} errores adicionales.») y **re-render 200** del formulario; excepción inesperada →
  «No se pudieron actualizar las fechas de acreditación.» con log. Lectura fallida → «No se pudo leer el archivo.».

### Exportaciones

No aplica (la descarga del archivo es EX02.02).

### API web del runtime

| Método | Path | Request | Respuestas |
| --- | --- | --- | --- |
| GET | `/api/web/comedores/importarexpedientes/subir/` | — | 200 `{fields[], initial, messages[]}` |
| POST | ídem | multipart `file`, `delimiter`, `has_header` | 200 `{ok, messages[], redirect}`; 400 `{ok: false, messages[]}`; 409 duplicado |
| POST | `/api/web/comedores/importarexpedientes/<id>/importar/` | vacío | 200 `{ok, messages[], redirect}`; 409 ya importado; 400 archivo ilegible; 500 `{messages[], redirect}`; 404 |
| POST | `/api/web/comedores/importarexpedientes/<id>/borrar-datos/` | vacío | 200 `{ok, messages[], redirect}`; 404 |
| GET | `/api/web/comedores/importarexpedientes/<id>/fechas-acreditacion/` | — | 200 `{batch, fields[], messages[]}`; 403; 404 |
| POST | ídem | multipart `file` | 200 `{ok, messages[], redirect}`; 400 `{ok: false, messages[]}`; 403; 404 |

- Permisos: subir, importar y borrar con autenticación solamente (paridad); fechas con los dos códigos ANY. Anónimo 401 (G1).
- Reutilización: se extraen los cuerpos de `ImportExpedientesView.form_valid`, `ImportDatosView.post` y
  `BorrarDatosImportadosView.post` a funciones de `importarexpediente/services.py` que devuelven `(nivel, mensaje)` ordenados y
  el destino; la vista nativa y la API los llaman y la nativa los vuelca a `messages` y redirige igual que hoy. Fechas reutiliza
  `actualizar_fechas_acreditacion_por_lote` y la misma composición de mensajes. Mismos forms (`CSVUploadForm`,
  `AcreditacionUploadForm`).
- `redirect` siempre `/importarexpedientes/listar` en éxitos y resultados definitivos de importar/borrar; los `messages[]` se
  devuelven en la respuesta (no quedan en sesión) y React los muestra en destino.
- Mutaciones: CSRF, sin reintento automático, 504 `uncertain: true` se presenta sin reenviar con «No se pudo confirmar el
  resultado. Revise el listado de lotes antes de volver a intentar.»; React deshabilita el botón mientras espera (paridad con
  «Procesando…»).
- Riesgo de 60 s: `aplicar_estados_por_lote` recorre todos los comedores del programa 2 con un `registrar_cambio_estado` por
  comedor; su duración no se midió. Hoy la ruta nativa ya pasa por el proxy con 25 s de lectura, así que la API (60 s) no reduce
  margen. Guardas de repetición existentes: importar está protegido por `select_for_update` + `importacion_completada`; borrar es
  idempotente; subir rechaza el mismo número de expediente ya registrado en otro lote. No existe job asíncrono para este circuito;
  no se crea uno en M2.

### Módulo React

Mismo módulo `routes/importarExpedientes.tsx`. Paths adicionales: `/importarexpedientes/upload` y
`/importarexpedientes/<n>/fechas-acreditacion/`. Las acciones «Completar Importación» y «Eliminar Archivo» viven en la pantalla
de detalle (EX02.02) como botones separados, cada uno con su confirmación literal; no se agrupan con ningún control de limpieza
de filtros o formulario. Volver nativo: breadcrumb «Importar Expedientes» → `/importarexpedientes/listar` en subida y fechas.

### Criterios de aceptación

- Subida: pestaña y título de tarjeta «Importar Expedientes desde CSV o XLSX», breadcrumb «Importar Expedientes» › «Importar Archivo»,
  campos «Archivo CSV o XLSX», «Delimitador», «Incluye cabecera», botón «Importar» y estado «Procesando…»; mensajes de error con
  alerta roja e ícono, otros con su nivel.
- Detalle: «Completar Importación» con confirmación «¿Confirmar importación del lote?»; «Eliminar Archivo» (rojo) con
  «¿Confirmar borrado de datos importados del lote?»; «Actualizar fechas de acreditación» solo con lote completo y permiso.
- Fechas: pestaña y título «Actualizar fechas de acreditación», breadcrumb «Importar Expedientes» › «Fechas de acreditación»,
  texto informativo literal de `importarexpediente_acreditacion_upload.html:39-45`, botón «Actualizar fechas».
- Todos los mensajes de «Acciones y efectos» aparecen con el mismo texto y nivel en el mismo destino.
- Orden de Tab y regla visual S13 para subida vacía, subida con errores, fechas con errores y cada resultado en el listado.

### Casos de prueba

- Backend (sobre fixtures de `importarexpediente/tests/conftest.py` y casos de `tests/test_import_flow.py`): anónimo 401;
  autenticado sin permisos puede subir, importar y borrar (paridad); fechas 403 sin permiso; extensión y tamaño inválidos;
  vacío y sin cabecera; duplicado 409 sin archivo guardado; filas con errores (persistidos todos, mostrados 20); importación crea
  expedientes, registros, bandera y estados; segunda importación 409 sin efectos; borrado físico y bandera en falso, estados sin
  revertir; borrado repetido borra cero; fechas con cada mensaje de validación y con IDs fuera del lote.
- Frontend (vitest): envío único, confirmaciones, `uncertain` sin reenvío, mensajes en destino, botón de fechas condicionado.
- Diferencial: las cuatro rutas nativas (incluido GET 405 de importar y borrar) devuelven igual que en la base después de extraer
  los servicios; comparar mensajes, redirects y filas creadas con el mismo archivo sintético.
- Visual: según criterios. Ningún caso usa datos reales.

### Riesgos

- Rutas destructivas sin permiso (subir, importar, borrar): exposición actual que se conserva.
- Excepción de base de datos dentro del bucle de importación sin savepoint puede dejar la transacción inválida y revertirse al
  salir del bloque mientras el mensaje informa filas importadas (ver Incertidumbres).
- La extracción a servicios toca las vistas nativas: el diferencial es obligatorio.
- Borrar no deshace estados de comedores: React no debe sugerir que «Eliminar Archivo» restaura la situación previa.

## Decisiones técnicas tomadas

1. **API JSON para todas las pantallas y mutaciones, con descargas nativas.** Fundamento: patrón ya implementado en Insumos y
   Usuarios; la única descarga binaria (`descargar_archivo_importado`) queda como GET nativo.
2. **Extraer a servicios la lógica que hoy vive en las vistas de importación.** El brief exige no reimplementar; la lógica de
   subir, importar y borrar está en las vistas, así que una extracción pequeña con mensajes como datos permite que vista nativa y
   API compartan el mismo código. Requiere diferencial.
3. **Importar y borrar por API pese al riesgo de duración.** La ruta nativa ya está limitada a 25 s por el proxy; la API con
   60 s no empeora y la guarda `select_for_update` + bandera evita duplicar efectos ante un reintento manual tras `uncertain`.
   No se introduce un job asíncrono porque no existe y cambiaría el circuito.
4. **Lista blanca de campos en la API de expedientes.** Solo los 23 campos renderizados llegan al form; `deleted_at` y
   `deleted_by` no se aceptan. Para cualquier envío originado en la UI el resultado es idéntico al nativo.
5. **Comedor inexistente en alta por API → 404 JSON** en lugar del 500 nativo. Es una respuesta de transporte de la ruta nueva;
   la vista nativa no cambia.
6. **Alta inválida conserva la presentación nativa** (form vacío sin errores) por la decisión del usuario S13 «mantene la paridad»;
   la API igual devuelve `errors` para tests y para una corrección futura separada.
7. **Mensajes Django como `messages[]` en JSON**, consumidos por la pantalla destino, para mantener texto, nivel y lugar.
8. **React en `ROUTES` con paths nativos** (patrón `userImportRoute`), no en `SHELL_ROUTES` (reservado hoy a `/v2/sisoc/insumos/`).

## Puntos estrictamente humanos

1. **Permisos y scope de rutas hoy abiertas** (lectura de expedientes sin permiso ni scope; subir, importar y borrar datos importados
   solo con login; escritura de expedientes con permisos de lectura). Es política de seguridad y producto.
   Opciones: (a) mantener paridad en M2 y abrir un issue de endurecimiento aparte; (b) endurecer durante M2 con permisos nuevos
   o existentes (`add_`/`change_`/`delete_`). Recomendación: (a), que es el criterio vigente S13; no bloquea ninguna entrega.

## Incertidumbres

- [sin ejecutar] Alta de expediente: `CreateView.form_valid` llama `form.save()` después de `crear_expediente_pago`; por fuente
  crearía un segundo registro con `comedor` nulo, invisible en el listado del comedor. Caracterizar con un test antes de
  implementar EX01.02; si se confirma, la API reproduce la conducta (paridad) y la corrección va en un issue aparte.
- [sin ejecutar] Inclusión real de `deleted_at`/`deleted_by` en `ExpedientePagoForm` (derivado de `fields="__all__"` y campos
  editables del mixin).
- [sin ejecutar] Comportamiento de la ficha y de las rutas cuando `comedor` es nulo (`SET_NULL`).
- [sin ejecutar] Rollback silencioso del bucle de importación ante error de base de datos sin savepoint.
- [no confirmado] Formato exacto de `fecha_subida` renderizado (depende de `DATETIME_FORMAT`, idioma y zona).
- [no confirmado] Content-type de la descarga para `.xlsx`/`.csv` y comportamiento con archivo ausente en storage.
- [no confirmado] Duración de `aplicar_estados_por_lote` con volumen productivo.
- [no confirmado] Alcance de receptores genéricos de `post_soft_delete` (`comedores/cache_signals.py:27`) sobre `ExpedientePago`
  y registro en auditoría.
- [no confirmado] Si el endpoint `column_preferences` del core es invocable desde React tal como lo usa el modal nativo.
- La entrada que sirve el SPA en paths nativos de verticales y el componente de filtros combinables son setup compartido no
  existente en HEAD.

## Fuente

Leído en HEAD 4ea95bcbe:
- `src/backends/comedores/expedientespagos/urls.py:1-58`, `views.py:1-275`, `forms.py:1-110`, `services.py:1-162`, `models.py:1-118`,
  `templates/expedientespagos_list.html:1-25`, `expedientespagos_detail.html:1-194`, `expedientespagos_form.html:1-57`,
  `expedientespagos_confirm_delete.html:1-19`.
- `src/backends/comedores/importarexpediente/urls.py:1-72`, `views.py:1-759`, `forms.py:1-36`, `models.py:1-117`,
  `services.py:1-746`, `filter_config.py:1-103`, `templates/upload.html:1-64`, `importarexpediente_list.html:1-89`,
  `importarexpediente_detail.html:1-117`, `importarexpediente_acreditacion_upload.html:1-56`,
  `partials/importarexpediente_list_rows.html:1-51`, `partials/importarexpediente_detail_rows.html:1-22`,
  `static/custom/js/importarexpedienteupload.js:1-11`, `tests/test_ajax_endpoints.py:200-240` y nombres de tests de `tests/`.
- `src/backends/kernel/core/soft_delete/view_helpers.py:1-118`, `base.py:1-140`, `cascade.py` (relaciones `CASCADE`),
  `kernel/core/decorators.py:1-67`, `kernel/core/services/column_preferences/builders.py:1-176`,
  `kernel/core/services/advanced_filters/engine.py:39-136`, `kernel/core/urls.py:58-66`, `kernel/core/web_gate.py:300-328`,
  `kernel/templates/components/delete_confirm.html:1-95`, `data_table.html:1-36,179-181`, `form_buttons.html:1-50`,
  `search_bar.html:17-136`, `kernel/static/custom/js/base.js:318-337`, `kernel/templates/includes/sidebar/opciones.html:370-386`.
- `src/backends/comedores/comedores_runtime/urls.py:1-35`, `config/backends.json:239-300`, `config/url_registry.json:845-860,2225-2250,3712-3722`,
  `config/settings.py:220-242,276`, `docker/django/entrypoint.py:320-329`.
- `src/backends/comedores/comedores/views/comedor.py:1003-1045`, `templates/comedor/comedor_mes_ejecucion_card.html:1-38`,
  `comedor_detail.html:1438-1450`, `services/comedor_service/impl.py:596-598`,
  `acompanamientos/templates/acompañamiento_detail.html:20-45`, `acompanamientos/urls.py:1-25`,
  `admisiones/views/web_views.py:424-458`, `admisiones/templates/admisiones/admisiones_detalle.html:624-660`,
  `sisoc_core/usuarios/web_navigation.py:185-200`.
- Patrón web: `src/backends/sisoc_core/insumos/web_api_urls.py`, `web_api_views.py`, `src/backends/sisoc_core/usuarios/web_api_urls.py`,
  `src/frontends/apps/sisoc/src/routes/index.ts`, `types.ts`, `userImport.tsx`, `categorias.tsx`.
- Decisión G1: `docs/registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md`. Desde disco (no versionados):
  `docs/plans/2026-T4/2026-10-27-2785-entregas-por-flujo.json` (flujos EX01, EX02, perfiles) y
  `docs/plans/2026-T4/2026-10-28-2785-comedores-legajo-base-m2.md`.
