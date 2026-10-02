# 2026-10-02 - Celiaquía React: documentación, asignación, RENAPER y subsanación

Cierra el flujo del módulo en el front v2.

## Carga de documentación por persona

Se habilita una vez procesado el Excel: recién ahí existen los legajos.

El endpoint `POST /legajos/{id}/archivos/` y el request del cliente **ya
existían**; faltaba la UI y, sobre todo, que el front supiera **qué archivos
pide cada legajo**. Eso no es fijo: `get_archivos_requeridos_por_legajo` lo
decide según el rol (un beneficiario pide DNI y certificación de ANSES; uno con
doble rol suma la biopsia).

Se agregó `legajo.archivos` al serializer, con slot, etiqueta, si está cargado y
la URL. Sin consultas extra: los requeridos salen del rol y los archivos son
campos del propio modelo.

`ArchivosLegajo` muestra los slots de ese legajo, cuántos faltan, link al
cargado y botón para subir o reemplazar. Se indica cuántos faltan porque el
expediente no se puede enviar hasta que todos los legajos estén completos.

## Asignación de técnico

Faltaba un endpoint que listara los técnicos asignables. La consulta vivía como
`_tecnicos_queryset` dentro de la vista; se movió a `celiaquia/scope.py` como
`tecnicos_asignables` y la vista la importa. Si las dos consultas divergieran,
por la API se podría asignar un usuario que la pantalla no ofrece.

`GET expedientes/tecnicos/` lo expone, solo para coordinación y admin.

`AsignacionTecnico` queda en modo lectura cuando el usuario no puede asignar: no
se oculta, porque saber quién está asignado le sirve igual a la provincia. Un
403 ahí no se reintenta: significa "no asignás", no un fallo de red.

## Validación RENAPER

Son **dos pasos y no uno**: `validar-renaper` consulta y no guarda nada;
`validacion-renaper` confirma. Esa separación es del back y la pantalla la
respeta: confirmar sin ver la comparación sería firmar a ciegas.

La tabla muestra lado a lado lo cargado y lo que devuelve RENAPER, resaltando
solo lo que difiere. Pedir subsanación exige motivo. Se avisa que rechazar
libera el cupo y saca al legajo del padrón, porque las tres opciones no son
simétricas.

## Respuesta a subsanación

Solo aparece cuando el legajo está en `SUBSANAR`: el back lo exige en
`SubsanacionService.exigir_puede_responder`, y mostrar el formulario cuando no
corresponde solo lleva a un 400.

Acepta varios archivos de una vez, porque son **evidencia nueva**: se suman a la
documentación original, no la reemplazan.

## Validación

- `pytest -n auto`: **5569 passed, 14 skipped**.
- Front: **60 tests**, 16 nuevos (7 de documentación, 9 del tramo final).
- `lint`, `typecheck`, `build` y `api:check` en verde.

Un detalle de los tests: `mutate()` de TanStack Query dispara la request de
forma asincrónica, así que las aserciones sobre la llamada van con `waitFor`. Y
`input.files` es de solo lectura en jsdom: hay que definirlo con
`Object.defineProperty`.

## Pendiente

- La pantalla **Django** de detalle pesa 3,9 MB con 5 filas con error, porque
  repite el combo de 15.394 localidades por fila. No afecta al front v2.
