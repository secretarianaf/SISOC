# Cambio: Nginx solo versionado

## Alcance

Por pedido del usuario se retira del deploy la comparación y reconciliación automática de Nginx. Se conservan los vhosts y snippets de referencia para QA, HML y producción, así como sus reglas de protección; se eliminan la dependencia del marcador y el socket de prueba, junto con el helper y las pruebas exclusivas de esa automatización.

## Comportamiento

El deploy continúa sin comprobar, instalar ni recargar Nginx. Los archivos versionados son referencias: no prueban el estado activo de ningún servidor y no autorizan instalarlos. Cualquier revisión o cambio manual de Nginx requiere autorización y validación independientes; las protecciones versionadas no acreditan que estén activas en un servidor.

## Verificación

Se verificó en pruebas locales el retiro del gate y la conservación de rutas y protecciones, y en Docker con Nginx y datos sintéticos los contratos de los tres vhosts. No se accedió ni modificó ningún servidor, no se ejecutó CI ni deploy y la aceptación humana permanece pendiente.
