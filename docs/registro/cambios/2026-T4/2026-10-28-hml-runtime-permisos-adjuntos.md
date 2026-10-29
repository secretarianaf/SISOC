# HML: identidad no-root y permisos persistentes de adjuntos

## Alcance
Implementación preparada en la rama `fix/hml-runtime-upload-permissions-pr`, basada en la revisión HML `2478a213`. No aplicada todavía al servidor ni integrada upstream. Producción y QA no seleccionan el nuevo overlay.

## Comportamiento previsto
- Solo HML agrega `docker/compose/docker-compose.hml-runtime.yml`: 19 procesos de aplicación/worker/scheduler usan UID10001:GID1016, identidad exclusiva de aplicación y grupo de despliegue existente. Migrador, DB y frontends no cambian.
- El deploy construye primero un aprovisionador efímero, sin red, usando el stage base ya existente. Luego prepara ACL antes de arrancar aplicaciones. El único proceso root nuevo es ese aprovisionador; no sirve tráfico.
- `src/scripts/operacion/provision_hml_runtime_permissions.py` verifica por defecto, sin cambios. La aplicación explícita requiere root y backup privado nuevo.
- ACL de lectura/escritura para archivos, escritura/recorrido para directorios y herencia para futuros adjuntos en media, logs y el volumen del scheduler. Conserva propietarios, contenido y acceso efectivo anterior de otros usuarios/grupos; al ampliar la máscara ACL puede cambiar la representación de bits de grupo en stat.
- No sigue symlinks. Compara identidad de inode y ACL antes de modificar; falla ante cambios concurrentes. Los backups incluyen metadatos sensibles de rutas: quedan fuera de media en `.deploy/runtime-permissions/`, con modo0600 y sin nombres de documentos en stdout.
- El script del aprovisionador se monta solo lectura desde el checkout validado; no se monta código de aplicación en los contenedores web.

## Verificación
- ACL: RED antes del helper y GREEN después; permisos heredados en directorios futuros, datos/propietarios conservados, idempotencia y no ampliación de usuarios previamente limitados por máscara.
- Despliegue: RED de HML sin overlay; GREEN con aliases homologacion/hml/staging y orden de aprovisionamiento anterior al arranque.
- Suite aislada Linux: 30 tests pasan, sin red, DB ni datos reales. Bash syntax y Black check correctos; Pylint E/F sin errores (no equivale a lint completo de CI).
- Verificación independiente: 27 tests y probes de archivo existente, herencia, symlinks y backup correctos. Comparación diferencial QA/PRD: stdout, stderr y exit code iguales al baseline, normalizando solo rutas temporales.
- Merge real de Docker Compose con perfiles y .env sintético: 19 procesos no-root en HML, migrador sin cambios y composición sin overlay para producción.
- Revisión nativa: R1-001/R3-001 reproducidos y corregidos; validación dirigida aprobada y acknowledgement completado. Nuevas ACL default no agregan grants de grupo/otros; si el UID objetivo es dueño se ajusta su entrada owner, no solo una entrada nominada.
- Plan preventivo por deploy: `docs/plans/2026-T4/2026-10-28-prevencion-permisos-adjuntos-hml-produccion.md`. Es propuesta; los gates previos al corte y rollback automático no están implementados.
- Pendientes: integración upstream, aplicación HML y aceptación HTTP/humana.

## Reversión y límites
Antes de aplicar en HML se debe conservar configuración/identidad anterior y el backup ACL con inode, propietario, modo y atributos anteriores. La reversión restaura solo metadatos coincidentes con ese backup; no reemplaza documentos ni aplica chown recursivo. Ante fallo parcial se conserva el backup y se detiene el arranque, sin afirmar rollback automático.

No se inspeccionó producción. Las ACL de HML no se replican allí automáticamente; compartir código no demuestra igualdad de identidades ni permisos. Ejecutar como root puede ocultar la misma desalineación. La permanencia en futuros deploys requiere incorporar estos archivos al repositorio; un parche remoto no integrado no lo demuestra.

Risk: item 2 (ACL e identidad de procesos), item 5 (despliegue HML).

## Adaptación a la base de publicación
La rama nace de development59a8f797 y conserva sus cambios concurrentes. Se cubrió el nuevo health_urls_worker y se agregó un guard contra escritores omitidos. Verificador independiente y Compose efectivo confirman19procesos; la comparación QA/PRD conserva stdout, stderr y exitcode. La revisión nativa consumida corresponde al candidato anterior; la evaluación del candidato de publicación se informa por separado.

## Preflight antes del corte

El despliegue HML prepara ACL y backup privado antes de detener servicios o ejecutar migraciones, y repite el aprovisionamiento después del migrador. Un fallo temprano aborta sin ejecutar down, migrador ni arranque. El pase puede ajustar ACL mientras el servicio anterior sigue activo y conserva backup ante fallo parcial; no implementa rollback automático. QA y producción no seleccionan este comportamiento. Validación real en HML y gates adicionales del plan siguen pendientes.

El wrapper `deploy_verified.sh` usa un archivo temporal privado de fase (`SISOC_DEPLOY_PHASE_FILE`, handshake interno, no opción pública). Si refresh falla en `precut`, restaura únicamente el checkout y no recrea el stack previo; en `cut`, fase desconocida o refresh antiguo conserva el rollback existente. El archivo se elimina al finalizar. Dry-run no escribe fase.
