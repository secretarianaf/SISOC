# Cambio: PDF consolidado de rendición generado con Celery (#2845)

## Causa

En PRD, "Generar descarga" de la rendición 1724 devolvía "El servicio no
respondió a tiempo". Ese texto es el 504 propio del proxy del core
(`src/backends/kernel/core/backend_proxy.py`, `READ_TIMEOUT_SECONDS = 25`).
El backend de comedores armaba el PDF dentro del request. Con los 15 documentos
de esa rendición (13 imágenes y 2 PDF, unos 25 MB) tardaba 29,7 s y producía un
PDF de 96 MB. El error log de PRD registró más de 13 `Gateway Timeout` de esa
URL el 2026-11-02. No es un caso aislado: cualquier rendición con suficiente
documentación supera el corte.

## Qué cambia

- El botón "Generar descarga" ahora hace un POST a
  `.../detalle/<pk>/descargar-pdf/solicitar/`. Si ya existe un PDF vigente lo
  reutiliza. Si no, crea o reinicia la solicitud y encola
  `rendicioncuentasmensual.tasks.generar_pdf_descarga` en la cola `comedores`.
- El detalle muestra "Generando el PDF…" y consulta
  `.../descargar-pdf/estado/` cada 3 s. Cuando la generación termina, navega a
  `.../descargar-pdf/`, que solo entrega el archivo guardado y nunca lo genera.
- El modelo nuevo `RendicionPdfDescarga` (migración `0029`) guarda una solicitud
  por rendición, con su estado, el archivo y una huella de los documentos
  validados (id, archivo y `ultima_modificacion`). Si la huella cambia, el PDF
  se regenera y el anterior se borra.
- Un `token` por solicitud impide que una tarea reemplazada pise el resultado
  de una solicitud más nueva. Una solicitud que lleva más de 15 minutos en curso
  se informa como error y puede reintentarse.
- Si Redis no responde al encolar, la solicitud queda en error en lugar de
  pendiente.
- Una purga diaria (beat, 03:30, cola `comedores`) borra los PDFs y las
  solicitudes terminadas hace más de 7 días.
- El PDF se guarda en `media/rendicioncuentasmensual_pdf_consolidado/` con un
  nombre que incluye el token. Se descarga solo por la vista con permisos
  (`_RENDICION_ACCESS_PERMS`), porque nginx sirve `/media/` sin autenticación.

## Infraestructura

- `config/celery.py` descubre las tareas de las apps instaladas (`pas`,
  `rendicioncuentasmensual`) según el settings del proceso. Así cada imagen solo
  importa su propio backend.
- `docker-compose.celery.yml` suma `celery_comedores_worker`: imagen
  `sisoc/backend-comedores`, `comedores_runtime.settings`, `-Q comedores` y
  `--concurrency=2`. Ese archivo forma parte del deploy de todos los entornos,
  y `deploy_targets` lo trata como servicio obligatorio, igual que Celery de PAS.
- El worker se agrega a `extra_services` de comedores, al override no-root de
  HML y a `healthcheck_prod.sh`.
- Beat sigue corriendo con la imagen de PAS y envía la purga por nombre, sin
  importar el código de comedores.

## Verificación

- Tests nuevos en `src/backends/comedores/tests/test_rendicion_pdf_descarga_issue_2845.py`
  y los tests de la vista de descarga adaptados. Pasaron 399 tests de
  rendiciones y deploy targets, con SQLite y la imagen local
  `sisoc-2789-django:latest`.
- `makemigrations --check` no detectó cambios. Black y djlint quedaron limpios y
  pylint dio 10/10 en los módulos tocados.
- Prueba real con Redis y un worker en `comedores_runtime.settings`: el worker
  registra las dos tareas, recibe una tarea enviada desde el web y la ejecuta.
  En el entorno de PAS solo se descubren las tareas de PAS, sin errores de
  import.
- No se verificó en navegador: el worktree no tiene un stack completo con datos.

## Límites y pendientes

- El deploy necesita levantar `celery_comedores_worker` en cada entorno. Sin
  ese worker, las solicitudes vencen a los 15 minutos y se informan como error.
- El PDF consolidado sigue inflando las imágenes (25 MB de entrada dan 96 MB de
  salida). Recomprimir las imágenes reduciría tiempo y disco, pero queda fuera
  de este cambio.
