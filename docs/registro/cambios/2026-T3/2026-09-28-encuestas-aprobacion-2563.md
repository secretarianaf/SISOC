# Aprobación de encuestas — issue #2563, punto 5

El gestor solicita publicación en lugar de publicar directamente. El nuevo grupo
Administrador de Encuestas revisa configuración, preguntas y segmentación desde
la bandeja de pendientes, aprueba (publica y abre la primera ronda) o rechaza
(devuelve a borrador). Los permisos se controlan en rutas y servicios.

Se agrega el estado `pendiente_aprobacion` y el permiso `aprobar_encuesta`.
Las transiciones y las ediciones usan transacciones y bloqueo de la encuesta;
los pendientes no admiten modificaciones. No cambia la segmentación en caliente
de las encuestas ya publicadas ni el scheduler de rondas.

Decisiones: recepción mediante listado filtrado y contador, sin notificación
externa; edición bloqueada durante revisión; motivo de rechazo obligatorio, sin
separación entre creador y aprobador si una cuenta posee ambos permisos.
Se conserva la atribución de última modificación, sin nuevo historial dedicado.
El último rechazo guarda además motivo, fecha y revisor mediante la migración
0005. Un modal exige texto no vacío de hasta 2000 caracteres; el gestor lo ve en
la edición y accede desde el listado. Se conserva tras corregir y reenviar para
dar contexto al revisor, y un rechazo posterior lo reemplaza. No se exporta ni
se copia a nuevas versiones; los rechazos previos no reciben motivos ficticios.

Aplicar migración 0004 y ejecutar `create_groups`. Asignar revisores explícitamente;
ningún gestor obtiene automáticamente permiso de aprobación. La ruta anterior
`publicar/` sigue disponible, pero ahora solicita la aprobación.

Contrato canónico: `docs/implementaciones/encuestas.md`.
Cobertura: transiciones, permisos, edición bloqueada, doble aprobación, rollback,
revisión y regresiones del módulo. Los helpers de pruebas publican mediante el
nuevo circuito con un revisor separado, sin elevar al actor de cada prueba.

## Validación local

- 248 tests de `encuestas/tests` pasaron en SQLite, con Python 3.14 y Django
  5.2.16. Se utilizó MD5PasswordHasher únicamente en el proceso de pytest para
  acelerar fixtures; no se cambió la configuración del proyecto.
- Black y djlint: sin diferencias. Pylint del módulo: 10/10.
- `makemigrations encuestas --check --dry-run`: sin cambios pendientes.
- La prueba preexistente de archivo mayor a 5 MB recibió un ID corto: su nombre
  automático incluía todo el contenido y excedía el límite de entorno de Windows.
- En la primera validación Docker no estaba disponible. Esa ejecución no valida MySQL ni sustituye CI:
  el entorno local tiene dependencias compatibles con Python 3.14, distintas en
  algunos casos de los pins de producción. Pylint 4 requiere omitir la opción
  obsoleta `suggestion-mode`; al incluir `users/bootstrap/groups_seed.py` también
  informa el tamaño preexistente del archivo (más de 1000 líneas).

## Prueba posterior con Docker y datos locales

- Los 248 tests también pasaron dentro del contenedor (Python 3.11, SQLite).
  `manage.py check` sin incidencias y migración 0004 aplicada en `sisoc-local`.
- Se crearon siete usuarios exclusivos de QA, sin superusuario: gestor, aprobador,
  consulta de resultados, participante que responde, participante que descarta,
  participante para prueba manual y usuario fuera de segmentación.
- Se probaron las rutas HTTP del servidor real, con login y CSRF, sobre MySQL local:
  crear, segmentar, solicitar, aprobar, rechazar, corregir y reenviar; permisos por
  rol, bloqueo de edición incluso mediante POST directo, aprobación repetida sin
  duplicar ronda, respuesta, descarte y rechazo de respuestas fuera del segmento.
- Se dejaron cinco encuestas `[QA 2563]`: dos publicadas, una rechazada en borrador,
  una pendiente para revisión manual y una sin preguntas para probar validación.
  Solo incluyen los documentos sintéticos de los participantes nuevos.
- Se verificó que las encuestas preexistentes conservaran título y estado.
  Las credenciales de prueba se entregan al usuario; no se versionan.

## Ajuste de interfaz según Usuarios

Se toma `/usuarios/` como referencia para el listado y `/usuarios/editar/<pk>/`
para la revisión. Se reutilizan el buscador combinable, estilos de tablas y
acciones, y las tarjetas de datos del formulario de usuarios. La revisión agrupa
datos generales, destinatarios y preguntas; el panel de decisión explica qué
sucede al aprobar o rechazar y se apila en móvil.

Se agregan filtros por título, todos los estados, anonimato y recurrencia, con
mapa cerrado de campos y operadores. Los parámetros anteriores se conservan
mediante redirección al contrato `filters`; la selección queda visible y se
conserva durante la paginación. Se mantiene la importación y el control de roles.

Validación: 67 pruebas de vistas, aprobación y portabilidad pasaron en Docker,
incluidos filtros combinados, todos los estados, paginación y campos no admitidos.
Black y djlint sin diferencias; pylint de vistas y filtros: 10/10. En Chrome se
verificaron combinación y persistencia de filtros, Resetear y acceso a pendientes;
las dos pantallas a 390 px no desbordan el viewport y no registraron errores JS.

## Validación del motivo de rechazo

La migración 0005 se aplicó en MySQL local. Pasaron los 259 tests de encuestas
en Docker, Black, djlint y pylint (10/10). En Chrome se verificaron cancelar el
modal, impedir motivos vacíos o de solo espacios y confirmar un rechazo con
motivo. El gestor ve el texto, revisor y fecha al editar la encuesta QA nueva.
