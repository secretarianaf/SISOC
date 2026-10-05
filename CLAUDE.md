# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Fuente de verdad para comportamiento de IA: `AGENTS.md`.

## Arranque mínimo

1. `AGENTS.md`
2. `docs/indice.md`
3. archivo objetivo + tests cercanos
4. una guía relevante de `docs/ia/` según la tarea
5. ampliar solo con evidencia concreta

## Comandos

```bash
# Levantar el stack local
docker compose up

# Ejecutar todos los tests (paralelo)
docker compose exec django pytest -n auto

# Ejecutar un archivo de tests específico
docker compose exec django pytest src/backends/<kernel|vertical>/tests/test_<modulo>.py -v

# Solo tests smoke (sin DB real)
docker compose exec django pytest -m smoke

# Tests que requieren MySQL real (CI)
docker compose exec django pytest -m mysql_compat

# Formatear Python
black .

# Lint Python
pylint <app>/

# Lint templates Django
djlint src/backends/kernel/templates/ --check
```

## Arquitectura

Django 5.2 + MySQL 8.4, desplegado con Docker Compose. Python 3.11+.

**Organización de apps:** cada dominio de negocio es una Django app propia (`src/backends/sisoc_core/comedores/`, `src/backends/pas/pas/`, `src/backends/kernel/users/`, etc.). La lógica de negocio vive en `<app>/services/`, nunca en views ni modelos. Las views son CBVs sin lógica. DRF coexiste con las views tradicionales; los serializers van en `api_serializers.py` y las API views en `api_views.py`.

**Core compartido:** `src/backends/kernel/core/` expone utilidades reutilizables (soft delete, permisos, cache, auth de API, validadores). No duplicar lo que ya existe ahí.

**Estructura (#1931/#2251/#2639):** todo el código vive en `src/`. `src/backends/kernel/` contiene el código común (`core`, `users`, `iam`, `ciudadanos`, `audittrail`) y los templates/static compartidos; el cluster de Comedores y los servicios propios del core van a `src/backends/sisoc_core/`, cada vertical a `src/backends/<vertical>/` y cada front a `src/frontends/apps/<modulo>/`. Los imports no cambian (`import core`, `import users`): `src/backends/config/__init__.py` agrega el kernel y los verticales al `sys.path`. Ver `docs/registro/decisiones/2026-10-02-estructura-src-backends.md`.

**Configuración central:** `src/backends/config/settings.py` centraliza DB, cache, middleware, apps instaladas, logging custom e integraciones externas (GESTIONAR, RENAPER, Sentry, PWA). El stack de middleware define contexto de seguridad, sesión, auditoría y thread-locals en ese orden — el orden importa.

**Tests:** junto a su dueño: los transversales en `src/backends/kernel/tests/`, los de cada vertical en `src/backends/<vertical>/tests/` o dentro de la app; los fixtures globales están en el `conftest.py` raíz. SQLite in-memory por defecto; el marker `mysql_compat` activa MySQL real. `pytest --reuse-db` reutiliza el schema entre corridas para acelerar.

**Registro de cambios:** todo cambio funcional visible, decisión de arquitectura o trade-off importante debe registrarse en `docs/registro/` (ver `docs/registro/README.md`).

## Reglas cortas

- No inventar modelos, endpoints, permisos ni settings sin evidencia en el repo o pedido explícito.
- Cambios pequeños y revisables; no mezclar feature + refactor + formateo masivo.
- Respetar `docs/ia/CONTEXT_HYGIENE.md` para decidir cuánto contexto cargar.
