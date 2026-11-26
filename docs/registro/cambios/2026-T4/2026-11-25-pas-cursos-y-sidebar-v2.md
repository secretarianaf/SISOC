# Cambio: módulo Cursos PAS y sidebar de PAS v2

## Alcance

Sidebar de PAS v2 (`/v2/pas/`) y nuevo módulo **Cursos PAS**, reservado para
una próxima versión, en v1 y v2.

## Comportamiento

- **Sidebar v2**: deja de mostrar los grupos de SISOC *Administración* (del
  sistema) y *Tableros*. Queda una sección **Administración** propia de PAS con
  *Buscador PAS* (antes en Módulos › PAS) y *Cursos PAS*. Módulos › PAS
  conserva Panel de control, Dashboard e Informes. El sidebar de v1 no cambia.
- **Cursos PAS v1**: `/pas/cursos` (`pas_cursos`), con permiso
  `pas.view_paspersona`. Pantalla vacía con el fondo estándar de PAS v1
  (`pas-workspace`).
- **Cursos PAS v2**: `/v2/pas/cursos`. Lee `GET /api/web/pas/cursos/`
  (`pas_web_cursos`), que proyecta el contexto de la vista nativa como el
  resto de la API web de PAS (G1 + regla nativa). Pantalla vacía con el fondo
  estándar del theme (`background.default`).
- No agrega modelos, permisos, migraciones ni prefijos de URL; se regeneró
  `src/backends/config/url_registry.json`.

## Verificación

Validado en el entorno local:

- `pytest src/backends/pas/pas/tests/test_web_pas_cursos.py`: 4 passed (pantalla
  v1, permiso requerido, payload de la API y respuesta 401/403 sin sesión o sin
  permiso). También incluidos en la corrida completa de PAS del registro
  `docs/registro/cambios/2026-T4/2026-11-25-pas-sintys-liquidacion.md`.
- `vitest` del test "Cursos PAS" de `src/frontends/apps/pas-backoffice/src/App.test.tsx`:
  ubica Buscador PAS y Cursos PAS en Administración, Panel de control en
  Módulos › PAS y no muestra los grupos de SISOC. `tsc --noEmit` y `eslint`
  sin errores.
- `black`, `pylint` (10.00/10) y `djlint` sobre los archivos tocados;
  `generar_registro_urls` regenerado con `pas_cursos` y `pas_web_cursos`.
- No se revisó visualmente por el agente (el navegador de la sesión no tenía
  login); pendiente la CI del PR.

## Rollback

Para revertir solo este cambio:

1. Borrar `src/backends/pas/pas/templates/pas/cursos.html`,
   `src/backends/pas/pas/tests/test_web_pas_cursos.py` y
   `src/frontends/apps/pas-backoffice/src/Cursos.tsx`.
2. Quitar `PasCursosView` de `src/backends/pas/pas/views.py` y su ruta
   `pas_cursos` de `src/backends/pas/pas/urls.py`.
3. Quitar `PasCursosWebView` de `src/backends/pas/pas/web_api_views.py` y la
   ruta `pas_web_cursos` de `src/backends/pas/pas/web_api_urls.py`.
4. En `src/frontends/apps/pas-backoffice/src/App.tsx`, quitar la ruta
   `cursos` y la sección Administración de `MenuPas`; para recuperar los grupos
   de SISOC, restaurar `GrupoSisoc`, el tipo `NodoNav` y la lectura de
   `navigation` de `web/session/`, y volver *Buscador PAS* a Módulos › PAS.
5. Quitar el test "Cursos PAS" de
   `src/frontends/apps/pas-backoffice/src/App.test.tsx`.
6. Regenerar el registro: `python manage.py generar_registro_urls` (sin
   agregar las entradas `media/` y `static/` que aparecen con `DEBUG`).
7. Reconstruir el frontend: `docker compose up -d --build front_pas`.

No hay datos ni migraciones que deshacer.
