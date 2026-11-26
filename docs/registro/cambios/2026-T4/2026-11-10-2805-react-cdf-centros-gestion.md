# Cambio: alta, edición y baja de centros CDF en React sobre G1 v1 (#2805, CDF04.02)

## Alcance

Segunda unidad de centros CDF, apilada sobre la
[consulta de centros](2026-11-10-2805-react-cdf-centros-consulta.md): formulario
de alta (`/centrodefamilia/centros/nuevo/`, también con `?faro=`), edición
(`/centrodefamilia/centros/<pk>/editar/`) y confirmación de baja
(`/centrodefamilia/centros/<pk>/eliminar/`). Contrato: CDF04.02 de
[CDF03/CDF04](../../../plans/2026-T4/2026-11-10-2785-cdf03-cdf04-contratos.md),
con la baja corregida: baja lógica en cascada, no `activo=False` solamente.

No cambian las vistas, el formulario `CentroForm`, las plantillas ni el
JavaScript nativos (`centro_form.js` también lo usa VAT). No activa React en
producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_gestion.py`: API web; rutas en
  `src/backends/cdf/centrodefamilia/web_api_urls.py`.
- `src/backends/cdf/centrodefamilia/web_preview.py`: entradas de alta, edición y
  baja.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfCentroForm.tsx` (rutas, formulario y
  confirmación).
- Pruebas: `src/backends/cdf/tests/test_web_cdf_gestion.py`,
  `src/backends/cdf/tests/test_web_cdf_preview.py` y
  `src/frontends/apps/sisoc/src/routes/cdfCentroForm.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/centros/options/?faro=` | Formulario sin datos: campos en orden, opciones, valores iniciales y `locked` (`tipo` y `faro_asociado` con `?faro=`) |
| `POST /api/web/cdf/centros/crear/[?faro=]` | `CentroCreateView.post`: 201 `{id, message: "Centro creado exitosamente.", redirect: "list", url}`; 400 con valores, `errors` y `non_field_errors` |
| `GET/POST /api/web/cdf/centros/<pk>/editar/` | Regla nativa de `dispatch` antes de leer el cuerpo; 200 `{id, message: "Centro actualizado correctamente.", redirect: "detail", url}`; 400; 403; 404 |
| `GET/POST /api/web/cdf/centros/<pk>/eliminar/` | Vista previa de la cascada; baja con `instance.delete(user, cascade=True)`: 200 `{message: "Centro dado de baja correctamente.", redirect: "list", url}`; 403; 404 si ya está dado de baja |

Cada endpoint corre la vista nativa, así que el mensaje de éxito queda en la
sesión como hoy: React vuelve a la URL nativa (listado o ficha) y el mensaje se
muestra una vez. Un 400 vuelve a dibujar el formulario con los errores; cualquier
otro resultado muestra «No se pudo confirmar el resultado. Verificá el estado
antes de reintentar.» y no reintenta.

Acceso sin cambios (paridad D1): el alta solo pide `view_centro` (el botón lo
limita `can_add`); edición y baja piden referente por FK, superusuario o SSE, y un
`AccesoCDF` activo no alcanza. Con `?faro=` el servidor fuerza «adherido» y el
FARO aunque el cuerpo diga otra cosa.

Pantalla React: mismos campos de crispy (clases, asteriscos, errores), mismas
reglas de visibilidad por tipo de `centro_form.js` (incluido que «Sitio web» y
«Link redes» quedan ocultos, porque el script busca otros ids), recarga de
municipios y localidades con los endpoints del core y el editor de mapa
`map_pin_editor.html` manejado por `mapPinEditor.js`. «Cancelar» conserva el
`href` vacío del formulario nativo. La baja reproduce `delete_confirm.html` con la
tabla de cascada.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la unidad anterior (13 de 14 y la
  entrada sin vistas nuevas) y luego en verde. Suite CDF, pruebas del core de
  G1 y registro, colección completa, `black`, `pylint` y `makemigrations --check`.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (7);
  Vitest del proyecto sisoc, `tsc`, ESLint y build de Vite.
- Visual (regla S13), 6 estados (alta, alta con FARO, edición de adherido y de
  FARO, baja de adherido y de FARO) más listado y ficha, en 1440x900 y 390x844:
  diferencia perceptual 0 % y desvío máximo de 0,02 px. Anónimo, sin permiso,
  `AccesoCDF` sin FK e inexistente responden igual (403/404).
- G1 de punta a punta (core y runtime CDF en dos contenedores): alta, edición
  inválida y válida y baja desde React, con el mensaje nativo en cada retorno.
  POST anónimo 401, sin CSRF 403, sin permiso 403.

## Limitaciones

- Mismas diferencias del marco compartido que la consulta (logo y menú móvil).
- Leaflet quedó bloqueado sin red en los dos lados: no se probó el mapa real ni
  el geocodificador.
- El formulario inválido se comparó por recorrido (G1), no con capturas; el
  arnés visual solo hace GET.
- La foto actual en edición usa un marcado aproximado de `ClearableFileInput`
  (no había fotos en los datos sintéticos).
