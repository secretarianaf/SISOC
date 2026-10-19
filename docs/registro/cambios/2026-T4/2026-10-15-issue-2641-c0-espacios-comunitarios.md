# #2641 C0: responsabilidades de Espacios comunitarios

Estado: implementado, revisado y validado con pruebas focalizadas locales.
No incorporado mediante commit/merge ni desplegado.

## Autorización y alcance

El usuario aprobó las fronteras del diagnóstico e indicó que el dominio móvil
debe llamarse **Espacios comunitarios**. Se ejecuta C0, la preparación local
descrita en `docs/registro/analisis/2026-10-15-issue-2641-fronteras-sisoc-core.md`.
Los identificadores técnicos `pwa`, tablas, permisos, clases y URLs se conservan.
No se agrega un servicio ni se extrae un runtime en este corte.

## Cambios

| Responsabilidad | Antes | Ahora |
| --- | --- | --- |
| Permisos de Espacios comunitarios | `src/backends/sisoc_core/usuarios/api_permissions.py` | `src/backends/sisoc_core/pwa/api_permissions.py` |
| Cuatro serializers de operadores | `src/backends/sisoc_core/usuarios/api_serializers.py` | `src/backends/sisoc_core/pwa/operadores_serializers.py` |
| Fachada de accesos por organización | `src/backends/sisoc_core/usuarios/api.py` | `src/backends/sisoc_core/pwa/api.py` |
| Consulta/etiquetado de territoriales PNUD | `src/backends/sisoc_core/usuarios/services_territoriales.py` | `src/backends/sisoc_core/comedores/territoriales_pnud.py` |

Se actualizaron consumidores en Comedores, Espacios comunitarios, gestión de
organizaciones, rendición mensual y el comando de sincronización. Los tests
existentes importan y parchean ahora el módulo dueño de la responsabilidad.
Los módulos anteriores de permisos y territoriales se retiraron tras actualizar
los consumidores encontrados. `usuarios.api` conserva los cuatro exports de su
fachada pública mediante reexports de `pwa.api`, sin lógica duplicada; el negocio
ya no lo importa. Los serializers de operadores se consumen desde su nuevo dueño.
Los contratos HTTP y las firmas de acceso se conservan.

Dos contratos de `.importlinter` impiden que los helpers trasladados dependan
de `usuarios` y que el negocio vuelva a consumir sus serializers de autenticación.
No se agregaron excepciones al baseline.

## Criterios y evidencia

- **Propiedad de helpers:** el análisis AST detectó cero imports a los cuatro
  módulos anteriores desde Comedores, Espacios comunitarios, gestión de
  organizaciones y rendición mensual. El módulo de serializers genérico sigue
  existiendo y contiene las cinco clases de autenticación/contexto/contraseña.
- **Conservación del código:** se comparó el AST contra HEAD: las 13 clases de
  permisos, cuatro funciones de acceso, dos helpers PNUD y nueve serializers
  (cinco de identidad y cuatro de operadores) conservan exactamente sus cuerpos.
- **Sintaxis y formato básico:** todos los Python modificados/nuevos compilan
  con sintaxis Python 3.11 sin ejecutarse; `git diff --check` sin errores.
  Se verificó el AST de los 14 consumidores/tests: sólo imports y destinos de
  mocks cambiaron; después se agrupó un import para cumplir pylint.
- **Black:** pasó en los 20 archivos Python afectados, con la configuración real.
- **Pylint:** cubrió los 15 archivos de runtime. Detectó un único C0412 nuevo
  por la posición del import PNUD en rendición mensual; se corrigió sólo su
  agrupación y el recheck de ese archivo terminó con código 0 y nota 10/10.
- **Boundaries:** import-linter 2.12/grimp 3.14 pasó ambas configuraciones:
  22 contratos generales, incluidos los dos nuevos, y uno aislado de Celiaquía.
- **Comportamiento y rechazos:** **135 tests pasaron** sobre MySQL 8.4 en
  299.90 s, con ocho warnings de deprecaciones existentes. Incluyen permisos y
  veto de escritura, acceso/revocación por organización, soft-delete/restore,
  territoriales PNUD, login/Token, formularios y alta/listado/desactivación de
  operadores. Las firmas y cuerpos conservados se comprobaron además por AST.

## Entorno y comandos de validación

El relevamiento inicial no inició servicios. Después de preparar el diff y la
revisión, el usuario autorizó explícitamente tests focalizados y linters con
Docker/MySQL aislados. También pidió omitir el ejercicio de modos de falla;
no se considera demostrada la comprensión humana.

