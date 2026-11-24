# AC01: seguimiento de acompañamiento e hitos (contrato M2 ejecutable)

| Dato | Valor |
|---|---|
| Fecha | 2026-11-10 |
| Base contrastada | HEAD `4ea95bcbe` (el código de `src/backends/comedores/` del worktree coincide con HEAD) |
| Runtime dueño | `comedores` (app `acompanamientos`), servicio `backend_comedores` |
| Transporte | G1 v1 aprobado: [protocolo G1 v1](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md) |
| Entregas | AC01.01 seguimiento e hitos [L], AC01.02 acciones autorizadas y evidencia [W] |

Confirmación del riesgo del catálogo («acciones de ficha pueden vivir en POST de
detalle»): la ficha de acompañamiento es un `DetailView` sin `post` (un POST a la
URL de detalle da 405). La única acción es **restaurar hito**, que tiene URL propia.
No hay otras escrituras en `acompanamientos/urls.py`.

## 1. Rutas nativas

Montaje: `comedores_runtime/urls.py:13` incluye `acompanamientos.urls` bajo
`acompanamientos/` (confirmado en `src/backends/config/url_registry.json`).

| URL nativa exacta | Nombre | Métodos | Guarda | Vista | Template | Entrega |
|---|---|---|---|---|---|---|
| `/acompanamientos/acompanamiento/` | `lista_comedores_acompanamiento` | GET | ANY `acompanamientos.view_informacionrelevante` + login | `ComedoresAcompanamientoListView` (`views.py:250–308`, `ensure_csrf_cookie`) | `lista_comedores.html` | AC01.01 |
| `/acompanamientos/acompanamiento/<comedor_id>/detalle/` | `detalle_acompanamiento` | GET (`?admision_id=`) | ANY `acompanamientos.view_informacionrelevante` + login | `AcompanamientoDetailView` (`views.py:87–247`) | `acompañamiento_detail.html` | AC01.01 |
| `/acompanamientos/acompanamiento/exportar/` | `lista_comedores_acompanamiento_exportar` | GET | ANY `auth.role_exportar_a_csv` + login + `CSVExportMixin.check_export_permission` | `AcompanamientoExportView` (`views_export.py:8–77`) | CSV | AC01.01 |
| `/acompanamientos/acompanamiento/ajax/` | `comedores_acompanamiento_ajax` | GET | ANY `acompanamientos.view_informacionrelevante` + login | `comedores_acompanamiento_ajax` (`views.py:311–361`) | JSON con HTML | ver §4.4 |
| `/acompanamientos/comedor/<comedor_id>/restaurar-hito/` | `restaurar_hito` | POST | ALL `auth.role_tecnico_comedor` y `acompanamientos.change_hitos` + login + `require_POST` | `restaurar_hito` (`views.py:48–84`) | redirección | AC01.02 |

Guardas en `acompanamientos/urls.py:7–43` con `core.decorators`
(`permissions_any_required`, `permissions_all_required`, levantan
`PermissionDenied`).

Entradas desde otras pantallas (no se cambian): sidebar
`kernel/templates/includes/sidebar/opciones.html:371`; volver desde
`expedientespagos_list.html:8`, `rendicioncuentasmensual_list.html:11` e
`informe_tecnico_complementario_detalle.html:11,23` (AD02/AD03).

## 2. Permisos, grupos y alcance

- Grupo sembrado «Tecnico Comedor» tiene `acompanamientos.view_informacionrelevante`,
  `acompanamientos.change_hitos` y `auth.role_tecnico_comedor`
  (`kernel/users/bootstrap/groups_seed.py:17–45`). Otros grupos con
  `view_informacionrelevante` leen pero no restauran.
- **Alcance del listado** (`acompanamiento_service.py:565–676`): comedores con al
  menos una admisión `enviado_acompaniamiento=True` y `activa=True`. Superusuario
  ve todos; coordinador, los de sus duplas; técnico o abogado, los de duplas donde
  es técnico o abogado; cualquier otro usuario con el permiso ve todos. **No aplica
  alcance territorial.**
- **Alcance del detalle y de restaurar**: `ComedorService.get_scoped_comedor_queryset`
  / `get_scoped_comedor_or_404` (`comedores/services/comedor_service/impl.py:536–566,
  877–887`): además de coordinador y dupla aplica `apply_territorial_scope` a
  usuarios territoriales. Comedor fuera de alcance: 404.
- Asimetría conservada (paridad): un usuario territorial puede ver en el listado o
  en el CSV un comedor cuyo detalle le da 404. Ver R2.
