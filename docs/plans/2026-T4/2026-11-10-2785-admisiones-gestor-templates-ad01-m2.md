# AD01: gestor de templates de informes técnicos (contrato M2 ejecutable)

| Dato | Valor |
|---|---|
| Fecha | 2026-11-10 |
| Base contrastada | HEAD `4ea95bcbe` (el código de `src/backends/comedores/` del worktree coincide con HEAD) |
| Runtime dueño | `comedores` (app `admisiones`), servicio `backend_comedores` |
| Transporte | G1 v1 aprobado: [protocolo G1 v1](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md) |
| Entregas | AD01.01 consulta [L], AD01.02 editor y operaciones [M], AD01.03 vista previa y documento backend [F] |
| Consumidores | AD02 (generación del DOCX del Informe Técnico) y AD03 (reporte de configuración faltante) |

Este contrato reemplaza la descomposición propuesta del catálogo para AD01. Cada
afirmación remite a código leído; lo que no se pudo confirmar se marca en
"Incertidumbres". La regla es paridad con el comportamiento nativo actual.

## 1. Rutas nativas

Todas las rutas viven en `src/backends/comedores/admisiones/urls/web_urls.py:46–137`,
montadas sin prefijo por `admisiones/urls.py:4` y `comedores_runtime/urls.py:12`.
Todas pasan por dos guardas idénticas (ver §2).

| URL nativa exacta | Nombre | Métodos | Vista (`views/templates_informe_tecnico.py`) | Template (`templates/admisiones/templates_informes_tecnicos/`) | Entrega |
|---|---|---|---|---|---|
| `/comedores/configuracion/templates/` | `gestor_templates_listar` | GET | `PlantillaInformeTecnicoListView` :42 | `list.html` | AD01.01 |
| `/comedores/configuracion/templates/crear/` | `gestor_templates_crear` | GET, POST | `PlantillaInformeTecnicoCreateView` :147 | `form.html` | AD01.02 |
| `/comedores/configuracion/templates/incidencias/` | `gestor_templates_incidencias_listar` | GET | `IncidenciaTemplateInformeTecnicoListView` :386 | `incidencias_list.html` | AD01.01 |
| `/comedores/configuracion/templates/incidencias/<pk>/` | `gestor_templates_incidencia_detalle` | GET (AD01.01), POST (AD01.02) | `IncidenciaTemplateInformeTecnicoDetailView` :421 | `incidencia_detail.html` | AD01.01/02 |
| `/comedores/configuracion/templates/variables/` | `gestor_templates_variables_listar` | GET | `VariableTemplateInformeTecnicoListView` :274 | `variables_list.html` | AD01.01 |
| `/comedores/configuracion/templates/variables/<pk>/alternar/` | `gestor_templates_variables_alternar` | POST | `VariableTemplateInformeTecnicoToggleView` :304 | redirección | AD01.02 |
| `/comedores/configuracion/templates/<pk>/` | `gestor_templates_detalle` | GET | `PlantillaInformeTecnicoDetailView` :164 | `detail.html` | AD01.01 |
| `/comedores/configuracion/templates/<plantilla_pk>/versiones/crear/` | `gestor_templates_version_crear` | POST | `PlantillaInformeTecnicoVersionCreateView` :189 | redirección | AD01.02 |
| `/comedores/configuracion/templates/<plantilla_pk>/versiones/<version_pk>/editar/` | `gestor_templates_version_editar` | GET, POST | `PlantillaInformeTecnicoVersionUpdateView` :236 | `version_form.html` | AD01.02 |
| `/comedores/configuracion/templates/<plantilla_pk>/versiones/<version_pk>/descartar/` | `gestor_templates_version_descartar` | POST | `PlantillaInformeTecnicoVersionDiscardView` :218 | redirección | AD01.02 |
| `/comedores/configuracion/templates/<plantilla_pk>/versiones/<version_pk>/previsualizar/` | `gestor_templates_version_previsualizar` | GET | `PlantillaInformeTecnicoVersionPreviewView` :314 | DOCX adjunto | AD01.03 |
| `/comedores/configuracion/templates/<plantilla_pk>/versiones/<version_pk>/publicar/` | `gestor_templates_version_publicar` | POST | `PlantillaInformeTecnicoVersionPublishView` :355 | redirección | AD01.02 |
| `/comedores/configuracion/templates/<pk>/inactivar/` | `gestor_templates_inactivar` | POST | `PlantillaInformeTecnicoDeactivateView` :372 | redirección | AD01.02 |

