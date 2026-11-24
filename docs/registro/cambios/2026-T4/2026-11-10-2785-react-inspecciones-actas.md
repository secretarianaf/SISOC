# Cambio: listado de actas de Inspecciones en React sobre G1 v1 (#2785, IN04.01)

## Alcance

Primera pantalla de un vertical remoto que usa el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la
pestaña Actas del panel de Inspecciones escolares (`/inspecciones/actas/`), del
[contrato de Inspecciones](../../../plans/2026-T4/2026-10-28-2785-inspecciones-circuitos-m2.md)
(familia IN04). El catálogo deja la partición de rutas de cada entrega para
cuando se define el contrato. IN04.01 («Consulta y ficha de actas») se parte
así: esta unidad es el listado con sus filtros y paginación. La ficha
(`/inspecciones/actas/<numero>/`), los archivos y las acciones de anular o
marcar prueba quedan para unidades siguientes.

No cambia las vistas, formularios, servicios, plantillas ni el JavaScript
nativos, ni la API de la PWA (`/api/inspecciones/`). No activa React en
producción.

Archivos:

- `src/backends/inspecciones/inspecciones/web_api.py` y
  `src/backends/inspecciones/inspecciones/web_api_urls.py`: API web, incluida
  desde `src/backends/inspecciones/inspecciones_runtime/urls.py`.
- `src/backends/config/backends.json`: prefijo `api/web/inspecciones/` del
  backend `inspecciones`. `src/backends/config/url_registry.json` se regeneró
  con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las dos rutas nuevas quedan
  fuera del atajo HEAD de admindocs, como las demás `/api/web/`.
- `src/backends/inspecciones/inspecciones/web_preview.py`: entrada React sin
  montar (`actas_preview_patterns`), solo para un URLconf local.
- `src/frontends/apps/sisoc/src/routes/`: `inspeccionesActas.tsx` (ruta),
  `ActasPage.tsx` (pantalla), `ClaroFrame.tsx` (layout claro) e
  `InspSelect2.tsx` (selector remoto J2).
- Pruebas: `src/backends/inspecciones/tests/test_web_actas.py`,
  `src/backends/inspecciones/tests/test_web_preview.py` y
  `src/frontends/apps/sisoc/src/routes/inspeccionesActas.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/inspecciones/actas/` | Mismos filtros (`fecha`, `inspector`, `provincia`, `estado`, `numero`), orden, 25 por página y 404 de página inválida que la vista nativa. Devuelve el marco del layout claro (breadcrumb, nombre, rol, iniciales), las pestañas, los valores de filtro tal como llegaron, las opciones, las filas y la paginación |
| `GET /api/web/inspecciones/inspectores/` | Búsqueda del selector de inspector: mismo servicio, mínimo de 3 letras, tope de 20 y alcance `alcance=programa` que `/inspecciones/ajax/inspectores/`. Solo GET |

La API reutiliza `ActasView` del HTML para armar el contexto (no hay una
segunda implementación de filtros). Solo lectura: no escribe en la base.
Responde JSON `private, no-store` con `Vary: Cookie`; otros métodos, 405.

Acceso, en este orden:

1. Composición dividida: el core exige sesión (401 JSON) y evalúa los requisitos
   web (403 JSON con `state` y `required_action_url`), firma la solicitud y la
   reenvía. El runtime solo atiende lo que `WebGateMiddleware` verificó: sin
   constancia, alterada, vencida (más de 60 s), de otro usuario, otro destino o
   otra audiencia responde 403 sin llegar a la vista.
2. Monolito: `WebGatePermission` evalúa la misma política localmente e ignora
   cualquier header recibido.
3. Después, la regla nativa sin cambios: `puede_gestionar` (permiso
   `gestionar_inspecciones`, coordinación o superusuario). Sin ella, 403.

Entrada React: en `/inspecciones/actas/` corre primero el despacho de
`ActasView` (anónimo al login, sin permiso 403 nativo, página inválida 404
nativo) y recién después devuelve el `index.html` congelado. Los assets se
sirven desde `/inspecciones/react/assets/` (prefijo propio del backend), con
caché inmutable y `nosniff`.

Pantalla React: toma el menú lateral, el usuario y el pie de
`/api/web/session/` (core) y los datos de la API del vertical. Reproduce el
layout claro (`includes/base_claro.html`): misma lista y orden de hojas de
estilo, tema claro, clases del `body`, barra lateral oscura con logo y cabecera
blanca. No usa el marco oscuro de negocio ni MUI. Los filtros siguen siendo un
formulario GET nativo y se envían al cambiar, como `panel.js`, también al vaciar
el buscador. El selector de inspector reproduce el marcado de Select2 4.1, sus
textos («Escribí al menos 3 letras», «Buscando…», «Sin resultados»), la espera
de 250 ms, la cruz para limpiar y la opción en dos renglones, y muestra el texto
de la respuesta como texto. Si la búsqueda falla o devuelve otra forma, el
selector muestra «No se pudieron cargar los resultados» en lugar de «Sin
resultados». Ese estado es nuevo: Select2 no informa el error.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (15 de 16 y la entrada sin módulo) y luego en
  verde. Suite de Inspecciones, `test_web_gate`, `test_backend_proxy`, pruebas
  de registro de backends y vistas previas de identidad, `black`, `pylint` 10/10
  y `makemigrations --check` sin cambios.
- Frontend: prueba de ruta en rojo (10 de 10) y luego en verde; Vitest del
  workspace, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 7 estados (listado, página 2, sin
  resultados, anuladas, inspector elegido, provincia y fecha, número) en
  1440x900 y 390x844: misma estructura, textos, controles y estilos, desvío
  geométrico máximo de 0,03 px, diferencia perceptual máxima de 0,001 % y el
  mismo orden de Tab. Mismo recorrido de selector, filtros y «Limpiar filtros»
  con las mismas URLs. Anónimo, sin permiso y página inválida responden igual.
- G1 de punta a punta: core y runtime de Inspecciones en dos contenedores
  gunicorn sobre una red interna. La pantalla carga por core → compuerta →
  runtime. Anónimo 401, sin permiso 403 y requisito pendiente 403 con `state`.
  El header que manda el cliente se descarta. Contra el runtime directo, una
  constancia faltante, falsa, alterada, de otro destino, audiencia o usuario,
  vencida (61 s) o futura responde 403, y una de 58 s responde 200.

## Limitaciones

- Roboto (Google Fonts) quedó bloqueada sin red en los dos lados, así que la
  comparación usó la fuente de reemplazo.
- El desplegable abierto del selector se comparó por recorrido y tamaño de
  captura, no con la matriz completa del manifiesto J2.
- La envoltura de OverlayScrollbars de la barra lateral se reproduce con valores
  fijos (barra de 16 px). No se probó con otras barras de desplazamiento.
- El menú móvil abierto está fuera de la comparación, por la excepción vigente.
- Ficha, archivos, anulación y marca de prueba quedan pendientes (resto de
  IN04.01, IN04.02 e IN04.03).
