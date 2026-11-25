# Cambio: observaciones CDI en React sobre G1 v1 y veto de auditoría CDI-A3 (#2785, CDI07)

## Alcance

Segunda entrega del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md), apilada
sobre la de [reportes](2026-11-10-2785-react-cdi-reportes.md): alta, ficha,
edición y baja de observaciones de un Centro de Desarrollo Infantil (CDI07 del
contrato `2026-10-28-2785-cdi-intervenciones-observaciones-m2.md`). El listado
de observaciones sigue en la ficha del centro, sin cambios.

Incluye la decisión CDI-A3 (`2026-10-28-2785-cdi-auditoria-a3.md`, elegida el
2026-10-28) para las tres operaciones de observaciones: quien es auditor SIMEPI
no puede crear, editar ni dar de baja observaciones, ni en las pantallas
nativas ni en la API. Usa el mismo predicado y las mismas excepciones que
CDI-A2 (`es_auditor_simepi`). Las otras cinco operaciones de CDI-A3
(intervenciones y adjuntos) no cambian en esta entrega.

No activa React en producción.

Archivos:

- `src/backends/cdi/centrodeinfancia/views.py`: las tres vistas nativas de
  alta, edición y baja suman `_AuditoriaSoloLecturaMixin`, el mismo que ya usan
  centros, nómina y trabajadores. Es el único cambio de comportamiento nativo.
- `src/backends/cdi/centrodeinfancia/web_api_observaciones.py` y
  `src/backends/cdi/centrodeinfancia/web_api_urls.py`: API web.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: cuatro entradas más.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdiObservaciones.tsx` y su prueba.
- Pruebas: `src/backends/cdi/centrodeinfancia/tests/test_web_observaciones.py`
  y casos nuevos en `src/backends/cdi/centrodeinfancia/tests/test_web_preview.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `/api/web/cdi/centros/<pk>/observaciones/crear/` | GET: centro del alcance (404 si no) y campo «Observación». POST: el servidor fija centro, observador (nombre y apellido o usuario) y fecha; vuelve a `next` si es del mismo sitio o al detalle |
| `/api/web/cdi/observaciones/<pk>/` | GET: ficha (centro, observador o «-», fecha y hora local, texto, enlaces Editar y Eliminar) |
| `/api/web/cdi/observaciones/<pk>/editar/` | GET/POST: mismo formulario; conserva el centro y vuelve al detalle |
| `/api/web/cdi/observaciones/<pk>/eliminar/` | GET: confirmación con el detalle de la baja en cascada. POST: baja lógica (`deleted_at`, `deleted_by`) y vuelta a la ficha del centro con «Observación dada de baja correctamente.» |

Cada vista de la API hereda la vista nativa, así que el formulario, el alcance
y los efectos son los mismos. Una redirección nativa se devuelve como
`{"ok": true, "redirect": ...}` y un formulario inválido como 400 con sus
errores. Solo se aceptan POST `application/x-www-form-urlencoded` (o sin
cuerpo); otro formato responde 415 sin escribir.

Acceso, en este orden: G1 (sesión y requisitos web, o la constancia firmada en
el runtime), el mismo permiso que la URL nativa (Add, View de Centro, Change o
Delete de Intervención; sin permisos nuevos de Observación) y después el
despacho nativo con el veto CDI-A3 en todo método que no sea GET, HEAD u
OPTIONS: 403 «El rol Auditoría tiene acceso de solo lectura.».

Veto CDI-A3: rechaza a quien tiene el grupo SIMEPI - Auditoría, también junto
con EGP o Equipo Nacional. No rechaza a superusuarios ni a quien además tiene
SIMEPI - Administrador o SIMEPI - Analista de datos. Las lecturas no cambian:
un auditor sigue viendo la ficha y los formularios.

Pantallas React: marco oscuro de `routes/cdiFrame.tsx`. El formulario reproduce
el campo de crispy (etiqueta con asterisco, `textarea` de 4 filas, error en
`invalid-feedback`), «Confirmar» y «Cancelar» (vuelve en el historial, como
`data-history-back`). El envío no se reintenta: si no se confirma el resultado,
se avisa y se desactiva el botón. Una redirección a otro sitio se descarta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 35 pruebas nuevas en rojo y luego en verde. Los rechazos comprueban
  que no cambian las filas (incluidas las dadas de baja) ni el historial de
  auditoría. Suite completa de CDI con `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends`: 1060 pasan y 3 se omiten.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego 10 de 10.
- Visual (regla S13) y G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- La diferencia del menú lateral de tercer nivel registrada en
  [reportes](2026-11-10-2785-react-cdi-reportes.md) también aparece acá. En
  estas rutas la versión nativa abre y marca «Centro de Infancia» por la ruta
  (`centrodeinfancia` en `pagina_actual`), algo que el marco compartido no
  reproduce.
- `safe_redirect` compara `next` con el host que ve el runtime; detrás del core
  un `next` absoluto con el host público puede caer en el detalle. Un `next`
  relativo, el caso de la ficha, funciona igual.
- Intervenciones y adjuntos (resto de CDI-A3) quedan para su propia entrega.
