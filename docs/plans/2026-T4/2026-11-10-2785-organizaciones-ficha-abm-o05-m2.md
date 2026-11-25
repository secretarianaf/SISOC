# O05: organización, legajo, ABM, programas y proyectos (M2)

| Campo | Valor |
|---|---|
| Fecha | 2026-11-10 |
| Familia | O05 (catálogo `2026-10-27-2785-entregas-por-flujo.json`), entregas O05.01, O05.02 y O05.03 |
| Dueño | runtime `comedores`, app `gestion_organizaciones` (modelos base en `kernel/organizaciones`) |
| Base leída | HEAD de Migracion-2 `4ea95bcbe` **y** `origin/development` `83d87cd41` (ver "Base de paridad") |
| Protocolo remoto | G1 v1 aprobado: [decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md) |
| Política de acceso | Paridad, por el mismo criterio que [T05](../../registro/decisiones/2026-11-10-2785-t05-programas-acceso-actual.md) |
| Estado | Contrato ejecutable, condicionado a la base de paridad; nada implementado ni ejecutado |

Este documento reemplaza, para O05, la descomposición propuesta del catálogo. Las
familias O01–O04 están en
[convenio, documentos, firmantes y rendiciones](2026-11-10-2785-organizaciones-convenio-documentos-firmantes-rendiciones-m2.md).
Ambos documentos comparten la base de paridad, la API y los riesgos comunes que se
describen acá.

## Base de paridad (evidencia integrada refrescada)

El catálogo pide "refrescar evidencia integrada antes de implementar" (#2775). Al
refrescarla apareció una diferencia que condiciona toda la familia O:

- El PR #2775 (#2745 etapas 1–3: programas, proyectos con línea, convenio por
  proyecto, programa del firmante y baja bloqueada) **está en HEAD**.
- El PR #2836 (#2745 etapas 4, 5 y 7: legajo por programa "B v3", regla
  comedor-organización, migración `0005_region_desde_issue_2642`) **se fusionó en
  `development` el 2026-11-03 pero no está en HEAD**. La base de Migracion-2 es
  `development` del 2026-10-27 (`13d367f81`, 286 commits detrás de
  `origin/development` leído el 2026-11-06).
- #2836 reescribe `OrganizacionDetailView`, `organizacion_detail.html` (11 partials
  nuevos en `templates/organizaciones/partials/legajo/`), `organizacion_form.html`,
  el retorno de `ConvenioProyectoView`, la respuesta de
  `proyectos_organizacion_ajax`, agrega `services/legajo.py` y elimina los modelos
  `RegionAbordaje`, `SubzonaAbordaje` y `DatosRegionOrganizacion`.

**Decisión técnica:** la referencia de paridad es `development` con #2836, que es
lo que verán los usuarios. Este contrato describe esa versión y cita líneas de
`origin/development` `83d87cd41` salvo que diga "HEAD". Ninguna entrega de la
familia O se implementa sobre la base actual de Migracion-2: antes hay que traer
`development` a la rama de migración. Las líneas de HEAD se citan solo donde el
código no cambia.

## Rutas nativas

Todas en `src/backends/comedores/gestion_organizaciones/urls.py:42–212` (igual en
HEAD y en development). Los permisos se aplican con
`permissions_any_required` (alcanza con uno). Constantes:

- `ORGANIZACION_DOCUMENTACION_PERMS` = `organizaciones.view_organizacion`,
  `auth.role_tecnico_comedor`, `auth.role_abogado_dupla` (`urls.py:31–35`).
- `ORGANIZACION_PROYECTOS_PERMS` = las anteriores + `comedores.add_comedor`,
  `comedores.change_comedor` (`urls.py:36–40`).

