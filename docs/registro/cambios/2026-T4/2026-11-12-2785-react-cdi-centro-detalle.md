# Cambio: ficha (legajo) del centro CDI en React sobre G1 v1 (#2785, CDI09.01)

## Alcance

Sexta entrega del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la ficha
de un centro (`/centrodeinfancia/detalle/<centro>`), parte de CDI09.01 del
contrato `2026-10-28-2785-cdi-centros-y-credenciales.md`. Incluye las tres
acciones de la propia pantalla: cambiar el estado de un usuario del centro
(suspender, reactivar, dar de baja), eliminar un trabajador y agregar una
observación desde su modal. El alta, la edición y la baja del centro, la
generación de usuarios, las altas y ediciones de trabajadores, los formularios y
la nómina siguen nativos y la ficha los enlaza igual que el HTML. No activa
React en producción y no cambia el comportamiento nativo. No se consulta RENAPER
ni ningún servicio externo.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_legajo.py` y `web_api_urls.py`.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json`.
- `src/frontends/apps/sisoc/src/routes/cdiCentroDetalle.tsx` y su prueba;
  `cdiFrame.tsx` acepta ahora el bloque `app-header` de la página.
- Pruebas: `tests/test_web_centro_legajo.py` y un caso en `test_web_preview_cdi.py`.

## Comportamiento

`GET /api/web/cdi/centros/<pk>/` ejecuta `CentroDeInfanciaDetailView`: el centro
sale del alcance del actor (404 fuera de él), las métricas, los trabajadores, la
tabla de observaciones (páginas de 5) y la tabla de usuarios salen del mismo
contexto que el HTML. Cada campo se renderiza con la expresión de
`centrodeinfancia_detail.html` (`default:"-"`, fechas localizadas), y una prueba
compara los pares etiqueta y valor con el HTML nativo. Las tarjetas de
formularios y de calidad siguen sus mismos permisos y la bandera
`CDI_FORMULARIOS_VISIBLE`.

Credenciales (CDI-CR1): la contraseña temporal sale solo para el superusuario o
la cuenta propia de cada fila, igual que el template, la respuesta es
`private, no-store` y el valor no entra en ningún contexto compartido ni en
almacenamiento del navegador.

Escrituras: `POST /api/web/cdi/centros/<pk>/usuarios/<acceso>/estado/` llama a
`cambiar_estado_usuario_cdi` y `POST /api/web/cdi/centros/<pk>/trabajadores/<id>/eliminar/`
a `TrabajadorCentroInfanciaDeleteView`, sin cambios: reglas del servicio (propio
usuario, responsable, motivo), baja lógica, mensajes y veto de auditoría CDI-A3 son
los nativos. Delante solo agregan G1, el permiso de la URL nativa y CSRF. La
redirección nativa pasa a `{"ok": true, "redirect": ...}` y el mensaje queda en la
sesión: la pantalla recarga la ficha (con `#usuarios` si corresponde) y lo muestra
como el HTML. La observación usa el alta existente
`/api/web/cdi/centros/<pk>/observaciones/crear/`.

Mientras `CDI_INTERVENCIONES_VISIBLE` esté activa (apagada en todos los
entornos) la API responde 409 y la entrada de vista previa sirve la página nativa:
la tarjeta de intervenciones y su modal todavía no están en React.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 18 casos nuevos y un caso de vista previa (escritos junto con la
  implementación, sin corrida en rojo previa). La ficha se compara con el HTML
  nativo (pares etiqueta y valor, métricas, mapa); los permisos de credenciales por
  fila, el alcance, los métodos, CSRF, el veto de auditoría y la bandera de
  intervenciones están cubiertos, y cada rechazo (sin motivo, acción inválida,
  estado inválido, propio usuario, responsable, otro centro, sin permiso) deja
  accesos, trabajadores y auditoría idénticos. Suite combinada de CDI y del núcleo
  (puerta web, proxy, servicios): 226 pasan; black y pylint 10/10 en los archivos
  nuevos; `makemigrations --check` sin cambios; `url_registry.json` regenerado
  (tres nombres nuevos).
- Frontend: 10 pruebas de ruta; una corrida completa de `vitest` (820), `tsc`,
  `eslint` y `vite build`. Dos pruebas de rutas vecinas (`cdiCentros`,
  `cdiObservaciones`) afirmaban que la ficha era «business» y ahora esperan la
  ruta nueva.
- G1 de punta a punta: anónimo 401, sin permiso 403, requisito pendiente 403,
  cabecera falsificada ignorada, CSRF 403, ficha 200, centro ajeno 404, cambio de
  estado rechazado sin efecto, cambio de estado 200 persistido, baja de trabajador
  sin permiso 403, baja 200 y repetición 404.
- Visual (regla S13), escritorio y móvil, ficha completa, ficha mínima, solapa de
  usuarios, modal de estado, rechazo del servidor con aviso, modal de observación y
  modal de baja: mismas etiquetas, controles, orden y Tab, diferencia geométrica
  máxima de 0,02 px y diferencia de píxeles de 0,000 % a 0,058 %, y mismos 403 y 404
  de guardas.

## Limitaciones

- Un rechazo del servidor al crear la observación (texto en blanco) se muestra en
  el mismo modal; el HTML recarga la pantalla de alta. El `required` del navegador
  evita el caso habitual.
- El menú «Acciones» no usa Popper: se ubica con CSS como un menú estático.
- Intervenciones: ver arriba.
- Mismas diferencias del marco compartido que el
  [listado](2026-11-12-2785-react-cdi-centros-listado.md).