Se creó el proyecto temporal `sisoc2641c0-137b6c50`, con MySQL 8.4, red
`internal: true`, sin puertos publicados y `/var/lib/mysql` en tmpfs. Se verificó
la creación de `test_sisoc_c0`. No se montan `.env`, dumps ni datos existentes;
el código se monta en sólo lectura. GESTIONAR está deshabilitado y la red no
permite salida a integraciones. No se inicia web ni workers.

La imagen de checks deriva del stage `dev` del Dockerfile real (Python 3.11.15)
y agrega las herramientas ya fijadas en `requirements/arch.txt`. No se cambian
dependencias del proyecto. Black/pylint/import-linter se ejecutan con sus
configuraciones reales. No se usa el bootstrap predeterminado: monta un dump y
heredaría configuración local, que no corresponden a esta validación aislada.

Configuración temporal y logs de esta ejecución:
`C:\Users\Juanito\AppData\Local\Temp\sisoc2641-c0-1nh_v_m2`.

Los cinco primeros archivos del conjunto focalizado son:

```powershell
src/scripts/ai/codex_run.ps1 test src/backends/sisoc_core/tests/test_users_api_permissions_unit.py src/backends/sisoc_core/tests/test_comedores_api_views_unit.py src/backends/sisoc_core/tests/test_pwa_accesos_organizacion.py src/backends/sisoc_core/tests/test_issue_2445_territorial_abordaje_organizacion.py src/backends/sisoc_core/tests/test_issue_2445_territorial_filtro_rendiciones.py
```

Se agregaron `test_users_api_login.py`, `test_users_pwa_forms.py` y cuatro nodos
de `test_pwa_comedores_api.py`: alta/listado de operadores, exclusión de comedores
sin programa, rechazo de gestión para operador y desactivación. Se corre una
única suite, sin xdist, con `USE_SQLITE_FOR_TESTS=false`, `--create-db`,
`--maxfail=3` y `-p no:cacheprovider`. El comando real usa `docker compose`
con el compose temporal, `--env-file NUL`, el proyecto aislado y
`run --rm --no-deps checks python -m pytest ... -q`.

No se declara CI, imagen de deploy aislada, suite completa ni aceptación humana.
Los scripts oficiales son referencia de argumentos; no se ejecutó su bootstrap.

Al terminar se retiraron el contenedor MySQL y la red del proyecto de pruebas.
Se comprobó que no quedaran contenedores ni redes con su etiqueta de proyecto.
La DB tmpfs desapareció con su contenedor; se conservan logs/config temporal e
imagen de herramientas para reproducir, sin datos de aplicación.

`python src/scripts/ci/check_docs_paths.py` sigue reportando las dos referencias
obsoletas preexistentes: `docs/ia/AGENT_REPO_MAP.md` (ahora línea 409) y
`docs/operacion/deploy_pwas.md:57`. No se amplió el corte para corregirlas.

Skills aplicadas: `brainstorming` para separar aprobación de fronteras y
ejecución; `systematic-debugging` para vincular el C0412 al import trasladado,
corregir solamente la agrupación y verificar el archivo afectado.

## Riesgos, reversa y siguientes cortes

- Restan `comedores.pwa_user_import → usuarios.pwa_import_access` y
  `pwa.auth_audit → usuarios.auth_audit`; la gestión de usuarios todavía escribe
  perfiles/permisos/accesos en una única transacción. Estas dependencias se
  declaran y no se ocultan con imports dinámicos.
- El contexto/login transversal y el dashboard siguen pendientes de C1. C0 no
  acredita independencia de proceso ni autoriza nuevos contratos de autenticación.
- No se cambian modelos, app labels, transacciones, settings, URLs, imágenes,
  Compose, selector, DB ni almacenamiento. No corresponde una migración.
- El selector aplicado al diff completo devuelve **completo + migrador** porque
  incluye `.importlinter`, una ruta que la regla vigente trata como completo.
  No se cambió el selector para evitarlo ni se ejecutó ese plan. Los tests del
  selector no equivalen a un deploy ni a evidencia de uptime de otros servicios.
- Rollback: restaurar los módulos y sus imports como una unidad; no hay reversa
  de datos ni migraciones. Todavía no hay commit para referenciar una reversión.
- La aceptación funcional y la comprensión humana no están demostradas por los
  checks estáticos. Antes de incorporar: revisión, modos de fallo y prueba
  funcional conforme a AGENTS.md.
- #2641 permanece abierto: se actualizó su cuerpo con fronteras aprobadas,
  evidencia de C0 local y límites; sólo se marcó el inventario comprobado.
  #2725 sigue postergado. No hubo commits, push, merge ni deploy.
