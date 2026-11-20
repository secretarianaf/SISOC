# Cambio: ficha del caso de DataCalle en React y regresión del consumidor de campo (#2785, DC02.01 y DC02.03)

## Alcance

Ficha del caso (`/datacalle/casos/<uuid>/`) sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md), y la
regresión de la app de campo (DC02.03). Contrato:
[DataCalle DC01-DC02](../../../plans/2026-T4/2026-11-10-2785-datacalle-dc01-dc02-contratos.md).
Continúa [operativos](2026-11-11-2785-react-datacalle-operativos.md), que ya
adelantó las opciones de dispositivos y relevadores (`opciones/...`).

DC02.02 no tiene operación web nativa (el backoffice no edita ni borra casos), así
que no hay nada que migrar. La API por token `api/datacalle/` y la app SISOC - Mobile
no cambian de código. No activa React en producción.

Archivos:

- `src/backends/dispositivos/datacalle/web_api.py` y `web_api_urls.py`:
  `GET /api/web/dispositivos/datacalle/casos/<uuid>/` (`CasoDetailWebView`). Corre
  `EncuestaDetailView` y proyecta lo que muestra la ficha nativa.
- `src/backends/dispositivos/datacalle/web_preview.py`: entrada React de la ruta del
  caso, con los mismos guardas nativos.
- `src/backends/config/middlewares/admindocs.py` y `src/backends/config/url_registry.json`
  (regenerado con `generar_registro_urls`, solo una alta).
- `src/frontends/apps/sisoc/src/routes/datacalleCasos.tsx` (ruta de la unidad) y
  `routes/index.ts` (registro).
- Pruebas: `src/backends/dispositivos/tests/test_web_datacalle_casos.py`,
  `src/backends/dispositivos/tests/test_web_datacalle_campo.py` y
  `src/frontends/apps/sisoc/src/routes/datacalleCasos.test.tsx`.

## Comportamiento

`GET casos/<uuid>/` exige `datacalle.view_encuesta` (no `view_relevamiento`) y que
el caso sea de un operativo en el alcance provincial; fuera de alcance, dado de baja
o id no UUID da 404. Otros métodos, 405. Respuestas `private, no-store`.

Devuelve: título «Caso {código o id}», estado y su etiqueta, origen, relevador (nombre
completo o usuario), fecha `d/m/Y H:i`, variante, indicadores de formulario de menores
y de franja etaria con su etiqueta, migas de pan y las respuestas tal como las
entrega `respuestas_legibles` (páginas con `titulo` e `items`). Una pregunta sin
etiqueta en el instrumento se ve como «None» en la ficha nativa y la API conserva ese
texto (quirk de paridad). Datos sensibles (personas en situación de calle, menores):
no se exponen las respuestas crudas, el GPS del caso ni `grupo_id`, que la ficha no
muestra.

La pantalla React repite `encuesta_detail.html`: avisos de menores y de franja,
páginas de respuestas, chip «pregunta retirada» y estado vacío «El caso no trae
respuestas».

## DC02.03: consumidor de campo

- Sin cambios de código en `api_urls.py`, `api_views.py`, `api_permissions.py` ni
  `api_serializers.py` (comprobado por diferencia contra la base).
- Las pruebas existentes de la app pasan sin modificarlas: `test_datacalle_api.py`,
  `test_datacalle_relevamientos.py`, `test_datacalle_roles.py`,
  `test_datacalle_qa_usuarios.py`, `test_datacalle_repro_500.py` y los tres
  `test_datacalle_instrumento_4_*`.
- `test_web_datacalle_campo.py` prueba las invariantes cruzadas: un operativo creado,
  cerrado o dado de baja desde la API web se ve en la app (`mis_relevamientos`, estado,
  `actualizado_en` y `?desde=`) igual que si se hiciera desde el HTML nativo; el cierre
  deja el 409 `relevamiento_cerrado` (no reintentable) a la carga de casos; el cierre
  por token sigue siendo del coordinador (403 `cierre_no_autorizado`).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: las pruebas del caso fallan sobre la base (5 de 6) y pasan con el cambio;
  suite de `datacalle` y `dispositivos` de la app, `test_web_gate`,
  `test_backend_proxy` y `test_servicios_backends` en verde; `black` y `pylint` 10/10.
- Frontend: prueba de ruta nueva; `tsc`, ESLint, Vitest del proyecto sisoc completo
  (519) y build de Vite sin errores.
- G1 de punta a punta (core y runtime en contenedores): ficha del caso por el core;
  anónimo 401, sin permiso y solo `view_relevamiento` 403, requisito pendiente 403,
  cabecera falsificada ignorada, POST sin CSRF 403, 405, id no UUID e inexistente 404.
- Visual (regla S13), nativo contra React, 5 estados en 1440x900 y 390x844 (caso
  normal, menores, franja etaria, vacío, solo `view_encuesta`): 10/10 con diferencia
  perceptual menor a 0,01 % y desvío geométrico 0; las 7 guardas responden igual.

## Limitaciones

- La ficha sigue mostrando el enlace «Ver» del operativo sin chequear `view_encuesta`
  (quirk nativo, conservado).
- Diferencias del marco compartido `SisocShell`, fuera de esta unidad (logo con
  `aria-label`, menú móvil).
