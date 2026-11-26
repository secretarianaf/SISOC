# Cambio: listado y ficha de formularios institucionales CDI en React sobre G1 v1 (#2785, CDI03)

## Alcance

Tercera entrega de la lane C5 sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): el listado
(`/centrodeinfancia/<centro>/formularios/`) y la ficha
(`.../formularios/<formulario>/`) de los formularios institucionales, contrato
`2026-10-28-2785-cdi-formularios-trabajadores-m2.md`. El alta y la edición siguen
nativas (sus enlaces conservan las URL nativas); el formulario no tiene ruta de baja. No
activa React en producción ni cambia el comportamiento nativo. No se consulta ningún
servicio externo.

Archivos: `web_api_formularios_institucionales.py`, `web_api_urls_formularios_institucionales.py`,
`web_preview_formularios_institucionales.py`, `routes/cdiFormularios.tsx` y su prueba, `admindocs.py` y
`url_registry.json`; `cdi_runtime/web_api_urls.py` solo agrega el include.

## Comportamiento

Las dos API ejecutan `FormularioCDIListView` y `FormularioCDIDetailView`: el centro y el
formulario salen del alcance del actor (404 fuera de él y para una página inválida) y cada
celda se renderiza con la misma expresión del template (fechas y decimales localizados,
«-» para vacíos, etiquetas de opciones). Dos pruebas comparan todas las celdas, pares
etiqueta/valor y totales con el HTML nativo. Acceso: G1 y después
`centrodeinfancia.view_formulariocdi`, como las URL nativas. Solo GET y HEAD. Las lecturas
no escriben: la ficha no usa `ensure_fixed_rows` (esa creación de filas está en la
edición y queda para la entrega del formulario).

La pantalla conserva la paginación nativa («Volver», «Continuar», puntos suspensivos y el
contador, que el template oculta cuando la página no tiene filas) y los demás parámetros de
la consulta.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 10 pruebas de API y 3 de vista previa; la suite de CDI y los tests de puerta
  web, proxy y servicios pasan (305); black limpio, pylint 10/10, `makemigrations --check`
  sin cambios; `url_registry.json` regenerado.
- Frontend: 7 pruebas de ruta; una corrida completa de `vitest` (1304), `tsc`, `eslint` y
  `vite build`.
- G1 de punta a punta: 20 verificaciones, entre ellas listado, ficha, par de otro centro
  404, sin permiso 403 y página inválida 404.
- Visual (S13), escritorio y móvil: listado, página 2, listado vacío, ficha completa y
  mínima sin diferencias (0,000 % de píxeles, geometría 0 px).

## Limitaciones

- Mismas diferencias del marco compartido que el
  [listado de centros](2026-11-12-2785-react-cdi-centros-listado.md).