Las vistas basadas en `View` solo definen `post` (o `get` en la vista previa):
otro método responde 405. Todas las pantallas incluyen la navegación
`includes/navigation.html` (Templates, Variables documentales, Incidencias) y la
hoja `custom/css/gestor_templates.css`.

Consumidor indirecto fuera del gestor (AD03, no se migra acá):
`/comedores/admisiones/<pk>/templates/reportar-faltante/`
(`admisiones_reportar_configuracion_faltante_template`, `web_urls.py:224–228`,
`views/web_views.py:380–413`) crea los casos que el buzón de incidencias muestra.

## 2. Permisos y alcance

- Doble guarda, igual en todas las rutas: el decorador
  `permissions_any_required(["admisiones.gestionar_templates_informe_tecnico"])`
  (`kernel/core/decorators.py:35–47`, levanta `PermissionDenied`) y el mixin
  `GestorTemplatesPermissionMixin` (`LoginRequiredMixin` + `UserPassesTestMixin`,
  `raise_exception = True`, `user_has_permission_code`, vista :32–39).
- Superusuario pasa siempre (`kernel/iam/services.py:90–97`).
- Grupo sembrado: «Gestor de templates» con ese único permiso
  (`kernel/users/bootstrap/groups_seed.py:466–468`). El menú lo agrupa en
  configuración (`sisoc_core/usuarios/web_navigation.py:34–41`, sidebar
  `kernel/templates/includes/sidebar/opciones.html:189–203`).
- No hay alcance por objeto: quien tiene el permiso ve y opera todas las
  plantillas, variables e incidencias. La vista previa acepta el ID de cualquier
  `InformeTecnico` sin filtrar por comedor, dupla ni territorio (vista :333–336).
  Se conserva (paridad); ver riesgo R3.
- La API nueva repite exactamente esa guarda (permiso de código, sin scope) después
  de `WebGatePermission`.

## 3. Modelo y máquina de estados que consume AD02

Fuente: `models/admisiones.py:1563–1960`, servicio
`services/templates_informe_tecnico_service/impl.py`.

- **Plantilla lógica** (`PlantillaInformeTecnico`): estados `activa`, `inactiva`,
  `eliminada` («Eliminada lógicamente»). Las condiciones identifican una
  combinación y no se editan después de crearla. `codigo` se genera `IT-%06d` al
  guardar (:1730–1734). La clave de combinación (`clave_condiciones`, :1690–1727)
  es `incorporacion|convenio:<id>|ex_pnud:<v>|estado_pnud:<v o ->` o
  `renovacion|convenio:<id>|renovacion:<v>|financiamiento:<v>|informe_complementario:<v>`.
- **Versión** (`PlantillaInformeTecnicoVersion`): `borrador`, `publicada`,
  `inactiva`, `eliminada`; única por (`plantilla`, `numero`), orden `-numero`.
- **Publicación** (`PlantillaInformeTecnicoPublicacion`): una fila por combinación
  (`clave_condiciones` único), `OneToOne` con la plantilla (`publicacion_vigente`) y
  con la versión (`PROTECT`). Es el índice que evita dos publicaciones simultáneas
  en MySQL.

Transiciones (solo por el servicio; React nunca cambia un estado directamente):

| Operación | Precondición | Efecto |
|---|---|---|
| Crear plantilla | Form válido + `full_clean` | Plantilla `activa` + versión 1 `borrador` vacía |
| Crear versión | Plantilla no `eliminada` | Si ya hay borrador, lo devuelve; si no, `max(numero)+1` copiando contenido y observaciones del origen |
| Guardar borrador | Versión `borrador` | Actualiza `contenido_html` (saneado) y `observaciones`; toca `modificado_por` de la plantilla |
| Descartar borrador | Versión `borrador` | **Borrado físico** de la versión (`version.delete()`, servicio :441) |
| Publicar | Plantilla `activa`, versión `borrador`, contenido no vacío, variables activas, sin otra plantilla publicada en la combinación | Versión publicada anterior pasa a `inactiva`; la nueva a `publicada` con `publicado`/`publicado_por`; crea o actualiza la fila de publicación |
| Inactivar plantilla | Plantilla `activa` | Versión publicada a `inactiva`, **borra físicamente la fila de publicación**, plantilla `inactiva` |

