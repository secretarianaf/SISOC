# Rendiciones mensuales y proyectos de organizaciones

## Asociación de proyecto

`RendicionCuentaMensual.proyecto` es la relación principal con
`ProyectoOrganizacion`. Para registros históricos se conserva el fallback por
`comedor.codigo_de_proyecto`; los listados, notificaciones y el detalle no
deben excluir datos legados cuando esa relación nueva todavía sea nula.

La PWA ofrece los proyectos activos de la organización y persiste el proyecto
seleccionado en la rendición. La publicación de SISOC y SISOC-Mobile debe ser
coordinada cuando cambie este contrato.

## Revisión y subsanaciones

- Validar u observar documentos no cambia por sí solo el estado global: la
  etapa se resuelve al finalizar la revisión.
- Territorial mantiene la rendición `En revisión` al derivarla a Auditoría.
  Solo el cierre satisfactorio de Auditoría finaliza la presentación.
- Una subsanación conserva la etapa que la originó. Al reanudar Auditoría se
  preservan documentos ya validados; solo el primer inicio restablece los
  documentos heredados desde Territorial.
- La gestión de Auditoría usa una pantalla propia dentro de Rendiciones,
  con validación obligatoria Sí/No, acta, resultado y observaciones
  condicionales, sin montos (issue #2673). Ver el apartado Auditoría conjunta.
- Una solicitud de documento faltante se registra por categoría, aun cuando la
  categoría ya tenga archivos. La PWA habilita esa categoría durante la
  subsanación y la solicitud se cierra al adjuntar un archivo nuevo.
- Los documentos previamente validados conservan su estado al reenviar una
  subsanación.

## Etapas, permisos y estados visibles

El flujo tiene cinco etapas: `Carga de documentación`, `Revisión Territorial`,
`Revisión para Carga`, `Auditoría` y `Regularización`. Las acciones se
autorizan con permisos Django configurables por grupo:

- `manage_territorial_stage`
- `manage_auditoria_review_stage`
- `manage_auditoria_stage`
- `manage_regularizacion_stage`

El permiso de etapa habilita listado, detalle, descarga y acciones de esa
etapa, pero no concede por sí solo edición de datos generales, creación o
eliminación. La interfaz y los POST aplican la misma comprobación de permisos.

`Revisión para Carga` es solamente la denominación visible de la etapa cuyo
valor persistido sigue siendo `revision_auditoria` (issue #2377). La constante
`ETAPA_REVISION_AUDITORIA`, los nombres de permisos y los `value` de los filtros
no cambiaron. No debe confundirse con la etapa independiente `Auditoría`
(`auditoria`). Cualquier consumidor —la PWA incluida— tiene que distinguir el
estado por `etapa_proceso` + `subestado_proceso`, nunca por la etiqueta.

El filtro `Estado` combina `etapa_proceso` y `subestado_proceso`, y refleja el
texto visible de la columna. `Estado general` mantiene el filtro histórico.
`Etapa` incluye las cinco opciones del modelo. Los datos generales requieren
fecha de inicio y fin del período, aunque esos campos sigan siendo anulables
para preservar registros históricos.

Una solicitud de documento faltante puede acumularse durante la revisión. La
etapa deriva a subsanación al finalizar la revisión si queda alguna solicitud
activa; al adjuntar un archivo nuevo se cierra la solicitud de su categoría.
Las observaciones quedan visibles debajo de la categoría solicitada.

## Auditoría conjunta (issue #2673)

Desde el listado se accede a «Nueva Auditoría» y se selecciona una rendición
existente en Auditoría pendiente o en curso. Desde el detalle se accede con
sus datos generales precargados. Ambos caminos requieren el permiso
`manage_auditoria_stage`; no crean nuevas rendiciones ni modifican datos
generales. La selección manual admite búsqueda por organización, proyecto y
período. El filtro predeterminado es Proyecto; la búsqueda se aplica en el
servidor y devuelve una tabla paginada con acción «Gestionar» por fila.
Al abrir o limpiar la pantalla no se listan rendiciones. El texto de búsqueda
es obligatorio, incluidos los envíos directos al servidor. Proyecto consulta
solo código/nombre del proyecto (con fallback al código del comedor legado);
Organización consulta solo su nombre. Las coincidencias son parciales y no
distinguen mayúsculas ni tildes españolas, normalizando entrada y columnas
consultadas sin depender de una collation concreta.
Período admite `MM/AAAA`, `DD/MM/AAAA`, `AAAA` y sus variantes ISO, buscando
rendiciones cuyos períodos se superponen con la fecha o ventana ingresada.
No se definió un alta de auditorías sin rendiciones en el issue.

`validada` es un booleano nullable para conservar los históricos sin atribuirles
una validación inexistente. En los paneles `NULL` y `False` se muestran como
«Validada: No». La gestión usa un check obligatorio; no permite guardar una
respuesta negativa. Una vez persistida como verdadera, la validación se muestra
como «Sí» y no se puede modificar, tampoco mediante POST.

El primer ingreso permite guardar solo el check, sin decidir sobre el acta:
queda `validada=True`, `genera_acta_auditoria=NULL`, subestado `en_curso` y
`fecha_gestion_auditoria=NULL`. Se vuelve al detalle base y se puede reingresar.
Al reingresar validada, la decisión de acta Sí/No es obligatoria. Si se elige
Sí/No ya en el primer ingreso, también se puede validar y cerrar en un solo paso.
El botón dice «Guardar» cuando se guarda solo la validación y «Guardar y cerrar
Auditoría» cuando se toma la decisión de acta o la validación ya estaba guardada.

Guardar una decisión explícita Sí/No registra `fecha_gestion_auditoria` y
cierra la gestión individual: no puede reabrirse desde el detalle, el buscador
ni por GET/POST directo. Con No conserva el subestado interno `en_curso` por
compatibilidad y muestra «Auditoría validada sin acta». Continúa siendo
elegible como rendición adicional de un acta posterior, sin volver a editarla.
Esa etiqueta exige validación afirmativa, decisión No, gestión cerrada y
subestado `en_curso`; no reemplaza el resultado de auditorías ya finalizadas.
Guardar solo la validación no habilita su inclusión en otra acta: antes debe
cerrarse con decisión No.
Para generar acta, la rendición actual debe estar validada y se exige resultado;
las observaciones son obligatorias únicamente para un resultado con observaciones.
El archivo de acta y el Acta Complementaria siguen siendo opcionales.

La rendición actual se incluye automáticamente y aparece marcada y bloqueada
en la lista de inclusión. Las otras opciones son casillas sin buscador. El selector adicional ofrece
rendiciones activas en Auditoría pendiente/en curso, del mismo código de
proyecto y organización, `validada=True`, `genera_acta_auditoria=False` y sin
archivo de acta.
También exige `fecha_gestion_auditoria` para excluir rendiciones que todavía
no fueron auditadas, aunque tengan otros datos precargados. La fila de la
rendición actual es compacta, gris y marcada como inclusión fija.
Incluye el fallback histórico por comedor; no limita la
selección a dos períodos. Mantiene la regla previa por línea: solo Línea
Tradicional admite rendiciones incluidas, y únicamente de Línea Tradicional. Se muestra un resumen documental por rendición seleccionada.
En el detalle se omiten el título y los desplegables de documentación incluida
si validación y generación de acta están ambos sin definir. El formulario de
gestión es una pantalla transitoria para Volver; vuelve al detalle o a los
resultados según el origen, conservando los filtros mediante la navegación
unificada. El detalle tiene como destino jerárquico el listado de rendiciones.

El guardado bloquea las filas en orden de PK y vuelve a validar la elegibilidad
dentro de la transacción. Replica validación, acta, resultado, observaciones
(solo con resultado con observaciones; nunca vacía las existentes),
Acta Complementaria y las relaciones del grupo; los archivos se almacenan una
sola vez. El cierre impide volver a gestionar la auditoría, pero si finaliza
con observaciones mantiene el proceso de regularización existente: «Iniciar
regularización» y, cuando está en curso, carga de Acta Complementaria y
«Finalizar regularización». Estas acciones requieren `manage_regularizacion_stage`
y están permitidas aunque haya acta afirmativa y fecha de cierre de auditoría,
únicamente desde la rendición que originó el acta. `rendicion_origen_acta`
identifica esa base en todos los integrantes; el valor Sí replicado a una
rendición incorporada no le habilita acciones de regularización. El servicio
también rechaza acciones enviadas directamente desde una incorporada.
Una rendición sin origen registrado (Línea Secos o acta legada no conciliada)
gestiona su propia regularización, como antes, sin propagarla a otras.
Las transiciones y el documento complementario se replican al grupo, incluso
si sus validaciones históricas son NULL, con bloqueo de filas en orden de PK.
Los campos de validación, decisión, inclusión y origen del acta no son editables
desde el formulario general. La tarjeta «Acciones del proceso»
se muestra únicamente si existe una acción autorizada para el estado actual.
Las actas cerradas no se pueden reabrir desde esta pantalla. Los formularios y servicios históricos de proceso se conservan como
compatibilidad para sus callers existentes; los POST antiguos de auditoría en
el detalle redirigen a la pantalla nueva sin escribir ni cerrar la rendición.

El legajo de organización omite Monto Auditado y Observaciones en listado y
detalle. Aplicar `rendicioncuentasmensual.0023_issue_2673_validada` con el
migrador antes de publicar el core nuevo, seguida de
`rendicioncuentasmensual.0024_cierre_gestion_auditoria` y
`rendicioncuentasmensual.0025_origen_acta_auditoria`. La 0025 recupera la base
de grupos históricos coherentes por el orden de inserción de sus vínculos
(el guardado insertaba primero los de la base); los casos inconsistentes
quedan sin origen y cada rendición regulariza por separado, como antes.
La 0024 solo agrega `fecha_gestion_auditoria`: no hay gestiones históricas
con validación registrada que cerrar.
No hace falta publicar otros backends
ni modificar contratos de la PWA.

## Contrato de carga

- Convenios admitidos: `P01`, `P02`, `P03`.
- Números de rendición admitidos: `1` a `6`.
- El número debe ser además **el siguiente de la secuencia** dentro del mismo
  proyecto y convenio: si el último es 2, el único valor aceptado es 3. La regla
  vive en `RendicionCuentaMensualService` y la aplican por igual el alta y la
  edición, en web y en API; no se delega en la PWA. Participan los borradores y
  quedan afuera las bajas lógicas, así que dar de baja una rendición libera su
  número. Editar sin cambiar el número no revalida la secuencia.
- La asignación del número se serializa con `select_for_update()` sobre la fila
  ancla del scope (proyecto, o comedor en el camino legado) dentro de la misma
  transacción que escribe, para que dos altas concurrentes no tomen el mismo.
- No se admiten períodos anteriores al último ya gestionado para el mismo
  convenio y proyecto, ni solapamientos.
- Inicio y fin deben pertenecer al mismo mes, **salvo en
  `Abordaje Comunitario - Línea Secos`**, donde el fin puede llegar hasta el
  último día del tercer mes calendario contado desde el mes de inicio
  (03/09 → 30/11). El cálculo usa el calendario real, no una cantidad fija de
  días. El error se devuelve en el campo `periodo_fin`.
- Las validaciones acumulan todos los errores y se devuelven identificados por
  campo (`convenio`, `numero_rendicion`, `periodo_inicio`, `periodo_fin`,
  `periodo`), para que la PWA los pueda mostrar junto al campo correspondiente.
- Formulario I, ambos Formulario V, Formulario VI y Extracto Bancario admiten
  múltiples archivos. Los comprobantes se separan entre Prestación Alimentaria
  y SIPH, y se muestran como `Facturas y Tickets Prestación Alimentaria` y
  `Facturas y Tickets SIPH` (cambio de etiqueta; los códigos
  `comprobantes_alimentario` y `comprobantes_siph` no cambian).
- El catálogo documental depende de la línea programática:
  `Planilla de Seguros` no se pide en `Línea Secos` y sí en `Línea Tradicional`.
  Web y API lo resuelven con `RendicionCuentaMensualService.obtener_categorias_visibles`,
  que además sigue mostrando las categorías desactivadas para la línea cuando la
  rendición ya tiene documentos históricos cargados en ellas.

## Despliegue y validación

Aplicar `rendicioncuentasmensual.0017`, luego
`rendicioncuentasmensual.0018` y finalmente
`rendicioncuentasmensual.0019_reconciliar_comprobantes_legacy` antes de usar
solicitudes de faltantes o permisos por etapa. La última migración reconcilia
la categoría legacy de comprobantes, también en registros con baja lógica.
Antes de aplicarla en producción, tomar un backup recuperable y detener las
instancias que aún puedan escribir `comprobantes`; validar después que no queden
filas con esa categoría. Configurar los grupos desde Usuarios > Grupos y
asignar únicamente los permisos de las etapas que correspondan.

Para una prueba local aislada, usar
`python manage.py seed_rendicion_stage_examples --comedor-id <id>`. El comando
solicita de forma interactiva una contraseña de al menos 12 caracteres, crea
cuatro usuarios/grupos QA y cuatro rendiciones en el comedor indicado, y es
idempotente. No ejecutarlo sobre datos productivos: está destinado a QA local
o de entorno controlado.
Validar una rendición nueva con proyecto, una histórica con fallback, una
subsanación de Territorial y otra de Auditoría antes de promover a producción.

## Referencias

- `src/backends/comedores/rendicioncuentasmensual/services.py`
- `src/backends/comedores/gestion_organizaciones/views.py`
- `docs/registro/cambios/2026-T3/2026-08-10-fixes-admisiones-pwa-rendiciones.md`
- `docs/registro/cambios/2026-T3/2026-08-12-correcciones-issues-reabiertos.md`
