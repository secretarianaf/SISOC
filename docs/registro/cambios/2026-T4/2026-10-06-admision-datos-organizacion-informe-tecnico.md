# 2026-10-06 - Admisión: datos de la organización en el informe técnico

Issue #2571.

## Problema

Con una admisión en curso, si se cambiaba la organización del comedor (o se
editaban los datos del legajo), el informe técnico tomaba siempre los datos de
la organización **vigente**, aunque el técnico eligiera "Continuar operando con
la Admisión actual" en el modal de resincronización:

- El formulario de un informe nuevo precargaba nombre, CUIT, mail, teléfono,
  domicilio, localidad, provincia y partido desde `comedor.organizacion`.
- En un informe ya guardado, provincia y localidad de la organización se
  pisaban con las de la organización vigente (`_configurar_selectores_geograficos`
  prioriza `field.initial`).
- "Actualizar Información desde Legajo Organización" no actualizaba los datos
  de la organización de los informes ya cargados.
- Editar solo los datos de la organización (sin cambiar tipo de entidad ni
  documentación) no mostraba el modal.

## Cambio

- `Admision.datos_organizacion_snapshot` (JSON, migración `0083`) guarda:
  - `informe`: datos con los que se precarga el informe técnico.
  - `legajo`: último estado del legajo aceptado por el técnico.
- Lógica en `admisiones/services/datos_organizacion_snapshot.py`:
  - El snapshot se inicializa al abrir la admisión y, antes de reasignar la
    organización del comedor o editar sus datos, se congela con los datos
    previos en las admisiones en curso que todavía no lo tienen (signals
    `pre_save` de `Comedor` y `Organizacion`).
  - Si los datos del legajo difieren de `legajo`, se muestra el modal de
    resincronización (título nuevo para este caso).
  - **Actualizar:** `informe` y `legajo` pasan a los datos actuales y se
    actualizan los informes técnicos de la admisión que no estén `Validado`.
  - **Continuar:** solo se mueve `legajo`; el informe conserva los datos
    anteriores.
- Los formularios de informe precargan los datos de la organización desde el
  snapshot y solo en informes nuevos; un informe guardado conserva sus valores.
- La opción A del modal y su confirmación aclaran que incluye los datos de la
  organización dentro del informe técnico.

## Trade-offs

- Los informes `Validado` no se modifican al actualizar, para no desalinear
  datos y documento ya validado.
- Las admisiones que nunca se abrieron y cuya organización cambió antes de este
  despliegue no tienen datos previos: adoptan los actuales.

## Tests

`src/backends/sisoc_core/admisiones/tests/test_datos_organizacion_snapshot.py`.
