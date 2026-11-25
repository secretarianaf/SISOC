# AD02: informes, revisión y documentos de admisión

E2: mapa inicial de preparación, con esquema contextual y transiciones precisados en suplemento; sin prueba runtime.
AD02.01 informes/metadatos; AD02.02 acciones; AD02.03 adjuntos/generación backend.
AD01 conserva configuración/publicaciones y AD03 circuito técnico/legal; AD02
consume sus contratos, no los reinventa dentro de componentes React.

## Rutas y acceso

Alta/editar/ver/descargarGDE con ANYlecturaficha; otras acciones tienen guards
propios. Resolver alta obtiene admisión globalPK; querysetinforme filtra solo tipo,
no actor/equipo. No atribuir scope de Comedores por provenir de ficha. Caracterizar
acceso y conservar reglas existentes, sin seguridad nueva o incidente acreditados.

Crear/editar informe_tecnico/<tipo>, tipos base/juridico; inválido mensaje→editor
admisiones_tecnicos_editar. GET/POSTForm, éxito mismoeditor. kwargs admision y
require_full=(action==submit): borrador no impone siempre campos de finalización.
Formbase/jurídico son ModelForm por exclusión; relaciones/estados/auditoríaservidor,
jurídico elimina resolucion_de_pago_1..6/monto_1..6 y ciertos avales/declaraciones;
base excluye validacion_registro_nacional/IF_relevamiento_territorial. FechaYYYY-MM-DD,
«no corresponde» depende admisión, MontoDecimalField no floatcliente. Schemaefectivo
requiere modelo+init+clean+render; no serializar modelo entero por Meta.exclude.

## Guardar y publicación

Submit exige documentos obligatorios cargados/aceptados. Alta repetida busca último
mismoadmisión/tipo; validado rechaza, no validado reutilizaPK/edición. Selecciona
publicación de plantilla por admisión en backend; errorplantilla deriva a draft.
Asigna actores/admisión servidor. Contexto publicación/error y detallecopiable de
combinación/tipoadmisión/convenio; React no elige versión arbitraria para continuar.
Máquina de revisión y regla del esquema efectivo se precisan abajo. Los campos
y snapshots del contrato implementado se verificarán por variante antes de activar.

## Detalle con acciones y complementario

POSTsubir_docx +docx_editado: requiere archivo, superusuario o técnico dupla y
estado «Docx generado»; servicio subir_docx_editado, feedback y safe retorno detalle.
OtrosPOST delegan procesar_revision_informe→editor técnico; capacidad no se infiere
de poder ver indicador. ComplementarioGET por tipo; POST claves campo_* novacías,
sin cambios rechaza; LegalesService revisa. No patchlibre antes de whitelist/servicio.

## Documentación: fila React, no HTML Django oculto

Upload clavearchivo, veto abogado sin técnico, superusuario o ventana técnica
permitida. update_or_create admisión/documentación; técnico bloqueado si últimoinforme
fuera Iniciado/borrador. Cambio documental postprocesa y limpia IF/GDE admisión:
no solo ficheroUI reemplazado, requiere efectos/historial y consumidorAD03.

Respuesta success/html/row_id/documento/estado_display/estado_valor/archivo_id usa
include documento_row.html actual. React debe construir fila con datos autorizados,
no mantener HTML de presentación Django ni asumir todos esos campos son DTO final.
PersonalizadoPOSTnombrestrip obligatorio≤255+archivo, superusuario/dupla y vetoabogado
solosin técnico;201success/documento/html, permiso403/resto400. Eliminar usa **DELETE**,
noPOST; login/vetoabogado/superusuario o dupla/ventana y reglas porestado/archivo.
Resto del servicio requiere lectura antes de afirmar contrato completo de baja.

## Binarios y futura verificación

Preview entrega DOCXtemporal sinpersistir/cambiarestado, guard de operar plantilla,
finalizado no preview. DescargaGDE superusuario/técnicodupla+estadoValidado: copiaDOC
últimoWordvalidado. Generación/conversión backend, no reescribir plantillas en React.

Casos sintéticos: base/jurídico, borrador/submitincompleto, altarepetida/validado,
publicaciónfaltante/fija, lector/técnico/abogado-mixto/superusuario, requeridoaceptado,
upload/reemplazo/DELETE/filaReact, DOCXeditado estadoincorrecto, campo_*ajeno/vacío,
errorgeneración y retorno. Guards/efectos y renderdocumento requieren pruebasfuturas;
referencia/candidato/diff porURL/estado/rol desktop-móvil/foco y acumulado. Nada
se ejecutó, no estadoAPI o permisos finales inventados a partir del título.

## Fuente y próximo mapa

