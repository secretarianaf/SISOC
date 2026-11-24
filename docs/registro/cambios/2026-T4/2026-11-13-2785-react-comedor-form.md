# Cambio: formulario de comedor (alta y edición) en React (#2785, CO07.02)

## Qué cambia

- **API (solo backend en esta entrega).** `src/backends/comedores/comedores/web_api_comedor_form.py`
  publica, bajo `/api/web/comedores/comedores/`:
  - `GET formulario/` y `GET <pk>/formulario/`: corren `ComedorCreateView` y
    `ComedorUpdateView` y devuelven los controles reales de `ComedorForm` y de
    `ReferenteForm` (prefijo `referente`) en el orden de `comedor_form.html`, con
    opciones, valores, atributos, el árbol de estados, la foto de legajo y las imágenes
    existentes. Permisos de las rutas nativas: `comedores.add_comedor` y
    `comedores.change_comedor`; la edición respeta el alcance del usuario (fuera de
    alcance es 404).
  - `POST crear/` (201) y `POST <pk>/editar/` (200): multipart; corren el `post` nativo
    (validación, guardado atómico con historial de estados, imágenes nuevas y, al editar,
    imágenes marcadas con `imagen_ciudadano-borrar-<id>`). Con errores responde 400 con
    los textos de Django por campo y el formulario con los valores enviados; no escribe
    nada. Un fallo al guardar mantiene el mensaje nativo «Error al guardar el comedor: …».
- **Solo lo que dibuja la plantilla llega a la vista nativa.** El `ModelForm` acepta más
  campos (`responsable_tarjeta_*`, `estado_validacion`…): un cuerpo de pedido no puede
  fijarlos por esta API, igual que no puede la página nativa.
- **React.** `src/frontends/apps/sisoc/src/routes/comedorForm.tsx` (`/comedores/crear` y
  `/comedores/<pk>/editar`) dibuja el formulario como lo hace crispy, con las cinco
  secciones plegables y sus insignias de progreso, el árbol de estados (estado general,
  subestado y motivo), provincia, municipio y localidad con los pedidos nativos, la
  organización con búsqueda remota y programa y proyecto según la organización, la
  categoría «otra», la foto de legajo (vista previa, ver completa, eliminar), las imágenes
  existentes (marcar para eliminar) y nuevas, el editor de pin del mapa y la pregunta de
  confirmación antes de guardar. Con errores la página queda con los textos nativos y los
  valores enviados. La entrada de vista previa suma las dos URLs nativas.
- La API suma al formulario el widget nativo de la foto de legajo (textos y casilla
  «Eliminar») y acepta `foto_legajo-clear`, que la plantilla dibuja junto a una foto
  existente.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red), 12 pruebas: proyección del formulario, alta con
  referente, historial de estados e imagen, rechazo sin escribir (campos, subestado ajeno),
  campos no dibujados ignorados, edición (dupla, referente, imágenes borradas, sin nuevo
  historial si el estado no cambia), edición rechazada sin cambios, 404, permiso propio de
  cada ruta, métodos, CSRF, 401 y requisito web pendiente con cabecera falsificada, y
  reversión ante un fallo al guardar.

- Vitest (12 pruebas del formulario), tsc, eslint y compilación sin avisos. G1 (alta, edición,
  rechazo y 403) y visual S13 contra la página nativa: alta vacía, edición con datos y
  guardado rechazado, escritorio y móvil, sin diferencias de estructura ni de píxeles.

## Limitaciones y diferencias conocidas

- La página nativa no dibuja los errores generales del formulario (por ejemplo «Error al
  guardar el comedor: …»); la pantalla React tampoco, igual que hoy.
- La búsqueda de organizaciones usa el selector remoto compartido de Inspecciones: sus
  textos («Sin resultados», «Buscando…») difieren de los de Select2 en inglés de la
  página nativa; no se comparó con una búsqueda abierta.

- Se conserva el comportamiento de origen: el borrado nativo de imágenes busca los ids sin
  filtrar por comedor, y la transacción no revierte los bytes ya escritos en el
  almacenamiento.
- `foto_legajo_borrar` no se publica porque la plantilla actual no lo dibuja.
