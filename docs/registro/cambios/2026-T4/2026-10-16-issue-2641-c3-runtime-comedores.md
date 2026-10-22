# #2641 C3: runtime de Comedores y selección de procesos

Estado: **C3 implementado y validado localmente; sin incorporación ni deploy**.
El responsable pidió continuar el desarrollo el 2026-10-16 después de la entrega
C2. No habilita commit, push, merge, cierre de issues, deploy ni acciones sobre
entornos existentes. #2725 sigue postergado; DB, storage y migrador compartidos.
Rama `juanikitro/Migracion`, base `1cede84d2b3490f2ddb6bf933852408d9fd68bc7`.

## Implementación

Se trasladan de `src/backends/sisoc_core/` a `src/backends/comedores/` las catorce
apps aprobadas: comedores, gestion_organizaciones, duplas, admisiones,
intervenciones, historial, acompanamientos, expedientespagos, relevamientos,
rendicioncuentasfinal, rendicioncuentasmensual, importarexpediente, comunicados y
pwa. Se conservan nombres importables, AppConfig, labels, tablas, migraciones,
ContentTypes, permisos y recursos binarios. Espacios comunitarios conserva `pwa`.

El portal conserva Usuarios, Dashboard, Encuestas, Insumos y OCR. El runtime
`comedores_runtime` reutiliza `config.backend_settings.aplicar` y
`config.backend_urls.urlpatterns_de_backend`. No instala apps del portal ni de
los otros backends. La composición completa y el migrador descubren el nuevo
dueño desde `config/backends.json`, sin duplicar apps.

Las rutas públicas conservan sus paths/nombres. El registro declara los prefijos
específicos de negocio, APIs, AJAX y admins; no captura `/`, `ajax/`, `admin/`,
login ni API de Usuarios en forma indiscriminada. Los contratos C1 en
`/interno/usuarios/` y `/interno/espacios/` existen sólo en el dueño y en la
composición completa: no se agregan como prefijos del proxy público.
La excepción legacy `/admin/pwa/auditoriasesionpwa/` queda antes del proxy en
portal, preservando el redirect a audittrail y sus restricciones C1.

El admin real se monta solamente en el runtime del dueño; `backend_urlpatterns`
no duplica el namespace admin cuando settings_all monta el admin completo.
Montos conserva `/admin/core/montoprestacionprograma/`, permisos `core.*` y
modelo kernel. El índice del portal ofrece `admin_links` del registro, filtrados
por permisos, sin instalar modelos remotos. El dueño vuelve a autorizar cada
petición: el enlace no sustituye sus permisos, sesión ni CSRF.

La fachada Python transitoria `usuarios/api.py` no tenía callers runtime y
reexportaba PWA, reintroduciendo el dominio en el portal. Se retira; los
consumidores ya usan `pwa.api` desde C0. No se retira una ruta HTTP pública.
Los cuatro contratos C3 prohíben imports entre Comedores, portal y otros
backends; no se añaden excepciones.

Los 111 tests exclusivos del dominio, clasificación y el JS de Informe Técnico
pasan a `src/backends/comedores/tests/`. Las integraciones transversales siguen
en portal/kernel. Se ajustan rutas literales y los tests de DOCX resuelven por
AppConfig. pytest agrega la raíz Comedores; pylint/CI de arquitectura ya la
descubren automáticamente. CI de imágenes usa las cinco apps actuales del portal
para comprobar que ninguna imagen web de backend las contiene.

Compose prepara `backend_comedores` con target backend, sin puertos publicados
y con media/static/logs compartidos. Mailing reutiliza esa imagen y su settings;
su command explicita entrypoint para no heredar Gunicorn. No cambia el número de
workers existentes ni sus nombres de comandos. Migrador y collectstatic siguen
siendo únicos y de grafo completo.

El selector incluye mailing e importación como `extra_services` de Comedores,
y el importador en todos los demás backends por contener su código.
`@core` también incluye el rol existente `user_import_worker`: debe recibir
cambios de Usuarios aunque use otra imagen. OCR, importación de ciudadanos y
credenciales permanecen en core. El primer corte requiere deploy completo por
config/registro/Docker; sólo los cambios futuros propios de Comedores podrán ser
selectivos. El selector y los dry-runs no demuestran un deploy real.

## Decisión aprobada del importador

El responsable eligió «2» el 2026-10-16: reutilizar la imagen completa del
migrador. Se aplica `sisoc/migrator`, target migrator, `config.settings_all` y
rol explícito `user_import_worker` en el servicio existente. El rol evita
migraciones, collectstatic y servidor HTTP. No se agrega target, settings,
worker ni dependencias. DB/storage/migrador continúan compartidos.

El costo aceptado es cargar todas las verticales/señales y actualizar el worker
ante cambios de cualquiera de ellas. Todos los backends lo declaran como
`extra_services`; `@core` lo selecciona por su rol. La resolución final contra
Compose deduplica y omite sólo mailing/importación si no están definidos en el
entorno. Otros servicios ausentes, incluso Celery de PAS, fuerzan el fallback
completo; no se oculta una configuración incompleta. No se imprime el JSON de
Compose con variables. Se agregan negativos de selección y dry-runs de Bash.

