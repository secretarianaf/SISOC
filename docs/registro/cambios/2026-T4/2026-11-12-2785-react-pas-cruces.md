# Cambio: cruces y novedades PAS en React sobre G1 v1 (#2785, PAS03.01 y PAS03.02)

## Alcance

Pantalla «Cruces y Novedades · PAS» (`pas/cruces`): resultados y evidencia
(PAS03.02) y las tres acciones de preparación y ejecución (PAS03.01), según el
[contrato PAS02-PAS04](../../../plans/2026-T4/2026-11-10-2785-pas02-pas04-contratos.md).
No cambia vistas, formularios, servicios ni plantillas nativas, ni activa React
en producción. SINTyS y RENAPER nunca se llaman: la exportación arma el archivo
localmente, la importación guarda el archivo sin leerlo y la actualización de
RENAPER solo registra la corrida mensual.

Archivos:

- `src/backends/pas/pas/web_api_cruces.py` (vistas nuevas) y rutas en
  `src/backends/pas/pas/web_api_urls.py`.
- `src/backends/pas/pas/web_preview_cruces.py`: entrada local del GET de
  `pas/cruces`.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado, cuatro rutas nuevas).
- `src/frontends/apps/sisoc/src/routes/pasCruces.tsx` y su registro en
  `routes/index.ts`.
- Pruebas: `src/backends/pas/pas/tests/test_web_pas_cruces.py`,
  `src/backends/pas/pas/tests/test_web_pas_cruces_preview.py` y
  `src/frontends/apps/sisoc/src/routes/pasCruces.test.tsx`.

## Comportamiento

- `GET /api/web/pas/cruces/` (cualquiera de `pas.view_paspersona`): corre
  `PasCrucesView` y proyecta `can_change`, `total_padron`, `circuito` (período y
  si existe), las seis `etapas` de `construir_etapas`, el resumen RENAPER, la
  bandeja de hasta 100 incompatibilidades pendientes (el mismo queryset nativo,
  con su exclusión de la baja por fallecimiento) y las áreas del circuito. No
  crea el circuito del mes. La corrida (`run_summary`) no se incluye: la
  plantilla no la muestra.
- `POST .../exportar-sintys/`: ejecuta el `post` de la vista nativa; crea el
  circuito si falta, marca la etapa 1 y responde el mismo XLSX con el mismo
  `Content-Disposition`. El archivo vuelve en el POST porque la exportación
  nativa crea el registro y entrega ese contenido.
- `POST .../importar-sintys/` (multipart `archivo`): `PasRetornoSintysForm`; válido
  guarda el archivo, marca la etapa 2 y responde
  `{"message": "Retorno SINTyS importado correctamente."}`; inválido responde 400
  con `message` («No se pudo importar el retorno: ...») y `errors`, sin tocar el
  circuito.
- `POST .../actualizar-renaper/`: `request_run`, idempotente por período
  (mismo `run_id`); responde `run_id` y el mensaje nativo.
- Acceso: G1 y después la regla nativa (`permissions_any_required`): lectura con
  `pas.view_paspersona`, acciones con `pas.change_paspersona`.
- React (`pasCruces.tsx`): mismo orden, textos y controles que `area.html`
  (rama `cruces`). Los botones solo aparecen con `can_change`. Elegir un archivo
  lo envía solo, como el script nativo; «Actualizar» pide la confirmación nativa
  y pasa a «Actualizando». Tras cada acción React vuelve a pedir el GET (la
  recarga del nativo) y los mensajes salen como toast al final del `<body>`. Un
  error al exportar abre `alert` con «No se pudo generar la nómina.»; un 504 o un
  resultado ilegible muestra el texto G1 de resultado incierto y no reintenta.

## Diferencias conocidas

- La recarga del nativo es una navegación; React vuelve a leer el GET y
  desmonta la pantalla un instante («Cargando área…»).
- El 403 de una acción lleva a la pantalla de acceso del marco, no al `alert`.

## Verificación

Entorno sintético, sin red, imagen fijada; ningún test llama a RENAPER (se
reemplaza el cliente por una función que falla).

- Backend: 18 pruebas nuevas en rojo (contra la base) y luego en verde, más dos
  de la entrada local; suite de `src/backends/pas`, `web_gate`, `backend_proxy`
  y `servicios_backends` (369 en verde, 1 omitida), `black`, `pylint` sobre los
  archivos tocados y `makemigrations --check` sin cambios.
- Frontend: Vitest de `sisoc` completo en verde (15 pruebas nuevas), `tsc`,
  ESLint y `vite build`.
- G1 de punta a punta (core y runtime de PAS): anónimo 401 (GET y POST), sin
  permiso 403, requisito pendiente 403, POST sin CSRF 403, encabezado de G1
  falsificado ignorado, lectura 200; lector sin cambio recibe 403 en las tres
  acciones; importar `.pdf` da 400 con el texto nativo; exportar y RENAPER 200.
- Visual (S13) en 1440x900 y 390x844: lista con permiso de cambio, lista de
  lector, importación rechazada y actualización de RENAPER; 0 a 0,19 % de píxeles
  distintos, desvío máximo 0,03 px, mismo orden de Tab. Guardas (anónimo y sin
  `view_paspersona`) iguales al nativo (403).

## Limitaciones

- Diferencias del marco compartido, fuera de esta entrega: el menú móvil y el
  nombre accesible del enlace de marca (primer tope de Tab).
- Exportar genera el XLSX de todo el padrón dentro del request: medir el tiempo
  con el volumen de PRD antes de activarlo (riesgo de 60 s del contrato).
- El estado vacío de la bandeja no está en la comparación visual (la semilla trae
  filas); lo cubren las pruebas de Vitest.
