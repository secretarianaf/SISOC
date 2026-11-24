# O01–O04: convenio, documentación, firmantes/avales y rendiciones de organización (M2)

| Campo | Valor |
|---|---|
| Fecha | 2026-11-10 |
| Familias | O01 (convenio de proyecto), O02 (documentos e historial), O03 (firmantes y avales), O04 (rendiciones) |
| Dueño | runtime `comedores`, app `gestion_organizaciones` |
| Base leída | HEAD `4ea95bcbe` y `origin/development` `83d87cd41` |
| Protocolo remoto | G1 v1 aprobado: [decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md) |
| Política de acceso | Paridad (precedente [T05](../../registro/decisiones/2026-11-10-2785-t05-programas-acceso-actual.md)) |
| Estado | Contrato ejecutable, condicionado a la base de paridad; nada implementado ni ejecutado |

La base de paridad, las reglas comunes de la API (`/api/web/comedores/organizaciones/`,
G1, errores, sin reintento), el DTO del legajo y la composición React están en
[O05](2026-11-10-2785-organizaciones-ficha-abm-o05-m2.md). Resumen: la referencia es
`development` con el PR #2836 fusionado; la rama de migración debe traer
`development` antes de implementar. Las líneas citadas son de `origin/development`
salvo que diga "HEAD"; para las vistas de documentos, firmantes y avales el código
es idéntico en ambas bases (solo cambia la numeración).

Permisos de ruta: `ORGANIZACION_DOCUMENTACION_PERMS` (`view_organizacion`,
`role_tecnico_comedor`, `role_abogado_dupla`) y `view_organizacion`, con
`permissions_any_required` (`urls.py:31–40`).

## O01: convenio de proyecto

### Ruta nativa

| URL | Nombre | Métodos | Vista | Permiso | Template |
|---|---|---|---|---|---|
| `/organizaciones/proyectos/<int:proyecto_id>/convenio/` | `organizacion_proyecto_convenio` | GET, POST | `views.py:973 ConvenioProyectoView` | `view_organizacion` | `convenio_proyecto_form.html` |

Alcance: `ProyectoOrganizacion` con `pk` y `activo=True`, sin filtro de dupla ni de
organización visible (`views.py:981–992`). Inactivo o inexistente: 404. Proyecto sin
línea: mensaje error "Asigná una línea al proyecto {codigo} antes de cargar el
convenio." y 302 a `/organizaciones/editar/<organizacion_id>` en GET y POST.
Un convenio por proyecto (`OneToOneField`): GET carga el existente o uno nuevo.

### O01.01 Consulta [L]

- Encabezado: franja "Abordaje Comunitario" con el nombre de la línea, título
  "Cargar datos del Convenio" o "Editar datos del Convenio", chip con el código.
- Datos: Organización, CUIT ("Sin información"), Código del proyecto, Línea, Región,
  Subzona (`convenio_proyecto_form.html`).
- En el legajo (development) el resumen por proyecto vive en
  `legajo/convenios.html`: "Datos de Convenio · {programa}", chip "Solo proyectos de
  esta línea", nota "Un convenio por cada proyecto de la línea.", por proyecto
  "Convenio {numero}" con "Cargado" o "Revisar montos", o "Sin cargar"; tabla de
  componentes, "Suma de componentes", aviso de no coincidencia con suma, total y
  diferencia; "Imprevistos no aplica: es solo para Línea Tradicional." en Secos;
  vacío "No hay proyectos en esta línea."; botón "Editar convenio"/"Cargar convenio"
  solo con `puede_gestionar_organizaciones`. Este componente es de O01 dentro del
  legajo de O05.01.

### O01.02 Operaciones [W]

`ConvenioProyectoForm` (`forms.py:609–653`), `ModelForm` sobre
`ConvenioProyecto` (`models.py:159–214`) excluyendo `proyecto`:

| Campo | Regla |
|---|---|
| `numero` | requerido, máx. 50 |
| `fecha` | requerida, `AAAA-MM-DD` |
| `meses` | requerido, entero positivo ≥1 |
| `monto_total`, `componente_alimentario`, `componente_gastos_generales`, `componente_siph`, `componente_gasto_bancario` | requeridos, decimal 14,2 ≥0 |
| `imprevistos` | solo existe si la línea es Tradicional; opcional; el modelo rechaza imprevistos fuera de Tradicional ("Imprevistos solo aplica a Línea Tradicional.") |

