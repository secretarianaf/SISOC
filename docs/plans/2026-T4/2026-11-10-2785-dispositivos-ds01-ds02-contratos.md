# DS01-DS02: Dispositivos en React (mapa, ubicación, listado, legajo y gestión)

Contrato ejecutable de #2785 para los flujos DS01 y DS02 del catálogo
[entregas por flujo](2026-10-27-2785-entregas-por-flujo.json). Fuente leída en
`HEAD 4ea95bcbe` con `git show`; las líneas del catálogo quedaron viejas y acá se
citan las vigentes. Sin implementación ni prueba runtime: es la especificación que
lee el writer. Regla general: **paridad nativa**. Los quirks se documentan y no se
corrigen incidentalmente.

## Decisiones comunes

- Dueño: runtime `dispositivos` (`src/backends/config/backends.json`, clave
  `dispositivos`, `urlconf` `dispositivos_runtime.urls`). Se agrega el prefijo
  `api/web/dispositivos/` a `url_prefixes` y se regenera
  `src/backends/config/url_registry.json` (setup compartido del padre).
- Transporte: G1 v1 ([decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md)).
  Vistas DRF `APIView` con `SessionAuthentication` + `core.web_gate.WebGatePermission`
  y, en la vista del dueño, los mismos permisos y el mismo alcance que la ruta nativa.
  Mutaciones POST con CSRF; sin reintento automático (504 con `uncertain: true` en
  métodos no seguros). `Cache-Control: private, no-store` en todas las respuestas.
- Reutilización obligatoria: `get_dispositivos_queryset`, `apply_dispositivos_scope`,
  `DISPOSITIVOS_ADVANCED_FILTER`, `get_filters_ui_config`, `DispositivoForm`,
  `DispositivoUbicacionForm`, `save_dispositivo_from_form`, `delete_dispositivo`,
  `geolocate_dispositivo`, `get_saved_dispositivo_location`,
  `get_dispositivo_map_query` (`src/backends/dispositivos/dispositivos/services.py`,
  `forms.py`, `views.py`). Refactor mínimo autorizado: extraer de
  `DispositivoDetailView.get_context_data` (`views.py:129-525`) una función
  `build_detalle_secciones(dispositivo)` que usen la vista nativa y la API; la salida
  nativa debe quedar byte a byte igual (prueba diferencial).
- Geografía en cascada: React reutiliza los endpoints JSON del core
  `/ajax/load-municipios/?provincia_id=` y `/ajax/load-localidades/?municipio_id=`
  (`src/backends/kernel/core/urls.py:44-52`, `core/views.py:67-84`), que ya aplican
  `get_geography_scope_map`. No se duplican en el vertical.
- Sobre de página: el de `InsumoPageSerializer`
  (`src/backends/sisoc_core/insumos/web_api_serializers.py:26-32`: `count`, `page`,
  `page_size`, `pages`, `filters`, `results`). Página inválida: 404
  `{"detail": "Página no válida."}` como Insumos.
- Errores de formulario: 400 `{"errors": form.errors.get_json_data()}` como Insumos.
  Éxito de mutación: mismo sobre que `InsumoMutationSuccessSerializer` con el
  mensaje nativo y la ruta React de destino.
- Archivos adjuntos: se siguen sirviendo con su URL de media nativa
  (`file_field.url`, `views.py:57-63`). La API devuelve `name` y `url` igual que hoy;
  no hay proxy JSON de archivos. Incertidumbre: qué proceso sirve `/media/` para
  este dueño en despliegue separado (no hay prefijo `media/` en `backends.json`
  para `dispositivos`); se conserva el comportamiento actual y se verifica en la
  prueba runtime, sin cambiarlo.
