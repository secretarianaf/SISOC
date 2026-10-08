# INET: permisos por grupo para crear sedes adicionales

El alta de ubicaciones adicionales usa el permiso Django existente
`VAT.add_institucionubicacion`, asignable a cualquier grupo desde el ABM de grupos.
El botón **Agregar sede** y la URL de alta ya exigían ese permiso; no hace falta
crear otro permiso ni una migración para controlar la misma acción.

Se completa la validación del backend para exigir además que el usuario pueda
gestionar el centro elegido, con el mismo alcance que aplica la interfaz.
Se rechaza con 403 el alta sobre centros ajenos, tanto por el modal con centro
bloqueado como por POST directo. El formulario independiente solo ofrece centros
gestionables. No se modifican las asignaciones predeterminadas de los grupos.

Para habilitar la acción, agregar `VAT.add_institucionubicacion` al grupo deseado.
Para deshabilitarla, quitarlo de todos los grupos y permisos directos que lo
otorguen al usuario. Los permisos efectivos se suman; los superusuarios conservan
acceso. Editar y borrar continúan usando permisos independientes:
`VAT.change_institucionubicacion` y `VAT.delete_institucionubicacion`.

Pruebas: `src/backends/vat/tests/test_ubicacion_create_permissions.py` cubre
visibilidad del botón, grupos con/sin permiso, revocación, permiso obtenido desde
otro grupo, alta autorizada y bloqueo del alta en centros ajenos.

Validación: 10 tests pasan con Django 5.2.16 y SQLite en una configuración temporal
que carga los modelos de kernel y VAT sin los hooks del runtime completo. Black,
Pylint 3.2.6 con pylint-django 2.7.0 y `git diff --check` pasan. Docker no está
disponible en el entorno; no se ejecutaron la composición completa ni migraciones.