Efectos de POST válido (`views.py:1031–1049`): `form.save()` crea o actualiza;
mensaje success "Datos de convenio guardados."; si la suma de componentes no
coincide con el total, además warning "La suma de los componentes ({suma}) no
coincide con el monto total ({total})." (formato del filtro `monto`). Redirect a
`/organizaciones/detalle/<organizacion_id>?programa=<id de la línea>` (en HEAD iba a
la edición de la organización). Inválido: 200 con errores. Cancelar lleva a
`/organizaciones/detalle/<pk>?programa=<línea>`. El cálculo de suma en pantalla es
informativo ("Se puede guardar igual.") y no bloquea. No hay baja de convenio.

### API

| Método | Ruta | Reutiliza | Respuesta |
|---|---|---|---|
| GET | `proyectos/<proyecto_id>/convenio/` | `ConvenioProyectoView.get_proyecto`, `get_object`, `ConvenioProyectoForm`, `resumen_convenio` | 200 `{proyecto, organizacion, linea, es_linea_tradicional, campos, resumen}`; 404; 409 `{error, redirect}` sin línea |
| POST | `proyectos/<proyecto_id>/convenio/` | `ConvenioProyectoView.form_valid` | 200 `{redirect, messages}` / 400 / 409 sin línea |

Decimales viajan como texto (sin `float`). React calcula la suma igual que el script
nativo (centavos enteros) solo para mostrar.

Módulo React: `routes/organizacionConvenio.tsx` (+ test) para
`/organizaciones/proyectos/<id>/convenio/`.

Aceptación O01: mismos textos de encabezado y aviso; guardar Secos sin imprevistos y
Tradicional con imprevistos; aviso de suma; proyecto sin línea con el mensaje y
destino citados; edición sin duplicar convenio; sin permiso 403.

## O02: documentos e historial de la organización

### Rutas nativas

| URL | Nombre | Métodos | Vista (development) |
|---|---|---|---|
| `/organizaciones/<int:organizacion_id>/documentacion/<int:documentacion_id>/historial/` | `organizacion_documento_historial` | GET | `views.py:1052 historial_documento_organizacion` |
| `/organizaciones/<int:organizacion_id>/documentacion/<int:documentacion_id>/subir/` | `organizacion_documento_subir` | POST | `views.py:1074 subir_documento_organizacion` |
| `/organizaciones/<int:organizacion_id>/documentacion/personalizada/agregar/` | `organizacion_documento_personalizado_agregar` | POST | `views.py:1152 agregar_documento_personalizado_organizacion` |
| `/organizaciones/documentacion/<int:archivo_id>/estado/` | `organizacion_documento_estado` | POST | `views.py:1209 actualizar_estado_documento_organizacion` |
| `/organizaciones/documentacion/<int:archivo_id>/vencimiento/` | `organizacion_documento_vencimiento` | POST | `views.py:1263 actualizar_vencimiento_documento_organizacion` |
| `/organizaciones/documentacion/<int:archivo_id>/numero-gde/` | `organizacion_documento_gde` | POST | `views.py:1305 actualizar_numero_gde_documento_organizacion` |

Todas con `ORGANIZACION_DOCUMENTACION_PERMS` y `login_required`. **No existe ruta
de borrado** de documentos de organización: el "cargar/borrar" del catálogo no
tiene fuente; la única baja es la masiva por cambio de tipo de entidad (O05.02).

### Capacidades y alcance

- `puede_validar` (abogado): superusuario o abogado de la dupla de algún comedor de
  la organización; `puede_enviar` (técnico): superusuario o técnico de esa dupla;
  `puede_modificar` = cualquiera de las dos (`views.py:339–364`).
- Historial y documentación adicional filtran la organización por dupla (404 si
  ajena). Subir usa la organización global, pero exige `puede_enviar` (403).
  Estado, vencimiento y GDE buscan el archivo global y exigen la capacidad sobre su
  organización.
- `view_organizacion` sin dupla **ve** el legajo pero no modifica documentos.

### O02.01 Historial y metadatos [L]

Catálogo por categoría (`views.py:184–242`): eclesiástica si tipo o subtipo contiene
"ecles" o "culto"; de base si contiene "base" o "hecho"; si no, personería jurídica.
Por documento del catálogo: archivo vigente (más reciente) e historial; luego los
adicionales (`documentacion` nula). Visible si `muestra_documentacion`
(`legajo.py:263–275`): programa Alimentar, organización sin programas, o sin
Alimentar pero con archivos.

