# Cambio: retiro del panel Cursos PAS

## Alcance

Se retiró la pantalla reservada de Cursos PAS de la interfaz Django y de PAS v2, junto con su API web y su entrada de menú.

## Comportamiento

Buscador PAS sigue en Administración. La consulta de cursos registrados del circuito Formación FCH sigue disponible. El retiro no requiere cambios en los datos ni migraciones.

## Verificación

- La suite de PAS v2 cubre la ausencia del enlace, la navegación a la ruta retirada y la ubicación del Buscador PAS. Pasaron los 30 tests de la suite.
- La compilación de PAS v2 y la comprobación de tipos finalizaron correctamente.
- Las dos pruebas de Django verificaron la respuesta 404 de las rutas retiradas.
