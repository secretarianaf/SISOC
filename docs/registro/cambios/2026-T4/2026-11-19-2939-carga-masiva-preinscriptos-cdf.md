# Cambio: carga masiva de preinscriptos de Centros de Familia (#2939)

## Alcance

Nueva pantalla para cargar preinscriptos desde la plantilla Excel oficial, separada del formulario de preinscripción y accesible desde el listado de preinscriptos (botón "Carga masiva"). El flujo es: descargar la plantilla, subir el archivo, revisar la vista previa validada fila por fila, editar o quitar filas, confirmar y descargar el comprobante. También hay historial de lotes, registro de ediciones, descarga del archivo original y descarga de las filas con error.

Se suma el campo **Observaciones** al preinscripto: se carga desde la columna 30 de la plantilla y también desde el formulario de preinscripción, y se muestra en el detalle.

Código en el vertical `cdf`:

- `src/backends/cdf/centrodefamilia/services/carga_masiva/`: columnas, lectura y generación de Excel, validación y ciclo de vida del lote.
- `src/backends/cdf/centrodefamilia/views/carga_masiva.py` y `src/backends/cdf/centrodefamilia/templates/carga_masiva/`.
- Migración `src/backends/cdf/centrodefamilia/migrations/0018_carga_masiva_preinscriptos.py`.

## Decisiones técnicas (sección 12 del issue)

- **DT-01**: tres modelos nuevos: `CargaMasivaPreinscriptos` (lote: archivo, estado pendiente o confirmado, totales y auditoría), `FilaCargaMasivaPreinscriptos` (número de fila original, celdas como texto en JSON, estado, motivos, quitada y acción prevista) y `EdicionCargaMasivaPreinscriptos` (usuario, fecha, fila, columna, valor anterior y nuevo, o "fila quitada").
- **DT-02**: todo se procesa dentro del request. Con el tope de 500 filas y sin RENAPER, cada validación del lote completo hace pocas consultas agrupadas (padrón, existentes y catálogos). Cada edición revalida el lote entero, lo que resuelve las filas dependientes (repetidos y titular compartido) sin lógica extra.
- **DT-03**: validación de CUIL, normalización de sexo y generación de Excel propias del vertical, porque las del kernel son privadas o están atadas a RENAPER. Del kernel se reutiliza `neutralize_csv_formula`.
- **DT-04**: el vínculo de cada fila se guarda en `BeneficiarioResponsable`. `Responsable.vinculo_parental` solo se completa al crear un titular nuevo y no se pisa al actualizarlo.
- **DT-05**: la confirmación no usa `BeneficiarioForm` ni `ResponsableForm`. Busca con `all_objects` (incluye bajas), asigna campos explícitos, reactiva con `restore(cascade=False)` y nunca cambia la identidad de un titular existente. `creado_por` se completa solo al crear.
- **DT-06**: FK opcional `Beneficiario.carga_masiva_origen`. Vacío significa que vino del formulario. En una reactivación apunta al lote que lo reactivó. Además, `Beneficiario.observaciones` es `TextField` con default vacío. La migración solo agrega columnas y tablas.
- **DT-07**: la plantilla se genera al descargarla, con las provincias y actividades vigentes, listas desplegables y columnas de CUIL y DNI en formato texto. Un archivo se acepta solo si tiene la hoja "Preinscriptos" con los 52 encabezados exactos en orden; se toleran mayúsculas y espacios.
- **DT-08**: los catálogos se comparan sin mayúsculas, tildes ni espacios repetidos. Un nombre que coincide con más de un registro se trata como no reconocido (S-02).

## Supuestos y reglas tomadas sin definición del área