src/backends/comedores/admisiones/urls/web_urls.py:171–249;
views/web_views.py:176–180,227–354,662–789,1012–1045,1563–1752,1881–1940;
forms/admisiones_forms.py:555–608,745–779;
services/informes_service/impl.py:542–556,1265–1337;
services/admisiones_service/impl.py:1809–1874,2637–2669.
Vistasweb/Formadmisiones/Serviceinformes contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; serviciodocumentalcheckout. Padre leyó
postprocesado/filadocumental. CodeGraphsync, sin app/tests/DB/PDF/navegador/remote.
Siguiente: schemaefectivobase-jurídico y guardar/revisión/documentos completos,
sin empezar simultáneamente gestoresAD01 y circuitolegalAD03.

- [FichaComedor y admisión](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Aceptación y documentos backend](2026-10-27-2785-aceptacion-riesgos-y-retiro.md).

## Contrato contextual y transiciones consolidados

### Elección técnica resuelta por el agente

Usar un catálogo explícito de controles React y grupos visuales existentes. El
backend construye el Form con admisión/tipo/acción reales y proyecta únicamente
campos autorizados que sobreviven a su configuración: presencia, obligatoriedad,
inicial, opciones y errores. No esquema de modelo completo ni generador universal
que admita campos o permisos arbitrarios. No dependencia nueva. Validación y
publicación siguen del lado del dueño; la lectura de un campo no concede escritura.

Draft usa require_full=False; submit True. Ambos Forms eliminan resoluciones/montos
1..6 y campos sustituidos de antecedentes/conclusiones/acreditaciones. Renovación,
ex-PNUD, avales, modificación de prestaciones y antecedentes de renovaciones
condicionan campos. «No corresponde»/fecha aplica solo a personería eclesiástica en
incorporación/renovación; fuera de condición rechaza, dentro limpia fecha. Último
convenio solo renovación. Representante no se precarga desde referente por analogía.
Antecedentes se guardan con helper existente, no con JSON arbitrario de cliente.
Omitido, vacío y retirado son distintos: no borrar historia por ocultar controles.

### Guardado y resultado observable

| Operación | Efecto fuente y resultado que debe mostrar React |
|---|---|
| Draft | Prepara o reabre Iniciado+borrador, puede conservar datos incompletos |
| Submit sin documentos aceptados | Rechazo de dominio, no finalización ficticia |
| Submit con error de publicación | Guarda borrador y devuelve successFalse/saved_as_draftTrue; no «nada persistido» |
| Submit válido | Resuelve publicación backend, genera DOCX, registra actores/M2M, congela documentación organizacional y transiciona admisión |
| Error de generación | Solicita rollback y retorna editable según envolvente actual; no cola/retry automático inventados |

Conservar transacción del caller/servicio y estado antes de devolver éxito. No
prometer que el rollback DB revierta archivos físicos. Alta repetida reutiliza
último no validado; validado rechaza. Submit limpia observaciones de subsanación.

### DOCX, revisión y archivos

Generación requiere publicación/versión y usa generar_docx_con_version_publicada.
Contenedor InformeTecnicoPDF se actualiza por admisión con tipo/informe/comedor/
archivo/versionado, aunque el nombre diga PDF; estado Docx generado. Validado no
regenera. Upload editado cambia a Docx editado y dispara enviar_informe_revision.
Aprobación usa el Word técnico final, no genera otro archivo al aprobar.

Revisión acepta A subsanar o Validado; otro valor no actúa. Subsanar transiciona,
reemplaza CampoASubsanar desde lista normalizada y guarda observación. Validado
transiciona y limpia pendientes. Excepciones se registran y vista retorna editor;
no error estructurado transaccional garantizado por el comportamiento actual.

DELETE documental resuelve archivo dentro de admisión con documentación/archivo_id/
fallbackID; veto abogado sin técnico, ventana y estado son guardas previas.
preview=1|true mantiene autorización y no ejecuta. Ejecución normal baja lógica
ArchivoAdmision, no hard=True interno ni borrado físico automático. Limpia IF/GDE;
puede quitar Documentacion no ligada a convenio ni archivos activos. Resultado
indica fila catálogo vacía frente a personalizado retirado. React usa datos de
fila/acción para sustituir HTML de Django conservando aspecto, mensajes y foco.

### Gates de implementación, no nuevas decisiones rutinarias

1. Snapshots base/jurídico × incorporación/renovación × draft/submit y condiciones
   PNUD/eclesiástica/antecedentes; whitelist efectiva y errores por campo/globales.
2. Efectos de borrador guardado tras error, rollback de generación y subsanación:
   contrastar persistencia, actores, estados, historia y publicación fijada.
