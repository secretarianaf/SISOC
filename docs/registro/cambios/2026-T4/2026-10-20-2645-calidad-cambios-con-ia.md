# Cambio: calidad y armonía de cambios hechos con IA (#2645)

## Alcance

Personas sin formación en sistemas van a empezar a desarrollar en SISOC con IA
(Claude Code, Codex y Copilot en el editor). El merge y el deploy siguen pasando
por el responsable del repo; el objetivo es que el código que llegue a su
revisión no sea de mala calidad ni rompa la armonía del sistema. Sigue a la
revisión de archivos para agentes (`2026-10-20-2645-archivos-agentes.md`).

Decisiones del responsable: ante zonas delicadas el agente **implementa
avisando** (no se bloquea); CI gana dos controles **bloqueantes** (código sin
tests y cobertura de las líneas cambiadas, mínimo 80%), con excepción por un
label que pone el revisor.

## Qué cambió

- **Agente.** `AGENTS.md` suma "Responsabilidades del agente": el agente es
  responsable de la calidad aunque quien pide no sepa programar; entiende el
  problema antes de codificar, sigue un patrón existente y lo nombra, no agrega
  dependencias/modelos/settings/permisos sin explicarlo, escribe tests que
  afirman el comportamiento, marca zonas delicadas como "Requiere revisión
  técnica", no mergea ni usa el label de excepción.
- **Skill `cambio-guiado`.** Flujo completo con autorrevisión de armonía, con un
  ejemplo sobre el patrón real de filtros avanzados de Comedores.
- **Copilot.** `.github/copilot-instructions.md` resume esas reglas, porque
  Copilot no carga skills.
- **Plantilla de PR.** Secciones "En lenguaje simple" (qué cambia, cómo probarlo,
  qué podría romperse) y "Calidad y armonía" (patrón seguido, zonas sensibles,
  checklist). No usan claves `clave: valor`, así que no cambian la metadata que
  lee `src/scripts/ci/pr_doc_automation.py`.
- **CI bloqueante, job `quality_gate`** (`.github/workflows/tests.yml`, exigido
  por `deploy_guard`). `pytest` publica `coverage.xml`; `src/scripts/ci/quality_gate.py`
  compara el merge del PR con su primer padre y falla si se modifica Python de
  una app sin tocar tests, o si las líneas cambiadas medibles quedan bajo 80%.
  El label `excepcion-calidad` lo destraba (hay que volver a correr el job: los
  labels se leen por API al correr).
- **CI no bloqueante, job `zonas_sensibles`** (`.github/workflows/lint.yml`).
  Pone el label `requiere-revision-tecnica` y un comentario con las rutas
  delicadas; lo quita si dejan de estar. No corre en forks.

## Límites

- La cobertura mide líneas ejecutadas, no si el test verifica algo: un test sin
  aserciones útiles pasa el control. Lo cubren la regla del agente y la revisión.
- Cualquier usuario con escritura puede poner labels; el control de la
  excepción es que queda visible en la revisión.
- Un archivo de app sin datos de cobertura cuenta todas sus líneas cambiadas
  como no cubiertas.
- Afecta también al equipo técnico: refactors sin tests o cambios de settings
  necesitan el label.

## Verificación

- `src/backends/kernel/tests/test_quality_gate.py`: parseo del diff, cobertura,
  umbral, código sin tests, zonas sensibles y label de excepción. Corridos
  localmente sin Django.
- `coverage.xml` real generado con `pytest --cov=.`: los nombres de archivo
  coinciden con las rutas de git.
- Script de `github-script` de `zonas_sensibles` simulado con un mock (agrega,
  actualiza y quita label/comentario); YAML de ambos workflows validado.
- La plantilla de PR sigue produciendo la misma metadata en `parse_pr_body_metadata`.
- No corrido: los jobs en Actions (los valida el PR) ni la suite en Docker.