- **S-03 (pendiente con el área)**: un titular dado de baja con identidad distinta en el Excel queda con error, igual que un titular activo (RN-26). Nunca se reemplaza la identidad.
- Un titular activo sin diferencias de contacto ni domicilio queda como "existente" y sin advertencia. La advertencia "se actualizarán los datos" aparece solo si algo cambia, lo que coincide con los resultados "existente" y "actualizado" del comprobante.
- Si un preinscripto existente tiene el mismo CUIL pero otro DNI (o al revés), la fila queda con error.
- Si se informan actividades extracurriculares con la columna 28 en "No", la fila tiene una advertencia y esas actividades no se guardan (mismo criterio que RN-19).
- Las filas que repiten un titular muestran en el comprobante el mismo resultado de titular que su primera aparición.
- **Cambia RN-04 a pedido del equipo**: se puede eliminar un lote **pendiente**. Se borran sus filas, el registro de ediciones y el archivo original, y en el log queda el id del lote y del usuario. Un lote confirmado no se puede eliminar, porque sus preinscriptos ya están cargados (RN-09). Hay que avisar al área, porque el issue decía que no había acción de descarte.
- **Regla nueva a pedido del equipo**: el titular no puede tener el mismo DNI o CUIL que el preinscripto de su fila; si coinciden, la fila queda con error. Rige solo en la carga masiva; el formulario de preinscripción no cambia.
- Las confirmaciones de "Quitar" y "Eliminar" usan `data-confirm-submit` (`base.js`) y no `onsubmit` en línea, porque el CSP bloquea los handlers en línea.
- Topes acordados: 10 MB y 500 filas con datos por archivo. Además, se cortan las hojas con más de 10.000 filas leídas, para no recorrer planillas con miles de filas vacías con formato.

## Seguridad y permisos

- Todas las pantallas y descargas exigen `centrodefamilia.view_centro`, igual que el alta por formulario (RN-01, RN-02).
- **Riesgo aceptado por el equipo**: ese mismo permiso habilita la descarga del archivo original, del listado de errores y del comprobante, que contienen datos personales de menores.
- El archivo original se guarda con nombre aleatorio en `centrodefamilia/cargas_masivas/` y se descarga solo por la vista con permiso. Si producción sirve `/media/` directamente, el nombre aleatorio evita que se pueda adivinar, pero no reemplaza un almacenamiento privado.
- Las descargas neutralizan textos que empiezan con `=`, `+`, `-` o `@`. Las fórmulas del archivo subido no se ejecutan: se lee el valor calculado (`data_only`). `defusedxml` ya está instalado y `openpyxl` lo usa.
- Lo que se edita en la vista previa se acepta solo para columnas de la plantilla, en lotes pendientes y con un máximo de 500 caracteres por celda.
- La confirmación bloquea el lote con `select_for_update` (RN-08), revalida contra SISOC dentro de la misma transacción (RN-07) y carga todo o nada (RN-06). Si otro usuario carga a la misma persona en ese instante, la restricción de unicidad corta la transacción y no queda nada cargado.

## Otros cambios

- Se cierra un `<div class="container">` que estaba abierto en `beneficiarios_form.html`; el navegador ya lo cerraba solo. Hacía fallar `djlint` sobre el template tocado.
- Se regeneró `src/backends/config/url_registry.json` con las rutas nuevas.

## Verificación

- `pytest src/backends/cdf/centrodefamilia/tests/test_carga_masiva_preinscriptos.py`: 43 tests que cubren CA-01 a CA-22 más reglas adicionales. CA-19 se prueba en secuencia: SQLite no permite reproducir dos transacciones simultáneas.
- `pytest src/backends/cdf`: pasa salvo 2 tests de `test_admin_operaciones_cdf.py` (N+1 en `ParticipanteActividad`) que ya fallaban sin este cambio.
- `black`, `pylint`, `djlint` y `makemigrations --check` sin hallazgos nuevos. La migración se aplicó sobre MySQL local.

## Pendientes

- Avisar al área que Observaciones pasó de la columna 52 a la 30 antes de publicar la plantilla.
- Confirmar S-03 con el área.
- Informar al área que ahora se pueden eliminar lotes pendientes (cambio sobre RN-04).
