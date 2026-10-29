# INET: provincia obligatoria al crear planes curriculares (#2819)

## Alcance

Pedido: agregar un selector de provincia al alta manual de planes para evitar
guardar planes que luego no aparecen al crear cursos.
Issue: [#2819](https://github.com/secretarianaf/SISOC/issues/2819).
Implementado y verificado localmente con navegador automatizado. El solicitante
autorizó publicar la rama y abrir el PR tras recibir el resultado de esa prueba;
no se presenta como un recorrido manual realizado por el usuario.

Dueño: vertical VAT/INET. Formulario compartido por las vistas Django y la API del
frontend INET. Sin modelos, migraciones, settings, dependencias de aplicación ni
permisos nuevos. **Requiere revisión técnica** por las restricciones territoriales.

## Comportamiento

- Provincia obligatoria antes del nombre, con búsqueda y opciones alfabéticas
  en el formulario Django.
- Acceso nacional: selección explícita de cualquier provincia, sin preselección.
- Una provincia completa autorizada: preseleccionada y bloqueada; el servidor
  conserva ese valor incluso si se manipula el envío.
- Varias provincias completas autorizadas: selección obligatoria entre ellas.
- Sin provincia completa autorizada ni acceso nacional: el alta no se valida;
  se indica que se debe contactar a un administrador.
- Las opciones restringidas se validan también en el servidor; el selector no
  concede permisos para crear planes.
- Al guardar se conserva la provincia validada, tanto en Django como en la API.
- Los errores conservan los datos ingresados. Un plan activo queda disponible
  para nuevos cursos de su provincia al recargar la pantalla.
- Edición y planes antiguos: se conserva la provincia existente, incluso nula.
  Este cambio no repara datos históricos ni habilita cambios de provincia.

Se mantiene el filtro provincial del selector de cursos y la compatibilidad
existente para los planes ya asociados a cursos.

## Patrón seguido y referencias

- Selector con búsqueda como `CentroAltaForm`, en
  `src/backends/vat/VAT/forms.py`.
- Alcance territorial existente: `get_full_province_scope_ids` de
  `src/backends/kernel/users/territorial_scope.py`, sin modificar el kernel.
- Acceso nacional existente: `is_vat_sse`.
- API: `src/backends/vat/VAT/api_inet_views.py`.
- Vistas: `src/backends/vat/VAT/views/catalogo.py`.
- [Manual de usuario](../../../vat/manual_usuario.md#14-planes-curriculares).

## Verificación

Tests junto al flujo existente en `src/backends/vat/VAT/tests.py` y
`src/backends/vat/tests/test_inet_api.py`: alta nacional y provincial, múltiples
provincias, falta de alcance, permisos de creación, manipulación del envío,
conservación al editar y disponibilidad de planes activos en cursos.

Validaciones locales realizadas con Python 3.11 y SQLite de tests, sin usar la
base de desarrollo:

- Selección ampliada de planes, cursos y API INET: 66 tests correctos.
- Después de extraer la configuración del campo a un método del formulario para
  resolver una observación del linter: 36 tests correctos del flujo afectado.
- Cobertura de líneas Python modificadas: 20/20 (100%), calculada con los helpers
  de `src/scripts/ci/quality_gate.py` sobre el diff local y `coverage.xml`.
- Black: cinco archivos Python sin cambios de formato pendientes.
- Pylint con `pylint_django`: 10/10 en los tres archivos de aplicación, usando
  `vat_runtime.settings` y sin persistencia de caché. La composición completa
  del linter encuentra rutas duplicadas de namespaces en Windows; se usó el
  runtime del dueño sin modificar settings del repositorio.
- Djlint: template sin cambios de formato pendientes ni errores.
- Validador de documentación: 0 referencias obsoletas o rotas.
- `git diff --check`: correcto.

La última selección se ejecutó con:

```powershell
$env:USE_SQLITE_FOR_TESTS = '1'
.venv/Scripts/python.exe -m pytest src/backends/vat/VAT/tests.py src/backends/vat/tests/test_inet_api.py -k 'alta_plan or editar_plan_conserva or plan_version_curricular or plan_estudio_create or plan_manual or curricular_plan or plans_forms' -q --tb=short --cov=VAT.forms --cov=VAT.views.catalogo --cov=VAT.api_inet_views --cov-report=xml
```

### Guía de aceptación manual

1. Abrir el alta manual con un administrador nacional: verificar el selector
   antes del nombre, búsqueda, orden alfabético y ausencia de selección inicial.
2. Intentar guardar sin provincia: debe mostrar el error y conservar los datos.
3. Crear un plan activo con una provincia y buscarlo en Nuevo curso de un centro
   de esa provincia tras recargar. No debe aparecer en otra provincia.
4. Con usuario provincial autorizado, verificar la provincia única bloqueada o
   las opciones restringidas si tiene varias provincias completas.
5. Verificar que editar un plan no permita cambiar su provincia.

### Prueba visual realizada

El primer arranque quedó bloqueado por `ModuleNotFoundError: No module named
'unfold'` en la imagen local anterior. Se resolvió reconstruyendo la imagen con
`docker compose build django`, sin cambiar dependencias del repositorio. Luego
se inició MySQL y Django con `docker compose up -d mysql django` y se completó
la preparación normal de la base local. Django respondió HTTP 200 en `/health/`.

Se usó Playwright con Microsoft Edge en modo headless sobre la aplicación real
en Docker y MySQL local. Se crearon usuarios, centros, sector, modalidad y un plan
ficticios para esta prueba. Ocho comprobaciones correctas:

1. Administrador nacional: selector con búsqueda y sin provincia preseleccionada.
2. Guardado sin provincia: muestra el error y conserva los datos ingresados.
3. El buscador permite seleccionar Buenos Aires.
4. El alta guarda el plan y abre su detalle.
5. En un centro de la misma provincia, Nuevo curso encuentra y permite
   seleccionar el plan recién creado.
6. En un centro de otra provincia, el plan no aparece en el selector.
7. En ancho móvil de 390 px, el selector es visible y no hay desbordamiento
   horizontal de la página.
8. Usuario con una provincia completa: provincia preseleccionada y bloqueada.

Se inspeccionaron las capturas de escritorio, error de validación, selector de
cursos, móvil y usuario provincial. La evidencia permanece local en
`.cache/inet-visual/`, excluida de Git. Los datos ficticios y las sesiones creadas
para esta prueba se retiraron al terminar. La aceptación humana y CI permanecen
pendientes; la prueba automatizada no se presenta como confirmación del usuario.

Entorno local disponible en
`http://localhost:8001/vat/catalogos/planes-curriculares/nuevo/`.

## Riesgo y reversión

El alta nacional, incluida la API, exige ahora enviar provincia; los consumidores
que la omitían recibirán un error de validación. El frontend INET usa el contrato
de formulario compartido. Sin cambios de esquema ni reparación de datos.
Revertir el cambio recupera el comportamiento anterior y conserva los planes
creados con provincia.