Tabla (`legajo/documentacion.html`, fila `documentacion_organizacion_row.html`):
columnas "Documento", "Estado / validación", "Archivo", "Vencimiento / carga",
"Número de GDE"; asterisco en obligatorios; insignia "Adicional"; botón "Historial"
si hay archivo de catálogo; estados "Pendiente", "Documento adjunto",
"A Validar Abogado", "Rectificar", "Aceptado"; observaciones bajo el estado;
"Ver Archivo" o "Sin archivo"; vencimiento con "Vencido", "Por vencer" (≤30 días),
"Vigente" o "Sin vencimiento"; GDE solo en Aceptado ("Sin número GDE" o "-"); fila
vacía "No hay documentación configurada.". Encabezado "Documentación de la
Organización" con la categoría.

Historial (`documentacion_historial.html`): sin filtrar `documentacion` por
categoría; todas las versiones `-creado, -id`; columnas "Fecha de carga", "Estado",
"Fecha de vencimiento", "Observaciones", "Archivo" ("Ver archivo"); vacío "No hay
documentos cargados.".

### O02.02 Carga y operaciones [F]

| Acción | Entrada | Reglas y mensajes (403/400) | Efecto |
|---|---|---|---|
| Subir catálogo | multipart `archivo`, `fecha_vencimiento` opcional | sin `puede_enviar`: 403 "Sin permisos para cargar este documento."; archivo: "Debe adjuntar un archivo.", "El archivo excede el tamaño máximo permitido de 20 MB.", "Formato inválido. Solo se permiten archivos PDF, JPG, PNG, Excel o Word.", "Tipo de archivo no permitido. Formatos válidos: PDF, JPG, PNG, Excel o Word."; fecha: "Fecha de vencimiento invalida." | si el vigente **no** está Aceptado, se **reemplaza en el mismo registro** (archivo, vencimiento, estado "Documento adjunto", observaciones vacías, GDE nulo, `creado` = ahora, actores); si está Aceptado o no hay, se crea uno nuevo (el anterior pasa a historial) |
| Adicional | multipart `nombre`, `archivo`, `fecha_vencimiento` | 403 igual; "Debe indicar un nombre para el documento."; mismas validaciones | crea `ArchivoOrganizacion` sin catálogo, nombre truncado a 255 |
| Estado | `estado`, `observaciones` | estado fuera de choices: 400 "Estado invalido."; reglas de `_validar_cambio_estado_documento_organizacion` (`views.py:367–402`) con 403 y textos "El abogado solo puede validar documentos en estado A Validar Abogado.", "El documento no esta disponible para envio tecnico.", "El tecnico solo puede enviar documentos a validar.", "Sin permisos para modificar este documento."; Rectificar por abogado sin observaciones: 400 "Debe indicar observaciones." | guarda estado; observaciones solo en Rectificar (si no, vacías) |
| Vencimiento | `fecha_vencimiento` (vacío borra) | 403 "Sin permisos para modificar este documento."; 400 "Fecha de vencimiento invalida." | guarda fecha |
| GDE | `numero_gde` (recorte 50, vacío = nulo) | 403 igual; no Aceptado: 400 "El número de GDE solo puede cargarse en documentos aceptados." | guarda y replica a admisiones (`AdmisionService.replicar_numero_gde_desde_organizacion`, `admisiones/services/admisiones_service/impl.py:2692`) |

Respuestas nativas de éxito: `{success, html, row_id}` (+ `estado`,
`fecha_vencimiento`, `numero_gde` o `archivo_id`). El HTML es la fila renderizada.

Mensajes del cliente nativo (`static/custom/js/organizacionesDocumentos.js`) que
React conserva: "Estado actualizado con éxito.", "Número GDE actualizado con éxito.",
"Vencimiento actualizado con éxito.", "Documento cargado con éxito.",
"Documento adicional agregado con éxito.", errores "No se pudo actualizar el
estado.", "No se pudo guardar el valor.", "No se pudo subir el archivo.",
"Error de red al subir el documento.", "No se pudo agregar el documento.",
"Error de red al agregar el documento.", "Debe indicar un nombre para el
documento.", "Debe completar las observaciones."; toasts por defecto "Cambio
guardado con éxito." / "No se pudo guardar el cambio.". Modal de Rectificar
"Observaciones obligatorias", etiqueta "Detalle el motivo de la rectificacion",
botones "Cancelar" / "Guardar observaciones". Bloque "Documentación Adicional":
"Opcional. Indicá un nombre y adjuntá el archivo. Podés agregar tantos como
necesites.", "Nombre del documento", "Vencimiento (opcional)", "Agregar documento
adicional". Progreso de subida con porcentaje.

