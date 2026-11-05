# Cambio: entrada HTML protegida para la vista previa React de Insumos (#2785)

## Alcance

Se agregan rutas propias de `insumos` para las entradas HTML de listado, alta,
edición y eliminación de la vista previa INS-A bajo `/v2/sisoc/insumos`. La
composición de URLs de `config` incluye estas rutas antes de la ruta genérica de
Front V2. No se cambian las URLs Django existentes, el proxy del kernel, los
upstreams predeterminados ni la activación global de SISOC.

La vista delega en `core.v2_frontend.frontend_v2` y reutiliza
`permissions_any_required` con los mismos permisos de acción que
`insumos.urls`: `view_insumo`, `add_insumo`, `change_insumo` y `delete_insumo`.

## Comportamiento

Las entradas HTML seleccionadas conservan el `403` para usuarios anónimos y
para sesiones sin el permiso de esa acción. Con el permiso correspondiente, la
vista previa reenvía solamente `GET` y `HEAD` al proxy existente. Las rutas con
y sin barra final se admiten para conservar los enlaces actuales de la vista
previa; otros recursos de SISOC y las descargas permanecen bajo el enrutamiento
genérico existente.

Los métodos no permitidos responden `405` sin consultar el upstream ni ejecutar
acciones de negocio.

## Verificación

- RED observado contra la composición raíz: las entradas anónimas caían en el
  `302` del proxy genérico en vez del `403` requerido. Los tests nuevos
  confirmaron además que no se consultaba el upstream antes de autorizar.
- GREEN: `python -m pytest
  src/backends/sisoc_core/insumos/tests/test_preview_entry.py
  src/backends/sisoc_core/insumos/tests/test_insumos_permisos.py
  src/backends/kernel/core/tests/test_v2_frontend.py -q -p no:cacheprovider`:
  42 pruebas pasaron en el runner aislado con SQLite y sin red.
- Black (`--check`) pasó para los cuatro archivos Python modificados; Pylint
  calificó esos archivos con 10.00/10.
- `python src/scripts/ci/check_docs_paths.py --existencia
  docs/registro/cambios/2026-T4/2026-11-02-2785-entrada-react-insumos.md`:
  87 documentos vigentes; ninguna referencia rota.
- La configuración HEAD de `XViewMiddleware` intercepta solicitudes con IP
  interna antes de la vista y devuelve un `200` vacío sin llamar al proxy. No se
  modificó el middleware compartido; las pruebas de permiso HEAD usan una IP
  sintética externa para alcanzar la vista.
- No se afirma activación pública ni aceptación humana. La prueba de navegador local posterior se detalla a continuación.

Riesgo: items 2/3/5 (permisos, precedencia de rutas compartidas y proxy). Requiere
revisión técnica.

## Verificación integrada posterior

- Verificación independiente: 42 pruebas del conjunto original y 33 probes independientes aprobaron; doce comparaciones de rutas adyacentes contra la base conservaron estado, cuerpo y cabeceras seleccionadas. El hash del volcado SQLite no cambió ante rechazos y no hubo llamada al upstream sin autorización. La comprobación del padre repitió las 42 pruebas con resultado satisfactorio.
- Chromium accedió realmente a Django, que reenviaba al bundle de producción final mediante un servidor estático dentro del mismo contenedor. El harness temporal solo permitió el salto exacto de loopback a ese servidor; no se abrió Vite a la red ni se modificaron settings del repositorio. El origen publicado fue únicamente 127.0.0.1.
- Anónimo y usuario sin permiso recibieron 403 del template fuente; usuarios de alta, edición y baja sin View alcanzaron su formulario y metadata API 200. Alta sin permiso de edición recibió 403 al intentar editar. Las entradas genéricas de VPSL, Celiaquía y otras rutas mantuvieron 302 de login. HEAD anónimo en navegador devolvió 403; la salvedad previa de IP interna sigue vigente.
- Fixture nueva preparada desde el manifiesto aprobado: un programa, tres categorías, 25 insumos y 24 archivos sintéticos. No se enviaron mutaciones. Las 572 solicitudes de assets externos se satisficieron desde la caché existente, verificando hash y tamaño; no hubo destinos desconocidos. Los dos contenedores de esta prueba se detuvieron; los runtimes anteriores se conservaron.
- Esta prueba cierra la entrada local, no la matriz visual completa, CI, despliegue ni aceptación humana.
