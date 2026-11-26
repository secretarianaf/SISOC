# Cambio: colaboradores de comedor en React sobre G1 v1 (#2785, CO03.01)

## Alcance

Primera entrega de la lane K6 del contrato
[`2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md`](../../../plans/2026-T4/2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md):
alta con búsqueda de ciudadano y edición de un colaborador del espacio
(`/comedores/<id>/colaboradores/crear/` y
`/comedores/<id>/colaboradores/<colaborador>/editar/`). El catálogo PNUD
(CO04.02) ya estaba migrado en
[`2026-11-10-2785-react-actividades-pnud.md`](2026-11-10-2785-react-actividades-pnud.md).
No activa React en producción y no cambia ninguna vista, formulario, servicio,
modelo, plantilla, ruta ni permiso nativo.

Un colaborador no es un usuario de acceso: asociar una persona no crea ni
otorga ningún usuario, y la edición nunca borra ni modifica al ciudadano.

Archivos:

- `src/backends/comedores/comedores/web_api_colaboradores.py` y
  `web_api_colaboradores_urls.py`: API web.
- `src/backends/comedores/comedores/web_preview_colaboradores.py`: dos entradas
  de la vista previa local.
- `src/backends/comedores/comedores_runtime/web_api_urls.py`,
  `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/comedorColaboradores.tsx` y su prueba.
- Pruebas: `src/backends/comedores/comedores/tests/test_web_colaboradores_k6.py`
  y `test_web_preview_colaboradores_k6.py`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET/POST /api/web/comedores/colaboradores/comedor/<pk>/crear/` | GET con `query` (DNI) o `ciudadano_id`: búsqueda local y, si no hay ciudadano, RENAPER; vista previa de la persona, aviso si ya es colaboradora y formulario. POST: `ciudadano_id` o `dni` más los campos del formulario |
| `GET/POST /api/web/comedores/colaboradores/comedor/<pk>/<pk2>/editar/` | Persona asociada y formulario con los valores actuales; solo colaboradores activos del comedor |
| `POST /api/web/comedores/colaboradores/comedor/<pk>/<pk2>/eliminar/` | Baja lógica nativa (`fecha_baja`, auditoría); la repetida solo responde «El colaborador ya se encuentra dado de baja.». Sin pantalla propia: el botón vive en la ficha del comedor |

Cada endpoint ejecuta el `dispatch` de la vista nativa
(`comedores/views/colaborador.py`), de modo que el comedor del alcance, el
veto de alta para «Abordaje Comunitario - Línea Secos» (404; la edición y la baja
no lo tienen), `ColaboradorEspacioForm` y `ColaboradorEspacioService`
(ciudadano, actividades, actor modificador y snapshot de auditoría) son los
mismos. Una redirección nativa se devuelve como `{"ok": true, "redirect": ...}`
y un rechazo como 400 con el formulario ligado, sus errores y los mensajes;
un rechazo no escribe nada. Solo se aceptan POST `application/x-www-form-urlencoded`
o `multipart/form-data` (otro formato responde 415) y las escrituras exigen CSRF.

Acceso, en este orden: G1, el permiso de la URL nativa
(`comedores.add_colaboradorespacio`, `change_colaboradorespacio` o
`delete_colaboradorespacio`; el superusuario pasa siempre) y el alcance de la
vista nativa. Sin cambios respecto de hoy.

Mensajes nativos conservados: «Colaborador agregado correctamente al espacio.»,
«Colaborador actualizado correctamente.», «Colaborador dado de baja
correctamente.», «La persona ya se encuentra registrada como colaborador de este
espacio.», «Debe buscar un ciudadano o consultar RENAPER antes de guardar el
colaborador.», «Errores en el formulario del colaborador.», «Ingrese un DNI
numérico válido para realizar la búsqueda.» y el texto de RENAPER.

Pantalla React: mismo marcado que `colaborador_form.html` y que `crispy`
(Bootstrap 5). La búsqueda es el mismo formulario GET de la plantilla (carga la
página con `?query=`); el botón de guardar muestra «Guardando…» como el script
`data-submit-with-spinner` y, como él, no pasa por la validación HTML
(el formulario es `noValidate`: la validación es la del servidor). Los mensajes
se muestran como alertas dentro del contenedor y como toast al final de `<body>`,
igual que la plantilla base.

Rarezas nativas conservadas, a propósito:

- Editar no puede poner `fecha_baja`: el `ModelForm` la asigna al objeto antes de
  que el servicio compruebe «activo» y responde «Solo se pueden editar
  colaboradores activos.» sin guardar.
- El alta excluye «Línea Secos»; editar y dar de baja no.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 19 pruebas de la API y 2 de la vista previa (acceso, CSRF y 415,
  veto de Secos, búsqueda local, RENAPER simulado, duplicado, errores de
  formulario sin escritura, alta, edición, baja idempotente, fechas, que no se
  cree ningún usuario). Pruebas de compuerta, proxy y registro de servicios,
  `black`, `pylint` y `makemigrations --check`.
- Frontend: 9 pruebas de la ruta, Vitest del workspace, `tsc`, ESLint y build.
- Visual (regla S13), nativo contra React, 6 estados (búsqueda, persona
  encontrada, alta inválida, persona ya colaboradora, DNI inválido, edición) en
  1440x900 y 390x844, y las guardas (anónimo, comedor y colaborador
  inexistentes).
- G1 de punta a punta en dos contenedores gunicorn: 401 anónimo, 403 sin
  permiso y con requisito pendiente, constancia falsificada ignorada, CSRF, y
  alta, rechazo, edición y baja por core → compuerta → runtime.

## Limitaciones

- La baja no tiene pantalla React propia: queda para la ficha del comedor.
- El resultado real de RENAPER y la cuenta de usuario PWA de un colaborador no se
  prueban aquí.
