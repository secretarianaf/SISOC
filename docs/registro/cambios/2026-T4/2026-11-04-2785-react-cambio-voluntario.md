# Cambio: transporte backend de contraseña voluntaria (#2785, ID-E)

## Corte backend actual

Esta unidad incorpora únicamente el adaptador JSON de la vista de cambio
voluntario de contraseña, sus pruebas y el montaje de su ruta. No incluye la
UI React ni cambia las rutas HTML, el formulario, las políticas o los efectos
de sesión del framework.

Archivos del corte: `src/backends/sisoc_core/usuarios/web_password_change.py`,
`src/backends/sisoc_core/tests/test_web_password_change.py`, la ruta
`password/change/` en `src/backends/sisoc_core/usuarios/web_api_urls.py`, su
entrada `web_password_change` en `src/backends/config/url_registry.json` y la
inclusión de `/api/web/password/change/` en el conjunto de rutas propias de
`src/backends/config/middlewares/admindocs.py`, para que HEAD aplique la misma
sesión y los mismos prerrequisitos desde cualquier dirección, sin el
diagnóstico `X-View`.

### Verificación del corte backend (2026-11-06)

Sobre una copia aislada del commit base, con imagen fijada, red deshabilitada,
fuente de solo lectura y SQLite sintética:

- RED: los 23 tests del archivo propio fallan sin la ruta (404 y ausencia de
  cookie CSRF). GREEN: pasan junto con las suites relacionadas de login, cambio
  obligatorio, cuenta, grupos, encuestas, insumos web, entrada de identidad,
  flujos de usuarios y admin (597 tests aprobados).
- Cinco tests de `kernel/tests/test_health_urls.py` y
  `kernel/tests/test_servicios_backends.py::test_registro_de_urls_al_dia` fallan
  igual en el commit base sin este cambio: el registro de URLs ya no incluye
  diez rutas de vista previa `v2/sisoc/insumos/...` agregadas antes. Este corte
  agrega solamente la entrada que el generador `generar_registro_urls` produce
  para la ruta nueva; no regenera el resto del archivo.
- Black, Pylint (10/10), `check_docs_paths --existencia` y
  `makemigrations --check --dry-run` pasaron.
- Prueba independiente por HTTP con el cliente de pruebas de Django, dirección
  externa salvo los casos internos: el cambio exitoso por la API y por
  `/password_change/` producen los mismos efectos (contraseña nueva válida,
  clave de sesión rotada con el hash de autenticación actualizado, sesión
  actual activa, otras sesiones del usuario rechazadas en su siguiente pedido,
  `last_login`, perfil y tokens sin cambios). Contraseña anterior incorrecta,
  contraseñas distintas, campos faltantes, sesión anónima o de usuario inactivo
  (401), acceso web denegado, cambio obligatorio o confirmación pendiente
  (403), CSRF ausente o inválido (403), JSON (415) y PUT/PATCH/DELETE (405) no
  escriben datos ni sesiones. Un campo extra que nombra a otro usuario no lo
  afecta. La comparación de 720 pedidos GET/HEAD/OPTIONS/POST sin CSRF sobre
  todas las rutas `/api/web/` existentes y las páginas `/password_change/` y
  `/password_change/done/`, entre el commit base y este corte, sólo difiere en
  la ruta nueva.

No se ejecutaron la suite completa, CI, prueba en navegador ni aceptación
humana; no hay UI React en este corte.

## Unidad React separada (2026-11-06)

Esta unidad agrega las pantallas React del cambio voluntario y su página de
confirmación sobre la API ya incorporada. No modifica backend, rutas de
producción, el Form ni dependencias.

