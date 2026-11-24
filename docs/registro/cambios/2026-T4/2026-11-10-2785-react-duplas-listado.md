# Cambio: listado y ficha de Duplas en React sobre G1 v1 (#2785, DU01.01)

## Alcance

Listado de equipos técnicos (`/equipo-tecnico/`) y ficha
(`/equipo-tecnico/<pk>/`) de Comedores, del
[contrato de Duplas](../../../plans/2026-T4/2026-10-28-2785-duplas-equipo-asignaciones-m2.md)
(DU01.01). Sigue el patrón del
[piloto de Inspecciones](2026-11-10-2785-react-inspecciones-actas.md) sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md). El alta,
la edición y la baja son DU01.02. La asignación a un comedor (`dupla_asignar`)
queda afuera.

No cambia vistas, formularios, señales, plantillas, JavaScript ni el CSV
nativos. No activa React en producción.

Archivos:

- `src/backends/comedores/duplas/web_api.py` y
  `src/backends/comedores/duplas/web_api_urls.py`: API web.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`: agregador de
  `/api/web/comedores/` (cada app suma su `include`), montado en
  `src/backends/comedores/comedores_runtime/urls.py`.
- `src/backends/config/backends.json`: prefijo `api/web/comedores/`.
  `src/backends/config/url_registry.json` se regeneró con
  `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/comedores/duplas/web_preview.py`: entradas React sin montar
  (`duplas_preview_patterns`).
- `src/frontends/apps/sisoc/src/routes/`: `duplas.tsx` (ruta),
  `duplasList.tsx`, `duplasDetail.tsx` y `duplasShared.tsx`.
- `src/frontends/apps/sisoc/src/identityFrames.tsx` y
  `src/frontends/apps/sisoc/src/routes/SisocShell.tsx`: parámetro opcional
  `activePath`. Sin él, el marco se comporta igual que antes.
- Pruebas: `src/backends/comedores/duplas/test_web_duplas.py`,
  `src/backends/comedores/duplas/test_web_duplas_preview.py` y
  `src/frontends/apps/sisoc/src/routes/duplas.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/duplas/` | Corre `DuplaListView`: 10 por página, orden `-fecha, nombre`, filtros combinables (`contains`, `ncontains`, `eq`, `ne`, `empty`) con resultados únicos, columnas según `duplas_list` y 404 de página inválida. Devuelve breadcrumb, configuración de filtros, sección de favoritos `duplas`, URLs, encabezados, filas con sus acciones, paginación y mensajes pendientes |
| `GET /api/web/comedores/duplas/<pk>/` | Corre `DuplaDetailView`: nombre, estado, técnicos, abogado, coordinador (o `null`, «Sin asignar»), fecha `d/m/Y H:i` y URLs de editar y eliminar. 404 si no existe o está dado de baja |

Acceso:

1. Igual que el piloto: el core exige sesión (401) y los requisitos web (403
   con `state`), firma y reenvía. El runtime solo atiende lo que
   `WebGateMiddleware` verificó. En el monolito, `WebGatePermission` evalúa la
   política local.
2. Después, la regla nativa sin cambios: `auth.role_admin` con el mismo
   predicado de `permissions_any_required` (superusuario incluido).
   `role_exportar_a_csv` no abre el listado.
3. CSV: sigue siendo `/equipo-tecnico/exportar/`, sin ruta en la API. El botón
   «Exportar búsqueda» aparece con la regla de `search_bar.html`: superusuario
   o `role_exportar_a_csv`. Hoy la URL acepta cualquiera de los dos roles, pero
   `CSVExportMixin` además exige `role_exportar_a_csv`. Se conserva tal cual.

Las lecturas no escriben en la base. Otros métodos responden 405.

Pantalla React: usa el marco `includes/main.html` (Volver, título y
breadcrumb) y agrega la clase `app-loaded` al `body`, como AdminLTE. Reproduce
`search_bar.html` en modo filtros (filas «+ Filtro»/«- Filtro», el operador sale
del tipo de campo, el formulario GET serializa `filters` como
`advanced_filters.js`), la tabla con orden en el cliente (`listSort.js`, incluido
el orden de clases de los íconos), el modal de columnas (`column_config.js`,
POST a `/ajax/columnas-preferencias/` y recarga), la paginación y el botón de
CSV (`export_helper.js`: misma URL con filtros y orden). Con 0 resultados no
muestra «Se encontraron…», igual que la plantilla. La ficha carga `hitos.css`
y `cardsDetail.css` como la página nativa.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (30 de 33; la de vista previa sin módulo) y
  luego en verde. Suite de Duplas, `test_web_gate`, `test_backend_proxy`,
  `test_servicios_backends` (incluye el registro de URLs): 140 pasan. `black`,
  `pylint` 10/10, `makemigrations --check` y `check` sin cambios.
- Frontend: prueba de ruta en rojo (sin módulo) y luego 11 de 11. Vitest del
  workspace, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 7 estados (listado, filtro, dos
  filtros, sin resultados, sin botón de CSV, ficha con y sin coordinador) en
  1440x900 y 390x844: 0 % de píxeles distintos, desvío geométrico 0 px, mismos
  textos, controles y estilos. Mismo recorrido de filtros, orden, CSV,
  paginación, Resetear y modal de columnas (18 pasos iguales). Las guardas
  (anónimo, sin rol, página o equipo inexistente) responden igual.
- G1 de punta a punta: ver el registro de DU01.02, que corrió sobre el árbol
  acumulado.

## Limitaciones

- Orden de Tab igual elemento por elemento. Diferencia ya conocida del marco:
  el logo tiene nombre accesible («Inicio de SISOC») en React y no en la página
  nativa.
- El menú móvil abierto está fuera de la comparación, por la excepción vigente.
  En el menú colapsado, React deja en el DOM, fuera de pantalla, la rama abierta
  que AdminLTE oculta. No se ve y los píxeles son iguales.
- La comparación usó la fuente de reemplazo (Google Fonts bloqueado sin red).
