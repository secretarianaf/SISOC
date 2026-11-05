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

El primer CI del PR de sincronización detectó que `celery_comedores_worker`,
incorporado desde main, no figuraba en el overlay de identidad HML. Se reprodujo
el fallo con el test existente de escritores persistentes. Se agregó ese servicio
al mismo anchor `hml-runtime` usado por los demás workers: usuario `10001:1016`,
`HOME=/tmp` y `USER=sisoc-app`. El test comprueba también esas variables. No cambia
la identidad de producción ni los permisos del filesystem; no ejecuta el
aprovisionador ni modifica datos. RED confirmado con la misma prueba de política.
Validación local: 10 tests Linux de permisos/ACL y 76 de deploy pasan; el
verificador independiente confirmó RED en la base y 10 tests verdes en el
candidato. CI del nuevo commit y aceptación operativa siguen pendientes.

La unión vacía no elimina los riesgos de las migraciones funcionales ya presentes
en el release. Antes de PRD se requiere backup verificado y estimación de duración,
especialmente por el ALTER de ciudadanos. No se verificó backup ni se accedió a
servidores, datos, variables reales o credenciales.

Espacios Comunitarios, DataCalle, Gestionar e Inspecciones figuran habilitados en el
inventario. Inicialmente faltaba autorización para otros repositorios; el usuario
la otorgó luego para la sesión actual de GitHub y sus flujos QA/HML/PRD, siempre
con CI y compatibilidad comprobados. DataCalle no requiere cambios; Inspecciones
no tiene diferencias de contenido, pero QA tiene un bloqueo de checkout.
Gestionar y Espacios no se promueven a PRD: requieren backends todavía no
desplegados. No se infiere un deploy posterior automático ni se declara listo el
conjunto por tener CI verde.

## Sincronización posterior hacia development

La preparación continúa desde development hacia la revisión HML saneada del PR
#2874. El único conflicto es documental: se conserva el registro completo de
development, incluida su sección de integración previa del hotfix de papelera.
No se resolvieron conflictos de código ni se agregaron nuevas migraciones en este
paso. El grafo conserva la unión vacía 0029.

El registro URL regenerado en una copia aislada contiene las mismas 2796
entradas que el merge. La diferencia inicial de bytes era solo CRLF/LF; no se
reescribe masivamente el archivo generado. `makemigrations --check --dry-run`
con settings completo, 10 tests Linux de permisos/ACL y 143 tests de integración
afectada pasan localmente y en la verificación independiente. Esta última confirmó
también los blobs publicados de ambas ramas y el estado completo de 360 modelos.
El CI remoto de este paso sigue pendiente; salud, deploy y aceptación humana son
estados separados.

El deploy HML del saneamiento #2874 terminó correctamente en la revisión
`7ee9065e93d994d098bec6ee8f9047c150a9581f`; falló después su promoción automática
a development por el conflicto documental. El run dejó advertencias de TLS,
restricción condicional MySQL no soportada y contenedores huérfanos; no se
ejecutaron reparaciones ni limpieza. La salud funcional informada por el workflow
no certifica por sí sola el estado final de cada worker ni aceptación humana.

Risk: items 1, 2, 3, 5 (grafo de migraciones, identidad HML, integración compartida y preparación de deploy).
