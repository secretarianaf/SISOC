# Cambio: dashboard de Centro de Familia y tableros embebidos en React sobre G1 v1 (#2785, D01)

## Alcance

Cuarta unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md): `/dashboard/centro-de-familia` y
`/dashboard/<slug>/`. Lee por `DashboardView` y `TableroEmbedView`, sin escrituras propias (la actualización de métricas es la de la vista
nativa) y sin tocar vistas, plantillas ni URLs nativas. No activa React en producción.

Archivos: `src/backends/sisoc_core/dashboard/web_api_dashboard.py`, `web_api_urls.py`, `web_preview_dashboard.py`,
`src/frontends/apps/sisoc/src/routes/dashboardTableros.tsx`, montaje en `config/urls.py`, `url_registry.json`,
`config/middlewares/admindocs.py` y `routes/index.ts`. Pruebas: `test_web_dashboard_api.py`, `test_web_preview_dashboard.py` y
`dashboardTableros.test.tsx`.

## Comportamiento

- Acceso: sesión (401) y compuerta G1. El tablero conserva su 403 (`usuario_puede_ver`), su 404 y el redirect a su pantalla propia.
- Sin `dashboard.view_dashboard` la API no devuelve números; la pantalla muestra solo el logo, como la plantilla.
- Si la fuente remota falla se muestra el aviso nativo y los últimos valores guardados; sin datos, «Sin información», nunca cero.
- Los CDN y los iframes remotos son los de la plantilla; en las pruebas visuales el acceso a internet está bloqueado en ambos lados.

## Verificación

Backend (imagen fijada, sin red): 11 pruebas de API y 2 de vista previa; `black`, `pylint` y `makemigrations --check`. Frontend: 13 pruebas,
`tsc`, `eslint` y build. G1 de extremo a extremo (401, 403, requisito pendiente, cabecera falsificada, CSRF, lectura de tablero y de
dashboard, 404). Comparación visual nativo contra React (con permiso, sin permiso, tablero plano, Looker y en confección; escritorio y
móvil) y guardas: 0,000 % de diferencia.

## Limitaciones

El contenido de los iframes remotos no se compara. El botón de colapso reproduce el efecto de AdminLTE (clase, cuerpo oculto e ícono).
