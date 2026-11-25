# Cambio: detalle de seguimientos, seguimientos PNUD y actas en React sobre G1 v1 (#2785, R03.01 y R02.01)

## Alcance

Segunda y tercera entrega del
[contrato R01-R03](../../../plans/2026-T4/2026-11-10-2785-relevamientos-seguimientos-actas-m2.md),
sobre el
[listado y detalle de relevamientos](2026-11-12-2785-react-relevamientos-listado-detalle.md):

- R03.01: el detalle de una instancia del ciclo de seguimiento
  (`/comedores/<c>/relevamiento/<r>/seguimiento/<pk>/`), su alias histórico
  `.../primer-seguimiento/` y el detalle del seguimiento PNUD
  (`/comedores/<c>/seguimiento-pnud/<pk>`).
- R02.01: el detalle del acta complementaria
  (`/comedores/<c>/acta-complementaria/<pk>`).

Los PDF (`seguimiento_pdf`, `seguimiento_pnud_pdf`), las ediciones, las
revisiones y las bajas siguen siendo enlaces y POST nativos; la conversión SIPH
sigue en la vista nativa. No cambia vistas, plantillas, modelos ni la API de la
app territorial. No activa React en producción.

Archivos:

- `src/backends/comedores/relevamientos/web_api_views.py`,
  `web_api_serializers.py` y `web_api_urls.py`: cuatro endpoints `GET` bajo
  `/api/web/comedores/relevamientos/` (`.../relevamiento/<r>/seguimientos/<pk>/`,
  `.../seguimientos/primero/`, `.../pnud/<pk>/` y `.../actas/<pk>/`);
  `src/backends/config/url_registry.json` regenerado y
  `src/backends/config/middlewares/admindocs.py` con las rutas nuevas.
- `src/backends/comedores/relevamientos/web_preview.py`: tres entradas React sin
  montar (seguimiento y alias, PNUD, acta).
- `src/frontends/apps/sisoc/src/routes/relevamientosSeguimientos.tsx`,
  `relevamientosActas.tsx` y `relevamientosShared.tsx` (bloque de revisión,
  modal, resumen y adjuntos compartidos), registrados en `routes/index.ts`;
  `relevamientos.tsx` exporta los componentes que reutilizan.
- Pruebas: `tests/test_web_relevamientos_seguimientos_api.py`,
  `tests/test_web_preview_relevamientos_seguimientos.py`,
  `routes/relevamientosSeguimientos.test.tsx` y `routes/relevamientosActas.test.tsx`.

## Comportamiento

Cada endpoint instancia la vista nativa (`setup()`, `get_object()` y
`get_context_data()`) y proyecta su contexto: mismos 404 (instancia de otro
relevamiento o comedor, alias sin seguimientos con «El relevamiento no tiene
seguimientos.», PNUD o acta de otro comedor), mismos bloques de
`_bloque_campos`, mismas filas y valores impresos por el motor de plantillas
(fechas, «Sin asignar», «Sin técnico», «-»). Las firmas salen como nodos de
imagen generados por la propia etiqueta `optimized_image`. El PNUD publica
`pdf_url` solo para el formulario SIPH.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401, 403 con `state`); después superusuario o
`relevamientos.view_relevamiento`, sin alcance por usuario. Los botones salen de
los permisos Django como `perms.*`. Solo GET y HEAD; la lectura no escribe.

Los modales de revisión del coordinador y de baja del acta son formularios POST
nativos con CSRF a las mismas URL de hoy.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada; hoja de AdminLTE
presente.

- Backend: pruebas nuevas en verde, `black` y `pylint` 10/10.
- Frontend: Vitest del proyecto completo, `tsc`, ESLint y build de Vite.
- Visual (S13): seguimiento completo, sin bloques y alias, PNUD SIPH y no SIPH,
  acta de la app y sin contenido, modal de revisión y modal de baja, en
  1440x900 y 390x844.

## Limitaciones

- El cabezal de cada página pasa nodos al `<h3>` del marco compartido
  (`SisocShell`) con un cast de tipo (decisión aceptada; ver el cambio del
  detalle de relevamientos).
- Las imágenes de firma dependen de que `optimized_image` pueda generar la
  versión WebP (igual que la página nativa).