3. Regresión de guardas por acción; no permiso global nuevo ni ampliar lectura.
4. Preview/DELETE/Word/descarga y feedback/retornos como circuito completo M2.
5. Referencia/candidato/diff por URL, estado, rol y viewport; documentos backend
   con datos sintéticos, render y aceptación separados.

Evidencia adicional: forms/admisiones_forms.py:180–310,436–452,555–919;
services/informes_service/impl.py:942–964,1265–1472,1620–1723;
views/web_views.py:707–831;
services/admisiones_service/impl.py:1809–1973,2637–2658,3922–3928.
Vistas/Forms/InformeService ya comparados al snapshot; guardas documentales checkout.
Padre contrastó error de plantilla→draft. No ejecución o contrato API aceptado.

## Actualización 2026-11-10: contrato ejecutable AD02

Base de lectura: HEAD `4ea95bcbe`, runtime `comedores` (`backend_comedores`). El
protocolo G1 v1 está aprobado
([decisión](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md)), así
que las APIs nuevas de este contrato viven bajo `/api/web/comedores/`. Esta
sección completa el esquema por campo que faltaba y fija rutas, API, módulo React,
criterios y pruebas. Lo anterior de este documento sigue vigente salvo las
correcciones explícitas de abajo.

### Correcciones contra el código actual

1. **Carga de archivo de catálogo** (`subir_archivo_admision`,
   `views/web_views.py:660–704`): la ruta solo exige sesión (`@login_required`) y
   `POST`; no tiene `permissions_any_required` en la URL
   (`urls/web_urls.py:171–175`) ni verifica superusuario o dupla.
   `AdmisionService.handle_file_upload` (`services/admisiones_service/impl.py`)
   solo aplica `_validar_modificacion_documental_por_tecnico`, que afecta al técnico
   de la dupla. El texto anterior («superusuario o ventana técnica permitida») se
   lee como alcance por objeto y no lo hay: cualquier usuario autenticado que no sea
   abogado sin rol técnico puede cargar en cualquier admisión. Se conserva (ver
   «Paridad de acceso» abajo).
2. **Alta y edición en las páginas propias del informe**
   (`InformeTecnicosCreateView`/`UpdateView`, `views/web_views.py:1563–1679`): no
   llaman a `AdmisionService.puede_editar_informe_tecnico`; esa guarda solo la
   aplica el editor embebido de `admisiones_tecnicos_editar`
   (`views/web_views.py:1264–1309`). Basta uno de los tres permisos de lectura de la
   URL.
3. **Revisión del informe** (`InformeTecnicoDetailView.post`,
   `views/web_views.py:1737–1752`, `InformeService.procesar_revision_informe`,
   `services/informes_service/impl.py:1432–1473`): no hay guarda de rol ni de
   dupla; cualquier usuario con uno de los permisos de lectura de la URL puede
   pasar el informe a «A subsanar» o «Validado» por POST directo. La vista siempre
   redirige al editor técnico, aun cuando el estado no es válido.
4. Los Forms quitan `resolucion_de_pago_1..6` y `monto_1..6` antes de marcar
   obligatorias las resoluciones 1–4 de renovación
   (`forms/admisiones_forms.py:599–601`, `636–641`, `782–784`, `816–822`): esa
   obligatoriedad es código muerto. Confirmado, no se reproduce.

### Rutas nativas AD02

Todas con `LoginRequiredMixin` o `@login_required`. «Lectura» significa
`permissions_any_required(["comedores.view_comedor", "admisiones.view_admision",
"acompanamientos.view_informacionrelevante"])` en la URL.