Consumo por AD02 (no se modifica en AD01):
`PlantillaInformeTecnicoService.resolver_publicacion_para_admision` (:56–115)
busca por clave la publicación con `plantilla__estado="activa"` y
`version__estado="publicada"`; sin publicación devuelve el mensaje
«No existe una versión publicada de template para la combinación de esta admisión.»,
que AD02 trata como guardado en borrador (`informes_service/impl.py:1309–1318`).
`InformeService.generar_docx_borrador` (:1618–1660) llama a
`generar_docx_con_version_publicada(informe, publicacion.version)` (:1005–1039) y
fija en `InformeTecnicoPDF` la plantilla y la versión usadas
(`plantilla_informe_tecnico`, `version_plantilla_informe_tecnico`, `SET_NULL`,
modelo :1192–1206). Por eso una versión ya usada nunca se borra: solo se borra un
borrador, y un borrador no se puede haber usado para generar.

Riesgo de catálogo: «templates que generan documentos quedan Django, no borrar
por nombre». Se cumple así: la generación DOCX (`Engine(debug=False, builtins=[],
libraries={})`, autoescape) y la marca de agua de vista previa quedan en el
backend; React no renderiza, no guarda ni borra plantillas por nombre o código.
Los templates Django de `templates/admisiones/docx/` y `pdf/` no se tocan.

## 4. AD01.01 Consulta

### 4.1 Listado de plantillas

- Paginación 50 (`paginate_by`, :45), parámetro `page`; orden fijo `codigo`.
- `estado`: por defecto `activa`; filtra si es `activa`, `inactiva` o `eliminada`;
  cualquier otro valor (la UI usa `todas`) no filtra (:48–55). Botones «Activas»,
  «Inactivas», «Todas». No hay botón para `eliminada`, pero `?estado=eliminada`
  funciona y se conserva.
- `q`: `icontains` sobre `nombre` o `codigo` (:56–60). Placeholder
  «Buscar por código o nombre», botón «Buscar».
- Filtros por choice válidos del modelo (valor inválido se ignora en silencio,
  :99–101): `tipo_admision`, `es_ex_pnud`, `estado_convenio_pnud`,
  `tipo_renovacion`, `estado_financiamiento`,
  `informe_complementario_modifica_prestaciones`. `tipo_convenio` solo si es
  dígito (:103–104), con opciones `TipoConvenio` ordenadas por `nombre` (todas, no
  solo las tres del formulario).
- En la UI, «Ex PNUD» y «Estado convenio PNUD» se ocultan si el tipo elegido es
  renovación, y «Renovación que tramita» / «Estado del financiamiento» si es
  incorporación (script de `list.html`). El select del informe complementario
  queda fuera de esos grupos y siempre visible, con opción vacía
  «Informe complementario: todos». Botones «Aplicar filtros» y «Limpiar».
- Columnas: Código, Nombre (+ descripción truncada a 85), Combinación
  (`Tipo · Convenio · Ex PNUD: … · PNUD: …` o
  `Tipo · Renovación · Financiamiento · Informe complementario: …`), Versión vigente
  («v<n> publicada» o «Sin versión publicada»), Estado, acción «Gestionar».
- Vacío: «No hay templates para este filtro» / «Podés crear una nueva combinación
  o cambiar los filtros de búsqueda.» con acción «Crear template».
- Paginador `components/pagination.html` con textos «Volver» y «Continuar».

### 4.2 Detalle de plantilla

- `get_object_or_404` por `pk` sobre todas las plantillas (cualquier estado).
- Contexto (:176–186): `borrador_actual` = primer borrador del prefetch (orden
  `-numero`); `versiones_historial` = las no borrador.
- Botón «Crear nueva versión» solo si no hay borrador y la plantilla está activa.
  Botón «Inactivar template» solo si activa.
- Bloque «Versión en preparación» (v<n>, «Última modificación: d/m/Y H:i»):
  «Continuar editando», «Publicar versión», «Descartar versión» con confirmación
  nativa «¿Descartar la versión en preparación? Esta acción no se puede deshacer.».
- Historial: Versión, Estado, Creada, Publicada (o «—»), acción
  «Usar como punto de partida» (solo plantilla activa).
- Vacío del historial: «No hay versiones publicadas todavía».
- Sin descripción: «Configuración de condiciones y versiones de este template lógico.».

### 4.3 Variables documentales

- Paginación 100, orden `categoria, orden, nombre, codigo` (:277, :295).
- `estado`: `activas` (defecto), `inactivas`; otro valor (`todas`) no filtra.
- `q`: `icontains` en `nombre`, `codigo`, `categoria`, `descripcion`. Placeholder
  «Buscar por nombre, categoría o código».
- Columnas: Categoría, Variable (+ descripción), Código insertado (`{{ codigo }}`),
  Estado («Activa» o «Eliminada»), acción «Eliminar» / «Activar».
- Vacío: «No se encontraron variables» / «Probá con otra búsqueda o cambiá el
  filtro de estado.».