- Admisión: el detalle solo muestra admisiones del mismo comedor con
  `enviado_acompaniamiento=True` (`obtener_datos_admision`, :451–499); un
  `admision_id` ajeno al comedor no muestra datos de otro comedor.
- El botón «Restaurar» se habilita si el hito está completado y el usuario es
  superusuario o tiene `auth.role_tecnico_comedor` (`views.py:101–104`); el POST
  exige además `acompanamientos.change_hitos`. La API usa la guarda del POST, y la
  bandera de capacidad que devuelve se calcula como la del template.

## 3. Origen de los datos (dependencias de circuito)

- El acompañamiento se crea en AD03: `_procesar_post_disponibilizar_acomp`
  (`admisiones/services/admisiones_service/impl.py:1142–1150`) y
  `comenzar_acompanamiento` (:2459–2473) llaman
  `AcompanamientoService.importar_datos_desde_admision` (:358–433), que crea
  `Acompanamiento` (con `nro_convenio`), `InformacionRelevante`, `Prestacion` y
  `Hitos` vacíos. También lo hace la acción de admin `admisiones/admin.py:60`.
- Los hitos se marcan en `True` desde intervenciones (CO02):
  `crear_hitos` (:60–132) mapea `HitosIntervenciones` (intervención/subintervención
  → `verbose_name` del hito) y `_verificar_hito_capacitacion_fch` (:161–207) exige
  los 8 subtipos de «Asistencia a Capacitación Formando Capital Humano».
- La ficha de comedor (CO07, `comedor_detalle`) es el destino del botón volver.

AC01 no modifica ninguno de esos productores.

## 4. AC01.01 Seguimiento e hitos

### 4.1 Listado

- Paginación 10 (`paginate_by`), `page`.
- Orden: `ordering=nombre|-nombre` (único permitido, encabezado ordenable
  «Nombre»); por defecto `-id`; con orden pedido agrega desempate `pk`
  (`kernel/core/services/list_ordering.py:6–19`).
- Búsqueda `busqueda` (en minúsculas, `icontains`) sobre nombre, provincia, tipo de
  comedor, calle, número y nombre, apellido o celular del referente.
- Filtros avanzados (`filters`, motor `AdvancedFilterEngine`) definidos en
  `services/filter_config.py:10–53`: «Nombre del comedor» (texto), «ID de comedor»
  (número), «Tipo de admisión», «Organización del comedor», «N° de expediente»,
  «Provincia», «Equipo técnico», «Estado de la admisión», «Fecha de última
  modificación»; operadores texto `contains, ncontains, eq, ne, empty`, número y
  fecha `eq, ne, gt, lt, empty`, choice `eq, ne`. Los valores de admisión salen de
  la admisión activa enviada más reciente (anotaciones por subquery).
- Filtros favoritos: sección `SeccionesFiltrosFavoritos.ACOMPANAMIENTOS`.
  Preferencias de columnas: clave `acompanamientos_comedores_list`.
- Columnas: ID, Nombre, Organización, N° Expediente, Provincia, Dupla
  (`str(comedor.dupla)`), Estado (`get_estado_admision_display`), Última
  Modificación (`d/m/Y`); faltante «-». Acción «Ver Acompañamiento» →
  `/acompanamientos/acompanamiento/<id>/detalle/?admision_id=<id o vacío>`
  (`preparar_datos_tabla_comedores`, :678–761).
- Título «Comedores en Acompañamiento»; vacío «No se encontraron comedores.»; barra
  `components/search_bar.html` sin botón de alta y con exportar.

### 4.2 Detalle (ficha de acompañamiento)

- Selector de convenios: admisiones del comedor con acompañamiento, orden `-id`
  (`obtener_admisiones_para_selector`, :242–266). Botón con `nro_convenio` o
  «Admisión #<id>», insignia «Cerrada» si no está activa, insignia
  «Múltiples convenios activos» si hay más de una activa.
- Resolución de la admisión mostrada (:189–205): `?admision_id` numérico del
  comedor; si no hay o no corresponde, la activa enviada más reciente; si tampoco,
  la primera del selector.
- Botones: «Intervenciones» (`comedor_intervencion_ver`, con `?admision_id`),
  «Expedientes de Pagos», «Seguimiento Mensual», y «Informe Técnico Complementario»
  (`informe_complementario_ver ...?origen=acompanamiento`) solo para técnico o
  superusuario y si existe informe `finalizado`.