| URL exacta | Nombre | Métodos | Vista | Guarda adicional | Template / respuesta |
|---|---|---|---|---|---|
| `/admision/<admision_id>/documentacion/<documentacion_id>/subir/` | `subir_archivo_admision` | POST | `web_views.py:662` | veto abogado sin técnico | JSON |
| `/admision/<admision_id>/documentacion/<documentacion_id>/eliminar/` | `eliminar_archivo_admision` | DELETE | `web_views.py:708` | veto abogado, superusuario o dupla, ventana técnica, estado | JSON |
| `/admision/<admision_id>/documentacion/personalizada/agregar/` | `documento_personalizado_crear` | POST | `web_views.py:1014` | veto abogado, `_verificar_permiso_documento_personalizado` | JSON 201/400/403 |
| `/comedores/admision/informe_tecnico/<tipo>/<admision_id>/crear/` | `informe_tecnico_crear` | GET, POST | `web_views.py:1563` | lectura; `tipo` en `base`/`juridico` | `admisiones/informe_tecnico_form.html` |
| `/comedores/admision/informe_tecnico/<tipo>/<pk>/editar/` | `informe_tecnico_editar` | GET, POST | `web_views.py:1626` | lectura | `admisiones/informe_tecnico_form.html` |
| `/comedores/admision/informe_tecnico/<tipo>/<pk>/previsualizar/` | `informe_tecnico_previsualizar_template` | GET | `web_views.py:278` | superusuario o técnico de dupla; no finalizado | DOCX adjunto |
| `/comedores/admision/informe_tecnico/<tipo>/<pk>/descargar-para-gde/` | `informe_tecnico_descargar_para_gde` | GET | `web_views.py:336` | lectura + superusuario o técnico de dupla; estado `Validado` | DOC adjunto |
| `/comedores/admision/informe_tecnico/<tipo>/<pk>/ver/` | `informe_tecnico_ver` | GET, POST | `web_views.py:1681` | lectura; POST `subir_docx` con superusuario o técnico de dupla | `admisiones/informe_tecnico_detalle.html` |
| `/comedores/admision/informe_complementario/<tipo>/<pk>/ver/` | `informe_complementario_ver` | GET, POST | `web_views.py:1913` | lectura | `admisiones/informe_tecnico_complementario_detalle.html` |

`revisar_informe_complementario` (`urls/web_urls.py:316`) es la revisión legal del
complementario: el catálogo la lista en AD02, pero su efecto es una transición de
`estado_legales`; este contrato la deja en AD03.03 para no partir el circuito legal.

### Esquema efectivo por campo

Fuente: modelo `InformeTecnico` (`models/admisiones.py:483–1072`), Forms
`InformeTecnicoJuridicoForm` (`forms/admisiones_forms.py:555–742`) e
`InformeTecnicoBaseForm` (`forms/admisiones_forms.py:745–919`), helpers
`_configurar_campos_informe_2233` (`:180–307`), `_prellenar_*` (`:328–433`) y
`_configurar_selectores_geograficos` (`:79–161`). El template agrupa los campos;
la tabla sigue el orden del modelo.

#### Reglas generales de obligatoriedad

- `draft` construye el Form con `require_full=False`; `submit`, con
  `require_full=True` (`_build_informe_form_kwargs`, `web_views.py:176–180`, y
  `web_views.py:1286–1292`).
- Todo campo presente queda `required = require_full`, salvo los opcionales fijos:
  `if_relevamiento`, `no_corresponde_fecha_vencimiento`,
  `validacion_registro_nacional` (solo existe en jurídico) y
  `fecha_vencimiento_mandatos` cuando se permite «No corresponde»
  (`:615–632`, `:798–813`).
- En borrador, un valor no vacío igual se valida por tipo: email, fecha
  `YYYY-MM-DD`, entero ≥ 0, `max_length`, choices y catálogo.
- Mensajes de error del Form: el mensaje global de la vista es
  «No se pudo guardar el informe. Revisá los campos: » seguido de
  `<etiqueta>: <errores>` unidos por « | »; sin errores listables,
  «No se pudo guardar el informe. Verificá que los campos obligatorios estén
  completos.» (`web_views.py:142–167`).

#### Campos nunca editables (servidor)

Excluidos en ambos Forms: `admision`, `estado`, `estado_formulario`, `tipo`,
`creado`, `modificado`, `creado_por`, `modificado_por`,
`observaciones_subsanacion`. Quitados en `__init__` de ambos:
`resolucion_de_pago_1..6`, `monto_1..6`, `antecedentes_renovaciones` (se escribe
con `_guardar_antecedentes_informe_2233`), `conclusiones` (se deriva de
`criterio_seleccionado`), `acreditaciones_ultimo_convenio`,
`monto_total_conveniado_informe`, `monto_total_conveniado`.

Solo base excluye `validacion_registro_nacional` e `IF_relevamiento_territorial`.
Solo jurídico excluye `declaracion_jurada_recepcion_subsidios`,
`constancia_inexistencia_percepcion_otros_subsidios`, `organizacion_avalista_1`,
`organizacion_avalista_2` y `material_difusion_vinculado`.

#### Organización solicitante y representante

