# Cambio: ficha de actividad y participantes de un centro CDF en React sobre G1 v1 (#2785, CDF-C)

## Alcance

Primera unidad de actividades CDF, apilada sobre
[centros](2026-11-10-2805-react-cdf-centros-consulta.md) y
[gestión de centros](2026-11-10-2805-react-cdf-centros-gestion.md): ficha de la
actividad (`/centrodefamilia/centros/actividades/<pk>/detalle/`), búsqueda y alta
de participantes
(`/centrodefamilia/centros/<centro>/actividades/<actividad>/participantes/crear/`)
y confirmación de baja (`.../participantes/<pk>/eliminar/`), con la promoción
desde la lista de espera dentro de la ficha. Contrato: CDF-C de
[participantes y asistencia](../../../plans/2026-T4/2026-10-28-2785-cdf-participantes-asistencia-m2.md).
Decisión de acceso:
[D1](../../decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).

No cambian las vistas `ActividadCentroDetailView` ni `ParticipanteActividad*`, el
formulario, el servicio `ParticipanteService`, las plantillas ni la regla de
acceso. No activa React en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_actividades.py` (API web) y
  `web_api_actividades_urls.py`, incluido desde
  `src/backends/cdf/cdf_runtime/web_api_urls.py`.
- `src/backends/cdf/centrodefamilia/web_preview_actividades.py`: entradas de las
  tres pantallas.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfActividades.tsx` (ficha y modal de cupo),
  `cdfParticipantes.tsx` (búsqueda, alta y baja) y `cdfCrispy.tsx` (campos de
  crispy compartidos), registrados en `routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_participantes_actividad.py`,
  `test_web_cdf_preview_actividades.py`, `cdfActividades.test.tsx` y
  `cdfParticipantes.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/actividades/<pk>/` | Contexto de la vista nativa: datos de la actividad, inscritos, lista de espera, costo total (precio por inscritos), `promo_error` y si el actor puede tomar asistencia |
| `GET .../centros/<c>/actividades/<a>/participantes/?query=` | Búsqueda por documento con el umbral nativo (siete dígitos), resultados y campos del formulario de ciudadano |
| `POST` en la misma ruta | `post()` nativo: alta por `ciudadano_id` o por formulario, lista de espera por cupo o por `allow_waitlist`, y las excepciones de dominio como aviso o error. Responde la redirección como JSON (`url`, `message`, `level`); el formulario inválido responde 400 con valores y errores |
| `GET/POST .../participantes/<pk>/eliminar/` | Datos de la confirmación; el POST corre `dar_de_baja` (historial y promoción automática) |
| `POST .../lista-espera/<pk>/promover/` | Cupo y promoción del primero por `fecha_registro`, no necesariamente la fila de la URL; sin cupo responde `promo_error` y no cambia nada |

Se conserva la política vigente: sesión y requisitos web (G1), `view_centro` y lo
que cada vista nativa exige después (solo login; no hay control de pertenencia del
centro ni de la actividad, igual que hoy). El umbral de la búsqueda sigue siendo
siete dígitos aunque el texto diga «mín 4 dígitos». El GET de promoción y el alias
histórico de la lista de espera siguen siendo vistas nativas que redirigen a la
ficha. El mensaje que encola la vista se deja en la cola y lo muestra la página a
la que se vuelve, una sola vez.

Pantalla React: mismo texto, orden y controles que las plantillas. «Agregar» y
«Crear y Asociar» envían sin validación del navegador y quedan deshabilitados con
el spinner, como `data-submit-with-spinner`; «Promover» no tiene ese estado en la
página nativa y no se le agrega. Ningún POST se reintenta: un resultado sin
confirmar muestra «No se pudo confirmar el resultado. Verificá el estado antes de
reintentar.».

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 28 pruebas nuevas en rojo (rutas inexistentes) y luego en verde:
  efectos persistidos, mensajes literales, rechazos sin cambios, orden de
  promoción, baja repetida, CSRF, cadena de acceso y entradas de vista previa.
- Frontend: Vitest de las dos rutas en verde, `tsc`, ESLint y build de Vite.
- Visual (regla S13): ficha con inscritos y espera, ficha vacía, modal de cupo,
  búsqueda, resultados, formulario de ciudadano, formulario con errores y
  confirmación de baja, en 1440x900 y 390x844: diferencia perceptual 0 % y desvío
  máximo de 0,02 px; orden de Tab igual.
- G1 de punta a punta (core y runtime CDF): anónimo 401, sin permiso 403, sin CSRF
  403, cabecera falsificada ignorada, formulario inválido 400 sin efectos, alta y
  baja persistidas.

## Limitaciones

- Mismas diferencias del marco compartido que las unidades anteriores (enlace del
  logo y menú móvil).
- Quedan fuera de esta unidad la toma de asistencia (CDF-D) y el alta, edición y
  listado de actividades (CDF-B), que siguen en las vistas nativas.
