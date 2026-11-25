# Cambio: alta y edición de una actividad de un centro CDF en React sobre G1 v1 (#2785, CDF-B)

## Alcance

Cuarta unidad de actividades CDF, apilada sobre
[listado y catálogo](2026-11-13-2785-react-cdf-actividades-lista-catalogo.md):
formulario de alta (`/centrodefamilia/centros/<centro>/actividades/nueva/`) y de
edición (`/centrodefamilia/centros/actividades/<pk>/editar/`) de una actividad del
centro. Contrato: «Actividades» de
[centros y actividades](../../../plans/2026-T4/2026-10-28-2785-cdf-centros-actividades-m2.md).
Decisión de acceso:
[D1](../../decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).

No cambian `ActividadCentroCreateView`, `ActividadCentroUpdateView`,
`ActividadCentroForm`, las plantillas, `centro_familia_categoria.js` ni la regla de
acceso. No activa React en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_actividad_form.py` (API web); rutas en
  `web_api_actividades_urls.py` y entradas en `web_preview_actividades.py`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfActividadForm.tsx` (formulario, selectores
  de hora y de actividad dependiente); `cdfCrispy.tsx` pasa a exportar el marco de
  campo (`FieldFrame`) que comparten los formularios CDF. Registro en
  `routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_actividad_form.py`,
  `test_web_cdf_preview_actividades.py` (entradas nuevas) y
  `src/frontends/apps/sisoc/src/routes/cdfActividadForm.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET/POST /api/web/cdf/centros/<centro>/actividades/nueva/` | `dispatch` nativo (centro inexistente 404), campos del formulario y `post()` nativo: guarda y responde la redirección a la ficha del centro como JSON (`url`, `message` «La actividad fue creada correctamente.», `level`); el formulario inválido responde 400 con valores y errores |
| `GET/POST /api/web/cdf/actividades/<pk>/editar/` | Valores actuales (categoría, actividad, días, sexos, horas, precio y estado) y `post()` nativo con «La actividad fue actualizada correctamente.» |

Se conserva la política vigente: sesión y requisitos web (G1), `view_centro` y solo
login en las vistas nativas. Reglas del formulario sin cambios: la actividad se
limita a la categoría elegida, las dos horas son obligatorias, un centro FARO
oculta el precio y rechaza uno distinto de cero («Un centro de tipo FARO no debe
tener un precio asignado.»). El mensaje queda encolado y lo muestra la ficha del
centro a la que se vuelve.

Pantalla React: la tarjeta no tiene título ni botón «Cancelar» porque la vista no
los pone en el contexto, igual que hoy. «Categoría» recarga las actividades desde
`/ajax/actividades/` como `centro_familia_categoria.js` («Cargando...» y luego
«Seleccione una actividad»). «Días» y «Actividad dirigida a...» usan el Select2
compartido con el aspecto de `custom.js`. Las dos horas usan el mismo plugin
flatpickr que la página nativa (CDN de jsDelivr, 24 h, `H:i`, sin calendario),
iniciado y destruido con el ciclo de vida del componente. Un resultado sin
confirmar muestra «No se pudo confirmar el resultado. Verificá el estado antes de
reintentar.» y no reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 12 pruebas nuevas en rojo (rutas inexistentes) y luego en verde:
  campos en orden, precio oculto en FARO, alta y edición persistidas con días,
  sexos y horas, mensajes literales, rechazos sin cambios, actividad de otra
  categoría, regla FARO con precio cero, 404, acceso y CSRF.
- Frontend: Vitest de la ruta en verde (10, con el plugin de hora simulado),
  `tsc`, ESLint y build de Vite.
- Visual (regla S13): alta, alta de FARO, cambio de categoría, edición, edición de
  FARO, selector de días abierto y edición con error del servidor, en 1440x900 y
  390x844: diferencia perceptual 0 % y desvío máximo de 0 px; orden de Tab igual.
- G1 de punta a punta (core y runtime CDF): anónimo 401, sin permiso 403, sin CSRF
  403, cabecera falsificada ignorada, formulario actual, rechazo 400 sin cambios y
  edición persistida.

## Limitaciones

- El plugin flatpickr viene del CDN y el entorno de verificación no tiene red: el
  navegador de la prueba visual no lo carga ni en la página nativa ni en la de
  React, así que el desplegable de hora no se pudo comparar visualmente. Queda
  probado con el plugin simulado (opciones, destino y destrucción) y debe
  mirarse a mano con red.
- Mismas diferencias del marco compartido que las unidades anteriores (enlace del
  logo y menú móvil).
