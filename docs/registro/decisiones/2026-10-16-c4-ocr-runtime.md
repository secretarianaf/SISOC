# C4: OCR y su worker con runtime propio

Estado: alcance aprobado por el responsable el 2026-10-16: «si, apruebo el plan
y avanza con el desarrollo». Implementado y validado localmente; sin incorporación
ni deploy. Aceptación funcional humana no demostrada.

## Contexto y decisión

C0–C3 separaron Comedores del portal. El siguiente corte propuesto era OCR,
que todavía instalaba su negocio en core y usaba `usuarios.views` para acceder
a un mixin de autorización ya perteneciente al kernel. Insumos y Encuestas no
forman parte de esta extracción. #2725 sigue postergado.

OCR pasa a `src/backends/ocr/ocr/`, con tests en `src/backends/ocr/tests/` y
`ocr_runtime` usando los helpers de settings/URLs existentes. Se registra el
backend y los prefijos históricos `ocr/` y `admin/ocr/` en el proxy actual.
El portal conserva Usuarios, Dashboard, Encuestas e Insumos.

`backend_ocr` y el servicio existente `ocr_worker` usan `sisoc/backend-ocr`,
target genérico backend y `ocr_runtime.settings`. El worker conserva su rol y
`process_ocr_jobs`; command explícito llama al entrypoint Python para evitar
heredar Gunicorn. No cambia su número de instancias ni la semántica de la cola.

Se conserva `ocr.use_ocr`, labels, tablas, IDs, migraciones, paths de archivos,
sesión, CSRF y restricciones por solicitante. Las vistas importan exactamente
el mismo `users.view_mixins.AdminRequiredMixin` que Usuarios reexportaba.
Los modelos remotos tienen admin real en el dueño y enlaces autorizados desde
el índice del portal. El dueño vuelve a comprobar sus permisos.

## Alternativa y consecuencias

La alternativa era mantener OCR y su worker en core; evitaba otro runtime pero
conservaba su acoplamiento de código y actualización. Se aprobó desarrollar la
extracción propuesta. La evaluación técnica siguiente proviene del agente;
no demuestra comprensión humana ni atribuye al responsable motivos adicionales.

El runtime propio añade otro servicio web y una imagen a construir/operar. La
DB, storage, sesión, entrada y migrador siguen compartidos. La imagen base
continúa incluyendo las bibliotecas OCR existentes; no se adelanta una poda de
dependencias ni separación de datos o credenciales. No se agrega dependencia.

OCR declara como extras `ocr_worker` y `user_import_worker`: este último carga
el grafo completo por la decisión C3 anterior y necesita recibir también cambios
de OCR. OCR worker es obligatorio en QA/HML/PRD, a diferencia de los dos workers
opcionales ya definidos. Un selectivo del portal no debe reiniciar OCR.

El primer corte requiere coordinación completa por cambios en config/Compose;
no se ejecuta deploy. Reversa coordinada de rutas/registro/Compose e imágenes,
sin borrar tablas, archivos ni ContentTypes. Revisar si cambian las necesidades
de datos/almacenamiento, recursos OCR o la disponibilidad de la entrada común.

Evidencia, límites y validación pendiente:
`docs/registro/cambios/2026-T4/2026-10-16-issue-2641-c4-ocr.md`.
