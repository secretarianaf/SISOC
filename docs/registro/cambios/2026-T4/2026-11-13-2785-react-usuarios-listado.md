# Cambio: listado de usuarios y activación/desactivación en React (#2785, U06)

## Alcance

Unidad U06.01/U06.02 del contrato
`docs/plans/2026-T4/2026-10-28-2785-usuarios-grupos-y-credenciales.md`: el
listado `/usuarios/` y las confirmaciones `/usuarios/borrar/<id>/` y
`/usuarios/activar/<id>/`, como transporte de sesión y pantallas React. No se
activa React globalmente; las vistas, plantillas, formularios, permisos y la
exportación CSV nativos no cambian. El formulario compuesto de alta y edición
es la unidad siguiente.

## Archivos

- `src/backends/sisoc_core/usuarios/web_users.py`: tres vistas que heredan de
  `UserListView`, `UserDeleteView` y `UserActiveView`. El queryset, el alcance
  del actor (`get_usuarios_en_alcance`), el filtro avanzado, las preferencias de
  columnas y el cambio de `is_active` son los nativos. La guarda repite el
  decorador de la URL nativa (`_has_any_permissions`) y la de la vista
  (`test_func`) después de los requisitos de acceso web.
- `src/backends/sisoc_core/usuarios/web_api_urls.py`: rutas
  `/api/web/users/list/`, `/api/web/users/<id>/deactivate/` y `.../activate/`.
- `src/backends/sisoc_core/usuarios/identity_preview.py`: entradas del URLconf
  sintético local con las mismas guardas y el 404 del objeto fuera de alcance.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (generado con
  `generar_registro_urls`).
- `src/frontends/apps/sisoc/src/routes/usuarios.tsx`, `usuariosList.tsx`,
  `usuariosState.tsx` y `usuarios.test.tsx`, registrados en `routes/index.ts`.
- Pruebas: `sisoc_core/tests/test_web_users_list.py` y
  `test_identity_preview_users.py`.

## Seguridad

- Nadie obtiene un acceso que hoy no tiene: ver el listado exige
  `auth.view_user`, cambiar el estado exige `auth.delete_user`, cada uno con su
  bypass de superusuario; tener solo uno no habilita el otro.
- Un usuario fuera del alcance delegable (o un superusuario) responde 404 en la
  confirmación y en el POST, sin cambios persistidos. Los usuarios sin grupos
  quedan dentro del alcance, como en la vista nativa.
- El POST exige CSRF; sin cuerpo o con formulario; otro tipo de contenido
  responde 415. El único efecto persistido es `is_active`, con el mensaje
  nativo «Usuario desactivado correctamente.» / «Usuario activado
  correctamente.», que el listado consume en el siguiente GET.
- Los DTO no incluyen contraseñas, hashes ni permisos; las celdas usan la misma
  localización que la plantilla.

## Verificación

Pruebas de API y de entradas de vista previa, pruebas de React, paridad visual
nativo/React (listado, listado con filtro, listado de otro actor, modal de
columnas, ambas confirmaciones; escritorio y móvil) y G1 en núcleo y runtime.

## Límites

- En G1, un POST anónimo sin CSRF responde 403 del middleware de CSRF (antes de
  la sesión) y no 401; no hay cambio de estado. El resto de las comprobaciones
  estándar pasan.
- El alta y la edición, y el reinicio de contraseña móvil, quedan para la
  unidad siguiente. La exportación CSV sigue siendo el GET nativo.
