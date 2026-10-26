# Issue #2638: análisis y plan de documentación

Pedido: revisar vigencia, planificar e implementar la documentación. Alcance
autorizado: guías, mapas/checklists y verificación de rutas; sin modificar
arquitectura, modelos, permisos, CI/deploy ni ejecutar comandos sobre DB.
Base local: `50d7535bc`, coincide con development remoto verificado por
`git ls-remote`; PR #2646 integrado; worktree `juanikitro/Issues`
inicialmente limpio. No se crea ADR: se explican decisiones ya registradas,
sin atribuir al responsable técnico razonamiento nuevo del agente.

## Verificación de afirmaciones

| Afirmación de #2638 | Resultado al 2026-10-05 | Evidencia / ajuste |
| --- | --- | --- |
| Olas 0–4 y cierre de #1931/#2251/#2309 | Confirmada en código, registros y estado actual del tracker. | #2610, #2626–#2628, #2633–#2637 y las tres épicas están cerrados. Esto no demuestra despliegue/aceptación productiva. |
| Carpetas kernel/backends/frontends en raíz | Desactualizada. | PR #2646 integrado: `src/backends/`, `src/frontends/`, `docker/compose/`, `requirements/all.txt`. #2639 aún figura abierto. ADR 2026-10-02 reemplaza estructura anterior. |
| Falta guía de trabajo | Confirmada, aunque hay contenido aprovechable en la guía operativa. | `MODULAR_BOUNDARIES.md` describe un único deployable, sin registro de extensiones y extracción futura: contradice el código. Se reemplaza con resumen y enlace canónico. |
| Kernel no importa core/verticales | Vigente con excepciones explícitas de herramientas locales. | Contrato `kernel-no-core-ni-backends`; arranque solo-kernel. No presentar excepciones como patrones de runtime. |
| Verticales independientes, sin imports al core/otros | Vigente por composición/imágenes; el lint tiene listas explícitas y cobertura parcial. | Dockerfile core/backend y job `service_images`; contratos `.importlinter`. La DB sigue compartida; no hay independencia total de datos/recursos. |
| Organizaciones/catálogos kernel y Firmante core | Confirmada. | Directorios actuales, migraciones de estado y `db_table` preservado; Firmante depende de Comedores. #2641 propone otra separación futura, no implementarla aquí. |
| HTML/JSON/favoritos para composición remota | Confirmada. | `ciudadanos.detail_contributions`, `core.backend_proxy`, registro CDF/VAT/Celiaquía. Un api.py Python de otro servicio no está en la imagen. |
| Nuevas rutas necesitan prefijos y registro | Necesita matiz. | Agregar prefijo solo si sale del existente; regenerar nombres de URLs cuando cambian. Celiaquía incluye ahora `/api/celiaquia/`. |
| Prohibir BASE_DIR + app | Vigente para recursos de código, no para media/logs/static_root. | `admisiones/services/docx_service/impl.py` usa AppConfig.path. El vínculo específico con un incidente de PRD no se demuestra solo con este código; no se presenta como incidente confirmado. |
| Mover modelos con estado, tabla y content types estables | Vigente para cambio de app label; mover carpeta no requiere lo mismo. | Firmante y catálogo conservan tablas y PK de content type; detienen duplicados. No se reejecutó una migración real. |
| Comandos DB en migrador | Vigente para comandos que cargan grafo de migraciones. | settings_all y perfil migrate; runtime parcial no tiene grafo completo. collectstatic también pasó al migrador en #2639. |
| Completo/selectivo/ninguno | Vigente, con diferencias que hay que explicar. | Compartidos de frontend despliegan todos los fronts; tests solo se omiten en carpetas directamente del dueño. Cambiar config/url_registry obliga completo. |
| 503, sección vacía y content types duplicados | Mecanismos confirmados, no diagnóstico único. | Proxy distingue timeout 504 de conexión 503; fragmento devuelve vacío por error/no 200; migración rechaza duplicados. NoReverseMatch puede tener otras causas. |
| Cada regla tiene test/contrato/CI | No es cierto hoy para todas las reglas. | Ubicación de recursos, SQL/imports dinámicos y preservación de datos requieren revisión/prueba específica. La guía identifica límites en vez de inventar controles. |

## Plan de implementación

1. Crear guía canónica en `docs/desarrollo/verticales_independientes.md`:
   ubicación por dueño, reglas/motivo/control, diagrama Mermaid, administración,
   deploy y diagnóstico con límites de cobertura.
2. Recorrer los cuatro checklists contra dispositivos/datacalle, CDF,
   contribuciones de CDF y traslado de Firmante. Registrar evidencia estática
   y simulaciones; no equipararlas con pruebas funcionales o DB real.
