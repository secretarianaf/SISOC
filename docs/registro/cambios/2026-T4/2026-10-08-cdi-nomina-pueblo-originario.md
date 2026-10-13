# 2026-10-08 - CDI Niños: no se podía guardar "Indígena" en grupo de pertenencia

## Contexto
- En el legajo de niños, marcar "Indígena, descendiente de pueblos originarios o mestizo/a/e"
  en "¿Desciende, tiene antepasados o pertenece a alguno de los siguientes grupos?" impedía
  guardar. El dato quedó sin cargar en todos los legajos.
- Causa: `destinatarioForm.js` buscaba un contenedor `#id_grupo_pertenencia`. El template de
  niños renderiza el campo con crispy, que genera `div_id_grupo_pertenencia`, así que el JS
  nunca detectaba la opción y la fila "¿Cuál?" (`pueblo_originario_cual`) quedaba oculta. El
  modelo exige ese dato cuando se marca "Indígena", por lo que el guardado fallaba con el error
  dentro de la fila oculta. En Trabajadores no pasaba porque su template arma el contenedor a
  mano.

## Cambios aplicados
- `centrodeinfancia/static/custom/js/destinatarioForm.js`: los checkboxes se buscan por
  `name="grupo_pertenencia"` en lugar del id del contenedor.
- `tests/test_destinatario_views.py`: test de regresión sobre el HTML real del alta.
- `tests/test_formularios_js_contrato.py`: test general que renderiza el alta de Niños y de
  Trabajadores y verifica que existan todos los ids que usa su JS. Con el JS anterior falla.

## Riesgos y rollback
- Solo JS y tests; sin cambios de modelo ni de datos. Rollback: revertir el commit.
- Los legajos guardados sin el dato no se recuperan: hay que volver a cargarlo.