| Entrega | URL exacta | Nombre | Métodos | Vista (development) | Permiso de ruta | Template |
|---|---|---|---|---|---|---|
| O05.01 | `/organizaciones/listar` | `organizaciones` | GET | `views.py:405 OrganizacionListView` | DOCUMENTACION | `organizacion_list.html` |
| O05.01 | `/organizaciones/ajax/` | `organizaciones_ajax` | GET | `views.py:1452 organizaciones_ajax` | DOCUMENTACION | `organizaciones/partials/organizacion_rows.html` + `components/pagination.html` |
| O05.01 | `/organizaciones/exportar` | `organizacion_exportar` | GET | `views_export.py:12 OrganizacionExportView` | `view_organizacion` o `auth.role_exportar_a_csv` | CSV |
| O05.01 | `/organizaciones/detalle/<int:pk>` | `organizacion_detalle` | GET | `views.py:821 OrganizacionDetailView` | DOCUMENTACION | `organizacion_detail.html` + partials `legajo/*` |
| O05.02 | `/organizaciones/crear` | `organizacion_crear` | GET, POST | `views.py:618 OrganizacionCreateView` | `view_organizacion` | `organizacion_form.html` |
| O05.02 | `/organizaciones/editar/<int:pk>` | `organizacion_editar` | GET, POST | `views.py:771 OrganizacionUpdateView` | `view_organizacion` | `organizacion_form.html` |
| O05.02 | `/organizaciones/eliminar/<int:pk>` | `organizacion_eliminar` | GET, POST | `views.py:1354 OrganizacionDeleteView` | `view_organizacion` | `organizacion_confirm_delete.html` |
| O05.02 | `/organizaciones/subtipos-entidad/ajax/` | `organizacion_subtipos_entidad_ajax` | GET | `views.py:1398 sub_tipo_entidad_ajax` | `view_organizacion` | JSON |
| O05.02 | `/organizaciones/cuil-check/ajax/` | `organizacion_cuil_check_ajax` | GET | `views.py:1412 cuil_check_ajax` | `view_organizacion` | JSON |
| O05.03 | `/organizaciones/<int:organizacion_id>/proyectos/ajax/` | `organizacion_proyectos_ajax` | GET | `views.py:1505 proyectos_organizacion_ajax` | PROYECTOS | JSON |
| — | `/ajax/load-organizaciones/` | `ajax_load_organizaciones` | GET | `views.py:118 load_organizaciones` | solo `login_required` | JSON Select2 |

Notas de ruta:

- Varias URLs **no terminan en barra** (`listar`, `exportar`, `crear`,
  `editar/<pk>`, `detalle/<pk>`, `eliminar/<pk>`). React las reconoce con la misma
  forma; no se agrega ni se quita la barra.
- `ajax_load_organizaciones` y `organizacion_proyectos_ajax` los consume el
  formulario de comedor (`comedores/templates/comedor/comedor_form.html:85,512`,
  familia CO07). No cambian en esta familia.
- `organizacion_subtipos_entidad_ajax` lo consume
  `static/custom/js/organizacionesform.js:77` con la URL escrita a mano.
- No hay endpoint nativo propio de programas ni de proyectos: se escriben dentro
  del POST de crear/editar organización (ver O05.03).

## Permisos y alcance (paridad exacta)

- **Ver todo** (`_puede_ver_todas_las_organizaciones`, `views.py:141–144`):
  superusuario o `organizaciones.view_organizacion`.
- **Alcance de dupla** (`_filtrar_organizaciones_por_dupla`, `views.py:147–154`):
  quien no ve todo solo ve organizaciones con algún comedor cuya dupla lo tenga como
  `abogado` o `tecnico`, con `distinct()`. Lo aplican listado, ajax del listado,
  detalle, historial, documentación adicional y proyectos ajax.
- **Sin alcance de objeto**: crear, editar, eliminar, subtipos y cuil-check solo
  exigen `view_organizacion` en la ruta y `LoginRequiredMixin`; sus querysets son
  globales. La exportación tampoco filtra por dupla.
- **Botones**: `puede_crear_organizacion` y `puede_gestionar_organizaciones` valen
  lo mismo que "ver todo" (`views.py:429–434`); sin eso, el listado muestra solo
  "Ver" y el legajo oculta Editar, Eliminar, altas y ediciones de firmantes, avales,
  proyectos, región y convenios.
- **Historial de auditoría** del encabezado: visible con
  `perms.auditlog.view_logentry` (`organizacion_detail.html:557–560`).
- **Exportar**: la ruta acepta `view_organizacion` **o** `role_exportar_a_csv`, y
  además `CSVExportMixin.check_export_permission` (`kernel/core/mixins.py:22–32`)
  exige superusuario o `auth.role_exportar_a_csv`. En la práctica: superusuario o
  `role_exportar_a_csv`; `view_organizacion` solo no alcanza.

**Decisión técnica (paridad):** la API web reproduce estas reglas sin endurecerlas,
como se decidió para T05. Las brechas conocidas (ABM sin alcance de objeto,
exportación sin alcance de dupla, `load_organizaciones` sin permiso) se documentan en
"Riesgos" y se corrigen en otro trabajo que cubra a la vez Django y la API web.

