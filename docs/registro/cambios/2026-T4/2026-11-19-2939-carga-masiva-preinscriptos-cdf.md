# Cambio: carga masiva de preinscriptos de Centros de Familia (#2939)

## Alcance

Nueva pantalla para cargar preinscriptos desde la plantilla Excel oficial, separada del formulario de preinscripción. Se entra con el botón "Carga masiva" del listado de preinscriptos, tanto en la pantalla Django como en la React. El flujo:

1. Descargar la plantilla.
2. Subir el archivo.
3. Revisar la vista previa validada fila por fila, y editar o quitar filas.
4. Confirmar: se cargan las filas sin error y se rechazan las demás.
5. Descargar el comprobante.

También hay historial de lotes, registro de ediciones, descarga del archivo original y de las filas con error, eliminación de lotes pendientes y opción para deshacer el último lote cargado.

Código:

- Vertical `cdf`:
  - `src/backends/cdf/centrodefamilia/services/carga_masiva/`: columnas, lectura y generación de Excel, validación y ciclo de vida del lote.
  - `src/backends/cdf/centrodefamilia/views/carga_masiva.py` y `src/backends/cdf/centrodefamilia/templates/carga_masiva/`.
  - Migración `src/backends/cdf/centrodefamilia/migrations/0018_carga_masiva_preinscriptos.py`.
- React:
  - `src/backends/cdf/centrodefamilia/web_api_beneficiarios.py`: la URL de carga masiva, solo si el usuario tiene el rol.
  - `src/frontends/apps/sisoc/src/routes/cdfDataTable.tsx`: botones adicionales del buscador.
  - `src/frontends/apps/sisoc/src/routes/cdfBeneficiarios.tsx`: muestra el botón.

## Reglas de negocio vigentes

Definidas en el issue y ajustadas por el área el 24/11/2026.

| Regla | Comportamiento |
|---|---|
| Archivo | Solo `.xlsx` de la plantilla oficial, hasta 10 MB y 500 filas con datos. Se cortan las hojas con más de 10.000 filas leídas. |
| Desplegables | Provincia, municipio y localidad tienen lista desplegable. El municipio depende de la provincia elegida y la localidad del municipio (hoja oculta "Ubicaciones"). |
| Obligatorios | Además de los del issue, el vínculo con el titular, la actividad preferida y el máximo nivel educativo. La calle es **opcional** para preinscripto y titular, en la carga masiva y en el formulario de preinscripción (modelo, JS nativo y React). |
| Edad | El preinscripto tiene que tener entre 6 y 17 años inclusive al validar. Con 18 cumplidos la fila se rechaza. |
| Preinscripto y titular | No pueden tener el mismo CUIL, el mismo DNI ni la misma fecha de nacimiento. |
| Preinscripto repetido | Se carga la primera fila y se rechaza la otra. |
| Preinscripto dado de baja | Se reactiva con los datos del Excel. |
| Titular repetido | Puede repetirse con distintos preinscriptos y vínculos. Los datos salen de su primera fila que se carga. |
| Titular existente | El Excel actualiza **todos** sus datos, incluidos nombre, apellido, sexo y fecha de nacimiento, y avisa qué columnas cambian. Solo es error que el DNI y el CUIL pertenezcan a dos titulares distintos. |
| Dato opcional vacío o mal cargado | La fila se carga sin ese dato y lo avisa en el comprobante. |
| Filas con error | Al confirmar se cargan las válidas y se rechazan las demás. El comprobante lista cada fila como cargada o "Rechazada", con sus motivos. |
| RENAPER | Apellido, nombre y fecha de nacimiento del preinscripto **y del titular** tienen que coincidir con RENAPER, comparando sin mayúsculas, tildes ni espacios repetidos ("Juan" no coincide con "Juan Carlos"). Si no coinciden, la fila se rechaza y el motivo muestra el dato de RENAPER para corregirlo. También se rechaza si RENAPER no encuentra a la persona o informa que falleció. Si RENAPER no informa un dato, ese dato no se compara. |
| Deshacer | Solo el último lote confirmado, y solo si nadie modificó o dio de baja después sus preinscriptos. |
| Retención (90 días) | Los lotes **pendientes** se eliminan completos a los 90 días de subidos: filas, ediciones, consultas a RENAPER y archivo original. Los confirmados y deshechos se conservan. |
| Observaciones | No se agrega: el área lo descartó. |
| Permiso | Rol nuevo `auth.role_cdf_carga_masiva`, en el grupo "Centros de Familia Carga Masiva" y en el grupo de administración. |

## Decisiones técnicas (sección 12 del issue)

