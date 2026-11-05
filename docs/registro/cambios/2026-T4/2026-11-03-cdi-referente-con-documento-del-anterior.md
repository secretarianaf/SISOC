# Cambio: el referente nuevo no se guarda con el DNI o el CUIL del anterior

Rama `Fix_CDI_3_11_26`. Sin ticket al momento de implementar. Continúa
`docs/registro/cambios/2026-10-20-cdi-referente-por-dni-y-renaper.md`.

## Alcance

Reporte de operación: en varios CDIs el EGP cambia el referente en la ficha y en
"Usuarios del centro" sigue figurando como responsable el usuario anterior.

Se reprodujo editando la ficha como EGP (POST real a la edición del CDI) con 18
casos, contra `origin/main` y contra `development`:

- En `origin/main` falla casi todo cambio de referente cuando la ficha no tenía
  DNI, y guardar de nuevo la ficha no corrige un CDI que ya quedó mal. Eso lo
  corrige el PR #2755, que está en `development` y `homologacion` pero todavía
  no en `main`.
- Con el código de `development` quedaba un caso: cambian nombre, apellido y
  email del referente pero dejan el DNI o el CUIL de la persona anterior. Como
  la persona se identifica por documento, se la toma como la misma: el
  responsable no cambia y, si la cuenta anterior todavía tenía la contraseña
  temporal, se le pasa el email del referente nuevo.

Implementado:

- `documentos_del_referente_anterior` en
  `src/backends/cdi/centrodeinfancia/services_user_provisioning.py`: devuelve el
  DNI y/o el CUIL que siguen con el valor anterior cuando cambiaron nombre y
  apellido. Reusa la misma regla de "otra persona por nombre" que
  `_cambio_persona_referente`.
- `CentroDeInfanciaForm._validar_documento_del_nuevo_referente` en
  `src/backends/cdi/centrodeinfancia/forms.py`: en la edición rechaza el
  guardado con el error en esos campos.

## Comportamiento

- Si en la edición del CDI cambian nombre **y** apellido del referente y el DNI
  o el CUIL siguen siendo los anteriores, la ficha no se guarda y el campo
  muestra: "Es el DNI/CUIL del referente anterior. Si cambió el referente,
  cargá el DNI/CUIL de la persona nueva."
- Corregir solo el nombre o solo el apellido (la misma persona) se guarda como
  antes.
- Completar nombre y apellido en una ficha que no los tenía no cuenta como
  cambio de persona.
- Si el nombre o el apellido nuevos no pasan la validación del formulario (por
  ejemplo, tienen números), solo se muestra ese error: sin un nombre válido no
  se puede saber si es otra persona, y no se suma el error del documento.
- El alta de CDI no cambia.
- No hay migración ni cambios en datos existentes. Un CDI que ya tiene la ficha
  con el nombre del nuevo referente y el documento del anterior queda igual
  hasta que alguien cargue el documento correcto.

## Verificación

Local, en el contenedor `django`:

- `pytest src/backends/cdi/centrodeinfancia/tests/test_automatic_user_provisioning.py src/backends/cdi/centrodeinfancia/tests/test_centrodeinfancia_form.py`:
  120 passed. Tests nuevos: documento anterior con DNI y CUIL, solo CUIL,
  cambio con documento nuevo y corrección de nombre con el mismo documento.
- `pytest -n auto src/backends/cdi src/backends/kernel/users`: los únicos fallos
  son los 2 de `test_admin_operaciones_cdi.py::test_listados_sin_n_mas_1`, que
  fallan igual sin este cambio (verificado con `git stash`).
- `black` sin cambios y `pylint` 10.00/10 en los archivos tocados.

Fix de revisión: un nombre nuevo inválido ya no suma un error engañoso en el DNI
o el CUIL. Test `test_nombre_invalido_no_suma_error_de_documento_del_anterior`;
los dos archivos de tests anteriores dan 121 passed.

Sin prueba manual en el navegador al momento de escribir este registro.
