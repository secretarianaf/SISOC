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
  `JSONField` en `CentroDeInfancia` y `NominaCentroInfancia` (migración 0050).
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

## Experiencia de usuario: primero el DNI

Producto eligió que cada persona arranque pidiendo solo el documento. Cada
bloque tiene cuatro estados (`partials/renaper_bloque.html` +
`static/custom/js/cdiRenaperBloques.js`):

| Estado | Qué se ve |
|---|---|
| Agregar | Solo "Agregar responsable 2" (bloque opcional sin usar) |
| DNI | Tipo de documento + DNI + "Validar con RENAPER". Enter en el DNI valida. "Cargar manualmente" aparece solo si RENAPER no encuentra a la persona o no responde |
| Verificado | Tarjeta de solo lectura con la identidad + los campos a completar (teléfono, email, relación, nivel educativo, consentimiento) |
| Manual | Todos los campos editables, con "Validar con RENAPER" disponible |

- El estado inicial lo calcula el form (`modos_renaper`): verificado si tiene
  datos de RENAPER; manual si ya hay identidad cargada a mano (registros
  previos o un POST con errores) o el documento no es un DNI; si no, DNI.
- Elegir un tipo de documento sin DNI pasa el bloque a carga manual.
- **"Cambiar persona"** en la tarjeta (responsables y referente; no en el
  niño/a): libera solo el DNI y, al validar a la persona nueva, reemplaza la
  verificación anterior. Un dato que la persona nueva no trae de RENAPER deja de
  estar bloqueado y se completa a mano (no se conserva el de la anterior).
  Una persona ya guardada como verificada solo se reemplaza validando a otra:
  la carga manual no aplica.
- La carga manual no es un atajo: se ofrece recién cuando RENAPER falla, o
  directamente si el tipo de documento no es un DNI. Si se intenta guardar con
  una persona todavía en el paso del DNI, el bloque avisa y lleva el foco al DNI
  en lugar de abrir la carga manual.
- Sin JS se ven todos los campos, como una carga manual.
- No se muestra la fecha de verificación (definición de producto: por ahora no).

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

- `backends/cdi/centrodeinfancia/tests/test_renaper_bloques.py`: consulta, alta, tokens
  ajenos, edición, validación de registros viejos, DNI del niño/a, edición
  rápida, referente, auditoría del teléfono, estado inicial de cada bloque y
  cambio de persona.
- `backends/cdi/centrodeinfancia/tests/test_nomina_renaper_validacion.py` ajustado al nuevo
  comportamiento.
