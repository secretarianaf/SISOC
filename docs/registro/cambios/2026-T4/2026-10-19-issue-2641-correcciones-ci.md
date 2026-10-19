# #2641 / PR #2734: correcciones de CI

## Alcance y causas

Se parte del HEAD `819ac2760`, con fallos en `gitleaks`, `smoke`, `pytest`
y `mysql_compat`; `deploy_guard` fallaba como consecuencia. Se conserva la
topología aprobada, Espacios comunitarios y las decisiones C0–C4. No se
modifican workflows, umbrales, reglas de incorporación ni dependencias.

| Fallo | Causa comprobada | Corrección |
| --- | --- | --- |
| Formulario independiente: tres altas DataCalle devuelven perfil anterior | El signal crea/cachea `user.profile`; el formulario guarda otra instancia | Al terminar `_save_profile`, asociar al usuario la instancia guardada. Las tres aserciones originales reproducen el fallo y se conservan |
| Tests de edición y roles | Seguían usando el formulario independiente para cambios compuestos que requieren al dueño | Usar `pwa.user_forms` en esos casos; probar por separado omisión parcial y vaciado explícito |
| Colección de smoke/MySQL | Test legacy importaba `pwa.auth_audit`, trasladado al kernel | Cubrir el persistidor real en `kernel/tests/test_auth_audit_unit.py`; conservar los tests del puerto de autenticación |
| Probes HTTP SQLite | El subprocess abría otra DB en memoria; `DATABASE_NAME` no sustituye esa configuración de tests | Fixture explícita `http_probe_database`: copia SQLite temporal compartida y restauración de la conexión original; transmitir la configuración efectiva antes de `django.setup()` |
| Migración de auditoría SQLite | CI usa syncdb (`TEST.MIGRATE=False`), sin historial; el executor intentaba crear tablas existentes. El schema editor tampoco puede correr dentro de la transacción envolvente | Ejecutar operaciones reales con estados históricos sólo en SQLite sin historial; conservar `MigrationExecutor` completo para MySQL y usar prueba transaccional para duplicados |
| Mapa y Select2 | Dueños, imports y ubicación del template anteriores al traslado | Afirmar fronteras actuales: auditoría común en kernel, historial de dominio en Comedores; conservar cobertura AST de namespace packages mediante una fuente sintética |
| Gitleaks | Prosa identificada como clave y fingerprint histórico desplazado por el formateo del template | Reformular la prosa y actualizar exclusivamente la línea del fingerprint ya existente; contenido exceptuado idéntico al anterior, sin ampliar allowlists |

## Validación

- Reproducción SQLite anterior al fix del perfil: tres fallos en las tres
  aserciones originales; no se agregó `refresh_from_db()` para ocultarlos.
- Primera ejecución focalizada Docker/SQLite: 147 aprobadas; los tres fallos
  restantes pertenecían al montaje local de archivos de control y a una
  aserción del mapa corregida posteriormente.
- Reejecución de estructura: **25 aprobadas**. Cubre los tres fallos anteriores;
  las dos ejecuciones focalizadas cubren 150 casos SQLite distintos.
- Gitleaks **8.30.1**, checksum del binario verificado: escaneo completo de una
  exportación del código versionado más el diff, con rutas relativas y la
  configuración/ignore del repo: **sin hallazgos**. No se montó `.env` local.
- Black con `pyproject.toml`: **11 archivos sin cambios pendientes**; Pylint de
  `kernel/users/admin_forms.py`: **10.00/10**.
- Rutas documentadas: **84 documentos vigentes, 0 referencias obsoletas**;
  se completó la ruta del test SIMEPI y se calificó el script que pertenece al
  repositorio externo de Inspecciones.
- MySQL 8.4 sintético: **7 aprobadas**, incluyendo migración/reversa con
  conservación de filas, constraints, ContentTypes, permisos y asignaciones,
  rechazo de duplicados y ambos probes HTTP. Contenedor y red eliminados al
  terminar, sin tocar otros proyectos.
- Suite integral remota y checks del nuevo HEAD: pendientes de ejecución tras
  publicar estos commits; su estado se verifica en Checks del PR.

Comando focalizado de integración (dentro del contenedor sintético configurado
con `config.settings_all`; no usar datos existentes):

```sh
python -m pytest -o addopts= --create-db -q \
  src/backends/sisoc_core/tests/test_issue_2641_auditoria_migration.py \
  src/backends/sisoc_core/tests/test_issue_2641_http_contracts.py \
  src/backends/comedores/tests/test_issue_2641_c2_http.py
```

## Límites y reversión

Docker local aislado, MySQL efímero en tmpfs, sin puertos publicados ni
integraciones externas. SQLite temporal se elimina con el entorno de pruebas.
Las verificaciones locales no sustituyen los checks del nuevo HEAD remoto ni
la aceptación humana. Los ensayos descritos no ejecutaron merge, deploy ni
cambios sobre datos reales.

La única modificación productiva es la coherencia de la referencia al perfil
devuelto por el formulario; no cambia schema, permisos ni persistencia. Su
reversión consiste en revertir ese fix, lo que reintroduciría los tres casos
reproducidos. El resto corrige pruebas y documentación del contrato vigente.

## Preparación de la incorporación autorizada

El usuario autorizó posteriormente fusionar el PR #2734 a `development` cuando
cumpla los controles. Se verificó que ese merge dispara el workflow
`.github/workflows/deploy.yml`, job `deploy-qa`, sin aprobación intermedia del
Environment. Informado ese efecto, el usuario autorizó expresamente también
el deploy automático de QA. No se autorizaron promociones ni despliegues de
HML/PRD, ni operaciones manuales sobre datos.

Se integró `origin/development` (`7c14fb090`) sin conflictos ni reescritura de
historial. Respecto de la base anterior, sólo aporta el enlace de Consultas CDI
en la cabecera y documentación de promociones anteriores. `djlint` de la
cabecera y el control de rutas documentales pasan. CI debe validar el nuevo
HEAD integrado antes del merge; las reglas vigentes no se omiten.

Merge y despliegue son resultados separados: el estado y SHA de cada uno se
verifican en el PR y en el job de QA. La autorización no demuestra aceptación
funcional ni comprensión humana de cada contrato; ambas siguen sin verificarse.
