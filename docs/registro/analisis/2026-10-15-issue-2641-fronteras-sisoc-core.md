# #2641: relevamiento y propuesta de fronteras de sisoc_core

Estado: **fronteras y C1 aprobados; C0 y C1 validados localmente**.
Fecha: 2026-10-15. Este documento conserva el diagnóstico y el plan inicial;
el resultado de C0 se registra en
`docs/registro/cambios/2026-T4/2026-10-15-issue-2641-c0-espacios-comunitarios.md`.
El diagnóstico inicial no es evidencia de deploy. Los contratos de C1 fueron
aprobados posteriormente; ver el ADR de identidad y Espacios comunitarios.

El responsable confirmó después los criterios de disponibilidad y últimos
indicadores guardados. El contrato propuesto y su aprobación posterior se detallan en
`docs/registro/analisis/2026-10-15-issue-2641-c1-disponibilidad-y-contratos.md`.

Nomenclatura confirmada por el usuario: **Espacios comunitarios**, en lugar de
"PWA de comedores". `pwa`, los nombres de clases/permisos y los paths API
citados como evidencia son identificadores técnicos existentes que C0 conserva.

## Punto de partida y autorización

- Repositorio: `secretarianaf/SISOC`, remoto HTTPS confirmado.
- Worktree: `C:\Users\Juanito\orca\workspaces\SISOC\Migracion`.
- Rama: `juanikitro/Migracion`.
- HEAD: `1cede84d2b3490f2ddb6bf933852408d9fd68bc7`.
- `git ls-remote`: `development` coincide con HEAD; `main` apunta a
  `a085404c5385575fc88a8d070749307df158f35b`. No se hizo fetch, merge ni cambio de rama.
