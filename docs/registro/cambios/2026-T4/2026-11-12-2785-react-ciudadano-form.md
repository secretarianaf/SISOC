# Cambio: alta y edición de ciudadano en React (#2785, C05.02)

## Qué cambia

- **API.** `GET`/`POST /api/web/ciudadanos/crear/` y
  `GET`/`POST /api/web/ciudadanos/<pk>/editar/` (`ciudadanos/web_form.py`, en el core)
  corren `CiudadanosCreateView` y `CiudadanosUpdateView` con su `dispatch`: login y
  permiso (`add_ciudadano` / `change_ciudadano`, 403) primero y, en la edición, el 404
  después. El `GET` proyecta campo por campo el formulario de `ciudadano_form.html`
  (etiquetas, ayuda, atributos, opciones, valores, errores, foto actual con los textos
  del widget), el aviso de revisión de identidad y la búsqueda del alta. Con `?dni=&sexo=`
  corre la búsqueda nativa de RENAPER; en las pruebas se reemplaza
  `ciudadanos.views.obtener_datos_ciudadano_desde_renaper` y nunca se llama a RENAPER.
  El `POST` es multipart como el formulario nativo y corre su `post()`: `CiudadanoForm`,
  normalización de identidad, identificador interno, error de identidad única y la foto
  en el almacenamiento nativo. Un 302 pasa a `{"ok": true, "redirect": ...}` (ficha del
  ciudadano, con el mensaje en cola) y un formulario rechazado a un 400 con el formulario
  ligado, sin escribir nada.
- **React.** `routes/ciudadanoForm.tsx` (`/ciudadanos/crear/`, `/ciudadanos/editar/<pk>`)
  reproduce la plantilla y sus scripts: tarjeta de búsqueda por DNI, aviso de revisión,
  progreso y estado de las cinco secciones (todas opcionales, como en la plantilla, y un
  interruptor solo cuenta si el usuario lo cambió), bloques de «Sin DNI» y «DNI no
  validado» (el documento se oculta para «Sin DNI»), geografía en cascada con los
  endpoints `/ajax/load-*` y el `Select2` compartido (provincia, municipio, localidad y
  nacionalidad), el editor de pin de mapa del motor compartido, la foto con vista previa,
  quitar y modal de la foto actual, y la fecha ISO de la instancia. Tras un 400 se
  reproduce la recarga nativa: errores, valores enviados, secciones abiertas y vista arriba.
- La entrada local `ciudadanos/web_preview.py` suma `ciudadanos/crear/` y
  `ciudadanos/editar/<pk>` con los guardas nativos (sin correr la búsqueda de RENAPER: la
  hace la API). Se agregaron las rutas a `_OWNED_PATTERNS` y a `url_registry.json`.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): formulario del alta y de la edición, búsqueda
  de RENAPER simulada (precarga, DNI inválido, sin resultado), alta con foto y efecto
  persistido exacto, edición (el tipo de documento no cambia), 400 sin escribir
  (obligatorios, latitud/longitud, motivo de «Sin DNI», documento repetido), 401, 403
  (antes que 404), 404, 405 y CSRF 403 con la tabla sin cambios, y las entradas de vista
  previa.
- Vitest, tsc y eslint sin avisos.
- G1 y visual S13 contra la página nativa, escritorio y móvil (alta vacía, alta con
  errores, edición con datos y foto, edición con revisión pendiente), ver el informe.

## Limitaciones y diferencias conocidas

- La plegadura de las secciones no anima.
- El indicador de carga de la miniatura de la foto actual (un `sr-only` de 1,3 px) queda
  unos píxeles corrido respecto de la página nativa; no cambia ningún píxel.
- La búsqueda por DNI del alta es un `GET` de la propia página, como en Django; con RENAPER
  real solo corre en los entornos que ya lo tenían configurado.
