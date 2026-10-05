# Deploy HML: reutilizar el fetch verificado

El deploy de homologación valida en el workflow que `origin/homologacion` coincide con el SHA del evento y que el checkout está limpio. `deploy_refresh.sh` vuelve a hacer `fetch` para confirmar que la rama no avanzó antes de desplegar; un corte transitorio de SSH a GitHub hizo fallar ese paso y activó un rollback innecesario.

Ahora se reintenta ese `fetch` hasta tres veces, con cinco segundos entre intentos. Se conserva la validación del SHA remoto más reciente antes de actualizar Docker; si los tres intentos fallan, el deploy se detiene con error. El deploy mantiene las verificaciones de migraciones, healthcheck y rollback para fallos posteriores al inicio de la actualización.
