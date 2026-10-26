# Contexto de feature PR #2647 - Vpsl(ux): cambios visuales/ux VPSL React

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2647
- Base: `development`
- Rama origen: `task/VPSL-V2-CambiosUX`
- Autor: `Esteban-Royo`

## Contexto funcional

- gestión territorial de VPSL.

## Arquitectura tocada

- No se detectó un patrón arquitectónico dominante más allá del diff observado.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: mejora visual y corrección funcional.
- Área principal declarada: frontend VPSL React y UI compartida.
- Impacto usuario declarado: interfaz más consistente y formularios mejor alineados.
- Riesgos / rollback: theme compartido; revertir cambios y reconstruir frontend.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: src/frontends/apps/vpsl/src/styles.css, src/backends/kernel/static/custom/img/sisoc_header_texture.png, src/backends/kernel/static/custom/img/sisoc_logo_header.png

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2647.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `docs/registro/cambios/2026-10-01-vpsl-react-cambios-visuales-v2.md`
- `src/frontends/apps/vpsl/src/App.test.tsx`
- `src/frontends/apps/vpsl/src/App.tsx`
- `src/frontends/apps/vpsl/src/StateChip.tsx`
- `src/frontends/apps/vpsl/src/Workflow.test.tsx`
- `src/frontends/apps/vpsl/src/Workflow.tsx`
- `src/frontends/apps/vpsl/src/styles.css`
- `src/frontends/packages/api/src/index.ts`
- `src/frontends/packages/ui/src/layout.tsx`
- `src/frontends/packages/ui/src/theme.ts`
- `src/backends/kernel/static/custom/img/sisoc_header_texture.png`
- `src/backends/kernel/static/custom/img/sisoc_logo_header.png`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