- `src/frontends/apps/sisoc/src/PasswordChange.tsx` tiene dos modos. En
  `/password_change/` muestra el `PasswordChangeForm` estándar con
  `old_password`, `new_password1` y `new_password2`, etiquetas, ayudas y textos
  que entrega `/api/web/password/change/`; no usa el formulario del cambio
  obligatorio. El POST es URL-encoded y solo navega al destino fijo
  `/password_change/done/` que devuelve Django; la sesión la conserva el
  framework. Los errores 400 limpian las contraseñas y muestran los errores del
  Form; un 403 muestra el aviso de acceso y un resultado incierto bloquea el
  reenvío y ofrece volver al formulario sin afirmar éxito. En
  `/password_change/done/` reevalúa el mismo guard antes de mostrar «Su
  contraseña ha sido cambiada.» y nunca envía POST.
- Ambos modos reproducen el template instalado de Unfold con sus mismos
  recursos: no usan el marco SISOC ni agregan contexto de tema. Los estilos
  ajenos se suspenden mientras el componente está montado y se restauran al
  desmontarlo.
- `App.tsx` monta ambos modos en sus rutas públicas, que coinciden con las
  entradas `IdentityVoluntaryPasswordEntry` e
  `IdentityVoluntaryPasswordDoneEntry` de
  `src/backends/sisoc_core/usuarios/identity_preview.py`.

### Verificación de esta unidad React

Sobre el árbol con grupos y encuestas React, en una copia aislada:
`PasswordChange.test.tsx` falló por módulo ausente y las dos rutas nuevas de
`App.test.tsx` fallaron antes de implementar. Después pasan las 176 pruebas
frontend, TypeScript, ESLint y el build de Vite.

Comparación visual en runtime sintético local, solo GET, dos cargas nuevas por
lado, 1440x900 y 390x844: la confirmación con usuario listo, el acceso anónimo
(redirige al login) y el usuario con cambio obligatorio pendiente (redirige a su
pantalla) son idénticos en píxeles y geometría, salvo el estado de render del
login ya conocido, que también varía entre dos cargas nativas. El formulario es
idéntico en geometría; la única diferencia de píxeles es el anillo de foco del
campo «Contraseña antigua». El template nativo depende del `autofocus` del
navegador, que en este runtime enfocó el campo en una de ocho cargas nativas;
React aplica el `autofocus` del Form en todas. Cuando la carga nativa enfoca el
campo, la captura móvil es idéntica a la de React.

Sin máscaras, errores de página, solicitudes bloqueadas ni POST; dominio
sintético sin cambios. El cambio real no se ejecutó en el navegador; lo cubren
las pruebas del componente y la verificación backend de arriba. No constituye
aceptación humana, revisión nativa, CI ni despliegue. Riesgo técnico:
contraseña y sesión, transporte público y respuestas asíncronas.

Las secciones siguientes preservan una nota histórica del circuito completo,
anterior a su cierre visual final. Sus resultados de UI, capturas y revisiones
no son pruebas nuevas ni aceptación del corte backend actual.

## Registro histórico del circuito completo

## Alcance

Se implementa el transporte web por sesión y la UI del cambio voluntario y su
página de confirmación. El alcance se sigue en `odd/tasks/react-global-2785.md`,
S9/T13, y en
el contrato histórico de remediaciones de identidad, no incluido en este corte.

Los cinco archivos de este circuito son el API
`src/backends/sisoc_core/usuarios/web_password_change.py`, su test
`src/backends/sisoc_core/tests/test_web_password_change.py`, el componente
`PasswordChange.tsx` (componente histórico no incluido), su test y este registro.
App, rutas, registro y bootstrap local son integración compartida del coordinador.
No se activa React globalmente ni se modifica admin/Unfold #2789.

## Comportamiento

`/api/web/password/change/` adapta la vista real `PasswordChangeView`. El Form es
`PasswordChangeForm`, con `old_password`, `new_password1` y `new_password2`.
La ejecución heredada conserva el guardado y la actualización de sesión del
framework. No se utiliza el helper del cambio obligatorio: no se limpian flags,
fechas ni temporales del perfil, no se revocan tokens y no se agrega transacción.