- El template nativo **no incluye paginador**: con más de 100 variables, las
  siguientes no son navegables desde la UI (sí con `?page=2`). Ver bug B2.

### 4.4 Incidencias

- Listado: paginación 50, orden del modelo `-ultima_fecha, -id`; `estado` por
  defecto `pendiente`, filtra si es un estado válido (`pendiente`, `en_analisis`,
  `resuelta`, `descartada`), `todas` no filtra; `q` en `codigo`,
  `clave_condiciones`, `casos__comedor_nombre`, `casos__organizacion_nombre`
  con `distinct()`. Columnas: Código, Combinación (clave), Casos, Último reporte,
  Estado, acción. Vacío: «No hay incidencias para este filtro».
- Detalle: resumen (Casos agrupados, Primer y Último reporte, Incidencia anterior),
  clave, condiciones reportadas (`clave|title: descripcion` o «-»), formulario de
  gestión y tabla «Admisiones afectadas» (Admisión, Informe, Comedor,
  Organización, Reportado por, Fecha). Vacío: «No hay casos registrados».

## 5. AD01.02 Editor y operaciones

### 5.1 Formulario de plantilla (`forms/templates_informe_tecnico_forms.py:167–234`)

| Campo | Regla |
|---|---|
| `nombre` | Requerido, máx. 255 |
| `descripcion` | Opcional (texto) |
| `tipo_admision` | Requerido; choices `Admision.TIPO_ADMISION` |
| `tipo_convenio` | Requerido; queryset limitado a «Personería Jurídica», «Personería Jurídica Eclesiástica» y «Organización Base», etiquetas «Personería jurídica», «Personería jurídica eclesiástica», «Asociación de hecho»; vacío «Seleccione un tipo de convenio» |
| `es_ex_pnud` | Incorporación: requerido («Debe indicar si la admisión es Ex PNUD.») |
| `estado_convenio_pnud` | Requerido si Ex PNUD = sí («Debe indicar el estado del convenio PNUD.»); se limpia a `None` si Ex PNUD = no |
| `tipo_renovacion`, `estado_financiamiento`, `informe_complementario_modifica_prestaciones` | Renovación: requeridos («Debe indicar la renovación que tramita.», «Debe indicar el estado del financiamiento.», «Debe indicar si se realizó un Informe Complementario para modificar prestaciones.»); en incorporación se limpian a `None` |

En renovación, `clean` limpia `es_ex_pnud` y `estado_convenio_pnud`. Los mensajes
de modelo vienen de `PlantillaInformeTecnico.clean` (:1640–1688) a través de
`full_clean` en `crear_plantilla`. Ayuda visible: «Esta condición toma el tipo de
convenio registrado en la admisión. Asociación de hecho utiliza el valor existente
Organización Base.» y el aside «Antes de crear». Botón «Crear borrador».

Éxito: mensaje «Template {codigo} creado con su versión {numero} en preparación.» y
redirección a `gestor_templates_detalle`.

Incertidumbre: `crear_plantilla` llama `full_clean()` fuera del ciclo del Form; un
`ValidationError` ahí no lo atrapa la vista (:152–161). Por el `clean` del Form, los
casos conocidos ya se limpian antes; un caso residual daría 500 nativo. Ver U2.

### 5.2 Formulario de versión (:237–260)

| Campo | Regla |
|---|---|
| `contenido_html` | Opcional en borrador. Se sanea con `sanitizar_contenido_template` (:16–164): etiquetas permitidas fijas, descarta `script`, `style`, `iframe`, `svg`, etc. con su contenido; solo `style` con `text-align`, `color`, `background-color`; `href` http/https/mailto; `colspan`/`rowspan` 1–100. Conserva `{{ variable }}` |
| `observaciones` | Opcional |

El saneamiento es del backend y es la única fuente: React envía el HTML del editor y
muestra lo que el backend devuelve; no sanea por su cuenta.

Guardar: si la versión ya no es borrador, error de formulario
«Solo se pueden editar versiones en borrador.» (form inválido, :267–269). Éxito:
«Versión en preparación guardada correctamente.» y redirección al detalle. El
queryset de edición solo admite borradores de esa plantilla: otra versión da 404
(:246–252).

Panel de variables: variables activas en orden `categoria, orden, nombre, codigo`,
agrupadas por categoría con contador; búsqueda «Buscar una variable»; enlace
«Administrar catálogo» en pestaña nueva; vacío «No hay variables activas en el
catálogo.». Clic o arrastre inserta el token en el cursor.

### 5.3 Acciones

