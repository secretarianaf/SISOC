# Cambio: variables de IF del último Informe Técnico para templates de renovación

## Alcance

Se pidió poder citar en los templates de Informe Técnico el IF del último informe técnico del comedor (el anterior al trámite en gestión) y un dato que cambie según si hubo Informe Técnico Complementario que modificó prestaciones.

Se agregaron dos variables documentales, calculadas sin persistir copias:

- `src/backends/comedores/admisiones/services/informe_tecnico_variables_service.py`: cálculo de las variables.
- `src/backends/comedores/admisiones/migrations/0084_variables_if_ultimo_informe_tecnico.py`: migración de datos que las registra en el catálogo del gestor de templates (mismo patrón que la `0079`). No cambia el esquema.

## Comportamiento

- `{{ informe.if_ultimo_informe_tecnico }}` (categoría "Renovaciones - antecedentes"): `numero_if_tecnico` de la admisión anterior más reciente del mismo comedor que lo tenga cargado. Usa el mismo criterio de antecedentes que `expediente_ultimo_convenio`: excluye la admisión actual, las posteriores y las descartadas o inactivadas.
- `{{ informe.if_referencia_prestaciones }}` (categoría "Renovaciones - Informe Complementario"): si la admisión indica "¿Se realizó Informe Complementario para modificar prestaciones?" = Sí, devuelve el "IF IT Complementario" cargado en el informe; si es No o está vacío, devuelve el IF del último Informe Técnico.
- Sin dato disponible, ambas variables quedan vacías. Los templates existentes no cambian.

## Verificación

En el entorno local (`docker compose`):

- `pytest` de `src/backends/comedores/admisiones/tests`, `src/backends/kernel/tests/test_informes_complementarios_templates.py` y `src/backends/comedores/tests/test_admisiones_gde_informe_sync_db.py`: 163 pasan, 5 de ellos nuevos en `src/backends/comedores/admisiones/tests/test_variables_documentales_renovacion.py`.
- `makemigrations --check --dry-run`: sin cambios pendientes. Migración aplicada en la base local.
- `black` sin cambios; `pylint` solo reporta el nombre de módulo de la migración, común a todas las migraciones.

Pendiente: verificación visual en el gestor de templates y en un documento generado, por parte de quien pidió el cambio.
