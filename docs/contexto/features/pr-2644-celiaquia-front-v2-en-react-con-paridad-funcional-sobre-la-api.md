# Contexto de feature PR #2644 - celiaquia: front v2 en React con paridad funcional sobre la API

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2644
- Base: `development`
- Rama origen: `Celiaquia-react`
- Autor: `nehuen871`

## Contexto funcional

- Celiaquía disponible en el front v2, sobre la API REST

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- El alcance incluye automatización o tooling de CI/CD.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: feature + refactor (extracción de lógica a services).
- Área principal declarada: celiaquia / frontends.
- Impacto usuario declarado: ninguno sobre la pantalla actual, que sigue en
- Riesgos / rollback: Sin migraciones. Rollback = revertir el merge. El riesgo real está en los cuatro services extraídos: la pantalla Django ahora delega en ellos. El movimiento fue verbatim y la suite cubre esos caminos, pero es lo que conviene mirar en el review. Los nuevos guards de estado endurecen operaciones que antes no verificaban nada. Si algún flujo dependía de procesar fuera de CREADO, se va a rechazar. El servicio front_celiaquia todavía no está en el compose de deploy.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: frontends/eslint.config.js

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2644.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.github/workflows/frontend_v2.yml`
- `.gitignore`
- `backends/celiaquia/celiaquia/api_serializers.py`
- `backends/celiaquia/celiaquia/api_urls.py`
- `backends/celiaquia/celiaquia/api_views.py`
- `backends/celiaquia/celiaquia/permissions.py`
- `backends/celiaquia/celiaquia/scope.py`
- `backends/celiaquia/celiaquia/services/cruce_service/impl.py`
- `backends/celiaquia/celiaquia/services/cupo_service/impl.py`
- `backends/celiaquia/celiaquia/services/expediente_service/impl.py`
- `backends/celiaquia/celiaquia/services/registros_erroneos_service/__init__.py`
- `backends/celiaquia/celiaquia/services/registros_erroneos_service/impl.py`
- `backends/celiaquia/celiaquia/services/reporte_service/__init__.py`
- `backends/celiaquia/celiaquia/services/reporte_service/impl.py`
- `backends/celiaquia/celiaquia/services/revision_service/__init__.py`
- `backends/celiaquia/celiaquia/services/revision_service/impl.py`
- `backends/celiaquia/celiaquia/services/subsanacion_service/impl.py`
- `backends/celiaquia/celiaquia/services/validacion_renaper_service/__init__.py`
- `backends/celiaquia/celiaquia/services/validacion_renaper_service/impl.py`
- `backends/celiaquia/celiaquia/tests/conftest.py`
- ... y 110 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