## O05.01: listado, exportación y legajo [L]

### Listado

- Queryset: `_build_organizacion_list_queryset(busqueda, user, request)`
  (`views.py:157–173`). Orden `-id`. Búsqueda simple `busqueda` (`views.py:104–115`):
  si son solo dígitos, igualdad exacta con `cuit`, `telefono` o `pk`; si no,
  `icontains` en `nombre` o `email`. Filtros combinables por el parámetro JSON
  `filters` con `ORGANIZACION_ADVANCED_FILTER` (`filter_config.py:16–136`): campos
  región, subzona, nombre, sigla, CUIT, teléfono, email, tipo y subtipo de entidad,
  domicilio, partido, provincia/municipio/localidad (por nombre), espacio
  comunitario, código de proyecto, sin vencimiento, fecha de vencimiento, fecha de
  creación e ID; operadores por tipo `TEXT_OPS`, `NUM_OPS`, `CHOICE_OPS`,
  `BOOL_OPS`, `DATE_OPS`. `distinct()` solo cuando hay filtro.
- Paginación: 10 por página con `NoCountPaginator` sobre PKs e hidratación
  (`views.py:416–423`, `kernel/core/pagination.py:39,99`); el paginador no cuenta
  filas y arma el rango con `build_no_count_page_range`. Textos de paginación
  "Volver" y "Continuar".
- Columnas y orden visual (`organizacion_list.html:20–51`): CUIT, Nombre, Comedores,
  Tipo de entidad, Subtipo de entidad, Teléfono, Email, Acciones. Nulos se muestran
  "-"; `comedores_count` 0. Fila vacía: "No hay organizaciones disponibles.".
- Acciones por fila (`organizacion_rows.html`): "Ver" siempre; "Editar" y
  "Eliminar" solo con `puede_gestionar_organizaciones`.
- Barra de búsqueda: título "Buscar Organización", botón "Agregar" solo con
  `puede_crear_organizacion`, filtros avanzados y botón de exportar.
- El orden por columna (`listSort.js`) es del lado del cliente sobre la página
  visible; el CSV es el único que ordena en servidor.

### Exportación

`views_export.py:12–71`. Nombre `exportacion_organizaciones_<AAAAMMDD_HHMM>.csv`
(`CSVExportMixin.get_export_filename`). Columnas: "CUIT", "Nombre", "Comedores",
"Tipo de Entidad", "Subtipo de Entidad", "Teléfono", "Email". Misma búsqueda y
filtros que el listado, **sin** alcance de dupla. Orden `sort`/`direction` con lista
blanca (`cuit`, `nombre`, `comedores`, `tipo_entidad`, `subtipo_entidad`,
`telefono`, `email`); sin `sort`, `-id`.

**Decisión técnica:** la exportación sigue siendo la URL nativa. React arma el
enlace `/organizaciones/exportar?<mismos parámetros>` y deja que el navegador
descargue. No se crea endpoint JSON de exportación.

### Legajo (detalle)

Queryset con alcance de dupla (`views.py:826–829`); objeto ajeno o inexistente: 404.
Contexto: `datos_legajo(organizacion, request.GET)` (`services/legajo.py:209–276`)
más avales y permisos (`views.py:831–922`). Parámetros de URL:

- `programa=<id>`: programa de la organización; inválido o ausente, el primero en
  orden del legajo (Alimentar, Secos, Tradicional, resto). Sin `programa`, un
  `proyecto` con línea elige esa línea (`legajo.py:60–84`).
- `seccion=info|rendiciones`: inválida o ausente, `rendiciones` si hay `proyecto`
  en la URL y si no `info` (`legajo.py:223–225`).
- `proyecto=<código>`: filtro de rendiciones, validado contra
  `RendicionesOrganizacionService.obtener_proyectos`.

Secciones en orden (`organizacion_detail.html:549–889`):

1. Encabezado: nombre, "CUIT: …" (o "Sin información"), tipo/subtipo, botones
   Historial, Editar, Eliminar según permisos.
2. Selector "Programa": enlaces `?programa=<id>` si hay más de uno; chip con el
   nombre si hay uno; chip "Sin programas" si no hay.
