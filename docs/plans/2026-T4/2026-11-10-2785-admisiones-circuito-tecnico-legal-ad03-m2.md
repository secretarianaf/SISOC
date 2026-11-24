# AD03: circuito técnico/legal y seguimiento de admisión

- Fecha: 2026-11-10. Base de lectura: HEAD `4ea95bcbe`.
- Dueño: runtime `comedores` (`backend_comedores`), app `admisiones`.
- Protocolo: G1 v1 aprobado
  ([decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md)). Las
  APIs nuevas viven bajo `/api/web/comedores/admisiones/`.
- Entregas: AD03.01 estado y seguimiento [L], AD03.02 transiciones técnicas [W],
  AD03.03 transiciones legales y efectos [W].
- AD02 (informe, documentos, previsualización) y AD01 (plantillas y
  publicaciones) tienen contratos propios. AD03 los consume, no los reimplementa:
  [AD02](2026-10-28-2785-admisiones-informes-documentos-m2.md).

Regla de corte: una transición observable por tarea. El editor de admisión
(`admisiones_tecnicos_editar`) y el detalle legal (`admisiones_legales_ver`)
concentran muchas acciones en un solo POST. La API las separa en un endpoint por
acción, y cada uno llama al mismo handler de servicio que la rama nativa.

## Rutas nativas

Archivo `src/backends/comedores/admisiones/urls/web_urls.py`, incluido sin prefijo
por `comedores_runtime/urls.py:12`. «Lectura» significa
`permissions_any_required(["comedores.view_comedor", "admisiones.view_admision",
"acompanamientos.view_informacionrelevante"])`. «Lectura+EP» agrega
`expedientespagos.view_expedientepago`. Todas exigen sesión
(`LoginRequiredMixin` o `@login_required`).

| URL exacta | Nombre | Métodos | Vista (`views/web_views.py`) | Permiso de URL | Template | Entrega |
|---|---|---|---|---|---|---|
| `/comedores/admisiones/tecnicos/listar` | `admisiones_tecnicos_listar` | GET | `AdmisionesTecnicosListView` :1050 | Lectura | `admisiones/admisiones_tecnicos_list.html` | 01 |
| `/comedores/admisiones/tecnicos/editar/<pk>` | `admisiones_tecnicos_editar` | GET, POST | `AdmisionesTecnicosUpdateView` :1132 | Lectura | `admisiones/admisiones_tecnicos_form.html` | 01 lectura, 02 acciones |
| `/comedores/<comedor_pk>/admision/<pk>/detalle/` | `admision_detalle` | GET, POST | `AdmisionDetailView` :1349 | Lectura | `admisiones/admisiones_detalle.html` | 01 lectura, 02 cierre forzado |
| `/comedores/admisiones/<pk>/templates/reportar-faltante/` | `admisiones_reportar_configuracion_faltante_template` | POST | `reportar_configuracion_faltante_template` :382 | ninguno | redirect | 02 |
| `/ajax/actualizar-estado/` | `actualizar_estado_archivo` | cualquiera (lee POST) | :845 | ninguno | JSON | 02 |
| `/ajax/actualizar-numero-gde/` | `actualizar_numero_gde_archivo` | POST | :870 | ninguno | JSON | 02 |
| `/ajax/actualizar-numero-gde-organizacion/` | `actualizar_numero_gde_organizacion_admision` | POST | :891 | ninguno | JSON | 02 |
| `/admisiones/<admision_pk>/resync-convenio/` | `admision_resync_convenio` | POST | :909 | ninguno | JSON | 02 |
| `/ajax/actualizar-convenio-numero/` | `actualizar_convenio_numero` | POST | :960 | ninguno | JSON | 02 |
| `/ajax/actualizar-vigente-pwa/` | `actualizar_vigente_pwa` | POST | :978 | ninguno | JSON | 02 |
| `/ajax/actualizar-personas-conveniadas-nomina/` | `actualizar_personas_conveniadas_nomina` | POST | :987 | ninguno | JSON | 02 |
| `/ajax/actualizar-num-expediente/` | `actualizar_num_expediente` | POST | :996 | ninguno | JSON | 02 |
| `/comedores/admisiones/legales/listar` | `admisiones_legales_listar` | GET | `AdmisionesLegalesListView` :1780 | Lectura+EP | `admisiones/admisiones_legales_list.html` | 01 |
| `/comedores/admisiones/legales/ver/<pk>` | `admisiones_legales_ver` | GET, POST | `AdmisionesLegalesDetailView` :1834 | Lectura+EP | `admisiones/admisiones_legales_detalle.html` | 01 lectura, 03 acciones |
| `/comedores/admisiones/legales/revisar-complementario/<pk>` | `revisar_informe_complementario` | GET, POST | `InformeTecnicoComplementarioReviewView` :1881 | Lectura+EP | `admisiones/revisar_informe_complementario.html` | 03 |
| `/comedores/admisiones/legales/ajax/` | `admisiones_legales_ajax` | GET | `admisiones_legales_ajax` :2016 | Lectura (sin EP, decorador interno) | JSON con HTML | 01 |

Las URLs de listar, editar y legales no terminan en `/`: React las reconoce así,
sin agregar slash. Los prefijos `ajax/actualizar-*` y `admisiones/` ya están en
`url_prefixes` de `comedores` (`src/backends/config/backends.json`).

Fuera de alcance: `AdmisionesTecnicosCreateView` (`views/web_views.py:1105`) no
tiene URL, y `partials/admisiones_tecnicos_rows.html:35` referencia el nombre
inexistente `admisiones_tecnicos_crear`. Es código sin ruta y no se migra.

## Permisos y alcance por objeto (estado actual)

