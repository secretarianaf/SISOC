# Contrato ejecutable de consulta de centros CDF (#2805)

Fecha: 2026-10-27; ejecutable desde 2026-11-10. Fuente: `HEAD` 4ea95bcbe (las
líneas citadas son de ese commit). Estado: **contrato ejecutable** de la entrega
CDF04.01 «Consulta de centros y ficha NoCount». No hay endpoints, tipos TS ni
capturas creados todavía. Complementa la [matriz CDF01–CDF04](2026-10-27-2786-matriz-flujos.md),
[CDF-A/CDF-B](2026-10-28-2785-cdf-centros-actividades-m2.md),
[usuarios/CABAL y CR1](2026-10-28-2785-cdf-usuarios-cabal-y-credenciales.md),
[circuitos y D1](2026-10-28-2785-cdf-circuitos-y-alcance-autorizacion.md) y el
[contrato CDF03/CDF04](2026-11-10-2785-cdf03-cdf04-contratos.md), que define
`DEF_2805_NoCount_y_alcances_separados` a partir de este documento.

Decisiones vigentes que este contrato aplica, sin reabrirlas: G1 v1 opción A con
ventana de 60 s ([decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md)),
D1 paridad estricta de autorización, CR1 para credenciales, M2 retorno/feedback
React, regla visual S13 (paridad estructural, cada elemento a ≤ 2 CSS px y diff
perceptual sin antialiasing ≤ 1 %).

## Decisión de reutilización (sin cambios)

La API `src/backends/cdf/centrodefamilia/api_views.py:60` (`CentroViewSet`,
`HasAPIKey` en :83) no se convierte a sesión ni se expone al navegador. La API web
nueva reutiliza los helpers del backoffice con el mismo permiso y alcance, sin
invocar una vista HTML como función de negocio. Rutas legacy (runtime cdf,
`src/backends/cdf/cdf_runtime/urls.py:11` monta `centrodefamilia/`):

| Ruta nativa | Nombre | Vista (HEAD) |
|---|---|---|
| `/centrodefamilia/centros/` | `centro_list` | `views/centro.py:122` `CentroListView` (urls.py:69–75) |
| `/centrodefamilia/centros/ajax/` | `centros_ajax` | `views/centro.py:443` (urls.py:76–80), queda sin consumidor React |
| `/centrodefamilia/centros/<pk>/` | `centro_detail` | `views/centro.py:189` `CentroDetailView` (urls.py:95–101) |

Todas las URLs exigen `permissions_any_required(["centrodefamilia.view_centro"])`
(`src/backends/kernel/core/decorators.py:35`): sin el permiso responde
`PermissionDenied` (403), también para anónimos.

## Endpoints

Runtime dueño: `cdf` (`src/backends/config/backends.json`, clave `cdf`). Prefijo
nuevo `api/web/cdf/` agregado a `url_prefixes` (configuración compartida del
padre) y montado en `cdf_runtime/urls.py` con
`path("api/web/cdf/", include("centrodefamilia.web_api_urls"))`. Vistas DRF
`APIView` con `SessionAuthentication` + `core.web_gate.WebGatePermission` y luego
el chequeo nativo (`user_has_permission_code(user, "centrodefamilia.view_centro")`,
si falla `PermissionDenied()` de DRF con su `detail` por defecto, como Insumos).
Respuestas JSON con `Cache-Control: private, no-store` y `Vary: Cookie`. Solo
`GET`/`HEAD`/`OPTIONS`. Errores del core según G1: 401 sin sesión, 403 con `state`
y `required_action_url` si hay requisito web pendiente, 414, 503, 504.

| Método y ruta | Uso | Respuesta |
|---|---|---|
| `GET /api/web/cdf/centros/?busqueda=&filters=&page=` | Listado | 200 página NoCount (abajo) |
| `GET /api/web/cdf/centros/<pk>/?search_actividades_curso=&page_actividades_curso=&search_actividades=&page_act=` | Ficha completa salvo credenciales | 200; 404 inexistente; 403 fuera de regla de ficha |
| `GET /api/web/cdf/centros/<pk>/usuarios/` | Panel «Usuarios del centro» (CR1) | 200 si `puede_ver_usuarios_cdf`; 403 si no; 404 inexistente |

