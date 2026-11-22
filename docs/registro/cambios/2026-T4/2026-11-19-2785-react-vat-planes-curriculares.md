# Cambio: planes curriculares de VAT en React (#2785, V07.01 y V07.02)

## Qué cambia

- **API.** `/api/web/vat/catalogos/planes-curriculares/` (`VAT/web_api_planes_curriculares.py`) suma la lista, el
  detalle (`<pk>/`), el alta (`nuevo/`) y la edición (`<pk>/editar/`). Corren `PlanVersionCurricular{List,Detail,Create,Update}View`:
  filtros combinables y favoritos de la lista, el texto que imprimen las plantillas (`—` y `-` por defecto, normativa
  estructurada), el formulario `PlanVersionCurricularForm` con sus bloqueos del rol INET provincial y su `form_valid`
  (guardado, sincronización del título de referencia y mensaje). Acceso: el permiso de la ruta nativa y la guarda del
  `dispatch` nativo (rol SSE o provincial; alta y edición exigen SSE o provincial con el permiso), que corre antes
  de cualquier dato. El alcance y los 404 son los del queryset nativo. El POST responde `{"ok": true, "redirect": ...}`
  o 400 con los campos y errores; un rechazo no cambia los datos.
- **React.** `routes/vatPlanes.tsx` (lista y detalle) y `routes/vatPlanesForm.tsx` (alta y edición) dibujan las
  páginas nativas: buscador con filtros, tabla ordenable por nombre, insignias de estado, botones según permiso,
  paginación, el héroe y los paneles del detalle, y el formulario con los campos de crispy-bootstrap5, la
  normativa libre cargada y los mensajes en cola como alertas. El detalle elimina con el formulario POST nativo y su
  confirmación «¿Está seguro?».
- Las entradas locales `VAT/web_preview_vat_planes.py` conservan la ruta, el permiso, la guarda de rol y los 404 nativos antes de servir
  el índice React. Se agregó la ruta a `_OWNED_PATTERNS` de `admindocs.py` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): 401, 403 por permiso y por rol, alcance provincial, 404, filas y filtros,
  coincidencia con el texto de la página nativa, alta y edición con el efecto persistido exacto (incluido el título de
  referencia y la normativa), rechazos sin cambios, CSRF, 405 y entradas de vista previa.
- Vitest, tsc y eslint; G1 (núcleo y runtime) y visual S13 contra las páginas nativas (escritorio y móvil).

## Limitaciones y diferencias conocidas

- La confirmación nativa `planes-curriculares/<pk>/eliminar/` falla con `NoReverseMatch` (su plantilla usa `plan.id` y la
  vista expone `planversioncurricular`): el enlace «Eliminar» de la lista lleva a esa página y da error 500, también hoy. La
  baja desde el detalle (POST directo) funciona. Se conserva el comportamiento nativo; corregir la plantilla es un cambio de dos
  líneas, pendiente de decisión.
- El subsector no se actualiza al cambiar el sector (la página nativa tampoco tiene ese script): un subsector de otro sector se rechaza al
  guardar con el mensaje nativo.
- Los campos bloqueados (`disabled`) se envían en el POST; el servidor ignora su valor, como con el formulario nativo.