| Concepto | Regla | Fuente |
|---|---|---|
| Listado técnico | Superusuario: todas. Coordinador con duplas: comedores de esas duplas con `dupla.estado == "Activo"`. Otro usuario: comedor cuya dupla activa lo tiene como técnico o abogado. Siempre se excluyen `enviado_acompaniamiento`, `enviada_a_archivo` y `activa=False`. | `services/admisiones_service/impl.py:659–725` |
| Listado legal | `enviado_legales=True` y `activa=True`. Un coordinador no superusuario ve solo las de sus duplas (ninguna si no tiene). Cualquier otro usuario con permiso de URL ve todas. | `services/legales_service/impl.py:1128–1189` |
| Editar admisión, detalle, detalle legal, revisar complementario | Objeto por PK global, sin filtro de actor. El detalle solo valida que `comedor_pk` coincida (si no, 404). | `views/web_views.py:1132–1137`, `1376–1381`, `1834–1838`, `1881–1884` |
| Técnico de dupla | Tiene uno de los permisos de lectura, es técnico de la dupla del comedor y la dupla está «Activo». | `_verificar_permiso_tecnico_dupla`, `impl.py:3278–3307` |
| Dupla | Técnico o abogado de la dupla activa. | `_verificar_permiso_dupla`, `impl.py:3310–3346` |
| Rol para botones | `auth.role_tecnico_comedor` y `auth.role_abogado_dupla`. | `_resolver_roles_para_botones`, `impl.py:3381–3385` |

Los botones del editor (`_get_botones_disponibles`, `impl.py:3348–3505`) y del
detalle legal (`LegalesService.get_botones_disponibles`,
`legales_service/impl.py:148–252`) solo deciden qué se muestra. Excepto
providencias y GDE PV (`_bloquear_fuera_de_secuencia`, `:633–662`), los handlers
POST no vuelven a verificar rol, dupla ni estado de origen.
`actualizar_estado_admision` (`impl.py:3508–3546`) aplica la transición pedida
desde cualquier estado.

## AD03.01 — Estado y seguimiento [L]

### Listados técnico y legal

- Paginación: 10 por página (`paginate_by = 10`), parámetro `page`.
- Orden: `apply_allowed_ordering`, única clave `nombre` → `comedor__nombre`; por
  defecto `-creado`. Encabezado ordenable «Nombre».
- Búsqueda libre `busqueda`:
  - técnico: comedor, provincia, tipo de comedor, calle, número y nombre, apellido
    o celular del referente (`impl.py:640–656`);
  - legal: comedor, tipo de convenio, `num_expediente`, `num_if` y
    `estado_legales`.
- Filtros avanzados (`services/admisiones_filter_config/impl.py` y
  `legales_filter_config/impl.py`), mismos campos con `estado` distinto:
  - `comedor_nombre` «Nombre del comedor» (text);
  - `comedor_id` «ID de comedor» (number);
  - `tipo_admision` «Tipo de admisión» (choice: Incorporación, Renovación);
  - `organizacion` «Organización del comedor» (text);
  - `num_expediente` «N° de expediente» (text);
  - `provincia` «Provincia» (choice, nombres de `Provincia`);
  - `equipo_tecnico` «Equipo técnico» (choice, `Dupla.objects.activas()`);
  - `estado`: `estado_admision` en técnico, `estado_legales` en legal (choice,
    `Admision.ESTADOS_ADMISION` o `Admision.ESTADOS_LEGALES`);
  - `fecha_modificado` «Fecha de última modificación» (date).

  Operadores: text `contains, ncontains, eq, ne, empty`; number y date
  `eq, ne, gt, lt, empty`; choice `eq, ne`.
- Favoritos: `SeccionesFiltrosFavoritos.ADMISIONES_TECNICOS` y
  `ADMISIONES_LEGALES`. Columnas configurables: `admisiones_tecnicos_list` y
  `admisiones_legales_list` (`build_columns_context_for_custom_cells`).
- Títulos: «Admisiones - Equipos técnicos» y «Expedientes - Legales». Migas:
  «Admisiones › Listar» y «Expedientes › Listar».
- Columnas (`impl.py:728–845`, `legales_service/impl.py:1191–1297`):
  - ID Comedor;
  - Tipo;
  - Nombre (enlace a `comedor_detalle`);
  - Organización;
  - N° Expediente;
  - N° Convenio (`<n>°` o `-`);
  - Provincia;
  - Equipo técnico;
  - Estado: display de `estado_admision` en técnico y de `estado_legales` en
    legal;
  - Última Modificación (`dd/mm/aaaa`).

  Valor vacío: `-`. Acción técnica: «Ver» (`warning`) con badge «Rectificar» si
  `estado_legales == "A Rectificar"` o «Archivado» si es «Archivado». Acción legal:
  «Ver» (`primary`).
- `admisiones_legales_ajax` devuelve `{html, pagination_html, count, num_pages,
  has_previous, has_next, current_page}`. Solo usa la búsqueda: no aplica filtros
  avanzados ni orden. React no lo consume: usa el endpoint de listado. Se conserva
  para la UI Django.

### Editor técnico (lectura) y detalle de admisión

Datos de `AdmisionService.get_admision_update_context` (`impl.py:1055–1123`):

- documentos del convenio por `orden` y personalizados;
- informe técnico y PDF;
- informes complementarios (lo que muestran y lo que exigen) y botones;
- capacidades `puede_editar_convenio_numero`, `puede_editar_num_expediente` y
  `puede_editar_personas_conveniadas_nomina`;
- `ValidacionesTemplateAdmisionForm` y `puede_editar_validaciones_template`
  (`web_views.py:1146–1156`);
- y, si `puede_editar_informe_tecnico`, el editor embebido de AD02 con la
  carátula.

Si el servicio falla, devuelve `{}` y la pantalla queda vacía: React muestra el
mismo estado vacío, no un error nuevo.