Nombres de URL: `web_cdf_centros_list`, `web_cdf_centros_detail`,
`web_cdf_centros_usuarios`. Archivo nuevo `centrodefamilia/web_api_urls.py`,
`web_api_views.py`, `web_api_serializers.py` (mismo patrón que
`src/backends/sisoc_core/insumos/web_api_*.py`).

**Ficha en un solo endpoint (decisión del agente):** la vista nativa calcula
actividades, métricas y paginaciones en un único `get_context_data`
(`views/centro.py:212–324`) y la búsqueda «en curso» cambia las métricas del
encabezado (ver ficha). Partirlo en varios endpoints duplicaría la consulta y
arriesga divergencias. El panel de credenciales sí va aparte porque CR1 exige
proyección privada separada con su propio predicado.

**Extracción mínima:** mover a `services/centro_service` las funciones puras que
hoy están en la vista (`_build_cdf_centro_list_queryset`,
`_hydrate_cdf_centro_page`, y el cálculo de contexto de ficha como
`build_centro_detail_data(centro, user, params)`), usadas por la vista HTML y la
API. Una regresión por regla compara el contexto HTML antes/después. No se
reescribe la vista ni se crean filtros alternativos.

## Listado

### Alcance (`views/centro.py:93–111`, `access.py:182–204`)

| Actor, además de `view_centro` | Alcance |
|---|---|
| Superusuario o `auth.role_cdf_sse` | Sin restricción adicional |
| Usuario con algún `AccesoCDF` (activo o histórico) | Solo `centro_id` de accesos activos; con historial y sin activos, lista vacía (no cae al FK legacy) |
| Sin historial `AccesoCDF` y con `auth.role_referentecentro` | `referente_id == user.id` |
| Otro | `Centro.objects.none()` |

`ids_centros_referente_cdf` devuelve `None` sin historial y lista (posiblemente
vacía) con historial: no confundir `[]` con `None`.

### Búsqueda, filtros, orden

- `busqueda` (`views/centro.py:82–90`): strip; vacío no filtra; solo dígitos →
  `codigo__startswith` **o** `pk` exacto; texto → `nombre__icontains`.
- `filters`: mismo parámetro y payload JSON de `AdvancedFilterEngine`
  (`views/centro.py:50–58`), con `FIELD_MAP`/`FIELD_TYPES`/operadores de
  `services/centro_filter_config/impl.py:5–69`. `codigo` está en `FIELD_MAP` pero
  no en `FIELD_TYPES`: se conserva tal cual (el motor decide); no se agrega tipo.
- Orden backend `-id`. El orden por columna es **local a la página visible**
  (`listSort.js`): React ordena solo las filas cargadas por `nombre`, `tipo`
  (texto visible), `calle`, `telefono`, `activo`; no se envía `sort` al servidor.
- Favoritos: sección `SeccionesFiltrosFavoritos.CDF_CENTROS`; se usan los
  endpoints existentes del core `ajax/filtros-favoritos/` y
  `ajax/filtros-favoritos/<pk>/` (`src/backends/kernel/core/urls.py:52–61`).

### Paginación NoCount (`src/backends/kernel/core/pagination.py:39–116`)

10 IDs por página sobre `values_list("pk")`, hidratación en el orden de los IDs.
Envolvente CDF (adapta la de Insumos, `web_api_serializers.py:26–32`, con total
desconocido explícito):

```json
{
  "count": null,
  "page": 1,
  "page_size": 10,
  "pages": null,
  "has_next": false,
  "has_previous": false,
  "page_range": [1],
  "filters": {"busqueda": "", "filters": ""},
  "results": []
}
```