3. Actualizar AGENTS, CLAUDE, MODULAR_BOUNDARIES, CONTEXT_HYGIENE y
   AGENT_REPO_MAP con bloques cortos (máximo 15 líneas) y referencia a la guía;
   corregir guía operativa e índice.
4. Reutilizar el mapa de apps real para un verificador stdlib de literales
   Markdown; corregir rutas vigentes comprobables. Conservar registros,
   snapshots y referencias históricas explícitas. No crear una skill nueva:
   los cuatro checklists y los checks existentes cubren el flujo requerido.
5. Validar rutas, ejemplos, checklists y selector; revisar diff y registrar
   checks no ejecutados. No iniciar Docker/DB, crear commits/PR ni desplegar.

## Recorridos de checklists

| Checklist | Caso / comprobaciones | Resultado y límite |
| --- | --- | --- |
| App en vertical | Registro dispositivos contiene dispositivos/datacalle; runtime incluye sus URLconfs y prefijos; servicio backend_dispositivos. | Recorrido contra código real, sin agregar app ni ejecutar backend. |
| Vertical nuevo | CDF: carpeta/runtime, aplicar(globals(), cdf), registro, backend_cdf en Compose, pythonpath, URLs y contrato de imports. | Recorrido de extracción real; service_images itera el registro. No se construyó una imagen nueva. |
| Pantalla remota | CDF registra sus dos fragmentos en AppConfig.ready y backends.json; kernel pide HTML con sesión y degrada a vacío. | Recorrido del flujo y ramas de error; no se accedió con una cuenta real. |
| Modelo entre apps | Firmante: modelo/destino, estado origen/destino, tabla organizaciones_firmante y reasignación de content type que rechaza duplicados. | Recorrido de migración real; sin ejecutar DB ni demostrar conservación de datos con una corrida nueva. |

## Validación ejecutada

- `python src/scripts/ci/check_docs_paths.py`: sin referencias obsoletas en su
  alcance explícito (literales inline/enlaces; no texto libre/bloques de comandos).
- `python -m pytest -c NUL --noconftest -o addopts= src/backends/kernel/tests/test_deploy_targets.py -q`:
  20 passed, sin Django/fixtures/DB; aviso de cache al usar NUL como config.
- Ocho simulaciones por import de `deploy_targets.py`: PAS y workers,
  selectivo core, completo kernel/config, ninguno docs, diferencia de tests
  de app/dueño y frontend compartido. Todas coincidieron con la tabla de la guía.
- Lint local del script: 10/10, pero configuración parcial: falta
  pylint_django y hay opciones no reconocidas. No se considera CI validado.
- Lint independiente con `python -m pylint --rcfile=pyproject.toml --load-plugins= src/scripts/ci/check_docs_paths.py`:
  10/10 sin los errores de configuración del lint oficial; lo complementa,
  no reemplaza pylint_django ni el runtime Python 3.11 de CI (local: 3.14.6).
- Verificación de estructura/checklists por lectura y assertions estáticas;
  14 escenarios de literales positivos/negativos del verificador, exclusiones
  históricas y comprobación de códigos de salida 1/0 sin DB.
- `git diff --check`: revisión de whitespace al cierre.

No ejecutado: lint-imports (no instalado), checks Docker oficiales,
service_images, suite funcional, migraciones MySQL ni aceptación de una persona
nueva. No hay cambio de comportamiento de producto; no justifica levantar
servicios/DB ni ejecutar suite completa. La guía deja comandos focalizados
para cambios futuros que sí alteren comportamiento.

Validación oficial de lint pendiente (el helper inicia un contenedor):
`powershell -ExecutionPolicy Bypass -File src/scripts/ai/codex_run.ps1 pylint src/scripts/ci/check_docs_paths.py`.

## Criterios de aceptación y evidencia

| Criterio del issue | Resultado / evidencia |
| --- | --- |
| Decidir dónde va código y cómo controlarlo | Tabla de dueños, ejemplos y matriz de controles; aceptación por persona nueva pendiente. |
| Cada regla con motivo y control | Matriz completa; identifica revisiones necesarias y límites donde hoy no existe check automático. |
| Cuatro checklists probados | Recorridos estáticos y assertions contra casos reales de la tabla anterior; sin operación de servicios ni DB. |
| Guías de agentes remiten y resumen en hasta 15 líneas | Bloques cortos en AGENTS, CLAUDE, CONTEXT_HYGIENE y AGENT_REPO_MAP; MODULAR_BOUNDARIES completo tiene 15 líneas. |
| Diagrama dentro del repo | Mermaid dentro de la guía, listo para versionar con el diff; sin commit ni verificación de render en navegador. |
| Documentos vigentes sin raíces antiguas | 80 documentos revisados por el verificador, cero hallazgos en literales/enlaces; alcance y exclusiones explícitos. No certifica todo texto libre o comando. |