Detalle (`/comedores/<comedor_pk>/admision/<pk>/detalle/`):

- equipo técnico (técnicos y abogado);
- documentos;
- informe y PDF, y complementarios;
- acompañamiento (`AcompanamientoService.obtener_datos_admision`, número IF,
  disposición, prestaciones por día);
- expedientes de pago, rendiciones mensuales y rendición final con documentos e
  historial;
- dos historiales paginados de 10, con parámetros `historial_page` y
  `historial_estados_page`:
  - de campos: Fecha, Usuario, Campo, Valor nuevo, Valor anterior;
  - de estados: Fecha, Estado nuevo, Estado anterior, Usuario.

  Fechas `dd/mm/aaaa HH:MM` en hora local.

Con `enviado_legales` el bloqueo del expediente se informa con «No se puede
editar el expediente una vez enviado a legales.».

### Detalle legal (lectura)

`LegalesService.get_legales_context` (`legales_service/impl.py:1403–1655`):

- estado del expediente («Sin información» si falta) y número de expediente
  (`legales_num_if`);
- Formulario Proyecto de Convenio, Primera y Segunda Providencia, con su PDF, su
  DOCX y su número (ícono de check, alerta o cruz);
- documentos e informe por tipo de convenio;
- complementarios y PDF final;
- botones de `get_botones_disponibles`.

Los PDF y DOCX se enlazan por `archivo.url` (media): React usa las mismas URLs,
sin endpoint nuevo de descarga.

### API AD03.01

| Método y ruta | Reutiliza | Respuesta |
|---|---|---|
| `GET tecnicos/` (query de listado) | `get_admisiones_tecnicos_queryset` + `get_admisiones_tecnicos_table_data` + filtros/columnas | 200 `{items, headers, page, num_pages, count, filters_config}`; celdas como datos, no `mark_safe` |
| `GET legales/` | `get_admisiones_legales_filtradas` + `get_admisiones_legales_table_data` | igual |
| `GET <pk>/` | `get_admision_update_context` + extras de `AdmisionesTecnicosUpdateView.get_context_data` | 200 datos del editor y `botones`; 404 |
| `GET <comedor_pk>/<pk>/detalle/` | builders de `web_views.py:416–658` | 200; 404 si no coincide el comedor |
| `GET legales/<pk>/` | `get_legales_context` | 200 |

Módulo React: `src/frontends/apps/sisoc/src/routes/admisionesSeguimiento.tsx`, que
reconoce los dos listados, el editor, el detalle y el detalle legal en sus URLs
nativas. Las acciones de AD03.02 y AD03.03 se montan dentro de esas pantallas
desde los módulos `admisionesTecnicos.tsx` y `admisionesLegales.tsx`.

## AD03.02 — Transiciones técnicas [W]

### Acciones del POST del editor (`AdmisionesTecnicosUpdateView.post`)

Orden de despacho: `subir_docx_final` (AD02), `btnInformeTecnicoCaratula`
(informe + carátula, AD02), y después `AdmisionService.procesar_post_update`
(`impl.py:1206–1274`), que toma la primera clave presente. Toda excepción se
convierte en «Error inesperado.». Éxito y error vuelven al editor con
`safe_redirect`, con el mensaje como toast.

| Clave POST | Botón y modal nativos | Efecto (servicio) | Mensajes |
|---|---|---|---|
| `mandarLegales` | «Derivar a legales»; «Confirmar derivar a Legales» | `marcar_como_enviado_a_legales`: `enviado_legales=True`, `estado_legales="Enviado a Legales"`, `estado_admision="enviado_a_legales"` | «La admisión fue enviada a legales correctamente.» / «La admisión ya estaba marcada como enviada a legales.» |
| `btnIFInformeTecnico` | «Cargar Informe Técnico -GDE» | `IFInformeTecnicoForm` (`forms/admisiones_forms.py:1510`) guarda en la admisión; luego `cargar_if_informe_tecnico` → `if_informe_tecnico_cargado` | «Número IF del Informe Técnico guardado correctamente.» / «Error en el formulario. Verifique los datos.» / «Error al guardar el número IF del Informe Técnico.» |
| `btnDisponibilizarAcomp` | «Comenzar Acompañamiento»; «Confirmar disponibilizar a acompañamiento» | En una transacción: `AcompanamientoService.importar_datos_desde_admision` (`acompanamientos/acompanamiento_service.py:358`), `enviado_acompaniamiento=True`, `estado_legales="Acompañamiento Iniciado"`, `estado_admision="enviado_a_acompaniamiento"` | «Se envió a Acompañamiento correctamente.» / «Error al enviar a Acompañamiento.» |
| `btnRectificarDocumentacion` | «Rectificar Documentación» | `enviado_legales=True`, `estado_id=2`, `estado_legales="Rectificado"`, `observaciones=None` | «Se rectificó la documentación.» / «Error al querer realizar la rectificación.» |
| `btnFinalizarCargaDocumentacion` | «Finalizar carga documentación» | `finalizar_carga_documentacion` → `documentacion_carga_finalizada` | «Carga de documentación finalizada correctamente.» / «No se pudo finalizar la carga de documentación.» |
| `btnCaratulacion` | «Caratular expediente» | `CaratularForm` inválido: re-render con el modal abierto. Válido: `guardar_caratulacion` → `cargar_expediente` → `expediente_cargado` | «Caratulación del expediente guardado correctamente.» / «Error al guardar la caratulación.» |
| `confirmar_tipo_convenio` | modal inicial | `confirmar_tipo_convenio_desde_organizacion`: tipo de convenio resuelto, `convenio_seleccionado`, validaciones de plantilla, congelado y snapshot documental | «Tipo de convenio precargado desde la organización.» / «No se pudo resolver el Tipo de Convenio desde el Tipo de Entidad de la organización.» / «No tiene permisos para confirmar estas validaciones.» |
| `guardar_validaciones_template` | formulario de validaciones | `ValidacionesTemplateAdmisionForm` (`:497–552`) | «Validaciones de templates guardadas correctamente.» / «No se pueden modificar las validaciones después de generar el Informe Técnico.» / «No tiene permisos para modificar estas validaciones.» / errores del Form unidos |

