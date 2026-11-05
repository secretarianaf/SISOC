# Sincronización de producción hacia homologación para el release del 5 de noviembre

## Alcance

Preparación solicitada con `preparar-deploy` para el 2026-11-05 a las 17:00 de
Argentina. El usuario autorizó incluir el contenido actual de homologación aunque
no haya cumplido siete días de prueba, y la excepción de tamaño de los PRs de
sincronización y promoción. Los dos PRs finales de SISOC deben quedar sin mergear
ni armar; la fecha del marker no programa una ejecución automática.

El workflow de producción del hotfix #2865 desplegó correctamente. Falló su
promoción posterior a homologación con un conflicto de merge; no se interpreta
ese resultado agregado como un fallo del despliegue productivo.

## Integración

- Se conservan la descarga asíncrona de PDF de #2856 y el arreglo de papelera de
  #2865, junto con el contenido existente de homologación.
- La revisión de documentos conserva la recarga del borrador y su edición hasta
  finalizar. La recarga también obtiene del servidor la acción de PDF asíncrono;
  no se restablece el antiguo bloqueo inmediato del selector.
- La eliminación de dispositivos conserva la respuesta existente de homologación
  para cualquier modelo protegido, sin volver a un mensaje exclusivo de Datacalle.
- `src/backends/comedores/rendicioncuentasmensual/migrations/0029_merge_pdf_descarga_upload_to.py`
  une las ramas publicadas de PDF y adjuntos. Es una migración vacía: no modifica
  datos ni reescribe, borra o renombra migraciones publicadas.

## Verificación

- RED observado: el test del grafo detectó las dos hojas de rendiciones antes de
  agregar la unión. La ejecución fue local, sin red y sin base de datos real.
- Las pruebas JavaScript existentes y la regresión de guardado de borrador pasan.
- Validación Python focalizada: 110 tests pasaron; suite afectada independiente:
  437 tests pasaron. El estado histórico del grafo conserva los tres campos de
  borrador y el modelo de descarga de PDF. Todas las migraciones publicadas de
  ambas ramas conservan sus bytes.
- `makemigrations --check --dry-run --settings=config.settings_all` falló con
  `NodeNotFoundError` tanto en el candidato como en la base de homologación.
  Se identificó la causa de la invocación: `manage.py` consulta `settings.DEBUG`
  antes de procesar `--settings`. Al indicar desde el inicio
  `DJANGO_SETTINGS_MODULE=config.settings_all`, el mismo comando devuelve
  `No changes detected`; el recheck independiente confirma salida 0. No se
  modificó código de runtime para resolverlo.
- Black no requiere cambios y Pylint con `.pylintrc` pasa para el test nuevo.
  El aviso inicial por nombre numérico de la migración provino de un probe extra;
  el glob real de CI no incluye esos archivos. No equivale a un fallo de CI.
- La revisión independiente no encontró bloqueantes causados por el cambio.
  Se desacopló el test de la hoja futura: solo la migración de unión debe ser vacía.
- CI remoto, despliegue HML y aceptación humana: todavía no realizados aquí.
- No se abrió un entorno de demostración: esta integración preserva el
  comportamiento de HML; las pruebas de JavaScript no equivalen a un recorrido
  real de navegador ni a aceptación humana.

## Consideraciones operativas

La unión vacía no elimina los riesgos de las migraciones funcionales ya presentes
en el release. Antes de PRD se requiere backup verificado y estimación de duración,
especialmente por el ALTER de ciudadanos. No se verificó backup ni se accedió a
servidores, datos, variables reales o credenciales.

Espacios Comunitarios, DataCalle, Gestionar e Inspecciones figuran habilitados en el
inventario. Su lectura y ejecución quedan bloqueadas hasta resolver el alcance de
autorización de los otros repositorios y comprobar compatibilidad con el backend
efectivamente desplegado. No se declara listo el conjunto por tener CI verde.

Risk: items 1, 3, 5 (grafo de migraciones, integración compartida y preparación de deploy).