- Árbol limpio al iniciar. Primero se agregó este análisis; luego se autorizó C0.
- [#2641](https://github.com/secretarianaf/SISOC/issues/2641): abierto,
  actualizado `2026-10-15T17:30:34Z`, sin comentarios al consultar.
- [#2725](https://github.com/secretarianaf/SISOC/issues/2725): abierto,
  actualizado `2026-10-15T17:28:56Z`, sin comentarios, explícitamente postergado.
- La señal del usuario autoriza relevamiento y planificación; implementar
  requiere aprobar los cortes. No autoriza commits, push, merge, deploy ni #2725.
- Se ofreció una hipótesis inicial antes del diseño; el usuario declinó aportarla.
  Las recomendaciones siguientes se originaron en el agente. Posteriormente
  el usuario aprobó las fronteras con la corrección Espacios comunitarios.
  No se presume una explicación humana del razonamiento ni aprobación de los
  contratos/decisiones por mera inferencia: C1 recibió aprobación expresa posterior.

Se leyeron `AGENTS.md`, `docs/indice.md`, la memoria operativa local,
`docs/ia/MODULAR_BOUNDARIES.md`, la guía de verticales, el ADR de 2026-09-30
y las reglas de registro. La documentación histórica se contrastó con código:
hay **ocho** entradas en `config/backends.json`, incluida Inspecciones; algunas
guías aún describen siete. No se reinterpretaron como pruebas actuales los
antecedentes de HML/PRD del issue.

Skill utilizada: `brainstorming`, para separar investigación, alternativas y
aprobación previa. Sus pasos de commit/implementación no se aplican: prevalecen
el alcance del usuario y las convenciones documentales del repositorio.
Las skills locales de frontend no corresponden a este relevamiento. No se abrió
un proceso paralelo de revisión de código: todavía no existe un diff funcional.

## Evidencia y límites

Se hizo lectura y análisis AST de imports, relaciones ORM, llamadas
`atomic`/`on_commit`, receivers, registros en `ready()`, tareas y recursos.
Las dependencias a otros backends se siguieron solamente para los tres maestros
compartidos y el consumo concreto de métricas CDF. Se excluyeron tests y
migraciones de los resúmenes de dependencias de runtime; el historial de
migraciones conserva el grafo compartido documentado.

Esto prueba dependencias visibles en el código, no su frecuencia, latencia,
salud operativa ni ausencia universal de SQL/imports dinámicos. No se inició
Docker, DB, servidor HTTP, worker ni integración externa. No se leyeron secretos.

Hechos confirmados:

1. `config.settings.CORE_APPS` instala **19 apps**. La imagen `core` conserva
   `config + kernel + sisoc_core`; `backend` copia `config + kernel + su dueño`.
   Mover una carpeta sin sacar dependencias de arranque no produce aislamiento.
2. Comedores, admisiones, relevamientos y rendiciones comparten FKs y efectos
   locales. `comedores/signals.py` crea documentos de rendición, clasifica
   relevamientos, reasigna nóminas y sincroniza accesos PWA. Separar estos
   escritores por proceso cambia el funcionamiento de los signals.
3. `usuarios/forms.py` guarda usuario, perfil, permisos, duplas y accesos PWA
   dentro de `transaction.atomic()`. Una llamada HTTP desde esa transacción a
   otro proceso no comparte su transacción ni garantiza visibilidad del commit.
4. `usuarios/api_views.py` atiende login PWA/territorial, Datacalle, Inspecciones
   y la variante SIIS. `usuarios/api_serializers.py` construye contexto PWA.
   `pwa/auth_audit.py` registra en un puerto local de `usuarios` el persistidor
   de auditoría. Llevar todo `usuarios` o toda autenticación a Comedores
   trasladaría responsabilidades ajenas y su dependencia de disponibilidad.
5. Las APIs operativas de `pwa/api_urls.py` usan espacios/comedores, nómina,
   colaboradores, actividades y mensajes; sus modelos contienen FKs a Comedor,
   Nomina, Dupla y Comunicado. Eso justifica agrupar esas operaciones con
   Comedores, pero no adjudicarle los logins de las demás aplicaciones.
6. `dashboard/signals.py` registra callbacks Python de Comedores/Relevamientos
   y escribe `dashboard.Dashboard`. `dashboard.views` consume esa tabla y,
   para CDF, un contrato JSON remoto si CDF no está instalado. Los callbacks
   locales no cruzan procesos. `Dashboard` también aparece en Django admin.
7. `admisiones/signals.py` congela snapshots al editar Organizacion y al cambiar
   la organización de un comedor. La localización del escritor de organizaciones
   importa aunque su modelo siga perteneciendo al kernel.
8. `core/backend_proxy.py` reenvía sesión/Authorization, método, body, query,
   errores y cookies; normaliza headers y rechaza segmentos punto. Las vistas
   proxy son `csrf_exempt` porque cada backend debe validar CSRF. El proxy
   guarda una sesión modificada antes del reenvío y evita sobrescribirla después.
9. `backend_settings.aplicar()` quita encuestas de middleware/context processors
   porque el core ya aplica el bloqueo. `/api/` está exceptuado por los controles
   web de contraseña, perfil y encuestas; DRF aplica autenticación/permisos propios.
   No se debe introducir de rebote el bloqueo web en las APIs token.
10. `@core` abarca web y los workers que usan imagen `sisoc/core:*`, no solamente
    `django`. Comedores/Relevamientos usan threads y `ThreadPoolExecutor` para
    GESTIONAR, no los workers Celery de PAS. Hay que preservar estos efectos.
11. Recursos de Comedores, incluidas certificaciones, viven parcialmente en
    `pwa/files`; se resuelven por app. Relevamientos usa datos por `__file__`.
    Separar la PWA de negocio también separaría recursos necesarios.

## Matriz de responsabilidades propuesta

"Portal" significa responsabilidad residual de entrada/administración transversal,
no un servicio nuevo autorizado. "Comedores" es el dominio candidato; su proceso
propio queda condicionado a resolver los bloqueos IAM, dashboard y consumidores.

| App / responsabilidad | Dueño actual | Dueño propuesto | Dependencias relevantes | Riesgo | Corte viable |
| --- | --- | --- | --- | --- | --- |
| `comedores` | sisoc_core | Comedores | admisiones, duplas, organizaciones, ciudadanos, PWA, relevamientos, rendiciones, usuarios | Alto: FKs, signals y accesos | Junto al cluster; no sola |
| `admisiones` | sisoc_core | Comedores | Comedor, organizaciones, pagos, rendiciones, historial | Alto: snapshots y documentos | Con Comedores y escritores de organizaciones |
| `relevamientos` | sisoc_core | Comedores | Comedor, PWA, seguimientos, GESTIONAR | Alto: clasificación, cierre y tareas | Con Comedores |
| `rendicioncuentasmensual` | sisoc_core | Comedores | Comedor, ProyectoOrganizacion, PWA, comunicados, territoriales | Alto: acceso y estados | Con Comedores |
| `rendicioncuentasfinal` | sisoc_core | Comedores | Comedor, historial, documentos por signal | Alto: efectos locales | Con Comedores |
| `acompanamientos` | sisoc_core | Comedores | Admision, duplas, catálogos | Alto si se parte la admisión | Con Comedores |
| `expedientespagos` | sisoc_core | Comedores | FK Comedor | Medio: pagos/documentos | Con su cluster |
| `importarexpediente` | sisoc_core | Comedores | ExpedientePago, Comedor, archivos/importación | Alto: escritura compuesta | Con pagos y Comedores |
| `duplas` | sisoc_core | Comedores | User/Profile; M2M y signals bidireccionales | Alto: ABM de usuarios | Junto al escritor de asignaciones |
| `intervenciones` | sisoc_core | Comedores | Comedor, Admision, catálogos kernel | Medio | Con Comedores; catálogos quedan compartidos |
| `gestion_organizaciones` | sisoc_core | Comedores, gestión operativa actual | maestros kernel, Firmante→Programas, rendiciones, territoriales | Alto: snapshots y FKs | Con admisiones; no extraer todo el maestro |
| `historial` | sisoc_core | Comedores, según consumidores actuales | ContentType/GFK; admisiones y rendición final | Medio: referencias genéricas | Con sus escritores; no promoverlo al kernel por su nombre |
| Espacios comunitarios (`pwa`), operaciones de espacios | sisoc_core | Comedores | Comedor, Nomina, Dupla, Comunicado; recursos y accesos | Alto | Mantener unidad de negocio; tratar auditoría/login compartido aparte |
| `comunicados` | sisoc_core | Comedores inicialmente, con parte institucional identificada | M2M Comedor/Organizacion; destinatarios con scope, mensajes PWA, mailing | Alto: modelo mixto | App completa con cluster inicialmente; no crear servicio por app |
| `usuarios` | sisoc_core | Identidad transversal / administración de accesos de dominio, aún por delimitar | kernel users/IAM, PWA y duplas dentro de atomic; SIIS/Datacalle/Inspecciones | **Bloqueante** | Preparar helpers; no separar procesos hasta aprobar la operación compuesta |
| `dashboard` | sisoc_core | Portal para UI/Tablero; métricas calculadas por su dominio | callbacks Comedores/Relevamientos, tabla persistida y admin; JSON CDF | Alto: métricas obsoletas al cortar signals | Aprobar contrato y conservación de actualización/persistencia antes del runtime |
| `encuestas` | sisoc_core | Portal transversal, por ahora | User, grupos; middleware y modal en páginas de todos | Alto: control obligatorio | Mantener en la entrada actual; no hacer otro servicio ahora |
| `insumos` | sisoc_core | Soporte documental en Portal, provisional | `core.Programa`, categorías, archivos y permisos | Bajo/medio | App local; verificar uso funcional antes de adscribirla a Comedores o aislarla |
| `ocr` | sisoc_core | Capacidad documental delimitada | usuario, OCRJob/Document, `usuarios.views.AdminRequiredMixin`, worker | Medio: permisos y jobs en curso | Extraíble tras eliminar import de vista; diferir para priorizar Comedores |
| ciudadanos, organizaciones, catálogo | kernel | Dominios compartidos explícitos en kernel durante #2641 | FKs y consumidores en varias imágenes | Alto si se muda su dueño | Conservar ubicación y contratos actuales; no ejecutar #2725 |

La pertenencia de Comedores a un mismo proceso preserva invariantes; no obliga
a que sus apps mezclen responsabilidades internamente. La adscripción de
insumos y el futuro de la parte institucional de comunicados siguen siendo
hipótesis; no hay evidencia funcional suficiente para convertirlos en servicios.

## Cómo consumir los maestros antes de considerar extraerlos

- **Ciudadanos:** hay consumidores runtime en Comedores/PWA, VPSL, VAT,
  Celiaquía, CDI y CDF. CDI, CDF, VAT, Celiaquía y Comedores tienen escrituras
  visibles sobre Ciudadano; no existe hoy un único proceso escritor central.
  Propuesta: mantener modelo/servicios compartidos en kernel y FKs existentes.
  Ciudadano 360 usa contribuciones HTML con sesión: convertir las contribuciones
  locales de Comedores/PWA en renderizadas remotas al extraer su runtime, usando
  el mecanismo existente, con autorización en el dueño y fallback probado.
  Un servicio maestro futuro necesitaría contrato de altas/edición/consulta,
  identidad, conflictos y atomicidad con nóminas/legajos. No se presume resuelto.
- **Organizaciones:** el muestreo de imports/FKs actuales detecta consumo en
  sisoc_core y CDF; no se trasladó sin comprobar la afirmación histórica de que
  CDI lo requería. Conservar el maestro en kernel, las pantallas operativas y
  Firmante junto a Comedores. Una futura API remota debe resolver también el
  congelado de snapshots previo a editar y proyectos/archivos compartidos.
  Leer el mismo modelo desde otra imagen no propaga un signal de admisiones.
- **catalogo_intervenciones:** Comedores/intervenciones/acompañamientos y CDI
  consumen catálogos y sus filtros por programa. Conservar modelos y servicios
  de consulta en kernel, sin duplicar filas/IDs. Una extracción futura exige
  contrato de catálogo, edición, compatibilidad de IDs y estrategia para FKs;
  no es necesaria para separar procesos en #2641.

Estas propuestas conservan acoplamiento deliberado de esquema y versión del
kernel. No equivalen a independencia de datos ni a privilegios DB por servicio.

## Alternativas y recomendación del agente

**Recomendada: dominio Comedores cohesionado, preparación incremental y proxy
actual durante los primeros cortes.** Mantener kernel compartido, aislar las
dependencias de apoyo y resolver explícitamente IAM/PWA y dashboard antes de
extraer el runtime. Ganancia: evita repartir transacciones/signals y reutiliza
registro, proxy, runtime, migrador y selector existentes. Costo: los primeros
cortes preparatorios no cumplen solos el objetivo de deploy independiente;
la entrada sigue siendo un punto compartido de disponibilidad.

**Alternativa principal: aislar primero entrada/IAM/proxy en un runtime e imagen
dedicados.** Sacaría tráfico de la imagen de negocio, pero exige resolver antes
autenticación mixta, auditoría PWA, formularios y control de encuestas. Ganancia:
un reinicio de Comedores no reiniciaría el proceso de entrada. Costo: otro
runtime/deploy/contrato y un punto de entrada cuya propia caída seguiría
afectando a todos. No reduce por sí solo el acoplamiento del cluster de negocio.

**No recomendar:** servicio por app o renombrar sisoc_core a comedores dejando
todo adentro. Tampoco usar SQL directo, imports dinámicos, copias de maestros
o excepciones de lint para simular independencia.

### Tráfico, autenticación y proxy

| Opción | Aislamiento | Ganancias | Costos / condiciones |
| --- | --- | --- | --- |
| App de entrada en el proceso actual | Solo código | Ordena responsabilidades sin cambiar saltos | Comparte workers, imagen, reinicios y fallas con negocio |
| Proxy actual, con Comedores detrás cuando sea viable | Proceso de negocio separado de entrada | Patrón existente; conserva middleware y sesiones | El core de entrada conserva su disponibilidad y hop HTTP; hay que sacar imports de negocio |
| Servicio dedicado de entrada/IAM/proxy | Imagen y proceso propios | Aísla su ciclo de release del negocio | Otro proceso; sigue siendo entrada común; encuestas/auditoría/contexto requieren resolución explícita |
| Nginx directo a backends | Entrada fuera de Django core | Quita un hop Django para las rutas directas | Cada backend debe aplicar todos los controles equivalentes; hoy omite encuestas. Cambia red/rutas/headers y exige validación operativa |

No se midieron latencia, saturación o disponibilidad: son diferencias de
topología, no beneficios cuantificados. Recomendación inmediata: conservar
proxy; mantener las otras dos topologías como alternativas, sin ejecutarlas.

Condiciones de cualquier cambio:

- Mantener sesión DB y clave compartidas, cookies, Host/esquema original,
  redirects, uploads, múltiples Set-Cookie y protección de prefijos. No publicar
  backends por fuera de la red confiable sin decisión de infraestructura.
- Autenticación identifica al actor; autorización de cada backend comprueba
  permisos, objetos, provincia/territorio y rol de solo lectura. Ningún header
  del cliente sustituye esa comprobación.
- Mantener CSRF de sesión en el dueño y Token/API key de las APIs existentes.
  Conservar excepciones web de `/api/`, SIIS y CORS PWA; no introducir JWS,
  tokens nuevos o un login propio por vertical.
- Mantener contraseña inicial, confirmación de perfil, encuesta obligatoria
  y las prioridades/exenciones entre sus redirects. Un servicio dedicado
  separado de encuestas necesitaría definir consulta y comportamiento ante
  falla; no asumir un bypass ni inventar una nueva política silenciosamente.
- Mantener `/api/users/login/`, `/me`, logout, password reset y `/v2/`.
  Resolver login sin sesión previa y auditoría aunque no esté instalado PWA:
  **no hay un contrato remoto ya verificado que permita dar esto por resuelto**.

## Cortes propuestos, dependencias y aceptación

Las fronteras y C0 fueron aprobados por el usuario después del relevamiento.
C1 recibió aprobación expresa posterior; C2/C3 dependen de validar su implementación.
No se promete extraer Comedores simplemente al terminar C0.

### C0. Dependencias locales mal ubicadas dentro del mismo runtime

- Separar permisos/serializers móviles del archivo de autenticación genérica,
  ubicándolos junto a PWA; reutilizar directamente sus servicios de acceso en
  los consumidores de Comedores en lugar de pasar por `usuarios.api`.
- Ubicar helpers territoriales PNUD con su dominio. Revisar los puertos actuales
  de importación y auditoría para enumerar, sin ocultar, las aristas que quedan.
  No trasladar al kernel una regla PWA para hacer pasar el lint.
- Archivos iniciales: `usuarios/api_permissions.py`, partes de
  `usuarios/api_serializers.py`, `usuarios/api.py`, `usuarios/services_territoriales.py`;
  `pwa/api_views.py`, `comedores/api_views.py`, `comedores/api_views_territorial.py`,
  `comedores/signals.py`, su comando de sincronización, y consumidores en
  `gestion_organizaciones`/`rendicioncuentasmensual`. Confirmar consumidores de
  cada símbolo antes de moverlo; conservar compatibilidad interna necesaria.
- Aceptación: el negocio deja de depender de esos helpers ubicados en usuarios,
  sin cambiar respuestas, validaciones, permisos, tablas, labels ni atomicidad.
  Las aristas pendientes de formularios, registro de importación y auditoría
  permanecen declaradas; no se afirma aislamiento de proceso.
- Validación: tests cercanos de permisos API, accesos por organización,
  usuarios PWA y territoriales; comparar imports antes/después; lint de fronteras.
  Los tests que necesiten DB esperan autorización concreta y entorno aislado.
- Rollback: revertir solo el código de este corte; sin cambio de esquema/datos.

### C1. Resolver fronteras que hoy comparten invariantes

**IAM/PWA:** trazar alta/edición/revocación de usuario, perfil, permisos, duplas y
accesos como una única operación. Recomendación de diseño: quien ejecuta la
mutación compuesta debe tener todos esos modelos en el mismo proceso y una sola
transacción; la UI puede reenviar una operación completa. No repartir los pasos
entre procesos ni reemplazar atomicidad por sincronización eventual sin una
decisión explícita. Falta acordar qué administración sigue siendo transversal,
la ruta de la operación y cómo el login/contexto/auditoría compartidos consumen
capacidades de Comedores sin importar su código. No se decide poner todo el ABM
genérico ni todos los logins dentro de Comedores como atajo.

**Dashboard:** definir contrato de métricas del dueño usando el patrón JSON ya
existente. Hay que decidir y probar quién mantiene la tabla Dashboard y su
admin, la misma semántica de actualización y qué representa una falla. Quitar
callbacks sin reemplazo deja datos obsoletos. No introducir cache nueva ni
cambiar de rebote el fallback CDF.

- Archivos: `usuarios/forms.py`, vistas/API/serializers, `auth_audit.py`,
  servicios/importador; `pwa/auth_audit.py`, `pwa/services/accesos.py`, registros
  de `comedores/apps.py`; `dashboard/{apps,signals,utils,views}.py`,
  `comedores/api.py`, `relevamientos/api.py` y URLs del dueño.
- Aceptación: guardado o rollback íntegro de la operación compuesta; denegación
  de actores fuera de scope; revocación efectiva; login/Token/session de los
  consumidores actuales conservados; métricas actualizadas con el backend en
  otro proceso y degradación acordada si cae.
- Pruebas: fallo entre usuario y acceso, cambios simultáneos/revocación,
  permisos manipulados, territorios ajenos, token inválido, login sin sesión,
  todos los consumidores de `/api/users/`, timeout/403/payload inválido de métricas.
- Rollback: estrategia por contrato compatible con versión anterior; no avanzar
  al runtime hasta demostrarla. Cualquier cambio de app label exige autorización
  específica y pruebas de migración de estado. La propuesta no lo presupone.

### C2. Consumidores de Comedores fuera de su imagen

- Convertir Ciudadano 360 y favoritos de Comedores/PWA al mecanismo remoto
  existente; registrar contribuciones HTML y dueño de secciones.
- Mantener recursos propios junto al dueño, incluidos templates DOCX/PDF,
  estáticos, fixtures, JSON de formularios y comandos. Mantener nombres de tareas.
- Verificar pantallas, admin y referencias GFK que actualmente resuelven
  modelos instalados en el core; los stubs de URLs no sustituyen el admin ni ORM.
- Aceptación: detalle ciudadano y favoritos funcionan con imágenes separadas;
  una falla no revela datos ni produce 500 en el portal. Certificaciones y
  documentos siguen disponibles sin instalar sisoc_core en la nueva imagen.
- Validación: contribuciones/favoritos permitidos y rechazados, caída parcial,
  documentos renderizados, reverse/resolve y ausencia de imports remotos.
- Rollback: soporte compatible de rutas/contratos durante la transición, sin
  borrar modelos, tablas o registros. Depende de C1 y del catálogo de rutas.

### C3. Runtime e imagen Comedores y selección de deploy

- Mover solamente apps aprobadas a `src/backends/comedores/`, con sus labels
  actuales; agregar `comedores_runtime` usando los helpers existentes.
- Ajustar `config/backends.json`, CORE_APPS, composición completa, URLs y
  registro generado, `.importlinter`, rutas de tooling, Docker/Compose y tests.
  Revisar los prefijos reales: además de `comedores/`, hay `equipo-tecnico/`,
  organizaciones, admisiones, rendiciones, APIs territorial/PWA y rutas AJAX.
  No usar un prefijo raíz indiscriminado que capture autenticación u otros dominios.
- Declarar workers que cambien de imagen como `extra_services` del dueño;
  por ejemplo mailing si se mueve comunicados. Conservar el migrador completo,
  DB, media/static/logs y collectstatic compartidos. OCR/importadores no se
  trasladan por accidente junto con `@core`.
- Revisar `docker/django/Dockerfile`, `docker/compose/docker-compose.deploy.yml`,
  override de producción, `src/scripts/operacion/deploy_targets.py`, su uso en
  `deploy_refresh.sh`, `pytest.ini`, `.pylintrc`, CI y tests por servicio.
- Aceptación: imagen Comedores arranca sin sisoc_core ni otros verticales; core
  arranca sin apps Comedores; los contratos prohíben imports entre dueños.
  Un cambio solo de Comedores selecciona backend + workers propios; kernel,
  registro/config o Compose siguen exigiendo deploy completo.
- El primer corte de configuración/imagen es **deploy completo**, aunque los
  cambios futuros locales al dominio puedan ser selectivos.
- Validación posterior autorizada: builds/arranque aislados, pruebas MySQL de
  compatibilidad, rutas/permisos/sesión/CSRF y ensayo de actualización/rollback.
  Registrar SHAs, contenedores y uptime de servicios no afectados en un entorno
  autorizado; el resultado del selector por sí solo no acredita esto.
- Rollback: imágenes/Compose anteriores compatibles con el esquema; no revertir
  automáticamente migraciones al revertir imagen. Separar cambios de label o
  datos si llegaran a ser necesarios y pedir su autorización específica.
- Documentación: actualizar guía de verticales, mapa del repo y registro de
  cambio; ADR con las decisiones humanas efectivamente confirmadas y su motivo.

### C4. Responsabilidades secundarias

Solo por decisión posterior: OCR y su worker son un candidato acotado para
imagen/runtime propios; el import de `AdminRequiredMixin` debe eliminarse sin
relajar permisos. Insumos/encuestas no justifican otro proceso con la evidencia
actual. No mezclar estos trabajos con C0–C3 ni instalar dependencias nuevas.

## Decisiones pendientes

1. Fronteras de la matriz aprobadas, con nombre Espacios comunitarios. Esto no
   autoriza cambios de labels, separación de datos ni contratos aún indefinidos.
2. C0 autorizado como preparación local, conservando runtime y comportamiento.
3. Antes de C1, resolver con el responsable la propiedad de la operación
   usuario/PWA y el contrato de autenticación/contexto/auditoría que aún falta.
   Preservar atomicidad es una restricción ya indicada, no una pregunta repetida.
4. Proxy actual durante esos cortes confirmado; Nginx directo o entrada dedicada
   siguen siendo alternativas no autorizadas para implementación.
5. Disponibilidad de funciones independientes y conservación de los últimos
   indicadores confirmadas. Aprobar los contratos concretos de C1 y, por separado,
   el traslado de estado/permisos de auditoría si se elige esa recomendación.

Antes de incorporar una decisión arquitectónica, contrastar la explicación del
responsable sobre elección, alternativa, costo y condición para revisarla. Tras
una implementación no trivial, ofrecer primera revisión y cubrir modos de fallo
y reversa conforme a AGENTS.md. Estos controles no se dan por cumplidos por
aprobar tests ni por la ausencia de una hipótesis inicial.

## Validación ejecutada y pendiente

- **23 tests del selector pasaron** en 0.12 s:
  `src/backends/kernel/tests/test_deploy_targets.py`, con pytest aislado del
  conftest/plugins del proyecto, sin Django/DB. Comando PowerShell usado:

  ```powershell
  $previousAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
  try {
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    python -m pytest -c NUL --noconftest -p no:cacheprovider src/backends/kernel/tests/test_deploy_targets.py -q
  } finally {
    if ($null -eq $previousAutoload) {
      Remove-Item Env:PYTEST_DISABLE_PLUGIN_AUTOLOAD -ErrorAction SilentlyContinue
    } else {
      $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $previousAutoload
    }
  }
  ```

- Inspección estática de registros, contratos, imágenes y Compose; AST sin cargar
  Django. No es ejecución de import-linter ni prueba de imagen aislada.
- `git diff --check` sin hallazgos en cambios rastreados; el análisis nuevo,
  todavía sin rastrear, se verificó aparte como UTF-8, con newline final y sin
  whitespace sobrante.
- `python src/scripts/ci/check_docs_paths.py` revisó 83 documentos vigentes y
  reportó **dos referencias obsoletas preexistentes**:
  `docs/ia/AGENT_REPO_MAP.md:394` (`kernel/tests/test_usuarios_simepi_scope.py`) y
  `docs/operacion/deploy_pwas.md:57` (`scripts/operacion/deploy_frontend.sh`).
  No se corrigieron fuera de alcance. El script excluye `docs/registro/analisis/`;
  por eso su resultado tampoco valida el contenido del presente documento.
- `importlinter` no está instalado en el Python consultado; no se instalaron
  paquetes. Pendiente `lint-imports` y su segunda configuración como en
  `.github/workflows/architecture.yml`, en un entorno preparado.
- No se corrieron `test_servicios_backends.py`, `test_kernel_arranca_solo.py`,
  `test_backend_proxy.py`, tests funcionales/auth/encuestas ni suites MySQL:
  requieren composición/servicios/DB o exceden este relevamiento. Algunas
  pruebas de proxy crean un servidor HTTP local; tampoco se iniciaron.
- No se ejecutó `generar_registro_urls`, migrations, collectstatic, builds,
  CI, smoke humano ni operaciones de entorno. Sus resultados siguen pendientes.

Tests cercanos identificados para los cortes: `test_users_api_login.py`,
`test_users_pwa_forms.py`, `test_users_api_permissions_unit.py`,
`test_pwa_accesos_organizacion.py`, `test_territorial_api.py`,
`test_nomina_scope_access_db.py`, `test_dashboard_comedores_core_boundary.py`,
`test_certificacion_prestaciones_service.py`, los de encuestas/permisos/middleware
y los de kernel/servicios/proxy/selector. Esta lista es un alcance de validación
futura, no una afirmación de que hayan pasado.

## Pendientes secundarios de #2641 conservados

| Pendiente | Evidencia o tratamiento propuesto |
| --- | --- |
| Smoke con usuario: Comedores/CDI/CDF/VAT/PAS/ciudadano/favoritos | Automatizado local en Docker con usuarios sintéticos y las imágenes nuevas: navegación, permisos/CSRF y caída/recuperación aprobados. `collectstatic` local aprobado. Aceptación humana y smoke de entornos existentes siguen pendientes. Evidencia: `docs/registro/cambios/2026-T4/2026-10-19-issue-2641-smoke-http-docker.md` |
| Deploy selectivo core/vertical, rollback y uptime ajeno | Selector probado; ejecución real pendiente, con SHAs y uptime |
| Salud backends/workers PAS y promoción HML | No se accedió a entornos; no inferir estado actual del run histórico |
| Grupo Docker temporal QA | No verificado; ninguna modificación de accesos |
| Lentitud de ciudadano/dashboard CDF/favoritos | Sin mediciones; diferir optimización/cache hasta necesidad y decisión |
| CPU/RAM y workers | Sin mediciones; no se proponen límites |
| Fixtures en DB vacía e importación ciudadanos SQLite | Revalidado localmente después de C4: importación SQLite aprobada; reproducido y corregido el orden entre fixtures de departamentos IPI/provincias. Evidencia y límites: `docs/registro/cambios/2026-T4/2026-10-16-issue-2641-fixtures-ciudadanos.md`. Sin ejecución en entornos existentes |
| Redirects legacy CDF | Siguen en `config.urls`; no retirar sin evidencia de uso/compatibilidad |
| Dependencias runtime/dev | Separación conservadora implementada y build real Docker validado localmente: 14 targets, perfiles, pip check, arranque e aislamiento. Diagnóstico compartido conservado; CI remota/incorporación pendientes. Evidencia: `docs/registro/cambios/2026-T4/2026-10-16-issue-2641-build-limpio-docker.md` |
| Coordinación #2577 y `/v2/` | Fronts registrados VPSL/Celiaquía y router existente; preservar contratos/rutas, coordinar al cortar |

Los diferimientos son propuestas; el responsable no los ha aceptado todavía.
No cerrar el issue por terminar solo el trabajo principal.

## Estado de salida

Diagnóstico inicial completado y C0 implementado localmente tras aprobación:
135 tests MySQL, Black, pylint y 23 contratos de imports pasaron. La configuración
de pruebas aislada se retiró; el registro de C0 detalla los comandos y límites.
#2641 sigue abierto: su cuerpo registra la aprobación, C0 local y su evidencia;
sólo se marcó el inventario efectivamente completado.
#2725 no se ejecutó. No hay commits, push, merge ni deploy. La aprobación de las
fronteras está registrada; el usuario delegó la revisión técnica y pidió omitir
el ejercicio de modos de falla. No se considera verificada su comprensión por
ese motivo. Los contratos pendientes de C1 todavía requieren decisión.


## Actualización posterior: C1 autorizado

El responsable aprobó los contratos y el traslado de auditoría, incluidos los
cuatro prefijos de permiso: «apruebo y prefiero no dejar pendiente». Las
referencias anteriores a decisiones pendientes de C1 describen el estado de la
propuesta inicial, ya superado por esa aprobación. Implementación local
validada con 392 pruebas focalizadas; C2/C3 aún no demuestran independencia de imagen o deploy.
Decisión: `docs/registro/decisiones/2026-10-15-identidad-y-espacios-comunitarios.md`.
