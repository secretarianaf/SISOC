# Contexto de feature PR #2605 - feat(vpsl): migrar modulo a Front React

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2605
- Base: `development`
- Rama origen: `task/VPSL-React`
- Autor: `Esteban-Royo`

## Contexto funcional

- Migración del módulo Ver para Ser Libre a Front v2.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- El alcance incluye automatización o tooling de CI/CD.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Funcional e infraestructura frontend/API.
- Área principal declarada: Ver para Ser Libre.
- Impacto usuario declarado: Nueva interfaz accesible por URL; las rutas Django actuales continúan disponibles.
- Riesgos / rollback: Validar integraciones y roles en homologación. Ante problemas, deshabilitar la ruta y el servicio React; el circuito Django sigue disponible.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: frontends/apps/vpsl/src/styles.css, frontends/eslint.config.js

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2605.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.env.example`
- `.github/workflows/deploy.yml`
- `.github/workflows/frontend-v2.yml`
- `.github/workflows/tests.yml`
- `.gitignore`
- `AGENT_REPO_MAP.md`
- `config/middlewares/csp.py`
- `config/settings.py`
- `config/urls.py`
- `core/tests/test_v2_frontend.py`
- `core/v2_frontend.py`
- `docker-compose.deploy.yml`
- `docker-compose.frontends.dev.yml`
- `docker-compose.yml`
- `docs/contexto/features/pr-2605-feat-vpsl-migrate-module-to-react-on-front-v2.md`
- `docs/indice.md`
- `docs/operacion/ver_para_ser_libre_react.md`
- `docs/registro/cambios/2026-09-29-vpsl-react-cierre-revision.md`
- `docs/registro/cambios/2026-09-29-vpsl-react-dependencias-seguras.md`
- `docs/registro/prs/PR-2605.md`
- ... y 51 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