- «Información Relevante» (fuente: informe técnico efectivo,
  `ComedorService.get_informe_tecnico_finalizado_efectivo`): Número de Convenio (si
  hay), Número de Expediente (`expediente_nro`), Número de Disposición, IF de
  Relevamiento, Vencimiento de Mandato (`d/m/Y` o «—»), Código de Proyecto. Vacío:
  «No hay información relevante disponible» / «No hay información relevante cargada
  para este comedor.».
- «Prestaciones por Día»: tabla tipo × lunes…domingo (`aprobadas_<tipo>_<dia>`,
  `None` → «Sin información») y «Resumen Semanal». Vacío: «No hay prestaciones
  disponibles» / «No hay información de prestaciones cargada para este comedor.».
- «Listado de Hitos»: 23 filas fijas en este orden y con estas descripciones
  (`views.py:115–187`): Retiro de Tarjeta; Habilitación de Tarjeta; Alta de Usuario
  en Plataforma; Capacitación Sincrónica Realizada; Capacitación Formando Capital
  Humano Realizada; Notificación de primera acreditación; Notificación de
  acreditación mes 2…6; Nómina entregada inicial; Nómina Alta/baja mes 2…6;
  Certificado mensual de prestaciones mes: 1…6. Columnas: Descripción del Hito,
  Estado («Completado» / «Pendiente»), Fecha Completado (fecha de la intervención
  más reciente que lo completó, `d/m/Y`, o «—»), Acciones («Restaurar»).
- Contadores «Completados», «Pendientes», «Total» (calculados en cliente en el
  nativo; en React se calculan del mismo conjunto de filas).
- Sin hitos: «No hay información de hitos disponible» / «No hay hitos cargados
  para este comedor.».
- Volver: botón a `comedor_detalle` (CO07). Breadcrumb: nombre del comedor →
  «Acompañamiento».

### 4.3 Exportación CSV

- Archivo: `exportacion_acompanamientos_<YYYYmmdd_HHMM>.csv`
  (`CSVExportMixin.get_export_filename`, `kernel/core/mixins.py:34–39`), separador
  `;`, BOM UTF-8, streaming.
- Mismo queryset que el listado (filtros avanzados, búsqueda y orden; cubierto por
  `tests/test_acompanamientos_list_filters_db.py:85–117`), sin paginar.
- Columnas según preferencias del usuario para `acompanamientos_comedores_list`; sin
  preferencias, todas: ID, Nombre, Organización, N° Expediente, Provincia, Dupla,
  Estado, Última Modificación (`YYYY-mm-dd HH:MM:SS`).
- Bug B1: Organización, Provincia y Dupla salen vacías (ver §8).
- React no genera el CSV: el botón conserva el GET nativo protegido con la consulta
  actual.

### 4.4 Endpoint AJAX nativo

`comedores_acompanamiento_ajax` devuelve filas HTML (`partials/comedor_rows.html`,
solo nombre y botón) y paginador, sin filtros avanzados. No se encontró ningún
template ni script que lo llame. React no lo usa; queda sin cambios.

## 5. AC01.02 Acciones autorizadas y evidencia: restaurar hito

| Paso | Comportamiento nativo |
|---|---|
| Entrada | POST `campo`; `admision_id` de POST, o de GET, o del `admision_id` del Referer |
| Formulario nativo | El HTML no trae `admision_id`; el script del template lo agrega como hidden cuando hay admisión activa (`acompañamiento_detail.html`, script final) |
| Alcance | `get_scoped_comedor_or_404` (404 fuera de alcance) |
| Sin hitos | Error «No se encontraron hitos para el convenio seleccionado.» |
| Campo válido | `hasattr(hito, campo)` y no `id`, `acompanamiento`, `fecha`: pone `False` y `save()`; éxito «El campo '<campo>' ha sido restaurado correctamente.» |
| Campo inválido | Error «El campo '<campo>' no existe en el modelo Hitos.» |
| Redirección | `safe_redirect` al Referer o, por defecto, `/acompanamientos/acompanamiento/<comedor_id>/detalle/?admision_id=<id>` |
| Evidencia | No se registra historial propio; solo el `save()` del modelo (auditoría genérica si existe en el proyecto, no contrastada) |

No hay transición inversa (marcar completado) desde la UI: solo intervenciones lo
hacen.

## 6. API web propuesta (`/api/web/comedores/`)

Precondición común: `api/web/comedores/` en `url_prefixes` de `comedores`
(`src/backends/config/backends.json`) y `url_registry.json` regenerado. Vistas DRF
con `WebGatePermission` y después la guarda de permiso nativa y el alcance de
§2; JSON privado `no-store`, `Vary: Cookie`; CSRF en POST urlencoded; sin reintento
automático (504 `uncertain: true` en el POST se muestra y se ofrece recargar).

