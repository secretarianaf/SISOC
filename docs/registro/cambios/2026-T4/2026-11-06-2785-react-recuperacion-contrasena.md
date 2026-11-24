# Cambio: recuperación de contraseña en React (#2785, ID-B)

## Alcance

Se implementa el circuito ID-B del contrato
`docs/plans/2026-T4/2026-10-27-2788-identidad-remediaciones-m2.md`:
`/password_reset/`, `/password_reset/done/`, `/reset/<uidb64>/<token>/`,
`/reset/done/` y el alias `/password/reset/confirm/<uidb64>/<token>/`, como una
sola unidad backend y React. No se activa React globalmente, no cambian las
rutas HTML de producción, el Form, el envío de correo ni el admin #2789.

Archivos:

- `src/backends/sisoc_core/usuarios/web_password_reset.py`: transporte JSON
  público sobre las vistas existentes `SisocPasswordResetView` y
  `PasswordResetConfirmCustomView` de `usuarios/auth_views.py`.
- `src/backends/sisoc_core/usuarios/web_api_urls.py`: rutas
  `/api/web/password/reset/` y `/api/web/password/reset/<uidb64>/`, con sus
  entradas generadas por `generar_registro_urls` en
  `src/backends/config/url_registry.json`.
- `src/backends/config/middlewares/admindocs.py`: ambas rutas se suman a las
  rutas propias donde HEAD responde la API y no el diagnóstico `X-View`; los
  patrones existentes se agrupan en una tupla sin cambiar su resultado.
- `src/backends/sisoc_core/usuarios/identity_preview.py`: entradas del URLconf
  sintético local para las cinco rutas públicas.
- `src/frontends/apps/sisoc/src/PasswordReset.tsx` y su ruta en `App.tsx`.

## Comportamiento

Solicitud: `GET /api/web/password/reset/` devuelve los campos reales de
`UsernameEmailPasswordResetForm` (`username` y `email`, con etiqueta, tipo,
`maxlength` y `autocomplete`) y la etiqueta de versión del pie; instala la
cookie CSRF. El POST URL-encoded con CSRF ejecuta la vista original: mismo
criterio de coincidencia (usuario activo exacto y correo sin distinguir
mayúsculas) y mismo correo existente. Si el formulario es válido, la respuesta
es siempre `{"ok": true, "redirect": "/password_reset/done/"}`, coincida o no la
cuenta, con el mismo estado, cuerpo y encabezados; no se agrega enumeración de
cuentas ni promesa de tiempo constante. Errores de Form: 400 con los errores
reales. Sin CSRF: 403; JSON: 415; PUT/PATCH/DELETE: 405.

Confirmación: el token del enlace nunca llega a React ni a la API. El GET de
`/reset/<uidb64>/<token>/` (o del alias) sigue en la vista original, que canjea
el token por la sesión y redirige a `.../set-password/` antes de servir la UI.
Por eso la entrada local sirve el index solo en `set-password` o cuando el
enlace es inválido, y React, ante una ruta con token, muestra directamente el
estado «El enlace no es válido o expiró. Solicita uno nuevo.» sin enviar el
token. `GET /api/web/password/reset/<uidb64>/` fuerza siempre el marcador
`set-password` y valida solo el token guardado en la sesión: devuelve
`{"validlink": true, "fields": [...]}` con los campos del `SetPasswordForm`, o
`{"validlink": false}`. El POST revalida el enlace en cada envío: si expiró, se
usó o la contraseña cambió entre medio, responde `{"validlink": false}` sin
escribir. Si es válido conserva los efectos de `PasswordResetConfirmCustomView`
(guarda la contraseña, elimina el token DRF, limpia flags y temporales del
perfil, borra el token de sesión, sin login automático) y responde
`{"ok": true, "redirect": "/reset/done/"}`. El POST directo con token a las
rutas HTML se mantiene sin cambios.

React reproduce `user/password_reset_base.html` y sus cuatro contenidos: mismo
header, tarjeta, imagen lateral, pie y hojas de estilo (incluida
`password_reset.css`), marcado de campos de crispy-forms (`div_id_*`,
`requiredField`, `invalid-feedback`, ayudas `form-text`), títulos de pestaña y
enlaces «Volver al login» y «Solicitar nuevo enlace». Las contraseñas solo
viven en estado efímero y se limpian al responder; un resultado incierto o
rechazado bloquea el reenvío.

## Verificación

Sobre una copia aislada del árbol base `f0a36a9f`, con la imagen fijada, red
deshabilitada, fuente de solo lectura y SQLite sintética:

- RED backend: los 24 tests de
  `src/backends/sisoc_core/tests/test_web_password_reset.py` y los dos nuevos de
  `test_identity_preview.py` fallaron antes de implementar. GREEN: 251 tests
  aprobados entre los propios y las suites de login, cambio obligatorio, cambio
  voluntario, entrada de identidad, flujos de usuarios, sesión web y admin;
  `test_registro_de_urls_al_dia` aprobado. Los tests comparan errores y efectos
  con las rutas HTML originales y verifican el correo con el backend de memoria
  de Django.
- Black, Pylint (10/10), `makemigrations --check --dry-run` y
  `check_docs_paths --existencia` pasaron.
- Comparación de 1020 pedidos GET/HEAD/OPTIONS/POST sin CSRF por lado (cinco
  actores, todas las rutas `/api/web/` existentes, login y las páginas HTML de
  recuperación y cambio voluntario) entre base y este cambio: cero diferencias
  fuera de las dos rutas nuevas, sin escrituras ni correos. El recorrido HTML
  completo (solicitud con y sin coincidencia, canje, error, éxito y reenvío) es
  idéntico en base y candidato, y el recorrido por la API produce los mismos
  efectos.
- RED frontend: `PasswordReset.test.tsx` falló por módulo ausente y siete casos
  de ruta de `App.test.tsx` fallaron. GREEN: 202 pruebas Vitest de `apps/sisoc`,
  TypeScript, ESLint y build de Vite.
- Visual nativo contra React, solo GET, dos cargas por lado, 1440x900 y
  390x844: formulario, solicitud recibida, enlace inválido (ruta y alias),
  formulario de nueva contraseña tras un canje real (ruta y alias) y contraseña
  actualizada. Las 14 capturas son idénticas en píxeles, estables entre
  repeticiones y con geometría igual; sin máscaras, errores de consola,
  solicitudes bloqueadas ni POST, y dominio sintético sin cambios. La secuencia
  de Tab de ocho pasos coincide con la nativa en cuatro pantallas y ambos
  tamaños, con capturas enfocadas idénticas.

No se ejecutaron en navegador los envíos (estados con errores, correo y
guardado): los cubren las pruebas del componente y del backend. Tampoco se
ejecutaron la suite completa, CI, revisión nativa, prueba humana ni despliegue.
Riesgo técnico: credenciales y tokens de recuperación, transporte público
anónimo y contrato de rutas HTML.