GET/HEAD devuelve descriptores de campo y textos del framework, sin valores de
contraseña, identidad, menú ni dumps de modelos/HTML. POST admite solamente datos
URL-encoded; devuelve errores del Form con 400 o el destino generado por Django
con 200. Las cookies de la respuesta heredada se conservan al adaptar el retorno.
La sesión ausente responde 401; acceso web, prerrequisitos y CSRF conservan la
denegación 403. Formato no admitido: 415; método no admitido: 405. Las respuestas
son privadas, no-store y varían por Cookie.

El componente admite los modos `form` y `done`, correspondientes a las rutas
originales `/password_change/` y `/password_change/done/`. Ambos reevalúan el mismo
guard antes de presentar contenido. Conserva contraseña anterior, etiquetas,
ayudas, errores, el destino fijo de confirmación y el texto «Su contraseña ha
sido cambiada.». Los valores sólo viven en estado efímero, se limpian al responder
o rechazar y no se registran. Las respuestas tardías se ignoran. Un resultado
incierto bloquea otro POST hasta revisar el estado; no hay reintento automático.

## Referencia visual heredada

En la imagen existente con Django 5.2.17, las dos rutas de aplicación resuelven
los templates de registro instalados de Unfold. La inspección local verificó
52 respuestas de assets con 200 y hash, fuentes Inter utilizadas cargadas y
`document.fonts.ready`. La apariencia parcialmente vacía no proviene de un CDN
faltante: el Form estándar produce inputs sin clases, borde ni padding; el
contexto genérico no aporta colores ni `has_permission` del admin. Por eso el
submit tiene texto blanco sobre fondo transparente y el header no muestra
herramientas. Es una limitación heredada de usabilidad, no una reparación incluida.

Se conservan los mismos recursos locales, clases y ausencia de contexto de tema.
No se agrega el shell SISOC, menú administrativo, otra fuente o paleta de colores.
Los estilos ajenos al template se suspenden sólo durante el montaje del componente
y se restauran con su estado previo al desmontarlo.

## Verificación

Se observó RED real por ausencia del endpoint público y del componente. La
verificación usa copias aisladas, imagen existente fijada, fuente readonly,
SQLite sintética y red saliente bloqueada; Node y dependencias existentes, sin
instalación en el repositorio. Los tests comparan errores y efectos con la ruta
HTML original del framework, incluyendo preservación de perfil/tokens, sesión,
rechazo sin escrituras y payload que no puede seleccionar otro usuario.

Se verificaron los 18 casos propios del API y la ruta HTML original, con los
mismos errores y efectos del framework; Black y Pylint de los dos archivos Python
pasaron tras normalizar con la configuración del proyecto. Los 10 tests React,
TypeScript y ESLint de la superficie propia también pasaron. La selección SISOC
integrada pasó 132 tests en un corte anterior; luego se verificaron únicamente
los deltas de Account y PasswordChange, los tipos/lint afectados y el build
integrado. No se presenta esa selección como una suite global de todos los fronts.

La matriz canónica inicial cubrió cuatro casos en desktop y mobile: ocho pares,
16 estados independientes. Requests, hashes de rechazo/lectura, sesión conservada
y ausencia de cambios extra en perfil/tokens pasaron; cada POST previsto ocurrió
una vez por estado. Seis pares fueron idénticos en píxeles. En los otros dos,
rechazo de contraseña antigua, se detectó un foco programático que agregaba un
outline ausente en la fuente, sin diferencia geométrica. Se reprodujo con un
regression test RED y se eliminó ese foco; los 10 tests, tipos/lint y un nuevo
build pasaron. La comprobación visual focalizada posterior y la revisión
independiente se registran separadamente en la tarea canónica; no se repite una
mutación exitosa para completar esa comprobación.

Persisten los avisos heredados de Django y WeasyPrint y la limitación de contraste
descrita arriba. La comparación no usa máscaras, fuentes alternativas, cambios
de golden ni dispensas visuales nuevas. No se interpreta como aceptación humana.
No se ejecutaron suites globales previas, CI, publicación o despliegue.

Riesgo técnico: autenticación y guards, transporte público y respuestas asíncronas.
La revisión independiente y la prueba humana permanecen separadas de estos checks.
