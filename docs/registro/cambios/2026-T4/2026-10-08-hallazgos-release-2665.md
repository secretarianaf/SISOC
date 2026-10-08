# Hallazgos de la revisión del release #2665

Correcciones de la revisión del PR de despliegue `homologacion` → `main`
(#2665), antes de su paso a PRD.

## Cambios

- **Rollback automático hacia `main` (`deploy_verified.sh`).** Si el primer
  deploy del layout nuevo fallaba, el rollback llamaba al `deploy_refresh.sh`
  de `main` con `--diff-base`, opción que ese script no conoce, y verificaba
  con el migrador y los compose de `docker/compose/`, que en `main` no
  existen. Ahora pasa `--diff-base` solo si el script restaurado la admite,
  usa los compose de la raíz cuando no está `docker/compose/` y, sin
  `src/backends/config/backends.json`, verifica como el `deploy_verified.sh`
  anterior (`migrate --check` en `django` y healthcheck).
- **Rollback de migraciones.** Nuevo runbook
  `docs/operacion/rollback_release_modularizacion.md`: el código de `main` no
  corre sobre la base migrada (columnas NOT NULL nuevas y content types
  movidos), así que hay que revertir migraciones con la imagen nueva antes de
  volver el código.
- **Alta de usuarios de app (`UserCreationForm`).** Un representante o
  coordinador PWA o un relevador DataCalle se crea con `acceso_web=False`
  aunque la casilla quede tildada (arranca marcada). Antes de `acceso_web`
  estos usuarios no entraban a la web. La edición no cambia: habilitar la web
  después sigue siendo posible, como define #2659.
- **RENAPER en CDI (`centrodeinfancia/ajax/renaper/<bloque>/`).** Límite de
  30 consultas cada 10 minutos por usuario (429) y log de cada consulta con
  usuario, bloque y DNI enmascarado. Quién puede consultar no cambia.
- **Proxy core → backends (`core/backend_proxy.py`).** El path decodificado
  se vuelve a codificar antes de reenviarlo (`%3F`, `%23`, `%25` llegan tal
  cual) y los segmentos `.`/`..` dan 404: un `%2e%2e` no sale del prefijo del
  backend. El docstring describe `X-Forwarded-For` como lo hace el código:
  agrega `REMOTE_ADDR` a la cadena recibida.

## Fuera de este cambio

- Los `.env.qa`, `.env.homologacion` y `.env.prod` borrados de la raíz no los
  usa ningún deploy. Si tenían credenciales reales, siguen en el historial de
  Git: la mitigación es rotarlas, fuera del repo.
- Disco y capacidad de workers de PRD: chequeos operativos previos al deploy.
