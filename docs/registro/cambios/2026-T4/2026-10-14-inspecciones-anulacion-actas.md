# Inspecciones escolares: anulación de actas y acta de prueba (backend)

Fecha: 2026-10-14. Rama: `feat/inspecciones-anulacion`. Antecedente:
`docs/registro/cambios/2026-T4/2026-10-14-inspecciones-escolares-backend.md`.
Fuente funcional: especificación de la PWA, §7 (estado Anulada) y §9
(indicadores de actas válidas).

## Qué cambia

- `inspecciones.services.anulacion`:
  - `anular_acta(acta, motivo, actor)`: exige un motivo de al menos 10
    caracteres (sin contar espacios sobrantes) y rechaza un acta ya anulada
    (`ValidationError`). En una transacción, con el acta bloqueada
    (`select_for_update`), pone `estado=anulada`, `anulada_at`, `anulada_por` y
    `motivo_anulacion`, y registra el evento `anulada` con actor, fecha y
    motivo. No toca número, instantánea, PDF ni notificaciones.
  - `marcar_prueba(acta, es_prueba, actor)`: cambia `es_prueba` y registra un
    evento; rechaza un acta anulada. Si el valor no cambia, no registra nada.
- Backoffice (sólo POST, `puede_gestionar_inspecciones`; sin permiso 403, sin
  sesión al login, número inexistente 404):
  - `POST /inspecciones/actas/<numero>/anular/` (`inspecciones_anular_acta`),
    campo `motivo`.
  - `POST /inspecciones/actas/<numero>/prueba/`
    (`inspecciones_marcar_prueba_acta`), campo `es_prueba` = `1` | `0`.
  - Redirigen a `next` si es una ruta del mismo host
    (`url_has_allowed_host_and_scheme`); si no, al detalle del acta
    (`inspecciones_acta_detalle`) o, si esa ruta no existe, al panel. El
    resultado se muestra con `django.contrib.messages`.
  - `src/backends/config/url_registry.json` regenerado con los dos nombres.
- API `/api/inspecciones/actas/` (listado y detalle): el resumen suma
  `anulada_at` (ISO o `null`) y `motivo_anulacion` (texto o `null`). Las actas
  anuladas siguen visibles para su autor y coordinación con
  `estado: "anulada"`; el historial muestra el evento `anulada`.

## Efecto en la PWA

- Un acta anulada no cuenta como visita válida: en
  `GET /escuelas/asignadas/` la escuela vuelve a `pendiente` y desaparece de
  `visitas_hoy` en la ficha (esos servicios ya filtraban por
  `estado=finalizada`; ahora queda cubierto por tests). El inspector puede
  registrar otra visita del mismo turno sin motivo de nueva visita y sin pisar
  la anterior, que se conserva anulada.
- Cargar la notificación en papel sobre un acta anulada sigue respondiendo 409.

## Decisiones

- **Evento de la marca de prueba**: `EventoInspeccion.Accion` no tiene una
  acción propia y sumarla requiere una migración. Se registra como `editada`
  con `detalle = {"campo": "es_prueba", "es_prueba": true|false}`. `editada` no
  se muestra en el historial del acta (`ACCIONES_VISIBLES`); queda para
  auditoría. Si hace falta mostrarla, sumar la acción en una migración futura.
- **Permiso**: lo valida la vista, igual que el resto del backoffice; el
  servicio no repite el chequeo.
- Sin migraciones.

## Pendiente fuera de este cambio

- Los totales del panel (`services/panel.py`) ya excluyen anuladas, pero no las
  actas de prueba; el panel y el dashboard son de otro cambio.

## Validación

`src/backends/inspecciones/tests/test_inspecciones_anulacion.py` (servicio,
vistas, efecto en asignadas, ficha, notificación y API) y
`test_anulaciones_simultaneas_anulan_una_sola_vez` (`mysql_compat`) en
`test_inspecciones_concurrencia.py`.
