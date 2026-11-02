# Preparación coordinada de SISOC y satélites

## Cambio y motivo

La skill `preparar-deploy` incorpora todos los componentes del inventario
`src/scripts/operacion/pwas.json` al expediente de release, aunque el diff del
backend no mencione contratos compartidos. Evita considerar completa una
promoción de SISOC cuando falta su frontend, como en el par #2730 / DataCalle #19.

## Funcionamiento y límites

La fuente permanece en `.agents/skills/preparar-deploy/`; `.claude/skills/` se
genera con `src/scripts/ai/sync_skills.py`. El expediente reúne SHA, promociones,
CI, despliegues, compatibilidad, orden, autorizaciones y recuperación por entorno.
Distingue sin cambios verificado, desconocido/bloqueado y deshabilitado.

La primera versión solo preparaba PRs y no ejecutaba satélites. El usuario corrigió
el alcance: "quiero que en los satelites si mergee y despliegue automaticamente"
y eligió "durante" el pre-deploy.

La skill ahora promueve, mergea y sigue el deploy satélite durante su ejecución,
si el alcance está autorizado y el backend efectivamente desplegado es compatible.
SISOC conserva sus PRs finales sin mergear/armar y su ciclo semanal HML. No cambia
workflows, gates humanos ni credenciales; no hay atomicidad ni rollback de datos.
Reutiliza autorización válida, evita dispatch duplicado y bloquea dependientes
ante fallos, revisiones distintas o falta de evidencia. Actualizar estos archivos
no ejecuta sus instrucciones ni constituye un deploy real.

## Verificación

- `python src/scripts/ai/sync_skills.py`: actualizó solo los tres espejos previstos;
  `python src/scripts/ai/sync_skills.py --check`: correcto.
- Tests existentes de `src/backends/kernel/tests/test_sync_skills.py`: tres
  correctos con pytest local, configuración mínima y scratch fuera del repo.
  Se aislaron plugins y conftest Django porque estos tests solo usan la biblioteca
  estándar y los fixtures propios de pytest; no se ejercitó la aplicación Django.
- Para el alcance corregido se repitieron sincronización y tests aislados y se
  revisaron las instrucciones: merge/despliegue satélite durante el pre-deploy,
  backend actualmente desplegado compatible, head fijado/base revalidada, dispatch
  único, gate humano, resultado terminal/SHA, fallo parcial, no-op, desconocido y
  deshabilitado. Los escenarios comprueban cobertura escrita, no una ejecución
  real de release; los PRs finales SISOC conservan su gate y ciclo semanal HML.
- `gh pr merge --help` confirmó `--match-head-commit`; `gh pr checks --help` y
  `gh run watch --help` confirmaron las formas de seguimiento documentadas.

No aplica RED funcional: se modifican instrucciones Markdown, no lógica
ejecutable. El entorno virtual compartido no inicia por una referencia a Python
3.10 ausente; se usó el Python local disponible para los tests aislados, no el
runner completo del proyecto. No se realizan deploys, consultas adicionales a
repositorios satélite ni pruebas con datos o servidores reales. No se modificó
la lógica del sincronizador ni los workflows.