| Campo | Etiqueta | Tipo / límite | Base | Jur. | Inicial |
|---|---|---|---|---|---|
| `expediente_nro` | Número Expediente | texto 100 | sí | sí | `admision.num_expediente` |
| `nombre_organizacion` | Nombre de la Organización Solicitante | texto 255 | sí | sí | snapshot de la admisión (`datos_organizacion_informe`), solo informe nuevo |
| `domicilio_organizacion` | Domicilio de la Organización Solicitante | texto 255 | sí | sí | snapshot |
| `localidad_organizacion` | Localidad de la Organización Solicitante | select de catálogo `Localidad`, guarda el nombre | sí | sí | snapshot |
| `partido_organizacion` | Partido de la Organización Solicitante | texto 255 | sí | sí | snapshot |
| `provincia_organizacion` | Provincia de la Organización Solicitante | select de catálogo `Provincia`, guarda el nombre | sí | sí | snapshot |
| `telefono_organizacion` | Teléfono de la Organización Solicitante | texto 50 | sí | sí | snapshot |
| `mail_organizacion` | Mail de la Organización Solicitante | email | sí | sí | snapshot |
| `cuit_organizacion` | CUIT de la Organización Solicitante | texto 20 | sí | sí | snapshot |
| `representante_nombre` | Nombre y Apellido del Representante | texto 255 | sí | sí | vacío (no se precarga del referente, `:685–691`) |
| `representante_cargo` | Cargo del Representante | texto 100 | sí | sí | vacío |
| `representante_dni` | DNI del Representante | texto 20 | sí | sí | vacío |
| `fecha_vencimiento_mandatos` | Fecha de vencimiento de mandatos | fecha `YYYY-MM-DD` | sí | sí | `organizacion.fecha_vencimiento` si el informe no tiene fecha ni «No corresponde» |
| `no_corresponde_fecha_vencimiento` | No corresponde fecha de vencimiento | checkbox | sí | sí | instancia |

Regla «No corresponde» (`_permite_no_corresponde_fecha_vencimiento`, `:436–452`):
se permite solo si la admisión es `incorporacion` o `renovacion` y el tipo de
convenio normalizado es «personeria juridica eclesiastica». Errores de `clean()`:

- marcado sin permiso: «No corresponde para este tipo de convenio.» en
  `no_corresponde_fecha_vencimiento`;
- en submit, con permiso, sin fecha ni marca: «Debe informar una fecha o marcar
  "No corresponde".» en `fecha_vencimiento_mandatos`;
- marcado y válido: la fecha se guarda vacía.

#### Espacio comunitario

| Campo | Etiqueta | Tipo / límite | Inicial |
|---|---|---|---|
| `tipo_espacio` | Tipo de Espacio Comunitario | select: Comedor, Merendero, Punto de Entrega, Comedor y Merendero | `comedor.tipocomedor` |
| `nombre_espacio` | Nombre del Comedor/Merendero | texto 255 | `comedor.nombre` |
| `domicilio_espacio` | Domicilio del Comedor/Merendero | texto 255 | calle + número, o «Sin definir» |
| `domicilio_electronico_espacio` | Domicilio electronico constituido del Comedor/Merendero | email, opcional en el modelo | instancia |
| `barrio_espacio` | Barrio del Comedor/Merendero | texto 255 | `comedor.barrio` |
| `localidad_espacio` | Localidad del Comedor/Merendero | select de catálogo | `comedor.localidad` |
| `partido_espacio` | Partido del Comedor/Merendero | texto 255 | `comedor.partido` |
| `provincia_espacio` | Provincia del Comedor/Merendero | select de catálogo | `comedor.provincia` |

`domicilio_electronico_espacio` tiene `blank=True` en el modelo, pero el bucle de
`__init__` lo vuelve obligatorio en submit como al resto.

#### Responsable de la tarjeta

`responsable_tarjeta_nombre` (255), `responsable_tarjeta_cuit` «CUIL/CUIT del
Responsable de la Tarjeta» (255), `responsable_tarjeta_dni` (20),
`responsable_tarjeta_domicilio` (255), `responsable_tarjeta_localidad` (select de
catálogo), `responsable_tarjeta_provincia` (select de catálogo),
`responsable_tarjeta_telefono` (50), `responsable_tarjeta_mail` (email). Etiquetas
«<Dato> del Responsable de la Tarjeta». En un informe nuevo de un comedor de
Alimentar Comunidad se precargan desde los campos homónimos del comedor
(`_prellenar_informe_nuevo`, `:340–364`).

#### Documentación y números GDE