3. "Datos de la Organización" con chip "Común a todos los programas": Nombre, CUIT,
   Tipo y Subtipo de Entidad, Teléfono, Email, Programas, Comedores asociados,
   Provincia, Municipio, Localidad, Partido, Domicilio, Fecha de Vencimiento
   (con insignia "Vigente"/"Vencido" o "Sin vencimiento"), Fecha de Creación.
4. "Avales" solo si el tipo de entidad es exactamente "Asociación de hecho"
   (`views.py`, contexto `avales`) — contrato en O03.
5. Sin programas: aviso "Sin programas asignados" con "Cargar programas"
   (`#section-programas`) y, si corresponde, región, proyectos y rendiciones
   generales.
6. Con programa: franja, pestañas "Información del programa" y "Rendiciones
   Presentadas (N)" (solo Abordaje), aviso de proyectos sin línea con "Asignar
   línea", Datos de Región, Proyectos, Datos de Convenio (O01), Firmantes (O03),
   Espacios o Comedores Asociados.
7. Documentación de la Organización si `muestra_documentacion` (O02).
8. Bloque "Sin programa asignado" (`legajo/sin_programa.html`).
9. Rendiciones (O04).

**Composición en React:** O05.01 es dueño del marco del legajo, del encabezado, del
selector de programa, de Datos de la Organización, de región, proyectos y comedores.
Las secciones de convenio, documentación, firmantes/avales y rendiciones son
componentes de O01, O02, O03 y O04 que reciben su parte del mismo DTO. Así cuatro
escritores pueden trabajar en paralelo sobre archivos distintos.

## O05.02: alta, edición y baja de organización [M]

### Formulario `OrganizacionForm` (`forms.py:41–572`)

`ModelForm` con `fields = "__all__"` sobre `kernel/organizaciones/models.py:124–193`.

| Campo | Tipo y regla | Fuente |
|---|---|---|
| `nombre` | requerido, máx. 255 | modelo |
| `sigla` | opcional, máx. 30 | modelo |
| `cuit` | opcional; `^[0-9]{11}$` sin espacios; error "Ingresá un CUIT de 11 dígitos, solo con números y sin espacios."; se guarda como entero | `forms.py:60–75`, `clean_cuit` |
| `cuil_duplicado_confirmado`, `cuil_duplicado_confirmado_valor` | ocultos; si otro registro tiene el mismo CUIT y no se confirmó **ese** valor: error en `cuit` "El CUIL ingresado ya está registrado en otra organización. Revisá la advertencia y confirmá para continuar." (código `cuil_duplicado_sin_confirmar`) | `clean` |
| `telefono` | entero opcional | modelo |
| `email` | email opcional | modelo |
| `domicilio`, `partido` | opcional, máx. 255 | modelo |
| `provincia` | FK; queryset todas | `popular_campos_ubicacion` |
| `municipio` | FK opcional; queryset de la provincia elegida o vacío | idem |
| `localidad` | FK opcional; queryset del municipio elegido | idem |
| `tipo_entidad` | FK opcional | modelo |
| `subtipo_entidad` | FK opcional; subtipos activos más el actual | `__init__` |
| `fecha_vencimiento` | fecha `AAAA-MM-DD`, no requerida por campo; error "Ingresá una fecha o seleccioná Sin Vencimiento." si falta y `sin_vencimiento` es falso; con `sin_vencimiento` se guarda nula | `__init__`, `clean` |
| `sin_vencimiento` | booleano | modelo |
| `region_abordaje`, `subzona_abordaje` | FK opcionales; activas más la actual; subzona limitada a la región elegida | `_configurar_subzonas` |
| `territoriales_abordaje_comunitario` | múltiple; usuarios territoriales PNUD más los ya asignados; error global "Para asignar un nuevo Territorial debés seleccionar también su Código de Proyecto." | `_configurar_territoriales`, `clean` |
| `fecha_creacion` | `auto_now_add`, no editable | modelo |
| `programas`, `proyectos_lineas`, `asignaciones_territoriales`, `quitar_territoriales_sin_proyecto` | ver O05.03 | — |

React no genera el esquema desde el modelo: el backend construye el `Form` real
(instancia, datos) y proyecta solo campos, opciones, iniciales y errores
(misma regla que AD02). Validación y guardado siguen en el `Form`.

### Comportamiento visible del formulario

- Botones "Cancelar" (historial atrás) y "Guardar organización"
  (`organizacion_form.html:367–372`).