| Método | Ruta | Reutiliza | Respuestas |
|---|---|---|---|
| GET | `/api/web/comedores/acompanamientos/` | `obtener_comedores_acompanamiento(user, request)` + `preparar_datos_tabla_comedores` + `get_filters_ui_config` + preferencias de columnas | 200 página de 10 con celdas, columnas activas, config de filtros, favoritos; 400 si `filters` es inválido según el motor actual (contrastar respuesta nativa); 401/403 |
| GET | `/api/web/comedores/acompanamientos/<comedor_id>/?admision_id=` | Contexto de `AcompanamientoDetailView.get_context_data` extraído a una función de servicio sin cambiar resultados | 200 convenios, admisión resuelta, información relevante, prestaciones, 23 hitos con fecha, capacidades `puede_restaurar` y `ver_informe_complementario`; 404 fuera de alcance |
| POST | `/api/web/comedores/acompanamientos/<comedor_id>/hitos/restaurar/` | Lógica de `restaurar_hito` (extraída a servicio) | 200 `{"ok": true, "message": {"level": "success", "text": "El campo '<campo>' ha sido restaurado correctamente."}, "redirect": <detalle con admision_id>}`; 400 campo inválido con el texto nativo; 404 alcance; 409 «No se encontraron hitos para el convenio seleccionado.»; 403 sin ALL de permisos |

El CSV no tiene endpoint JSON: GET nativo a
`/acompanamientos/acompanamiento/exportar/` con la misma consulta.

## 7. Módulo React

- `src/frontends/apps/sisoc/src/routes/acompanamientos.tsx` (+
  `acompanamientos.test.tsx`), registrado en `routes/index.ts` antes de
  `businessRoute`; reconoce `/acompanamientos/acompanamiento/` y
  `/acompanamientos/acompanamiento/<id>/detalle/` (con el slash final nativo).
- Listado con los componentes compartidos de búsqueda/filtros/tabla ya usados por
  otras pantallas migradas cuando existan; si no, réplica del markup de
  `search_bar.html` y `data_table.html`. CSS `listModerno.css` y `hitos.css`
  cargadas solo con la ruta montada.

## 8. Decisiones técnicas del agente

1. **`admision_id` explícito al restaurar.** React envía siempre la admisión
   mostrada (lo mismo que agrega el script nativo cuando hay admisión activa). No
   depende del Referer.
2. **Lista blanca de `campo` en la API.** La vista nativa acepta cualquier atributo
   del objeto (`hasattr`), lo que permite con un POST manual poner `False` en `pk`,
   `acompanamiento_id` o reemplazar un método (B2). La API nueva acepta solo los 23
   campos booleanos de §4.2 y para cualquier otro devuelve 400 con el mismo texto
   nativo «El campo '<campo>' no existe en el modelo Hitos.». Para las 23 entradas
   válidas el efecto es idéntico; la vista Django queda como está.
3. **Contadores en servidor o cliente**: se calculan desde las 23 filas devueltas,
   iguales a los del script nativo.
4. **AJAX** sin uso: no se migra ni se borra.

## 9. Criterios de aceptación

1. Listado: mismo conjunto, orden (`-id`, `nombre`, `-nombre`), 10 por página,
   búsqueda y filtros avanzados que el HTML; mismas celdas y «-».
2. Detalle: misma admisión resuelta para `?admision_id` ausente, válido, de otro
   comedor y no numérico; textos de vacíos exactos de §4.2.
3. Restaurar con técnico: hito pasa a `False`, aviso «El campo 'retiro_tarjeta' ha
   sido restaurado correctamente.» y vuelta al detalle del mismo convenio.
4. Restaurar sin `acompanamientos.change_hitos`: 403 sin escritura. Comedor fuera
   de alcance: 404 sin escritura.
5. CSV: mismo archivo byte a byte (salvo timestamp del nombre) que el GET nativo
   para la misma consulta.
6. Visual S13 por URL/estado/rol en desktop y móvil: paridad estructural y diff
   perceptual ≤1 % ignorando antialiasing; 8 minutos máximo de diagnóstico.

## 10. Dependencias

- G1 v1 (hecho) y prefijo `api/web/comedores/` (compartido; un dueño del cambio).
- AD03: crea el acompañamiento; sin AD03 migrado, los datos siguen viniendo del
  flujo Django y AC01 funciona igual.
