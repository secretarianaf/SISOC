# Cambio: mailing masivo de comunicados en React sobre G1 v1 (#2785, CM01)

## Alcance

Entregas CM01.01 (formulario con últimos lotes y detalle del lote) y CM01.02
(crear lote y reanudar) del
[contrato de comunicados y mailing](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).
CM02 y CM03 ya están en React y no se tocan.

No cambia vistas, formularios, servicios, modelos, plantillas ni URLs nativas,
ni el worker `process_mailing_jobs`. No activa React en producción. La API
nunca envía correo ni arranca el worker: crear un lote solo deja un
`MailingJob` en `pending`; el envío sigue siendo del job asíncrono existente.

Archivos:

- `src/backends/comedores/comunicados/web_api_mailing.py` y
  `web_api_mailing_urls.py`, incluidos desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/comedores/comunicados/web_preview_mailing.py`: entradas React sin
  montar, assets en `/comunicados/mailing-react/assets/`.
- `src/frontends/apps/sisoc/src/routes/comunicadosMailing.tsx`, registrado en
  `routes/index.ts` antes del módulo de comunicados.
- Pruebas: `test_web_comunicados_mailing_api.py`,
  `test_web_preview_comunicados_mailing.py` y
  `routes/comunicadosMailing.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/comunicados/mailing/` | `MailingUploadView`: campos del formulario, enlace a la plantilla y últimos 10 lotes del propio usuario |
| `POST` ídem (multipart) | Valida el libro y crea el lote `pending` con sus adjuntos; 400 con los errores nativos por campo y los valores escritos; 415 si no es multipart |
| `GET .../mailing/jobs/<pk>/?page=` | Detalle de cualquier lote (50 filas por página, `page` inválido tolerado); inexistente 404 |
| `POST .../mailing/jobs/<pk>/resume/` | `MailingJobResumeView`: 200 también cuando el lote no está fallido (el error nativo queda en cola) |

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero; después `is_admin` en todas (403 sin mensaje). El detalle de un lote
ajeno sigue siendo visible para cualquier administrador.

Los mensajes de éxito quedan en la sesión y los consume el detalle del lote,
como la página nativa. Crear y reanudar exigen CSRF, se envían una sola vez y
ante un resultado incierto la pantalla no reenvía («Revise los últimos lotes…»,
«Use Actualizar estado.»). «Descargar plantilla» conserva el envío GET nativo y
«Actualizar estado» es un enlace.

## Verificación

Entorno sintético, sin red, sin worker y con el backend de correo en memoria
(`locmem`); imagen fijada.

- Backend: 14 pruebas (12 de API: lecturas sin efectos ni correo, alta con
  adjuntos, rechazos, reanudar, 403/401/CSRF/415, 404; y 2 de servicio con `locmem`: una dirección inválida detiene el lote y reanudar
  reintenta la misma fila; un lote reclamado no se toma dos veces), y 4 de preview; black y
  pylint 10/10; `makemigrations --check` sin cambios.
- Frontend: 12 pruebas de ruta; Vitest completo (1499 en verde), `tsc`,
  ESLint y build de Vite.
- Visual (S13), 7 estados (formulario con últimos lotes, formulario rechazado,
  detalle fallido con error, adjunto y 2 páginas, pendiente, procesando,
  completado) en 1440x900 y 390x844: estructura, texto, orden de Tab y
  geometría iguales (desvío máximo 0,03 px), diferencia de píxeles 0,000 %.
  Anónimo, sin rol de administrador y lote inexistente responden igual. Los
  lotes de captura son filas sintéticas en la base: nunca se envió el formulario
  con datos ni corrió el worker.
- G1 de punta a punta (core y runtime de Comedores con gunicorn): anónimo 401,
  sin permiso 403, requisito pendiente 403, header falsificado ignorado, POST
  sin CSRF 403, lectura del formulario y de un lote ajeno 200, alta vacía 400 y
  reanudar un lote fallido 200.

## Limitaciones

- El detalle expone asunto, cuerpo, destinatarios y adjuntos de lotes de otros
  administradores: es el comportamiento nativo y se conserva.
- «Descargar plantilla» sigue siendo un envío GET que lleva asunto y cuerpo a la
  URL, como el nativo (el contrato proponía un enlace; se prefirió la paridad
  estructural, igual que la importación masiva de ciudadanos).
- La carrera nativa entre crear el lote `pending` y sus adjuntos se conserva.
- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo y
  menú móvil.