- Mapas: mismo proveedor y semántica. Listado general con Leaflet 1.9.4 por CDN
  (mismo SRI que `dispositivos_map.html:7-10,118-120`) y teselas OpenStreetMap;
  vista del legajo con iframe de Google Maps (`dispositivos/ubicacion_mapa.html:19-25`).
  El editor de pin React existe en `src/frontends/apps/vpsl/src/MapPinEditor.tsx`
  (Leaflet por CDN, sin paquete). Decisión técnica: promoverlo a
  `src/frontends/packages/ui` sin cambiar su comportamiento (tests VPSL en verde) y
  consumirlo desde Dispositivos; no se agrega dependencia. #2792 (pin interactivo)
  ya está integrado en `HEAD` (commit `1e84aca94` y anteriores); no hay coordinación
  pendiente, solo paridad con el editor compartido `kernel/templates/components/map_pin_editor.html`.
- Módulos React: `src/frontends/apps/sisoc/src/routes/dispositivos.tsx` (listado,
  legajo, alta, edición, baja) y `src/frontends/apps/sisoc/src/routes/dispositivosMapa.tsx`
  (mapa general). Rutas de pantalla iguales a las nativas. Entrada React en el
  runtime: patrón que deja el piloto de Inspecciones (L134); dependencia dura.
- Regla visual S13 por caso (paridad estructural + diff perceptual <= 1 %, 8 min de
  diagnóstico). Escritorio y móvil, foco y orden de Tab.

## Rutas nativas y permisos (no intercambiables)

Fuente: `src/backends/dispositivos/dispositivos/urls.py:14-75`. Los decoradores
`permissions_any_required`/`permissions_all_required` lanzan `PermissionDenied`
(`src/backends/kernel/core/decorators.py:35-62`); además cada vista es
`LoginRequiredMixin`.

| Nombre | Ruta | Permiso | Alcance |
|---|---|---|---|
| `dispositivos_listar` | `GET /dispositivos/` | ANY `view_dispositivo` | `apply_dispositivos_scope` |
| `dispositivos_detalle` | `GET /dispositivos/<pk>/` | ANY `view_dispositivo` | scope; fuera de alcance 404 |
| `dispositivos_crear` | `GET/POST /dispositivos/crear` | ANY `add_dispositivo` | geografía del form acotada |
| `dispositivos_editar` | `GET/POST /dispositivos/<pk>/editar` | ANY `change_dispositivo` | scope + geografía |
| `dispositivos_eliminar` | `GET/POST /dispositivos/<pk>/eliminar` | ANY `delete_dispositivo` | scope |
| `dispositivos_mapa` | `GET /dispositivos/mapa/` | ALL `view_dispositivo` + `ver_mapa_dispositivo` | scope |
| `dispositivos_ubicacion` | `GET /dispositivos/<pk>/ubicacion/` | ALL los dos anteriores | scope; 404 fuera |
| `dispositivos_previsualizar_ubicacion` | `POST /dispositivos/ubicacion/previsualizar/` | ANY `add_dispositivo`, `change_dispositivo` | geografía del form |

Alcance (`services.py:31-59`): anónimo vacío; superusuario o no territorial sin
restricción; territorial por provincia y, si corresponde, municipio (un alcance de
localidad se respeta hasta su municipio); territorial sin alcances, vacío.
Las rutas sin barra final (`crear`, `editar`, `eliminar`) se conservan tal cual.

## Endpoints `/api/web/dispositivos/`

| Método y ruta | Permiso y alcance (igual al nativo) | Respuesta |
|---|---|---|
| `GET /api/web/dispositivos/` | ANY `view_dispositivo`; scope | página de 15 |
| `GET /api/web/dispositivos/options/` | ANY `view_dispositivo` | config de filtros y flags |
| `GET /api/web/dispositivos/<pk>/` | ANY `view_dispositivo`; scope | legajo |
| `GET /api/web/dispositivos/mapa/` | ALL `view` + `ver_mapa`; scope | dispositivos del mapa |
| `GET /api/web/dispositivos/<pk>/ubicacion/` | ALL `view` + `ver_mapa`; scope | resultado de ubicación |
| `POST /api/web/dispositivos/ubicacion/previsualizar/` | ANY `add`, `change` | resultado de ubicación |
| `GET /api/web/dispositivos/formulario/` | ANY `add_dispositivo` | esquema de alta |
| `POST /api/web/dispositivos/crear/` | ANY `add_dispositivo` | 201 / 400 |
| `GET /api/web/dispositivos/<pk>/formulario/` | ANY `change_dispositivo`; scope | esquema + valores |
| `POST /api/web/dispositivos/<pk>/editar/` | ANY `change_dispositivo`; scope | 200 / 400 |
| `GET /api/web/dispositivos/<pk>/eliminar/` | ANY `delete_dispositivo`; scope | datos de confirmación |
| `POST /api/web/dispositivos/<pk>/eliminar/` | ANY `delete_dispositivo`; scope | 200 / 409 |