- **DT-01**: tres modelos nuevos.
  - `CargaMasivaPreinscriptos`: el lote, con archivo, estado (pendiente, confirmado o deshecho), totales y auditoría.
  - `FilaCargaMasivaPreinscriptos`: número de fila original, celdas como texto en JSON, estado, motivos, si se quitó, acción prevista, titular y el estado previo para deshacer.
  - `EdicionCargaMasivaPreinscriptos`: usuario, fecha, fila, columna y valor anterior y nuevo, o "fila quitada".
- **DT-02**: la validación se procesa dentro del request: cada una hace pocas consultas agrupadas (padrón, existentes y catálogos). Cada edición revalida el lote entero, lo que resuelve las filas dependientes (repetidos y titular compartido).
- **RENAPER por tandas**: 500 consultas no entran en un pedido web (gunicorn corta a los 65 segundos) y no hay un worker para CDF en el servidor. Por eso se consulta así:
  - La vista previa pide tandas de 8 personas a `beneficiarios/carga-masiva/<id>/renaper/` (`static/custom/js/carga_masiva_renaper.js`) y muestra el avance.
  - Cada persona (DNI y sexo) se consulta una sola vez por lote y se guarda en `ConsultaRenaperCargaMasiva`.
  - Editar nombre o fecha revalida sin volver a consultar; cambiar DNI o sexo deja a la persona pendiente.
  - Si se cierra la página, la verificación sigue al volver.
  - Una falla técnica de RENAPER deja a la persona pendiente para reintentar.
  - No se puede confirmar con personas pendientes.
  - Al confirmar, la respuesta se guarda en `BeneficiariosResponsablesRenaper`, como en el formulario, y las consultas del lote se borran.
- **DT-03**: validación de CUIL, normalización de sexo y generación de Excel propias del vertical, porque las del kernel son privadas o están atadas a RENAPER. Del kernel se reutiliza `neutralize_csv_formula`.
- **DT-04**: el vínculo de cada fila se guarda en `BeneficiarioResponsable`. `Responsable.vinculo_parental` solo se completa al crear el titular.
- **DT-05**: la confirmación no usa `BeneficiarioForm` ni `ResponsableForm`. Busca con `all_objects` (incluye bajas), asigna campos explícitos y reactiva con `restore(cascade=False)`. `creado_por` se completa solo al crear.
- **DT-06**: FK opcional `Beneficiario.carga_masiva_origen`. Vacío significa que vino del formulario.
- **DT-07**: la plantilla se genera al descargarla con los catálogos vigentes. Un archivo se acepta solo si tiene la hoja "Preinscriptos" con los encabezados exactos en orden; se toleran mayúsculas y espacios.
- **DT-08**: los catálogos se comparan sin mayúsculas, tildes ni espacios repetidos. Un nombre que coincide con más de un registro se trata como no reconocido (S-02).
- **Deshacer**: al confirmar, cada fila guarda qué creó y cómo estaba antes lo que reactivó o actualizó (preinscripto, titular y vínculo).
  - Lo creado se borra definitivamente.
  - Lo reactivado o actualizado vuelve al estado previo, incluida la baja.
  - Un titular creado por el lote se conserva si mientras tanto le asociaron otro preinscripto.
  - Un titular modificado después de la carga no se restaura.
  - La condición "nadie modificó esos preinscriptos" se controla con `fecha_modificado` y `deleted_at` posteriores a la confirmación.

## Diferencias con el issue

Cambios del área sobre lo que decía el issue, a informar:

- **RN-05/RN-06**: ya no es todo o nada. La confirmación igual es atómica: si falla la carga de una fila no se carga ninguna.
- **RN-09**: se puede deshacer el último lote.
- **RN-04**: se puede eliminar un lote pendiente, con sus filas, ediciones y archivo original.
- **RN-14/RN-17**: un formato inválido en una columna opcional (mail, altura, teléfono, etc.) ya no es error: es advertencia y la fila se carga sin ese dato.
- **RN-26 y S-03**: el titular existente se actualiza completo, sin error por identidad distinta.
- **RN-01**: el acceso deja de ser `view_centro` y pasa al rol propio.
- **Sección 3.2 y RNF-03**: ahora la carga masiva consulta RENAPER, por tandas.
- **RN-04 y RNF-02**: además de eliminarlos a mano, los lotes pendientes se eliminan solos a los 90 días.
- **RF-13 y columna 30**: Observaciones se eliminó; la plantilla tiene 51 columnas.

## Retención de 90 días

- La regla del área ("los datos de menores se guardan 90 días") se definió con el equipo como: eliminar los lotes que nadie confirmó.
- **Cuándo corre:** la purga corre cada vez que alguien abre el historial de carga masiva. No depende del cron del servidor: según `docs/infra/PROD_CHANGE_PROPOSALS.md`, el cron de `purge_auditlog` apunta a rutas que ya no existen.
- **Cuándo puede no correr:** si nadie abre la pantalla, los lotes vencidos siguen guardados hasta la próxima vez.
- **Opción para infraestructura:** el comando `python manage.py purgar_cargas_masivas_pendientes [--dias 90]` permite programarla en el servidor.