Ejemplo de página vacía, no respuesta real. `page_range` sale de
`build_no_count_page_range` (ventana 2) y puede contener el string `"..."`.
Reglas: `page` inválida, cero, negativa o `last` → 1; página por encima del final →
última no vacía (búsqueda binaria), no 404; cero resultados → página 1 vacía. El
tipo TS `CdfNoCountPage<T>` admite `null` en `count`/`pages`; no se modifica el
tipo `Page` compartido. La UI no muestra total ni «página X de Y»: el componente
nativo omite «Se encontraron N resultados» cuando `count` es `None`
(`components/pagination.html`, último bloque).

### Fila (`templates/centros/centro_list.html:51–98`)

| Campo JSON | Fuente | Visible |
|---|---|---|
| `id` | `pk` | enlaces |
| `nombre` | `nombre` | enlace a ficha, `title="Ver detalles"` |
| `tipo`, `tipo_display` | `tipo`, `get_tipo_display()` | Tipo (FARO muestra «faro», en minúscula, como hoy) |
| `calle` | `calle` | Dirección |
| `telefono`, `celular` | ídem | «`{telefono} / {celular}`» (con barra aunque falte uno) |
| `activo` | `activo` | badge «Activo»/«Inactivo» |

No se devuelven `codigo` (cargado por `only` pero no visible), beneficiarios,
contactos ni perfiles.

### Capacidades de presentación

| Clave | Regla | Efecto en UI |
|---|---|---|
| `can_add` | `is_superuser or role_cdf_sse` (`views/centro.py:154–156`) | Botón «Agregar» + «Agregar Actividad» (`actividad_create_sola`) + «Procesar Informe Cabal» (`informecabal_list`) |
| `can_delete` | `perms.centrodefamilia.delete_centro` del template (:82) | Botón «Eliminar» por fila |

«Ver» y «Editar» se muestran en todas las filas sin condición (:70–81); la ruta de
destino autoriza. Presencia de botón no es permiso. «Eliminar» es POST con CSRF y
confirmación `¿Estás seguro de que deseas eliminar este centro? Esta acción no se puede deshacer.`;
en React su acción pertenece a CDF04.02 y, hasta que esa entrega exista, envía el
mismo POST nativo a `/centrodefamilia/centros/<pk>/eliminar/` desde un formulario
con CSRF (nunca GET).

### Textos de aceptación

Título «Centros de Familia»; breadcrumb «Centro de Familia» › «Listar»; buscador
«Buscar Centro», placeholder y ayuda «Buscar por nombre, dirección o tipo»;
columnas «Nombre», «Tipo», «Dirección», «Teléfono», «Estado», «Acciones»; vacío
«No se encontraron centros.»; paginación «Volver»/«Continuar».

## Ficha

### Autorización (`views/centro.py:194–210`)

Permitido si referente FK (`referente_id == user.id`), `AccesoCDF` activo en ese
centro, superusuario, `auth.role_cdf_sse` **o** `puede_gestionar_usuarios_cdf`
(`access.py:56–78`: delegación del grupo «CDF - Referente centro» + territorio,
sin cupo). Inexistente → 404; existente fuera de regla → 403 (paridad, no se
oculta con 404). La ficha no se deriva del listado.

### Proyección

| Bloque | Campos JSON | Regla fuente |
|---|---|---|
| `centro` | `id, nombre, tipo, tipo_display, activo, codigo, localidad, provincia, municipio` (strings `str()` o null), `correo, sitio_web, link_redes, organizacion_asociada, telefono, celular, calle, numero, domicilio_actividad, nombre_referente, apellido_referente, telefono_referente, correo_referente` | `centro_detail.html:17–220, 420–446`; vacíos se renderizan «—» en cliente |
| `mapa` | `query` = `google_maps_query(latitud, longitud)` (`custom_filters.py:225`) o null; `direccion` = `{calle, numero, localidad, municipio, provincia}` solo si los cinco existen | iframe Google como hoy (:188–199), si no «Sin mapa disponible» |
| `acciones` | `editar_url`, `agregar_actividad_url`, `agregar_adherido_url` (solo FARO), `generar_usuario_url` si `puede_generar_usuario_cdf` | :37–55; Editar y Agregar Actividad siempre visibles |
| `metricas` | `categorias, actividades, inscriptos, hombres, mujeres, mixtas, interacciones`, `total_recaudado` (solo adherido), `asistentes {total, hombres, mujeres, espera}` | :216–303; ver reglas |
| `actividades_curso` | página Django `Paginator(…, 5)` exacta: `count, page, pages, page_range, results[{id, actividad, categoria, dias[], horariosdesde, horarioshasta, estado_display, detalle_url}]` | :241–244 |
| `actividades_otras` | ídem con `results[{id, centro, actividad, categoria, estado_display, cantidad_personas, dias[], horariosdesde, horarioshasta, precio}]` | :253–276, modal :680–732 |
| `cabal` | `ultimo {fecha_subida, usuario}` o null; `archivos[{id, nombre_original, fecha_subida, url}]` orden `-fecha_subida` | :305–310, :161–172, :639–671 |
| `adheridos`, `observaciones` | listas vacías fijas | sin productor en vista (:513–526, :566–638) |
| `puede_ver_usuarios` | bool | habilita la llamada a `/usuarios/` |

