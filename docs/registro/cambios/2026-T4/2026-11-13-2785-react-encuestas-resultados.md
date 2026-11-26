# Cambio: resultados de encuestas en React sobre G1 v1 (#2785, E03)

## Alcance

Segunda unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la pantalla `/encuestas/<pk>/resultados/`. Lee por
`EncuestaResultadosView` y no escribe nada. Las exportaciones CSV y Excel por ronda (`.../resultados/rondas/<ronda_pk>/exportar/`)
y la exportación JSON de la encuesta (`/encuestas/<pk>/exportar/`) siguen siendo los GET nativos: la pantalla enlaza la primera
y la segunda es un enlace del formulario de edición (E04). No se tocan vistas, servicios, plantillas ni URLs nativas ni se activa
React en producción.

Archivos:

- `src/backends/sisoc_core/encuestas/web_api_resultados.py` (ruta en `web_api_urls.py`), `url_registry.json` y
  `config/middlewares/admindocs.py`.
- `src/backends/sisoc_core/encuestas/web_preview_encuestas.py`: entrada de vista previa de la ruta.
- `src/frontends/apps/sisoc/src/routes/encuestasResultados.tsx`, registrado en `routes/index.ts`.
- Pruebas: `test_web_resultados_api.py`, `test_web_preview_encuestas.py` y `encuestasResultados.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `encuestas.ver_resultados` (403; `change_encuesta` no alcanza), igual que la ruta nativa.
  Una encuesta inexistente da 404 y la ruta no admite POST (405).
- Los textos llegan formateados como los imprime la plantilla: fechas `d/m/Y` en hora local, porcentajes y posiciones con la
  localización de Django (`66,7`, `50,0`) y promedio, mínimo y máximo con `floatformat`. Por eso un ancho como `66,7%` es tan
  inválido en React como en el `style` nativo: es un quirk conservado, no un defecto nuevo.
- La proyección no agrega campos: los resultados por pregunta solo cuentan y agrupan (nunca quién respondió qué), y el nombre
  de cada puntaje solo aparece donde la plantilla lo imprime («Respuesta anónima» si no hay).
- El selector de ronda hace un GET de la página con `?ronda=<id>`, como el `onchange` nativo. Una ronda que no es de la
  encuesta deja la barra sin ronda actual, sin exportaciones ni tarjetas. Sin rondas: «Esta encuesta todavía no tiene rondas.».

## Verificación

- Backend (imagen fijada, sin red): 7 pruebas nuevas (acceso, comparación de los textos con la página nativa, ronda
  inexistente, sin rondas y lectura sin escrituras) y 1 de la vista previa; `black`, `pylint` y `makemigrations --check`.
- Frontend: 7 pruebas nuevas, `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo (401, 403, requisito pendiente, cabecera falsificada, CSRF y lectura con una ronda de 3 respuestas).
- Comparación visual nativo contra React (con respuestas, con puntaje identificado y anónimo, sin rondas y ronda inexistente;
  escritorio y móvil) y guardas.

## Limitaciones

Una encuesta con muchas rondas muestra todas en el selector, como la plantilla. La descarga de CSV y Excel se hace con la
navegación nativa y no por la API.
