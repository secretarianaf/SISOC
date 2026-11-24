# Cambio: el borrado de imágenes del comedor se limita al comedor editado (CO-I2)

## Alcance

Corrección de seguridad en la edición nativa de un comedor. `ComedorService.delete_images`
borraba por identificador toda imagen marcada con `imagen_ciudadano-borrar-<id>` en el
formulario, sin comprobar que perteneciera al comedor que se edita. Un usuario con permiso
sobre el comedor A podía enviar el identificador de una imagen del comedor B y borrarla.

No cambia pantallas, URLs ni permisos. No se llama a ningún servicio externo.

Archivos:

- `src/backends/comedores/comedores/services/comedor_service/impl.py`: `delete_images`
  recibe `comedor_id` y filtra por él.
- `src/backends/comedores/comedores/views/comedor.py`: la vista de edición pasa el comedor.
- Pruebas: `src/backends/comedores/tests/test_delete_images_por_comedor_co_i2.py` (nueva) y
  ajuste de `test_comedor_service_renaper_helpers_unit.py` a la nueva firma.

## Comportamiento

- Se borran solo las imágenes marcadas cuyo `comedor` es el comedor editado.
- Un identificador de otro comedor se ignora en silencio: la fila y el archivo de esa
  imagen quedan intactos.

## Verificación

Entorno sintético, imagen fijada, sin red. La prueba negativa A/B falló antes del arreglo
(la imagen del comedor B desaparecía) y pasa después; la positiva pasa en ambos estados.

## Límites

`delete_legajo_photo` ya opera sobre el comedor recibido. Otras rutas de borrado de
imágenes (API móvil/PWA) no se tocan en este cambio.
