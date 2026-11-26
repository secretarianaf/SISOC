# Cambio: formulario compuesto de usuarios en React (#2785, U08)

## Alcance

Subunidades U2a (API de sesión), U2b (pantalla del núcleo) y U2c (proyección del
dueño de Espacios comunitarios, cartas restantes y registro de la ruta) del contrato
`docs/plans/2026-T4/2026-10-28-2785-usuarios-u08-formulario-compuesto.md`: el
transporte de sesión sobre las vistas nativas de alta (`/usuarios/crear/`) y
edición (`/usuarios/editar/<id>/`), con los campos del núcleo y las secciones
DataCalle e Inspecciones escolares. Las tarjetas de Espacios comunitarios
(acceso mobile, territorial comedor, equipos técnicos) y las pantallas React se
agregan en las subunidades siguientes; la ruta React del formulario se registra
solo cuando el formulario esté completo (U2c). No cambian las vistas, plantillas,
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
  esas secciones, grupos o roles de dominio, cambios de alcance en edición) se
  reenvía al dueño por el mismo relevo interno que usan las vistas nativas, pero
  pidiendo JSON (ver U2c). Si el dueño no está disponible, el POST responde 409
  `comedores_runtime_required` sin persistir nada y el GET vuelve al formulario
  del núcleo con la advertencia nativa.

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
se registra en U2c.

## Subunidad U2c: proyección del dueño y tarjetas de Espacios comunitarios

- `src/backends/comedores/pwa/web_user_form.py`: `WebUserCreateView` y
  `WebUserUpdateView` heredan de las vistas compuestas del dueño
  (`pwa.user_admin_views`), que siguen siendo las únicas que validan y guardan
  (una transacción atómica). Proyectan el formulario compuesto (tarjetas del
  núcleo más Acceso a Espacios comunitarios, Territorial comedor y Equipos
  técnicos, el contexto de subusuario mobile y los usuarios mobile creados) como
  el payload del núcleo. `src/backends/comedores/pwa/user_admin_urls.py` agrega
  `/interno/usuarios/operacion-web/` y registra el mismo servicio para la
  composición local.
- `usuarios/web_user_form.py` (núcleo): el GET reenvía al dueño si el actor tiene
  alguna sección de Comedores (como la vista nativa) y el POST si
  `operacion_requiere_espacios`; el JSON del dueño recibe la presentación, las
  URLs y los mensajes pendientes del portal. La autoridad la vuelve a aplicar el
  dueño (permisos de ABM, alcance del objeto).
- Credencial (U-CR1): el dueño ya no escribe la contraseña generada en un
  mensaje flash. La operación que la crea la recibe una vez en un resultado
  privado (`credential`, `Cache-Control: no-store`) y la pantalla la muestra con
  un enlace «Continuar». La lectura de edición conserva la paridad con la
  plantilla nativa: quien edita (`auth.change_user`, dentro del alcance) ve la
  contraseña temporal vigente guardada en el perfil, como hoy. Un actor con solo
  alta recibe el resultado de su propia operación, pero no obtiene lectura de
  edición.
- Redirecciones: una redirección del dueño que no sea el éxito hacia
  `/usuarios/` (la del control de permisos hacia el login) responde 401 y nunca
  `ok`; el núcleo la propaga y la pantalla informa que no se pudo confirmar el
  resultado.
- `usuariosMobile.tsx` y `usuariosControls.tsx`: tarjetas de Comedores con las
  reglas de `user_mobile_access.js` y del selector de organizaciones y espacios
  (pestañas, búsqueda, tablas, selección de espacios al marcar una organización).
- `routes/usuarios.tsx` registra `/usuarios/crear/` y
  `/usuarios/editar/<id>/`; la prueba de la ruta se actualizó.
- Pruebas: `comedores/tests/test_web_user_form_pwa.py`.

## Verificación

Pruebas de API (guardas, proyección por actor, alta persistida, rechazo
atómico, escalada de privilegios, contraseña vacía y nueva, credencial) y de
las entradas de vista previa.

## Límites

- Los errores no asociados a un campo no se dibujan, igual que la plantilla
  nativa (decisión aceptada).
- En G1, un POST anónimo sin CSRF responde 403 del middleware de CSRF (antes de
  la sesión) y no 401; no hay cambio de estado.
- El camino HTTP del relevo (núcleo y runtime separados) está cubierto por G1; las
  pruebas unitarias corren con la composición local.
- Paridad visual (escritorio y móvil, actor con las secciones del núcleo):
  alta, alta con actor acotado y rechazo coinciden. En la edición con grupos
  seleccionados difiere solo la posición de dos `<option>` del `<select>`
  oculto de 1 px (el navegador nativo lo desplaza hasta la opción elegida);
  la diferencia de píxeles es 0 %.
