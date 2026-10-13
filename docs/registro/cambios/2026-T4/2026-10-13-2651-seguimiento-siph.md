# Seguimiento SIPH: nuevo formulario PNUD en la app y en SISOC (#2651)

Issue #2651: "Formulario de actividades" para los espacios comunitarios que
financia el PNUD. Es el "IV-Formulario Seguimiento de SIPH-Línea Tradicional y
Módulos secos" (Servicios Integrales de Promoción Humana). Aplica a las dos
líneas de Abordaje Comunitario (Línea Tradicional y Línea Secos), se carga n
veces por comedor, con o sin relevamiento inicial previo, desde la app
territorial o asignado desde SISOC, y se exporta al docx que adjuntó el área.

## Decisiones

- Es un `formulario` más de `SeguimientoPnud` (`siph`), no un modelo nuevo. El
  modelo ya resuelve n instancias por comedor, la validación del coordinador,
  el origen (app / asignado desde SISOC) y `sin_cargar`. Migración `0022`
  (solo `choices`).
- La API territorial lo habilita en ambas líneas (`FORMULARIOS_POR_LINEA`); el
  resto de programas sigue devolviendo 400. La asignación desde SISOC
  (`alta_backoffice`) lo ofrece como "Seguimiento SIPH" con la misma regla de
  "uno sin terminar por técnico" que los demás PNUD; otro SIPH se puede
  asignar cuando el anterior terminó.
- Las actividades del punto 4 se precargan desde `ActividadEspacioPWA`
  (actividades del comedor, activas), agrupadas por tipo, subtipo y horario,
  con los días concatenados. El GET del listado PNUD devuelve `actividades`
  con `tipo`, `subtipo`, `dias`, `horario` y `etiqueta`; la app arma con eso
  el desplegable "Nombre de la actividad" (más "Otra") y las filas iniciales
  del cuadro. El técnico puede editar las filas y agregar más.
- "Cerrado" en FUNCIONAMIENTO deriva, dentro del mismo formulario, a una
  sección de excepción (motivo y detalle), como el formulario de excepción de
  PAC; el resto de las secciones se ocultan. Queda en `datos` como
  `excepcion_motivo` / `excepcion_detalle`.
- Los nombres de `datos` son las claves del papel (`funcionamiento`,
  `actividades[]`, `financiamiento_componentes`, `mejoras`, `dificultades`,
  `demandas_cuales`, `modalidad_entrevista`, `firma_entrevistado`, etc.). El
  detalle en SISOC es el genérico por secciones de `pnud_formularios.json`.

## Exportación docx

`relevamientos/siph_docx.py` arma el contexto y
`SeguimientoPnudDocxView` (`seguimiento_pnud_docx`, permiso
`view_relevamiento`) descarga `seguimiento-siph-<id>.docx`. La plantilla
`relevamientos/templates/relevamientos/docx/seguimiento_siph.docx` es el docx
del área con sus blancos, casillas (☐/☒) y celdas reemplazados por tags de
docxtpl (`DocumentTemplateService` de admisiones). Solo el SIPH tiene
plantilla: para los demás formularios PNUD la URL responde 404. El detalle
muestra "Descargar docx" solo en el SIPH.

La plantilla se regenera con
`relevamientos/scripts/armar_plantilla_siph.py <docx del área> <destino>` (en el
contenedor de Django) cuando el área cambie el formulario; también quita las
fuentes embebidas del original (9 MB).

## `pnud_formularios.json`

Se agrega únicamente la entrada `siph` generada por la app
(`scripts/pnud/formularios-json.mjs`). El generador actual de la app también
emite otra estructura para los formularios existentes (desde 1.1.56: última
página sin "Cierre" y etiquetas del ranking de combustible sin la pregunta).
Esa resincronización cambia cómo SISOC muestra el detalle de esos formularios
y queda fuera de este cambio.

## App (secretarianaf/Gestionar, 1.1.61)

Formulario `siph` en `features/pnud/pnudForm.ts` con los textos literales del
papel, catálogos en `catalogos.ts`, precarga de actividades en
`pnudPrecarga.ts`, elección "Prestaciones alimentarias" / "Seguimiento SIPH"
al iniciar un seguimiento PNUD en ambas líneas y PDF genérico. Tests en
`tests/unit/pnud-siph.test.mjs` más las suites de estructura y formato papel.

## Tests

`tests/test_seguimiento_siph_2651.py`: formulario disponible en ambas líneas
(API y popup de asignación), alta desde la app sin inicial (201) y 400 en
Alimentar, segunda asignación cuando la anterior terminó, actividades
precargadas y agrupadas en el GET, detalle con etiquetas y botón de docx,
descarga del docx con las respuestas y 404 para otros formularios.

Validación (13/10): suites focales de PNUD, territorial y backoffice en
SQLite en memoria; black, pylint y djlint sobre lo tocado. No se verificó
MySQL localmente.
