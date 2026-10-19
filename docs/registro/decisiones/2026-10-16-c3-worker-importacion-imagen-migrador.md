# C3: importador de Usuarios con la imagen completa del migrador

Estado: aprobado por el responsable el 2026-10-16 para #2641. Eligió «2» entre
imagen compuesta acotada y reutilización de la imagen del migrador completo.
No autoriza commit, push, merge, cierre de issues, deploy ni entornos existentes.

## Contexto y decisión

C2 conserva usuario, accesos PWA y checkpoint del lote en una única transacción.
El adaptador local requiere Usuarios y Comedores juntos. Las imágenes web C3
son separadas: portal con sus cinco apps y Comedores con su cluster de catorce.
No volver a instalar el dominio en el portal para ejecutar el importador.

Se reutiliza `sisoc/migrator` con target `migrator` y `config.settings_all` en el
servicio existente `user_import_worker`. El rol explícito `user_import_worker`
reemplaza el rol heredado de la imagen; entrypoint ejecuta el comando existente
`process_user_import_jobs`, sin migrar, collectstatic ni servidor HTTP.
`SISOC_PREPARAR_DB=false` deja explícito el propósito. El servicio `migrator`
con su perfil/rol de migración conserva su responsabilidad y número de instancias.
DB, media/static/logs siguen compartidos. #2725 continúa postergado.

La alternativa recomendada por el agente era un target y settings propios con
kernel + portal + Comedores: carga más acotada, a cambio de más configuración.
El responsable eligió la reutilización sin aportar motivos adicionales. El
análisis técnico siguiente es del agente; no una justificación humana retrospectiva.

## Consecuencias y mitigaciones

No se agrega target ni settings, pero el worker instala todas las verticales y
sus señales. El aislamiento de código de los runtimes web se conserva. Un cambio
local de cualquier backend requiere actualizar también ese worker en entornos
donde exista; no basta actualizarlo sólo por cambios de Usuarios o Comedores.

Cada backend declara `user_import_worker` en `extra_services`. `@core` lo incluye
por su rol existente. El selector resuelve el conjunto contra los servicios del
Compose del entorno, deduplica y omite sólo mailing/importación ausentes (viven en el
override de producción para HML/PRD). Si falta otro servicio, incluido Celery, o falla la resolución,
usa el fallback completo; no omite silenciosamente un servicio principal.
La lectura de Compose no registra sus variables de entorno.

El primer corte C0–C3 requiere deploy completo. No hay deploy autorizado ni
prueba sobre servicios existentes. La validación local debe cubrir el rol,
comando/adaptador en la imagen, importación y rollback del checkpoint sobre
MySQL sintético, y selección del worker por cada backend.

Revisar esta elección si las señales de otros programas interfieren, el costo de
cargar todo el grafo deja de ser aceptable, se requiere independizar actualizaciones
del worker, o se aprueba #2725. El rollback coordina imágenes/Compose/registro,
sin revertir automáticamente esquema ni metadata C1.

Evidencia y límites:
`docs/registro/cambios/2026-T4/2026-10-16-issue-2641-c3-runtime-comedores.md`.
La elección no demuestra comprensión humana ni aceptación funcional manual.
