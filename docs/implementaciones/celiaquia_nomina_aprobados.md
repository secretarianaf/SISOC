# Celiaquía: nómina de aprobados

La descarga se genera desde los legajos actuales de la base, no desde el Excel
original. Incluye beneficiarios con revisión técnica `APROBADO` y resultado
Sintys `MATCH`; los responsables puros no tienen fila propia.

## Responsables (#2829)

- Se reutilizan los vínculos de cuidador principal del grupo familiar, pero
  solo cuentan los responsables con legajo en el mismo expediente.
- Si existe responsable dentro del expediente, debe tener revisión técnica
  `APROBADO`. De lo contrario, se omite la fila de la persona a cargo,
  aunque esta tenga `APROBADO` y `MATCH`.
- Un vínculo externo se ignora: no aporta columnas de responsable ni impide
  exportar a un beneficiario independiente que cumpla las reglas existentes.
- Si hay varios responsables locales, se conserva la selección alfabética
  previa. La aprobación se exige al responsable seleccionado, sin reemplazarlo
  silenciosamente por otro que esté aprobado.
- La presencia en Sintys se acredita mediante el `MATCH` del beneficiario.
  El cruce existente usa el documento del responsable; un responsable puro
  conserva `SIN_CRUCE`. No se exige `MATCH` al responsable puro.

La disponibilidad de la descarga y el Excel aplican la misma selección. Si
no quedan filas, no se ofrece la descarga y el endpoint devuelve 404.
Se conservan columnas, formatos de fecha, orden y etiquetas de cupo.

## Implementación y alcance

La regla vive en
`src/backends/celiaquia/celiaquia/services/padron_final_service/impl.py`.
Se reutiliza `FamiliaService.obtener_responsables_por_hijo` sin modificarlo.
No cambia el cruce, la asignación de cupos, los roles ni datos almacenados.
Los cambios posteriores de revisión o vínculos se reflejan al descargar;
no se reconstruye el cruce ni se vuelve a leer el archivo Sintys.

Pruebas: `test_padron_final_export.py` y `test_flujo_e2e_celiaquia.py`, en
`src/backends/celiaquia/celiaquia/tests/`.