Visibilidad de botones (`impl.py:3431–3495`), que React reproduce desde `botones`
del endpoint de lectura y nunca calcula por su cuenta:

- `comenzar_acompaniamiento`: técnico, `numero_convenio` y sin
  `enviado_acompaniamiento`.
- `rectificar_documentacion`: `estado_legales == "A Rectificar"`.
- `finalizar_carga_documentacion`: técnico, `documentacion_aprobada` y sin
  expediente.
- `caratular_expediente`: técnico, `documentacion_carga_finalizada` y sin
  expediente.
- `if_informe_tecnico`: técnico, `informe_tecnico_aprobado` y sin
  `numero_if_tecnico`.
- `mandar_a_legales`: técnico, `if_informe_tecnico_cargado` y sin
  `enviado_legales`.

`ValidacionesTemplateAdmisionForm`:

- incorporación: `es_ex_pnud` obligatorio; si es «si» y falta
  `estado_convenio_pnud`, error «Debe indicar el estado del convenio PNUD.»;
- renovación: `tipo_renovacion`, `estado_financiamiento` e
  `informe_complementario_modifica_prestaciones` obligatorios;
- los campos del otro tipo se guardan vacíos.

### Cierre forzado (POST del detalle)

Clave `forzar_cierre` con `motivo_forzar_cierre`:

- la guarda repite los permisos de lectura: «No tiene permisos para realizar
  esta acción.»;
- motivo vacío: «El motivo del cierre forzado es obligatorio.»;
- efecto: `activa=False`, `motivo_forzar_cierre`, `estado_mostrar="Inactivada"`
  con la fecha de hoy, y `estado_legales="Inactivada"` si había estado legal o
  `estado_admision="inactivada"` si no;
- éxito: «La admisión ha sido cerrada forzadamente.»
  (`web_views.py:1442–1491`).

La misma vista acepta el documento personalizado (`archivo` + `nombre`, JSON
`{"success": true}` y errores «El archivo y el nombre son obligatorios.» / «El
abogado de la dupla no puede adjuntar archivos.») y `subir_docx_final`, ambos de
AD02. Un POST sin claves reconocidas se responde como GET.

### Acciones parciales AJAX

Todas devuelven JSON. Un error de negocio responde 400 con
`{"success": false, "error": ...}`, también por falta de permiso. Un objeto
inexistente cae en el `except` del servicio y devuelve 400 con el texto de la
excepción.

| Endpoint nativo | Entrada | Guardas, en orden | Escritura y efectos | Respuesta de éxito |
|---|---|---|---|---|
| `/ajax/actualizar-estado/` | `estado`, `documento_id`, `admision_id`, `observacion` | completos, si no «Datos incompletos.»; superusuario o dupla, si no «Sin permisos para modificar esta admision.» («Admision sin comedor asociado.»); ventana técnica: «No puede modificar documentos cuando el informe tecnico ya no esta iniciado ni en borrador.»; archivo de la admisión (404 → 400); con estado «rectificar» y grupo «Abogado Dupla», observación obligatoria: «Debe ingresar observaciones para rectificar.» | `ArchivoAdmision.estado` normalizado (pendiente, Documento adjunto, A Validar Abogado, Rectificar, Aceptado; otro valor se guarda tal cual), observación y `_actualizar_estados_por_cambio_documento` (rectificación, documentación finalizada o aprobada) | `{success, nuevo_estado, grupo_usuario, mostrar_select:false, opciones:[], gde_html, html, row_id}`; error genérico «No se pudo actualizar el estado.» |
| `/ajax/actualizar-numero-gde/` | `documento_id`, `numero_gde` | «ID de documento requerido.»; estado «Aceptado», si no «Solo se puede actualizar el número GDE en documentos aceptados.»; de origen organizacional: «El número de GDE de documentos de la Organización se gestiona desde el Legajo de la Organización.»; superusuario o dupla: «No tiene permisos para editar este documento.»; ventana técnica | `numero_gde` (vacío → null), limpia IF/GDE de la admisión y sincroniza el campo del informe en borrador (`InformeService.sincronizar_numero_gde_en_informe`) | `{success, numero_gde, valor_anterior, campo_informe_actualizado}` |
| `/ajax/actualizar-numero-gde-organizacion/` | `archivo_organizacion_id`, `admision_id`, `numero_gde` | «Faltan parametros admision o archivo de organizacion.»; «El archivo no pertenece a la organizacion de la admision.»; «Solo se puede actualizar el numero GDE en documentos aceptados.»; superusuario o dupla; ventana técnica | `NumeroGdeOrganizacion` (get_or_create por admisión y archivo) y limpieza de IF/GDE | `{success, numero_gde, valor_anterior}` |
| `/admisiones/<admision_pk>/resync-convenio/` | `accion` = `actualizar` o `continuar` | otra acción: «Accion invalida.»; **sin guarda de permiso** | `actualizar`: si cambió el tipo de entidad, `resync_admision_desde_organizacion` (nuevo tipo de convenio, `estado_id=1`, `convenio_seleccionado`, baja lógica de todos los `ArchivoAdmision`, nuevo snapshot y datos de la organización también en el informe); si no, `actualizar_documentacion_desde_organizacion` (dirigido). `continuar`: `aceptar_desincronizacion_admision` (solo mueve la línea de base). Todo en una transacción. | `{success, mensaje, redirect}` al editor; flash `success` («Admision actualizada desde el Legajo de la Organizacion.») o `info` («Continuara operando con la informacion actual de la admision.») |
| `/ajax/actualizar-convenio-numero/` | `admision_id`, `convenio_numero` | «ID de admision requerido.»; superusuario o técnico de dupla: «No tiene permisos para editar esta admision.»; entero: «Debe ingresar un numero valido.»; ≥ 0: «El numero de convenio no puede ser negativo.» | `convenio_numero` (vacío → null) | `{success, convenio_numero, valor_anterior}` |
| `/ajax/actualizar-vigente-pwa/` | `admision_id`, `vigente_pwa` (`1/true/on/si`) | «ID de admision requerido.»; superusuario o técnico de dupla | con `select_for_update` sobre las admisiones del comedor, desmarca las otras vigentes y guarda `vigente_pwa` (restricción `uniq_admision_vigente_pwa_por_comedor`) | `{success, vigente_pwa}` |
| `/ajax/actualizar-personas-conveniadas-nomina/` | `admision_id`, `personas_conveniadas_nomina` | «ID de admision requerido.»; superusuario o un permiso de lectura (**sin alcance por objeto**): «No tiene permisos para editar esta admision.»; programa Alimentar Comunidad: «Disponible solo para Alimentar Comunidad.»; entero ≥ 0: «Debe ingresar un numero valido.» / «El valor no puede ser negativo.» | `personas_conveniadas_nomina` (vacío → null) | `{success, personas_conveniadas_nomina}` |
| `/ajax/actualizar-num-expediente/` | `admision_id`, `num_expediente` | «ID de admisión requerido.»; «El número de expediente es obligatorio.»; formato `EX-\d{4}-\d{9}- -APN-[A-Z0-9]+#[A-Z0-9]+` sin distinguir mayúsculas: «Formato inválido. Use EX-AÑO-NÚMERO- -APN-REPARTICIÓN#ORGANISMO.»; duplicado (**antes del permiso**): «El expediente ya pertenece a la admisión #<pk>; comedor: <comedor>; organización: <org>; tipo: <tipo>.»; enviado a legales: «No se puede editar el expediente una vez enviado a legales.»; si no: «No tiene permisos para editar esta admisión.» | `num_expediente` en mayúsculas | `{success, num_expediente, valor_anterior}` |
| `/comedores/admisiones/<pk>/templates/reportar-faltante/` | `informe_id` opcional | superusuario o técnico de dupla, si no 403 vacío | `PlantillaInformeTecnicoService.reportar_configuracion_faltante`: crea o agrupa una incidencia de AD01 | redirect a `informe_tecnico_editar` o al editor; «La configuración pendiente fue registrada para que los referentes del sistema puedan revisarla.», «Esta admisión ya estaba registrada en una configuración pendiente.», «Ya existe una versión publicada para esta admisión.» o «El Informe Técnico no corresponde a la admisión indicada.» |