- CUIT: el cliente deja solo dígitos (máx. 11); con 11 dígitos consulta
  cuil-check tras 400 ms; si hay coincidencias muestra "Este CUIT ya está registrado
  en las siguientes organizaciones:" con tabla (Nombre, Tipo de entidad, Subtipo,
  Teléfono, Email, Domicilio, Provincia, Municipio, Localidad), casilla "Revisé la
  información y confirmo la creación del nuevo registro" y deshabilita guardar hasta
  confirmar. En edición consulta al cargar.
- Cambio de Tipo de Entidad en edición: aviso y modal "Confirmar cambio de Tipo de
  Entidad" con "Cancelar"/"Confirmar cambio" (`organizacion_form.html:383–415`).
- Subtipos: al cambiar tipo, consulta subtipos activos del tipo.

### Efectos

| Acción | Efecto en datos | Resultado |
|---|---|---|
| Crear válido | `form.save()` en transacción (`forms.py:491–505`): organización, programas, proyectos, territoriales | 302 a `/organizaciones/detalle/<pk>`; sin mensaje |
| Crear/editar inválido | nada | 200 con errores por campo y globales |
| Editar válido sin cambio de tipo | `form.save()` | 302 a `/organizaciones/detalle/<pk>`; sin mensaje |
| Editar con cambio de `tipo_entidad` | después de guardar: `AdmisionService.congelar_documentacion_organizacional` por cada admisión de comedores de la organización con `enviada_a_archivo=False`; luego **baja lógica** en cascada de todos los `ArchivoOrganizacion` de la organización (`SoftDeleteQuerySet.delete`, sin usuario) | 302 al legajo con aviso warning "Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad." (`views.py:785–815`) |
| Baja GET | vista previa de cascada (`SoftDeleteDeleteViewMixin`, `delete_confirm.html`): título y botón "Dar de baja Organización", total de afectados y desglose | 200 |
| Baja POST con proyectos | nada; mensaje error de `motivo_que_impide_baja` ("No se puede dar de baja la organización: tiene N proyecto(s) (…). Darla de baja borraría esos proyectos y sus datos.") | 200 con la misma confirmación (`views.py:1361–1368`, `services/programas.py:165–200`) |
| Baja POST sin proyectos | `delete(user, cascade=True)` lógica | 302 a `/organizaciones/listar` con "La organización {nombre} fue dada de baja correctamente." |
| Baja con `ValidationError` | nada | 200, mensaje de la excepción |
| Baja con `ProtectedError` | nada | 200, "No se puede dar de baja la organización porque tiene datos asociados que no se pueden borrar." |

El `success_message` "Organización dada de baja correctamente." de la clase no se
usa porque `post` está sobrescrito; React muestra el texto con el nombre.

## O05.03: programas y proyectos [M]

No tiene vista propia: son campos del mismo `OrganizacionForm`.

| Campo | Regla | Fuente |
|---|---|---|
| `programas` | múltiple opcional; opciones = Alimentar, Secos, Tradicional más los ya asignados; no se puede quitar uno con datos asociados: "No se puede quitar {programa}: tiene {n} {clave} asociados." (cuenta también dados de baja) | `forms.py:141–152,412–427`, `services/programas.py:133–162` |
| `proyectos_lineas` | JSON oculto `[{"codigo","linea"}]`; códigos vacíos se ignoran, duplicados se unifican, orden por código; máx. 255 ("El código {…}… supera los 255 caracteres."); JSON inválido "No se pudo leer la lista de proyectos."; línea no entera "La línea del proyecto {codigo} no es válida." | `clean_proyectos_lineas` |
| reglas de línea | línea fuera de Secos/Tradicional; con programas cargados: sin programa de Abordaje "El proyecto {codigo} necesita una línea de Abordaje Comunitario: elegí el programa o quitá el proyecto.", sin línea "Elegí la línea del proyecto {codigo}.", línea no elegida "La línea del proyecto {codigo} no está entre los programas elegidos."; convenio con imprevistos que pasa a Secos "El convenio del proyecto {codigo} tiene Imprevistos, que solo aplica a Línea Tradicional."; sin programas no se exige línea | `_validar_lineas_proyecto` |
| `asignaciones_territoriales` | JSON `[{"proyecto","territorial"}]`; proyecto debe estar en la lista ("Seleccioná un código de proyecto de esta organización."); territorial entero permitido ("Seleccioná un territorial válido para cada proyecto."); pares duplicados se unifican | `clean_asignaciones_territoriales` |
| `quitar_territoriales_sin_proyecto` | múltiple de asignaciones generales existentes | `_configurar_territoriales` |