- CO02 (intervenciones): marca hitos. CO07 (ficha): destino de volver. Ninguno es
  bloqueante: AC01 enlaza a sus URLs nativas.

## 11. Riesgos

- R1: restaurar sin `admision_id` y sin Referer cae al acompañamiento más reciente
  del comedor; React lo evita enviando la admisión (decisión 1).
- R2: alcance asimétrico listado/detalle para territoriales (paridad).
- R3: 504 incierto al restaurar: el usuario recarga; restaurar es idempotente
  (repetirlo deja `False`).

## 12. Bugs nativos detectados (no se corrigen en esta entrega)

- B1: el CSV usa rutas `organizacion__nombre`, `provincia__nombre` y
  `dupla__nombre` (`views_export.py:25–28`), pero `CSVExportMixin.resolve_field`
  separa por `.` (`kernel/core/mixins.py:48–58`): esas tres columnas salen siempre
  vacías.
- B2: `restaurar_hito` permite escribir `False` en cualquier atributo existente del
  objeto `Hitos`; sin `campo`, `hasattr(hito, None)` lanza `TypeError` (500).
- B3: el endpoint AJAX pasa la búsqueda en minúsculas como `request_or_query`; no
  aplica filtros avanzados ni coincide con el listado (sin consumidores).

## 13. Incertidumbres

- U1: respuesta nativa a anónimo (decorador `PermissionDenied` antes del login).
- U2: si existe auditoría genérica de `Hitos` (auditlog); no se encontró registro
  específico en `acompanamientos`.
- U3: respuesta del motor de filtros ante `filters` mal formado (fijar en la línea
  base del diferencial).

## 14. Casos de prueba

Backend (`src/backends/comedores/tests/` o `acompanamientos/tests/`):

1. Guardas del listado y detalle: con permiso 200; sin permiso 403; anónimo 401 G1.
2. Alcance: dupla ve solo los suyos; coordinador sus duplas; territorial con comedor
   fuera de territorio: aparece en listado, detalle 404 (paridad).
3. Resolución de admisión: sin parámetro, válido, de otro comedor, cerrada.
4. Hitos: 23 filas en orden; fecha de la intervención más reciente; FCH completa
   solo con los 8 subtipos.
5. Restaurar: campo válido pone `False`; `campo` fuera de lista 400 sin escritura
   (`pk`, `acompanamiento_id`, vacío); sin hitos 409; sin `change_hitos` 403;
   repetir 200 idempotente; `admision_id` explícito restaura ese convenio y no otro.
6. API y HTML: mismo estado final tras restaurar por cada vía.
7. CSV nativo sin cambios (regresión de los dos tests existentes).

Frontend (vitest): rutas con y sin slash; selector de convenio navega con
`?admision_id`; botón deshabilitado cuando no hay capacidad o hito pendiente;
contadores; 400/403/404/409 como avisos; 504 incierto sin reintento.

Diferencial y visual: base vs candidato para listado (vacío, con filtros, página
2, orden) y detalle (sin admisión, una, varias activas, cerrada, sin hitos, con
informe complementario) por rol (técnico, lector, coordinador, superusuario) en
desktop y móvil, regla S13.

## 15. Fuente

- `src/backends/comedores/acompanamientos/urls.py:1–43`
- `src/backends/comedores/acompanamientos/views.py:1–361`
- `src/backends/comedores/acompanamientos/views_export.py:1–77`
- `src/backends/comedores/acompanamientos/acompanamiento_service.py:30–785`
- `src/backends/comedores/acompanamientos/services/filter_config.py:1–80`
- `src/backends/comedores/acompanamientos/models/hitos.py:7–93`
- `src/backends/comedores/acompanamientos/templates/acompañamiento_detail.html:1–1089`, `lista_comedores.html`, `acompanamientos/partials/comedor_rows.html`
- `src/backends/comedores/comedores/services/comedor_service/impl.py:536–566, 877–887, 1034–1059`
- `src/backends/comedores/admisiones/services/admisiones_service/impl.py:1142–1150, 2459–2473`
- `src/backends/comedores/comedores_runtime/urls.py:12–13`
- `src/backends/kernel/core/mixins.py:13–120`; `src/backends/kernel/core/services/list_ordering.py:6–31`
- `src/backends/kernel/users/bootstrap/groups_seed.py:17–45`
- Pruebas existentes: `src/backends/comedores/tests/test_acompanamientos_filter_config_unit.py`, `test_acompanamientos_list_filters_db.py`

Lectura de código sin ejecución de app, base de datos ni navegador.
