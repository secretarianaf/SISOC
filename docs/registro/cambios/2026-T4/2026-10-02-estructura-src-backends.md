# Orden de la raíz del repo (#2639)

Decisión: `docs/registro/decisiones/2026-10-02-estructura-src-backends.md`.
Plan: `docs/plans/2026-T4/2026-10-02-issue-2639-orden-raiz-plan.md`.

## Qué cambió

- **Código:** `config/`, `kernel/` y `backends/*` están en `src/backends/`;
  `frontends/` en `src/frontends/`. Los imports, app labels, migraciones y
  tareas de Celery no cambian.
- **Templates, estáticos y tests** se repartieron por dueño. Lo compartido
  está en `src/backends/kernel/{templates,static,tests}/`; 95 estáticos de un
  solo vertical pasaron a `<app>/static/custom/` (misma URL pública) y 144
  tests a `src/backends/<vertical>/tests/`. Los fixtures de `tests/conftest.py`
  están en el `conftest.py` raíz.
- **Deploy:** el migrador corre `collectstatic` (es la única imagen con todos
  los estáticos); el core monta `static_root/` en solo lectura. Las imágenes
  usan `PYTHONPATH=/sisoc/src/backends`.
- **`deploy_targets.py`:** `src/backends/<x>/tests/` no despliega; `kernel/`
  y `config/` siguen siendo despliegue completo.
- **Compose y requirements:** los overrides están en `docker/compose/` (usar
  `--project-directory` en la raíz); `requirements.txt` pasó a
  `requirements/all.txt`.
- **Limpieza:** se borraron `centros.xlsx`, `usuarios.xlsx`, `coverage.json`,
  `appspec.yml`, `.idea/`, los `.env` por entorno y el `package-lock.json`
  vacío de la raíz. No se reescribió el historial.
- **Docs:** registros por trimestre (`AAAA-TN/`); se borró
  `docs/contexto/features/`; `CODEX.md`, `LLM.md` y `docs/agentes/guia.md` se
  fusionaron en `AGENTS.md`; `postman/` está en `docs/api/postman/` y
  `AGENT_REPO_MAP.md` en `docs/ia/`.
- **Skills:** `.agents/skills/` es la fuente y `.claude/skills/` una copia
  generada por `scripts/ai/sync_skills.py` (ver `docs/ia/SKILLS.md`).

## Impacto para devs

- `docker compose up` y `python manage.py ...` funcionan igual.
- Los tests nuevos van junto a su dueño (ver `docs/ia/TESTING.md`).
- Un estático de un solo vertical va en `<app>/static/custom/`.
- Para deploy manual con un override: `docker compose --project-directory .
  -f docker/compose/docker-compose.deploy.yml ...`.

## Riesgos y rollback

- **Primer deploy:** es completo y cambia dónde corre `collectstatic`. Si en
  HML/PRD falta un estático en el manifest, la página da error 500. Validar en
  QA las pantallas de cada vertical antes de promover.
- **Rutas de runtime:** `media/`, `logs/` y `static_root/` siguen en la raíz
  del checkout del servidor.
- **Sentry:** cambian las rutas de los stack traces (revisar code mappings).
- **Rollback:** revertir el merge y desplegar. El revert vuelve a poner
  `collectstatic` en el core.
