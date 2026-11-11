# Cambio: tope de tiempo en la búsqueda RENAPER por DNI (#2889)

## Alcance

El 06/11, `/centrodeinfancia/<id>/nomina/crear/` respondió 504 61 veces. Ese día se dieron de alta 44 nóminas, frente a un promedio de 95 diarias en las dos semanas anteriores. En la base de PRD no hay ciudadanos validados por RENAPER desde el 27/10.

Cuando el DNI no está en la base, la búsqueda consultaba RENAPER probando con M, F y X. Cada intento hacía su propio login, y cada request podía esperar hasta `RENAPER_REQUEST_TIMEOUT_SECONDS` (10 s). Con RENAPER lento, la vista superaba el corte de 25 s del proxy del core y el usuario recibía 504 sin poder seguir.

Rutas:

- `src/backends/kernel/core/integrations/renaper.py`: `APIClient` acepta `deadline` y recorta el timeout de cada request al tiempo que le queda.
- `src/backends/kernel/ciudadanos/api.py`: `_consultar_por_dni` usa un solo cliente, con `reuse_token=True`, y un tope total de `PRESUPUESTO_CONSULTA_RENAPER_SEGUNDOS = 15`.
- `src/backends/cdi/centrodeinfancia/views.py`: el aviso de RENAPER en las altas de nómina y de trabajador agrega «Podés continuar con la carga manual.»

## Comportamiento

- Una búsqueda por DNI hace un login y, como mucho, tres consultas, y nunca supera unos 15 s en total. Si RENAPER no contesta a tiempo, devuelve «RENAPER no respondió a tiempo…», en lugar de dejar la vista colgada hasta el 504.
- En CDI, el formulario manual queda disponible con el DNI cargado, como ya pasaba cuando RENAPER fallaba rápido. La ficha se guarda como `manual`, sin validación RENAPER.
- `_consultar_por_dni` es compartida: el tope también aplica a las otras vistas que buscan por DNI con `ciudadanos.api` (ciudadanos del core, VPSL y los bloques RENAPER de CDI). Comedores usa su propia consulta y no cambia.
- Sin `deadline`, `APIClient` se comporta igual que antes; las importaciones y validaciones masivas no cambian.

Este cambio no arregla RENAPER en PRD. Que no haya validaciones desde el 27/10 es un problema aparte de la integración o de la cuenta con el proveedor.

## Verificación

Validado en local, con SQLite y dobles HTTP:

- Tests nuevos en `src/backends/kernel/tests/test_consulta_renaper_unit.py`, `src/backends/kernel/tests/test_ciudadanos_renaper_api_unit.py` y `src/backends/cdi/centrodeinfancia/tests/test_nomina_renaper_validacion.py`. Con el código anterior fallan 6 de los 7 nuevos; el que pasa verifica que un timeout corte los intentos, algo que ya ocurría.
- Se ajustó `src/backends/vpsl/ver_para_ser_libre/tests/test_workflow.py`, que fijaba los argumentos exactos de `consultar_datos_renaper` y ahora recibe también `client`.
- Suites: CDI, 910 pasan y 2 fallan; VPSL, 169 pasan y 2 fallan; tests de RENAPER y ciudadanos de `kernel`, 169 pasan. Los 4 fallos son `test_listados_sin_n_mas_1` del admin de CDI y VPSL, y con el código de `HEAD` fallan igual. La suite completa de `kernel` no se pudo correr en local porque el contenedor se queda sin memoria.
- `pylint` reporta `too-many-return-statements` en `APIClient.consultar_ciudadano`, igual que con el código anterior.

Sin verificar: el comportamiento con el RENAPER real de PRD.
