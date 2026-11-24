# Cambio: servir el build React de SISOC en producción (#2785)

## Qué cambia

- `FRONTEND_V2_UPSTREAMS["sisoc"]` (`FRONT_SISOC_ORIGIN`) y el servicio `front_sisoc` en `docker-compose.deploy.yml`,
  igual que Celiaquía (PR #2644). El core proxea `/v2/sisoc/` y `/v2/sisoc/assets/`.
- Chequeo de salud de `front_sisoc` en QA, HML y producción (`deploy.yml`).
- Setting `SISOC_REACT_BUILD_DIR` y stage `export` del Dockerfile de frontends para el build congelado de las entradas `web_preview_*`.
- No monta ninguna URL: eso lo hace el flag de activación por vertical.

## Cómo se verificó

- Test `test_v2_sisoc_esta_en_el_allowlist_y_proxea_al_front_sisoc` (pytest en imagen fijada), black y pylint.
- No se desplegó ni se construyó la imagen.

## Limitaciones

- Falta copiar el `export` a las imágenes de los runtimes (`docker/django/Dockerfile`) y leer `SISOC_REACT_BUILD_DIR` al montar las entradas.
