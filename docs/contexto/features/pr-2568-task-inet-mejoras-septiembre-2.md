# Contexto de feature PR #2568 - Task/inet mejoras septiembre 2

## Resumen

- PR: https://github.com/secretarianaf/SISOC/pull/2568
- Base: `development`
- Rama origen: `Task/inet-mejoras-septiembre-2`
- Autor: `juancruzventura-ai`

## Contexto funcional

- Legajo de Centro (CFP) del programa VAT/INET — identificación, plan curricular, alta de curso y sedes adicionales.

## Arquitectura tocada

- Se modifican templates, con posible impacto visual o de composición UI.
- Existen cambios de persistencia o migraciones que requieren revisión de datos.

## Decisiones y supuestos detectados

- Tipo de cambio declarado: Corrección funcional / control de acceso.
- Área principal declarada: VAT
- Impacto usuario declarado: Los perfiles CFP ya no pueden editar denominación/CUE de su centro (salvo que también tengan un rol de administración); ya no se ofrece "Usa voucher" al cargar cursos; se puede cargar una sede en cualquier departamento de la provincia.
- Riesgos / rollback: Revertir el PR restaura el comportamiento anterior. Sin riesgos abiertos adicionales a los ya documentados en los REQ de docs/registro/analisis/.

## Design system y UI

- El PR toca piezas de UI y conviene revisar consistencia visual con el patrón existente.
- Archivos visuales relevantes: VAT/templates/vat/centros/centro_detail.html, VAT/templates/vat/centros/partials/centro_cursos_panel.html, VAT/templates/vat/curso/curso_form.html, VAT/templates/vat/institucion/ubicacion_form.html

## Memoria operativa para agentes

- Empezar por `docs/registro/prs/PR-2568.md` para contexto resumido del PR.
- Revisar primero estos archivos del diff:
- `VAT/forms.py`
- `VAT/models.py`
- `VAT/templates/vat/centros/centro_detail.html`
- `VAT/templates/vat/centros/partials/centro_cursos_panel.html`
- `VAT/templates/vat/curso/curso_form.html`
- `VAT/templates/vat/institucion/ubicacion_form.html`
- `VAT/tests.py`
- `VAT/urls.py`
- `VAT/views/centro.py`
- `VAT/views/institucion.py`
- `docs/contexto/features/pr-2568-task-inet-mejoras-septiembre-2.md`
- `docs/registro/analisis/2026-09-23-inet-bloquear-cue-y-denominacion.md`
- `docs/registro/analisis/2026-09-23-inet-modalidad-sector-en-selector-de-plan.md`
- `docs/registro/analisis/2026-09-23-inet-quitar-usa-voucher-alta-curso.md`
- `docs/registro/analisis/2026-09-23-inet-sedes-fuera-del-departamento.md`
- `docs/registro/prs/PR-2568.md`
- Documentación sugerida para ampliar contexto:
- `docs/indice.md`
- `docs/ia/CONTEXT_HYGIENE.md`
- `docs/ia/ARCHITECTURE.md`
- `docs/ia/TESTING.md`

## Trazabilidad

- Documento generado automáticamente desde el evento de `pull_request`.
- Si este PR cambia de título, el archivo se renombrará para mantener el slug alineado.