Guardado (`forms.py:491–572`):

- Programas: alta de `ProgramaOrganizacion` nuevos; baja **física** de los quitados
  (solo llegan sin datos; queda en auditoría).
- Proyectos: los que no vienen se **desactivan** (`activo=False`), conservando línea
  y convenio; los que vienen se crean o reactivan; la línea se crea o se cambia.
- Territoriales: solo si `asignaciones_territoriales` **está presente** en el POST
  ("formato nuevo"): se reemplazan los territoriales de cada proyecto y se quitan de
  la asignación general los asociados y los marcados para quitar. Sin la clave, las
  asignaciones históricas no se tocan.
- En development el cliente propone la línea anterior de un proyecto quitado y
  vuelto a agregar (`lineas_de_proyectos_quitados`, `forms.py:203–214`) y rechaza
  códigos con coma solo en el cliente ("El código no puede tener comas.").

**Decisión técnica:** O05.02 y O05.03 se implementan como **una sola unidad** con un
solo POST. Motivo: el `Form` trata la ausencia de `programas` y `proyectos_lineas`
como lista vacía; un formulario React que omitiera esos campos quitaría programas y
desactivaría todos los proyectos. La API exige ambos campos en crear y editar
(400 si faltan) y el cliente envía siempre `asignaciones_territoriales`.

Proyectos ajax (development `views.py:1505–1536`): organizaciones con alcance de
dupla, proyectos activos, filtro opcional `programa`; respuesta
`{"proyectos":[{"id","codigo","nombre","linea"}],"programas":[ids]}`. Consumidor
nativo: formulario de comedor (CO07); se conserva sin cambios.

## API web propuesta (`/api/web/comedores/organizaciones/`)

Común a O01–O05:

- Prefijo `api/web/comedores/` agregado a `url_prefixes` de `comedores` en
  `src/backends/config/backends.json`; regenerar `src/backends/config/url_registry.json`
  con `generar_registro_urls`, sin editarlo a mano.
- Vistas DRF con `WebGatePermission` (`kernel/core/web_gate.py:308`) seguido de los
  mismos permisos de ruta (`permissions_any_required` equivalente) y del mismo
  alcance de objeto. Archivo nuevo `gestion_organizaciones/web_api_views.py` y
  `web_api_urls.py`, incluidos en el URLconf del runtime y del monolito. Si el piloto
  de Inspecciones (primera entrega vertical G1, en curso) fija otra ubicación,
  se adopta la suya.
- POST `application/x-www-form-urlencoded` (multipart solo para archivos), CSRF de
  Django, `Cache-Control: private, no-store`. Errores de G1: 401/403 JSON del core,
  503 antes del envío, 504 con `uncertain: true` en métodos no seguros. **Nunca hay
  reintento automático**; ante 504 incierto React recarga el recurso y muestra el
  estado real.
- Errores de formulario: 400 `{"errors": {campo: [mensajes]}, "non_field_errors": [...]}`
  con los mismos textos de Django. Sin permiso de ruta: 403. Objeto fuera de
  alcance o inexistente: 404.

| Método | Ruta | Reutiliza | Respuesta |
|---|---|---|---|
| GET | `organizaciones/?busqueda=&filters=&page=` | `_build_organizacion_list_queryset`, `NoCountPaginator`, `_hydrate_organizaciones_page`, `get_filters_ui_config` | 200 `{results:[{id,cuit,nombre,comedores_count,tipo_entidad,subtipo_entidad,telefono,email}], page:{number,has_previous,has_next,page_range}, capabilities:{puede_crear,puede_gestionar,puede_exportar}, filters_config}` |
| GET | `organizaciones/<pk>/?programa=&seccion=&proyecto=` | `OrganizacionDetailView.get_queryset`, `datos_legajo` | 200 DTO del legajo con secciones `datos`, `programas`, `region`, `proyectos`, `convenios` (O01), `documentacion` (O02), `firmantes`/`avales`/`sin_programa` (O03), `rendiciones` (O04), `capabilities` |
| GET | `organizaciones/formulario/` y `organizaciones/<pk>/formulario/` | `OrganizacionForm` (incl. `datos_formulario`) | 200 campos, opciones, iniciales, avisos |
| POST | `organizaciones/` | `OrganizacionCreateView.form_valid` | 201 `{id, redirect:"/organizaciones/detalle/<id>"}` / 400 |
| POST | `organizaciones/<pk>/` | `OrganizacionUpdateView.form_valid` (mismo bloque de cambio de tipo) | 200 `{redirect, messages}` / 400 |
| GET | `organizaciones/<pk>/baja/` | `build_delete_preview`, `motivo_que_impide_baja` | 200 `{nombre, cascade_preview, motivo}` |
| POST | `organizaciones/<pk>/baja/` | `OrganizacionDeleteView.post` | 200 `{redirect:"/organizaciones/listar", messages}`; 409 `{error}` con el motivo, el texto de `ProtectedError` o de `ValidationError` |
| GET | `organizaciones/subtipos/?tipo_entidad=` | `sub_tipo_entidad_ajax` | 200 `[{id,text}]` |
| GET | `organizaciones/cuil/?cuil=&exclude=` | `cuil_check_ajax` | 200 `{organizaciones:[…]}` (mismos campos) |
| GET | `organizaciones/<pk>/proyectos/?programa=` | `proyectos_organizacion_ajax` | 200 mismo shape |