### API AD03.02

| Método y ruta | Reutiliza | Códigos |
|---|---|---|
| `POST <pk>/acciones/<accion>/` con `accion` en `derivar-legales`, `if-informe-tecnico`, `comenzar-acompanamiento`, `rectificar-documentacion`, `finalizar-carga-documentacion`, `caratular`, `confirmar-tipo-convenio`, `validaciones-template` | el handler `_procesar_post_*` o el servicio correspondiente, invocado por nombre y no por clave POST | 200 `{success, message, level, redirect?}`; 400 Form inválido (`CaratularForm`, `IFInformeTecnicoForm`, validaciones) con errores por campo; 404 acción o admisión desconocida |
| `POST <comedor_pk>/<pk>/forzar-cierre/` | `_handle_forzar_cierre_post` + `_aplicar_forzar_cierre_admision` | 200, 400 motivo vacío, 403 |
| `POST documentos/<archivo_id>/estado/` | `AdmisionService.actualizar_estado_ajax` | 200 con fila como datos; 400/403/404 |
| `POST documentos/<archivo_id>/numero-gde/` | `actualizar_numero_gde_ajax` | 200; 400; 403 |
| `POST <pk>/organizacion/archivos/<archivo_org_id>/numero-gde/` | `actualizar_numero_gde_organizacion_ajax` | 200; 400; 403; 404 |
| `POST <pk>/resync-convenio/` (`accion`) | `resync_convenio_admision` (misma transacción) | 200; 400 |
| `POST <pk>/convenio-numero/`, `<pk>/vigente-pwa/`, `<pk>/personas-conveniadas/`, `<pk>/num-expediente/` | servicios `*_ajax` | 200; 400; 403 |
| `POST <pk>/plantilla/reportar-faltante/` | `reportar_configuracion_faltante_template` | 200 `{message, level, redirect}`; 403 |

## AD03.03 — Transiciones legales y efectos [W]

Despacho del POST de `admisiones_legales_ver`:

1. `btnLegalesNumIF` con `LegalesNumIFForm` inválido: re-render con
   `modalLegalesNumIF` abierto.
2. Modales de providencia inválidos (`form_modal_invalido`, `:1299–1338`):
   re-render con el modal abierto y sus errores.
3. `LegalesService.procesar_post_legales` (`:1340–1401`), primera clave presente.

Toda excepción no capturada da «Error inesperado al procesar el POST de
legales.». Las respuestas son redirects al detalle legal con mensaje flash.

