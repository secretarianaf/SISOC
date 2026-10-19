# Inspecciones escolares: backend propio, rol por programa y cierre numerado

Fecha: 2026-10-14. Estado: implementado en `feat/inspecciones-escolares` (sin
desplegar). Cambio asociado:
`docs/registro/cambios/2026-T4/2026-10-14-inspecciones-escolares-backend.md`.

## Contexto

La PWA **Sisoc Inspecciones** (repositorio aparte) registra visitas de unos 120
inspectores a escuelas, firma en pantalla y emite actas numeradas. Hoy funciona
contra un backend simulado. Consume el contrato `CONTRATO-API-INSPECCIONES.md`
de ese repositorio. La primera operación prevista es el 15/10/2026.

## Decisiones

1. **Vertical nuevo `src/backends/inspecciones/`** (app `inspecciones`, runtime
   `inspecciones_runtime`, servicio `backend_inspecciones`). Es otro programa
   (no Comedores) y sólo depende del kernel (`users`, `core`). Prefijos
   `/inspecciones/` (backoffice) y `/api/inspecciones/` (PWA), que el core
   reenvía por proxy. Contratos de import-linter: nadie importa `inspecciones`
   y `inspecciones` no importa otros dominios.
2. **Rol por programa en el perfil, como DataCalle.** `Profile.es_inspector_escolar`
   (acceso) + `Profile.inspecciones_rol` (`inspector` | `coordinacion`). El flag
   sin rol no alcanza. La administración del programa es una función de
   coordinación (no hay un tercer rol). El inspector es usuario sólo de la app:
   se crea sin acceso SISOC web ni `is_staff`, igual que el relevador de DataCalle.
   Helpers en `users.services_inspecciones` (kernel) para que los use el core
   (login, `/me/`) y el vertical sin importarse entre sí.
3. **Permisos en el servidor.** El inspector ve y modifica lo propio; lo ajeno
   responde 404. Coordinación consulta todo pero no escribe sobre inspecciones
   ni actas de otros (escrituras ajenas: 404 también). Sólo usuarios del
   programa usan la API (`TieneAccesoInspecciones`).
4. **Cierre en una transacción.** Valida, guarda la instantánea (payload final,
   etiquetas y opciones de la versión del formulario, huella de imágenes y
   SHA-256 de la instantánea), toma el número y registra la hora oficial.
   Numeración con una fila por año en `SecuenciaActa` bloqueada con
   `select_for_update`: el incremento y el acta se confirman o revierten juntos,
   sin huecos ni duplicados. Compatible con MySQL (READ COMMITTED de Django y
   lecturas con bloqueo). El formato es `ACTA-AAAA-NNNNNN` con secuencia por año.
5. **Idempotencia por uuid del cliente.** Borrador: gana la mayor `revision`.
   Cierre: se bloquea la inspección antes de nada; un segundo cierre (doble
   toque, reintento o pedido simultáneo) espera y devuelve la misma acta. La
   fila de la inspección y la del año se crean en transacciones cortas previas
   para que dos pedidos simultáneos no choquen al insertarlas. Imágenes y
   notificaciones: idempotentes por su uuid.
6. **Archivos privados.** `MEDIA_ROOT/inspecciones/` con un storage sin URL
   (`inspecciones.storage`); se descargan sólo por la API con los permisos del
   acta y `Cache-Control: private, no-store`. El Nginx del host debe bloquear
   `/media/inspecciones/` (mismo criterio que `/media/pas/ddjj/`). El tipo de
   imagen se decide por la firma binaria (JPEG/PNG), no por el cliente.
7. **El PDF lo genera la app** con el número y la hora del cierre; el servidor
   lo guarda una sola vez y lo sirve. La notificación en papel es un anexo
   versionado (`reemplaza`) que no toca el acta.
8. **Dashboard de coordinación fuera de alcance.** El modelo queda preparado:
   campos desnormalizados (`fecha_visita`, `turno`, `resultado`, `escuela`,
   `firma_tipo`, `notificacion_estado`), `es_prueba`, `estado` con `anulada`,
   `Inspeccion.reemplaza` y eventos de auditoría.

## Panel del backoffice (2026-10-15)

Detalle en `docs/registro/cambios/2026-T4/2026-10-15-inspecciones-panel-backoffice.md`.

9. **El Cueanexo reusa `codigo` y `cue`.** No hay columna nueva: `codigo`
   (único, `id` de la API) y `cue` guardan el Cueanexo de las escuelas
   nuevas, y `codigo` no cambia nunca porque la app lo guarda en sus
   borradores. Una columna `cueanexo` aparte habría triplicado el dato.
10. **`localidad` y `distrito` siguen siendo texto**, mantenidos desde la
    localidad vinculada (`localidad_vinculada`, FK nula si no se resolvió).
    Así la API de la PWA no cambia de forma y `services/escuelas.py` no se
    toca.
11. **La importación del padrón escribe con SQL directo** (`INSERT` múltiple
    con el sufijo de conflicto que arma el backend de Django) y la
    confirmación usa las filas normalizadas en la revisión, sin releer el
    `.xlsx`. Con 64.495 filas, `bulk_create`/`bulk_update` y la doble lectura
    no entraban en el `timeout` de Gunicorn; el `.xlsx` se lee en streaming
    con `lxml` (sólo la primera hoja) porque `openpyxl` tardaba el doble.

## Alternativas descartadas

- App en `sisoc_core`: evitaba un servicio nuevo, pero mezclaba un programa
  ajeno a Comedores con el core, contra la guía de verticales.
- Numerar con `AUTO_INCREMENT` o `MAX()+1`: no garantiza ausencia de huecos ni
  es seguro con concurrencia sin bloqueo explícito.
- Verificar `firma.hash_contenido` en el servidor: la app lo calcula sobre su
  modelo interno (camelCase), no sobre el cable; se guarda como evidencia.
