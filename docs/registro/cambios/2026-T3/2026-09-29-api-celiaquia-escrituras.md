# 2026-09-29 - API de Celiaquia: superficie de escritura

## Contexto

- La API REST de Celiaquia (2026-09-25) era de **solo lectura** mas cuatro
  acciones: `procesar`, `confirmar-envio`, `asignar-tecnico` y
  `solicitar-subsanacion`.
- El front v2 en React (`frontends/apps/celiaquia/`) necesita hacer lo mismo que
  las pantallas Django, y casi todo eso son escrituras: alta con Excel,
  revision tecnica, cruce, cupos y pagos.
- Varias de esas reglas no vivian en `celiaquia/services/` sino dentro de las
  views, que es exactamente lo que `CLAUDE.md` pide evitar. Exponerlas por API
  sin moverlas primero habria significado dos copias de la misma logica.

## Cambios aplicados

### Logica que se movio a services

- `celiaquia/services/revision_service/` (nuevo). Sale de `RevisarLegajoView`:
  permisos por rol, transiciones validas, liberacion de cupo, aprobacion,
  rechazo, subsanacion (con sus observaciones) y baja logica del legajo. La
  vista queda como traductora de HTTP y delega todo.
- `ExpedienteService.recepcionar` (nuevo). Sale de `RecepcionarExpedienteView`;
  conserva la guarda de estado (solo desde `CONFIRMACION_DE_ENVIO`).
- `ExpedienteService.crear_legajos_desde_filas` (nuevo). Sale de
  `CrearLegajosView`; conserva el `get_or_create` por ciudadano, que es la regla
  que evita duplicar una persona dentro del mismo expediente.

La vista sigue parseando el request: los formatos del POST (observaciones
multiples, motivos por checkbox, el fallback legacy de `tipo_subsanacion`) son
de la pantalla, no del dominio.

### Endpoints nuevos

| Recurso | Endpoints |
|---|---|
| Expedientes | `POST /expedientes/`, `PATCH`, `DELETE`, `preview-excel`, `recepcionar`, `crear-legajos`, `cruce`, `registros-erroneos`, `estructura-familiar`, `nomina-sintys`, `padron-final` |
| Legajos | `revisar` (APROBAR/RECHAZAR/SUBSANAR/ELIMINAR), `archivos` |
| Cupos | `provincia/<id>` (configurar total), `legajos/<id>/baja`, `/suspender`, `/reactivar` |
| Pagos | `POST /pagos/`, `procesar-respuesta`, `exportar-nomina` |

### Tests

- `celiaquia/tests/test_api_escrituras.py` (nuevo): 20 casos sobre permisos por
  rol, guardas de transicion y delegacion efectiva en los services.
- `celiaquia/tests/conftest.py` (nuevo): fixture autouse que limpia el
  `lru_cache` de `_estado_id`.

## Un bug latente que aparecio

`ExpedienteService._estado_id` memoiza con `@lru_cache` el PK de cada
`EstadoExpediente`. En produccion esos ids son estables, pero en los tests cada
caso corre en una transaccion que se revierte: el id cacheado en un test apunta
a una fila que ya no existe en el siguiente, y su `create_expediente` falla con
un FK invalido.

Estaba desde antes; no se veia porque ningun par de tests de la misma corrida
llamaba a `create_expediente`. El test nuevo del alta por API lo desperto. Se
resolvio en el `conftest.py` del modulo, sin tocar el cache de produccion.

**Queda como deuda**: si mañana se recrea una fila de `EstadoExpediente` con
otro id (una migracion de datos, un reseteo de catalogo), el proceso vivo sigue
usando el id viejo hasta que se reinicie. Vale evaluar sacar el `lru_cache`.

## Decisiones

- **Fuera de alcance responde 404, no 403**, tambien en las escrituras. Un
  tecnico que no tiene el expediente asignado recibe 404 al intentar revisar un
  legajo: responder 403 confirmaria que existe.
- **El motivo de rechazo/subsanacion lo compone el backend.** El cliente manda
  solo el texto libre; el service concatena las observaciones tecnicas del
  legajo. La previsualizacion del modal no es la fuente de verdad.
- **Un error al liberar cupo no aborta la revision**, igual que antes: se
  registra y se sigue. Un cupo sin liberar se corrige; una revision a medias
  deja el legajo inconsistente.
- **`PATCH` y no `PUT`** para metadatos, y solo en estado `CREADO`.
- Los `ViewSet` siguen siendo de lectura + acciones: no hay `ModelViewSet` con
  escritura por serializer en ningun caso.

## Impacto esperado

- Las pantallas Django no cambian de comportamiento: la extraccion es un
  movimiento de codigo, y los 336 tests previos del modulo lo cubren.
- El front v2 todavia **no consume** estos endpoints: sigue leyendo de
  `app/lib/mock.ts`.

## Lo que falta para la paridad completa

Requieren su propia extraccion de logica desde las views y quedan para la
proxima tanda:

- Registros erroneos: editar y reprocesar (`ActualizarRegistroErroneoView`,
  `ReprocesarRegistrosErroneosView`, ~300 lineas de reglas en la vista).
- Validacion RENAPER (`views/validacion_renaper.py`, 772 lineas).
- Respuesta a subsanacion con archivos (`SubsanacionRespuestaUploadView`).
- Comentarios tecnicos: listar y crear.
- Correccion de evaluacion final (`CorregirEvaluacionView`).
- Descarga del Excel original y de la plantilla, y lookup de localidades.

## Validación

- `pytest celiaquia/tests`: **356 passed**, sin errores (336 previos + 20
  nuevos).
- `manage.py spectacular`: genera el schema sin warnings de celiaquia.
- `black` sobre los archivos tocados.

## Riesgos y rollback

- Riesgo principal: la extraccion de `RevisarLegajoView` toca el camino de las
  pantallas, no solo el de la API. Los 336 tests del modulo cubren ese camino,
  incluidos los de revision, eliminacion y cupo.
- Rollback: revertir el commit. No hay migraciones.
