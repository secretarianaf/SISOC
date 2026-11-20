# Cambio: baja de intervenciones de comedor en React (#2785, CO02)

## Alcance

Tercera entrega de la lane K4 del contrato
[`2026-10-28-2785-comedores-intervenciones-observaciones-m2.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-intervenciones-observaciones-m2.md),
sobre la de [formulario](2026-11-13-2785-react-comedor-intervenciones-formulario.md):
la confirmación de baja lógica de una intervención
(`intervencion_confirm_delete.html` sobre `components/delete_confirm.html`). Con
esta entrega CO02 queda completo salvo la subida de archivo, que no tiene
pantalla. No activa React en producción y no cambia ninguna vista, ruta ni
permiso nativo.

Archivos:

- `src/backends/comedores/intervenciones/web_api_baja.py` y `web_api_urls.py`.
- `src/backends/comedores/intervenciones/web_preview.py`: entradas de alta,
  edición y baja (las dos primeras corresponden a la entrega anterior).
- `src/backends/config/url_registry.json` (regenerado) y
  `src/backends/config/middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/comedorIntervencionesBaja.tsx` y su
  prueba; `comedorIntervenciones.tsx` suma la ruta nativa.
- Pruebas de backend: `test_web_intervenciones_baja_k4.py` y
  `test_web_preview_intervenciones_k4.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/intervenciones/comedor/<comedor_id>/baja/<intervencion_id>/` | Ejecuta `IntervencionDeleteView`: nombre en mayúsculas, vista previa de la baja en cascada, textos de los botones y enlace de vuelta al listado |
| `POST` a la misma ruta | Ejecuta el `post()` nativo: baja lógica con `deleted_at` y `deleted_by`, mensaje «Intervención dada de baja correctamente.» y `{"ok": true, "redirect": <listado>}` |

Acceso, en este orden: G1 y el permiso de la URL nativa,
`comedores.delete_nomina` (el superusuario pasa siempre). Ese permiso no tiene
relación con las intervenciones: el contrato pide caracterizarlo, no
reemplazarlo, y se conserva. La intervención se busca solo por su id:
`comedor_id` es únicamente el destino de vuelta y la migaja, sin comprobar que
la intervención sea de ese comedor (diferencia conservada). Un id inexistente
responde 404.

La migaja de la plantilla se conserva tal cual: «Admisiones» enlaza a la
misma página y el segundo enlace apunta a la ficha de comedor con el id de la
intervención (no el del comedor). El componente de confirmación
(`BajaContent`) es el mismo que usa la baja de observaciones.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 4 pruebas de baja y 2 de la vista previa, en rojo y luego en verde:
  proyección, baja lógica con actor y mensaje, comedor de retorno distinto,
  rechazos (sin sesión, sin permiso, sin CSRF, inexistente) sin cambiar la fila.
- Frontend: 4 pruebas nuevas (el módulo no existía); `tsc`, `eslint` y la
  compilación sin errores.
- Visual (regla S13) y G1 de punta a punta: ver el informe de la entrega.

## Limitaciones

- La plantilla nativa envía `href=""` en «Admisiones»; React lo reemplaza por
  la ruta actual, que es adonde apunta el nativo.
- Sin protección adicional: cualquier usuario con `comedores.delete_nomina`
  puede dar de baja cualquier intervención (hallazgo residual del contrato).
