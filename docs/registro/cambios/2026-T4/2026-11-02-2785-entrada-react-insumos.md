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

## Verificación histórica INS-A

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


## Extensión backend INS-B (2026-11-05)

Se agregan las cuatro entradas de categorías del contrato existente: listado,
alta, edición y eliminación. Cada ruta conserva su slash y permiso de acción
propio, reutilizando el decorador y proxy ya incorporados; no cambia el mount
raíz, los upstreams, el proxy ni las rutas Django de aplicación.

Esta unidad acredita únicamente el routing y la autorización antes del proxy.
El upstream de las pruebas es un mock explícito: no demuestra un frontend real,
recuperación visual pendiente, activación global o aceptación de interfaz.
La configuración interna HEAD de admindocs permanece como en el baseline;
las guardas HEAD de la vista se verifican con IP externa, sin afirmar semántica
JSON de API para estas entradas HTML. Los diagnósticos no contienen UI privada.

La verificación aislada actual pasa: 65 pruebas de entradas preview, permisos
nativos y proxy kernel; Black en dos Python, Pylint y referencias documentales.
Persisten siete avisos previos. Se usó la imagen local fijada sin red, código
de solo lectura y datos sintéticos; todos los upstreams se simularon.

El RED inicial incluía cuatro fallos de configuración del test HEAD autorizado:
faltaba el override de upstream explícito que usan las pruebas existentes.
Corregido solo ese fixture antes del código de rutas, el RED focalizado observó
ocho denegaciones fallidas y cuatro casos autorizados correctos. Las pruebas
previas también observaron ocho fallos GET de denegación. Tras añadir las
cuatro rutas, las guardas de acción se verifican antes del proxy.

La comprobación independiente pasa 24 GET/HEAD externos de categorías y 24 HEAD
internos baseline/candidato. Veinte controles existentes por árbol conservan
estado, longitud, cabeceras, proxy y sesión. Dos hashes de cuerpos403 exigieron
una comprobación adicional autorizada: ocho GET reprodujeron únicamente ocho
apariciones de nonce CSP y dos tokens CSRF por respuesta, validados contra la
petición; todo el contenido restante coincide por rol entre repeticiones y
baseline/candidato. No se enmascararon diferencias sin explicar ni se cambió
la aplicación. Solo se conservaron evidencias saneadas, nunca valores secretos
ni cuerpos crudos. Los cuerpos originales no retenidos no se reconstruyeron;
esta conclusión corresponde a la reproducción controlada posterior.

No se repitieron las guardas ya aprobadas ni la suite durante esa recuperación.
Sesiones, datos sintéticos y archivos protegidos permanecen intactos. El modo
100755 de `config/urls.py` no cambió. Requiere revisión técnica por controlar
permisos antes de reenviar al proxy; no acredita un frontend vivo, paridad
visual, aceptación humana, CI ni despliegue.