| Campo | Etiqueta | Base | Jur. | Precarga GDE (`admisiones/utils.py:89–123`) |
|---|---|---|---|---|
| `nota_gde_if` | Nota GDE IF | sí | sí | «Nota de solicitud e inclusion al programa» |
| `constancia_subsidios_dnsa` | Constancia IF RTA DNSA sobre subsidios | sí | sí | «Acta de solicitud de subsidio» |
| `constancia_subsidios_pnud` | Constancia IF RTA PNUD sobre subsidios | sí | sí | «Respuesta memo PNUD» |
| `partido_poblacion_destinataria` | Partido donde se ubica la población destinataria | sí | sí | — |
| `provincia_poblacion_destinataria` | Provincia donde se ubica la población destinataria | sí | sí | — (select de catálogo) |
| `if_relevamiento` | IF Relevamiento (jurídico) / IF de relevamiento territorial (base) | sí, opcional | sí, opcional | relevamiento PAC / PAC-AC en base |
| `IF_relevamiento_territorial` | IF Relevamiento Territorial | no | sí | relevamiento PAC / PAC-AC en jurídico |
| `validacion_registro_nacional` | Validación Registro Nacional Comedores/Merenderos | no | sí, opcional | «Validacion RENACOM» |
| `declaracion_jurada_recepcion_subsidios` | Declaración Jurada sobre recepción de subsidios nacionales | sí | no | — |
| `constancia_inexistencia_percepcion_otros_subsidios` | Constancia de inexistencia de percepción de otros subsidios nacionales | sí | no | — |
| `organizacion_avalista_1` | Organización Avalista 1 | sí | no | — |
| `organizacion_avalista_2` | Organización Avalista 2 | sí | no | — |
| `material_difusion_vinculado` | Material de difusión vinculado | sí | no | — |

Todos texto de 255. La precarga GDE escribe `form.initial` solo mientras
`informe_admite_replica_gde` es verdadero (sin guardar, `Iniciado` o `borrador`,
`utils.py:191–205`). Con el informe finalizado o validado se muestra lo guardado.

#### Condiciones del circuito 2233 (`:180–307`)

| Campo | Etiqueta | Aparece solo si | Submit |
|---|---|---|---|
| `finalizacion_convenio_pnud_vigente` | Finalización de Convenio PNUD Vigente | incorporación, `es_ex_pnud == "si"` y `estado_convenio_pnud == "vigente"`; widget fecha | obligatorio |
| `expediente_incorporacion` | Expediente de Incorporación | renovación; inicial: `num_expediente` de la primera incorporación del comedor | obligatorio |
| `convenio_incorporacion` | Convenio de Incorporación | renovación; inicial: `numero_convenio` de esa incorporación | obligatorio |
| `presentacion_avales` | Presentación de Avales | renovación y tipo base | obligatorio |
| `informe_tecnico_complementario_modificacion_prestaciones` | Informe Técnico Complementario - Modificación de Prestaciones | renovación y `informe_complementario_modifica_prestaciones == "si"` | obligatorio |
| `if_it_complementario` | IF IT Complementario | mismas condiciones | obligatorio |
| `criterio_seleccionado` | Criterio seleccionado | siempre: A - Coincidencia, B - Solicitud Menor, C - Solicitud Mayor, D - Equivalencias | obligatorio; al guardar escribe `conclusiones` con la etiqueta |
| `antecedente_<pk>_resolucion` | Resolución / Disposición de Renovación | renovación con `tipo_renovacion == "segunda_o_posterior"`, una fila por cada renovación anterior del comedor (orden `creado`, `pk`); texto 255 | obligatorio |
| `antecedente_<pk>_convenio` | Convenio de Renovación | ídem | obligatorio |
| `antecedente_<pk>_expediente` | Expediente de Renovación | ídem | obligatorio |
| `antecedente_<pk>_incluir` | Incluir en el informe | ídem; checkbox, inicial verdadero | opcional |

Los antecedentes toman su inicial de lo guardado en `antecedentes_renovaciones`
o, si falta, de la admisión anterior (`numero_disposicion`, `numero_convenio`,
`num_expediente`). Un campo ausente por condición no se borra en la base: el
modelo conserva el valor anterior.

#### Prestaciones

- `solicitudes_<comida>_<dia>` (28 enteros ≥ 0, base y jurídico).
- `aprobadas_<comida>_<dia>` (28 enteros ≥ 0, base y jurídico).
- `aprobadas_ultimo_convenio_<comida>_<dia>` (28 enteros ≥ 0): solo renovación y
  obligatorios en submit. En un informe nuevo de renovación se precargan con las
  `aprobadas_*` del informe finalizado efectivo de la admisión activa anterior
  (`ComedorService.get_informe_tecnico_finalizado_efectivo`).

Comidas: `desayuno`, `almuerzo`, `merienda`, `cena`. Días: `lunes`, `martes`,
`miercoles`, `jueves`, `viernes`, `sabado`, `domingo`. Sin etiqueta propia
(`label = False`, `aria-label` vacío): el template rotula filas y columnas.
Jurídico agrega las clases `form-control form-control-sm text-center`.

#### Cierre del informe

`total_acreditaciones` «Total de acreditaciones a Producir» (150, inicial «6») y
`plazo_ejecucion` «Plazo de Ejecución» (150, inicial «6 meses»), en ambos Forms.

#### Selects de catálogo

