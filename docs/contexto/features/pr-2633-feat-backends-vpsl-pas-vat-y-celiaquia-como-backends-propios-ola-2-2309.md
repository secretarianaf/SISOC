# Contexto de feature PR #2633 - feat(backends): VPSL, PAS, VAT y Celiaquía como backends propios (Ola 2 #2309)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2633
- Base: `development`
- Rama origen: `feat/2309-backends-ola2`
- Autor: `juanikitro`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.
- El alcance incluye automatización o tooling de CI/CD.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: backends/celiaquia/celiaquia/templates/celiaquia/carga_masiva_personas.html, backends/celiaquia/celiaquia/templates/celiaquia/ciudadano_detalle_seccion.html, backends/celiaquia/celiaquia/templates/celiaquia/cruce_upload.html, backends/celiaquia/celiaquia/templates/celiaquia/cruce_validar.html, backends/celiaquia/celiaquia/templates/celiaquia/cupo_dashboard.html, backends/celiaquia/celiaquia/templates/celiaquia/cupo_provincia.html, backends/celiaquia/celiaquia/templates/celiaquia/detalle_pago.html, backends/celiaquia/celiaquia/templates/celiaquia/expediente_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2633.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.github/workflows/deploy.yml`
- `AGENT_REPO_MAP.md`
- `VAT/sidebar_access.py`
- `backends/celiaquia/celiaquia/__init__.py`
- `backends/celiaquia/celiaquia/admin.py`
- `backends/celiaquia/celiaquia/api.py`
- `backends/celiaquia/celiaquia/apps.py`
- `backends/celiaquia/celiaquia/ciudadano_detail.py`
- `backends/celiaquia/celiaquia/comentarios_tecnicos.py`
- `backends/celiaquia/celiaquia/fixtures/pais_a_nacionalidad.json`
- `backends/celiaquia/celiaquia/fixtures/parametria.json`
- `backends/celiaquia/celiaquia/forms.py`
- `backends/celiaquia/celiaquia/global_urls.py`
- `backends/celiaquia/celiaquia/management/commands/migrar_comentarios.py`
- `backends/celiaquia/celiaquia/management/commands/sanear_celiaquia.py`
- `backends/celiaquia/celiaquia/management/commands/test_celiacos.py`
- `backends/celiaquia/celiaquia/management/commands/test_celiacos_import.py`
- `backends/celiaquia/celiaquia/management/commands/test_celiacos_real.py`
- `backends/celiaquia/celiaquia/migrations/0001_squashed_0012.py`
- `backends/celiaquia/celiaquia/migrations/0002_subsanacion_models.py`
- ... y 492 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
