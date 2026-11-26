# Cambio: PAS con retorno SINTyS gestionable, arrastre de crédito FCH, liquidación y ajustes del back office v2

## Alcance

Backend común de PAS v1 (templates Django) y v2 (`/v2/pas/`, React), más las
pantallas de Panel de control, Buscador, Formación, Cruces, Liquidación y
Dashboard de la SPA (`src/frontends/apps/pas-backoffice/`).

## Comportamiento

### Cruces SINTyS

- **Exportación a SINTyS**: el XLSX sigue el formato de envío de titulares
  de SINTyS (41 columnas, de `PROG` a `DOMICILIO_COMPLETO_SINTYS`). PAS
  completa `PROG` (PAS), `ID_ORIG`, `NOMBRE_ORIG`, `APELLIDO_ORIG`,
  `NDOC_ORIG`, `CUIT_ORIG`, `SEXO_ORIG`, `ESTADO`, `MONTO_ORIG` ($78.000,
  solo activos), `CALLE`, `NUMERO`, `LOCALIDAD` (municipio), `PROV_ORIG`,
  `TELCELULAR` y `EMAIL`; el resto de las columnas va con encabezado y sin
  dato. Se exportan los titulares que no están de baja.
- **Importación del retorno**: acepta TXT/CSV delimitado (`|`, `;`, `,` o
  tabulador) o XLSX con las columnas `ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO`.
  `COMPATIBLE` no genera cambios. `INCOMPATIBLE` propone Suspendido con aviso
  10 (categoría Patrimonio si el motivo menciona bienes, si no Ingresos),
  `RENUNCIA` propone Baja con aviso 39 y `FALLECIDO` propone Baja con aviso
  40. El titular se busca por `ID` solo si coincide con su DNI; si no, por
  `NDOC`. Solo se generan alertas para titulares cuyo estado cambiaría; los que
  ya están de baja o ya tienen ese estado y aviso se cuentan como "sin
  cambios". Las filas sin titular o con evaluación desconocida se informan como
  observaciones. Reimportar en el mismo mes reemplaza las alertas SINTyS
  pendientes y no reabre las confirmadas. Un archivo sin el encabezado
  esperado se rechaza y no registra nada.
- **Bandeja de alertas**: cada alerta muestra el cambio propuesto y el botón
  *Gestionar* con *Confirmar* (aplica el cambio propuesto) o *Modificar*
  (abre el cambio de estado, pide confirmación al guardar). En ambos casos el
  cambio queda en el historial del titular, con el detalle de la alerta, y la
  alerta pasa a *Confirmada*. Cuando no quedan pendientes del período se
  completa la etapa "Procesamiento de alertas".
- **Pasos del circuito**: Justicia y Migraciones quedan *Pendiente* sin frenar
  el avance; después de importar el retorno el paso en curso es
  "Procesamiento de alertas".

### Formación FCH

- El cierre de cada ciclo de 90 días se guarda en `PasPeriodoFormacion` y el
  excedente sobre 100 puntos pasa como crédito al ciclo siguiente (120 puntos
  → arranca con 20). El resumen informa crédito, semáforo (verde, amarillo,
  rojo) y si bloquea el pago. Mientras la fuente FCH no esté integrada
  (`FORMACION_INTEGRADA = False`) la formación no bloquea ni se cierran ciclos.
- Un curso FCH solo figura como **Inscripto** (azul) o **Aprobado** (verde),
  en Formación FCH y en la pestaña Capacitaciones FCH, en v1 y v2. Lo que la
  fuente informe como terminado (aprobado, completada) se muestra Aprobado;
  cualquier otro valor, Inscripto. Solo los aprobados suman puntos.
- **Datos de prueba**: con `DEBUG` activo se puede definir
  `PAS_FORMACION_DEMO` en el `.env` local (JSON `{"dni": puntos}`) para ver el
  semáforo sin la fuente FCH. Sin esa variable no hay datos de prueba.

### Liquidación

- Puntos de control PC1 (SINTyS exportado e importado y sin alertas
  pendientes), PC2 (Mesa de Ayuda, sin integrar), PC3 (FCH) y DDJJ
  procesadas. La descarga se bloquea mientras alguno esté pendiente. Por
  titular se habilitan solo los activos con DDJJ presentada, sin alertas
  pendientes y, con FCH integrado, en verde. La preliquidación muestra los
  primeros 100 titulares con los totales del padrón; la columna Titular se
  ajusta al nombre más largo.
- **Nómina BNA**: Excel (`.xlsx`, hoja `nomina`) con la estructura de la
  planilla "Estructura de datos de salida", solo con titulares habilitados y
  $78.000 en `MES CURSO`. `idPersona` y `DNI` van como números y los textos se
  neutralizan contra fórmulas. La primera descarga cierra el circuito del mes y
  guarda el archivo; las siguientes devuelven el mismo padrón.
- **Preliquidación en CSV**: el botón *Exportar CSV* de la tabla descarga
  todas las filas del período (no solo las 100 visibles) con Titular, CUIL,
  CBU BNA, Monto, FCH, Cruces, DDJJ y Estado final. Usa la política central de
  CSV (UTF-8 con BOM) y requiere `pas.view_paspersona` y el rol transversal
  `auth.role_exportar_a_csv`, como la descarga de informes.

### Panel de control y Buscador (v2)

