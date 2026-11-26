# Cambio: ficha de un destinatario de la nómina CDI en React sobre G1 v1 (#2785, CDI04.01)

## Alcance

Cuarta entrega del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la ficha
de solo lectura de un destinatario de la nómina
(`/centrodeinfancia/<centro>/nomina/<nómina>/ver/`), parte de CDI04.01 del
contrato `2026-10-28-2785-cdi-nomina-asistencia-m2.md`. La lista de nómina,
las altas, ediciones, bajas, la derivación y la asistencia siguen nativas. No
activa React en producción y no cambia el comportamiento nativo. No se consulta
RENAPER ni ningún servicio externo.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_nomina.py` y `web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json`.
- `src/frontends/apps/sisoc/src/routes/cdiNomina.tsx` y su prueba.
- Pruebas: `tests/test_web_nomina_destinatario.py` y un caso en
  `test_web_preview_cdi.py`.

## Comportamiento

`GET /api/web/cdi/centros/<pk>/nomina/<nomina_id>/` ejecuta
`NominaCentroInfanciaDestinatariosDetailView`: el centro y el registro salen del
alcance del actor y cualquier par fuera de él responde 404. Cada campo de
`destinatario_detail.html` se renderiza con la misma expresión del template
(`{{ expresión|default:"—" }}`), de modo que etiquetas de opciones, fechas
localizadas y `yesno` salen idénticos; una prueba compara los más de 60 pares
etiqueta y valor con el HTML nativo. La respuesta trae las secciones en el orden
nativo (Responsable 2 y Observaciones solo si existen), las listas de insignias,
la tabla de vacunas NOMIVAC y el enlace Editar solo con
`change_nominacentroinfancia`.

Acceso: G1 y después `centrodeinfancia.view_centrodeinfancia`, como la URL
nativa. Solo GET y HEAD.

La pantalla dibuja las tarjetas plegables del marcado nativo: encabezado con
`role="button"`, `tabindex="0"` y `aria-expanded`, Enter y Espacio para plegar.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 13 pruebas nuevas en rojo y luego en verde (paridad de campos,
  secciones condicionales, CUIL, insignias, vacunas, alcance y ids anidados,
  permisos, runtime firmado). Suite combinada: 1096 pasan y 3 se omiten; black y
  pylint 10/10; `makemigrations --check` sin cambios.
- Frontend: pruebas de ruta en rojo y luego en verde; una corrida completa de
  `vitest` (673), `tsc`, `eslint` y `vite build`.
- G1 de punta a punta: anónimo 401, sin permiso 403, CSRF 403, cabecera
  falsificada ignorada, registro ajeno 404 y camino feliz.
- Visual (regla S13), escritorio y móvil, ficha completa y mínima: 0,000 % de
  diferencia de píxeles y misma geometría fuera del menú lateral.

## Limitaciones

- El plegado no anima como el colapso de Bootstrap: alterna la clase `show`.
- Mismas diferencias del marco compartido que el
  [listado](2026-11-12-2785-react-cdi-centros-listado.md).
