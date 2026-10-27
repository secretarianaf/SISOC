# Cambio: datos por programa de la Organización, Etapa 1 (#2745)

## Alcance

Etapa 1 del plan
`docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md`, según
la decisión `docs/registro/decisiones/2026-10-20-2745-legajo-organizacion-por-programa.md`
(pasa a "aceptada"). Sin cambios de pantalla.

- Modelos nuevos en `src/backends/comedores/gestion_organizaciones/models.py`:
  `ProgramaOrganizacion`, `LineaProyecto`, `RegionAbordaje`, `SubzonaAbordaje`,
  `DatosRegionOrganizacion` y `ConvenioProyecto`, con FKs `PROTECT` y
  validaciones en `clean()` (línea Secos/Tradicional y del programa de la
  organización si tiene programas; subzona de la región; Imprevistos solo en
  Línea Tradicional, controlado desde el convenio y desde la línea).
- Migraciones en `src/backends/comedores/gestion_organizaciones/migrations/`:
  `0002_datos_por_programa` (solo crea tablas), `0003_catalogo_region_subzona`
  (5 regiones y 28 subzonas del Anexo A) y
  `0004_carga_inicial_programas_lineas` (programas de cada organización desde
  todos sus comedores, incluidos los dados de baja y programas fuera de los
  tres; línea de cada proyecto desde sus comedores solo si todos tienen el
  mismo programa de Abordaje).
- `src/backends/comedores/comedores/utils.py`: `es_programa_linea_secos` y
  `es_programa_linea_tradicional` reciben un programa; las funciones que
  reciben comedor las usan sin cambiar su resultado.
- Admin de los seis modelos y auditoría (Historial de la organización) en
  `src/backends/comedores/gestion_organizaciones/audit_signals.py`.
- `src/backends/config/url_registry.json` regenerado con
  `generar_registro_urls`: solo agrega las URLs del admin de los modelos
  nuevos, bajo el prefijo existente `admin/gestion_organizaciones/`.

## Comportamiento

- Para el usuario no cambia nada visible todavía; los catálogos y los datos
  nuevos se ven en el admin.
- Preservación de datos (sección 2.1 del plan): las migraciones solo crean
  tablas y agregan filas en ellas; no modifican ni borran datos existentes;
  las de datos son idempotentes y su reversa es `noop`. La carga inicial no
  dispara auditoría (usa modelos históricos) y deja en el log de `django` la
  cantidad de programas y líneas creados y los IDs de proyectos sin línea,
  en tandas de 200 por línea de log.
- No se modifica `Comedor.programa`, `Comedor.proyecto` ni
  `comedores.ComedorDatosConvenioPnud` (datos de convenio del comedor, distintos
  del convenio por proyecto de la organización; definición 27 del plan).
- La baja de una organización cuyos proyectos tengan línea o convenio falla
  por `PROTECT`; hoy ya falla sin mensaje cuando un proyecto lo usa un comedor
  (comportamiento previo; se resuelve en la Etapa 3, paso 7 del plan). Verificado localmente sobre la
  organización de prueba dentro de una transacción revertida.
- La carga inicial corre una sola vez: las organizaciones que reciban
  comedores después no obtienen programas automáticamente (la definición 22
  del plan evita que eso bloquee altas en las etapas siguientes).

## Verificación

Local, en contenedor Docker de un solo uso (SQLite en memoria, sin tocar la
base local):

- `pytest src/backends/comedores/gestion_organizaciones/tests/test_issue_2745_datos_por_programa.py`:
  21 tests pasan (equivalencia de `utils.py`, unicidad, `PROTECT`, `clean()`,
  catálogo 5/28 e idempotente, carga inicial con bajas y otros programas,
  línea sin ambigüedad, sin cambios en filas existentes al correrla dos veces,
  auditoría).
- `pytest -n auto` sobre `gestion_organizaciones`, `comedores`,
  `comedores/tests` y `rendicioncuentasmensual`: 1748 pasan, 1 falla
  (`test_issue_2641_c2_http.py`), que también falla en `development` sin este
  cambio en el entorno local.
- `black --check` y `pylint` de los archivos tocados sin observaciones (las
  migraciones y tests están excluidos por `.pylintrc`).
- `makemigrations --check`: sin cambios pendientes.
- `lint-imports` (32 contratos) y `.importlinter_celiaquia_config` (1): todos
  se cumplen.

No verificado todavía: aplicar las migraciones sobre MySQL con datos reales
(la base local del autor tiene un historial de migraciones inconsistente,
ajeno a este cambio) y los conteos de la Etapa 6 en homologación.
