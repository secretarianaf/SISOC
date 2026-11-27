# Cambio: modelo de la Encuesta de satisfacción de CDI (210SatisfaccionCDI)

## Alcance
Primera parte de la encuesta pública y anónima de satisfacción de familias de CDI (PFPI / SIMEPI): el modelo de datos, sin pantallas ni API. Las partes siguientes son la API pública, el formulario React y la descarga en Reportes.

- `src/backends/cdi/centrodeinfancia/encuesta_satisfaccion_schema.py`: versión del instrumento (1.0), códigos y etiquetas (canal, sala, origen de la sala, escala, dispositivo, estado, motivo de rechazo), las 15 preguntas y la equivalencia entre las salas de la nómina y las de la encuesta.
- `src/backends/cdi/centrodeinfancia/models_encuesta_satisfaccion.py`: `EncuestaSatisfaccionToken` (token de un solo uso, solo el hash), `EncuestaSatisfaccionRespuesta` (una fila por encuesta enviada) y `EncuestaSatisfaccionRechazo` (envíos rechazados, sin respuestas ni datos personales).
- `src/backends/cdi/centrodeinfancia/migrations/0058_encuesta_satisfaccion.py`: las tres tablas.
- `src/backends/cdi/centrodeinfancia/migrations/0059_encuesta_satisfaccion_mysql.py`: solo en MySQL, los triggers de inmutabilidad y la vista `v_210SatisfaccionCDI_descarga`.

Las decisiones de diseño están en `docs/registro/decisiones/2026-11-27-encuesta-satisfaccion-cdi-modelo.md`.

## Comportamiento
- No cambia nada visible para usuarios todavía: no hay pantalla ni endpoint que use estas tablas.
- Una respuesta guardada no se puede editar ni borrar desde Django (`RespuestaInmutableError`) ni, en MySQL, directo sobre la base (triggers). Se admiten solo la anulación lógica, que queda preparada para la próxima etapa y es irreversible, y la purga de `ip_hash`.
- La base rechaza valores fuera de dominio: P01 a P15 entre 1 y 5, P13 además 9 («No brinda alimentación»), sala de 1 a 6, envío anterior a la apertura, anulación sin motivo, puntaje de captcha fuera de 0 a 1 y dos respuestas con el mismo token.
- La vista para el área trae una fila por respuesta con código y etiqueta de cada variable, sin token, `ip_hash`, captcha ni hash de integridad, con `fecha_carga` en hora Argentina.
- Las tablas nuevas no se registran en el audittrail: la encuesta es anónima y sus respuestas no se editan.

## Verificación
- `pytest src/backends/cdi/centrodeinfancia/tests/test_encuesta_satisfaccion_modelo.py` en SQLite: 24 pasan y 3 se saltean (los de MySQL).
- El mismo archivo contra el MySQL 8.4 local, con la base de test creada desde todas las migraciones (`USE_SQLITE_FOR_TESTS=0`): 27 pasan, incluidos los triggers y la vista.
- Suite completa del vertical CDI (`pytest src/backends/cdi -n 6`, sin el build React local, como en CI): 1362 pasan; fallan los dos tests N+1 del admin de CDI (`AccesoCDI`, `NominaCentroInfancia`), que fallan igual en local sobre `development` sin este cambio.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- Migraciones 0058 y 0059 aplicadas y revertidas sobre el MySQL 8.4 local.
- `black` y `pylint` sobre los archivos tocados: sin observaciones fuera del nombre de módulo de las migraciones, que CI ignora.
- Pendiente fuera del código: confirmar con infraestructura los privilegios del migrador para crear triggers en producción y crear el usuario de solo lectura del área sobre la vista.