## Alcance del verificador y riesgos

Escanea Markdown vigente, AGENTS, CLAUDE y README. Excluye registros, planes,
análisis, infraestructura histórica y memorias validadas por commit. Un
registro histórico fuera de esas carpetas se marca al comienzo; una referencia
histórica o relativa se marca en su línea. No es un validador universal de
links, archivos existentes ni de semántica; comandos/bloques se revisan además
manualmente. No se agrega a CI ni cambia workflows en este issue.

El nuevo script de CI es una ruta no exceptuada por deploy_targets: **el diff
completo requiere deploy completo**, aunque los cambios Markdown solos dan
ninguno. No cambiar el selector para evitarlo: eso modificaría comportamiento
fuera de alcance. No se ejecutó deploy.

La aceptación humana (decidir dónde poner un archivo solo con esta guía) queda
pendiente. La lectura y las pruebas no demuestran comprensión del usuario.
No hay nuevo contrato/schema/dependencia de producción ni razón para crear
un tracker adicional. Skill usada: brainstorming para ordenar alcance y
alternativas; se reutilizó la autorización directa del pedido para implementar.

## Continuación tras el reordenamiento de scripts y frontend

El checkout recibió cambios adicionales sin commit: scripts a `src/scripts/`,
configuración frontend a `src/frontends/config/`, imagen a `docker/frontends/`
y nuevas excepciones del selector. No forman parte de la implementación de
#2638; se preservan y la documentación describe el estado observado.

Se reprodujo el fallo del verificador ya movido: `parents[2]` resolvía `src/`
y buscaba `src/src/backends`, dando FileNotFoundError. Se corrigió a
`parents[3]`, como los otros scripts actuales, y se agregó la raíz antigua
scripts al mapa de detección. Se actualizaron comandos de la guía/plan,
referencia administrativa y mapa del repo. No se modificó el selector.

Su código cambió durante la continuación: ahora `docker/frontends/` y
`src/scripts/frontends/` son selectivo de todos los fronts, y
`src/scripts/github/` no despliega. La guía y tabla operativa reflejan esas
excepciones. `src/scripts/ci/check_docs_paths.py` sigue dando completo.

Validación de esta continuación:
- `python src/scripts/ci/check_docs_paths.py`: 80 documentos, cero hallazgos.
- 16 casos de literales, exclusiones históricas, códigos de salida 1/0 y
  ejecución del CLI desde una carpeta temporal fuera del repo: pasaron.
- `python -m pytest -c NUL --noconftest -p no:cacheprovider -o addopts= src/backends/kernel/tests/test_deploy_targets.py -q`:
  23 passed, sin DB ni advertencia de cache.
- 12 escenarios contra el selector actual: pasaron; se comprobó que su
  contenido no cambió durante ese experimento.
- `python -m pylint --rcfile=pyproject.toml --load-plugins= src/scripts/ci/check_docs_paths.py`:
  10/10. Mantiene el límite respecto del lint oficial con pylint_django.
- Enlaces y rutas concretas de la guía resuelven a archivos existentes.
- `git diff --check`: sin errores de whitespace.

Se aplicó systematic-debugging: reproducción, comparación con scripts que
resuelven la raíz correctamente, corrección mínima y ejecución desde otro cwd.
No se iniciaron servicios/DB, construyeron imágenes, publicaron cambios ni
crearon commits. La revisión humana y los checks funcionales/DB siguen sin
validarse; no se consideran demostrados por esta validación documental.

## Publicación autorizada

El responsable pidió commits sistemáticos y PR, y confirmó incluir **ambos**
trabajos: #2638 y la continuación de #2639. Se agrupan scripts/CI, frontend
y documentación. Los archivos auxiliares de tmp/ se conservan localmente y
se excluyen de los commits. El PR se abre como borrador: no demuestra
aceptación humana ni autoriza merge o despliegue.

La configuración frontend final conserva ESLint, Vitest y Playwright en la
raíz del workspace para su autodetección; solo las opciones base TypeScript
permanecen en config/. Esa corrección del reordenamiento adicional reemplaza
la ubicación observada en la primera continuación.

Evidencia nueva y pendientes de ambos trabajos en
`docs/registro/cambios/2026-T4/2026-10-05-configuracion-frontends-scripts-src.md`:
86 pruebas focalizadas de scripts, 10 de releases, contrato API, descubrimiento
de configuraciones frontend y verificador documental. Los controles de
CI, imágenes, DB y QA reales siguen pendientes.
