# Celiaquía: edición de Localidad y Municipio del legajo (#2017)

En el modal "Editar legajo" del detalle de expediente, Nación cambiaba el
Municipio, guardaba con éxito y el cambio no se reflejaba.

Causa: los selects de Municipio y Localidad usan Select2, que dispara `change`
vía jQuery; los listeners del modal estaban registrados con
`addEventListener`, que no recibe esos eventos. Al elegir otro municipio no se
filtraban las localidades ni se limpiaba la localidad anterior, y el backend
(`EditarLegajoView.post`) deriva el municipio de la localidad enviada, por lo
que la localidad vieja restauraba el municipio original.

Cambio: `static/custom/js/expediente_detail.js` registra los handlers con
`jQuery.on('change')` (con fallback nativo), que escucha tanto eventos nativos
como los de Select2. Al cambiar el municipio, la lista de localidades se
filtra y, si la localidad previa no pertenece al nuevo municipio, queda vacía
y es obligatorio elegir una antes de guardar.

No cambia el backend: se mantiene que la localidad define el municipio
(cubierto por `test_legajo_editar_actualiza_nacionalidad_elegida_y_municipio_desde_localidad`),
ni los permisos de edición. El resto de los campos del legajo no se ve
afectado.
