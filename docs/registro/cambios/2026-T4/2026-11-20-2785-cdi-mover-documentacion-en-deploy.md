# Cambio: el movimiento de documentos CDI corre solo en el deploy (#2785)

## Decisión

Del responsable, 2026-11-20: "quiero que el comando para mover la documentacion se ejecute automatico al promover este pr".

## Qué cambia

- `src/scripts/operacion/deploy_refresh.sh`: nueva función `mover_documentacion_cdi` que corre `mover_documentacion_cdi --aplicar` en el migrador, después de las migraciones y antes de reaplicar permisos (HML) y levantar servicios. Corre en cada deploy que despliega servicios, también en los selectivos con `MIGRAR=0` (el migrador se construye siempre); no corre con plan `ninguno`.
- `docker/compose/docker-compose.deploy.yml`: el migrador monta `./media` (antes no lo tenía, el comando no habría visto los archivos).
- Fallos: una excepción o exit distinto de 0 detiene el deploy. `CONFLICTO`, `PENDIENTE`, `EN USO`, `FALTANTE` y `OMITIDO` no lo fallan; se repiten con el prefijo `[REVISAR-CDI]` en el log.
- Docs: `docs/operacion/comandos_administracion.md` y `docs/operacion/deploy_automatizado.md`.

## Riesgos y límites

- Alto: mueve archivos guardados en todos los entornos. El deploy no toma backup de `media/` ni de la base; el comando copia, verifica SHA-256, actualiza la fila y borra el original solo si nadie lo usa. Confirmar el respaldo de Infra antes de promover.
- Cada deploy repite una pasada de reconciliación: una consulta y un chequeo de existencia por fila ya movida.
- Nginx no se recarga solo: el bloqueo de `/media/cdi/` sigue siendo manual por entorno, después de verificar que no quedan `MOVER`.
- Nada se ejecutó contra datos reales ni se hizo un deploy real.

## Verificación

Tests en `src/backends/kernel/tests/test_deploy_refresh_script.py` (orden después de migrar, deploy selectivo sin migraciones, HML antes de permisos, plan `ninguno`, fallo del comando, conflictos que no fallan, salida limpia).
