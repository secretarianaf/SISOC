# Cambio: agregar familiar en React (#2785, C05.02)

## Qué cambia

- **API.** `GET` y `POST /api/web/ciudadanos/<pk>/familiares/nuevo/`
  (`ciudadanos/web_familiar.py`, `CiudadanoFamiliarNuevoWebView`, en el core) corren
  `GrupoFamiliarCreateView` con su orden nativo: el ciudadano primero (404) y después
  `ciudadanos.change_ciudadano` (403). El `GET` proyecta lo que imprime
  `grupofamiliar_form.html`: ciudadano, etiquetas, opciones de vínculo y estado,
  valores y errores. El `POST` (urlencoded, como el formulario nativo) arma el
  `GrupoFamiliarForm` con `get_form_kwargs` (el campo `ciudadano_2` toma
  `ciudadano_2_id`) y, si es válido, corre `form_valid`: crea la relación, deja el
  mensaje «Familiar agregado correctamente.» y redirige a la ficha, que pasa a
  `{"ok": true, "redirect": ...}`. Un formulario inválido responde 400 con el
  formulario ligado y no escribe nada. Las validaciones son las del formulario
  nativo: requerido, familiar no válido, autorreferencia y relación ya existente (en
  cualquier sentido).
- **React.** `routes/ciudadanoFamiliar.tsx` (`/ciudadanos/<pk>/familiares/nuevo`)
  dibuja el encabezado, el indicador de progreso, las tres secciones plegables
  (clic, Enter y Espacio), las etiquetas de estado «Sin completar» / «Completa» y
  los botones. El buscador de familiar es el de la plantilla: desde 4 caracteres
  consulta el endpoint nativo `/api/ciudadanos/buscar/?q=…&exclude_id=<pk>`, lista
  los resultados y un clic completa el texto y el id oculto. Tras un 400 se
  reproduce la página nativa recargada: errores, valores enviados (el campo de texto
  muestra el id enviado como `ciudadano_2`, el id oculto queda vacío), secciones
  abiertas y vista arriba.
- La entrada local `ciudadanos/web_preview.py` suma `ciudadanos/<pk>/familiares/nuevo`
  con los guardas nativos. Se agregó la ruta a `_OWNED_PATTERNS` y a
  `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): formulario, relación persistida (ambos
  ciudadanos, vínculo, estado, convivencia, notas, sin `deleted_at`) y mensaje
  consumido una vez, 400 por familiar vacío o inválido, autorreferencia y duplicado
  inverso sin escribir, 401, 403, 404 antes que 403, 405 y CSRF 403 con la tabla sin
  cambios, y la entrada de vista previa.
- Vitest, tsc y eslint sin avisos.
- G1 y visual S13 contra la página nativa, escritorio y móvil (ver el informe de la
  entrega).

## Limitaciones y diferencias conocidas

- La plegadura de las secciones no anima (Bootstrap anima la altura).
- El resto de las pantallas de C05.02 (editar y alta de ciudadano) siguen en Django.
