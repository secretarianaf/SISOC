# Cambio: listado de encuestas y acciones de fila en React sobre G1 v1 (#2785, E04.A)

## Alcance

Tercera unidad del [contrato E02 a E04 y D01](../../../plans/2026-T4/2026-11-13-2785-encuestas-dashboard-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la pantalla `/encuestas/` con su barra de búsqueda por
filtros, la tabla, la bandeja de pendientes y las acciones de fila «Solicitar publicación» e «Importar». Lee por
`EncuestaListView` y escribe por las vistas nativas `EncuestaPublicarView` y `EncuestaImportarView` (y expone `RondaCerrarView`
sin interfaz, porque la plantilla nativa no dibuja ese control). No se tocan vistas, servicios, plantillas ni URLs nativas ni se
activa React en producción. La revisión, aprobar, rechazar y el formulario de alta y edición (E04.B y E04.C) siguen nativos.

Archivos:

- `src/backends/sisoc_core/encuestas/web_api_lista.py` (rutas en `web_api_urls.py`), ajuste de
  `web_transport_encuestas.py` (`consume=False`), `url_registry.json` y `config/middlewares/admindocs.py`.
- `src/backends/sisoc_core/encuestas/web_preview_encuestas.py`: entrada de vista previa de `/encuestas/`.
- `src/frontends/apps/sisoc/src/routes/encuestasLista.tsx`, registrado en `routes/index.ts`.
- Pruebas: `test_web_lista_api.py`, `test_web_preview_encuestas.py` y `encuestasLista.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `encuestas.view_encuesta` o `encuestas.ver_resultados` (403), igual que la URL nativa. La
  solicitud de publicación exige `change_encuesta`; el cierre manual de ronda, `change_rondaencuesta`. CSRF obligatorio (403).
- La lista corre la vista nativa: filtros del motor `FILTER_ENGINE`, orden, 20 por página, página inválida 404 y los enlaces
  antiguos `busqueda` y `estado` con su redirect a `filters`. Las banderas `puede_*` y la bandeja de pendientes se calculan con
  los mismos permisos que la plantilla.
- «Solicitar publicación» y «Importar» dejan el mensaje del servicio en cola y navegan al redirect, igual que el formulario
  nativo: la lista recargada lo muestra una vez como toast al final de `<body>`. Un rechazo (por ejemplo, una encuesta sin
  preguntas o un archivo inválido) no cambia nada y muestra el error del servicio. «Importar» muestra el indicador de espera y
  deshabilita el botón mientras se envía.
- `POST /api/web/encuestas/rondas/<pk>/cerrar/` cierra la ronda con `cerrar_ronda(manual=True)`; repetirlo devuelve el error
  nativo sin cambiar la fecha de cierre real.

## Verificación

- Backend (imagen fijada, sin red): 11 pruebas nuevas de la API (acceso, comparación de los textos con la página nativa, filtros,
  enlaces antiguos, paginación, bandeja, solicitud de publicación con efecto persistido y rechazo sin cambios, cierre de ronda) y
  1 de la vista previa; `black`, `pylint` y `makemigrations --check`.
- Frontend: 10 pruebas nuevas, `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo (401, 403, requisito pendiente, cabecera falsificada, CSRF, lectura, solicitud persistida y mensaje
  mostrado una sola vez).
- Comparación visual nativo contra React (gestora, aprobadora, lectora, filtrada, vacía, publicación rechazada e importación
  inválida; escritorio y móvil) y guardas.

## Limitaciones

La página 2 de la lista no entra en la comparación visual. El flujo de importación acepta archivos de hasta lo que admita el
servicio nativo; el tope y su mensaje son los de `importar_encuesta`.
