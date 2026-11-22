# Cambio: fábrica local de entradas React para identidad (#2785)

## Alcance

Se agrega `src/backends/sisoc_core/usuarios/identity_preview.py`, una fábrica
`identity_preview_patterns(build_directory)` que arma rutas para un URLconf de
vista previa aislado. Sirve el `index.html` de un build React fijo en las
mismas direcciones públicas de identidad: `/`, `/login/`, `/inicio/`,
`/password/first-change/`, `/mi-cuenta/`, `/mi-cuenta/confirmar/`,
`/password_change/`, `/password_change/done/` y `/grupos/` (listado, alta y
edición). La usan los circuitos ID-A, ID-C, ID-D, ID-E, U07 y EQ-A para las
pruebas locales de navegador.

La fábrica no se monta: no cambian `config/urls.py`, `config/urls_all.py`,
settings, middlewares ni `url_registry.json`. Solo un URLconf descartable de
prueba o de demostración local la importa.

## Comportamiento

- Cada entrada hereda de la vista fuente (`UsuariosLoginView`,
  `FirstLoginPasswordChangeView`, `MiCuentaView`, `ConfirmacionDatosView`,
  `PasswordChangeView` y `PasswordChangeDoneView` de Django, `GroupListView`,
  `GroupCreateView`, `GroupUpdateView`) y solo reemplaza el cuerpo del `GET`.
  El `dispatch`, los mixins de sesión, las redirecciones tempranas y el `POST`
  nativo (formularios, mensajes y destinos) quedan como en la fuente.
- `/password_change/` usa el `PasswordChangeView` de Django con
  `old_password`, no la API web de ID-E.
- `/inicio/` sirve el `index.html` solo para `GET`/`HEAD` con sesión; el resto
  de los métodos sigue en `core.views.inicio_view`.
- Las entradas de grupos conservan `permissions_any_required` como capa
  externa, con el mismo permiso de acción que `usuarios/urls.py`. Es la misma
  precedencia que las entradas de `insumos/preview_urls.py`: permiso primero,
  vista después.
- Los middlewares de acceso web, contraseña obligatoria y confirmación de datos
  se ejecutan antes que la entrada: un perfil sin acceso web recibe `403` y uno
  con contraseña pendiente se redirige a `/password/first-change/`, también
  con `HEAD`.
- Las respuestas HTML son `private, no-store`, varían por `Cookie` y entregan
  la cookie CSRF. Los parámetros de consulta no se copian al HTML.
- Los assets se congelan en memoria al crear las rutas, bajo
  `/sisoc-identity/react/` (antes `/static/sisoc-identity/`; ver
  `2026-11-22-2785-assets-react-ruteables.md`), con una lista cerrada de extensiones, `ETag`
  SHA-256, caché inmutable y `nosniff`. Una consulta, un archivo fuera de la
  lista o un enlace simbólico responde `404` o rechaza la construcción.

## Verificación

Entorno: imagen local fijada sin red, código de solo lectura, 768 MiB, 1 CPU y
SQLite sintético.

- RED: con el test nuevo y sin el módulo, 4 fallos y 12 errores, todos
  `ModuleNotFoundError: No module named 'usuarios.identity_preview'`.
- GREEN: `src/backends/sisoc_core/tests/test_identity_preview.py`,
  16 pruebas aprobadas. Cubren guardas anónimas, sin permiso, sin acceso web y
  con contraseña pendiente, también con `HEAD`; cabeceras privadas; ausencia de
  sesión anónima y de escrituras en usuarios y grupos durante `GET`/`HEAD`;
  el `POST` nativo de grupos y de cambio voluntario de contraseña; y la
  frontera de assets.
- Suites relacionadas sin cambios de comportamiento:
  `src/backends/sisoc_core/tests/test_web_login.py`,
  `src/backends/sisoc_core/tests/test_web_required_password.py`,
  `src/backends/sisoc_core/tests/test_web_account.py`,
  `src/backends/sisoc_core/tests/test_web_groups.py`,
  `src/backends/sisoc_core/encuestas/tests/test_web_answer.py` y
  `src/backends/sisoc_core/insumos/tests/test_preview_entry.py`: 284 pruebas
  aprobadas.
- Black (`--check`) sin cambios y Pylint 10.00/10 en los dos archivos Python;
  `check_docs_paths.py --existencia` sin referencias rotas;
  `makemigrations --check --dry-run`: sin cambios.

## Límites

- Con una IP de `INTERNAL_IPS`, `HEAD` sigue interceptado por el
  `XViewMiddleware` heredado antes de la vista, igual que en la ruta fuente y
  en la entrada de Insumos. Un test fija que la entrada no amplía esa conducta
  respecto de la fuente; las guardas `HEAD` se prueban con una IP externa. No
  se modificó el middleware compartido.
- No hay montaje productivo, activación global, CI, despliegue ni aceptación
  humana en este cambio.

Riesgo: items 2/3 (guardas de sesión y permisos, y rutas públicas compartidas
reutilizadas por la fábrica). Requiere revisión técnica.
