# Cambio: catálogo de actividades PNUD en React sobre G1 v1 (#2785, CO04.02)

## Alcance

Catálogo global de actividades PNUD
(`/comedores/configuracion/actividades-pnud/`) del contrato CO04.02 (plan de
colaboradores, actividades y catálogos de Comedores, todavía sin versionar en
la rama): listado con búsqueda y filtro de estado, alta, edición y baja lógica.
Sigue el [ABM de montos](2026-11-10-2785-react-montos.md) sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).

No cambia la vista, el formulario, el modelo, las plantillas, las URLs nativas
ni las actividades de los espacios. No borra registros. No activa React en
producción.

Archivos:

- `src/backends/comedores/comedores/web_api_pnud.py` y
  `src/backends/comedores/comedores/web_api_pnud_urls.py`: API web, incluida
  en `src/backends/comedores/comedores_runtime/web_api_urls.py`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/backends/comedores/comedores/web_preview_catalogos.py`: entradas sin
  montar de las cuatro URLs.
- `src/frontends/apps/sisoc/src/routes/actividadesPnud.tsx` (ruta y
  pantallas).
- Pruebas: `src/backends/comedores/comedores/tests/test_web_pnud.py`,
  `src/backends/comedores/comedores/tests/test_web_preview_catalogos.py` y
  `src/frontends/apps/sisoc/src/routes/actividadesPnud.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/actividades-pnud/` | Listado nativo: 50 por página, orden categoría, actividad e id; `estado` activa por defecto, `inactiva`, cualquier otro valor sin filtro; `q` por categoría o actividad |
| `GET/POST /api/web/comedores/actividades-pnud/crear/` | `ActividadPnudForm` con `categoria_modo` existente o nueva |
| `GET/POST /api/web/comedores/actividades-pnud/<pk>/editar/` | Edición con la categoría actual elegida |
| `GET/POST /api/web/comedores/actividades-pnud/<pk>/baja/` | Confirmación; el POST marca `activo=False` y actualiza `fecha_actualizacion`, o avisa que ya estaba inactiva |

Cada endpoint ejecuta la vista nativa de `views/actividades_pnud.py`. Mensajes
nativos: «Actividad PNUD creada correctamente.», «Actividad PNUD actualizada
correctamente.», «Actividad PNUD dada de baja correctamente.» y, como aviso,
«La actividad PNUD ya se encontraba inactiva.». Un formulario inválido devuelve
400 con los errores de Django tal cual. Las escrituras exigen el token CSRF.

Acceso: después de G1, la regla de `ActividadPnudPermissionMixin` sin cambios.
Leer: `auth.role_admin`, `pwa.view_catalogoactividadpwa` o
`pwa.manage_catalogoactividadpwa`. Escribir: `auth.role_admin` o
`pwa.manage_catalogoactividadpwa`. Quien solo puede ver no tiene «Agregar» y ve
«-» en acciones.

Pantalla React: mismo marcado que la plantilla y el componente `search_bar`
(buscador, «Resetear», «Agregar»), el filtro de estado enganchado al formulario
de búsqueda y los botones «Usar existente» y «Crear nueva», que hacen lo mismo
que el script de la plantilla: muestran un campo y vacían el otro. Igual que la
plantilla, el error «La categoria es obligatoria.» no se muestra (el formulario
lo asigna al campo del modo, que la plantilla no imprime), aunque el campo queda
con `aria-invalid`. El listado sin filas no muestra «Se encontraron 0
resultados», como el componente de paginación.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre el árbol de montos (17 de 22) y luego en
  verde (22). Suites de Comedores, menú, navegación, botón volver, runtime,
  `test_web_gate`, `test_backend_proxy`, `test_servicios_backends` (236),
  registro de URLs, `black`, `pylint` 10/10 y `makemigrations --check`.
- Frontend: prueba de ruta en rojo (8 de 8) y luego en verde; Vitest del
  workspace (421), `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 8 estados (listado, página 2,
  todas con búsqueda, inactivas, sin resultados, alta, edición, baja) y el
  listado de solo lectura, en 1440x900 y 390x844: contenido de la página con el
  mismo texto, controles, estilos y orden de Tab, desvío máximo de 0,02 px y
  diferencia de píxeles máxima de 0,024 %. El mismo recorrido (cambio de modo,
  alta inválida, alta con categoría nueva y existente, edición, baja, segunda
  baja y vista de solo lectura) da los mismos valores, errores, `aria-invalid` y
  mensajes. Anónimo, sin permiso, solo lectura en alta o baja, página inválida y
  objeto inexistente responden igual.
- G1 de punta a punta en dos contenedores gunicorn: listado, alta y baja por
  core → compuerta → runtime; solo lectura recibe 403 en el formulario y en su
  entrada; requisito pendiente 403 con `state`.

## Limitaciones

- Las mismas diferencias del marco compartido que el ABM de montos (enlace
  «Legajos» del menú resaltado en la página nativa, estructura del menú móvil,
  nombre accesible del logo).
- El selector de actividad de los espacios sigue en Django; esta unidad no lo
  toca.