### API

| Método | Ruta | Reutiliza | Respuesta |
|---|---|---|---|
| GET | `organizaciones/<id>/documentacion/<doc_id>/historial/` | `historial_documento_organizacion` (queryset) | 200 `{organizacion, documentacion, archivos:[{id,creado,estado,fecha_vencimiento,observaciones,url}]}` / 404 |
| POST | `organizaciones/<id>/documentacion/<doc_id>/subir/` (multipart) | lógica de `subir_documento_organizacion` | 200 `{fila}` / 400 / 403 |
| POST | `organizaciones/<id>/documentacion/personalizada/` (multipart) | `agregar_documento_personalizado_organizacion` | 200 `{fila}` / 400 / 403 / 404 |
| POST | `documentacion/<archivo_id>/estado/` | `actualizar_estado_documento_organizacion` | 200 `{fila}` / 400 / 403 / 404 |
| POST | `documentacion/<archivo_id>/vencimiento/` | `actualizar_vencimiento_documento_organizacion` | idem |
| POST | `documentacion/<archivo_id>/numero-gde/` | `actualizar_numero_gde_documento_organizacion` | idem |

`fila` es un DTO de la fila (`row_id`, nombre, obligatorio, personalizado, estado,
observaciones, url del archivo, vencimiento con su estado, GDE, historial,
capacidades de edición), no HTML de Django. Para no duplicar reglas, la lógica de
cada vista nativa se extrae a funciones de servicio que usan la vista HTML y la API
(refactor chico autorizado por el contrato, sin cambio de salida nativa, verificado
con el diferencial). Subidas: un solo POST, sin reintento; tras 504 incierto se
vuelve a leer el legajo.

Archivos: el enlace es `archivo.archivo.url` (media directa), igual que hoy. No se
agrega descarga protegida (paridad).

Módulo React: la tabla es un componente de O02 dentro de `organizaciones.tsx`
(legajo); el historial es `routes/organizacionDocumentos.tsx` para
`/organizaciones/<id>/documentacion/<doc_id>/historial/`.

Consumidores indirectos: AD02/AD03 leen los archivos de organización (congelado y
GDE replicado); el reemplazo en el mismo registro y la réplica de GDE deben seguir
idénticos.

## O03: firmantes y avales

### Rutas nativas

| URL | Nombre | Métodos | Vista (development) | Template |
|---|---|---|---|---|
| `/organizaciones/firmante/crear/<int:organizacion_pk>` | `firmante_crear` | GET, POST | `views.py:441 FirmanteCreateView` | `firmante_form.html` |
| `/organizaciones/firmante/editar/<int:pk>` | `firmante_editar` | GET, POST | `views.py:640 FirmanteUpdateView` | `firmante_form.html` |
| `/organizaciones/firmante/eliminar/<int:pk>` | `firmante_eliminar` | GET, POST | `views.py:709 FirmanteDeleteView` | `firmante_confirm_delete.html` |
| `/organizaciones/aval/crear/<int:organizacion_pk>` | `aval_crear` | GET, POST | `views.py:561 AvalCreateView` | `aval_form.html` |
| `/organizaciones/aval/editar/<int:pk>` | `aval_editar` | GET, POST | `views.py:686 AvalUpdateView` | `aval_form.html` |
| `/organizaciones/aval/eliminar/<int:pk>` | `aval_eliminar` | GET, POST | `views.py:740 AvalDeleteView` | `aval_confirm_delete.html` |

Todas: `view_organizacion` y `LoginRequiredMixin`; querysets globales, sin alcance de
dupla (paridad). Sin barra final.

### O03.01 Consulta [L]

