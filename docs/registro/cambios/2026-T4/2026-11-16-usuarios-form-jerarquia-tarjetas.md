# Cambio: formulario de usuarios con bloques numerados y tarjetas jerarquizadas

## Alcance

Se pidió modernizar los estilos de `/usuarios/crear/` y jerarquizar sus tarjetas.
El template es el mismo para crear y editar, así que el cambio aplica a las dos pantallas.

Archivos:

- `src/backends/kernel/users/templates/user/user_form.html`
- `src/backends/kernel/static/custom/css/user_form.css`
- `src/backends/sisoc_core/usuarios/static/custom/js/user_mobile_access.js`
- `src/backends/kernel/users/identity_fields.py` (solo el widget de "Tipo de usuario")

No cambian validaciones, permisos ni el JS que maneja el alcance mobile.

## Comportamiento

- Las tarjetas se agrupan en tres bloques numerados: **Datos del usuario** (datos personales y
  de acceso), **Permisos en SISOC web** (permisos y roles, alcance territorial, equipos
  técnicos, administración de accesos) y **Aplicaciones mobile** (Espacios comunitarios,
  Territorial comedor, DataCalle, Inspecciones escolares). SISOC web va antes que mobile
  porque tiene más jerarquía. El bloque mobile solo aparece si el actor puede gestionar al
  menos una de esas apps.
- Hay tres niveles visuales de tarjeta: principal (borde y acento dorado), módulo (más
  compacta) e informativa (borde punteado, atenuada). Dentro del nivel módulo, las tarjetas
  web llevan borde lateral e ícono dorados; las mobile quedan neutras hasta que se habilitan.
- Cada tarjeta lleva ícono, título y una línea que explica para qué sirve.
- Las tarjetas de apps mobile se resaltan y muestran "Habilitado" cuando se tilda su
  interruptor (solo CSS, con `:has()`).
- Al activar "Espacios comunitarios" se oculta el bloque web completo, encabezado incluido.
  Antes ya se ocultaban sus cuatro tarjetas. La numeración de los bloques se ajusta sola.
- "Datos personales" suma el correo, al lado del tipo de usuario. "Datos de acceso" queda
  con usuario y contraseña en dos columnas iguales.
- "Tipo de usuario" pasa de radio a desplegable, con una primera opción vacía
  ("Seleccioná un tipo"): sigue siendo obligatorio y no se preselecciona ningún valor. El
  cambio está en `src/backends/kernel/users/identity_fields.py`, compartido con el
  formulario de usuarios PWA.
- "Ver contraseña" pasa a ser un ícono de ojo dentro del campo, sin texto visible. Mantiene
  `aria-label`, `aria-pressed` y `title`. Si el JS no carga, el botón queda debajo del campo.
- La tabla de solo lectura "Usuarios mobile creados por este usuario" pasa al final.
- La botonera queda fija abajo de la pantalla mientras se recorre el formulario.
- El título dice "Nuevo usuario" o "Editar usuario", y el breadcrumb dice "Agregar" o "Editar".
  Antes decía "Agregar" también al editar.
- Se reemplazaron clases de Bootstrap 4 que no tenían efecto en Bootstrap 5 (`mr-*`,
  `ml-2`, `text-right`, `badge-success`/`badge-secondary`).

Se conservan los `id` de todas las tarjetas que usan los tests y el JS. Las clases
`.card-custom`/`.card-header-custom` siguen en `user_form.css`, porque las usan
`encuestas/encuesta_revision.html` y `duplas/dupla_form.html`.

## Verificación

- `djlint --check` y `djlint --lint` sobre el template: sin cambios pendientes, 0 errores.
- `pytest -n auto` sobre los tests de la pantalla de usuarios (secciones por permiso,
  regresiones de usuarios, inspecciones escolares, contratos 2641, formularios PWA,
  DataCalle, layout de inspecciones, assets de Select2): 244 pasaron, 2 fallaron.
  Los 2 que fallan (`test_issue_2641_http_contracts.py`: operación compuesta y login) fallan
  en el setup porque el servidor auxiliar tarda más de 30 s en arrancar en el Docker local
  de Windows. No llegan a renderizar el template.
- Tests nuevos: `test_alta_usuario_tipo_usuario_es_desplegable_sin_preseleccion` en
  `src/backends/kernel/tests/test_users_regressions.py` y un caso en
  `src/backends/sisoc_core/tests/js/user_mobile_access.test.js` que comprueba que el bloque
  web completo se oculta en usuarios solo mobile.
- El DOM simulado de `user_mobile_access.test.js` sumó `createElement`, `append` e
  `insertBefore`: el script del ojo de contraseña los usa y sin ellos fallaban los 26 tests
  JS del archivo (en `development` pasaban 25).
- Revalidación del 2026-11-17: 26 tests JS pasan; en Python, 271 pasan y 2 se saltean en los
  tests de usuarios de `sisoc_core`, comedores y DataCalle. black, pylint y djlint sin
  observaciones.
- Revisión visual en navegador hecha en el entorno local: alta (bloques, desplegable sin
  preselección, ojo de contraseña, rechazo sin tipo), usuario solo mobile (bloque web
  oculto) y edición (tipo precargado y guardado).
