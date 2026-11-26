# Cambio: pestaña Asignaciones de Inspecciones en React sobre G1 v1 (#2785, IN02)

## Alcance

Familia IN02 del
[contrato de Inspecciones](../../../plans/2026-T4/2026-10-28-2785-inspecciones-circuitos-m2.md)
(sección «Asignaciones IN02»): la jornada (`/inspecciones/asignaciones/`) con
sus totales, filtros y paginación, el alta de asignación en el modal y como
página (`/inspecciones/asignaciones/nueva/`), «Asignar y cargar otra», el aviso
de otra visita y «Quitar». Sigue el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y el patrón
de la [pestaña Escuelas](2026-11-10-2785-react-inspecciones-escuelas.md). Los
mensajes y los filtros se migran juntos, como pide el catálogo.

No cambia vistas, formularios, servicios, plantillas ni el JavaScript nativos.
No activa React en producción. La importación (IN01) no se migra: el botón
«Importar Excel/CSV» abre el mismo modal y envía el mismo formulario multipart a
la URL nativa.

Archivos:

- `src/backends/inspecciones/inspecciones/web_api_asignaciones.py`: jornada,
  formulario, baja, aviso y búsqueda de escuelas; rutas en
  `src/backends/inspecciones/inspecciones/web_api_urls.py`.
- `src/backends/inspecciones/inspecciones/web_preview.py`: entradas sin montar
  `AsignacionesEntry` y `AsignacionNuevaEntry` (el POST de página y la baja siguen
  siendo las vistas nativas).
- `src/backends/config/middlewares/admindocs.py` (un patrón) y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `inspeccionesAsignaciones.tsx` (ruta),
  `inspeccionesAsignacionesPage.tsx` (jornada, modales y página),
  `inspeccionesAsignacionForm.tsx` (formulario),
  `inspeccionesAsignacionesApi.ts` (contrato, POST de alta y de baja, aviso) e
  `inspeccionesScreen.ts` (carga de sesión y pantalla, ahora compartida con
  Escuelas, que exporta además `InspModal`, `Pagination`, `Screen` e
  `ImportModal` con título y ayuda propios). `InspSelect2.tsx` suma
  `data-insp-verifica` en el `select` oculto.
- Pruebas: `src/backends/inspecciones/tests/test_web_asignaciones.py` y
  `src/frontends/apps/sisoc/src/routes/inspeccionesAsignaciones.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/inspecciones/asignaciones/` | Corre `AsignacionesView`: jornada (`fecha`, hoy por omisión), filtros (`inspector`, `escuela`, `provincia`, `estado`, `estado_acta`; un valor inválido se ignora), orden, 25 por página y enlaces de día anterior, siguiente y hoy. Los totales de la jornada son los del servicio nativo: ignoran los filtros de estado y de acta aunque las filas sí los apliquen, así que la pantalla no los deriva de la página |
| `GET /api/web/inspecciones/asignaciones/nueva/` | El formulario como datos: valores (la jornada viene de `?fecha=` u hoy), errores y las opciones ya elegidas del inspector y la escuela. Con `X-Requested-With` (modal) no consume mensajes |
| `POST` de esa ruta | Corre el `post()` nativo. Modal: `{"ok", "mensaje", "otra"}`; el mensaje queda en cola salvo con «otra». Página: el 302 nativo como `{"ok": true, "redirect": ...}` (`/inspecciones/asignaciones/?fecha=` o el alta vacía con la misma fecha). Inválido: el formulario con sus errores (400) |
| `POST /api/web/inspecciones/asignaciones/<pk>/quitar/` | Corre `AsignacionQuitarView.post`: baja lógica y retorno a la jornada de la asignación; con acta (aun anulada) rechaza con el mensaje nativo y no escribe. Inexistente o ya quitada, 404 |
| `GET /api/web/inspecciones/asignaciones/verificar/` | El aviso «otra visita» del modal: mismo formulario y servicio que `/inspecciones/ajax/asignaciones/verificar/` |
| `GET /api/web/inspecciones/escuelas/buscar/` | Búsqueda del selector de escuela: mismo servicio y tope (3 letras, 20) que `/inspecciones/ajax/escuelas/` |

Reglas conservadas: fecha, inspector y escuela requeridos; el inspector debe ser
del programa con rol Inspector; la misma escuela con otro inspector es una visita
adicional permitida con el aviso «También la tiene asignada … (otra visita).»;
la misma escuela, inspector y jornada rechaza «Esa escuela ya está asignada a ese
inspector en esa jornada.», y una asignación quitada se restaura. Los mensajes
(«Se asignó … para el dd/mm/aaaa.», «Se quitó la asignación de … a ….») son los
nativos. A diferencia de las otras pestañas, la jornada nativa usa `get_page`:
una página inexistente muestra la última, no un 404.

Acceso: 401 sin sesión, 403 por requisitos web o sin `puede_gestionar`, CSRF en
los POST. Las lecturas no escriben y los métodos no permitidos responden 405.

Pantalla React: reproduce `panel.js`. Los filtros son un formulario GET nativo
con envío automático al cambiar. El modal sigue a Bootstrap 5.3 (foco, trampa,
Escape, fondo). El aviso de otra visita se pide al cargar y al cambiar la
jornada, el inspector o la escuela, con el texto nativo; un fallo de esa consulta
lo deja como estaba. «Quitar» pide `window.confirm` con el texto nativo, envía
una vez y vuelve a la jornada con la recarga completa (el toast sale de la cola).
Con «otra» el siguiente alta se carga con la fecha que se acaba de guardar.

Estado nuevo: si un POST no confirma el resultado (alta o baja) se muestra «No
se pudo confirmar el resultado.» con un enlace a las asignaciones y no se
reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (28 de 30) y luego en verde (30). Suite de
  Inspecciones (306 + 4 omitidas, previas), `test_web_gate`,
  `test_backend_proxy`, `test_servicios_backends`, `black`, `pylint` 10/10 y
  `makemigrations --check`.
- Frontend: Vitest del proyecto `sisoc` (60 archivos, 619 pruebas), `tsc`,
  ESLint sin avisos nuevos y build de Vite.
- Visual (regla S13) en 1440x900 y 390x844: jornada, jornada filtrada, modal de
  alta, modal con errores, página de alta y página con errores. 12 de 12 casos
  con diferencia perceptual de 0,000 %, desvío geométrico de 0,06 px como máximo
  y el mismo orden de Tab. Guardas iguales (anónimo y sin permiso, en la jornada
  y en el alta).
- G1 de punta a punta: core y runtime en dos contenedores gunicorn. Anónimo 401,
  sin permiso 403, requisito pendiente 403 con `state`, header del cliente
  descartado, POST sin CSRF 403, alta feliz, duplicado 400 y baja inexistente 404.

## Limitaciones

- Roboto quedó bloqueada sin red en los dos lados; el menú móvil abierto y la
  página 2 están fuera de la comparación.
- No se probó el desplegable abierto del selector (ya cubierto por Escuelas) ni
  archivos reales de importación (IN01).
