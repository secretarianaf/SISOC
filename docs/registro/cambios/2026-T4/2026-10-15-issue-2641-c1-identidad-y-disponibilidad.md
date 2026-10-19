# #2641 C1: identidad disponible y contratos de Espacios comunitarios

Estado: implementado, revisado y validado localmente con 392 pruebas focalizadas.
Rama `juanikitro/Migracion`; SHA base
`1cede84d2b3490f2ddb6bf933852408d9fd68bc7`. C0 se conserva sin cambios ajenos.
No hay commit, push, merge ni deploy de estos cortes.

## Autorización y resultado

El responsable aprobó los contratos y el traslado de auditoría con «apruebo y
prefiero no dejar pendiente». Su criterio: mantener disponibles las operaciones
independientes, bloquear sólo las dependientes y conservar el último agregado
válido. Decisión y costos aceptados en
`docs/registro/decisiones/2026-10-15-identidad-y-espacios-comunitarios.md`.

Se conserva **Espacios comunitarios** como nombre funcional y `pwa` como
identificador técnico. No se agrega gateway, dependencia, DB, caché ni contrato
de autenticación. #2725 sigue postergado. C1 prepara los límites de ejecución;
no extrae todavía imágenes ni modifica Compose o el registro de backends.

## Archivos y responsabilidades

| Área | Implementación y cambio |
| --- | --- |
| Identidad compartida | `src/backends/kernel/users/credentials.py`, `account_forms.py`, `admin_forms.py`, `form_sections.py`, `identity_fields.py`, `admin_operations.py`, `view_mixins.py`, `temporary_passwords.py` y `services_territorial_comedor.py`: validación común, formularios, clasificación de efectos y guardado genérico sin ORM de Espacios |
| Pantallas y API central | `src/backends/sisoc_core/usuarios/auth_views.py`, `auth_forms.py`, `api_views.py`, `api_serializers.py`, `services_password_reset_pwa.py`, `views.py`, `forms.py` y `urls.py`: identidad separada del ABM compuesto, URLs públicas conservadas y compatibilidad de imports explícita |
| Dueño de Espacios | `src/backends/sisoc_core/pwa/user_forms.py`, `user_admin_views.py`, `identity_services.py`, `identity_urls.py`, `identity_api_urls.py`, `user_admin_urls.py` y `apps.py`: reglas de acceso, contexto y operación completa con identidad en una transacción |
| Transporte | `src/backends/kernel/core/internal_services.py`, `backend_proxy.py`, `users/middleware_admin_body.py`, `users/middleware.py` y `src/backends/config/settings.py`: adaptadores locales o HTTP con destino fijo, identidad original, CSRF y sin reintento de mutaciones |
| Auditoría | `src/backends/kernel/audittrail/{models,auth,admin,legacy_admin_urls}.py`, migración `0002_auditoria_sesion_desde_pwa.py` y `src/backends/sisoc_core/pwa/migrations/0027_auditoria_sesion_a_kernel.py`: un solo modelo/escritor, traslado de estado y ContentType, sin DDL de la tabla existente |
| Indicadores | `src/backends/sisoc_core/comedores/dashboard_metrics.py`, `api_urls.py`, `apps.py` y `src/backends/sisoc_core/dashboard/{comedores_metrics,views,apps}.py`: cálculo autorizado en el dueño y última muestra completa en el portal; se retiran `dashboard/signals.py` y `utils.py` |
| Recursos y límites | Template compartido en `src/backends/kernel/users/templates/user/user_form.html`; `dashboard/templates/dashboard.html`; URLs y registro en `src/backends/config/`; tres contratos nuevos en `.importlinter`; tests cercanos, guía de verticales y mapa del repo |

Los mixins, campos y formularios existentes se reutilizan; no se duplican modelos
ni datos de dominio. Los reexports preservan consumidores conocidos durante C2.

## Comportamiento, rechazos y fallas

- Login de Datacalle, Inspecciones y otras capacidades compartidas no exige
  consultar Espacios. SIIS conserva su flujo. Login exclusivo de Espacios vuelve
  a autenticar en el dueño; una caída responde 503 sin emitir Token provisional.
- `/api/users/me/` conserva identidad, permisos y territorio. El nuevo indicador
  `espacios_comunitarios_disponible` distingue contexto disponible de defaults
  conservadores. Contextos incompletos o malformados tampoco autorizan accesos.
- Logout y contraseña no requieren al dueño. El recupero exclusivo conserva el
  enlace de Espacios; otros programas y cuentas mixtas usan el enlace central.
  Se preservan usuario+email, rate limit y antienumeración. El confirmador web
  revoca el Token previo junto con el cambio de contraseña: la revisión detectó
  y corrigió este efecto del nuevo destino para cuentas mixtas.