Códigos comunes: 401/403 del core G1 (sin sesión o requisito pendiente), 403 JSON
por permiso de acción, 404 por objeto fuera de alcance o inexistente, 503 de
ubicación cuando Georef no responde (igual al nativo).

## DS01.01 Mapa y consulta de ubicación [L]

Fuente: `views.py:620-712` (`DispositivoMapView`, hereda de `DispositivoListView`),
`views.py:715-727` (`DispositivoLocationView`), `services.py:85-205`,
`templates/dispositivos_map.html:1-122`, `static/custom/js/dispositivosMap.js:1-207`,
`templates/dispositivos/ubicacion_mapa.html:1-27`.

`GET /api/web/dispositivos/mapa/` acepta los mismos parámetros que el listado
(`busqueda`, `filters` del motor avanzado, `dispositivo`) y devuelve, sin paginar:

- `devices`: por dispositivo `id`, `name`, `type` (display), `province_id`,
  `province`, `representative`, `phone` (prefijo y número unidos por espacio,
  omitiendo vacíos), `address` (`"{calle} {altura}, {municipio}, {provincia}"`),
  `detail_url` (ruta de pantalla), `location_url` (endpoint API de ubicación),
  `location` (`get_saved_dispositivo_location`: coordenadas explícitas o resultado
  persistido con firma vigente, si no `null`).
- `provinces`: provincias del alcance del usuario (no del resultado filtrado),
  orden `provincia__nombre`, distinct (`views.py:653-658`).
- `filters_config`: la del listado con `provincia` convertida a `choice` con
  nombres de `provinces` y el campo extra `estado_ubicacion`
  (Ubicado/Pendiente/Dirección ambigua/Sin coincidencia/Servicio no disponible;
  valores `located`, `pending`, `ambiguous`, `not_found`, `unavailable`).
- `location_filters`: ítems `estado_ubicacion` con `op` `eq`/`ne` del JSON
  `filters`; JSON inválido equivale a `{}` (`views.py:683-698`).
- `initial_device`: id pedido en `dispositivo` solo si está en `devices`, si no `""`.

Incertidumbre a contrastar en la prueba: el motor avanzado recibe también el ítem
`estado_ubicacion`, que no está en `FIELD_MAP`; se asume que lo ignora (el filtro es
solo de cliente). Probar que no cambia el queryset.

Comportamiento de cliente (paridad con `dispositivosMap.js`):

- Centro/zoom inicial, teselas OSM y atribución `© OpenStreetMap`; si Leaflet no
  carga: «No se pudo cargar el mapa. Consultá las direcciones en la tabla.».
- Primero procesa los dispositivos con `location`; después consulta en serie
  `location_url` con timeout de 20 s por pedido (`AbortSignal.timeout(20000)`). Tras
  el primer `unavailable` deja de consultar y marca el resto como no disponible.
- Estado por fila: «Pendiente» hasta resolver; etiquetas «Ubicado», «Dirección
  ambigua», «Sin coincidencia», «Servicio no disponible».