Las rutas nativas no cambian; los handlers HTML y los ajax nativos se conservan para
sus consumidores. Los mensajes de Django que hoy viajan por redirect se devuelven
en `messages` con su nivel para el contenedor Toastr.

## Módulo de ruta React

`src/frontends/apps/sisoc/src/routes/organizaciones.tsx` (+ `organizaciones.test.tsx`),
registrado en `routes/index.ts` antes de `businessRoute`. Reconoce
`/organizaciones/listar`, `/organizaciones/crear`, `/organizaciones/editar/<pk>`,
`/organizaciones/detalle/<pk>` y `/organizaciones/eliminar/<pk>` con los slashes
nativos. El botón Volver del marco usa el destino nativo de cada pantalla (patrón de
`6b5de569f`). Se sirve con una entrada de preview sin activar rutas globales, como
las entradas de identidad.

## Criterios de aceptación

1. El listado muestra las mismas filas, orden `-id`, 10 por página, columnas y
   textos ("No hay organizaciones disponibles.", "Volver", "Continuar") para
   superusuario, `view_organizacion`, técnico y abogado de dupla.
2. El CSV descargado desde React es idéntico byte a byte (salvo el minuto del nombre)
   al nativo con los mismos parámetros.
3. El legajo reproduce development para organización sin programas, con uno, dos y
   tres programas, programa inválido, `seccion` y `proyecto`.
4. Crear y editar producen los mismos registros (organización, `ProgramaOrganizacion`,
   proyectos, líneas, territoriales) y los mismos errores con los textos citados.
5. Cambiar el tipo de entidad congela admisiones, da de baja los archivos y muestra
   "Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.".
6. La baja con proyectos se rechaza con el texto de `motivo_que_impide_baja`; sin
   proyectos termina en el listado con "La organización {nombre} fue dada de baja
   correctamente.".
7. Regla visual S13 por pantalla, estado, rol y viewport: paridad estructural (texto,
   controles, orden de Tab, estilos clave, cada elemento a ≤2 px) y diferencia
   perceptual ≤1 % sin antialiasing; caso que falla: máximo 8 min de diagnóstico y
   pasa a la prueba humana de la ola.

## Dependencias

- Base: `development` con #2836 dentro de la rama de migración (bloqueante).
- G1 v1 integrado (`6d17843d0`) y timeouts de gunicorn (`668c61fe4`).
- O01, O02, O03 y O04 aportan secciones del legajo; O05.01 publica el DTO y el marco.
- CO07 (ficha de comedor) enlaza al legajo y consume `ajax_load_organizaciones` y
  `organizacion_proyectos_ajax`; no cambian.
- AD02/AD03: `congelar_documentacion_organizacional` se dispara desde la edición
  (`admisiones/services/admisiones_service/impl.py:3697`).
- Comunicados comparte `ORGANIZACION_ADVANCED_FILTER` (`filter_config.py` docstring);
  no se modifica.

## Riesgos

- Formulario parcial que borra programas o desactiva proyectos (mitigado por la
  unidad única y el 400 ante campos faltantes).
- Efecto destructivo del cambio de tipo: baja de toda la documentación y congelado
  de admisiones en un solo POST; ante 504 incierto no se reintenta.
- La baja lógica de la organización no llega a proyectos (sin baja lógica); la
  regla `motivo_que_impide_baja` es la única protección.
