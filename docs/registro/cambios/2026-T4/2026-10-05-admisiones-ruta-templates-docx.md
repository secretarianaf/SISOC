# Admisiones: ruta de los templates DOCX

## Qué pasaba

`DocumentTemplateService.generar_docx` armaba la ruta del template como
`BASE_DIR/<app>/templates/<app>/docx/<template>`. Eso funcionaba cuando
`admisiones/` estaba en la raíz del repo. Desde la ola 4 de la modularización
(2026-10-01) la app vive en `backends/sisoc_core/admisiones/` (hoy
`src/backends/sisoc_core/admisiones/`), así que la ruta no existía y toda
generación de DOCX de admisiones (informes técnicos, convenios, disposiciones,
documentos de legales) fallaba con `FileNotFoundError`.

## Qué cambió

- La carpeta se resuelve con `apps.get_app_config(app_name).path`, que no
  depende de dónde esté la app en el repo.
- Test: `test_generar_docx_encuentra_el_template_en_la_carpeta_de_la_app` en
  `src/backends/kernel/tests/test_docx_service_helpers_unit.py`.

## Validación y riesgo

- Tests de docx, informes, legales y admisiones: 86 OK.
- Falta probar en QA la descarga de un informe técnico y de un documento de
  legales con datos reales. Rollback: revertir el commit.
