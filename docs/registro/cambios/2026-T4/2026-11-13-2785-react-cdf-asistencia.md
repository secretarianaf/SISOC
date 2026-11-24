# Cambio: toma de asistencia de una actividad CDF en React sobre G1 v1 (#2785, CDF-D)

## Alcance

Segunda unidad de actividades CDF, apilada sobre
[ficha de actividad y participantes](2026-11-13-2785-react-cdf-actividades-participantes.md):
planilla de asistencia
(`/centrodefamilia/centros/actividades/<pk>/asistencia/`) con su fecha, sus
métricas y el guardado. Contrato: CDF-D de
[participantes y asistencia](../../../plans/2026-T4/2026-10-28-2785-cdf-participantes-asistencia-m2.md).
Decisión de acceso:
[D1](../../decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).

No cambian la vista `AsistenciaActividadView`, el servicio
`AsistenciaActividadService`, la plantilla ni la regla de acceso. No activa React
en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_asistencia.py` (API web); ruta en
  `web_api_actividades_urls.py` y entrada en `web_preview_actividades.py`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfAsistencia.tsx`, registrada en
  `routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_asistencia.py`,
  `test_web_cdf_preview_actividades.py` (entrada nueva) y
  `src/frontends/apps/sisoc/src/routes/cdfAsistencia.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/actividades/<pk>/asistencia/?fecha=` | Contexto de la vista nativa: fecha (hoy por defecto; una fecha inválida o futura vuelve a hoy con su aviso), planilla de los inscritos actuales ordenados por apellido y nombre con su marca (presente, ausente o sin marcar) y totales |
| `POST` en la misma ruta | `post()` nativo: guarda en una transacción y responde la redirección como JSON (`url` con `?fecha=AAAA-MM-DD`, `message`, `level`). **Lo no marcado se guarda como ausente.** Una fecha inválida o futura no guarda nada y la redirección vuelve a la planilla con el error |

Orden de acceso, igual que hoy: sesión y requisitos web (G1), `view_centro` (403),
actividad inexistente (404) y después `puede_tomar_asistencia_cdf` (referente del
centro, acceso CDF activo, rol SSE o superusuario; 403). Solo cuentan los inscritos
actuales: la lista de espera y las bajas no aparecen ni se guardan aunque lleguen
marcas en el POST. Repetir el guardado actualiza la marca y el autor del
registro de ese participante y esa fecha, sin duplicarlo; no hay bloqueo de edición
concurrente, igual que hoy. El mensaje de éxito queda encolado y lo muestra la planilla a
la que se vuelve.

Pantalla React: mismo texto, orden y controles que la plantilla. Las métricas se
recalculan en el navegador como el script nativo; «Presente (todos)» y «Ausente
(todos)» marcan todas las filas y se excluyen entre sí, pero desmarcar un casillero
masivo no limpia las filas y un cambio manual no los toca. El guardado no tiene
estado de espera en la página nativa y no se le agrega; un resultado sin confirmar
muestra «No se pudo confirmar el resultado. Verificá el estado antes de reintentar.»
y no reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 11 pruebas nuevas en rojo (ruta inexistente) y luego en verde:
  cadena de acceso con sus tres 403, solo inscritos y orden, None/True/False,
  guardado con ausente por defecto, repetición sin duplicado, fecha pasada,
  inválida y futura, CSRF y denegaciones sin efectos.
- Frontend: Vitest de la ruta en verde (7), `tsc`, ESLint y build de Vite.
- Visual (regla S13): planilla tomada, nueva, vacía, fecha inválida, fecha futura,
  «Presente (todos)» y una marca manual, en 1440x900 y 390x844: diferencia perceptual
  máxima 0,002 % y desvío máximo de 0,02 px; orden de Tab igual.
- G1 de punta a punta (core y runtime CDF): anónimo 401, sin permiso 403, sin CSRF
  403, cabecera falsificada ignorada, fecha futura rechazada sin cambios y guardado
  con la marca persistida y el no marcado como ausente.

## Limitaciones

- Mismas diferencias del marco compartido que las unidades anteriores (enlace del
  logo y menú móvil).
- Sin bloqueo ante guardados concurrentes de la misma planilla (conducta vigente).
