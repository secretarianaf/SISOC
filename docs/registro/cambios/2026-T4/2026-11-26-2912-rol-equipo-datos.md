# Cambio: rol para la administración de Datos (#2912)

## Alcance

La semilla de grupos crea el rol `Equipo de Datos` sin asignar personas ni permisos generales de administración de usuarios. La comprobación específica del administrador de tableros exige ese rol explícito, asignado directamente o mediante un grupo. No concede acceso automático por ser superusuario y rechaza cuentas inactivas. La revocación se consulta sin depender de la caché de permisos de la sesión.

## Verificación

Las pruebas con datos sintéticos cubren la creación del grupo, las asignaciones y revocaciones directas y por grupo, y los casos sin rol, superusuario e inactivo. La creación del grupo sigue el comando idempotente `create_groups`.

## Limitaciones

Este cambio es una base y no habilita todavía ninguna pantalla ni ruta. La interfaz y todas sus operaciones deberán usar esta comprobación en el servidor. La gestión de CDI requiere un contrato validado con la vertical. El rol no se asigna automáticamente a usuarios reales.

Si ya existe un permiso con el código canónico pero con otro nombre, el rol falla cerrado y requiere resolver la colisión antes de habilitar el administrador. No se asigna ese permiso ajeno al grupo de Datos.
