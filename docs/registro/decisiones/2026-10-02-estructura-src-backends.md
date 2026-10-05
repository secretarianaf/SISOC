# 2026-10-02 — Estructura del repo: `src/backends/` con kernel y config adentro

## Estado

Aceptada (#2639). Reemplaza la parte de estructura del repo de
`2026-09-30-monorepo-kernel-backends.md` (punto 2 y sus rutas `kernel/`,
`backends/` y `frontends/`). El resto de esa decisión sigue vigente.

## Contexto

- Tras la modularización (#1931, #2251 y #2309) la raíz mezclaba código
  (`config/`, `kernel/`, `backends/`, `frontends/`, `templates/`, `static/`,
  `tests/`), datos que no debían estar versionados (`centros.xlsx`,
  `usuarios.xlsx`), artefactos (`coverage.json`, `appspec.yml`, `.idea/`),
  `.env` por entorno, seis archivos de compose y varios archivos para agentes.
- El issue planteó como contras de mover el código a `src/`: volver a mover
  todas las rutas (Dockerfile, `sys.path`, pytest, pylint, import-linter, CI,
  scripts de deploy y docs), generar conflictos en PRs abiertos y que el
  beneficio sea solo de orden.
- El responsable técnico (juanikitro) aceptó esas contras "siempre y cuando se
  documente como decisión y el orden que se gana sea mantenible y usable, que
  no complique a los devs".

## Decisión

Las definió el responsable técnico. Las marcadas como *recomendación del
agente* surgieron de la propuesta del agente y fueron aceptadas.

1. **Código en `src/`.** `src/backends/{config, kernel, sisoc_core, <vertical>}`
   y `src/frontends/`. `kernel/` y `config/` van **dentro** de `backends/`
   porque son código del backend. `manage.py` queda en la raíz.
2. **`BASE_DIR` sigue en la raíz** (de ahí salen `media/`, `logs/` y
   `static_root/`, que montan los servidores); `BACKENDS_DIR` apunta al
   código. Los imports no cambian (`import core`, `import pas`): `manage.py`,
   el `PYTHONPATH` de las imágenes y `pytest.ini` agregan `src/backends/`, y
   `config/__init__.py` agrega el kernel y los verticales. *Recomendación del
   agente:* `PYTHONPATH` en el Dockerfile en lugar de un flag en cada comando
   de gunicorn y celery.
3. **`templates/`, `static/` y `tests/` se reparten por dueño.** Lo compartido
   va a `src/backends/kernel/` y lo de un vertical, a su app
   (`<app>/static/custom/...`, con la misma ruta pública) o a
   `src/backends/<vertical>/tests/`.
4. **`collectstatic` pasa al migrador.** El core no tiene los estáticos de los
   verticales, así que el migrador (composición completa) corre
   `collectstatic` sobre `static_root/` en cada deploy y el core lo monta en
   solo lectura. El responsable eligió esto en lugar de dejar todos los
   estáticos en el kernel.
5. **Compose:** `docker-compose.yml` (desarrollo) queda en la raíz; los
   overrides van a `docker/compose/` y se usan con `--project-directory` en la
   raíz. *Recomendación del agente.*
6. **`requirements.txt` pasa a `requirements/all.txt`**, sin cambiar qué se
   instala.
7. **Datos y `.env`:** se borran los `.xlsx`, `coverage.json`, `appspec.yml`,
   `.idea/` y los `.env.qa`, `.env.homologacion` y `.env.prod` (el deploy usa
   el `.env` de cada servidor). **No se reescribe el historial de git**: los
   archivos borrados siguen en commits anteriores.
8. **Documentación:** los registros (`docs/registro/cambios/`,
   `docs/registro/prs/`, `docs/plans/`) se ordenan por trimestre (`AAAA-TN/`)
   y el bot escribe directo así; `docs/registro/decisiones/` no se mueve. Se
   borra `docs/contexto/features/`, que duplicaba el registro del PR (decidido
   durante la implementación).
9. **Skills compartidas entre Codex y Claude Code:** la fuente vive en
   `.agents/skills/` y `scripts/ai/sync_skills.py` genera la copia en
   `.claude/skills/`; un check de CI falla si difieren. *Recomendación del
   agente:* se descartaron las symlinks porque se rompen en Windows con
   `core.symlinks=false`.

## Alternativa descartada

**Dejar el código donde estaba** y ordenar solo lo que no es código. Evitaba
mover rutas otra vez y los conflictos con PRs abiertos, pero la raíz seguía
mezclando código con configuración y docs. Se eligió el orden mantenible
aunque implique mover rutas.

## Consecuencias aceptadas

- **Gana:** la raíz queda con configuración, puntos de entrada y carpetas con
  propósito (mapa en `README.md`); cada vertical tiene juntos su código,
  templates, estáticos y tests; los registros no crecen sin límite en una sola
  carpeta.
- **Pierde:** links rotos en issues y PRs viejos que apuntan a rutas movidas;
  conflictos con ramas abiertas; rutas distintas en los stack traces de
  Sentry; quien use un override de compose sin `--project-directory` resuelve
  mal las rutas relativas.
- **Riesgo operativo:** el primer deploy después del cambio es completo y
  cambia dónde corre `collectstatic`. Se valida en QA antes de HML y PRD.

## Cuándo revisarla

*Recomendación del agente; no la definió el responsable técnico.*

- Si se encara la separación de dominios de #2641 (sacar `ciudadanos`,
  `organizaciones` y `catalogo_intervenciones` del kernel y partir
  `sisoc_core`): esa decisión cambia lo que hay dentro de `src/backends/`.
- Si `collectstatic` en el migrador alarga los deploys o algún servicio
  necesita estáticos que el migrador no tiene.
- Si las herramientas de agentes leen skills de una sola carpeta común y la
  copia deja de hacer falta.
