# Cambio: convenio PNUD/Abordaje de comedor en React sobre G1 v1 (#2785, CO07.03)

## Alcance

Segunda entrega de la lane K5 del contrato
[`2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md):
la pantalla «Datos del Convenio» (`comedor_convenio_pnud_form.html`) y su API.
No activa React en producción y no cambia ninguna vista, ruta ni permiso
nativo.

Archivos:

- `src/backends/comedores/comedores/web_api_convenio.py` y la ruta en
  `web_api_validacion_convenio_tarjeta_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_convenio_tarjeta.py`: entrada
  de la vista previa local.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorConvenio.tsx` (registrada en
  `routes/index.ts`) y su prueba.
- Pruebas: `src/backends/comedores/comedores/tests/test_web_comedor_convenio_k5.py`
  y `test_web_preview_convenio_tarjeta_k5.py`.

## Comportamiento

`GET` y `POST` `/api/web/comedores/comedores/<pk>/convenio-pnud/` ejecutan la
vista nativa `ComedorDatosConvenioPnudUpdateView`:

- Alcance del comedor (404 si no) y rechazo de comedores que no usan el
  convenio: la misma redirección a la ficha con «Esta opcion solo aplica para
  comedores PNUD o Abordaje Comunitario.» en cola.
- El GET crea el registro vacío si no existe (`get_or_create`), como el
  nativo: no es una lectura pura. La entrada de la vista previa no lo crea; lo
  hace la API cuando la pantalla React la lee.
- El formulario por variante (`secos`, `tradicional`, resto) lo arma el
  formulario real: React recibe nombre, etiqueta, valor tal como lo muestra el
  widget (`1.235` para un monto), errores y atributos, más los datos de solo
  lectura (organización, código, estados, nombre, ID externo, domicilio y
  territoriales por proyecto) y los indicadores de variante. Los campos que la
  variante retira no se envían ni se limpian: sus valores históricos se
  conservan.
- Los montos son Decimal (14,2). La interfaz admite enteros con puntos de
  miles y rechaza decimales con el mensaje existente. Si el monto visible
  redondeado no cambió, el formulario restaura el valor inicial y conserva los
  centavos históricos. No se usa `float` ni se reconstruye el monto desde el
  texto redondeado.
- POST válido: 200 con `{"redirect": <ficha>}` sin mensaje adicional. POST
  inválido: 400 con los errores y el formulario ligado; no se guarda nada.

Acceso: G1, el permiso de la URL nativa (`comedores.change_comedor`; el
superusuario pasa siempre), CSRF y el alcance del comedor.

Pantalla React: mismas etiquetas, orden, columnas por variante y tabla de
prestaciones por convenio que la plantilla; los montos reciben los puntos de
miles al salir del campo (`convenio_pnud.js`); solo se envían los campos que
la plantilla muestra; tras un rechazo la pantalla vuelve arriba y muestra los
errores donde el nativo los dibuja (`invalid-feedback` y `errorlist`); un
fallo de red avisa y desactiva el guardado sin reintentar.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 24 pruebas de la API y 3 de la vista previa, en rojo (sin la ruta)
  y luego en verde: acceso, variantes, GET que crea una vez, rechazo por
  programa, alcance, efectos persistidos, montos decimales y mal formados,
  centavos conservados, cantidades negativas, matriz faltante y campos
  retirados que se conservan.
- Frontend: 9 pruebas nuevas; `tsc`, `eslint` y la compilación sin errores.
- Visual (S13, escritorio y móvil): lista de casos en el informe de la
  entrega; los cuatro estados (resto, secos, tradicional y error de monto)
  coinciden con el nativo.
- G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- No se agregan restricciones ni se modifican las vistas nativas.
- No hay suma obligatoria entre montos o prestaciones: el contrato la excluye.
