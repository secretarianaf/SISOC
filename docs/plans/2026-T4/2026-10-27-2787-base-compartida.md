# R1: base compartida, brechas y trabajo propuesto (#2787)

Fecha: 2026-10-27. SHA `afa6fcf4bb221082d5fa692ff941be75bc74d8d1`.
Diagnóstico estático, sin correcciones ni ejecución de tests. Complementa el
[plan integral](2026-10-27-2785-migracion-integral-react.md) y el
[índice R0](2026-10-27-2786-inventario-estatico.md).

## Capacidades verificadas frente a incertidumbres

«Existe» acredita implementación/configuración en el SHA inspeccionado, no
comportamiento en producción ni que sirva sin adaptación a cualquier módulo.

| Capacidad | Evidencia concreta | Clasificación y límite |
|---|---|---|
| Monorepo y dependencias | `src/frontends/package.json`, `package-lock.json`; `workspaces` apps y packages; scripts lint/typecheck/test/build | Reutilizable. No crear otro repo ni lockfile. Reconsultar versiones tras #2794 |
| Layout/tema | `src/frontends/packages/ui/src/index.ts` exporta `V2Layout`, `AppShell`, temas y componentes; `layout.tsx` y `layout/AppShell.tsx` tienen marcos diferentes | Reutilizable con evaluación visual. No hay evidencia de equivalencia exacta con templates actuales; no normalizar ambas apps preventivamente |
| UI actual | `src/backends/kernel/templates/includes/base.html`, `main.html`, variantes `new_*`, sidebar/navbar y CSS por flujo | Fuente del diseño. Inventariar consumidores de cada variante; no elegir una nueva paleta ni confundir archivos presentes con plantilla activa |
| Navegación por permisos | VPSL `src/frontends/apps/vpsl/src/App.tsx` usa `/session/` y `can_view_*` para enlaces internos; `V2Layout` recibe una lista externa `modules` | Existe en VPSL. Falta demostrar catálogo transversal de apps/enlaces legacy con permisos y aspecto de sidebar actual |
| Contexto de sesión VPSL | `src/backends/vpsl/ver_para_ser_libre/api_views.py`, `session`: `ensure_csrf_cookie`, 401 sin autenticación, username/capacidades/permisos | Candidato de patrón, específico de VPSL; no ampliar sus permisos para convertirlo en contexto global |
| Contexto `/api/users/me/` | `src/backends/sisoc_core/usuarios/api_views.py`, `UserContextViewSet`: `TokenAuthentication`, `IsAuthenticated`; consulta interna de contexto PWA; registro en `src/backends/sisoc_core/usuarios/api_urls.py` | Brecha confirmada para sesión web común. No usar este endpoint asumiendo cookie ni cambiar autenticación sin estudiar consumidores PWA/SIIS |
| Cliente de Celiaquía | `src/frontends/packages/api/src/client.ts`: Axios con credenciales, lectura csrftoken, métodos no seguros, redirección 401 con pathname/query, `SinPermiso` ante 403 y helpers de error | Reutilizable. No prueba que todos los endpoints devuelvan 401/403 de forma coherente; no preserva hash en `next` |
| Cliente VPSL | `src/frontends/packages/api/src/index.ts`: cliente base `/api/vpsl`, CSRF, `ApiError`, `get`/`postForm`; tipos de VPSL exportados | Reutilizable para VPSL. Conviven dos clientes intencionalmente; no unificarlos como requisito de migración |
| Archivos | `descargarBlob` compartido, formularios VPSL multipart y API Celiaquía; descarga protegida de insumos | Existen piezas. Cada flujo debe comprobar MIME, nombre, tamaño, respuesta binaria, permiso y errores; no convertir una URL media pública en reemplazo de descarga protegida |
| API Inspecciones | `src/backends/inspecciones/inspecciones/api_urls.py` declara contrato PWA y `api_views.py`, `InspeccionesAPIView`, usa `TokenAuthentication` | No equivalente a sesión web. Importaciones del panel requieren contrato propio o reutilización justificada; conservar `puede_gestionar` y propiedad de subidas |
| Formatos/fechas | `src/frontends/packages/ui/src/fechas.ts` exporta formateadores; hay tests Celiaquía y VPSL | Reutilizar donde el comportamiento coincida; comprobar fechas sin hora, zona horaria y formatos actuales de cada pantalla |
| Formularios | Consumidores existentes con React Hook Form/zod y componentes MUI en VPSL/Celiaquía | Herramientas reutilizables, no un formulario genérico para todos los dominios. Reglas y errores definitivos siguen backend |
| Carga, vacío, error y confirmación | VPSL `App.tsx`, `Workflow.tsx`, componentes de UI compartida y tests de Celiaquía | Patrones existentes; verificar cobertura por flujo. Los textos/estados deben conservar diseño y semántica actuales |
| Contrato VPSL | `src/backends/kernel/core/v2_frontend.py`, `schema_endpoints` limita a `/api/vpsl/`; `src/frontends/packages/api/openapi.yaml` y `src/generated.ts` | Reutilizable para ese dominio. Nuevos módulos no entran automáticamente al schema ni a su verificación |
| Contrato Celiaquía | `src/backends/config/urls_frontend_v2.py` incluye solo Celiaquía; `src/scripts/frontends/verificar-contrato.mjs` compara tipos con `openapi.celiaquia.yaml` | Reutilizable como patrón; URLConf y script específicos, no cobertura automática del resto |
| Typecheck/build/lint | `src/frontends/tsconfig.json` incluye `apps/*/src` y paquetes; build por workspaces; ESLint raíz | Base común. Una app nueva debe comprobar inclusión real y scripts propios antes de confiar en CI |
| Tests de componentes | `src/frontends/vitest.config.ts`: proyectos packages, VPSL y Celiaquía explícitos | Brecha confirmada de incorporación de futuras apps: no se descubren por workspaces automáticamente |
| E2E actual | `src/frontends/playwright.config.ts` preview de VPSL; `src/frontends/e2e/vpsl.e2e.ts` intercepta requests de API | Reutilizar Playwright. Es evidencia de pruebas con respuestas simuladas, no de sesión real/API/DB ni de comparación visual Django→React |
| CI | `.github/workflows/frontend-v2.yml`: audit/lint/typecheck/test/build/E2E y chequeos de schema/tipos VPSL/Celiaquía | Configurado. No ejecutado aquí. Falta incorporación explícita de apps/contratos y artefactos visuales por URL |
| Disponibilidad/router | `src/backends/kernel/core/v2_frontend.py`: login requerido, allowlist en settings, GET/HEAD, timeout 3 s, 503 vacío si upstream falla; cache diferenciada | Base vigente. No puede alojar login público sin cambiar contrato; una SPA caída no puede dibujar su propio error |
| Controles forzados | `src/backends/kernel/users/middleware.py` y `src/backends/sisoc_core/encuestas/middleware.py`; orden en `src/backends/config/settings.py` | Cambio de contraseña → perfil → encuesta, con exenciones API. React no debe saltarlos; diseño de transición requiere revisarlos explícitamente |
| Accesibilidad/móvil | MUI/labels y pruebas de componentes existentes no cubren todas las URLs legacy | Incertidumbre por flujo. Evaluar teclado, foco, modales, contraste, responsive y mensajes; no declarar conformidad global |
| Rendimiento/observabilidad | `src/frontends/packages/api/src/observabilidad.ts`; router ocupa workers al entregar assets | Hay punto de observabilidad, no medición comparativa. Baseline local/HML por flujo sigue pendiente; no afirmar mejora por usar React |

