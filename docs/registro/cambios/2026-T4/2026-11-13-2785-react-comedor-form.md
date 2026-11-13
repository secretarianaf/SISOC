# Cambio: API del formulario de comedor (alta y edición) para React (#2785, CO07.02)

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
- No hay pantalla React ni ruta de vista previa todavía: se registran en la entrega que
  completa la pantalla.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red), 12 pruebas: proyección del formulario, alta con
  referente, historial de estados e imagen, rechazo sin escribir (campos, subestado ajeno),
  campos no dibujados ignorados, edición (dupla, referente, imágenes borradas, sin nuevo
  historial si el estado no cambia), edición rechazada sin cambios, 404, permiso propio de
  cada ruta, métodos, CSRF, 401 y requisito web pendiente con cabecera falsificada, y
  reversión ante un fallo al guardar.

## Limitaciones y diferencias conocidas

- Se conserva el comportamiento de origen: el borrado nativo de imágenes busca los ids sin
  filtrar por comedor, y la transacción no revierte los bytes ya escritos en el
  almacenamiento.
- `foto_legajo_borrar` no se publica porque la plantilla actual no lo dibuja.