`provincia_organizacion`, `localidad_organizacion`, `provincia_espacio`,
`localidad_espacio`, `responsable_tarjeta_provincia`,
`responsable_tarjeta_localidad` y `provincia_poblacion_destinataria` usan
`CatalogoNombreSelectField` (`:16–76`). Las provincias listan todo el catálogo.
Las localidades solo listan el vacío y el valor seleccionado, y se completan por
provincia con `ajax_load_localidades`. Un valor histórico fuera del catálogo se
ofrece como «<valor> (valor histórico fuera del catálogo)». Un PK desconocido da
«Seleccione una opción válida del catálogo.». Lo que se guarda es el nombre, no
el PK.

### API web propuesta (`/api/web/comedores/admisiones/`)

Todas con sesión, `WebGatePermission` y CSRF, y respuesta
`Cache-Control: private, no-store`. Cada vista repite las guardas de su vista
nativa, sin agregar ni quitar ninguna (ver «Paridad de acceso»). Ninguna mutación
se reintenta sola: un 504 con `uncertain: true` se muestra como resultado
desconocido y React vuelve a leer el estado.

| Método y ruta | Reutiliza | Respuesta |
|---|---|---|
| `GET informes/<tipo>/nuevo/<admision_id>/` | `InformeService.get_admision_y_tipo_from_kwargs`, `get_form_class_por_tipo` con `admision` | 200 esquema proyectado (abajo); 404 admisión; 400 tipo fuera de `base`/`juridico` con «El tipo de informe seleccionado no está disponible para carga online.» |
| `POST informes/<tipo>/nuevo/<admision_id>/` (`action=draft|submit`, urlencoded) | mismo Form + `_handle_informe_tecnico_form_valid` | 200 `{informe_id, redirect}`; 400 errores por campo y global con los textos nativos; 409 con «El informe técnico ya fue validado y no puede editarse.» |
| `GET`/`POST informes/<tipo>/<pk>/` | `InformeTecnicosUpdateView` (mismo Form y servicio) | igual al anterior |
| `GET informes/<tipo>/<pk>/detalle/` | `InformeService.get_context_informe_detail` | 200 datos del detalle y `mostrar_revision_tecnico` |
| `POST informes/<tipo>/<pk>/docx-editado/` (multipart `docx_editado`) | `_handle_subir_docx_editado_post` → `InformeService.subir_docx_editado` | 200 «DOCX enviado a validar correctamente.»; 400 «Debe seleccionar un archivo DOCX.»; 403; 409 «Estado inválido para subir el DOCX editado del informe técnico.» |
| `POST informes/<tipo>/<pk>/revision/` (`estado`, `campos_a_subsanar[]`, `observacion`) | `InformeService.procesar_revision_informe` | 200 `{redirect}` al editor técnico; un estado fuera de `A subsanar`/`Validado` no hace nada, como en la nativa |
| `GET`/`POST informes-complementarios/<tipo>/<pk>/` (`campo_*`) | `InformeTecnicoComplementarioDetailView` + `InformeService.guardar_campos_complementarios` + `LegalesService.actualizar_estado_por_accion(..., "enviar_informe_complementario")` | 200 «Informe complementario enviado para validación.» con `redirect` (acompañamiento si `origen=acompanamiento`); 400 «No se han realizado cambios en el informe.» |
| `POST <admision_id>/documentos/<documentacion_id>/archivo/` (multipart `archivo`) | `AdmisionService.handle_file_upload` + `_serialize_documentacion` | 200 fila como datos (`row_id`, `documento`, `estado_display`, `estado_valor`, `archivo_id`), sin `html`; 403 veto abogado; 400 sin archivo o no guardado |
| `DELETE <admision_id>/documentos/<documentacion_id>/archivo/` (`?archivo_id=`, `?preview=1`) | mismo orden de guardas de `eliminar_archivo_admision` + `AdmisionService.delete_admision_file` | 200 `{nombre, personalizado, documento?}` o `{preview}`; 403/400 con los textos nativos |
| `POST <admision_id>/documentos/personalizados/` (multipart `nombre`, `archivo`) | `AdmisionService.crear_documento_personalizado` | 201 `{documento}`; 403; 400 |

La previsualización (`/comedores/admision/informe_tecnico/<tipo>/<pk>/previsualizar/`)
y la descarga para GDE (`/comedores/admision/informe_tecnico/<tipo>/<pk>/descargar-para-gde/`)
siguen siendo GET nativos que devuelven el archivo. React solo enlaza a esas URLs:
no hay binarios por JSON ni API nueva.

