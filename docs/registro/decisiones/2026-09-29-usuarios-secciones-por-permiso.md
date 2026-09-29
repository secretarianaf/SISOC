# 2026-09-29 - ABM de usuarios: secciones habilitadas por permiso

## Estado
- aceptada (implementada en `feat/usuarios-secciones-por-permiso`, 2026-09-29)

## Contexto

En `/usuarios/crear/` y `/usuarios/editar/<pk>/`, cualquiera con
`auth.add_user`/`auth.change_user` veía **todas** las secciones del formulario,
fuera o no de su programa. Un coordinador de DataCalle veía y podía usar el
acceso mobile de Comedores; un gestor de Comedores veía la sección de DataCalle.

La única excepción era una lista fija en el formulario
(`CDI_ABM_RESTRICTED_GROUPS`) que ocultaba algunos campos a los gestores
CDI/SIMEPI. Esa lista no cubría Territorial comedor ni DataCalle, así que un
referente CDI podía dar de alta un entrevistador de DataCalle o un territorial
de cualquier provincia.

## Clasificación de las secciones

| Sección | Clase | Permiso |
|---|---|---|
| Datos personales, Datos de acceso | General | — |
| Permisos y Roles (grupos, rol descriptivo) | General (grupos acotados por delegación) | — |
| Alcance territorial (usuario provincial + alcances) | General | — |
| Acceso SISOC - Mobile (+ usuarios mobile creados) | Comedores | `auth.role_usuarios_seccion_mobile_comedores` |
| Acceso SISOC - Mobile Territorial comedor | Comedores | `auth.role_usuarios_seccion_territorial_comedor` |
| Equipos técnicos (coordinador + duplas) | Comedores | `auth.role_usuarios_seccion_equipos_tecnicos` |
| Acceso SISOC - Mobile DataCalle | DataCalle | `auth.role_usuarios_seccion_datacalle` |
| Administración de accesos (permisos directos, grupos/roles asignables) | Administración | `auth.role_usuarios_seccion_administracion` |

El catálogo vive en `users/secciones_usuario.py` y los campos de cada sección en
`CAMPOS_POR_SECCION` (`users/forms.py`).

## Decisión

- Cada sección no general se muestra y se puede editar sólo si el actor tiene su
  permiso. Sin el permiso, la tarjeta no se renderiza y sus campos quedan
  `disabled`: un POST armado a mano no los modifica y, en edición, Django
  conserva los valores actuales del usuario.
- Los "roles" son grupos que agrupan esos permisos:
  - `Admin`: todas las secciones.
  - `Usuarios - Gestor Comedores` (nuevo): `view/add/change_user` + las tres
    secciones de Comedores.
  - `Coordinador DataCalle` y `Administrador DataCalle`: sólo DataCalle.
  - Grupos CDI/SIMEPI: ninguna sección (reemplaza `CDI_ABM_RESTRICTED_GROUPS`).
- El superusuario y los usos del formulario sin actor ven todas las secciones,
  igual que el resto de las restricciones por actor del formulario.
- "Configuración Adicional" se separó en tres tarjetas: **Alcance territorial**
  (general), **Equipos técnicos (Comedores)** y **Administración de accesos**.
  Los permisos directos pasaron de "Permisos y Roles" a Administración.

## Despliegue

La migración `users/0055_usuarios_secciones_por_permiso` crea los permisos y
conserva lo que hoy ve cada perfil: todo grupo o usuario con
`auth.add_user`/`auth.change_user` recibe todas las secciones, salvo:

- grupos CDI/SIMEPI: ninguna (como antes, y ahora sin Territorial ni DataCalle);
- grupos DataCalle: sólo DataCalle. **Este es el cambio visible:** los
  coordinadores y administradores de DataCalle dejan de ver las secciones de
  Comedores y la de administración.

`create_groups` (entrypoint) crea el grupo `Usuarios - Gestor Comedores` y
suma los permisos del seed a `Admin` y a los grupos DataCalle.

Para acotar a un perfil existente que hoy ve todo, alcanza con sacarle a su
grupo los permisos `role_usuarios_seccion_*` que no le correspondan.

## Trade-offs

- Un gestor de Comedores sin sección Administración no configura delegación, así
  que los grupos que puede asignar siguen saliendo de su propio
  `grupos_asignables`, que le configura un administrador.
- Los permisos usan el prefijo `role_`, como el resto de los permisos
  funcionales del repo; por eso también se pueden delegar desde "Roles que
  puede asignar".
- Al pasar un actor sin la sección DataCalle, ya no se fija la provincia
  DataCalle a su alcance: con el campo deshabilitado, eso pisaba la provincia del
  relevador editado.
