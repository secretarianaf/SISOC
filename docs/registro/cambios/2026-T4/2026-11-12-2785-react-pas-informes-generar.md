# Cambio: solicitud de generación de informes PAS en React sobre G1 v1 (#2785, PAS04.02)

## Alcance

Formulario «Generar informe PAS» (`pas/informes/generar`), su previsualización
y la creación del informe, según el
[contrato PAS02-PAS04](../../../plans/2026-T4/2026-11-10-2785-pas02-pas04-contratos.md).
No cambia vistas, formulario, servicios ni plantillas nativas, ni activa React
en producción.

Archivos:

- `src/backends/pas/pas/web_api_informes.py` (vistas nuevas) y rutas en
  `src/backends/pas/pas/web_api_urls.py`.
- `src/backends/pas/pas/web_preview_informes.py`: entrada local del GET de
  `pas/informes/generar`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado, tres rutas nuevas).
- `src/frontends/apps/sisoc/src/routes/pasInformesGenerar.tsx` y su registro en
  `routes/index.ts`.
- Pruebas: `src/backends/pas/pas/tests/test_web_pas_informes_generar.py`,
  ampliación de `test_web_pas_informes_preview.py` y
  `src/frontends/apps/sisoc/src/routes/pasInformesGenerar.test.tsx`.

## Comportamiento

- `GET /api/web/pas/informes/opciones/?provincia=<id>`: estados, avisos,
  provincias y municipios leídos de los querysets de `PasInformeGenerarForm`
  (mismo orden; municipios solo de la provincia pedida, ninguno sin ella o con
  un valor inválido), más el breadcrumb nativo.
- `POST /api/web/pas/informes/previsualizar/`: el mismo formulario y
  `preview_payload`/`errors_payload` de la vista nativa (200 con hasta 50
  filas, 400 con `{"ok": false, "errors": {...}}`).
- `POST /api/web/pas/informes/generar/`: formulario válido crea exactamente un
  `PasInforme` con `generar_informe_pas` y responde el CSV
  (`csv_response_for_informe`, BOM, `pas-inf-NNNNNN.csv`), con el encabezado
  `X-PAS-Informe-Id`. Inválido responde 400 y no crea nada.
- Acceso: G1 y después `permissions_all_required` con `pas.view_paspersona` y
  `pas.add_pasinforme`, igual que las rutas nativas. El CSV vuelve en el mismo
  POST porque la descarga posterior exige además `auth.role_exportar_a_csv`:
  separarlos cambiaría quién recibe el archivo.
- React (`pasInformesGenerar.tsx`): mismos campos, orden, textos y botones que
  `informe_form.html`; los municipios se recargan al cambiar la provincia
  (lista reiniciada a «---------» como en `pas_informe.js`); la vista previa
  muestra `field: mensaje` y conserva la tabla anterior ante un error. «Realizar
  informe» deshabilita los botones mientras espera, no reintenta, guarda el CSV
  con el nombre del servidor y deja al usuario en el formulario (sin redirección
  ni mensaje, como el nativo). Un 400 marca cada campo; ante un 504 o un
  resultado ilegible muestra el texto G1 con un enlace al listado.

## Diferencias conocidas

- El municipio se carga con `opciones/` y no con la ruta AJAX del core
  (`ajax_load_municipios`), como fija el contrato.
- Tras un error de formulario el nativo recarga la página y React no: el
  primer Tab posterior parte del botón enviado y no del inicio. Es propio de
  una pantalla que no recarga.
- Sigue vigente el bug nativo del autor borrado (500 en listado y detalle):
  React muestra «-» (ver el registro de PAS04.01).

## Verificación

Entorno sintético, sin red, imagen fijada; SINTyS y RENAPER nunca se llaman.

- Backend: 24 pruebas nuevas en rojo (22 de 24) y luego en verde, más dos en la
  entrada local; suite de `src/backends/pas`, `web_gate`, `backend_proxy`,
  `servicios_backends` y `admindocs`, registro de URLs al día, `black`,
  `pylint` 10/10 y `makemigrations --check`.
- Frontend: Vitest de `sisoc` completo en verde, `tsc`, ESLint y build.
- G1 de punta a punta (core y runtime de PAS en dos contenedores gunicorn,
  informes y solicitud juntos): anónimo 401 (GET y POST), sin permiso 403,
  requisito pendiente 403, POST sin CSRF 403, encabezado de G1 falsificado
  ignorado (200 con la cookie del lector), listado, detalle, opciones y
  previsualización con CSRF 200; en el navegador, municipios por provincia,
  previsualización, error de rango y descarga de `pas-inf-000002.csv` con BOM.
- Visual (S13) en 1440x900 y 390x844: formulario, con vista previa, con error
  de rango y con error de vista previa. Área principal igual: desvío 0 px y
  0 % de píxeles distintos. Guardas (anónimo, sin permiso de alta, lector)
  iguales al nativo (403).

## Limitaciones

- Diferencias del marco compartido, fuera de esta entrega: el menú lateral
  (en móvil queda fuera de pantalla) y el nombre accesible del enlace de marca
  que cambia el primer tope de Tab.
- Cada POST de `generar/` crea un registro; no hay idempotencia. Por eso la
  pantalla no reintenta y ante un 504 pide verificar el listado.