| Acción | Entrada | Efecto y mensaje nativo exacto | Redirección |
|---|---|---|---|
| Crear versión | `origen_version_id` opcional (si falta, usa la versión publicada vigente) | Plantilla inexistente: error «No se encontró el template solicitado.». Eliminada: error «No se pueden crear versiones de una plantilla eliminada.». Borrador existente: éxito «Ya existe una versión en preparación. Puede continuar editándola.». Nueva: éxito «Versión en preparación creada correctamente.» | Inexistente → listado; eliminada → detalle; resto → editor |
| Descartar | — | No borrador: error «Solo se pueden descartar versiones en preparación.». Éxito «La versión en preparación fue descartada.» (borrado físico). Versión ajena a la plantilla: 404 | Detalle |
| Publicar | — | Errores: «No se encontró la versión solicitada.», «Solo se puede publicar una plantilla lógica activa.», «Solo se pueden publicar versiones en borrador.», «Debe ingresar contenido antes de publicar la versión.», «El contenido usa variables que no están activas en el catálogo: {{ a }}, {{ b }}. Actívelas o reemplácelas antes de publicar.», «Ya existe una plantilla publicada para esta combinación: {codigo} - {nombre}.», «Otra plantilla fue publicada para esta combinación. Actualice la pantalla e intente nuevamente.». Éxitos: «La versión ya se encuentra publicada.», «Versión publicada correctamente.» | Detalle |
| Inactivar plantilla | — | Inexistente: «No se encontró el template solicitado.» (→ listado). No activa: «La plantilla ya no se encuentra activa.». Éxito «Plantilla inactivada correctamente.» | Detalle |
| Alternar variable | `next` | Invierte `activo` y guarda; éxito «Variable activada correctamente.» o «Variable inactivada correctamente.». La UI llama «Eliminar» a inactivar (baja lógica por `activo`) | `next` o listado de variables |
| Gestionar incidencia | `estado` (requerido), `plantilla` (opcional, solo activas por `codigo`), `observaciones` | Form inválido re-renderiza. Reabrir con otra abierta: «La incidencia {codigo} ya está abierta para esta combinación.» o «No se pudo reabrir la incidencia porque ya existe otra abierta para esta combinación.». Éxito «Incidencia actualizada correctamente.». Estado abierto fija `clave_abierta`; cerrado la limpia | Detalle de incidencia |

No hay borrado de plantillas desde la UI. El estado `eliminada` existe pero ninguna
ruta lo asigna.

## 6. AD01.03 Vista previa y documento backend

- GET con `informe_id`. Sin ID: error «Indique el ID del Informe Técnico para la
  vista previa.» y redirección al editor. Versión ajena a la plantilla o informe
  inexistente: 404. La vista acepta cualquier estado de versión (docstring: «incluso
  un borrador»), aunque el formulario solo aparece en el editor de borradores.
- Genera con `InformeService.generar_docx_vista_previa` (:1042–1075): reutiliza
  `generar_docx_con_version_publicada` y agrega en cada encabezado la marca
  «VISTA PREVIA — DOCUMENTO NO VÁLIDO». No persiste nada ni cambia estados.
- Falla de generación (sintaxis de template o excepción): error «No se pudo generar
  la vista previa del template.» y redirección al editor.
- Respuesta: `FileResponse` adjunto `vista-previa-{codigo}-v{numero}.docx`, tipo
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
- UI: formulario GET con `target="_blank"`, campo «ID del Informe Técnico»
  (`number`, `min=1`, requerido), botón «Descargar vista previa» y el texto
  «Probá esta versión con un Informe Técnico real. El DOCX se descarga con la marca
  de agua VISTA PREVIA — DOCUMENTO NO VÁLIDO y no se guarda en la admisión.».

## 7. API web propuesta (`/api/web/comedores/`)

Precondición común: agregar `api/web/comedores/` a `url_prefixes` de `comedores`
en `src/backends/config/backends.json` (si otra entrega del runtime no lo agregó
antes) y regenerar `src/backends/config/url_registry.json` con
`generar_registro_urls`. Vistas DRF con `WebGatePermission`
(`kernel/core/web_gate.py:308`) más una guarda de permiso de código igual a §2;
`SessionAuthentication`, CSRF, JSON, `Cache-Control: private, no-store`,
`Vary: Cookie`. POST como `application/x-www-form-urlencoded` (patrón INS-B). Sin
reintento automático; un 504 con `uncertain: true` muestra el estado incierto y
ofrece recargar, nunca reenvía.

