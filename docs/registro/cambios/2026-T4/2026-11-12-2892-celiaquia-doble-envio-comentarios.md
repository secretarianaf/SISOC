# Cambio: Celiaquía no duplica comentarios técnicos ni otros envíos por doble clic

## Alcance

Issue #2892: en el expediente 335 un comentario técnico quedó registrado dos
veces en Observaciones, con el mismo minuto. No era un problema de caché ni del
usuario: el botón "Guardar Comentario" seguía habilitado mientras viajaba el
POST y el backend no tenía ningún control, así que un doble clic (o clic +
Enter) creaba dos registros.

No hay modelos, migraciones, permisos ni settings nuevos.

## Qué cambia

- **Comentario técnico, front**
  (`src/backends/celiaquia/celiaquia/static/custom/js/legajo_comentarios.js`):
  el botón Guardar se deshabilita y muestra un spinner "Guardando…" mientras
  hay un envío en curso; los envíos repetidos se ignoran.
- **Comentario técnico, back**
  (`ComentariosTecnicosService.registrar`, parámetro
  `ventana_reenvio_segundos`): la vista web pasa 10 segundos. Si el mismo
  usuario ya registró un comentario idéntico (tipo, Sí/No, código y texto)
  sobre el legajo dentro de esa ventana, se devuelve ese en lugar de crear
  otro. Se bloquea la fila del legajo (`select_for_update`) para que dos POST
  simultáneos no pasen ambos el chequeo.
- **Hora de los comentarios**: `fecha` y `publicado_en` se formateaban en UTC
  y se veían 3 horas adelantadas; ahora se pasan a hora local antes de
  formatearlas (`src/backends/celiaquia/celiaquia/views/comentarios.py`).
- **Formularios con recarga de página**: el nuevo
  `src/backends/celiaquia/celiaquia/static/custom/js/celiaquia_un_solo_envio.js`
  bloquea el botón con spinner en los forms marcados con `data-un-solo-envio`:
  Generar expediente de pago (cupo provincial y listado de pagos), alta de
  expediente, Procesar respuesta del pago y Asignar técnico.
- **Registros erróneos**
  (`src/backends/celiaquia/celiaquia/static/custom/js/registros_erroneos.js`):
  Confirmar reprocesar y Confirmar baja no se disparan dos veces.

## Criterio

- El dedupe por ventana de tiempo no es el comportamiento por defecto del
  service: el negocio permite volver a registrar la misma observación (por
  ejemplo, para una nueva instancia de subsanación, issue #2592). Por eso es
  opt-in y lo usa solo la vista web; la API no lo usa.
- No se usó el cache de Django para un token de idempotencia porque es
  `LocMemCache` (por proceso) y no cubre varios workers.
- El resto de los modales del expediente y de cupo ya deshabilitaban el botón
  con spinner; se siguió ese mismo patrón.
- "Generar expediente de pago" queda protegido solo en la pantalla. Impedir un
  segundo pago del mismo período en el backend es una regla de negocio que
  queda para definir con producto.
- Los comentarios que ya están duplicados en producción no se limpian con este
  cambio.

## Verificación

- `pytest src/backends/celiaquia/celiaquia/tests/test_comentarios_tecnicos_service.py`:
  reenvío dentro de la ventana devuelve el mismo registro; fuera de la ventana,
  con otro contenido o de otro usuario se crea uno nuevo.
- `pytest src/backends/celiaquia/celiaquia/tests/test_comentarios_tecnicos_flujo.py`:
  dos POST idénticos al endpoint dejan un solo comentario; el listado muestra
  la hora argentina.
- Suite de Celiaquía: 691 pasan. Fallan 3 `test_listados_sin_n_mas_1` de
  `test_admin_operaciones_celiaquia.py`, que fallan igual sin este cambio.
- Prueba manual: doble clic en Guardar comentario deja uno solo, con spinner y
  hora correcta.
