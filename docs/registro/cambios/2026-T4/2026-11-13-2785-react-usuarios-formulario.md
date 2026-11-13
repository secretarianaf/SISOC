# Cambio: formulario compuesto de usuarios en React (#2785, U08), API de sesión

## Alcance

Subunidad U2a del contrato
`docs/plans/2026-T4/2026-10-28-2785-usuarios-u08-formulario-compuesto.md`: el
transporte de sesión sobre las vistas nativas de alta (`/usuarios/crear/`) y
edición (`/usuarios/editar/<id>/`), con los campos del núcleo y las secciones
DataCalle e Inspecciones escolares. Las tarjetas de Espacios comunitarios
(acceso mobile, territorial comedor, equipos técnicos) y las pantallas React se
agregan en las subunidades siguientes; la ruta React del formulario se registra
solo cuando el formulario esté completo. No cambian las vistas, plantillas,
formularios ni permisos nativos.

## Archivos

- `src/backends/sisoc_core/usuarios/web_user_form.py`: `WebUserCreateView` y
  `WebUserUpdateView` heredan de `UserCreateView` y `UserUpdateView`. El
  formulario (`UserCreationForm`/`CustomUserChangeForm`), el alcance del actor
  (`get_usuarios_en_alcance`), las secciones por permiso, la delegación de
  grupos y roles, el guardado atómico y el mensaje nativo siguen siendo los
  nativos. El módulo solo proyecta el formulario ligado a JSON.
- `src/backends/sisoc_core/usuarios/web_api_urls.py`: rutas
  `/api/web/users/create/` y `/api/web/users/<id>/edit/`.
- `src/backends/sisoc_core/usuarios/identity_preview.py`: entradas
  `usuarios/crear/` y `usuarios/editar/<id>/` del URLconf sintético local.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (generado con
  `generar_registro_urls`).
- Pruebas: `sisoc_core/tests/test_web_user_form_api.py` y
  `test_identity_preview_user_form.py`.

## Contrato del payload

`sections[]` sigue el orden de las tarjetas nativas y solo incluye las que el
formulario habilita para el actor (`can_manage_datacalle`,
`can_manage_inspecciones_escolares`, `can_manage_delegation`); cada campo trae
tipo, etiqueta, ayuda, obligatoriedad, `disabled`, opciones (las del queryset ya
acotado por el actor) y valor. `identity_present` lista los controles para los
que la plantilla emite `_identity_present` (un control vaciado es un cambio, un
campo omitido no revoca). `errors` es `form.errors.get_json_data()` con los
mensajes nativos. El POST es `application/x-www-form-urlencoded` con CSRF; el
éxito responde `{ok, redirect}` y el mensaje nativo («Usuario creado
correctamente.») lo consume el listado.

## Seguridad

- Mismas guardas que la vista nativa, antes de buscar el objeto: requisitos de
  acceso web, `auth.add_user` / `auth.change_user` y 404 fuera del alcance.
- Un POST forjado no otorga nada: los campos de secciones que el actor no tiene
  quedan deshabilitados en el servidor (se ignoran), los grupos y roles fuera de
  la delegación se rechazan con el error nativo y no se guarda nada; los
  indicadores `is_staff`/`is_superuser` no son campos del formulario.
- La contraseña nunca viaja en un payload (ni tras un rechazo); la contraseña
  temporal vigente solo se proyecta en la edición, en `credential`, con la misma
  autoridad que la plantilla nativa (`auth.change_user` dentro del alcance),
  con `Cache-Control: no-store` y sin aparecer en el listado ni en el alta.
- Una operación que el POST nativo reenvía a Espacios comunitarios (campos de
  esas secciones, grupos o roles de dominio, cambios de alcance en edición)
  responde 409 `comedores_runtime_required` sin persistir nada, en lugar de
  reenviar HTML. La subunidad U2c lo reemplaza por la proyección del dueño.

## Subunidad U2b: pantalla React de los campos del núcleo

`src/frontends/apps/sisoc/src/routes/usuariosForm.tsx` (y `usuariosForm.test.tsx`)
dibuja las tarjetas nativas (datos personales, acceso, DataCalle, Inspecciones
escolares, permisos y roles, alcance territorial, administración de accesos) a
partir del payload de U2a, con el marcado de `user/user_form.html`. Repite solo
las reglas de visibilidad de `user_mobile_access.js` y la tabla de alcances de
`usuarioprovincial.js`; publica solo los controles habilitados más los
`_identity_present`, y tras un rechazo vuelve a dibujar los valores ligados y
los errores nativos. La contraseña se puede mostrar/ocultar y la credencial
temporal vigente se dibuja solo si el servidor la proyecta. La ruta
(`routes/usuarios.tsx`, patrón `/usuarios/crear/` y `/usuarios/editar/<id>/`)
NO está registrada: se entrega aparte y se activa al completar U2c.

## Verificación

Pruebas de API (guardas, proyección por actor, alta persistida, rechazo
atómico, escalada de privilegios, contraseña vacía y nueva, credencial) y de
las entradas de vista previa.

## Límites

- La GET no reenvía a Espacios comunitarios: para un actor con esas secciones
  solo se anuncian en `comedores.sections`.
- Las tarjetas de Espacios comunitarios y el reemplazo del 409 por la
  proyección del dueño (U2c) requieren un módulo nuevo en `comedores/pwa`, fuera
  de las superficies de esta unidad.
- Paridad visual (escritorio y móvil, actor con las secciones del núcleo):
  alta, alta con actor acotado y rechazo coinciden. En la edición con grupos
  seleccionados difiere solo la posición de dos `<option>` del `<select>`
  oculto de 1 px (el navegador nativo lo desplaza hasta la opción elegida);
  la diferencia de píxeles es 0 %.