Envolventes (patrón `sisoc_core/insumos/web_api_views.py:163–240`):
éxito `{"ok": true, "message": {"level", "text"}, "redirect": "<URL nativa>"}`;
errores de formulario 400 `{"errors": form.errors.get_json_data()}`; rechazo de
regla del servicio 409 `{"ok": false, "message": {"level": "error", "text"}, "redirect"}`
con el texto nativo exacto; objeto inexistente 404 (con el mensaje nativo cuando
la vista nativa lo tiene). `redirect` siempre es la URL nativa a la que iría la
vista Django; React navega allí y muestra el aviso con apariencia Toastr.

| Método | Ruta | Reutiliza | Respuestas |
|---|---|---|---|
| GET | `/api/web/comedores/admisiones/plantillas-informe/` | `PlantillaInformeTecnicoListView.get_queryset` y sus choices | 200 lista paginada + opciones de filtro; 401/403 |
| GET | `/api/web/comedores/admisiones/plantillas-informe/<pk>/` | `PlantillaInformeTecnicoDetailView` (queryset y contexto) | 200; 404 |
| GET, POST | `/api/web/comedores/admisiones/plantillas-informe/crear/` | `PlantillaInformeTecnicoForm` + `crear_plantilla` | GET 200 metadatos del form; POST 200 éxito / 400 |
| POST | `/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/` | `crear_version_borrador` | 200 (incluye el caso «Ya existe…»); 404; 409 eliminada |
| GET, POST | `/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/` | `PlantillaInformeTecnicoVersionForm` + `guardar_borrador`; variables activas | GET 200; POST 200 / 400; 404 si no es borrador de esa plantilla |
| POST | `/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/descartar/` | `descartar_borrador` | 200; 404; 409 |
| POST | `/api/web/comedores/admisiones/plantillas-informe/<pk>/versiones/<version_pk>/publicar/` | `publicar_version` | 200 (incluye «ya publicada»); 404 con «No se encontró la versión solicitada.»; 409 |
| POST | `/api/web/comedores/admisiones/plantillas-informe/<pk>/inactivar/` | `inactivar_plantilla` | 200; 404; 409 |
| GET | `/api/web/comedores/admisiones/plantillas-informe/variables/` | `VariableTemplateInformeTecnicoListView.get_queryset` | 200 paginado |
| POST | `/api/web/comedores/admisiones/plantillas-informe/variables/<pk>/alternar/` | misma lógica de :305–310 (extraer a servicio sin cambiar efecto) | 200; 404 |
| GET | `/api/web/comedores/admisiones/plantillas-informe/incidencias/` | `IncidenciaTemplateInformeTecnicoListView.get_queryset` | 200 paginado |
| GET, POST | `/api/web/comedores/admisiones/plantillas-informe/incidencias/<pk>/` | `IncidenciaTemplateInformeTecnicoForm` + `gestionar_incidencia` | GET 200 detalle + casos + opciones; POST 200 / 400 / 409 |

La vista previa (AD01.03) **no** tiene endpoint JSON: React envía el mismo GET
nativo a `/comedores/configuracion/templates/<p>/versiones/<v>/previsualizar/` en
pestaña nueva, como hoy. El binario sigue siendo generado y protegido por la vista
Django.

Orden de objetos en la API: la vista detalle filtra versiones por `plantilla_id`
igual que la nativa; nunca se resuelve una versión solo por su ID.

## 8. Módulo React

- `src/frontends/apps/sisoc/src/routes/gestorTemplates.tsx` (+
  `gestorTemplates.test.tsx`), registrado en `routes/index.ts` antes de
  `businessRoute`. Reconoce las URLs nativas de §1 con sus mismos slashes (las de
  solo POST no son páginas).
- Componentes de pantalla bajo `apps/sisoc/src/` con la navegación del gestor, la
  hoja `gestor_templates.css` cargada solo mientras la ruta está montada (patrón
  INS-A) y el marco del shell.
- Volver/breadcrumbs: los del template nativo («Gestor de templates» → código →
  «Editar v<n>»).

## 9. Decisiones técnicas del agente

1. **Editor enriquecido.** El editor nativo depende de jQuery 3.6.0 y
   Summernote 0.8.18 (bs4) cargados por `kernel/templates/scripts/mainscripts.html:34,75`
   y de `admisiones/static/custom/js/gestor_templates_editor.js` (IIFE que se
   engancha al DOM y sincroniza el textarea en el `submit`, :395–397). Se decide no
   agregar una dependencia npm de editor (requeriría aprobación y cambiaría el HTML
   que se guarda). La ruta del editor monta el mismo contrato de DOM
   (`[data-template-editor-source]`, `[data-template-variable]`,
   `#buscar-variable-template`, `[data-categoria-variable]`) y carga solo en esa
   ruta, en orden, las mismas URLs y versiones de jQuery, Summernote JS/CSS y el
   script nativo. El listener `submit` del script corre en el formulario antes del
   handler delegado de React, que luego envía el textarea sincronizado. Si la
   política CSP del shell o el diff visual no lo permiten dentro del tope de 8
   minutos de diagnóstico, el editor queda como página Django y React enlaza a ella
   (híbrido documentado), sin bloquear el resto de AD01.
