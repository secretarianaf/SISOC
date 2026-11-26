# Cambio: operativos de DataCalle en React sobre G1 v1 (#2785, DC01.01 a DC01.03)

## Alcance

Backoffice web de los operativos de DataCalle sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): listado
(`/datacalle/relevamientos/`), ficha (`/datacalle/relevamientos/<uuid>/`), alta
(`crear/`), edición (`<uuid>/editar/`), baja (`<uuid>/eliminar/`) y cierre
(`<uuid>/cerrar/`). Contrato:
[DataCalle DC01-DC02](../../../plans/2026-T4/2026-11-10-2785-datacalle-dc01-dc02-contratos.md).
Sigue el patrón de [Dispositivos](2026-11-11-2785-react-dispositivos-consulta.md),
que comparte el runtime y el prefijo `api/web/dispositivos/`.

Fuera de esta unidad: la ficha del caso (DC02.01) y la regresión del consumidor de
campo (DC02.03). DC02.02 no tiene operación web nativa que migrar. La app SISOC -
Mobile y la API por token `api/datacalle/` no cambian. No activa React en producción.

Archivos:

- `src/backends/dispositivos/datacalle/web_api.py` y
  `src/backends/dispositivos/datacalle/web_api_urls.py`: API web bajo
  `/api/web/dispositivos/datacalle/`. Reutiliza `DispositivosWebView`, `native_view`,
  `pending_messages` y la proyección del listado de `src/backends/dispositivos/dispositivos/web_api.py`.
- `src/backends/dispositivos/dispositivos_runtime/web_api_urls.py`: suma la inclusión
  `datacalle/`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera del
  atajo HEAD de admindocs. `src/backends/config/url_registry.json` se regeneró con
  `generar_registro_urls` (solo altas).
- `src/backends/dispositivos/datacalle/web_preview.py`: entradas React sin montar
  (`datacalle_preview_patterns`), solo para un URLconf local; assets en
  `/datacalle/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/`: `datacalleRelevamientos.tsx` (ruta de la
  unidad: listado, ficha, cierre y baja), `datacalleRelevamientoForm.tsx` (alta y
  edición) y `datacalleSelect2.tsx` (Select2 4.1.0-beta.1 como lo arma `custom.js`).
- Pruebas: `src/backends/dispositivos/tests/test_web_datacalle_relevamientos.py`,
  `src/backends/dispositivos/tests/test_web_datacalle_preview.py` y
  `src/frontends/apps/sisoc/src/routes/datacalleRelevamientos.test.tsx`.

## Comportamiento

| Ruta (`/api/web/dispositivos/datacalle/`) | Permiso nativo | Comportamiento |
|---|---|---|
| `GET relevamientos/` | `view_relevamiento` | Corre `RelevamientoListView`: alcance provincial, `estado`, `fase`, `busqueda`, página de 15. Sobre de Insumos más `page_range`, `query_prefix`, `resumen`, opciones de filtros, `add_url` y `can_change`. Página inválida: 404 «Página no válida.» |
| `GET relevamientos/<uuid>/` | `view_relevamiento` | Corre `RelevamientoDetailView`: fuera de alcance o inexistente, 404. Ficha, `resumen_de_casos`, equipo, cierre y hasta 50 casos |
| `GET relevamientos/formulario/` | `add_relevamiento` | `RelevamientoForm` vacío con `actor`: campos, etiquetas, ayudas y opciones |
| `POST relevamientos/crear/` | `add_relevamiento` | `form_valid` nativo (`save_relevamiento_from_form`): 201 `{id, url}`; 400 con el formulario ligado y `errors` (`get_json_data()`) |
| `GET relevamientos/<uuid>/formulario/` | `change_relevamiento` | Formulario con los valores guardados; alcance 404 |
| `POST relevamientos/<uuid>/editar/` | `change_relevamiento` | Igual que el alta, 200 |
| `POST relevamientos/<uuid>/cerrar/` | `change_relevamiento` | `cerrar_relevamiento`: 200 `{cerrado_ahora, message, level, url}` y el mismo mensaje encolado que el nativo; repetido no cambia nada |
| `GET/POST relevamientos/<uuid>/eliminar/` | `delete_relevamiento` | Confirmación; el POST corre el `form_valid` nativo (`delete_relevamiento`) y responde `{url}` del listado |
| `GET opciones/dispositivos/`, `opciones/relevadores/` | `view_relevamiento` | El mismo cuerpo que `cargar_dispositivos` / `cargar_relevadores` (los usa la cascada del formulario) |

Acceso, en este orden: sesión y requisitos web (G1), después el permiso nativo
(403 antes de buscar el objeto) y el alcance de `apply_relevamientos_scope`. El
POST exige CSRF. Respuestas `private, no-store`; otros métodos, 405 (GET al cierre
incluido, como el nativo).

Efectos persistidos (comparados contra la ruta nativa en las pruebas):