En el legajo (development, `legajo/firmantes.html`): "Firmantes · {programa}" con
los firmantes del programa; "Agregar Firmante" con `puede_gestionar_organizaciones`
(no en el bloque "Sin programa asignado" cuando hay programa); columnas "Nombre",
"Rol" (insignia), "CUIT", "Programa" (solo en "Sin programa asignado": "{programa}
(no cargado en la organización)" o "Sin programa"), "Acciones"; vacío "No hay
firmantes registrados.". Avales solo si el tipo de entidad es "Asociación de hecho":
"Avales", "Agregar", columnas "Nombre", "CUIT", vacío "No hay avales registrados.".

### O03.02 Altas, cambios y desvinculación [M]

`FirmanteForm` (`forms.py:575–606`): `nombre` requerido (255); `rol` opcional;
`cuit` opcional 0..99999999999; `programa` opcional.

- Roles en **alta** según el tipo de entidad (`views.py:469–497`): "personería
  jurídica" → Presidente, Tesorero, Secretario; "personería jurídica eclesiástica" →
  Obispo, Apoderado 1, Apoderado 2; "asociación de hecho" → Firmante 1, 2, 3;
  otro tipo: todos; sin tipo: ninguno. En **edición** se ofrecen todos los roles.
- Programas: solo los de la organización más el actual; sin programas, todos.
- Rol único por organización: "Ya existe un firmante con ese rol para esta
  organización." (alta y edición, excluyendo el propio).
- Alta toma la organización del campo oculto `organizacion_id` del POST, no de la
  URL; si falta: error "Falta el id de la organización.".
- Botones del alta: "Volver" (al legajo), "Guardar", "Guardar y agregar otro" (vuelve
  a `firmante_crear`). Edición: "Guardar". Éxito: 302 a
  `/organizaciones/detalle/<pk>` sin mensaje.

`AvalForm` (`forms.py:656–664`): `nombre` y `cuit` opcionales; mismos botones y
retornos.

Baja (`SoftDeleteDeleteViewMixin`): GET confirmación con vista previa de cascada,
título de página "Confirmar Eliminación", encabezado por defecto "Atención!", migas
"Detalle de Organización" / "Confirmar Eliminación", texto "¿Está seguro que desea
dar de baja al firmante {nombre}" o "¿Está seguro que desea dar de baja el aval
{nombre}" seguido del nombre de objeto vacío y "?", botones "Dar de baja"/"Cancelar"
(`delete_confirm.html`); POST baja
lógica con usuario y cascada, mensaje "Firmante dado de baja correctamente." o
"Aval dado de baja correctamente.", 302 al legajo.

### API

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `organizaciones/<id>/firmantes/formulario/` y `firmantes/<pk>/formulario/` | campos y roles/programas permitidos |
| POST | `organizaciones/<id>/firmantes/` | 201 `{redirect, otro}` / 400 |
| POST | `firmantes/<pk>/` | 200 `{redirect}` / 400 / 404 |
| GET/POST | `firmantes/<pk>/baja/` | preview / 200 `{redirect, messages}` |
| GET/POST | equivalentes `avales/` | idem |

**Decisión técnica:** la API toma la organización de la URL y además acepta
`organizacion_id` del cuerpo con la misma precedencia que la vista
(`kwargs["organizacion_id"]` nunca existe, por lo que manda el POST). Se conserva
la precedencia para paridad y queda en "Riesgos".

Módulo React: `routes/organizacionFirmantes.tsx` (+ test) para las seis URLs.

## O04: rendiciones de organización

### Ruta nativa

| URL | Nombre | Métodos | Vista | Template |
|---|---|---|---|---|
| `/organizaciones/<int:organizacion_id>/rendiciones/<int:pk>/detalle/` | `organizacion_rendicion_detalle` | GET | `views.py:925 OrganizacionRendicionDetailView` | `organizacion_rendicion_detail.html` |

Permiso `ORGANIZACION_DOCUMENTACION_PERMS`; queryset (`views.py:930–958`): rendición
no borrada, de un proyecto de la organización o de un comedor no borrado de ella, y
organización visible por dupla. Otro caso: 404.

### O04.01 Consulta [L]

Lista dentro del legajo (development): pestaña "Rendiciones Presentadas (N)" para
programas de Abordaje, filtrada por la línea de la rendición
(`rendiciones_por_programa` → `RendicionesOrganizacionService.obtener_rendiciones`
con `linea_programatica`, `services.py:1604–1665`), filtro "Código de Proyecto"
("Todos los proyectos", "Filtrar") si hay más de un código, bloque "Rendiciones de
otras líneas" con la nota "Su línea no está entre los programas de la organización.
Se muestran acá para que no queden ocultas."; sin Abordaje, "Rendiciones
Presentadas" generales. Columnas (`legajo/rendiciones_tabla.html`): opcionales
"Línea" y "Proyecto", luego "Conv.", "N° de Rend.", "Período", "Validación
Territorial", "Revisión para Carga", "Validación", "Auditada", "Detalle" ("Ver");
valores "✔" o "-"; vacío "No hay rendiciones presentadas para la selección actual.".
Orden `-periodo_inicio, -id`. Este es el filtro de línea que el catálogo pide no
perder.

Detalle: "Rendición {numero}", organización, "Ir a Rendición" con
`rendicioncuentasmensual.view_rendicioncuentamensual`; datos Código de Proyecto,
Convenio, Número de Rendición, Período, Estado del proceso, Validación Territorial
y fecha, Validación Auditoría y fecha, "Validación" y "Fecha de Validación"
(development), Auditada y fecha, Regularización y fecha, enlaces a acta y acta
complementaria (media directa, "Ver archivo").

### O04.02 Acciones y evidencias [W]

No hay acciones nativas en esta app. La única acción es "Descargar" el PDF
consolidado (`components/pdf_descarga_action.html`, issue #2845), visible con
`view_rendicioncuentamensual` y `validacion_auditoria_finalizada`: POST a
`/rendicioncuentasmensual/detalle/<pk>/descargar-pdf/solicitar/` y consulta de
`.../estado/`, con los textos "Generando PDF…", "Generando el PDF. Puede tardar unos
minutos.", "PDF listo. La descarga comienza en unos segundos.", "La generación del
PDF tardó demasiado. Intentá nuevamente.", "No se pudo generar el PDF.".

**Decisión técnica:** O04.02 no crea API propia: React reutiliza los endpoints
nativos de `rendicioncuentasmensual` (dueño de ese job) igual que el script nativo,
sin reintentar el POST. Si esa familia migra su job a `/api/web/comedores/`, O04.02
la sigue. Las transiciones de rendición pertenecen a su propia familia, no a O04.

### API

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `organizaciones/<id>/rendiciones/<pk>/` | 200 DTO del detalle con capacidades (`puede_ir_a_rendicion`, `puede_descargar_pdf`) / 404 |

La lista viaja en el DTO del legajo (O05.01). Módulo React:
`routes/organizacionRendiciones.tsx` para
`/organizaciones/<id>/rendiciones/<pk>/detalle/`.

## Criterios de aceptación comunes

1. Cada acción produce los mismos registros, estados, actores y efectos laterales
   (réplica de GDE, reemplazo en el mismo registro) que la vista nativa.
2. Cada texto citado aparece igual en React; los 400/403 conservan el mensaje de
   Django.
3. Técnico, abogado, superusuario, `view_organizacion` sin dupla y usuario ajeno
   obtienen los mismos permisos de pantalla y API que hoy.
4. Ningún POST se reintenta solo; tras 504 incierto se relee el estado.
5. Regla visual S13 por URL × estado × rol × viewport (estructura + ≤1 % sin
   antialiasing; 8 min de diagnóstico y luego prueba humana de la ola).
6. Diferencial: 0 diferencias en rutas existentes fuera de las rutas nuevas.

## Dependencias

- Base `development` con #2836 (bloqueante, ver O05).
- O05.01 publica el marco y el DTO del legajo; O01, O02, O03 y O04 aportan sus
  secciones y pueden escribirse en paralelo con superficies disjuntas
  (`web_api_views.py` se divide por familia o tiene un dueño único).
- AD02/AD03: consumen `ArchivoOrganizacion` (congelado y GDE).
- Rendiciones mensuales (dueño de `rendicioncuentasmensual`): job PDF de O04.02.
- CO07: la ficha de comedor enlaza al legajo.

## Riesgos

- Subir sobre un documento no aceptado reemplaza el archivo en el mismo registro:
  la versión anterior no queda en historial (comportamiento nativo).
- Alta de firmante con `organizacion_id` del cuerpo: puede apuntar a otra
  organización que la de la URL (sin validación de pertenencia; paridad). Un id
  inexistente probablemente termina en error de integridad 500 (no verificado).
- La regla `rol == "aval"` de `FirmanteForm.clean` compara un objeto con un texto y
  nunca se cumple (regla muerta; paridad, sin efecto visible).
- Archivos y actas servidos por URL de media directa, sin descarga protegida
  (paridad).
- Convenio sin alcance de dupla: cualquier `view_organizacion` edita cualquier
  proyecto activo (paridad).

## Casos de prueba

- O01: GET nuevo y existente, proyecto inactivo (404), sin línea (409 y mensaje),
  Secos sin campo imprevistos, Tradicional con imprevistos, suma distinta (warning),
  POST sin CSRF (403), sin permiso (403).
- O02: técnico sube PDF válido, archivo de 20 MB + 1 byte, extensión y content-type
  inválidos, fecha inválida; reemplazo sobre "Rectificar" (mismo id) y nueva versión
  sobre "Aceptado"; abogado acepta y rectifica (sin y con observaciones); técnico
  intenta aceptar (403 con texto); GDE en no aceptado (400) y en aceptado con réplica
  a admisión; historial ajeno (404); adicional sin nombre.
- O03: roles por tipo de entidad, rol repetido en alta y edición, programas
  limitados, "Guardar y agregar otro", baja lógica con preview, aval visible solo en
  "Asociación de hecho".
- O04: rendición de otra organización (404), filtro por línea y por código, bloque
  de otras líneas, PDF con y sin permiso, job pendiente/listo/error simulado sin
  efectos externos reales.
- Visual y diferencial como en O05.

## Decisiones técnicas del agente

1. Paridad contra `development` con #2836 (ver O05).
2. DTO de fila de documento en lugar del HTML de Django; extracción a servicios sin
   cambiar la salida nativa.
3. Sin ruta de borrado de documentos: no existe en la fuente.
4. O04.02 reutiliza el job PDF nativo; sin API duplicada.
5. Precedencia de `organizacion_id` del alta de firmante conservada.
6. Un módulo de ruta React por familia (`organizacionConvenio.tsx`,
   `organizacionDocumentos.tsx`, `organizacionFirmantes.tsx`,
   `organizacionRendiciones.tsx`) para escritores paralelos.

## Incertidumbres

- Nada se ejecutó. Las líneas de development son del fetch local del 2026-11-06.
- La fila de catálogo declara `data-vencimiento-id="org-doc-venc-<id>"`, pero el
  único input con ese id está dentro de un bloque `{% comment %}` de
  `legajo/documentacion.html:61–181`. Leído en código: la subida desde el catálogo
  no envía vencimiento (solo el documento adicional lo hace). React lo reproduce
  (sin campo de fecha en la fila); confirmar en el navegador durante la referencia
  visual.
- Comportamiento exacto del alta de firmante con organización inexistente.
- Los estados "Validación" y "Fecha de Validación" del detalle de rendición dependen
  de campos de `rendicioncuentasmensual` cambiados por #2836 (`validada`,
  `fecha_gestion_auditoria`); no se leyó su modelo completo.

## Fuente

`origin/development` `83d87cd41` salvo indicación:
`src/backends/comedores/gestion_organizaciones/urls.py:31–212`;
`views.py:184–402,441–768,925–1351`; `forms.py:575–664`; `models.py:17–51,159–214`;
`services/programas.py:110–130,203–224`; `services/legajo.py:115–207,263–275`;
`templates/convenio_proyecto_form.html`, `firmante_form.html`, `aval_form.html`,
`organizaciones_confirm_delete_shared.html`, `organizacion_rendicion_detail.html`,
`organizaciones/documentacion_historial.html`,
`organizaciones/partials/documentacion_organizacion_row.html`,
`organizaciones/partials/legajo/{convenios,documentacion,firmantes,filtro_proyecto,rendiciones_tabla,sin_programa}.html`;
`static/custom/js/organizacionesDocumentos.js` (HEAD, sin cambios en development);
`src/backends/kernel/organizaciones/models.py:54–87,227–340`;
`src/backends/comedores/rendicioncuentasmensual/services.py:1604–1665`, `urls.py:64–82`,
`static/custom/js/rendicioncuentasmensual_pdf_descarga.js`;
`src/backends/kernel/templates/components/{form_card,delete_confirm}.html`;
`src/backends/comedores/rendicioncuentasmensual/templates/components/pdf_descarga_action.html`;
`src/backends/comedores/admisiones/services/admisiones_service/impl.py:2692,3697`.
