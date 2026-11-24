# Cambio: listado de actividades y catálogo de actividades CDF en React sobre G1 v1 (#2785, CDF-B)

## Alcance

Tercera unidad de actividades CDF, apilada sobre
[toma de asistencia](2026-11-13-2785-react-cdf-asistencia.md): listado de
actividades (`/centrodefamilia/actividades/`) y alta de una actividad del catálogo
(`/centrodefamilia/actividades/nueva/`). Contrato: «Actividades» de
[centros y actividades](../../../plans/2026-T4/2026-10-28-2785-cdf-centros-actividades-m2.md).
Decisión de acceso:
[D1](../../decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).

No cambian `ActividadCentroListView`, `ActividadCreateView`, `ActividadForm`, las
plantillas ni la regla de acceso. No activa React en producción. El alta y la
edición de una actividad de un centro (`ActividadCentroForm`, con su hora y sus
selectores) siguen en la vista nativa.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_actividades_gestion.py` (API web); rutas
  en `web_api_actividades_urls.py` y entradas en `web_preview_actividades.py`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfActividadList.tsx` (listado y catálogo),
  registrada en `routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_actividades_gestion.py`,
  `test_web_cdf_preview_actividades.py` (entradas nuevas) y
  `src/frontends/apps/sisoc/src/routes/cdfActividadList.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/actividades/?centro=` | Contexto de la vista nativa: sin paginación, ordenado por centro y actividad, filtrado por centro si se pasa. Incluye los encabezados de la tabla |
| `GET/POST /api/web/cdf/actividades/nueva/` | Campos del formulario `ActividadForm` (categoría y nombre) y `post()` nativo: guarda y responde la redirección al listado de centros como JSON, sin encolar mensaje; el formulario inválido responde 400 con valores y errores |

Se conserva la política vigente: sesión y requisitos web (G1), `view_centro` y
solo login en las vistas nativas. El `test_func` de la vista del catálogo nunca se
evalúa (la clase no usa `UserPassesTestMixin`), así que un usuario sin
superusuario también puede guardar, igual que hoy; no se agrega ese control.

Se conservan los detalles de la plantilla: el título, los botones y el
breadcrumb salen vacíos porque la vista no los pone en el contexto; una actividad
sin días muestra el texto del administrador relacionado (`core.Dia.None`); el
orden local por columna es el de `listSort.js` (tres estados, sin volver al orden
original) y no cambia el orden del servidor. El catálogo envía con la validación
del navegador, como el formulario nativo.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 9 pruebas nuevas en rojo (rutas inexistentes) y luego en verde: orden,
  filtro, texto de días vacíos, campos con sus atributos, alta persistida sin
  mensaje, rechazo sin cambios, acceso solo por login y `view_centro`, CSRF y
  entradas de vista previa.
- Frontend: Vitest de la ruta en verde (8), `tsc`, ESLint y build de Vite.
- Visual (regla S13): listado, filtrado, vacío, orden por centro y descendente por
  horario, catálogo y catálogo con errores, en 1440x900 y 390x844: diferencia
  perceptual 0 % y desvío máximo de 0 px; orden de Tab igual.
- G1 de punta a punta (core y runtime CDF): anónimo 401, sin permiso 403, sin CSRF
  403, cabecera falsificada ignorada, alta rechazada con 400 y alta persistida.

## Limitaciones

- Mismas diferencias del marco compartido que las unidades anteriores (enlace del
  logo y menú móvil).
- El estado de `hover` de los encabezados ordenables tiene una transición de 0,2 s;
  las pruebas visuales de orden esperan a que termine antes de comparar.
