# 2026-10-28 - CUIL de extranjeros en la validación RENAPER

## Problema

En la nómina de niños/as y de trabajadores del CDI, con DNI de extranjeros
(serie 9x.xxx.xxx, p. ej. 95445413) RENAPER informa el CUIL en `"0"` y el alta
no se podía guardar.

- **Trabajadores CDI:** la vista leía `data["cuit"]`, una clave que no existe
  (el mapeo de ciudadanos la llama `cuil_cuit`), y caía al crudo
  `datos_api["cuil"]`. Precargaba `0` y lo **bloqueaba como dato verificado**:
  `clean_cuit` lo rechazaba al guardar y no había forma de corregirlo.
- **Beneficiarios CDF:** se buscaba por el CUIL del padrón y después se pisaba
  con el `"0"` crudo de RENAPER.
- **Nómina CDI (niño/a y responsable 1):** el CUIL llegaba vacío, pero el CUIT
  es obligatorio y hay extranjeros con DNI que no tienen CUIL asignado (ANSES no
  lo da de alta automáticamente). Quedaban sin poder cargarse.

El resto de los consumidores de RENAPER (ciudadanos, comedores, importación
masiva, celiaquía, VAT, PAS, VPSL) ya usaban el CUIL mapeado o no lo usan.

## Cambios

1. `core/services/renaper.py`: `data["cuil"]` solo trae un CUIL de 11 dígitos
   con dígito verificador válido; si no, `None`. Antes solo descartaba `"0"` y
   similares. `datos_api` sigue siendo la respuesta cruda de RENAPER, sin tocar:
   se guarda como respaldo y no corresponde reescribirla.
2. Trabajadores CDI: el prefill usa `data["cuil_cuit"]` (ya validado).
3. Beneficiarios CDF: usa el CUIL validado de RENAPER y, si no hay, el del
   padrón.
4. Bloqueo RENAPER en CDI (trabajador y bloques de nómina/referente/usuario):
   un CUIT inválido no se bloquea. `field.clean` no mira el dígito verificador.
5. Casilla **"No posee CUIL"** en trabajador, niño/a y responsable 1 de la
   nómina (campos `Trabajador.sin_cuil`, `NominaCentroInfancia.sin_cuil_nino` y
   `NominaCentroInfancia.responsable_legal_1_sin_cuil`, migración
   `centrodeinfancia/0052_sin_cuil`).

## Regla de la casilla

- El CUIT sigue siendo obligatorio salvo que se marque "No posee CUIL". Así
  queda registrado que falta porque la persona no lo tiene, no por olvido.
- Marcada la casilla, el CUIT queda vacío. Casilla + CUIT cargado es un error.
- Si el CUIT vino de RENAPER (bloqueado), la persona lo tiene: la casilla queda
  deshabilitada y se guarda en `False`.
- En el detalle se muestra "No posee CUIL" en lugar del CUIT.

Se eligió una casilla explícita en lugar de volver opcional el CUIT o de
deducirlo del número de DNI (serie 9x): mantiene el control de carga y permite
filtrar después a quienes no tienen CUIL.

## Fuera de alcance

- Responsable 2 y referente del CDI: su CUIT ya es opcional.
- "Generar usuario" de CDI sigue exigiendo CUIL.
- Exportes y reportes muestran el CUIT vacío; no distinguen "No posee CUIL".

## Validación

- Tests nuevos: mapeo central (`"0"`, ceros, dígito verificador inválido),
  alta de trabajador extranjero con CUIL `"0"` de punta a punta, casilla en
  trabajador, niño/a y responsable 1, bloqueo de CUIT inválido en la nómina y
  CUIL del padrón en CDF.
- Archivos afectados (CDI trabajadores, nómina y bloques RENAPER, kernel
  RENAPER, CDF beneficiarios): 312 passed. Los 12 tests de `APIClient` en
  `kernel/tests/test_consulta_renaper_unit.py` fallan igual en `development`
  con el RENAPER simulado del entorno local; no los toca este cambio.
- `makemigrations --check`: sin cambios pendientes.
- `black`, `pylint` y `djlint` sin observaciones nuevas en los archivos tocados.