- Línea de estado: «{n} dispositivos para cargar.» al inicio; luego
  «{ubicados} ubicados · {guardados} guardados · {sin ubicar} sin ubicar · {procesados}/{total} revisados».
  Sin dispositivos: «No hay dispositivos para mostrar con los filtros seleccionados.».
  Con no disponible se agrega «. No se pudo consultar el servicio de ubicación. Volvé a intentar recargando la página.».
- Ajuste automático con el primer ubicado, cada 20 procesados y al final; botón
  «Ver todos» deshabilitado sin marcadores.
- Tabla del mapa dentro de `<details open>` «Dispositivos ({n})», columnas
  Institución, Tipo, Provincia, Municipio, Dirección, Ubicación, Acciones; acciones
  «Ver en mapa» (deshabilitado con título «Ubicación pendiente» hasta ubicarse,
  luego «Ver {nombre} en el mapa») y «Ver detalle». Paginación de cliente de 15 con
  «…» y «Continuar»; contador «Mostrando {a}–{b} de {n} dispositivos» o
  «No se encontraron dispositivos».
- Filtros de estado de ubicación se aplican en cliente; sin coincidencias se muestra
  la fila «No hay dispositivos que coincidan con la provincia y el estado seleccionados.».
  Sin resultados del servidor: «No se encontraron dispositivos» / «No hay dispositivos
  que coincidan con los criterios de búsqueda.».
- `<noscript>` nativo no aplica a React; se documenta como diferencia aceptada de
  plataforma (una SPA no funciona sin JavaScript), sin texto alternativo nuevo.

`GET /api/web/dispositivos/<pk>/ubicacion/`: mismo cuerpo que la vista nativa
(`geolocate_dispositivo`), 503 si `status == "unavailable"`, 200 en otro caso.
Efecto: puede persistir `ubicacion_georef` cuando el resultado es definitivo y la
dirección no cambió (`services.py:136-151`) y escribir caché 30 días (located) o 1
día. Es un GET con efecto ya existente; se conserva. No se reintenta en cliente.

Legajo (vista de consulta): con `ver_mapa_dispositivo`, sección «Ubicación en el
mapa» con iframe `https://www.google.com/maps?q={mapa_query}&output=embed`
(`Argentina` si falta). La API del legajo devuelve `mapa_query` solo con ese
permiso (`views.py:132-133`).

Criterios de aceptación: mismos dispositivos que el nativo para cada combinación de
filtros y rol; mismos textos; consulta de ubicación nunca dispara Georef real en
pruebas (`locate_address` mockeado); usuario sin `ver_mapa_dispositivo` recibe 403
en `mapa/` y `ubicacion/` aunque tenga `view_dispositivo`; dispositivo fuera de
alcance 404.

## DS01.02 Edición de punto y previsualización [M]

Fuente: `views.py:730-746` (`DispositivoLocationPreviewView`), `forms.py:723-732`
(`DispositivoUbicacionForm`), `templates/dispositivos/ubicacion_mapa.html:4-18`,
`kernel/templates/components/map_pin_editor.html`, `static/custom/js/dispositivoUbicacion.js`,
plan [pin interactivo](2026-10-26-2778-pin-interactivo.md).

- Vive dentro del formulario de alta/edición (DS02.02); se entrega junto o después
  de DS02.02.
- `POST /api/web/dispositivos/ubicacion/previsualizar/` (multipart o form-urlencoded,
  campos `provincia`, `municipio`, `localidad`, `calle`, `altura`): valida con
  `DispositivoUbicacionForm(user=request.user)` (mismos querysets acotados que el
  alta). Inválido: 400 `{"status": "invalid", "errors": form.errors}` (forma nativa,
  no la de Insumos, porque el editor ya la consume así). Válido:
  `geolocate_dispositivo(Dispositivo(**cleaned_data))`, 503 si no disponible. No
  guarda el dispositivo; no persiste resultado (sin `pk`).
- Textos: botón «Previsualizar ubicación»; estado «Se priorizan latitud y longitud.
  Si ambas están vacías, se busca por domicilio. La previsualización no guarda
  cambios.»; editor: «Ajustar pin en el mapa», «Arrastrá el pin hasta la ubicación
  correcta. El domicilio escrito se conserva. Los cambios se guardan al guardar el
  formulario.», «Colocar pin en el centro del mapa», «Descartar ajuste del pin».
