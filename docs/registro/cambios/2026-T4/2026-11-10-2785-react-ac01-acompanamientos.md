# Cambio: seguimiento de acompañamiento e hitos en React sobre G1 v1 (#2785, AC01)

## Alcance

Entregas AC01.01 (listado, ficha e hitos, CSV nativo) y AC01.02 (restaurar
hito) del
[contrato AC01](../../../plans/2026-T4/2026-11-10-2785-acompanamientos-seguimiento-hitos-ac01-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).
No cambia vistas, servicios, modelos, plantillas ni URLs nativas. No activa
React en producción.

Archivos:

- `src/backends/comedores/acompanamientos/web_api.py` y
  `src/backends/comedores/acompanamientos/web_api_urls.py`, incluidos desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado.
- `src/backends/config/middlewares/admindocs.py`: rutas nuevas fuera del atajo HEAD.
- `src/backends/comedores/acompanamientos/web_preview.py`: entradas sin montar
  (`acompanamientos_preview_patterns`), assets en `/acompanamientos/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/acompanamientos.tsx` (ruta y ficha) y
  `routes/acompanamientosList.tsx` (listado), registrados en `routes/index.ts`.
- Pruebas: `src/backends/comedores/acompanamientos/tests/test_web_acompanamientos_api.py`,
  `src/backends/comedores/acompanamientos/tests/test_web_preview_acompanamientos.py` y
  `src/frontends/apps/sisoc/src/routes/acompanamientos.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/acompanamientos/` | `ComedoresAcompanamientoListView`: alcance, búsqueda, filtros avanzados, orden `nombre`/`-nombre`, preferencias de columnas, 10 por página, página inválida 404 |
| `GET /api/web/comedores/acompanamientos/<comedor_id>/?admision_id=` | `AcompanamientoDetailView`: convenios, admisión resuelta, información relevante, prestaciones, 23 hitos con fecha y `puede_restaurar`; fuera de alcance 404 |
| `POST /api/web/comedores/acompanamientos/<comedor_id>/hitos/restaurar/` | `campo` y `admision_id`: 200 con `{"ok": true, "message", "redirect"}`; 400 «El campo '<campo>' no existe en el modelo Hitos.»; 409 «No se encontraron hitos para el convenio seleccionado.»; 404 fuera de alcance; 403 sin las dos guardas |

Acceso: G1 y después las guardas nativas sin cambios
(`acompanamientos.view_informacionrelevante` para leer; `auth.role_tecnico_comedor`
y `acompanamientos.change_hitos` para restaurar, superusuario incluido).

Restaurar repite `restaurar_hito` (alcance, hitos del convenio, `False` y
`save()`, mensaje nativo, que muestra la ficha siguiente) con las dos
decisiones del contrato: `admision_id` explícito, sin Referer, y lista blanca
de los 23 hitos booleanos. La vista Django queda como está (bugs AC01-B1 a B3
sin cambios). La pantalla no reintenta: 400/409 muestran el texto nativo y un
resultado incierto (por ejemplo 504) ofrece recargar la ficha. Tras restaurar,
React vuelve a la ficha con `?admision_id=` del convenio mostrado; la vista
nativa vuelve al Referer.

El CSV sigue siendo el GET nativo `/acompanamientos/acompanamiento/exportar/`
con la consulta actual. El encabezado `<h2>` del comedor (bloque `app-header`)
se dibuja en la fila vacía que deja `SisocShell`.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo sobre la base (20 de 21 de la API; la entrada
  sin módulo) y en verde (25).
- Frontend: prueba de ruta en rojo (sin módulo) y en verde (7); `tsc`, ESLint y build.
- Visual (S13), 11 estados por rol (lector, técnico sin alcance, superusuario):
  listado, página 2 con orden, búsqueda, vacío, ficha completa, convenio
  cerrado, dos convenios activos, sin hitos y admisión ajena, en 1440x900 y
  390x844: contenido fuera del menú igual, desvío máximo 0,02 px, diferencia
  de píxeles ≤ 0,002 %. Guardas iguales (anónimo y sin permiso 403, ficha fuera
  de alcance y página inválida 404).
- Recorrido: restaurar desde React y desde el HTML deja el mismo estado y el
  mismo mensaje; un lector no tiene botones habilitados.

## Limitaciones

- El listado repite el filtro combinable y el modal de columnas de
  `routes/duplasList.tsx`, que no los exporta; conviene extraerlos a un módulo
  compartido.
- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo y
  menú móvil, igual que en las otras pantallas.
- Hallazgo: en la ficha nativa, «Vencimiento de Mandato» sin fecha se muestra
  vacío (`None|date` da `""` y `default_if_none` no aplica), no «—»; React
  conserva ese comportamiento.