2. **Vista previa** como GET nativo en pestaña nueva (§7): el DOCX no pasa por la
   API, no se duplica la generación y se conserva el nombre de archivo.
3. **Variable «Eliminar»**: la API conserva la semántica nativa (alterna `activo`);
   no se introduce borrado.
4. **`next` del alternado**: la API no acepta `next`; devuelve como `redirect` la
   URL del listado con la consulta actual que React envía como contexto. Evita
   reproducir la redirección abierta (B1) sin cambiar el destino observable.
5. **Mensajes** siempre del servicio (texto nativo), nunca reescritos en React.

## 10. Criterios de aceptación

1. Las 13 URLs nativas responden con la pantalla React en el entorno de preview y
   su HTML equivalente sigue intacto para el resto.
2. Sin permiso: 403 en página y API; anónimo: 401 JSON en la API
   («Inicie sesión para continuar.» del core G1) y en página el comportamiento
   nativo actual.
3. Listados: mismos filtros, defaults (`activa`, `activas`, `pendiente`), orden,
   tamaños de página (50, 100, 50) y textos vacíos de §4.
4. Cada acción de §5.3 produce el mismo efecto en base de datos y el mismo mensaje
   textual y redirección que la vista Django.
5. Guardar un HTML con `<script>` devuelve el contenido saneado igual al del Form.
6. Publicar con variable inactiva muestra exactamente
   «El contenido usa variables que no están activas en el catálogo: … Actívelas o
   reemplácelas antes de publicar.».
7. La vista previa descarga `vista-previa-<codigo>-v<n>.docx` con la marca de agua
   y no crea filas.
8. Después de publicar en React, AD02 resuelve esa versión
   (`resolver_publicacion_para_admision`) igual que tras publicar en Django.
9. Visual S13 por URL/estado/rol en desktop y móvil: paridad estructural (textos,
   controles y orden de Tab, estilos clave, cajas a ≤2 CSS px) y diff perceptual
   ≤1 % ignorando antialiasing; 8 minutos máximo de diagnóstico por caso fallido.

## 11. Dependencias

- G1 v1 integrado (hecho) y prefijo `api/web/comedores/` registrado (compartido con
  otras entregas del runtime: un solo dueño del cambio en `backends.json`).
- AD02 consume publicaciones; AD01 no cambia `resolver_publicacion_para_admision`
  ni la generación. AD03 crea incidencias; el buzón solo las lee y gestiona.
- Sin dependencia de CO07 (ficha de comedor).

## 12. Riesgos

- R1: publicación concurrente. El servicio bloquea con `select_for_update` y la
  clave única; la API debe llamar al servicio en el mismo request, sin lógica previa
  que lea y decida fuera de la transacción.
- R2: el editor depende de scripts de CDN globales; ver decisión 1.
- R3: la vista previa expone datos de cualquier Informe Técnico a quien tenga el
  permiso del gestor. Es el comportamiento actual y se conserva; se documenta.
- R4: descartar borra físicamente; el aviso de confirmación debe ser el nativo.
- R5: un 504 incierto en publicar o inactivar no se reintenta; React recarga el
  detalle para mostrar el estado real.

## 13. Bugs nativos detectados (no se corrigen en esta entrega)

- B1: `VariableTemplateInformeTecnicoToggleView` redirige a `request.POST["next"]`
  sin validar (:311): redirección abierta tras un POST con CSRF válido. Baja
  severidad (el atacante necesita el token del usuario).
- B2: `variables_list.html` no incluye paginador aunque la vista pagina por 100.
- B3: en `publicar_version` y `gestionar_incidencia`, el `IntegrityError` se atrapa
  dentro de `@transaction.atomic` sin savepoint propio (:522–545, :353–368). Según
  el motor, los cambios previos de la misma transacción (versión anterior a
  `inactiva`, versión nueva a `publicada`) podrían confirmarse con la publicación
  fallida. No se reprodujo; ver U1.

## 14. Incertidumbres

- U1: efecto real de B3 en MySQL; contrastar con prueba `mysql_compat` antes de
  activar.