## Fichas derivadas propuestas

El plan fue aprobado y se publicaron cinco fichas acotadas como sub-issues de
#2785: G1 se concretó primero como definición de contrato en #2798; G2 → #2799,
G3 → #2800, G4 → #2801 y G5 → #2802. G6/G7 requieren descomposición/contratos
antes de publicar implementación. El [backlog derivado](2026-10-27-2785-backlog-derivado.md)
registra dependencias y estado real. La aprobación de lineamientos no transforma
en contrato cerrado los campos/rutas que quedaron abiertos.
Cada futura tarea deberá enlazar su flujo en R0 y el manifiesto visual del plan.

### G1 — Contexto y navegación de sesión web

- Resultado: usuario de sesión web ve identidad, capacidades y enlaces
  permitidos, incluidos destinos todavía legacy; acceso directo a API sigue
  autorizado por backend. No depender del token PWA.
- Hecho que lo motiva: `UserContextViewSet` es token/PWA; VPSL tiene contexto
  propio y el layout recibe enlaces por props.
- Alternativas: endpoint de sesión web separado frente a ampliar el existente.
  Recomendación del agente: separar contrato web para minimizar impacto PWA;
  dueño y forma se deciden con #2788 antes de implementarlo. No implementar un
  catálogo configurable nuevo sin verificar los metadatos actuales.
- Dependencias: reconciliar menús/context processors/roles R0; decisión de
  endpoint y campos; coordinar #2793 que toca context processors/config.
- Validación: sesión válida, sin sesión, usuario sin acceso web, permisos
  mixtos, alcance, cuenta bloqueada/primer cambio/perfil/encuesta; confirmar que
  PWA/SIIS y VPSL/Celiaquía conservan sus contratos. Tests reales de CSRF para
  mutaciones; no basta esconder enlaces.
- Riesgo: permisos demasiado amplios, dependencia de PWA para abrir toda la UI o
  bypass de controles vía endpoints API. Debe marcarse revisión técnica.