- Reglas del editor (plan #2778): arrastrar cambia solo latitud/longitud del
  formulario; descartar restaura los valores previos; una coincidencia única completa
  coordenadas sin guardar; respuesta vieja se descarta si cambió el domicilio o se
  movió/descartó el pin; sin ubicación inicial vista de Argentina.
- Quirk a conservar: en edición, el editor consulta la ubicación guardada con
  `dispositivos_ubicacion`, que exige `view` + `ver_mapa`. Un editor sin
  `ver_mapa_dispositivo` recibe 403 en esa consulta y el editor sigue sin ubicación
  inicial. No se relaja el permiso.

Criterios: alcance territorial ajeno en `provincia`/`municipio` da 400 con errores de
`choice` nativos; ningún POST de previsualización crea ni modifica filas.

## DS02.01 Listado y legajo [L]

Fuente: `views.py:77-118` (listado), `views.py:121-525` (legajo),
`dispositivos_filter_config.py:1-75`, `templates/dispositivos_list.html:1-90`,
`templates/dispositivos_detail.html:154-345`, `favorite_filters.py`.

Listado (`GET /api/web/dispositivos/`):

- Orden `-created_at`, `nombre_institucion` (`services.py:22-28`); 15 por página.
- `busqueda` (trim): `icontains` sobre `nombre_institucion`, `tipo_dispositivo`
  (valor crudo de choice), `provincia__nombre`, `municipio__nombre`.
- `filters`: JSON del motor avanzado con `FIELD_MAP`/`FIELD_TYPES`; operadores texto
  `contains`, `ncontains`, `eq`, `ne`, `empty`; choice `eq`, `ne`, `empty`.
  Favoritos: sección `SeccionesFiltrosFavoritos.DISPOSITIVOS` vía endpoint core
  existente `ajax/filtros-favoritos/`.
- `results`: `id`, `nombre_institucion`, `tipo_dispositivo_display`, `provincia`,
  `municipio`, más `can_change`/`can_delete` derivados de permisos del usuario
  (los botones nativos dependen solo del permiso, no del objeto).
- `options/`: `filters_config`, `add_url` (solo con `add_dispositivo`), `map_url`
  (solo con `ver_mapa_dispositivo`; React arma `?{query sin page}&dispositivo={pk}`
  como `views.py:110-116` y `dispositivos_list.html:34-41`), `titulo`
  «Buscar Dispositivos».
- Textos: columnas Institución, Tipo, Provincia, Municipio, Acciones; botones
  «Ver en mapa» (título «Ver ubicación en el mapa»), «Ver detalle», «Editar»,
  «Eliminar»; «Agregar dispositivo»; enlace «Mapa de dispositivos»; vacío
  «No se encontraron dispositivos» / «No hay dispositivos que coincidan con los
  criterios de búsqueda.»; paginación «Volver»/«Continuar» conservando parámetros
  (`kernel/templates/components/pagination.html`).
- Quirk: `listSort.js` ordena solo la página visible en cliente; no se convierte en
  orden de servidor.

Legajo (`GET /api/web/dispositivos/<pk>/`): encabezado `nombre_institucion`, meta
tipo · provincia · municipio · «Actualizado el {d/m/Y}», botón «Editar» con
`change_dispositivo`; `breadcrumb` Dispositivos → nombre; `detalle_secciones`
idénticas a `views.py:138-524` (9 secciones, mismas etiquetas, `-` para vacío
mostrado como «—», listas como chips, archivos con `name`/`url`). Carrusel de
paneles y detalle completo como hoy; textos «Cargando información...». Fuera de
alcance: 404.

Exportación: no hay export nativo en Dispositivos; no se agrega.

## DS02.02 Gestión autorizada del dispositivo [M]

Fuente: `views.py:528-617`, `forms.py:11-720`, `validators.py:1-45`,
`templates/dispositivos_form.html:1-902`, `templates/dispositivos_confirm_delete.html:1-39`,
`static/custom/js/dispositivoFormModerno.js`.

Formulario (`formulario/`): campos y orden de `DispositivoForm.Meta.fields`
(`forms.py:413-473`), etiquetas y ayudas de `FIELD_LABELS_AND_HELP`, choices de las
listas `*_CHOICES` (`forms.py:14-160`) y del modelo. El esquema se genera desde el
form (no a mano). Geografía: `provincia` acotada al alcance; `municipio` según
provincia elegida y alcance; `localidad` según municipio (`forms.py:540-581`).

Reglas de validación (mensajes literales):

- `cuit_institucion`: se quitan no dígitos; exige 11 — «Ingrese un CUIT válido de 11 dígitos.».
- `responsable_dni`: 7 u 8 dígitos — «Ingrese un DNI válido (solo números).».
- `telefono_prefijo` requerido — «Ingrese el prefijo (solo números).»;
  `telefono_numero` requerido — «Ingrese el teléfono (solo números).»; ayuda
  «Tanto el prefijo como el teléfono deben ingresarse sin puntos ni guiones».
- `calle` y `altura` requeridos.
- Listas con «otro»: detalle obligatorio — «Este campo es obligatorio cuando selecciona 'Otro'.»
  (10 pares, `forms.py:630-680`).
- «Este campo es obligatorio cuando el tipo de gestión es 'Otra'.»;
  «Este campo es obligatorio cuando el tipo de dispositivo es 'Otro'.»;
  «Este campo es obligatorio cuando el tiempo de permanencia es 'Otro'.»;
  «Complete el detalle cuando el modo de registro es 'Otro'.».
- Archivos (5 campos): PDF/JPG/PNG, máx. 10 MB, content type permitido —
  «Solo se permiten archivos PDF, JPG o PNG.», «El archivo supera el tamaño máximo de 10 MB.»,
  «El tipo de archivo no está permitido.»; ayuda «PDF, JPG o PNG. Máximo 10 MB.».
  Quitar un archivo guardado envía `<campo>-clear=on` (ClearableFileInput), como el
  overlay «Marcado para eliminar» del nativo.
- Aviso general con errores: «No se pudo guardar el formulario. Revisá los campos marcados.».

Interfaz: 9 secciones con indicador «Progreso del Formulario» y
«{n}/9 secciones completadas»; «Añadir archivo»; botones «Volver» (listado),
«Cancelar» (historial atrás) y «Guardar dispositivo». Campos condicionales y
visibilidad de «otro» como `dispositivoFormModerno.js`.

Efectos:

- Alta: `save_dispositivo_from_form(form)` → destino legajo con
  «Dispositivo creado correctamente.» (201).
- Edición: `save_dispositivo_from_form(form, instance=...)` → legajo con
  «Dispositivo actualizado correctamente.» (200). Editar el domicilio invalida la
  firma de `ubicacion_georef` sin borrarla (comportamiento actual).
- Baja: confirmación «Confirmar eliminación» / «¿Seguro que desea eliminar el
  dispositivo {nombre}?», botones «Eliminar» y «Cancelar» (al legajo).
  `delete_dispositivo` es **baja física** (`instance.delete()`, `Dispositivo` no usa
  soft delete). `ProtectedError` (p. ej. relevamientos DataCalle con
  `on_delete=PROTECT`, incluidos los dados de baja lógica) → 409 con
  «No se puede eliminar el dispositivo porque tiene registros asociados: {lista}.» y
  React vuelve al legajo con ese error. Éxito → listado con
  «Dispositivo eliminado correctamente.».

Riesgos: multipart con hasta 5 × 10 MB bajo la ventana G1 de 60 s; probar 50 MB
sintéticos con red lenta antes de habilitar. Baja física irreversible: no se cambia
(paridad), pero la prueba debe usar base aislada.

## Dependencias

- Setup compartido `api/web/dispositivos/` (backends.json, url_registry, admindocs,
  `routes/index.ts`).
- Patrón de entrada React por runtime del piloto Inspecciones (L134).
- Editor de pin compartido (promoción de `MapPinEditor.tsx` a `packages/ui`).
- DS01.02 depende de DS02.02. DataCalle (DC01.02) enlaza «Dar de alta un
  dispositivo» a `dispositivos_crear` en pestaña nueva.

## Casos de prueba

Backend (`src/backends/dispositivos/dispositivos/tests/`, junto a
`test_dispositivos_views.py` y `test_dispositivos_map_services.py`):

1. Listado: superusuario, no territorial, provincial, provincial+municipio,
   territorial sin alcance (vacío); `busqueda`; cada operador de filtro; página 2;
   página inválida 404; mismos ids y orden que la vista nativa.
2. Permisos: sin `view` 403 en listado/legajo; con `view` sin `ver_mapa` 403 en
   `mapa/` y `<pk>/ubicacion/`; previsualizar con solo `add` o solo `change` 200 y
   sin ninguno 403; `crear` sin `add` 403; `editar` sin `change` 403; baja sin
   `delete` 403; objeto fuera de alcance 404 en legajo, ubicación, edición y baja.
3. Ubicación: Georef mockeado `located`, `ambiguous`, `not_found`, `unavailable`
   (503, sin persistencia); coordenadas explícitas sin llamada; firma vieja ignora
   lo guardado.
4. Formulario: cada mensaje literal anterior; provincia fuera de alcance rechazada;
   localidad de otro municipio rechazada; archivo 11 MB y `.exe` rechazados;
   `-clear` borra el archivo; alta y edición persisten igual que el POST nativo.
5. Baja: con relevamiento asociado 409 y fila intacta; sin asociados borra.
6. G1: sin constancia el runtime rechaza; sin sesión 401 desde el core.
7. Diferencial: HTML de las rutas nativas idéntico antes y después del refactor de
   `build_detalle_secciones`; rutas existentes sin cambios.

Frontend (`routes/dispositivos.test.tsx`, `routes/dispositivosMapa.test.tsx`):
textos literales, orden de Tab, estados vacíos, estado del mapa con respuestas
mockeadas en serie, corte tras `unavailable`, paginación de cliente, filtros de
estado de ubicación, botones según permisos, 409 de baja.

Visual S13: listado (con/sin resultados, con/sin permisos), mapa (cargando,
completo, no disponible), legajo (con/sin mapa, con archivos), alta, edición con
errores, confirmación de baja; escritorio y móvil.

## Fuente

`src/backends/dispositivos/dispositivos/urls.py:14-75`; `views.py:44-746`;
`services.py:22-205`; `forms.py:11-732`; `validators.py:1-45`;
`dispositivos_filter_config.py:1-75`; `models.py:10-80,304-310`;
`templates/dispositivos_list.html:1-90`; `dispositivos_map.html:1-122`;
`dispositivos_detail.html:154-345`; `dispositivos_form.html:1-902`;
`dispositivos_confirm_delete.html:1-39`; `dispositivos/ubicacion_mapa.html:1-27`;
`static/custom/js/dispositivosMap.js:1-207`; `dispositivoFormModerno.js:368-540`;
`src/backends/kernel/core/decorators.py:35-62`; `core/views.py:67-84`;
`kernel/templates/components/map_pin_editor.html`; `pagination.html`;
`src/backends/dispositivos/dispositivos_runtime/urls.py:1-20`;
`src/frontends/apps/vpsl/src/MapPinEditor.tsx`. Leído en `HEAD 4ea95bcbe`; sin
app, tests, DB, navegador ni remoto.

- [DataCalle DC01-DC02](2026-11-10-2785-datacalle-dc01-dc02-contratos.md).
- [Catálogo existente](2026-10-27-2785-entregas-por-flujo.json).