- El portal clasifica campos y efectos reales de grupos/permisos en servidor,
  vuelve a comprobarlos al guardar y conserva campos omitidos y cambios ajenos.
  Un flag del navegador no evita las reglas. Cambios compuestos van completos
  al dueño, con validación de actor, alcance y una sola transacción. El catálogo
  IAM compartido conserva su administración existente; no se muda su propiedad.
- Un middleware limitado al POST de crear/editar usuario conserva el cuerpo
  antes de que CSRF consuma multipart. No exime el ABM de CSRF ni de contraseña
  obligatoria, confirmación de datos, encuesta o acceso web. Sólo las dos rutas
  API internas de login/contexto reciben la misma clasificación API preexistente.
- Timeout de una mutación informa resultado incierto y pide comprobar el estado;
  no reintenta ni declara un rollback que no puede probar.
- Indicadores completos y válidos reemplazan las cinco claves en una transacción.
  Timeout, 403, 503 y payload parcial/malformado conservan valores anteriores.
  La pantalla distingue una muestra anterior de ausencia de información y
  conserva ceros reales. CDF conserva su contrato y fallback existentes.
- Auditoría común no consulta Comedores para escribir. Conserva su política
  previa de registrar el error sin interrumpir autenticación. La auditoría de
  operaciones de negocio permanece en Espacios.

## Migración aprobada y compatibilidad

Se conserva `pwa_auditoriasesionpwa`, filas, PKs, FK a User e índices con sus
nombres. `SeparateDatabaseAndState` crea/retira sólo el estado; RunPython mueve
el ContentType con la misma PK y conserva Permission PKs y asignaciones.
Los cuatro prefijos de permiso del modelo pasan expresamente de `pwa` a
`audittrail`; `pwa.manage_*` no cambia. Si ya existen ambos ContentTypes, falla
explícitamente sin fusionar ni borrar.

El admin canónico usa `audittrail`; los enlaces GET legacy de auditoría redirigen
al nuevo admin conservando query. Un formulario POST viejo no se reenvía:
responde 405 y debe abrirse nuevamente. Las rutas internas no tienen nombre
público ni entradas propias en `url_registry.json`. El generador oficial agregó
las nuevas rutas públicas del admin y las métricas.

## Validación y revisión

La corrida final completa pasó: **392 tests, ocho warnings de deprecaciones
existentes, 257.63 s**, sobre MySQL 8.4. Incluye regresiones, criterios de
aceptación automatizados, upgrade/reversa y HTTP real. No demuestra CI, deploy
ni aceptación humana. Log: `c1-final-tests-recheck.log` en el directorio temporal
indicado abajo. No quedan hallazgos P1/P2 abiertos en las dos revisiones focalizadas.

Cobertura focalizada bajo `src/backends/sisoc_core/tests/`:

| Criterio | Evidencia automatizada |
| --- | --- |
| Identidad independiente y contexto degradado explícito | `test_issue_2641_identidad_disponible.py`: login ajeno sin consultar Comedores, 503 sin Token provisional, `/me/` con permisos/territorio, cambio/logout/recupero y revocación al completar el enlace web |
| Sólo se bloquea la operación dependiente | Mismo archivo: omisiones y delegaciones conservadas, flags manipulados, efectos indirectos de grupos, revalidación al guardar, alcance, controles obligatorios, fallo de dominio que revierte identidad y timeout sin reintento |
| HTTP entre procesos con identidad original | `test_issue_2641_http_contracts.py`: login/contexto/métricas con dueño activo, terminación del proceso y continuidad independiente; alta compuesta con sesión y CSRF válido y rechazo de CSRF inválido |
| Último valor válido sin mezclas ni ceros inventados | `test_dashboard_comedores_core_boundary.py`: payloads fallidos/parciales/inválidos, reemplazo atómico, permiso del dueño y pantalla con muestra anterior o ausencia |
| Tabla, IDs y asignaciones conservados | `test_issue_2641_auditoria_migration.py`: upgrade/reversa, conflicto de ContentTypes, estado sin DDL y enlaces legacy del admin |
| Límites e independencia de imports | Tres contratos nuevos y `src/backends/kernel/tests/test_identity_arranca_sin_espacios.py`, que impide importar módulos del dominio en un intérprete aparte |

La suite también conserva las regresiones de formularios, SIIS, permisos,
territoriales, organizaciones y operadores, proxy, arranque del kernel,
registro de URLs y selector. No es el smoke humano multivertical del issue.