Reglas de métricas (conservar, no recomputar en React):

- `qs_acts` filtra por `search_actividades_curso` (strip + lower; nombre,
  categoría o estado `icontains`). `actividades` = su count, `interacciones` y
  `asistentes.total` = suma de `Count(participanteactividad, distinct)` **sin
  filtrar estado**; `total_recaudado` = Σ `precio × inscritos` del mismo filtro.
  Por eso buscar «en curso» cambia esas métricas del encabezado.
- `inscriptos`, `hombres` («Masculino»), `mujeres` («Femenino») cuentan
  `estado="inscrito"` del centro sin filtro; `espera` cuenta `lista_espera`;
  `mixtas = interacciones − hombres − mujeres` (puede ser negativa).
- `categorias` = `Categoria.objects.count()` global.
- La tarjeta FARO «Centros Adheridos» usa `metricas.centros_faro`, que la vista no
  calcula: se renderiza vacía. Se conserva vacía (`null`), no se conecta un conteo.
- La pestaña «En curso» lista **todos los estados**; no filtrar `en_curso`.
- Otras actividades: `exclude(centro)`, orden `centro__nombre, actividad__nombre, id`,
  búsqueda en actividad, categoría, estado o nombre de centro.
- Paginadores Django `get_page`: inválida → 1, fuera de rango → última.

Búsquedas: el nativo recarga en cada `input` (`centrodefamilia.js:121–136`);
`search_actividades` borra `page_act`, `search_actividades_curso` borra `page`
(no `page_actividades_curso`). React re-consulta en cada cambio (puede agregar
debounce ≤ 300 ms sin cambiar resultado), resetea `page_act` con la búsqueda de
«todas» y **conserva** `page_actividades_curso` con la de «en curso» (el
paginador lo acota a la última). Si hay `page_act` o `search_actividades`, se
activa la pestaña «Todas las actividades» (:735–743). Los enlaces de paginación de
«todas» no llevan `search_actividades_curso`, y los de «en curso» no llevan los de
«todas»: se replica esa pérdida de parámetros (paridad de quirks).

### Panel de credenciales (CR1)

`GET /api/web/cdf/centros/<pk>/usuarios/`: primero la regla de ficha, después
`puede_ver_usuarios_cdf` (`access.py:93–106`); si falla, 403. Filas: superusuario
ve todos los `AccesoCDF` del centro; otro actor solo el propio activo; orden
`-activo, user__username` (`views/centro.py:316–322`). Campos exactos:
`username, nombre_completo (get_full_name o null), email (o null), activo,
contrasena_temporal (profile.temporary_password_plaintext o null)`. Nada más del
User/Profile. El cliente no lo guarda en estado persistente, URL, storage,
telemetría ni logs; la respuesta no se cachea (no-store).

Textos: «Usuarios del centro»; «Credenciales visibles solo para el referente del
centro y administradores. La contraseña temporal se oculta automáticamente cuando
el usuario la cambia.»; columnas «Usuario», «Nombre», «Email», «Estado»,
«Contraseña temporal»; «Activo»/«Baja»; «Ya cambiada»; vacío «No hay usuarios
generados para este centro.».

