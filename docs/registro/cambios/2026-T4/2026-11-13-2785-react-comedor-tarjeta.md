# Cambio: responsable de la tarjeta de comedor en React sobre G1 v1 (#2785, CO07.03)

## Alcance

Tercera entrega de la lane K5 del contrato
[`2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md):
la pantalla «Responsable de la Tarjeta» (`responsable_tarjeta_form.html`) y su
API. No activa React en producción y no cambia ninguna vista, ruta ni permiso
nativo.

Archivos:

- `src/backends/comedores/comedores/web_api_tarjeta.py` y la ruta en
  `web_api_validacion_convenio_tarjeta_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_convenio_tarjeta.py`: segunda
  entrada de la vista previa local.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorTarjeta.tsx` (registrada en
  `routes/index.ts`) y su prueba.
- Pruebas: `src/backends/comedores/comedores/tests/test_web_comedor_tarjeta_k5.py`
  y `test_web_preview_convenio_tarjeta_k5.py`.

## Comportamiento

`GET` y `POST` `/api/web/comedores/comedores/<pk>/responsable-tarjeta/`
ejecutan la vista nativa `ResponsableTarjetaComedorUpdateView`:

- Cadena de guardas nativa: permiso de la ruta `auth.role_tecnico_comedor`,
  alcance del comedor, programa «Alimentar Comunidad» y pertenencia exacta al
  grupo «Tecnico Comedor». Quien pasa el permiso pero no está en el grupo
  recibe el 404 nativo; el superusuario tampoco tiene un atajo nuevo (sin el
  grupo, 404). No se cambia el grupo por un permiso.
- El formulario real (`ResponsableTarjetaComedorForm`) entrega los nueve campos
  en el orden de la plantilla, con las opciones que armó para los valores
  actuales: provincias completas ordenadas, municipios de la provincia y
  localidades del municipio (o de la provincia si no hay municipio). Un
  registro antiguo con localidad y sin municipio deriva el municipio de la
  localidad.
- Se guardan solo esos nueve campos; cualquier otro dato del cuerpo (nombre del
  comedor, estado de validación) se ignora. Todos son opcionales, de modo que
  una carga parcial es válida.
- Éxito: 200 con `{"redirect": <ficha>}` y sin mensaje adicional. Rechazo
  (correo inválido, longitudes, municipio de otra provincia, localidad de otro
  municipio): 400 con los errores y el formulario ligado, y no se guarda nada.

Acceso: G1, el permiso de la URL nativa, CSRF y las guardas de la vista.

Pantalla React: mismas etiquetas, orden y columnas que la plantilla. Los tres
selectores reproducen el widget Select2 y recargan municipios y localidades
como `ubicacionSelects.js` (se vacían los dependientes y se piden por AJAX).
Se envían los nueve campos tal como se escribieron; tras un rechazo la
pantalla vuelve arriba y muestra los errores y las opciones que reconstruyó el
servidor. Un fallo de red avisa y desactiva el guardado sin reintentar.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 15 pruebas de la API y 2 nuevas de la vista previa, en rojo (sin la
  ruta) y luego en verde: acceso, grupo exacto, programa, alcance, orden y
  opciones, localidad antigua, carga parcial, efectos persistidos solo en los
  nueve campos y rechazos sin escritura.
- Frontend: 8 pruebas nuevas; `tsc`, `eslint` y la compilación sin errores.
- Visual (S13, escritorio y móvil): vacío, lleno y error de correo coinciden
  con el nativo.
- G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- En el entorno de prueba el grupo «Tecnico Comedor» ya porta el permiso de la
  ruta, así que «grupo sin permiso» no se puede construir; se prueba el caso
  contrario (permiso sin grupo) que el contrato exige.
- No se agregan restricciones ni se modifican las vistas nativas.