- Alta y edición: `creado_por` solo en el alta; cambiar el equipo cambia qué
  entrevistadores ven el operativo en `mis_relevamientos` de la API por token.
  Sin mensaje de éxito, como el nativo.
- Cierre: estado `finalizado`, `fecha_cierre` y `cerrado_por` en el primer cierre;
  el repetido devuelve `cerrado_ahora: false` y «El relevamiento ya estaba
  cerrado.» (nivel `info`) sin tocar el registro. No exige rol de coordinador
  DataCalle (asimetría nativa con la API por token).
- Baja: baja lógica en cascada. Observado igual por las dos vías: el operativo y
  sus casos (`Encuesta`) quedan con `deleted_at`, desaparecen del listado, de la
  ficha y de `mis_relevamientos`. Sin mensaje.

Pantallas React: misma estructura que `relevamiento_list.html`,
`relevamiento_detail.html`, `relevamiento_form.html` (crispy Bootstrap 5, Select2,
su script de fase y cascada) y `relevamiento_confirm_delete.html`, con los textos
literales del contrato. El cierre no pide confirmación (como el nativo) y nunca se
reintenta solo: con respuesta va a la ficha que indica la API; ante un 504
`uncertain` o sin respuesta recarga la ficha, que muestra el estado real y decide
si el botón vuelve. Un guardado incierto deja el botón deshabilitado con el aviso
«No se pudo confirmar el resultado. Verificá el estado antes de reintentar.»
(diferencia de plataforma: el nativo no tiene ese estado).

Quirks conservados:

- El `resumen` del listado cuenta todo el alcance, sin filtros.
- La paginación conserva `estado` y `fase` pero no `busqueda` (el componente no
  recibe `query`).
- El orden de `Meta.ordering` no aplica: el `annotate(Count)` de
  `get_relevamientos_queryset` hace que Django ignore el orden del modelo en la
  consulta agrupada (aviso `UnorderedObjectListWarning`). La API corre la misma
  consulta, así que muestra el mismo orden que la página nativa.
- La ficha muestra hasta 50 casos sin aviso de truncado y el enlace «Ver» del caso
  sin chequear `view_encuesta`.
- «Punto GPS» con `lat = 0` se ve como «—».
- Mensajes del contrato que el formulario no puede emitir: el municipio, las
  localidades, el dispositivo y el equipo se acotan en el queryset, así que un valor
  de otra provincia o municipio da «Escoja una opción válida...» antes de llegar a
  «El municipio no pertenece a la provincia seleccionada.», «Hay localidades que
  no pertenecen al municipio elegido: ...», «El dispositivo no pertenece a la
  provincia seleccionada.» o «Hay integrantes que no son entrevistadores...». La
  API devuelve exactamente los errores del formulario nativo en cada caso (probado
  escenario por escenario).

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (la API: 36 fallas sobre la base; la entrada React:
  error de colección por módulo inexistente) y luego en verde (46). Suite de
  `dispositivos`, `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`
  (registro de URLs incluido): 418 en verde. Colección completa sin errores,
  `black`, `pylint` 10/10 y `makemigrations --check` sin cambios.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (13); `tsc`,
  ESLint y build de Vite sin errores. Vitest del proyecto sisoc: dos corridas completas
  en verde; en la tercera falló una prueba de otra pantalla (Select2 de Inspecciones),
  que no toca esta unidad.
- G1 de punta a punta (core y runtime en contenedores separados): listado, alta por
  el formulario React con cascada, cierre con su mensaje mostrado una sola vez y baja
  por la confirmación, todo a través del core. Anónimo 401, sin permiso 403, requisito
  pendiente 403, cabecera falsificada ignorada, POST sin CSRF 403, cierre repetido 200
  sin cambios, GET al cierre 405. Consulta directa al runtime sin constancia, alterada,
  de otro destino, usuario o audiencia, vencida (61 s) o futura: 403; dentro de 58 s: 200.
- Visual (regla S13), nativo contra React, 19 estados en 1440x900 y 390x844 (listado,
  página 2, filtrado, búsqueda, vacío, lector, coordinador provincial, ficha completa,
  cerrada, vacía, con 50 casos y de lector, alta, alta con provincia fija, validación de
  fase en el cliente, edición, edición de alojamiento, edición con errores, baja): 38/38
  con diferencia perceptual 0 % y desvío geométrico de 0,05 px como máximo; las 10
  guardas (anónimo, sin permiso, lector, página inválida, inexistente, fuera de
  alcance) responden igual en las dos versiones.

## Limitaciones

- La ficha del caso (`/datacalle/casos/<uuid>/`) sigue en HTML nativo hasta DC02.01;
  el enlace «Ver» de la ficha apunta a esa ruta.
- Diferencias del marco compartido `SisocShell`, fuera de esta unidad: el logo tiene
  `aria-label` y en móvil cambia el marcado del menú (menú móvil fuera de la
  comparación).
