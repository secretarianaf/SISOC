# CDI: validación RENAPER de responsables y referente, con identidad bloqueada

Rama `Renaper_CDI`. Sin ticket al momento de implementar.

## Pedido

En el módulo CDI, toda persona que necesite cruce con RENAPER (responsables,
referentes) tiene que validarse contra RENAPER. Los datos que trae RENAPER
quedan sin poder editarse, salvo teléfono y email, y de esos dos tiene que
quedar registrado quién los cambia.

Definiciones de producto:

1. Se bloquea solo lo que efectivamente vino de RENAPER. Los registros cargados
   a mano antes del cambio siguen editables y tienen un botón "Validar con
   RENAPER".
2. Si RENAPER no encuentra a la persona o no responde, se permite la carga
   manual (como ya pasaba en Trabajadores).
3. Datos de identidad que se bloquean: nombre, apellido, DNI, fecha de
   nacimiento, sexo, nacionalidad y CUIT/CUIL.
4. Quién editó se consulta en la pantalla de auditoría existente.

## Estado previo

- **Trabajadores** ya resolvía esto: precarga desde RENAPER y campos
  bloqueados según `Trabajador.campos_verificados_renaper`.
- **Nómina, niño/a**: consultaba RENAPER en el alta pero los campos quedaban
  editables, tanto en el alta como en la edición.
- **Nómina, responsables 1 y 2** y **referente del CDI**: carga manual.
- Auditoría: `CentroDeInfancia` ya estaba auditado completo (incluye email y
  teléfono del referente). `NominaCentroInfancia` y `Trabajador` no.

## Solución

Se generaliza el patrón de Trabajadores en un servicio por **bloque** de
persona (`centrodeinfancia/services_renaper_bloques.py`): `nino`,
`responsable_legal_1`, `responsable_legal_2` y `referente`. Cada bloque mapea
los datos de identidad a los campos del formulario.

- Botón **"Validar con RENAPER"** junto al DNI de cada bloque
  (`partials/renaper_bloque.html` + `static/custom/js/cdiRenaperBloques.js`).
  Llama a `centrodeinfancia/ajax/renaper/<bloque>/`, que devuelve los valores y
  un **token firmado** atado al usuario y al bloque.
- El form recibe el token en el POST (`renaper_token_<bloque>`). El servidor
  toma los valores **del token, no del POST**, y deja esos campos `disabled`:
  Django ignora lo que llegue para ellos, así que no se pueden alterar desde el
  navegador. Token ajeno, de otro bloque, alterado o vencido = carga manual.
- Los campos verificados se guardan en `campos_verificados_renaper`, nuevo
  `JSONField` en `CentroDeInfancia` y `NominaCentroInfancia` (migración 0049).
  En las ediciones siguientes quedan bloqueados.
- `CamposRenaperFormMixin` (en `forms.py`) aplica el bloqueo. Está en
  `NominaCentroInfanciaBaseForm`, así que también lo respeta la edición rápida
  de nómina (`nomina_centrodeinfancia_editar_ajax`), y en `CentroDeInfanciaForm`.

Alcance por pantalla:

| Pantalla | Alta | Edición |
|---|---|---|
| Nómina, niño/a | Se bloquea la identidad precargada desde RENAPER, o la de un ciudadano local ya validado | Botón para validar registros viejos |
| Nómina, responsables 1 y 2 | Botón | Botón |
| Ficha del CDI, referente | Botón | Botón |

Teléfonos (y email del referente) nunca se bloquean.

## Auditoría

`TrackedModelDefinition` admite `included_fields` (lista de campos permitidos)
además de `excluded_fields`. Se agregan:

- **Nómina CDI**: solo los teléfonos de responsables y de la persona adulta
  responsable.
- **Trabajador CDI**: solo `telefono` y `email`.

Se audita una lista acotada y no el modelo completo porque la ficha de nómina
tiene datos de salud de niños/as (discapacidad, vacunación, alergias,
antropometría) y el log de auditoría es exportable y sobrevive al borrado. Es
el mismo criterio que ya se usa para los casos de DataCalle. El referente sigue
cubierto por la auditoría completa de `CentroDeInfancia`.

## Decisiones

- **Vigencia del token: 1 hora** (Trabajadores y la precarga del niño/a usan
  15 minutos). La ficha de nómina es larga. Si vence, los datos quedan como
  carga manual y se puede volver a validar.
- **El token se ata al usuario y al bloque, no al CDI.** Certifica qué devolvió
  RENAPER para un DNI. El alta de un CDI todavía no tiene `pk`.
- **Validar al niño/a desde la edición exige el mismo DNI de la ficha.** La
  ficha ya está vinculada a un `Ciudadano`: la validación confirma la identidad,
  no la cambia.
- **Ciudadano local ya validado**: al elegirlo en el alta se bloquean DNI,
  apellido, nombre y fecha de nacimiento, que son los datos que compara la
  validación. Sexo, nacionalidad y CUIL del ciudadano pueden haberse cargado a
  mano y no se bloquean.
- **Validación "solo letras"**: no se aplica a nombres y apellidos bloqueados.
  RENAPER puede devolver signos (por ejemplo, apóstrofos) que la persona usuaria
  no podría corregir.
- **Cambio de comportamiento en el alta del niño/a**: antes, si se alteraba la
  identidad precargada, la ficha se guardaba como "manual". Ahora la alteración
  se ignora y se guarda lo de RENAPER. Se reemplazó
  `test_token_no_valida_identidad_modificada` por
  `test_alta_ignora_identidad_alterada_en_post`.

## Fuera de alcance

- **Persona adulta responsable** de la nómina: la ficha actual
  (`destinatario_form.html`) no la muestra. Solo aparece en `nomina_form.html`,
  que ninguna vista usa.
- **FormularioCDI** (referente del CDI y de la organización): no tiene campo
  DNI. Pendiente de definición.
- Validar al niño/a desde la edición no actualiza el estado RENAPER del
  `Ciudadano` vinculado.

## Validación

- `centrodeinfancia/tests/test_renaper_bloques.py`: consulta, alta, tokens
  ajenos, edición, validación de registros viejos, DNI del niño/a, edición
  rápida, referente y auditoría del teléfono.
- `centrodeinfancia/tests/test_nomina_renaper_validacion.py` ajustado al nuevo
  comportamiento.