| Clave POST | Botón | Origen visible (`get_botones_disponibles`) | Efecto | Mensajes |
|---|---|---|---|---|
| `btnObservaciones` | «Rectificar» (`modalRectificar`, «Enviar a Rectificar») | «Enviado a Legales» sin `legales_num_if`, o «Rectificado»/sin estado antes del formulario y la primera providencia | `LegalesRectificarForm`: `estado_id=3`, `observaciones`, `estado_legales="A Rectificar"` | «Enviado a rectificar con éxito.» / «Error al enviar a rectificar.» |
| `btnLegalesNumIF` | «Agregar Número de expediente» | sin `legales_num_if` | `LegalesNumIFForm` → `estado_legales="Expediente Agregado"` | «Número de IF guardado correctamente.» / «Error al guardar el número de IF.» |
| `btnProyectoConvenio` | «Formulario Proyecto de Convenio» | «Expediente Agregado» o complementario validado | `ProyectoConvenioForm`; PDF WeasyPrint `admisiones/pdf/<tipo>_pdf_proyecto_convenio_<sufijo>.html` y DOCX `<tipo>_docx_proyecto_convenio_<sufijo>.docx` (sufijo base, juridica o juridica_eclesiastica); el DOCX puede faltar; → «Formulario Convenio Creado» | «Formulario guardado y documentos generados correctamente.» / «Formulario guardado y PDF generado correctamente. (DOCX no disponible)» / «Error al guardar el formulario Proyecto de Convenio.» / «Error inesperado al guardar formulario Proyecto de Convenio: <error>» |
| `btnConvenioNumIF` | «IF Proyecto de Convenio» | «Formulario Convenio Creado» | `ConvenioNumIFFORM` → «IF Convenio Asignado» | «Número IF de Proyecto de Convenio guardado correctamente.» / «Error al guardar el número IF de Proyecto de Convenio.» |
| `btnPrimeraProvidencia` | «Generar Primera Providencia» | «IF Convenio Asignado» (validado en servidor) | `PrimeraProvidenciaForm` con `es_judicializado` del comedor; variante base, cinco_comedores o judicializados; PDF + DOCX; → «Formulario Primera Providencia Creado» | «Primera Providencia generada correctamente.» / «Error al generar la Primera Providencia.» / «No se puede generar la Primera Providencia: el expediente está en estado '<estado>'.» |
| `btnGDEPVPrimera` | «Cargar número de GDE PV» | «Formulario Primera Providencia Creado» (validado) | `ProvidenciaGDEPVForm` → «IF Primera Providencia Asignado» | «Número de GDE PV de la Primera Providencia guardado correctamente.» / «Todavía no se generó la Primera Providencia.» |
| `btnSegundaProvidencia` | «Generar Segunda Providencia» | «IF Primera Providencia Asignado» (validado) | requiere la primera con GDE PV; PDF + DOCX `segunda_providencia.docx`; → «Formulario Segunda Providencia Creado» | «Segunda Providencia generada correctamente.» / «Primero debe generarse la Primera Providencia y cargarse su número de GDE PV.» |
| `btnGDEPVSegunda` | «Cargar número de GDE Segunda PV» | «Formulario Segunda Providencia Creado» (validado) | → «IF Segunda Providencia Asignado» | «Número de GDE PV de la Segunda Providencia guardado correctamente.» |
| `BtnIntervencionJuridicos` | «Intervención Jurídicos» | «IF Segunda Providencia Asignado» o el heredado «IF Disposición Asignado» | `IntervencionJuridicosForm`. Rechazo por dictamen con observación en el proyecto de convenio: se borran (hard delete) `FormularioProyectoDeConvenio` y `Providencia` y vuelve a «Expediente Agregado». Con observación en la providencia: se borran las `Providencia` y vuelve a «IF Convenio Asignado». Si no: «Juridicos: Validado» o «Juridicos: Rechazado». | «Intervención Jurídicos guardada correctamente.» / «Error al guardar Intervención Jurídicos.» |
| `btnConvenio` | «Convenio» | sin `numero_convenio` y «Juridicos: Validado», «Disposición Firmada» o `informe_sga` | `ConvenioForm` (multipart) → «Acompañamiento Pendiente» | «Convenio guardado correctamente.» / «Error al guardar el Convenio.» |
| `btnReinicioExpediente` | «Reinicio de Expediente» | «Juridicos: Rechazado» por providencia, o rechazo sin dictamen fuera de ese estado | `ReinicioExpedienteForm`, `enviada_a_archivo=True` → «Archivado» | «Reinicio de expediente guardado y enviado a archivo correctamente.» |
| `btnInformeComplementario` | «Solicitar Informe Técnico Complementario» | dictamen «observacion en informe técnico» sin complementario solicitado | `SolicitarInformeComplementarioForm`, `complementario_solicitado=True` → «Informe Complementario Solicitado» | «Informe complementario solicitado.» |
| `btnRevisarInformeComplementario` (o POST de `revisar_informe_complementario`) | «Revisar Informe Complementario» | «Informe Complementario Enviado» | `accion_complementario=validar`: estado `validado`, PDF final generado, → «Informe Complementario: Validado». `rectificar` con observaciones: estado `rectificar`, → «Informe Complementario Solicitado» | «Informe complementario validado correctamente. Se ha generado el PDF final.» / «Error al generar el PDF final del informe complementario.» / «Las observaciones son obligatorias para rectificar.» / «Informe complementario enviado a rectificar.» / «No se encontró informe complementario para revisar.» / «Acción no válida.» |
| `btnIFInformeComplementario` | «IF Informe Técnico Complementario» | complementario validado y PDF sin `numero_if` | guarda `numero_if` en el PDF y `_limpiar_flujo_anterior` (borra formulario y providencias, limpia jurídicos y vuelve a «Informe Complementario: Validado») | «Número IF del informe complementario guardado correctamente.» / «El número IF es obligatorio.» / «No se encontró PDF de informe complementario validado.» |
| `ValidacionJuridicos` | sin botón en el template | — | `validar_juridicos` → «Pendiente de Validacion» si se cumplen las condiciones | «Estado cambiado a 'Pendiente de Validacion'.» / «No se puede validar: asegúrese de completar el Proyecto de Convenio y las Providencias, y agregar el Número IF.» |

