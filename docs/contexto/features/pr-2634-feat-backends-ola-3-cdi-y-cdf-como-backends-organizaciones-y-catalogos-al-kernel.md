# Contexto de feature PR #2634 - feat(backends): ola 3, CDI y CDF como backends; organizaciones y catálogos al kernel

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2634
- Base: `development`
- Rama origen: `feat/2309-backends-ola3`
- Autor: `juanikitro`

## Contexto funcional

- No informado explícitamente; inferir desde el título del PR y el diff.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: No informado
- Área principal declarada: No informada
- Impacto usuario declarado: No informado
- Riesgos / rollback: No informado

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: backends/cdf/centrodefamilia/templates/beneficiarios/beneficiarios_detail.html, backends/cdf/centrodefamilia/templates/beneficiarios/beneficiarios_form.html, backends/cdf/centrodefamilia/templates/beneficiarios/beneficiarios_list.html, backends/cdf/centrodefamilia/templates/beneficiarios/responsable_detail.html, backends/cdf/centrodefamilia/templates/beneficiarios/responsable_list.html, backends/cdf/centrodefamilia/templates/centrodefamilia/ciudadano_detalle_monto.html, backends/cdf/centrodefamilia/templates/centrodefamilia/ciudadano_detalle_seccion.html, backends/cdf/centrodefamilia/templates/centros/actividad_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2634.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.importlinter`
- `AGENT_REPO_MAP.md`
- `acompanamientos/acompanamiento_service.py`
- `backends/cdf/cdf_runtime/__init__.py`
- `backends/cdf/cdf_runtime/settings.py`
- `backends/cdf/cdf_runtime/urls.py`
- `backends/cdf/centrodefamilia/__init__.py`
- `backends/cdf/centrodefamilia/access.py`
- `backends/cdf/centrodefamilia/admin.py`
- `backends/cdf/centrodefamilia/api.py`
- `backends/cdf/centrodefamilia/api_urls.py`
- `backends/cdf/centrodefamilia/api_views.py`
- `backends/cdf/centrodefamilia/apps.py`
- `backends/cdf/centrodefamilia/ciudadano_detail.py`
- `backends/cdf/centrodefamilia/favorite_filters.py`
- `backends/cdf/centrodefamilia/fixtures/actividad_categoria.json`
- `backends/cdf/centrodefamilia/forms.py`
- `backends/cdf/centrodefamilia/forms_generar_usuario.py`
- `backends/cdf/centrodefamilia/management/commands/__init__.py`
- `backends/cdf/centrodefamilia/management/commands/cargar_legajos.py`
- ... y 332 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
