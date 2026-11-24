# Cambio: asistencia de la nómina CDI en React sobre G1 v1 (#2785)

## Alcance

Pantalla `/centrodeinfancia/<centro>/nomina/asistencia/` (`nomina_asistencia.html`), con el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y la decisión de
[acceso conservado](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md). Sigue después del
[detalle del formulario de nómina](2026-11-17-2785-react-cdi-nomina-formulario.md). No activa React en
producción ni cambia el comportamiento nativo. No se consulta ningún servicio externo.

Archivos: `web_api_nomina_asistencia.py`, `web_api_urls_nomina_asistencia.py`,
`web_preview_nomina_asistencia.py`, `cdi_runtime/web_api_urls.py`, `routes/cdiNominaAsistencia.tsx` con su
prueba, `admindocs.py` y `url_registry.json`.

## Comportamiento

La API ejecuta `AsistenciaNominaCentroView`: el centro se filtra por alcance (404 fuera de él), la fecha
se interpreta con el servicio nativo (una fecha inválida muestra su mensaje y usa hoy) y las filas, los
contadores y el `guardar` son los nativos. Delante solo agrega G1 y el permiso de la URL
(`change_centrodeinfancia`). El POST acepta solo urlencoded; un guardado o un rechazo del servicio
responden con la redirección nativa y el mensaje se muestra en la página de destino.

El calendario mensual que abre la pantalla **no se migra**: es un endpoint JSON que solo consulta el
script de esta página y sigue siendo el nativo (`.../asistencia/calendario/?mes=AAAA-MM`). La pantalla
lo llama con `fetch` y `credentials: "same-origin"`, como el script nativo, y deja el mes sin marcas si
la respuesta no es exitosa.

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 13 pruebas nuevas (filas y contadores contra el contexto nativo, fecha por defecto e inválida,
  sin nómina, guardado con redirección y mensaje, borrado de la marca previa, rechazo del servicio sin
  escrituras, formato y CSRF, alcance, calendario nativo, 401 y 403, URLs nativas, entrada de vista
  previa); black limpio, pylint 10/10; `url_registry.json` regenerado (solo 1 nombre agregado).
- Frontend: pruebas de ruta; una corrida completa de `vitest`, `tsc`, `eslint` y `vite build`.
- G1 de punta a punta y visual (S13) escritorio y móvil: ver el resultado en la entrega de la unidad.

## Limitaciones

- El calendario depende de la URL nativa del monolito: en un despliegue donde React se sirva sin esa
  ruta, el mes se muestra sin marcas (igual que ante un error en el script nativo).