- Cada titular del listado del Panel muestra los chips *DDJJ* (sin DDJJ
  completa) y *FCH* (menos de 100 puntos en el ciclo, crédito incluido), como
  en el Figma, y solo la provincia (Ciudad Autónoma de Buenos Aires se
  abrevia CABA). Al pasar a Formación FCH se mantiene el titular seleccionado.
- *Importar titulares* y *Nuevo titular* abiertos desde el Buscador quedan
  dentro del módulo (`/v2/pas/buscador/importar` y `/v2/pas/buscador/nuevo`):
  el sidebar sigue en Buscador PAS y se puede volver. El alta guardada vuelve
  al Buscador filtrado por el DNI creado. Desde el Panel, las mismas acciones
  siguen en `/titulares/importar` y `/titulares/nuevo`.
- La pantalla de importación se rediseñó: zona de carga con botón
  *Seleccionar archivo*, nombre y tamaño del archivo elegido, resumen del
  resultado en cifras y un panel *Formato del archivo* con las columnas
  obligatorias y opcionales y las reglas de importación a demanda.

## Permisos y riesgos

- Nuevo permiso `pas.download_nomina_pago` para descargar la nómina (además
  de `pas.view_paspersona`). Gestionar alertas requiere
  `pas.change_paspersona`, como el resto de Cruces.
- Migración `pas.0009_circuito_sintys_liquidacion_formacion`: aditiva salvo
  el cambio de la restricción única de incompatibilidades, que ahora incluye
  el origen (RENAPER o SINTyS). La baja automática por RENAPER solo toma
  alertas de origen RENAPER.
- Migración `pas.0010_historial_observacion`: agrega el campo `observacion`
  (aditivo) al historial de estados.
- Nueva tarea Celery diaria `pas.tasks.cerrar_periodo_formacion` en
  `src/backends/config/celery.py`; no hace nada hasta integrar FCH.
- Convivencia con la DDJJ pública: `src/frontends/apps/pas` (DDJJ pública en
  React) y `src/frontends/apps/pas-backoffice` usan la misma base Vite
  `/v2/pas/`. No chocan porque `src/backends/pas/pas/ddjj_preview.py`
  reescribe los assets de la DDJJ a `/pas/ddjj/react/assets/` y los sirve
  Django; si esa reescritura se quitara, la DDJJ pediría sus assets al
  contenedor del back office.

## Supuestos a confirmar

Los propuso el agente al implementar; requieren confirmación funcional.

- Clasificación de alertas SINTyS: el retorno no trae categoría. Patrimonio
  se infiere por palabras del motivo (automotor, vehículo, inmueble,
  embarcación, aeronave); el resto de las incompatibilidades queda en
  Ingresos, y Renuncia es una categoría propia.
- En el envío a SINTyS el municipio va en `LOCALIDAD` (con `DEPARTAMENTO`
  vacío) y `SEXO_ORIG` lleva el código M, F o X.
- Valores de `FUENTE`/`TAREA` en la nómina BNA: se usó la planilla de salida
  tal cual y quedan vacíos.
- CBU y estado de la cuenta BNA no existen en el padrón: la columna sale vacía.
- Los ciclos de 90 días siguen contando desde el 01/01/2026 para todo el
  padrón, no desde el ingreso de cada titular.

## Verificación

Validado en el entorno local (Docker, MySQL 8.4), sobre la rama actualizada
con `development` (`ddfe07735`):

- `pytest src/backends/pas src/backends/kernel/tests/test_servicios_backends.py -n auto`:
  363 passed, 1 skipped, 3 failed. Los 3 fallos son
  `test_admin_pas.py::test_listados_sin_n_mas_1` (23 consultas contra un tope
  de 20) y fallan igual sobre una copia limpia de `development` en este
  entorno; en la CI de `development` pasan.
- `python manage.py makemigrations --check --dry-run`: sin cambios. Las
  migraciones `pas.0009` y `pas.0010` se aplicaron en la base local.
- `black --check`, `pylint` (10.00/10) y `djlint --check` sobre los archivos
  tocados; `generar_registro_urls` regenerado (solo suma las rutas nuevas de
  PAS) y `check_docs_paths.py --existencia` sin referencias rotas.
- Frontend: `tsc --noEmit` y `eslint` de `apps/pas-backoffice` y `apps/pas`, y
  `vitest` de ambas apps: 45 passed. La suite completa (`npx vitest run`):
  2214 passed con `NODE_OPTIONS=--no-experimental-webstorage`; sin esa opción,
  74 fallos en sisoc, vpsl y celiaquia por `localStorage`, propios de Node 26
  local (la CI usa Node 22.14, `src/frontends/.nvmrc`).
- Manual: la persona que pidió el cambio verificó en el navegador el botón
  *Gestionar* (Confirmar/Modificar) de Cruces. El resto de las pantallas no se
  revisó visualmente por el agente (el navegador de la sesión no tenía login).
- Pendiente: CI del PR y prueba con el retorno SINTyS y la fuente FCH reales.

## Puntos de entrada

- `src/backends/pas/pas/services/cruces_service.py`
- `src/backends/pas/pas/services/liquidacion_service.py`
- `src/backends/pas/pas/services/estructura_salida.py`
- `src/backends/pas/pas/services/formacion_service.py`
- `src/backends/pas/pas/services/persona_service.py`
- `src/frontends/apps/pas-backoffice/src/Circuitos.tsx`
- `src/frontends/apps/pas-backoffice/src/ImportarTitulares.tsx`
- Guía canónica: `docs/implementaciones/pas.md`