### G2 — Baseline y comparación visual por URL

- Resultado: cada caso del manifiesto tiene captura Django, captura React, diff
  y revisión humana; reporte marca URL/rol/viewport/estado sin comparación como
  pendiente, nunca «aprobado». Cubrir también consumidores indirectos.
- Reutilización: `@playwright/test` y config/scripts existentes; sin nueva
  dependencia. Separar pruebas visuales de E2E simulado y de E2E con API real
  dentro de la infraestructura de pruebas actual.
- Propuesta concreta: proyecto/config Playwright para comparar dos bases
  autorizadas (referencia y candidata), mismo Chromium/entorno/fixtures;
  capturar con la API de screenshots y comparar usando las capacidades de
  snapshots de Playwright. Manifestar correspondencias origen/destino; no usar
  `--update-snapshots` para aceptar el resultado React sin revisión.
- Evidencia a producir: manifiesto del flujo, metadatos de ejecución y SHAs,
  PNG antes/después/diff y reporte HTML. Conservar artefactos de ejecuciones
  correctas y fallidas según las prácticas CI del repo; sin cookies/PII.
- Dependencias: decidir referencia actual aceptada por flujo, entorno sintético
  y tolerancias; fijar fuentes, reloj, datos, temas y viewports. El contrato
  visual completo está en el plan padre; no se baja su cobertura por ahorro.
- Validación del mecanismo: una URL faltante hace fallar cobertura; un cambio
  deliberado de espaciado/icono/texto es detectado; mismo caso sin cambios pasa;
  un estado API/permiso no se considera equivalente por compartir screenshot.
- Regresión: Celiaquía/VPSL e INET cuando corresponda, si cambian UI/tema/layout.
- Riesgo: snapshots aprobados automáticamente, ruido por entorno, máscaras que
  esconden cambios o fixtures distintas. No ejecutar servidores/DB/CI sin el
  alcance autorizado para esa tarea.

### G3 — Shell React con apariencia actual

- Resultado: header/sidebar/footer y navegación mantienen geometría, acciones,
  permisos, scroll, tema y responsive de los templates activos del flujo.
- Reutilización: comparar `V2Layout`/`AppShell`, CSS y assets vigentes. Extender
  solo lo necesario; no crear un tercer shell ni componentes anticipados antes
  de demostrar que los existentes no alcanzan.
- Dependencias: G1 para datos reales, G2 para medir igualdad, #2794 para cambios
  compartidos de shell/tema. Probar primero con el piloto sin mutar otros temas.
- Validación: screenshots completos escritorio/móvil y por rol/tema; teclado,
  menú/cuenta, cierre de drawer, foco y navegación entre legacy/v2. Si cambia un
  paquete común, diff visual de todas sus URLs consumidoras.
- Riesgo: `CssBaseline`, fuentes o selectores globales alteran otras apps;
  mantener versiones compatibles y revertir el cambio de paquete si falla.

### G4 — Registro de nuevas apps en pruebas y contratos

- Resultado: el primer módulo nuevo ejecuta sus tests, build, tipos y contrato en
  los comandos oficiales/CI; una app ignorada o contrato divergente se detecta.
- Archivos candidatos: `src/frontends/vitest.config.ts`,
  `src/frontends/playwright.config.ts`, `.github/workflows/frontend-v2.yml`,
  URLConf de schema y verificadores/tipos existentes. No modificar todos en un
  único PR si se puede incorporar por módulo.
- Dependencias: nombre/dueño de la app de #2788 y reconciliar #2794 que toca los
  mismos archivos. No generar el schema global de todas las APIs ajenas por
  conveniencia ni perder contratos ya chequeados.
- Validación: introducir un fallo controlado en test/tipo/schema de la app
  candidata debe romper el chequeo correspondiente; verificar descubrimiento
  de tests e igualdad de tipos sin simular cobertura ejecutando solo líneas.
- Riesgo: CI verde que nunca ejecuta el nuevo workspace, o snapshots sin upload
  cuando fallan. Revisión técnica de workflows/configuración.

### G5 — Piloto de consulta y descarga de insumos

- Ficha completa en el plan padre: rutas exactas, permisos, inactivos, filtros,
  services, contrato faltante, tests y baseline identificados.
- Dependencias: G1/G2/G3/G4 en el alcance mínimo necesario. Se puede preparar
  contrato y revisar datos de prueba antes; no iniciar UI bajo una app elegida
  por omisión. API nueva y extracción mínima compartida en el mismo alcance
  revisable para evitar duplicación de filtros.
- Regresión: pruebas de insumos actuales y compatibilidad del admin si comparte
  servicios; no tocar sus permisos/admin por asociación.

### G6 — Recorridos de identidad y controles forzados

- Resultado: sesión, login/logout, reset, contraseña obligatoria, confirmación
  de perfil y encuesta conservan semántica y apariencia, sin bucles ni bypass.