Entorno autorizado: Docker con MySQL 8.4 sintético, sin dumps ni `.env`, fuentes
RO, sin puertos publicados y red interna sin integraciones. Un test usa un
servidor WSGI hijo en loopback: es otro intérprete/proceso, autentica por HTTP y
se detiene para probar la caída. Su destino se inyecta sólo en la prueba; no es
una imagen de Comedores aislada ni evidencia del deploy real. El changelog local
se monta RO para evitar el fallback HTTP del footer.

Al terminar se ejecutó `docker compose ... down --volumes` del proyecto temporal
`sisoc2641c0-137b6c50` y se comprobó que no quedaran contenedores ni redes con su
etiqueta. La DB tmpfs desapareció; se conservan configuración, logs e imagen de
herramientas, sin datos de aplicación.

Comandos y logs temporales:
`C:\Users\Juanito\AppData\Local\Temp\sisoc2641-c0-1nh_v_m2`.
`c1-final-tests-command.json` conserva los argumentos exactos de la suite. Usa
`docker compose --env-file NUL ... run --rm --no-deps checks pytest --reuse-db -q
--maxfail=3 -p no:cacheprovider`, sin xdist ni suites simultáneas sobre la misma DB.
Black, pylint y ambos contratos usan sus configuraciones reales del repo.

La primera corrida final tuvo 390 pruebas aprobadas y dos fallos del worker de
importación: `close_old_connections()` cerraba la conexión abierta dentro del
atomic envolvente de pytest, dejando la transacción inutilizable en MySQL. Se
cambiaron sólo esos dos tests a `django_db(transaction=True)`, para modelar el
worker real; no se modificó el importador ni se ocultó el cierre de conexiones.
La repetición completa pasó y comprobó también su orden. Pylint detectó además
un `return None` terminal innecesario en el nuevo middleware; retirarlo y volver
a comprobar ese archivo resolvió R1711 sin cambiar comportamiento.

Checks estáticos finales: Black en 78 Python modificados/nuevos; pylint sobre
60 módulos runtime, con recheck del único R1711; import-linter con 25 contratos
generales y uno de config/Celiaquía, sin excepciones nuevas; `manage.py check`
sin problemas y `makemigrations --check --dry-run` sin cambios. Registro de URLs
regenerado con `manage.py generar_registro_urls`. El selector aplicado al diff
completo responde `MODO=completo SERVICIOS="" MIGRAR=1`; no se ejecuta ese plan.

El verificador de rutas documentales conserva dos fallos de baseline:
`docs/ia/AGENT_REPO_MAP.md` refiere a `kernel/tests/test_usuarios_simepi_scope.py`
y `docs/operacion/deploy_pwas.md` a `scripts/operacion/deploy_frontend.sh`.
Se informa el resultado, sin convertirlo en un check aprobado ni arreglar deuda
ajena al corte.

Skills: `brainstorming` para respetar fronteras y decisiones antes de ejecutar;
`systematic-debugging` para contrastar los fallos observados de CSRF/multipart y
arranque HTTP con su causa, sin ampliar timeouts; `code-review` para revisar por
separado estándares y especificación con dos agentes de sólo lectura. La revisión
de estándares no encontró P1/P2; la de especificación detectó la revocación de
Token corregida arriba. No se creó un tracker o workflow adicional.

## Rollback, riesgos y continuación

Revertir código y contratos como unidad. Si el migrador ya aplicó el traslado,
coordinar primero la reversa de estado/ContentType y luego la versión anterior;
la imagen no revierte metadata. No mezclar versiones que exijan prefijos de
permiso distintos. La tabla y datos no se borran. Verificar conflicto de
ContentTypes antes de actuar; no resolverlo automáticamente.

DB, almacenamiento y migrador siguen compartidos: una caída de esos recursos
afecta a todos. Quedan C2 (importador y consumidores) y C3 (runtime, imágenes,
Compose, backends y deploy selectivo), y los pendientes secundarios de #2641.
Las pruebas del selector no son evidencia de reinicios o uptime. No se ejecutan
suite completa, CI, QA/HML/PRD, deploy ni smoke humano. Los dos paths documentales
obsoletos preexistentes se conservan fuera del corte.

El responsable delegó revisión y omitió el ejercicio de fallas; no se acredita
comprensión humana. No se recomienda incorporación ni se cierra #2641 a partir
de estas pruebas. El siguiente paso técnico es C2; C3 requiere su propia
validación y toda autorización material pendiente.

Se actualizó sólo el cuerpo/checklist de #2641 con fronteras/contratos aprobados
y evidencia comprobada de C1; se releyó y verificó **OPEN**, actualizado a
`2026-10-15T21:29:38Z`. Se conservan implementación global, C2/C3 y pendientes
operativos sin marcar. #2725 sigue **OPEN** y postergado, sin modificaciones.
