# API web PAV (tk 2593)

Fecha: 2026-09-29

## Objetivo

Exponer los registros de PAV de un ciudadano, consultados por DNI, con el mismo
contrato que la API web de VAT que ya consume la web.

## Cambios

- Nuevo endpoint `GET /api/vat/web/pav/?documento=<dni>`.
- `VAT/services/pav_service.py` consulta el data warehouse: busca el DNI en
  `DW_sisoc.DIM_Ciudadanos_Ciudadano.documento`, une con `DW_sisoc.FCT_PAV`
  por `ciudadano_key` y con `LEFT JOIN DW_sisoc.DIM_PAV_Cursos` por
  `pav_curso_key`. Devuelve todas las columnas de `FCT_PAV` más
  `pav_curso_desc`.
- Colección Postman: carpeta `PAV web` dentro de la API web de VAT, y conteos
  actualizados en `postman/api_inventory.md`.

## Contrato

- Autenticación: `HasAPIKeyOrToken`, igual que el resto de `/api/vat/web/`.
- `documento` es obligatorio y numérico. Si falta o no es numérico responde
  400 con `{"documento": [...]}` y no consulta el DW. A diferencia del listado
  de inscripciones VAT, nunca devuelve registros sin filtrar.
- La respuesta va paginada con la paginación DRF del proyecto
  (`count`, `next`, `previous`, `results`).
- Un DNI sin registros devuelve 200 con `results` vacío.
- Si el DNI corresponde a más de un ciudadano en el DW (el documento no es
  único en `DIM_Ciudadanos_Ciudadano`), se devuelven los registros de todos.

## Decisiones

- `LEFT JOIN`: un registro cuyo curso no está en `DIM_PAV_Cursos` se devuelve
  con `pav_curso_desc` en `null` en lugar de desaparecer.
- Un error de base no se atrapa como en
  `comedores.services.dw_transacciones_service`: se loguea (sin el DNI) y se
  propaga, y bajo `/api/` termina en 500 `{"detail": "Error interno del
  servidor."}`. Así "el DW no responde" no se confunde con "sin registros".
- El endpoint vive en la app VAT porque sigue el contrato de `/api/vat/web/`
  que ya consume la web. No hay modelos: las tablas son del DW.
- Columnas de `FCT_PAV` listadas en forma explícita (`COLUMNAS_PAV`) en lugar
  de `SELECT f.*`: si el DW agrega o cambia columnas, el contrato de la API no
  cambia.
- Orden: `fecha_inscripcion` descendente y `pav_cursada_key` descendente como
  desempate, para que la paginación sea estable entre pedidos.
- La consulta lleva `MAX_EXECUTION_TIME(5000)`: si el DW está lento, MySQL la
  corta a los 5 s y la API responde 500, antes del timeout de 10 s del cliente
  web.



## Estructura confirmada del DW

Obtenida en la base de producción el 2026-09-29:

- `FCT_PAV`: `pav_cursada_key` (PK), `ciudadano_key`, `pav_curso_key`,
  `fecha_inscripcion`, `fecha_finalizacion`, `estado`, `fecha_carga`. Índice
  único `(ciudadano_key, pav_curso_key)`: un registro por ciudadano y curso, y
  la búsqueda por `ciudadano_key` usa índice. 60.362 filas.
- `DIM_PAV_Cursos`: `pav_curso_key` (PK), `pav_curso_desc` (no nulo, único).
- `DIM_Ciudadanos_Ciudadano`: `ciudadano_key` (PK) y `documento`
  `bigint unsigned` con índice, no único. `ciudadano_key` es una clave propia
  del DW, no el `id` de `ciudadanos_ciudadano` de SISOC: de 60.362 registros de
  `FCT_PAV`, 53.420 no coinciden con ningún ciudadano de SISOC.
- `FCT_PAV` no tiene clave foránea hacia `DIM_PAV_Cursos`. Hoy no hay
  registros sin curso, pero nada lo garantiza; por eso el `LEFT JOIN`.

## Pendientes

- Orden: producto indicó devolver el orden actual; el cliente web reordena.
- El filtro no distingue tipo de documento
  (`ciudadano_tipo_documento_key`), igual que el listado de inscripciones VAT
  por `documento`.
- Requisito de deploy: el usuario de base de SISOC en producción necesita
  `SELECT` sobre `DW_sisoc.FCT_PAV`, `DW_sisoc.DIM_PAV_Cursos` y
  `DW_sisoc.DIM_Ciudadanos_Ciudadano`.
- El schema `DW_sisoc` no existe en local ni en tests: los tests mockean el
  service y el cursor. La consulta real se valida en un ambiente con el DW.

## Validación

- `tests/test_vat_pav_api_unit.py`: validación de `documento`, rechazo sin
  credenciales, paginado, lista vacía, armado de registros, columnas
  explícitas, orden, tiempo máximo y propagación del error de base.
- Prueba local de punta a punta sin el DW: 401 sin credenciales, 400 por
  documento faltante o no numérico y 500 JSON al no existir `DW_sisoc`.
- Prueba local de punta a punta con un `DW_sisoc` de prueba (estructura real,
  datos inventados): DNI en dos ciudadanos, curso inexistente con
  `pav_curso_desc` nulo, fecha de inscripción nula al final, paginación de 12
  registros en 10 + 2 y DNI sin registros o inexistente con `results` vacío.
- `MAX_EXECUTION_TIME` verificado en MySQL 8.4: corta con error 3024.
- La vista navegable de DRF (abrir la URL en el navegador con sesión) renderiza
  el HTML. El ViewSet hereda de `viewsets.ViewSet` y no de `GenericViewSet`,
  porque ese renderer llama a `get_queryset()` y PAV no tiene queryset. Lo
  cubre un test de regresión.
