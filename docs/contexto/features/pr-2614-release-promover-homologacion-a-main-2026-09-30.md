# Contexto de feature PR #2614 - release: promover homologacion a main (2026-09-30)

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2614
- Base: `main`
- Rama origen: `homologacion`
- Autor: `juanikitro`

## Contexto funcional

- Preparación de la promoción de homologacion a main.

## Arquitectura tocada

- El PR toca lógica en `services/`, por lo que impacta reglas de negocio u orquestación.
- Hay cambios en capa API/DRF y conviene revisar contratos de request/response.
- Hay cambios en vistas web y puede existir impacto en permisos o renderizado.
- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.
- El alcance incluye automatización o tooling de CI/CD.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Corrección de CI/CD y saneamiento de promoción.
- Área principal declarada: CI/CD, migraciones de usuarios y despliegue HML.
- Impacto usuario declarado: Sin cambios funcionales nuevos; permite validar y desplegar la rama de homologación de forma consistente.
- Riesgos / rollback: Las migraciones de datos aplicadas no se revierten al restaurar el código. El rollback operativo vuelve al SHA previo y debe verificarse.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: VAT/templates/vat/beneficiarios/beneficiarios_detail.html, VAT/templates/vat/beneficiarios/responsable_detail.html, VAT/templates/vat/catalogo/modalidadcursada_detail.html, VAT/templates/vat/catalogo/modalidadcursada_list.html, VAT/templates/vat/catalogo/planversioncurricular_detail.html, VAT/templates/vat/catalogo/planversioncurricular_list.html, VAT/templates/vat/catalogo/sector_detail.html, VAT/templates/vat/catalogo/subsector_detail.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2614.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `.env.example`
- `.github/workflows/deploy.yml`
- `.github/workflows/frontend-v2.yml`
- `.github/workflows/tests.yml`
- `.gitignore`
- `AGENT_REPO_MAP.md`
- `VAT/api_urls.py`
- `VAT/api_web_views.py`
- `VAT/catalogo_filter_config.py`
- `VAT/forms.py`
- `VAT/models.py`
- `VAT/services/nomina_export.py`
- `VAT/services/pav_service.py`
- `VAT/services/reportes_inscripciones_asistencia.py`
- `VAT/templates/vat/beneficiarios/beneficiarios_detail.html`
- `VAT/templates/vat/beneficiarios/responsable_detail.html`
- `VAT/templates/vat/catalogo/modalidadcursada_detail.html`
- `VAT/templates/vat/catalogo/modalidadcursada_list.html`
- `VAT/templates/vat/catalogo/planversioncurricular_detail.html`
- `VAT/templates/vat/catalogo/planversioncurricular_list.html`
- ... y 620 archivo(s) adicional(es) relacionados.
- Documentación sugerida para ampliar contexto:
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
