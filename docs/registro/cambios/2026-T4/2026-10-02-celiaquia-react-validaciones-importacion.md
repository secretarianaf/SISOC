# 2026-10-02 - Celiaquía React: las validaciones del Excel no llegaban al front

## Síntoma

"No se están teniendo en cuenta las validaciones al cargar los Excel; por
ejemplo, se pueden repetir personas entre expedientes."

## Diagnóstico

Las 22 validaciones de la importación (campos obligatorios, CUIL, edad,
provincia fuera de alcance, y el duplicado por documento contra el resto de los
expedientes) viven en `ImportacionService` y **no estaban rotas**. El problema
eran dos huecos del lado del front v2:

### 1. La pantalla React no ofrecía "Procesar"

`ExpedienteDetailPage` tenía botones para nómina Sintys, padrón, historial y
cruce, pero **ninguno para procesar el Excel**. Sin ese paso la importación
nunca corre, así que ninguna validación se aplica. La pantalla Django lo ofrece
cuando el expediente está en `CREADO`.

### 2. La API descartaba el resultado

`ExpedienteService.procesar_expediente` **devuelve** un resumen con
`creados`, `errores`, `excluidos` y `excluidos_detalle`. La acción `procesar`
del ViewSet lo ignoraba y respondía solo `{"detail": "Expediente procesado."}`.

Eso importa porque las **exclusiones no son registros erróneos**: la fila del
Excel está bien formada, pero la persona ya está en el programa. No hay nada que
corregir, así que no aparecen en la grilla de errores. Sin el resumen,
desaparecían en silencio.

## Cambios

- `procesar` ahora responde con `resultado`, serializado por
  `ProcesamientoResultadoSerializer`, con el detalle de cada exclusión: fila,
  documento, nombre, motivo y el expediente donde la persona ya está cargada.
- Botón **"Procesar expediente"** en la pantalla de detalle, visible solo en
  estado `CREADO`, igual que en Django.
- Componente `ExclusionesImportacion`: tabla aparte de los registros erróneos,
  con enlace al expediente de origen.
- Aviso con el resumen: cuántos legajos se crearon, cuántas filas fallaron y
  cuántas personas ya estaban en el programa.

## Lo que no se hizo, a propósito

**No se replicaron las validaciones en React.** `frontend_v2.md` (sección 7) es
explícito: "React no replica reglas de negocio; solo hace validaciones de UX".
Duplicar las 22 reglas garantizaría que los dos frentes se desincronicen. El
front muestra el resultado; la regla queda donde está.

Los tres motivos de exclusión que aplica el back:

| Motivo | Cuándo |
| --- | --- |
| Ya existe en este expediente | El documento se repite dentro del mismo Excel |
| Ya está dentro del programa en otro expediente | Tiene legajo activo en otro |
| Duplicado por estado de legajo no duplicable | El estado del legajo no admite otra carga |

## Validación

- `pytest -n auto`: **5566 passed, 14 skipped**. 2 tests nuevos sobre el resumen
  de procesamiento (44 en `test_api_escrituras.py`).
- Front: **35 tests**, 4 nuevos sobre `ExclusionesImportacion`.
- `lint`, `typecheck`, `build` y `api:check` en verde.

## Segunda parte: validaciones que vivían solo en el template

Auditando el resto del flujo aparecieron reglas que `expediente_detail.html`
aplica **escondiendo el botón**, pero que ni la vista ni el service verifican.
Esconder un botón no es una validación: por la API se podían saltear.

| Operación | Estado requerido | Antes | Ahora |
| --- | --- | --- | --- |
| Editar metadatos | CREADO | ya estaba en la API | — |
| Procesar expediente | CREADO | **sin verificar** | `exigir_estado` |
| Subir / reprocesar cruce | ASIGNADO o PROCESO_DE_CRUCE | **sin verificar** | `exigir_estado` |
| Exportar nómina Sintys | ASIGNADO, PROCESO_DE_CRUCE o CRUCE_FINALIZADO | **sin verificar** | `exigir_estado` |
| Confirmar envío | EN_ESPERA | ya estaba en el service | — |
| Recepcionar | CONFIRMACION_DE_ENVIO | ya estaba en el service | — |

El caso más serio era **procesar**: un expediente en `CRUCE_FINALIZADO` se podía
reprocesar y volvía a `EN_ESPERA`, perdiendo el avance del cruce.

La regla quedó en `expediente_service.exigir_estado`, con las listas de estados
como constantes. `cruce_service` la importa en vez de repetirla, así que las dos
pantallas y la API validan lo mismo. El mensaje de error dice el estado actual y
el requerido, en vez de un "no se puede" a secas.

## Fechas en DD/MM/YYYY

Corrección a lo que dije antes: **el back no "espera" `DD/MM/YYYY`**.
`CiudadanoService._to_date` es tolerante y acepta `YYYY-MM-DD`, `DD-MM-YYYY`,
`DD/MM/YYYY` e ISO con hora, recortando la parte horaria. Se verificó con los
casos ambiguos (`06/07/2000` → 6 de julio). El cambio es de presentación.

El problema real era de lectura:

- `toLocaleDateString("es-AR")` devuelve `1/10/2026` y `5/6/2000`, sin ceros y
  de ancho variable. En una tabla queda desprolijo.
- El campo editable de los registros erróneos mostraba el valor crudo del
  Excel: `2000-06-25 00:00:00`. Un timestamp no se corrige a ojo en un input.

Se agregó `packages/ui/src/fechas.ts` con tres funciones, usadas en los cinco
lugares donde se mostraban fechas:

| Función | Salida |
| --- | --- |
| `formatearFecha` | `25/06/2000` |
| `formatearFechaHora` | `01/10/2026 09:05` |
| `normalizarFechaEditable` | el valor crudo del Excel → `25/06/2000` |

Dos detalles que están cubiertos por tests:

- **No se usa `new Date()` para normalizar el valor editable.** Con una fecha
  sin zona (`2000-06-25`) el navegador la interpreta como UTC y en Argentina
  muestra el día anterior. Se parsea el texto.
- **Un valor que no se reconoce se deja intacto.** Puede ser justamente el dato
  mal cargado que el usuario tiene que corregir; pisarlo le ocultaría qué vino
  en el archivo.

## Pendiente

- La pantalla Django de detalle pesa 3,9 MB con 5 filas con error, porque repite
  el combo de 15.394 localidades por fila.
