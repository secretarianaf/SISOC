# Cambio: comunicados publicados en React sobre G1 v1 (#2785, CM03.01)

## Alcance

Primera entrega del
[contrato CM01-CM03](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md):
el listado público `/comunicados/` y el detalle `/comunicados/ver/<pk>/` en su
variante sin gestión. Gestión, publicación, edición y mailing quedan para las
entregas siguientes. No cambia vistas, plantillas, modelos ni la API PWA
(`/api/comunicados/`). No activa React en producción.

Archivos:

- `src/backends/comedores/comunicados/web_api_views.py`,
  `src/backends/comedores/comunicados/web_api_serializers.py` y
  `src/backends/comedores/comunicados/web_api_urls.py`, incluidos desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado y
  `src/backends/config/middlewares/admindocs.py` con la ruta nueva.
- `src/backends/comedores/comunicados/web_preview.py`: entrada React sin montar
  (`comunicados_preview_patterns`), assets en `/comunicados/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/comunicados.tsx`, registrado en
  `routes/index.ts`; reutiliza `Pagination` de `routes/listControls.tsx`.
- Pruebas: `src/backends/comedores/comunicados/test_web_comunicados_publicados_api.py`,
  `src/backends/comedores/comunicados/test_web_preview_comunicados.py` y
  `src/frontends/apps/sisoc/src/routes/comunicados.test.tsx`.

## Comportamiento

`GET /api/web/comedores/comunicados/` ejecuta `ComunicadoListView`: solo
internos publicados y vigentes, búsqueda `titulo`, destacados primero, 20 por
página, 404 «Página no válida.» con página inválida. Fechas `d/m/Y H:i` en hora
local y resumen `truncatewords:50` salen del backend. `GET .../<pk>/` ejecuta
`ComunicadoDetailView` con su mismo queryset (sin filtro para gestores) y
devuelve los permisos del contexto nativo. Acceso: G1 primero (401 sin sesión,
403 con requisito pendiente) y después cualquier usuario autenticado, como
`LoginRequiredMixin`. Solo GET y HEAD, sin escrituras.

La vista previa sirve React en el detalle solo a usuarios sin
`can_manage_comunicados`; los gestores siguen viendo la página nativa hasta que
se acepte CM02.01.

## Verificación

Entorno sintético, sin red, imagen fijada. Pruebas nuevas en rojo sobre la base
y en verde; Vitest del proyecto tres veces, `tsc`, ESLint y build de Vite;
`black`, `pylint` 10/10 y `makemigrations --check`. Visual S13 en 6 estados
(lector, gestor, filtro, vacío, detalle destacado con adjuntos y vencimiento,
detalle simple), escritorio y móvil: 0,000 % de píxeles distintos y desvío
máximo 0,06 px fuera del menú. Guardas iguales: anónimo al login, páginas 9 y
`x` 404, borrador e inexistente 404 para lector, gestor ve el detalle nativo.

## Limitaciones

- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  («Inicio de SISOC») en React; cambia el primer elemento del orden de Tab.
- Los adjuntos se enlazan a `/media/` como en la página nativa.