- Brechas de acceso conservadas por paridad: ABM con solo `view_organizacion` y sin
  alcance de objeto; exportación sin alcance de dupla; `load_organizaciones` solo con
  sesión (no se expone por la API nueva).
- El caché de 15 min de `get_filters_ui_config` hace que opciones nuevas tarden en
  verse igual que hoy.

## Casos de prueba

Backend (pytest, `gestion_organizaciones/tests/`):

- Listado API: superusuario, `view_organizacion`, técnico y abogado de dupla
  (solo sus organizaciones), sin permiso (403), anónimo (401 del gate), búsqueda
  numérica y textual, `filters` válido e inválido, página fuera de rango.
- Legajo API: objeto fuera de alcance (404), combinaciones de programas y parámetros
  iguales al contexto de `datos_legajo`.
- Crear/editar: CUIT inválido, CUIT duplicado sin y con confirmación del mismo valor,
  sin vencimiento, programas con datos, cada error de líneas y territoriales, falta
  de `programas` o `proyectos_lineas` (400), cambio de tipo con admisión abierta y
  archivada (archivos dados de baja, admisión congelada, mensaje).
- Baja: preview, con proyectos (409 y nada borrado), sin proyectos (baja lógica con
  usuario), POST sin CSRF (403).
- Regresión: cada ruta nativa responde igual que en la base (diferencial
  respuesta-a-respuesta, como en U04/U05).

Frontend (vitest): render de listado y estados vacíos, paginación, enlace de
exportación con parámetros, selector de programa, formulario con CUIT duplicado,
modal de tipo de entidad, errores 400, 409 de baja, 504 incierto sin reintento.

Visual y diferencial: pares nativo/React por URL × estado × rol × escritorio/móvil
con la regla S13; diferencial de rutas existentes con 0 diferencias fuera de las
rutas nuevas.

## Decisiones técnicas del agente

1. Paridad contra `development` con #2836, no contra HEAD: es la versión que usan
   los usuarios y la que valida el área (#2745 etapa 6).
2. Acceso igual al nativo (precedente T05), sin endurecer ni ampliar.
3. O05.02 y O05.03 en una unidad y un POST, por el riesgo de datos descrito.
4. Exportación por URL nativa; sin endpoint JSON nuevo.
5. Ajax nativos intactos; la API nueva expone sus equivalentes solo para React.
6. Esquema proyectado desde el `Form` real, sin generador desde el modelo.
7. El legajo se arma con un DTO por secciones para permitir escritores paralelos
   (O01–O05) sin tocar el mismo componente.

## Incertidumbres

- No se ejecutó nada: ni app, ni tests, ni navegador. Las líneas de development
  provienen de `origin/development` `83d87cd41` leído localmente (fetch del
  2026-11-06); si `development` avanzó, refrescar antes de implementar.
- No se verificó qué script consume `organizaciones_ajax` en el listado (se asume
  el componente de búsqueda); confirmar antes de retirar nada.
- El mapeo de roles de firmante y el texto exacto de tipos de entidad dependen del
  catálogo de datos de cada entorno.
- El comportamiento de `delete_confirm.html` con `cascade_preview` de organizaciones
  grandes no se midió.

## Fuente

`origin/development` `83d87cd41` salvo indicación:
`src/backends/comedores/gestion_organizaciones/urls.py:31–212`;
`views.py:91–173,405–438,618–637,771–922,1354–1536`;
`views_export.py:12–71`; `forms.py:41–572`; `filter_config.py:16–136`;
`services/programas.py:133–224`; `services/legajo.py:1–276`;
`templates/organizacion_list.html`, `organizaciones/partials/organizacion_rows.html`,
`organizacion_form.html:1–415,625–692`, `organizacion_detail.html:549–889`,
`organizacion_confirm_delete.html`, `organizaciones/partials/legajo/*.html`;
`src/backends/kernel/organizaciones/models.py:124–340` (HEAD = development);
`src/backends/kernel/core/soft_delete/view_helpers.py:90–117` y `base.py:23–60`;
`src/backends/kernel/core/mixins.py:13–40`; `src/backends/kernel/core/pagination.py:39,99`;
`src/backends/kernel/templates/components/delete_confirm.html`;
`src/backends/config/backends.json` (prefijos de `comedores`).
Plan origen: [#2745](2026-10-20-2745-legajo-organizacion-por-programa.md). Estado de
#2836 leído con `gh pr view 2836` (MERGED).
