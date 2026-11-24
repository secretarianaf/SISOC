# Cambio: lista de la nómina CDI y derivación en React sobre G1 v1 (#2785, CDI04.02 y CDI04.03)

## Alcance

Quinta entrega del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la lista
de la nómina de un centro (`/centrodeinfancia/<centro>/nomina/`) y la operación
de derivar a una persona a otro centro desde su modal, parte de CDI04.02 y
CDI04.03 del contrato `2026-10-28-2785-cdi-nomina-asistencia-m2.md`. El alta, la
edición, la baja (pantalla de confirmación) y la asistencia siguen nativas y la
lista las enlaza igual que el HTML. No activa React en producción y no cambia el
comportamiento nativo. No se consulta RENAPER ni ningún servicio externo.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_nomina_lista.py` y `web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json`.
- `src/frontends/apps/sisoc/src/routes/cdiNominaLista.tsx` y su prueba.
- Pruebas: `tests/test_web_nomina_lista.py` y un caso en `test_web_preview_cdi.py`.

## Comportamiento

`GET /api/web/cdi/centros/<pk>/nomina/` ejecuta `NominaCentroInfanciaDetailView`:
el centro sale del alcance del actor (404 fuera de él), las filas son las de la
página de 100 y las métricas, la distribución por edad y los centros de destino
salen del mismo contexto que el HTML, de modo que no pueden diferir. Cada celda
se renderiza con la expresión de `nomina_detail.html` (`default`, `date:"d/m/Y"`).
Una página inválida responde 404 como la nativa. Los filtros de texto, estado y
sala siguen siendo locales sobre la página, igual que el script nativo, y el
estado de «Ver estadísticas detalladas» se recuerda en `localStorage`
(`nominaDetailsExpanded`).

`POST /api/web/cdi/nomina/<pk>/derivar/` llama a la función nativa
`nomina_centrodeinfancia_derivar` sin cambios: el servicio de dominio, los
códigos (200, 400, 404, 405) y los mensajes son los nativos. Delante solo agrega
G1, el permiso de la URL nativa (`change_nominacentroinfancia` o
`add_nominacentroinfancia`, «alguno de») y CSRF. El modal envía el destino y el
motivo codificados como el formulario, una sola vez por confirmación; un
resultado no confirmado se muestra en el mismo aviso y nunca se reintenta solo.

Acceso de la lista: G1 y después `centrodeinfancia.view_nominacentroinfancia`,
como la URL nativa (el permiso de ver centros no alcanza).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 20 pruebas nuevas y un caso de vista previa (escritas junto con la implementación, sin corrida en rojo previa). La
  lista se compara con el HTML nativo (celdas, estado, sala, métricas); la
  derivación verifica los efectos persistidos (origen en Baja, destino Pendiente,
  historial con actor y motivo recortado) y que cada rechazo (destino inválido,
  igual, fuera de alcance, origen no activo, repetición, sin permiso, sin CSRF,
  método, requisito pendiente) deja las tablas de nómina y derivaciones idénticas.
  Suite combinada de CDI y del núcleo (puerta web, proxy, servicios): 218 pasan;
  black y pylint 10/10; `makemigrations --check` sin cambios.
- Frontend: 15 pruebas de ruta; una corrida completa de
  `vitest` (795), `tsc`, `eslint` y `vite build`.
- G1 de punta a punta: anónimo 401, sin permiso 403, requisito pendiente 403,
  cabecera falsificada ignorada, CSRF 403, lista 200, derivación inválida 400,
  derivación 200 y repetición 400.
- Visual (regla S13), escritorio y móvil, lista, estadísticas abiertas, modal de
  derivación y aviso de error del modal: 0,000 % de diferencia de píxeles, misma
  geometría y mismo orden de Tab, y mismos 403 y 404 de guardas.

## Limitaciones

- La lista nativa falla si un ciudadano de la nómina no tiene sexo cargado y no
  tiene sexo en la ficha (`ciudadano.sexo.sexo`); la API conserva el mismo
  comportamiento en lugar de ocultarlo.
- «Agregar persona», «Editar» y «Borrar» abren las pantallas nativas.
- Mismas diferencias del marco compartido que el
  [listado](2026-11-12-2785-react-cdi-centros-listado.md).
