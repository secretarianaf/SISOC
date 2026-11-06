# Hotfix: error 500 en Papelera y al eliminar dispositivos

Rama `hotfix/papelera-y-eliminar-dispositivo`, desde `main`.

## Síntoma

En producción respondían 500:

- `/papelera/` (core), para cualquier superadmin.
- `/dispositivos/<pk>/eliminar` (backend de Dispositivos), al confirmar la eliminación.

## Causa

- **Papelera:** `iter_soft_delete_models()` (`core/soft_delete/registry.py`) llamaba a
  `apps.get_model()` sobre todas las claves de `SOFT_DELETE_MODEL_KEYS`. Desde la
  modularización, cada proceso desplegado instala solo sus apps
  (`config/backends.json`): en el core no están `admisiones`, `comedores`, etc., y
  `get_model()` lanza `LookupError` (no devuelve `None`). Los tests no lo detectaban
  porque corren con `config.settings_all`, que instala todas las apps.
- **Eliminar dispositivo:** el borrado es físico y `datacalle.Relevamiento.dispositivo`
  usa `on_delete=PROTECT`. Si el dispositivo tiene relevamientos, Django lanza
  `ProtectedError`, que la vista no manejaba.

## Solución

- La papelera omite los modelos cuyas apps no están instaladas en el proceso. En el
  core muestra solo los modelos del kernel (ciudadanos, organizaciones).
- `DispositivoDeleteView` captura `ProtectedError`, conserva el dispositivo y vuelve
  al detalle con el mensaje: "No se puede eliminar el dispositivo porque tiene
  relevamientos de Datacalle asociados."

## Verificación

- Tests nuevos: `kernel/core/tests/test_soft_delete_registry.py` (simula el core con
  `override_settings(INSTALLED_APPS=...)`) y
  `test_eliminar_dispositivo_con_relevamientos_no_falla_y_lo_conserva`. Ambos fallaban
  antes del fix (`LookupError` / `ProtectedError`).
- Suites de papelera, kernel y dispositivos en verde.
- No se verificó contra los logs de producción: el diagnóstico sale del código.

## Limitaciones

- Desde el core, la papelera no lista los registros borrados de modelos que viven en
  otros backends (comedores, CDI, CDF, celiaquía…). Para eso hace falta una papelera
  por backend o una consulta agregada; se sigue en #2864.
- Un dispositivo con relevamientos sigue sin poder eliminarse; ahora lo informa con un
  mensaje en lugar de fallar.

## Integración en `development`

En `development`, la parte del dispositivo ya estaba resuelta por #2750, con un mensaje
genérico que lista los registros asociados. El cherry-pick conserva esa versión y solo
trae el fix de la papelera.