Esquema proyectado (un mismo formato para alta y edición): `{fields: [{name,
label, widget, required, max_length, choices, initial, value, errors,
grupo}], antecedentes: [{admision_id, campos}], permite_no_corresponde,
template: {publicacion, error, detalle_copiable}, estado, estado_formulario,
campos_a_subsanar, observacion, non_field_errors}`. Sale del Form ya construido:
solo incluye los campos que sobreviven a `__init__`. El catálogo de grupos
visuales vive en React y reproduce `informe_tecnico_form.html`.

### Módulo React

`src/frontends/apps/sisoc/src/routes/admisionesInformes.tsx` (con su test). Cubre
las URLs nativas de crear, editar, ver y complementario, con sus slashes. El editor
embebido de `admisiones_tecnicos_editar` reutiliza el mismo componente de
formulario desde AD03.02. Documentos: una fila React (`DocumentoRow`) construida
con los datos de la respuesta, no con el HTML de `documento_row.html`.

### Criterios de aceptación

1. Para base y jurídico, en incorporación y renovación, en borrador y en submit,
   y con PNUD, eclesiástica y segunda renovación, el esquema React tiene
   exactamente los campos, las etiquetas, la obligatoriedad y las opciones del
   Form nativo.
2. Un borrador incompleto se guarda. El submit incompleto muestra
   «No se pudo guardar el informe. Revisá los campos: …» con las mismas etiquetas
   y errores.
3. Un submit con documentos faltantes o sin validar muestra, respectivamente,
   «No puede finalizar el informe técnico si faltan documentos obligatorios por
   cargar.» o «No puede finalizar el informe técnico si hay documentos
   obligatorios sin validar.».
4. Un error de publicación de plantilla guarda borrador y muestra el error de la
   plantilla, sin afirmar que no se guardó nada.
5. El éxito del editor embebido muestra «Informe técnico guardado
   correctamente.».
6. La subida del DOCX final muestra «DOCX final subido correctamente. El informe
   está ahora en revisión.». Un estado inválido muestra «Estado inválido para
   subir el DOCX final del informe técnico.».
7. Documentos: «El abogado de la dupla no puede adjuntar archivos.»,
   «El abogado de la dupla no puede eliminar archivos.»,
   «No se pueden eliminar documentos cuando el informe tecnico esta finalizado o
   en etapas posteriores.», «No se puede eliminar un documento en estado aceptado
   o a validar abogado.» y «Metodo no permitido» (405 en la nativa), con el mismo
   resultado en datos.
8. La vista previa y la descarga GDE devuelven el mismo nombre de archivo y tipo
   (`vista-previa-informe-<pk>.docx`, `informe-<pk>-para-gde.doc`).
9. Paridad visual S13 por URL, estado, rol y viewport: estructura idéntica y
   diferencia perceptual ≤ 1 % sin contar antialiasing.

### Casos de prueba

- Backend API: un snapshot del esquema por cada variante del criterio 1;
  draft/submit; alta repetida (reutiliza el último no validado, rechaza el
  validado); publicación faltante; guardas de rol y estado por acción (lector,
  técnico, abogado mixto, abogado solo, superusuario); `campo_*` vacío; fila
  React tras carga, reemplazo, DELETE con y sin `preview`; personalizado sin
  nombre o con nombre de 256 caracteres.
- Contraste de efectos: estado de la admisión, `InformeTecnicoPDF`,
  `CampoASubsanar`, historial y limpieza de IF/GDE iguales entre el POST nativo y
  la API, sobre datos sintéticos aislados.
- Diferencial: las rutas nativas no cambian (requests base contra candidato,
  0 diferencias fuera de `/api/web/comedores/`).
- React (vitest): render por variante, una sola ejecución del POST, manejo de
  `uncertain`, foco en el primer error.
- Visual: casos de referencia y candidato en escritorio y móvil, con un tope de
  8 minutos de diagnóstico por caso.

### Paridad de acceso

Las brechas de las correcciones 1–3 se replican tal cual, según el precedente de
T05 ([decisión](../../registro/decisiones/2026-11-10-2785-t05-programas-acceso-actual.md)).
Los tests de la API las fijan para que un arreglo posterior tenga que cambiarlos
de forma explícita. Si el responsable decide endurecerlas, el cambio va en otro
trabajo y cubre a la vez las vistas Django y la API.

### Estado de preparación

AD02.01, AD02.02 y AD02.03 son ejecutables con el criterio de paridad anterior.
Dependen de G1 v1 (integrado), de que se agregue `api/web/comedores/` a
`url_prefixes` de `comedores` en `src/backends/config/backends.json` (y se
regenere `url_registry.json`) y del marco de la ficha de admisión de AD03.02
para el editor embebido. AD01 (publicaciones) se consume sin modificarlo.