`actualizar_estado_por_accion` (`:254–284`) mapea las acciones a `estado_legales` y
hace un `save()` completo para recalcular `estado_mostrar`. Los cambios de
`Admision` generan `AdmisionHistorial` (`signals.py:15–61`) y
`HistorialEstadosAdmision` (`signals.py:84–172`) con el usuario de
`config.middlewares.threadlocals`: la API debe correr detrás del mismo middleware
para no perder el autor del historial.

Código sin entrada en la UI, fuera de alcance:

- `guardar_informe_sga` (`:375–393`) no está en el despacho;
- `btnDocumentoExpediente` existe en el template (`:815`) pero no tiene handler.

No se agrega ninguno de los dos.

### API AD03.03

| Método y ruta | Reutiliza | Códigos |
|---|---|---|
| `POST legales/<pk>/acciones/<accion>/` con `accion` en `rectificar`, `numero-expediente`, `proyecto-convenio`, `if-proyecto-convenio`, `primera-providencia`, `gde-pv-primera`, `segunda-providencia`, `gde-pv-segunda`, `intervencion-juridicos`, `convenio` (multipart), `reinicio-expediente`, `solicitar-complementario`, `if-complementario`, `validar-juridicos` | el método `LegalesService.guardar_*` correspondiente (o `enviar_a_rectificar`/`validar_juridicos`), con el `request` sintetizado del POST de la API. Los mensajes flash que agrega el servicio se drenan y se devuelven en `messages`, y se descarta su redirect. | 200 `{messages, estado_legales, botones}`; 400 con errores por campo cuando el Form es inválido (equivale al modal abierto); 409 si `_bloquear_fuera_de_secuencia` corta; 404 acción o admisión |
| `GET`/`POST legales/<pk>/complementario/revision/` | `InformeTecnicoComplementarioReviewView` + `revisar_informe_complementario` | 200; 400 |

Para la API, los errores de generación de PDF o DOCX llegan como el mensaje
nativo «Error inesperado al …: <error>» con 200 y `level: error`, igual que la
página Django.

Módulo React: `src/frontends/apps/sisoc/src/routes/admisionesLegales.tsx`.

## Implementación común

- Prefijo: agregar `api/web/comedores/` a `url_prefixes` de `comedores` en
  `src/backends/config/backends.json` (si otra entrega del runtime ya lo agregó,
  se reutiliza), y regenerar `src/backends/config/url_registry.json` con el
  comando del repo.
- Vistas DRF en `admisiones/web_api_views.py` (con `web_api_urls.py`):
  - `WebGatePermission` y autenticación de sesión;
  - CSRF en métodos no seguros;
  - `Cache-Control: private, no-store`;
  - nunca reintentar;
  - un 504 incierto lo maneja React releyendo el endpoint de lectura.
- El cuerpo de error conserva el texto nativo. La API corrige solo el código HTTP:
  - 403 para los textos de permiso;
  - 404 para el objeto inexistente, que se resuelve en la vista antes de llamar
    al servicio para no exponer el texto de `Http404`;
  - 409 para la secuencia legal.

  La UI Django no cambia.
- Transacciones y bloqueos: los mismos del servicio (`select_for_update` de PWA,
  `transaction.atomic` de resync, acompañamiento y providencias).

## Decisiones técnicas del agente

1. **Un endpoint por acción** en lugar de un POST multiacción. Así cada transición
   se prueba y se revierte por separado, y React no reproduce el orden de
   despacho por claves.
2. **Reutilizar los servicios que ya escriben mensajes** (`LegalesService`) y
   drenar `messages` en la API, en vez de reescribir los textos. Así se conserva
   cada texto sin copiarlo.
3. **Códigos HTTP correctos solo en la API nueva** (403/404/409) con el mismo
   texto. Mantener 400 para todo no sirve en JSON, y la API es nueva, así que no
   rompe a ningún consumidor.
4. **Botones desde el servidor**: React no recalcula la visibilidad. La
   asimetría de que los handlers no revaliden queda igual que hoy.
5. **Paridad de acceso**: se replican las brechas de abajo, según el precedente de
   T05 ([decisión](../../registro/decisiones/2026-11-10-2785-t05-programas-acceso-actual.md)),
   y los tests las fijan.

## Brechas nativas observadas (se conservan)

1. `resync_convenio_admision` no verifica permiso: cualquier usuario autenticado
   puede reconstruir la documentación de cualquier admisión. Los archivos tienen
   baja lógica (`SoftDeleteQuerySet.delete`), pero el estado vuelve a
   `convenio_seleccionado`.
2. `actualizar_personas_conveniadas_nomina` solo pide un permiso de lectura, sin
   alcance por objeto.
3. `actualizar_num_expediente` informa el duplicado (admisión, comedor,
   organización, tipo) antes de comprobar el permiso.
4. `admisiones_tecnicos_editar`, `admision_detalle` y `admisiones_legales_ver`
   resuelven el objeto por PK global. Las acciones del editor y del detalle legal
   (salvo providencias y GDE PV) no verifican rol ni estado de origen.
5. `AdmisionesTecnicosUpdateView` delega en `UpdateView.post` con
   `AdmisionForm(fields="__all__")` cuando ninguna clave coincide. La API no expone
   ese camino genérico: solo las acciones listadas.
6. `admisiones_legales_ajax` exige un conjunto de permisos distinto del listado
   legal (no acepta `expedientespagos.view_expedientepago`).
7. Los servicios AJAX devuelven `str(exception)` en el error.
8. En `AdmisionDetailView.get_object` el texto de 404 tiene mojibake
   («La admisiA3n no pertenece al comedor solicitado.»). Solo se ve con DEBUG.

## Dependencias

- [AD02](2026-10-28-2785-admisiones-informes-documentos-m2.md): editor embebido de
  informe y carátula, documentos y DOCX final.
