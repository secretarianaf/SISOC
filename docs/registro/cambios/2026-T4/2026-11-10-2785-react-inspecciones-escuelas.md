# Cambio: pestaña Escuelas de Inspecciones en React sobre G1 v1 (#2785, IN05)

## Alcance

Familia IN05 del
[contrato de Inspecciones](../../../plans/2026-T4/2026-10-28-2785-inspecciones-circuitos-m2.md):
el panel de escuelas (`/inspecciones/`) con totales, buscador, filtros de
provincia y localidad, chip «A revisar» y paginación, y el formulario de escuela
en el modal y como página (`/inspecciones/escuelas/nueva/`,
`/inspecciones/escuelas/<pk>/editar/`), con «Guardar y cargar otra», retorno y
apertura automática con `?editar=`. Sigue el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y el patrón
de la [ficha del acta](2026-11-10-2785-react-inspecciones-acta-detalle.md).

No cambia vistas, formularios, servicios, plantillas ni el JavaScript nativos.
No activa React en producción. La importación (IN01) no se migra: el botón
«Importar Excel/CSV» abre el mismo modal y envía el mismo formulario multipart a
la URL nativa.

Archivos:

- `src/backends/inspecciones/inspecciones/web_api_escuelas.py`: panel,
  formulario y búsqueda de localidades; rutas en
  `src/backends/inspecciones/inspecciones/web_api_urls.py`.
- `src/backends/inspecciones/inspecciones/web_preview.py`: entradas sin montar
  `EscuelasEntry`, `EscuelaNuevaEntry` y `EscuelaEditarEntry` (el POST de página
  sigue siendo la vista nativa).
- `src/backends/config/middlewares/admindocs.py` (un patrón) y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `inspeccionesEscuelas.tsx` (ruta),
  `inspeccionesEscuelasPage.tsx` (panel, modales y página),
  `inspeccionesEscuelaForm.tsx` (formulario), `inspeccionesEscuelasApi.ts`
  (contrato y POST), `inspeccionesModal.ts` (modal de Bootstrap 5.3) e
  `inspeccionesEscuelasNavigation.ts`. `InspSelect2.tsx` suma opciones que el
  listado de actas no usa: deshabilitado, vaciado dependiente, ancho y
  `dropdownParent` del modal, clases y `required` del `select` original.
- Pruebas: `src/backends/inspecciones/tests/test_web_escuelas.py` y
  `src/frontends/apps/sisoc/src/routes/inspeccionesEscuelas.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/inspecciones/escuelas/` | Corre `EscuelasView`: mismos filtros (`q`, `provincia`, `localidad`, `a_revisar`), orden, 25 por página, 404 de página inválida, totales del panel, contador y enlace del chip, `?editar=` y mensajes pendientes |
| `GET /api/web/inspecciones/escuelas/nueva/` y `.../<pk>/editar/` | El formulario como datos: valores, errores, localidad inicial, aviso «Datos a revisar» y enlace «Abrir para editar» de un Cueanexo repetido. Con `X-Requested-With` (modal) no consume mensajes, como el fragmento nativo |
| `POST` de esas rutas | Corre el `post()` nativo. Modal (`X-Requested-With`): `{"ok", "mensaje", "otra"}` y el mensaje queda en cola salvo con «otra». Página: el 302 nativo como `{"ok": true, "redirect": ...}` (`/inspecciones/?q=<cueanexo>` o una alta vacía con «otra»). Inválido: el formulario con sus errores (400) en lugar de HTML |
| `GET /api/web/inspecciones/localidades/` | Mismo servicio, alcance por `provincia` y tope que `/inspecciones/ajax/localidades/` |

Mensajes y validaciones son los nativos («Se agregó la escuela … (…).», «Se
guardaron los cambios de … (…).», Cueanexo de 9 dígitos, «Ya existe: …», mail
múltiple, C. P., «La localidad no es de esa provincia.»). Acceso: 401 sin
sesión, 403 por requisitos web o sin `puede_gestionar`, CSRF en los POST, edición
inexistente 404. Las lecturas no escriben.

Pantalla React: reproduce `panel.js`. La provincia vacía y deshabilita la
localidad antes del envío automático; el modal muestra «Cargando…», enfoca el
primer control, envía una vez, repinta los errores, con «otra» recarga el alta
con el aviso verde y si no recarga la página (el toast sale de la cola). El modal
sigue a Bootstrap 5.3: trampa de foco por `focusin`, Escape dentro del diálogo,
clic en el fondo y, en el de importar, foco de vuelta al botón. En la página, un
envío inválido vuelve arriba y deja el foco al inicio del documento, como una
página nueva.

Estado nuevo: si un POST no confirma el resultado, se muestra «No se pudo
confirmar el resultado.» con un enlace al panel y no se reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (20 de 21) y luego en verde (21). Suite de
  Inspecciones, `test_web_gate`, `test_backend_proxy`, `test_servicios_backends`,
  `-k registro_de_urls_al_dia`, `pytest --collect-only src/backends` sin errores,
  `black`, `pylint` 10/10 y `makemigrations --check`.
- Frontend: prueba en rojo (módulo inexistente) y en verde (8); Vitest del
  proyecto `sisoc`, `tsc`, ESLint sin avisos y build de Vite.
- Visual (regla S13) en 1440x900 y 390x844: panel, provincia, localidad,
  búsqueda, «A revisar», sin resultados, desplegable de localidad, modal de
  importar, modal de alta, edición, edición con datos a revisar, errores, alta
  con «otra», guardado con toast y la página de alta, edición, error y guardado.
  36 de 38 casos pasan con diferencia perceptual de 0,000 % (0,131 % como
  máximo en los desplegables móviles), desvío geométrico de 0,03 px como máximo
  y el mismo orden de Tab. Los dos restantes son los desplegables abiertos en
  escritorio (0,054 % y 0,102 %), por la diferencia de foco descrita en
  Limitaciones. Guardas iguales (anónimo, sin permiso, inspector, edición
  inexistente, página inválida). Los 14 casos del listado de actas y su
  recorrido del selector se repitieron con el `InspSelect2` ampliado y siguen
  iguales.
- G1 de punta a punta: core y runtime en dos contenedores gunicorn. El panel
  carga por core → compuerta → runtime; alta con «otra», Cueanexo repetido con
  «Abrir para editar» y alta de página con retorno a `?q=` y toast. Anónimo 401,
  sin permiso 403, requisito pendiente 403 con `state`, header del cliente
  descartado, POST sin CSRF 403 y edición inexistente 404.

## Limitaciones

- Desplegable abierto: el `InspSelect2` del piloto pone el foco en el buscador
  del desplegable y el Select2 nativo lo deja en el selector. Da 0,05–0,13 % de
  píxeles y otro orden de Tab desde ese foco. Viene del listado de actas y no se
  cambió para no alterar el piloto.
- Roboto quedó bloqueada sin red en los dos lados; el menú móvil abierto está
  fuera de la comparación.
- No se probaron archivos reales de importación (IN01).
