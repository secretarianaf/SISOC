# INET: localidades de sedes adicionales

Al agregar una sede desde el detalle de un centro VAT, seleccionar un departamento
en Select2 no cargaba sus localidades. La cascada se inicializaba en el bloque
`content`, antes de cargar jQuery en `mainscripts`, y enlazaba únicamente el evento
nativo `change`, que no recibe los eventos emitidos por Select2.

La inicialización pasa al bloque `customJS`, después de cargar jQuery y Select2.
Se conserva la delegación sobre el formulario para soportar el reemplazo de campos
al agregar o editar, la selección guardada en edición y el fallback sin jQuery.
El endpoint y la validación de localidades no cambian.

Prueba de regresión: `node --test src/backends/vat/tests/js/ubicacion_departamento.test.js`.
Cubre la carga por eventos jQuery/Select2 después de reemplazar campos, el cambio
nativo sin jQuery y la conservación de la localidad al abrir edición.

Validación ejecutada: las cuatro pruebas JavaScript pasan; contra el template de
`HEAD` fallan los dos casos de selección por eventos jQuery/Select2. También pasa
`test_centro_detail_template_bien_formado` y `git diff --check`. `djlint --check`
señala únicamente las comillas del include de breadcrumb, con el mismo resultado
en el template original. No se verificó el navegador de producción.