- Dependencias: decisiones de #2788 y su matriz de pruebas; no ampliar el login
  token existente para conseguir una cookie sin análisis.
- Dividir luego en contratos de auth, UI pública, cuenta y encuesta; no son una
  sola tarea implementable todavía. Revisión técnica obligatoria.

### G7 — Disponibilidad, errores y activación reversible

- Resultado: una app caída produce respuesta entendible, rutas inválidas
  conservan status y activación se puede revertir sin pérdida de datos ni
  ruptura de enlaces/contratos anteriores.
- Dependencias: política de emergencia/URLs aprobada en #2788; revisión de
  controles y proxy existentes. No cambiar Nginx ni introducir SSR/BFF.
- Dividir por router público/protegido, manejo de errores y activación de cada
  flujo. Pruebas 403/404/500/503, timeouts, assets/versiones y rollback con el
  API anterior/candidato. No confundir revertir navegación con revertir datos.

## Validación posterior mínima

Para cada futura app y paquete tocado se seleccionarán comandos focales de los
scripts existentes. Al preparar PRs se ejecutarán los checks exigidos por el
repo y CI dentro del entorno autorizado. Hay scripts raíz para lint,
typecheck, test, build, test:e2e, types:check y api:check; su existencia no
acredita ejecución ni cobertura de una nueva app. No se ejecutó ninguno aquí.

Los tests backend/API usarán datos sintéticos y servicios externos simulados;
cuando la propiedad dependa de DB/servicios reales se propondrá el experimento
aislado correspondiente, sin presentar mocks como prueba de integración.
Todo cambio Python incluye tests y cobertura del diff exigida por CI. Al
modificar cliente, UI, contrato o middleware común, comprobar regresiones de
Celiaquía/VPSL y consumidores PWA/SIIS según el contrato afectado.

## Qué falta para cerrar #2787

Precisión posterior: [contratos compartidos/remediaciones](2026-10-27-2798-contratos-y-remediaciones.md)
y [reutilización INET con evidencia de 63 rutas](2026-10-27-2794-reutilizacion-y-referencia-visual.md).
Se encontró diferencia fuente entre oscuro forzado legacy y modos de V2Layout;
I1/I2 requiere referencia elegida, no afecta solo una preferencia interna de código.

El [delta posterior de Unfold/INET](2026-10-27-2786-delta-integraciones.md)
actualiza las brechas contra `59a8f797688c9e762d5a4e9eaa187698ffade8aa`.
INET ya incluye app, API de sesión, nueve recursos, proyecto Vitest y preview
Playwright; no se consideran inexistentes por la inspección inicial. G1/P1/C2
están elegidas con su alcance; contratos ejecutables y validación siguen pendientes.

El [análisis por consumidor](2026-10-27-2786-2788-brechas-por-consumidor.md)
agrega evidencia de CDF/varias APIs VAT con HasAPIKey, VAT web con permiso que
también admite usuario autenticado, DataCalle/Comedores/Inspecciones token y
Comunicados publicado frente a gestión. No es correcto tratar toda API como
reutilizable ni exigir que se rehaga toda: comparar por acción/alcance. Las
definiciones nuevas #2805–#2808 quedan vinculadas al padre y al
[backlog](2026-10-27-2785-backlog-derivado.md).

Continuación de G1/G2/G5: el
[contrato de contexto web](2026-10-27-2798-contrato-contexto-web.md) y
[preparación de Insumos](2026-10-27-2799-2802-paridad-insumos.md) concretan campos,
rutas/status, compatibilidad, UI activa y manifiesto de casos. Se confirmó que
Insumos fuerza tema oscuro y que show_management refleja add_insumo aun cuando
editar/borrar exigen permisos distintos. También se detectó el conflicto entre
403 anónimo del entry legacy y redirect del router v2. No se consideran brechas
corregidas por estar especificadas.

Contrastar estas brechas con todos los flujos finales de #2786; resolver las
incertidumbres por consumidor, publicar tareas acotadas y registrar decisiones
de auth/infra sin asumirlas. No está validado runtime, accesibilidad integral,
rendimiento ni visual. No se confunde un componente disponible con paridad de
un flujo, ni la configuración CI con un check pasado.

## Decisión de dependencia de selectores: J2 elegida

Se contrastaron usos Select2 en CDF/Inspecciones y el patrón React Autocomplete
existente en VPSL; no iniciar un motor nuevo sin revisar esa práctica.
[J1/J2](2026-10-27-2787-selectores-react-j1-j2.md) compara encapsular el plugin
actual frente a reproducir control/interacción en React con estilo idéntico.
El responsable eligió J2 explícitamente; J1 descartada. No actualizar
dependencias, copiar scripts globales o aceptar un aspecto MUI distinto.
