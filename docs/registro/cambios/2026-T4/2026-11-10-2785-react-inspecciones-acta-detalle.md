# Cambio: ficha del acta de Inspecciones en React sobre G1 v1 (#2785, IN04)

## Alcance

Segunda unidad de la familia IN04 del
[contrato de Inspecciones](../../../plans/2026-T4/2026-10-28-2785-inspecciones-circuitos-m2.md),
después del [listado de actas](2026-11-10-2785-react-inspecciones-actas.md):
la ficha del acta (`/inspecciones/actas/<numero>/`), sus archivos privados y las
acciones «Anular acta» y «Marcar como prueba» / «Quitar marca de prueba». Sigue
el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).

No cambia las vistas, servicios, plantillas ni el JavaScript nativos, ni la API
de la PWA (`/api/inspecciones/`). No activa React en producción. No agrega un
botón de envío de notificación: la notificación en papel sigue siendo solo
consulta, como en el HTML (el productor es la PWA).

Archivos:

- `src/backends/inspecciones/inspecciones/web_api_acta.py`: ficha y acciones;
  rutas en `src/backends/inspecciones/inspecciones/web_api_urls.py`.
- `src/backends/inspecciones/inspecciones/web_preview.py`: entrada React sin
  montar de la ficha (`ActaDetalleEntry`, dentro de `actas_preview_patterns`).
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs. `src/backends/config/url_registry.json` se
  regeneró con `generar_registro_urls`.
- `src/frontends/apps/sisoc/src/routes/`: `inspeccionesActaDetalle.tsx` (ruta),
  `inspeccionesActaDetallePage.tsx` (pantalla), `inspeccionesActaNavigation.ts`
  (navegación después de una acción) e `inspeccionesToasts.tsx` (mensajes como
  toastr en el layout claro).
- Pruebas: `src/backends/inspecciones/tests/test_web_acta_detalle.py` y
  `src/frontends/apps/sisoc/src/routes/inspeccionesActaDetalle.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/inspecciones/actas/<numero>/` | Corre `ActaDetalleView` (mismo 404, breadcrumb e iniciales) y devuelve cada texto ya impreso como en `acta_detalle.html`: fechas, guiones de dato faltante, aviso de anulación, insignias, respuestas F00–F16, evidencia, notificaciones, institución, geolocalización, firma e historial. También devuelve y consume los mensajes pendientes |
| `POST /api/web/inspecciones/actas/<numero>/anular/` | Corre el `post()` de `AnularActaView`: mismo servicio, mismo `next` validado y mismos mensajes («Acta … anulada.», «Indicá el motivo de la anulación (al menos 10 caracteres).», «El acta … ya está anulada.»). Responde `{"ok": true, "redirect": ...}` con el destino del 302 nativo |
| `POST /api/web/inspecciones/actas/<numero>/prueba/` | Corre el `post()` de `MarcarPruebaActaView`: «Acta … marcada como de prueba.», «Acta … desmarcada como de prueba.», «Valor de prueba inválido.» y el rechazo de un acta anulada. Sin cambio de valor no registra evento |

Acceso: el core exige sesión (401) y los requisitos web (403 con `state`) y
firma la solicitud; el runtime solo atiende lo que verificó `WebGateMiddleware`.
Después rige la regla nativa `puede_gestionar` (403). Un acta inexistente da
404. Las acciones exigen POST (405) y CSRF (403). Las lecturas no escriben en la
base.

Los archivos siguen siendo las URLs nativas (`.../pdf/`, `.../imagenes/<uuid>/`,
`.../notificaciones/<uuid>/`) con su propia guarda, `private, no-store` y
`nosniff`; React solo arma los enlaces y las miniaturas.

Entrada React: en `/inspecciones/actas/<numero>/` corre primero el despacho de
`ActaDetalleView` (anónimo al login, sin permiso 403, acta inexistente 404) y
recién después devuelve el `index.html` congelado.

Pantalla React: layout claro (`routes/ClaroFrame.tsx`). El modal de anulación
reproduce el de Bootstrap 5: foco en el diálogo, Tab circular, Escape, clic en
el fondo y «Cancelar» cierran, el foco vuelve a «Anular acta», `modal-open` y el
relleno de la barra de desplazamiento en el `body`. El motivo conserva
`minlength="10"` y `required`. Un POST confirmado navega al destino como el 302
nativo; la página siguiente muestra los mensajes como toastr (abajo a la
derecha, último primero, 5 s, como último hijo del `body`).

Estado nuevo: si el POST no confirma el resultado (red o respuesta inesperada),
la pantalla muestra «No se pudo confirmar el resultado.» con un enlace al acta y
no reintenta. Un destino que no sea una ruta interna no se sigue.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (18 de 19) y luego en verde. Suite de
  Inspecciones, `test_web_gate`, `test_backend_proxy`,
  `test_servicios_backends`, `-k registro_de_urls_al_dia`, `pytest
  --collect-only src/backends` sin errores, `black`, `pylint` 10/10 y
  `makemigrations --check` sin cambios.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (8);
  Vitest del proyecto `sisoc`, `tsc`, ESLint sin avisos y build de Vite.
- Visual (regla S13), nativo contra React, en 1440x900 y 390x844: ficha
  completa, carga manual con resultado parcial, anulada, de prueba, sin escuela
  de catálogo, modal abierto, después de marcar como prueba, después de anular y
  con un motivo que pasa `minlength` pero queda corto sin espacios. Los 18 casos
  pasan: misma estructura, textos, controles y estilos, desvío geométrico
  máximo de 0,02 px, diferencia perceptual 0,000 % y el mismo orden de Tab. El
  Escape del modal deja el mismo estado y el mismo foco. Anónimo, sin permiso,
  inspector y acta inexistente responden igual.
- G1 de punta a punta: core y runtime en dos contenedores gunicorn sobre una
  red interna. La ficha carga por core → compuerta → runtime; marcar como
  prueba y anular persisten y la página siguiente muestra el mensaje. Anónimo
  401, sin permiso 403, requisito pendiente 403 con `state`, acta inexistente
  404, header del cliente descartado, POST sin CSRF 403, GET a una acción 405 y
  `next` externo reemplazado por la ficha.

## Limitaciones

- Roboto (Google Fonts) quedó bloqueada sin red en los dos lados.
- La transición de entrada del toast (jQuery `fadeIn`) no se reproduce; se
  comparó el estado visible a 1,5 s.
- El menú móvil abierto está fuera de la comparación, por la excepción vigente.
- No se probó el modal con un `body` que ya tenga relleno a la derecha.
