# Cambio: formulario de intervenciones de comedor en React, alta y edición (#2785, CO02)

## Alcance

Segunda entrega de la lane K4 del contrato
[`2026-10-28-2785-comedores-intervenciones-observaciones-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-intervenciones-observaciones-m2.md),
sobre la de [lectura](2026-11-13-2785-react-comedor-intervenciones-lectura.md):
alta y edición de una intervención de comedor (`intervencion_form.html`) y la
lista de subtipos que el formulario consulta. La baja de la intervención y las
observaciones (CO06) quedan para entregas siguientes. No activa React en
producción y no cambia ninguna vista, ruta ni permiso nativo.

Archivos:

- `src/backends/comedores/intervenciones/web_api_formulario.py` y
  `web_api_urls.py`: API web (tres rutas nuevas).
- `src/backends/config/url_registry.json` (regenerado) y
  `src/backends/config/middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/comedorIntervencionesForm.tsx` y su
  prueba; `comedorIntervenciones.tsx` suma las dos rutas nativas.
- Prueba de backend:
  `src/backends/comedores/intervenciones/tests/test_web_intervenciones_formulario_k4.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `/api/web/comedores/intervenciones/comedor/<pk>/crear/` | GET/POST: ejecuta `IntervencionCreateView` (`intervenciones.add_intervencion`) |
| `/api/web/comedores/intervenciones/<pk>/editar/<pk2>/` | GET/POST: ejecuta `IntervencionUpdateView` (`intervenciones.change_intervencion`); `pk` es la intervención y `pk2` el comedor, como en la URL nativa |
| `GET /api/web/comedores/intervenciones/subestados/?id=` | Devuelve la lista nativa `[{id, text}]` de `sub_estados_intervenciones_ajax`; la ruta nativa solo pide sesión y no se agrega permiso |

El POST acepta `multipart/form-data` o `application/x-www-form-urlencoded`
(otro formato responde 415 sin escribir) y ejecuta el `post()` nativo:
`IntervencionForm`, la verificación de la admisión (`admision_id` del cuerpo o
de la consulta, «La admisión seleccionada no corresponde al comedor actual.»),
el archivo y `safe_redirect` con `next`. Una redirección nativa se devuelve
como `{"ok": true, "redirect": ...}` y un formulario rechazado como 400 con los
valores ligados. Un rechazo no escribe la fila ni el archivo.

Acceso, en este orden: G1 (sesión y requisitos web, o la constancia firmada del
runtime) y los mismos códigos de permiso que la URL nativa (el superusuario
pasa siempre). No se agrega alcance por comedor.

Rarezas nativas conservadas, a propósito:

- La plantilla no dibuja mensajes de error: el 400 solo marca `aria-invalid`
  y `aria-describedby` en los campos inválidos, como el HTML nativo.
- En la edición, la fecha llega como `dd/mm/aaaa` y un campo `type=date` la
  muestra vacía: hay que cargarla de nuevo.
- Con un tipo ya elegido (edición o formulario devuelto), el script de la
  plantilla vuelve a pedir los subtipos y descarta el subtipo elegido; si el
  tipo tiene subtipos hay que elegirlo otra vez.
- El tipo enviado siempre es válido aunque no sea del programa del comedor
  (`include_ids` del formulario nativo).
- El año de la fecha se valida en el navegador con `new Date(valor)`, que usa
  UTC: el 1 de enero de 2000 se considera 1999 en horario argentino, igual que
  el script nativo.

Pantalla React: marco oscuro de `routes/MainFrame.tsx`, los dos pasos, la barra
de progreso, `Select2` compartido para tipo y subtipo, la fila del archivo que
se muestra al tildar la casilla y el envío multipart con un solo intento: si
no se confirma el resultado se avisa y no se reenvía. Un rechazo vuelve al
paso 1 con los valores ligados (como la recarga nativa).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 19 pruebas nuevas en rojo (sin las rutas) y luego en verde:
  permisos, proyección del formulario, alta con archivo y redirección, `next`
  local y externo, ocho rechazos sin escritura, formato JSON (415), CSRF,
  edición y subtipos.
- Frontend: 9 pruebas nuevas (el módulo no existía); `tsc`, `eslint` y la
  compilación sin errores.
- Visual (regla S13) y G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- La subida de archivo del formulario conserva el contrato nativo: sin
  validación de extensión ni de tamaño y sin protección de descarga (hallazgo
  residual del contrato).
- Las rarezas de la lista anterior se reportan como decisión pendiente: no se
  corrigen por esta vía.