### Textos de aceptación de ficha

Pills «Activo»/«Inactivo» y tipo; botones «Editar», «Agregar Actividad»,
«Agregar Adherido», «Generar usuario»; métricas «Centros Adheridos», «Monto
Recaudado», «Categorías», «Actividades», «Inscriptos», «Asistentes» con
«{h} hombres · {m} mujeres», «Lista de espera»; «Información del centro»,
«Último informe CABAL», «Sin informes vinculados»; «Ubicación», «Sin mapa
disponible»; «Actividades», «En curso», «Todas las actividades», «Buscar
actividad…», «No hay actividades en curso.», «No hay actividades.», «Anterior»,
«Siguiente», «Detalles»; modal «Cupo Total», «Días», «No especificado», «Horario
desde», «Horario hasta», «Precio», «Gratuita», «Estado»; «Referente»,
«Responsable», «Teléfono», «Correo»; «Observaciones», «Sin observaciones», «No
hay observaciones registradas para este centro.»; «Gestión del centro», «Centros
adheridos», «Informes CABAL», «Buscar centro…», «No hay centros adheridos.»,
«Archivo», «Fecha de carga», «Acción», «Ver registros», «No hay informes CABAL con
registros vinculados a este centro.». Fuente Lora y `cdf.css` se conservan.

## React

Módulo `src/frontends/apps/sisoc/src/routes/cdfCentros.tsx`, registrado en
`SHELL_ROUTES` antes de `insumosRoute`. Rutas `/v2/sisoc/centrodefamilia/centros/`
y `/v2/sisoc/centrodefamilia/centros/<pk>/`. Enlaces a pantallas no migradas
apuntan a la URL nativa (`/centrodefamilia/...`). Depende del patrón de entrada
React por runtime que define el piloto de Inspecciones (L134).

## Casos de prueba

| Caso | Esperado |
|---|---|
| SSE / superusuario | Lista completa `-id`, `can_add` true, ficha 200 |
| `AccesoCDF` activo en A | Lista solo A; ficha A 200; ficha B 403; `/usuarios/` de A solo su fila |
| Historial sin activos + FK legacy de C | Lista vacía; ficha C 200 por FK |
| Referente legacy sin historial | Lista por FK; panel de usuarios 403 |
| Delegador territorial sin cupo | Ficha 200; `generar_usuario_url` ausente; `/usuarios/` 403 |
| Sin `view_centro` | 403 en los tres endpoints; inexistente con permiso 404 |
| `busqueda=12` | código con prefijo 12 o id 12; `busqueda=ana` nombre |
| `page=0`, `page=last`, `page=999`, cero resultados | 1, 1, última no vacía, página vacía con `count:null` |
| Búsqueda «en curso» | métricas `actividades/interacciones/asistentes.total/total_recaudado` cambian; `inscriptos/espera/categorias` no |
| G1 | sin sesión 401; requisito pendiente 403 con `state`; header falso en runtime 403 |
| Diferencial | contexto HTML de lista y ficha idéntico antes/después de la extracción |
| Visual S13 | lista (vacía, 1 y 2 páginas, por rol), ficha FARO/adherido, cada pestaña, modal, panel visible/oculto, desktop y móvil, orden de Tab |

Pruebas existentes a extender: `src/backends/cdf/tests/test_centro_views_unit.py`,
`src/backends/cdf/centrodefamilia/tests/test_generar_usuario_cdf.py`,
`test_centrodefamilia_public_api.py` (la API key no cambia).

## Riesgos e incertidumbres

- D1 conserva accesos amplios (p. ej. `Editar` visible a quien solo ve la ficha);
  no se corrigen aquí.
- `google_maps_query` y el iframe dependen de Google; no se prueba el proveedor.
- La extracción de helpers toca la vista HTML: se cubre con el diferencial.
- No verificado en runtime: que `Count(participanteactividad)` coincide en MySQL
  con los fixtures; se valida con `mysql_compat` si el entorno lo permite.
