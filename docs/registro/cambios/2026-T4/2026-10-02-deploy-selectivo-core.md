# Deploy selectivo del core

Continúa `2026-10-01-backends-ola4-sisoc-core.md` (#2309).

## Qué cambió

- **Un cambio solo en `backends/sisoc_core/**`** (Comedores, admisiones,
  relevamientos, PWA, dashboard, etc.) ya no hace un deploy completo:
  - construye la imagen del core y el migrador, y migra;
  - recrea solo los servicios que corren la imagen `sisoc/core`. En QA son
    `django` y `ocr_worker`; en PRD, además, los workers de importación,
    credenciales y mailing.
- **Los 7 backends de vertical siguen corriendo** con su imagen anterior.
  Ninguna imagen de vertical incluye `sisoc_core`, así que el cambio no los
  afecta.
- **Cómo se eligen los servicios:** `deploy_targets.py` devuelve el marcador
  `@core`, y `deploy_refresh.sh` lo traduce con `docker compose config` a
  los servicios con imagen `sisoc/core` de ese entorno. Si no puede
  resolverlos, hace un deploy completo.
- **Cambios mixtos:** si el cambio también toca `kernel/`, `config/`,
  `templates/`, `static/` u otro código compartido, el deploy sigue siendo
  completo.

## Riesgos

- **Mientras se recrea el core,** el proxy no atiende. Los backends siguen
  vivos, pero sin tráfico. Es el mismo corte que en un deploy completo, pero
  más corto.
- **El migrador corre todas las migraciones,** igual que en el deploy
  selectivo de un vertical.
