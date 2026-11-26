# Cambio: visibilidad del menú de tableros (#2912)

## Alcance

El catálogo incorpora `visible_menu` para decidir si se muestra el enlace en el menú, independientemente del estado activo. Las entradas existentes y nuevas lo tienen activado por defecto.

## Comportamiento

El formulario administrativo permite cambiar la visibilidad e indica que ocultar el enlace no modifica permisos ni bloquea la ruta directa. Los formularios antiguos que no incluyen el nuevo control conservan la visibilidad existente. La sincronización del catálogo desde código tampoco modifica este campo en registros existentes. La autorización de cada ruta sigue siendo independiente.

## Verificación

Las pruebas sintéticas y la verificación independiente cubren menú, acceso directo, política explícita, formularios antiguos y prefijados, sincronización y auditoría. La migración y sus valores iniciales se probaron en SQLite y MySQL 8 descartables; la reversión se probó en SQLite. El usuario confirmó la verificación visual de ocultamiento, acceso directo autorizado y denegación sin permiso en la demo sintética.

## Limitaciones

Este cambio no crea el front dedicado al equipo de Datos ni modifica sus permisos. Las rutas internas deben protegerse por sí mismas. No se utilizaron datos reales ni hubo publicación o despliegue.