- U2: `ValidationError` de `full_clean` en `crear_plantilla` no capturado; no se
  encontró una entrada válida del Form que lo dispare.
- U3: respuesta nativa a anónimo: el decorador externo levanta `PermissionDenied`
  antes del `LoginRequiredMixin`; si un middleware de login del core redirige antes,
  la página verá 302. Fijar con la línea base del diferencial.
- U4: compatibilidad de Summernote bs4 dentro del shell React y su CSP.

## 15. Casos de prueba

Backend (pytest, junto al dueño en `src/backends/comedores/admisiones/tests/`):

1. Guardas: usuario con «Gestor de templates» 200; sin permiso 403; superusuario 200;
   anónimo 401 por G1; header G1 alterado 403 sin ejecutar negocio.
2. Listado: default `activa`; `todas` incluye inactivas; `eliminada` filtra;
   `tipo_convenio=abc` se ignora; choice inválido se ignora; página 2 con 51 filas.
3. Crear: incorporación Ex PNUD = no limpia estado PNUD; renovación sin
   financiamiento da 400 con el mensaje de modelo; tipo de convenio fuera de los
   tres da 400; éxito crea v1 borrador y el mensaje con código.
4. Versiones: crear con borrador existente devuelve el mismo y el mensaje
   «Ya existe…»; `origen_version_id` copia contenido; plantilla eliminada 409.
5. Guardar: sanea `<script>` y conserva `{{ x }}`; versión publicada 404.
6. Publicar: contenido vacío 409; variable inactiva 409 con lista ordenada;
   combinación ocupada por otra plantilla 409; republicar la publicada 200
   «La versión ya se encuentra publicada.»; publicar v2 deja v1 `inactiva` y mueve la
   fila de publicación.
7. Inactivar: borra la publicación y deja la versión `inactiva`; repetir 409.
8. Descartar: borra solo el borrador; versión publicada 409; versión de otra
   plantilla 404.
9. Variables: alternar invierte y responde el mensaje correcto; listado `todas`.
10. Incidencias: reabrir con otra abierta 409 con el código; cerrar limpia
    `clave_abierta`; `plantilla` inactiva da 400.
11. Paridad API/HTML: misma secuencia por las dos vías deja filas idénticas
    (excepto marcas de tiempo).
12. Vista previa: sin `informe_id` redirige con mensaje; DOCX con marca de agua y
    sin filas nuevas.

Frontend (vitest): reconocimiento de rutas con y sin slash; filtros condicionales;
confirmación de descarte; render de errores 400 por campo; 409 como aviso de error
y navegación al `redirect`; 504 incierto sin reintento; editor envía el textarea
sincronizado.

Diferencial y visual: corrida base vs candidato de todas las URLs de §1 por rol
(gestor, sin permiso, superusuario) y estado (sin plantillas, con borrador, con
historial, inactiva, incidencias abiertas y cerradas) en desktop y móvil, con la
regla S13.

## 16. Fuente

- `src/backends/comedores/admisiones/urls/web_urls.py:1–137, 218–228`
- `src/backends/comedores/admisiones/views/templates_informe_tecnico.py:1–460`
- `src/backends/comedores/admisiones/forms/templates_informe_tecnico_forms.py:1–278`
- `src/backends/comedores/admisiones/services/templates_informe_tecnico_service/impl.py:1–572`
- `src/backends/comedores/admisiones/models/admisiones.py:1192–1206, 1563–1960`
- `src/backends/comedores/admisiones/services/informes_service/impl.py:1005–1075, 1295–1340, 1618–1660`
- `src/backends/comedores/admisiones/views/web_views.py:380–413`
- `src/backends/comedores/admisiones/templates/admisiones/templates_informes_tecnicos/` (`list.html`, `detail.html`, `form.html`, `version_form.html`, `variables_list.html`, `incidencias_list.html`, `incidencia_detail.html`, `includes/navigation.html`)
- `src/backends/comedores/admisiones/static/custom/js/gestor_templates_editor.js:1–410`
- `src/backends/kernel/templates/scripts/mainscripts.html:34, 75`
- `src/backends/kernel/core/decorators.py:35–62`; `src/backends/kernel/iam/services.py:90–105`
- `src/backends/kernel/users/bootstrap/groups_seed.py:466–468`
- `src/backends/sisoc_core/insumos/web_api_views.py:163–240` (patrón de envolvente)
- Pruebas existentes: `src/backends/comedores/admisiones/tests/test_gestor_templates_informe_tecnico.py` (20 pruebas), `test_validaciones_templates.py`

Lectura de código sin ejecución de app, base de datos ni navegador.
