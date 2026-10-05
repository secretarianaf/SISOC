# #2444: carga de roles territoriales PNUD en `Profile.rol`

La data migration `users.0056_issue_2444_roles_territoriales_pnud` asigna el rol
indicado en el CSV del issue a 100 usuarios: 82 `TERRITORIAL PNUD` y 18
`RESPONSABLE TERRITORIAL PNUD`. Estos roles son los que usa el campo
"Territorial Asignado Abordaje Comunitario" del legajo de Organización y el
filtro de Rendiciones (#2445).

## Alcance

- Solo modifica `Profile.rol` de los usernames listados. No crea usuarios ni
  modifica nombre, email, grupos, permisos ni contraseñas.
- Si un usuario no tiene `Profile`, se le crea.
- Los usernames que no existen en la base se omiten y se informan.
- Es idempotente: si se vuelve a ejecutar, no modifica a quienes ya tienen el rol.

## Salida

Al aplicarse, la migración imprime la cantidad de usuarios actualizados, por
cada uno su valor anterior y el nuevo (`username: 'anterior' -> 'nuevo'`), la
cantidad sin cambios y la lista de usernames no encontrados. Conviene guardar
esa salida del deploy: es el registro para restaurar valores si hiciera falta.

## Reversa

La reversa no modifica datos (`RunPython.noop`). `Profile.rol` es un dato
descriptivo que no otorga permisos ni accesos, por lo que dejarlo cargado no
tiene impacto funcional. Vaciarlo borraría también roles previos, sin forma de
recuperarlos. Para restaurar un valor anterior se usa la salida de la migración.

## Despliegue

Se aplica con el `migrate` habitual del deploy, sin pasos manuales. Revisar en
la salida la lista de "No encontrados": si aparece algún username, hay que
confirmar con el área si el usuario tiene otro username o todavía no fue creado.
