# VPSL React: cierre de revisión contra frontend_v2

Con la implementación oficial del PR #2566 como base, se cerraron los faltantes del adaptador y de las pantallas: instrucciones de subsanación, cartas, contactos, evidencias, actas e historiales, fechas en es-AR, estados neutrales y contraste AA. La API acepta JSON para datos y multipart para archivos sin duplicar validación de ModelForms; sesión, CSRF, permisos y alcance provincial siguen en Django. El alcance se comparte entre vistas y API en `services/access.py`.

El detalle de jornada entrega checklist y cierre; registros y casos de laboratorio se paginan en rutas propias con el formato DRF y límite 200. OpenAPI documenta variantes de entrada y salida, incluida la excepción de graduación histórica, y se regeneraron los tipos TS. El frontend divide bundles y carga Sentry solo si hay DSN.

Desarrollo local usa el upstream Vite correcto, CSP acotada a HMR en `/v2/` y un preámbulo de React Refresh externo. CI ejecuta frontend en todos los PR de las ramas protegidas, lo exige para el guard de deploy y comprueba auditoría y E2E. Las verificaciones y límites vigentes se detallan en `docs/operacion/ver_para_ser_libre_react.md`.

## Evidencia local de cierre

- 165 pruebas Python del módulo VPSL, router y despliegue aprobadas en SQLite de pruebas; `manage.py check` limpio y sin migraciones pendientes.
- OpenAPI generado sin warnings y coincidente byte a byte con el archivo versionado; tipos TypeScript regenerados.
- Node 22.14.0: `npm ci`, auditoría de cero vulnerabilidades, ESLint, TypeScript, 14 pruebas Vitest y build aprobados.
- Tres flujos Playwright sobre el build final y la imagen Nginx, con CSP estricta: subsanación con archivo/CSRF, envío JSON/CSRF y 403 visible sin reintentos.
- La imagen `prod` se construyó y el Nginx del contenedor devolvió 200 para la raíz y una ruta React profunda. Compose de desarrollo válido. Pylint focal 10/10 y Black conforme.

Estas pruebas no sustituyen una validación en homologación de RENAPER, Maps, almacenamiento, perfiles reales y medidas visuales de Figma.