ADR con alternativa, consecuencias y condiciones de revisión:
`docs/registro/decisiones/2026-10-16-c3-worker-importacion-imagen-migrador.md`.
No se atribuye al responsable una motivación adicional a su elección.

## Validación y evidencia

Scratch: `C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.
Fuentes de tests RO; MySQL 8.4 tmpfs y red interna sin puertos, sin .env, dumps ni
servicios existentes. Correos locmem e integración GESTIONAR desactivada.

- `c3-before-manifest.json` / `c3-before.zip`: snapshot previo. Verificación de
  las 143 rutas combinadas C0+C1+C2 sin diferencias al iniciar. El backup C2 y el
  inicial no se sobrescriben.
- `c3-preservation.json`: 134 de las 143 rutas anteriores mantienen exactamente
  su contenido/ausencia, considerando movimientos; nueve cruces intencionales
  son contratos/docs, settings/URLs/registro y retiro de la fachada transitoria.
  Otros 700 archivos trackeados del cluster conservan su blob; sólo se ajustan
  tres archivos de tests/scripts por rutas/comentarios. Binarios sin cambios.
- `c3-imports.log`: **30 contratos conservados, cero rotos**, más el contrato
  separado de configuración Celiaquía conservado.
- `c3-pylint.log` y `c3-pylint-selector.log`: siete Python de runtime/selector,
  **10/10**. `c3-black.log`: 17 Python editados, sin formateo del cluster completo.
  `c3-migration-drift.log`: **No changes detected**.
- `c3-image-{core,comedores}-probe.log`: arranque y checks con código físicamente
  separado; ausencia real de módulos del otro dueño y admin de Montos en dueño.
- Los builds offline reutilizan `sisoc2641c0-137b6c50:checks` como base y ejecutan
  las etapas de copia del Dockerfile de producción sin red. IDs iniciales:
  core `sha256:789e8e7e49bc16043cf0921b8801bc95a42ddd3708192db3c896083aa68acb94`,
  Comedores `sha256:27fd624277f7678fb1d1bfbeed8cd25ff1beba447ef62d80bec421242cf7f789`.
  El build completo sin red no tuvo cache para APT y falló resolviendo Debian.
  No se declara reconstruida la base de producción ni ejecutado CI.
- `c3-http.log` / `c3-http-commands.json`: las dos imágenes sin montaje de código,
  conectadas a MySQL sintético, verifican login/sesión, favoritos, navegación y
  ModelAdmins remotos, redirect legacy, rechazo CSRF sin escritura y alta de
  Montos con Historial. Al detener el dueño, portal/login/salud siguen disponibles
  y la ruta de negocio devuelve 503. Los dos procesos HTTP se retiran al terminar.
- La primera regresión tuvo 323 aprobados y ocho fallos de fixtures: dos rutas
  DOCX antiguas y seis tests con URLconf cacheado sin proxy. Se corrigieron los
  fixtures, sin alterar código runtime para ocultar fallos; el bloque de
  correcciones pasó 16/16. La regresión final en `c3-tests.log` y comando en `c3-tests-command.json`
  pasó **333/333**, ocho warnings existentes, 128.83 s. Incluye los 280 casos C2
  más rutas/arranque C3 y selector/dry-runs, sin sumar corridas como tests únicos.
- `c3-routes-owner-sqlite-probe.log`: el probe existente recorre todas las rutas
  propias sin argumentos del dueño, autenticado, sin respuestas 500. Usa SQLite
  privado, sin migraciones: no sustituye la regresión MySQL ni el HTTP entre
  imágenes. Su primer intento heredó OPTIONS MySQL al cambiar engine y falló por
  charset; se ejecutó con USE_SQLITE_FOR_TESTS=true, sin modificar runtime.
  `c3-mailing-command.log`: el comando real de mailing está disponible en la
  imagen aislada del dueño; no se ejecutó una cola ni envío de correo.
- `c3-docs.log`: sólo las dos referencias obsoletas preexistentes (SIMEPI y script
  de fronts). Este control sigue sin aprobarse. No se reescriben registros históricos.

### Validación final después de la elección 2

- `c3-final-runtime-tests.log` y `c3-final-tests-command.json`: **375 passed**, ocho
  warnings existentes, 214.96 s. Regresión focalizada C0–C3: contratos HTTP,
  sesión/CSRF, rutas, admin, importador y selector con negativos/dry-runs.
- `c3-worker-image-tests.log`: **2 passed**, tres warnings, 336.61 s, dentro de la
  imagen migrator sin montar fuentes. Un XLSX real de prueba confirma usuario,
  acceso y checkpoint en la misma transacción; un fallo inyectado en el checkpoint
  revierte las tres escrituras. Se usa exclusivamente MySQL sintético.
- Los dos fixtures HTTP C1/C2 ahora arrancan `comedores_runtime.settings`, el dueño
  efectivo C3, en vez del grafo completo. Conservan todas las aserciones y el límite
  de arranque de 30 s. READY medido: 11.916, 14.747 y 16.868 s. Las corridas anteriores
  con uno/dos errores de arranque se conservan en `c3-final-tests.log` y
  `c3-final-tests-recheck.log`. No cambian timeouts ni política de errores runtime.
  `c3-final-image-tests.log` conserva además dos fallos del inventario de fronts:
  ese checkout no forma parte de la imagen backend; ambos pasan en la corrida de
  fuentes final. No se presenta esa corrida de imagen como aprobada.
- `c3-final-black.log`: **21 Python sin cambios pendientes de formato**. Pylint
  de runtime/selector y los dos módulos del worker: **10/10**, según
  `c3-pylint.log`, `c3-pylint-selector.log` y `c3-worker-pylint.log`.
  Se conservan los resultados de 30 contratos más uno de Celiaquía y ausencia
  de drift de migraciones. `c3-js.log`: JS de Informe Técnico aprobado.
- `c3-worker-yaml.log`: Compose/CI y selección coherentes con imagen migrator,
  rol explícito, preparación DB deshabilitada y worker extra en los nueve backends.
  `c3-resource-precedence.json`: cero colisiones de templates/static entre las
  36 apps propias inventariadas. `c3-collectstatic.log`: 456 archivos copiados
  en contenedor efímero con storage de desarrollo, sin escribir static real.
- `c3-final-build-{core,comedores,migrator}.log`: etapas de producción con base
  local reutilizada. IDs finales: core
  `sha256:9abfec7fee1cfde5fb289e15042458ad2d7e08451592db659f07138f385a1b71`,
  Comedores `sha256:e72e2b9a69480b5a4f0f978c1d6ec9ec8242c2dd10bbd68eb60520ea0a1b4edf`,
  migrator `sha256:5d0d5d36529a0caafb3f922b06cff45f4a636102d8e7828837d6af30b07dd983`.
  No es reconstrucción completa de Debian/dependencias ni build de un commit.
- `c3-update-rollback.log` / `c3-update-rollback-states.json`: actualización y
  rollback de las imágenes del dueño y del worker, conservando exactamente ID y
  StartedAt del portal. Se confirma el proceso real del importador sin Gunicorn,
  HTTP con sesión/CSRF/admin/favoritos/Montos y lectura de datos tras revertir.
  Las imágenes previas son snapshots locales C3, no versiones desplegadas.
- `c3-final-preservation.json`: **131/143** entradas previas idénticas considerando
  movimientos; doce cruces deliberados: los nueve iniciales, nota de continuación
  del ADR C2 y adaptación de los dos fixtures HTTP. Otros 700 archivos del cluster
  mantienen su blob; los tres ajustes de tests/scripts y binarios siguen iguales
  a lo ya documentado. No se descartan C0+C1+C2.

No se ejecutan suite completa, CI, smoke en QA/HML/PRD, promoción, deploy ni
prueba de uptime de servicios existentes. Tampoco se valida collectstatic con
storage de producción ni envío real de mailing. Los probes locales no acreditan
esos resultados. El control documental sigue con las dos referencias anteriores.

## Riesgos, reversa y estado humano

C3 no cambia esquema ni elimina ContentTypes; no ejecutar remove_stale_contenttypes.
Rollback de este corte requiere coordinar imágenes, registro, rutas y Compose,
conservando la DB y las migraciones anteriores. C1 conserva sus precauciones de
metadata y permisos; no revertirlas automáticamente al revertir una imagen.

La extracción conserva la dependencia de DB/storage/migrador y del portal de
entrada. Montos y el admin del dominio pierden disponibilidad con Comedores,
según la decisión C2. Se prueban fallbacks, sin prometer independencia total.

La comprensión humana y aceptación funcional manual no se consideran validadas.
Se reutilizan la revisión delegada y los ejercicios declinados en la sesión
previa; no se impone otro examen. Skills: brainstorming para separar la decisión
material pendiente del diseño ya aprobado; systematic-debugging para identificar
causas de fallos de build/fixtures antes de corregirlos. Revisión propia focalizada
contra el snapshot; no se atribuye revisión externa de Claude ni aceptación humana.

El ensayo final retiró los tres contenedores sintéticos portal/dueño/worker,
con evidencia en su log. Al cerrar, Docker Desktop dejó de responder (pipe del
daemon ausente); no se lo reinicia ni se afirma haber retirado MySQL/red de ese
último ensayo. Cuando Docker vuelva a estar disponible, verificar y retirar sólo
el proyecto aislado `sisoc2641c0-137b6c50`, mediante:
`docker compose --env-file NUL -f C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/compose.yml -p sisoc2641c0-137b6c50 down --volumes --remove-orphans`.

Se conservan imágenes, logs y los backups anteriores sin sobrescribirlos. El
respaldo final es `c3-final-manifest.json` / `c3-final.zip`, más
`c0-c1-c2-c3-final.patch` (el patch solo no incluye archivos untracked).
`git diff --check` final pasó. No se tocó ningún entorno existente ni se inicia C4.