## Seguridad y permisos

- Todas las pantallas y descargas exigen `auth.role_cdf_carga_masiva` (`ROLE_CDF_CARGA_MASIVA_PERMISSION` en `access.py`). El botón del listado se muestra solo con ese rol.
- El grupo "Centros de Familia Carga Masiva" (rol más `centrodefamilia.view_centro`) lo crea `create_groups` al arrancar. Se asigna desde la administración de usuarios.
- **Riesgo aceptado por el equipo**: el rol habilita descargar el archivo original, el listado de errores y el comprobante, que contienen datos personales de menores.
- El archivo original se guarda con nombre aleatorio en `centrodefamilia/cargas_masivas/` y se descarga solo por la vista con permiso. Si producción sirve `/media/` directamente, el nombre aleatorio evita que se adivine, pero no reemplaza un almacenamiento privado.
- Las descargas neutralizan textos que empiezan con `=`, `+`, `-` o `@`. Las fórmulas del archivo subido no se ejecutan: se lee el valor calculado (`data_only`). `defusedxml` ya está instalado y `openpyxl` lo usa.
- Las ediciones en la vista previa se aceptan solo para columnas de la plantilla, en lotes pendientes y con un máximo de 500 caracteres por celda.
- Confirmar, eliminar y deshacer bloquean el lote con `select_for_update` (RN-08). La confirmación revalida contra SISOC dentro de la misma transacción (RN-07).
- Las confirmaciones de "Quitar", "Eliminar" y "Deshacer" usan `data-confirm-submit` (`base.js`) y no `onsubmit` en línea, porque el CSP bloquea los handlers en línea.

## Otros cambios

- Se cierra un `<div class="container">` que estaba abierto en `beneficiarios_form.html`; el navegador ya lo cerraba solo. Hacía fallar `djlint` sobre el template tocado.
- Se regeneró `src/backends/config/url_registry.json` con las rutas nuevas.
- Zonas delicadas: migración, permiso nuevo y `src/backends/kernel/users/bootstrap/groups_seed.py` (kernel). Requiere revisión técnica.

## Verificación

- `pytest src/backends/cdf/centrodefamilia/tests/test_carga_masiva_preinscriptos.py`: 65 tests, con RENAPER simulado. Cubren los criterios de aceptación vigentes, las reglas nuevas, RENAPER (diferencias, no encontrado, fallecido, caído y reintento, una consulta por persona), deshacer, retención, permisos y los desplegables de la plantilla. CA-19 se prueba en secuencia: SQLite no permite reproducir dos transacciones simultáneas.
- `pytest src/backends/cdf` y los tests de grupos del kernel: pasan, salvo 2 tests de `test_admin_operaciones_cdf.py` (N+1 en `ParticipanteActividad`) que ya fallaban en development.
- Frontend: `vitest` de `cdfBeneficiarios` y `cdfPreinscripcion` (19 tests), `eslint` y `tsc` sin errores.
- `black`, `djlint` y `makemigrations --check` sin hallazgos. `pylint` no suma avisos: los de `views/beneficiarios.py` y `groups_seed.py` ya están en development. La migración se aplicó sobre MySQL local.
## Privacidad del archivo original

El XLSX original conserva su ubicación en el volumen de media y su política de
retención. No tiene URL pública de storage. La vista autenticada del lote sigue
verificando el permiso de carga masiva, entrega el original como adjunto y
responde con `Cache-Control: private, no-store`.

El servidor DEBUG bloquea el acceso directo al directorio de originales, sin
afectar la media pública de otros módulos. Antes de activar la carga masiva en
un entorno, el operador debe verificar que **cada vhost efectivo** tenga la
regla de denegación del prefijo CDF antes del alias general de media. Actualizar
la referencia versionada no instala la regla en el host. Validar con un archivo
sintético: ruta estática 404, descarga autorizada 200 y media pública ajena 200.
No se necesita mover originales ni ampliar los permisos de la aplicación.

## Navegación de regreso

El historial de cargas, las ediciones y la edición de fila reutilizan el botón
**Volver** de la aplicación, sin duplicarlo dentro de la pantalla. Sin historial,
el listado regresa a preinscriptos y las dos pantallas del lote regresan a su
vista previa. Se comprueban los tres destinos en el HTML renderizado.

## Respuestas simultáneas de RENAPER

Las consultas externas siguen fuera de la transacción. Al volver, se bloquea
el lote pendiente antes de guardar y revalidar. Una respuesta ya resuelta no
se reemplaza por una respuesta tardía; una falla técnica previa sí permite
reintentar. Dos tandas simultáneas aún pueden hacer la misma consulta externa.
