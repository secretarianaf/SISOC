# 2026-11-27 - Encuesta de satisfacción de CDI: modelo, inmutabilidad y vista del área

## Estado
- aceptada

## Contexto
- El área del PFPI / SIMEPI especificó el instrumento 210SatisfaccionCDI (especificación v1.3 y un DDL MySQL) pensando en una tabla `CDI` de su base de procesamiento, con provincia y departamento como texto y catálogos en tablas.
- En SISOC el maestro de los CDI es el legajo (`CentroDeInfancia`), con provincia y departamento como claves foráneas y el estado Activo/Pendiente/Baja que ya existe desde #2945.
- El área pidió acceso de lectura en tiempo real a una tabla o vista SQL; si no fuera posible, la descarga desde Reportes.
- La especificación pide salas variables por CDI. En producción, al 27/11/2026, ningún CDI tiene cargada la distribución de salas del Formulario CDI, mientras que 185 de los 222 CDI tienen fichas de nómina activas con la sala cargada con las claves del formulario de nómina.

## Decision
- Las tablas de la encuesta viven en la app `centrodeinfancia` (vertical CDI), con clave foránea al legajo. Las columnas de la respuesta usan los nombres de la matriz SQL del área.
- Los catálogos (canal, sala, escala, dispositivo, estado, motivo de rechazo) son `IntegerChoices` en `encuesta_satisfaccion_schema.py`, con `CheckConstraint` en la base, en lugar de las tablas `210Cat_*` del DDL. La vista resuelve las etiquetas con `CASE`. Propuesta del agente: evita mantener en paralelo el código y las tablas de catálogo para el mismo contrato.
- La inmutabilidad (RF-19) tiene dos capas: el modelo y su `QuerySet` rechazan editar o borrar el contenido desde Django; en MySQL, dos triggers lo impiden también fuera de la aplicación. Solo se admiten la anulación lógica (irreversible) y la purga de `ip_hash`.
- El contrato de lectura con el área es la vista `v_210SatisfaccionCDI_descarga`: una fila por respuesta, con código y etiqueta, sin token, `ip_hash`, captcha ni hash de integridad, y con `fecha_carga` en hora Argentina.
- Los triggers y la vista van en una migración propia (0059), separada de las tablas (0058), porque MySQL no revierte DDL: si la creación de los triggers falla por privilegios, las tablas ya quedan registradas y la 0059 se reintenta sola.
- Las salas de la encuesta salen de las fichas de nómina activas del CDI. Los CDI sin nómina activa también aparecen en la encuesta, con la lista completa de salas. Cada respuesta guarda `sala_origen` (1 = nómina, 2 = lista completa) para que el procesamiento pueda distinguirlas.
- P13 usa el código 9 con la etiqueta «No brinda alimentación».

## Consecuencias
- El procesamiento del área lee las etiquetas de la vista sin depender de tablas de catálogo. Cambiar una etiqueta o un código pide una migración nueva y, si cambia el instrumento, una versión nueva (RF-28).
- La migración 0059 necesita los privilegios `TRIGGER` y `CREATE VIEW` para el usuario del migrador; con el binlog activo, MySQL puede pedir además `SUPER` o `log_bin_trust_function_creators = 1`. Hay que verificarlo con infraestructura antes del deploy.
- El usuario de solo lectura del área sobre la vista lo crea infraestructura; no forma parte del código.
- En SQLite los triggers y la vista no existen: los tests de esa capa corren con la marca `mysql_compat`.
- Los tests que usan `django_db(transaction=True)` sobre MySQL no pueden dejar respuestas creadas: el vaciado de tablas del test usa `DELETE`, que el trigger rechaza.
- `sala_origen` es una variable nueva respecto de la matriz de la especificación v1.3; el área tiene que incorporarla.

## Referencias
- Cambio: `docs/registro/cambios/2026-T4/2026-11-27-encuesta-satisfaccion-cdi-modelo.md`.
- Estado del CDI: #2945.
- Código: `src/backends/cdi/centrodeinfancia/encuesta_satisfaccion_schema.py`, `src/backends/cdi/centrodeinfancia/models_encuesta_satisfaccion.py`.