- AD01: publicación de plantillas e incidencias que alimenta «reportar
  faltante».
- AC01: `btnDisponibilizarAcomp` llama a
  `AcompanamientoService.importar_datos_desde_admision`, y el complementario
  vuelve a `detalle_acompanamiento` con `origen=acompanamiento`. AC01 debe aceptar
  admisiones creadas por esta acción.
- CO07 (ficha del comedor): enlaza `admision_detalle`
  (`comedor/comedor_detail.html:1427`) y el nombre de los listados lleva a
  `comedor_detalle`.
- O02 (documentos de la organización): el número GDE de origen organizacional se
  edita allí y se replica (`replicar_numero_gde_desde_organizacion`); resync lee
  el legajo.
- Expedientes de pago y rendiciones (EX/RC): el detalle de admisión los muestra
  en solo lectura.
- DU01: el alcance depende de la dupla activa y de sus técnicos o abogado.

## Riesgos

- Una sola transición observable por tarea: AD03.02 se implementa en tres cortes
  (lecturas y acciones de documento; derivaciones de estado; resync y cierre
  forzado), y AD03.03 en dos (providencias y GDE; jurídicos, convenio y
  complementario).
- La generación de PDF y DOCX (WeasyPrint, plantillas) puede superar 30 s. El
  read timeout de 60 s y gunicorn en 65 s y 75 s
  (`docs/operacion/backends_por_servicio.md`) lo cubren, pero un 504 deja el
  resultado incierto. React no reenvía y vuelve a leer el estado.
- El borrado definitivo de formulario y providencias en jurídicos y en el IF del
  complementario es irreversible: se prueba solo con datos sintéticos.
- Historial: si la API no pasa por el middleware de threadlocals, se pierde el
  usuario.

## Casos de prueba

- Backend API (pytest):
  - alcance de los listados (superusuario, coordinador con y sin duplas,
    técnico, abogado, dupla inactiva, admisiones excluidas);
  - filtros, operadores y orden;
  - paginación y página inválida;
  - una prueba por acción con su estado de origen visible y uno no visible (fija
    la paridad: el handler igual ejecuta, salvo la secuencia legal, que da 409);
  - mensajes exactos;
  - efectos en `estado_admision`, `estado_legales`, `estado_mostrar` e
    historiales;
  - borrados definitivos de jurídicos;
  - `vigente_pwa` exclusivo bajo concurrencia;
  - regex y duplicado de expediente;
  - resync `actualizar` contra `continuar`, con y sin cambio de tipo de
    entidad;
  - las brechas 1–3 fijadas;
  - anónimo 401, requisito pendiente 403 y sin G1 403.
- Diferencial: base contra candidato sobre las rutas nativas, 0 diferencias fuera
  de `/api/web/comedores/`.
- Efectos: el POST nativo y la API dejan el mismo estado de base (hash de las
  filas de `Admision`, `ArchivoAdmision`, `Providencia`, historiales) sobre datos
  sintéticos aislados.
- React (vitest): toasts por nivel, modales con errores, una sola ejecución por
  confirmación, manejo de `uncertain`, foco.
- Visual (regla S13): listados, editor por estado y rol, detalle y detalle legal
  por estado, en escritorio y móvil. Estructura idéntica y diferencia perceptual
  ≤ 1 % sin antialiasing, con un tope de 8 minutos de diagnóstico por caso.

## Criterios de aceptación

1. Los listados devuelven el mismo conjunto, orden y celdas que la página nativa
   para cada actor y filtro.
2. Cada acción produce el mismo cambio de datos y muestra exactamente el texto
   nativo de las tablas de arriba.
3. Las URLs nativas siguen funcionando sin cambios y las nuevas solo existen bajo
   `/api/web/comedores/admisiones/`.
4. Ninguna mutación se reintenta sola.
5. Paridad visual S13 y orden de Tab igual a la página nativa.

## Incertidumbres

- No se ejecutó nada: no hubo app, base de datos, navegador ni tests. Los
  textos se tomaron del código.
- El contenido exacto de `LegalesService.get_legales_context` después de
  `:1420` (paginación de documentos) se leyó en parte. El DTO del detalle legal
  se fija al implementar, con un snapshot.
- Qué hace `AcompanamientoService.importar_datos_desde_admision` en AC01 (se leyó
  solo su ubicación).
- El orden de Tab de los modales legales.

## Estado de preparación

- AD03.01: ejecutable.
- AD03.02 y AD03.03: ejecutables con paridad de acceso (precedente T05). Si el
  responsable decide endurecer las brechas 1–4, el cambio va en otro trabajo que
  cubra Django y la API.
- Todas dependen del prefijo `api/web/comedores/` y de AD02 para el editor
  embebido.

## Fuente

`src/backends/comedores/admisiones/`:

- `urls/web_urls.py:130–334`;
- `views/web_views.py:69–230,270–414,416–658,660–1046,1049–1561,1779–2062`;
- `services/admisiones_service/impl.py:60–100,640–960,1055–1420,1700–1810,1977–2340,2577–3276,3278–3546,3833–3880`;
- `services/legales_service/impl.py:1–1420`;
- `services/admisiones_filter_config/impl.py`, `services/legales_filter_config/impl.py`;
- `forms/admisiones_forms.py:491–552`;
- `models/admisiones.py:36–390,401–420`;
- `signals.py:1–172`;
- `templatetags/admisiones_tags.py:50–230`;
- `templates/admisiones/admisiones_tecnicos_form.html:180–1340`;
- `templates/admisiones/admisiones_legales_detalle.html:30–860`.

Otras fuentes:

- `src/backends/comedores/acompanamientos/acompanamiento_service.py:358`;
- `src/backends/kernel/core/soft_delete/base.py:23–58`.
