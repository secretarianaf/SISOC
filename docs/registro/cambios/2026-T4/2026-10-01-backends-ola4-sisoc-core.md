# Ola 4: el código del core pasa a `backends/sisoc_core/`

Cierra el movimiento de código de #2309, #1931 y #2251. Continúa
`2026-10-01-backends-ola3.md`. Decisión 16 del ADR
`2026-09-30-monorepo-kernel-backends.md`.

## Qué cambió

- **Apps movidas.** Las 19 apps que corre solo el core pasan de la raíz a
  `backends/sisoc_core/`: acompanamientos, admisiones, comedores,
  comunicados, dashboard, duplas, encuestas, expedientespagos,
  gestion_organizaciones, historial, importarexpediente, insumos,
  intervenciones, ocr, pwa, relevamientos, rendicioncuentasfinal,
  rendicioncuentasmensual y usuarios.
- **Imports, app labels y migraciones** no cambian: `backends/sisoc_core` se
  agrega al `sys.path`, igual que los demás backends.
- **Imagen del core:** incluye `backends/sisoc_core` y ningún otro backend.
- **Deploy:** un cambio en `backends/sisoc_core/**` hace un deploy completo,
  igual que un cambio en esas apps cuando estaban en la raíz.

## Sin cambios

URLs, permisos, datos, comportamiento y el plan de deploy.

## Riesgos

- **Rutas de archivo fijas** (scripts, tests, herramientas externas) que
  apunten a `comedores/...` o a otra app en la raíz: hay que actualizarlas a
  `backends/sisoc_core/<app>/...`.
