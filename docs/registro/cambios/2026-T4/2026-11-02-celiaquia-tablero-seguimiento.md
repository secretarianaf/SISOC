# Cambio: tablero de seguimiento de Celiaquía

## Alcance

El equipo de Datos seguía el programa con un Power BI externo. Se agrega una
pantalla de SISOC, `/celiaquia/tablero/` ("Celiaquía Seguimiento"), con datos
en vivo y solo agregados.

- Service: `src/backends/celiaquia/celiaquia/services/tablero_service/impl.py`
  (ORM, sin SQL crudo ni objetos nuevos en la base).
- Vista: `src/backends/celiaquia/celiaquia/views/tablero.py`; template
  `celiaquia/tablero.html` sobre `includes/main.html`; Chart.js; datos por
  `json_script` (CSP: sin scripts inline).
- Permiso nuevo `celiaquia.view_tablero_celiaquia` (migración
  `celiaquia/0010_permiso_tablero_celiaquia`, solo cambia `Meta.permissions`).
  Hace falta porque el tablero no debe quedar atado a los permisos de
  expedientes, Cupos ni el Reporter. No se siembra a nadie: lo asigna un
  administrador desde el admin.
- Patrón seguido: el Reporter de Provincias (service + vista delgada + permiso
  propio en `Expediente.Meta.permissions`).

Para que aparezca en el menú "Tableros" se carga una entrada con
`ruta_interna = /celiaquia/tablero/` (ver
`docs/registro/cambios/2026-T4/2026-11-02-tableros-ruta-interna.md`).

## Comportamiento

Bloques: tarjetas (expedientes, personas cargadas por revisión técnica,
titulares), cupo usado por provincia, titulares por edad y género, circuito del
beneficiario, paso entre etapas, ranking de expedientes con más casos por
resolver, revisión técnica por provincia, errores de la carga masiva, motivos de
rechazo y de subsanación. Filtros de provincia y de expediente (por id: el
`numero_expediente` es texto libre y se repite).

Reglas de los números (las mismas de `cupo_service`, `pago_service` y
`reporte_service`):

- Solo beneficiarios (`beneficiario` y `beneficiario_y_responsable`), de
  legajos y expedientes sin borrado lógico.
- Provincia = la del ciudadano.
- Titular = `DENTRO` + `es_titular_activo` + `APROBADO` + `MATCH`. El cupo
  usado se calcula desde los legajos, no desde el contador `ProvinciaCupo.usados`.
- Motivo de rechazo: el último `HistorialValidacionTecnica.motivo` con
  `estado_nuevo = RECHAZADO`, clasificado por palabras clave. El texto libre
  (trae nombres) no sale del servidor; una rechazada puede contar en dos motivos.

Alcance: por ahora quien tiene el permiso ve todas las provincias. El service
recibe `provincias_visibles` para sumar el alcance territorial cuando se defina.
Sin login o sin permiso: 403, igual que Cupos y el Reporter.

## Verificación

- `pytest src/backends/celiaquia/celiaquia/tests/test_tablero_celiaquia.py`:
  23 pasan (reglas de conteo, borrados lógicos, responsables, tramos de edad,
  motivos múltiples y último motivo, subsanación, errores, expedientes,
  `provincias_visibles`, 403 sin login y sin permiso, sin datos personales en
  la respuesta). Suite de `celiaquia` y `dashboard` con `DJANGO_DEBUG=False`:
  668 pasan.
- `black`, `djlint` y `pylint` (10/10) sin observaciones; `makemigrations
  --check` sin cambios.
- Verificación visual en el entorno local con datos inventados que reproducen
  los totales de producción por provincia y por expediente (sin personas
  reales): confirmada por quien pidió el tablero, incluido el caso de un
  usuario sin permiso.
