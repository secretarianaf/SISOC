# #2639: auditoría ampliada de estructura y DX

Estado: revisión local y correcciones focalizadas; no es aceptación en QA.
Complementa la [verificación de rutas](2026-10-05-2639-verificacion-rutas.md).

## Criterio de orden

El código se concentra en `src/backends/`, `src/frontends/` y `src/scripts/`.
Imágenes/Compose viven en `docker/`, dependencias Python en `requirements/`,
documentación en `docs/` y automatización GitHub en `.github/`.
Cada backend conserva sus apps, recursos y tests; los siete registros de
verticales apuntan a directorios existentes. El frontend conserva `apps/` y
`packages/` como workspace npm.

La raíz del repo y la del workspace npm conservan los archivos que sus
herramientas descubren por convención. Trasladarlos por estética requiere
configurar cada consumidor y puede romper editores o comandos directos.
Los scripts manuales heredados siguen en `src/scripts/`; no se cambian sus
procedimientos de datos para uniformar carpetas.

## Hallazgos y correcciones

- CI Pylint conservaba `**/*.py`, que sin globstar busca un nivel y ahora
  queda sin coincidencias. Se reemplazó por `src/scripts/*.py`, conservando
  la cobertura anterior de scripts directos y config/apps. El glob completo
  resuelve 815 archivos existentes. No se amplió a todas las subcarpetas.
- El debugger nativo lanzaba `manage.py` con su default de core. Se declaró
  `config.settings_all`, coherente con el desarrollo de composición completa.
- `debug_cruce.py` importaba modelos antes de preparar las rutas e inicializar
  Django. Se reprodujo `ModuleNotFoundError: celiaquia.services`. El bootstrap
  ahora precede los imports y usa `settings_all` por defecto; respeta un módulo
  de settings explícito. No se ejecutó su consulta de datos.
- Se corrigieron la ruta de uso del script manual de intervenciones, los
  settings documentados de pytest, el origin y la preparación de `.env` en
  README. La guía de instalación vuelve a usar `scripts/` para SISOC-Mobile:
  ese repositorio externo no fue reorganizado junto con SISOC.

## Evidencia nueva

Backend: contenedores `--rm --network none` usando las dependencias de
`sisoc-ci/migrator:latest`, fuentes actuales montadas readonly en `/audit`,
sin `.env` y con `PYTEST_RUNNING=1`, `USE_SQLITE_FOR_TESTS=True`,
`DJANGO_SETTINGS_MODULE=config.settings_all` y entorno dev.

| Comprobación | Resultado |
|---|---|
| `python manage.py check` | Sin problemas |
| `python -m pytest --collect-only -q -o addopts= -p no:cacheprovider` | 6308 tests descubiertos, sin errores |
| Tests de `test_servicios_backends.py`, `test_runtime_unit.py`, `test_deploy_targets.py`, `test_deploy_workflow.py` | 44 pasaron; incluye arranque/páginas de siete verticales, separación del core, registro de URLs y grafo de migraciones de usuarios |
| `runpy` del debugger sin ejecutar `__main__`, seguido de imports de sus modelos | OK sin queries; también se verificó el default sin settings explícito |
| Pylint sobre los dos scripts Python tocados | OK, 10/10 |
| Black sobre `src/scripts/` y el test de rutas de deploy | 18 archivos sin cambios necesarios |
| `python src/scripts/ci/check_docs_paths.py` | 80 documentos vigentes, 0 referencias obsoletas |
| `python src/scripts/ai/sync_skills.py --check` | Copias sincronizadas |
| `git diff --check` | OK |

La primera prueba montó fuentes nuevas sobre `/sisoc` de una imagen antigua:
su antiguo `/sisoc/scripts/` y workflows produjeron colisiones de imports y
fallos de fixtures de archivos. Se corrigió el experimento usando `/audit`
con fuentes/configuraciones actuales. Esos fallos no se atribuyen al repo.

## Límites y riesgos heredados

No se ejecutaron los 6308 tests, compatibilidad MySQL, import-linter, un deploy
ni scripts sobre datos reales. Las pruebas frontend, builds y Nginx de la
revisión anterior siguen documentadas por separado; no se repitieron porque
esta pasada no cambió su código/configuración. El debugger de VS Code se
revisó y alineó, pero no se inició una sesión interactiva del editor.

`src/scripts/update_fixtures_from_production.py` es una herramienta heredada de
datos: necesita settings adecuados a los modelos exportados y abre el destino
antes de confirmar `dumpdata`. No se probó ni modificó su procedimiento de
producción. `src/scripts/crontab` contiene rutas de servidor heredadas; no se
instaló y no debe confundirse con una configuración activa validada. Los cron
externos y comandos guardados que usen rutas antiguas requieren revisión al
incorporar el cambio.

Se aplicó `systematic-debugging`: reproducción de glob/imports, comprobación
de la causa y validación posterior. Se evitó otra reorganización estética que
introdujera consumidores nuevos o cambiara procedimientos operativos.
La validación no ejecutó deploy ni operaciones sobre datos reales. Las
correcciones se incorporan al PR #2650 contra `development`, separadas en
commits de CI, DX y documentación. Se conservan los temporales de pytest
cuya limpieza recursiva fue rechazada en la revisión anterior.
