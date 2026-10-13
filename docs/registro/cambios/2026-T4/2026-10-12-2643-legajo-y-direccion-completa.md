# Seguimientos sin tocar el legajo y dirección completa en la API territorial (#2643, feedback de QA)

Dos observaciones de QA sobre el #2643 (8 y 9/10), después del PR #2662.

## 1. Solo el relevamiento inicial actualiza el legajo del comedor

Regla funcional (jcamiloparra, 8/10): la información de los seguimientos no
debe actualizar el legajo del comedor; solo el relevamiento inicial lo hace.

Hasta ahora, `PATCH /api/relevamiento/primer-seguimiento` aceptaba un bloque
`comedor` (N19.8) y lo aplicaba con `RelevamientoService.update_comedor`: el
domicilio cargado en un seguimiento pisaba la ficha. La app lo mandaba en cada
envío.

Ahora `PrimerSeguimientoSerializer._process_comedor` descarta el bloque sin
aplicarlo. Se sigue aceptando porque las versiones anteriores de la app lo
mandan; el resto del PATCH se procesa igual. El bloque `comedor` de
`PATCH /api/relevamiento` (inicial) no cambia. PNUD y actas ya no tocaban el
legajo.

El bloque `referente` tampoco modifica un referente vinculado al legajo de
ningún comedor. Si el DNI resuelve uno de esos registros y llegan datos de la
visita, se guarda una copia para el seguimiento, conservando los campos no
enviados. La relación del comedor y el referente original quedan intactos;
los reenvíos por DNI reutilizan la copia si sigue sin estar vinculada a un legajo.

Del lado de la app (`secretarianaf/Gestionar`, 1.1.60) el seguimiento deja de
mandar el bloque: el domicilio se muestra y sale en el PDF, pero no viaja.

## 2. Dirección completa en la API territorial

QA (FacuDrudkh, 9/10): el Form II A (PNUD) no precargaba entre calles,
manzana, lote, piso ni departamento. La API territorial no exponía
`piso`, `departamento`, `manzana`, `lote` ni `partido`, y la app tampoco los
mapeaba.

`TerritorialComedorSerializer` (listado asignado y detalle) y
`TerritorialComedorZonaSerializer` (comedores de la zona sin asignación, desde
donde también se activan altas) exponen ahora esos campos; la zona además
`entre_calle_1/2` y `codigo_postal`, que tampoco tenía. Son los mismos campos
del modelo `Comedor`; todos `allow_null`.

## Tests

- `tests/test_2643_legajo_y_direccion.py`: el PATCH con bloque `comedor` no
  cambia el comedor; el detalle y la zona exponen la dirección completa.
- `tests/test_huecos_seguimiento_n19.py`: el test del punto 8 de N19 ahora
  asegura lo contrario de lo que aseguraba (el bloque se acepta y no se aplica).
- Regresión del referente compartido en ambos PATCH de seguimiento: conserva
  el legajo propio o de otro comedor, los campos omitidos y una sola copia
  durante el reenvío.

Validación de la corrección del referente (13/10): los cuatro casos HTTP fallan
con el método anterior; las tres suites focales pasan con la corrección
(54 tests, SQLite en memoria). Black, Pylint con el plugin Django y el check de
rutas de documentación pasan. No se verificó la app ni MySQL localmente.
