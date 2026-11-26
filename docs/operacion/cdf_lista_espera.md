# Lista de espera CDF: compatibilidad W1 (#2811)

## Corte actual en Migracion-2

Esta unidad conserva exclusivamente la compatibilidad W1 de la URL de espera
y el ancla de la ficha nativa existente. No incorpora React, nuevos permisos,
modelos, servicios ni operaciones de promoción.

Estado verificado del corte (2026-11-06), con datos sintéticos locales:

- RED real sobre la base: 17 fallas y 11 aprobadas (templates, métodos y ancla
  ausentes). Sobre el árbol corregido: 28 pruebas focales y 106 relacionadas
  aprobadas; Black, Pylint 10/10, djlint y rutas de documentos correctos.
- Verificación independiente: guardas externas, redirect fijo 302 a
  `#lista-espera`, 405 para métodos distintos de GET/HEAD, HEAD público frente a
  diagnóstico interno y ausencia de escrituras de dominio. Sin solicitudes de
  promoción, asistencia ni otras acciones de negocio.
- Comparación visual nativa en escritorio 1440x900 y móvil 390x844: cero píxeles
  distintos, sin diferencias de geometría, texto ni estilos y sin máscaras. Ancla,
  scroll, teclado y 403 negativo correctos. Se mantienen como advertencias de la
  base el scroll horizontal nativo de la tabla, los mensajes 403 esperados en
  consola y una advertencia de Pillow.
- Prueba humana local confirmada: con sesión autorizada, la URL de espera llega a
  Lista de Espera; en una ventana privada se deniega con 403. No se ejecutó
  Promover ni Dar de baja.

Esta confirmación acepta solo este recorrido local de compatibilidad. No es
aceptación de producción, de la migración global a React ni consentimiento de
revisión. Riesgo: ítems 2 (precedencia de permisos) y 3 (contrato de la URL
histórica compatible).

Las secciones siguientes preservan la evidencia histórica de origen. Sus
resultados, capturas y diagnósticos no son pruebas nuevas ni aceptación de este
corte. No se repetirá la consulta de promoción para cerrar capturas.

## Registro histórico de origen

## Estado y alcance

Implementación local verificada el 2026-11-03 con datos sintéticos. La URL
histórica redirige a la ficha existente, que incorpora un ancla. W1 no cambia
configuración, dependencias, modelos, permisos ni datos existentes. No es un
circuito CDF completo migrado a React; CI, despliegue y aceptación humana se
acreditan por separado.

## Motivo

Antes del cambio, `actividadcentro_lista_espera` apuntaba a una vista de lista que
filtraba participantes por actividad y referenciaba un template ausente en la
aplicación. La fase RED reprodujo `TemplateDoesNotExist` con datos sintéticos;
esto no demuestra un incidente en producción.

`actividadcentro_detail` ya presenta inscritos, lista de espera y promoción. Se
reutiliza esa pantalla sin crear otra lista ni modificar su contenido.

Fuentes:

- `src/backends/cdf/centrodefamilia/urls.py`.
- `src/backends/cdf/centrodefamilia/views/participante.py`.
- `src/backends/cdf/centrodefamilia/views/actividad.py`.
- `src/backends/cdf/centrodefamilia/templates/centros/actividadcentro_detail.html`.

## Comportamiento

- Se conserva la URL y su decorador externo `centrodefamilia.view_centro`.
- GET y HEAD públicos ordinarios autorizados comprueban que existen centro y
  actividad y que la actividad pertenece al centro. Responden 302 al destino
  generado por `reverse("actividadcentro_detail", kwargs={"pk": actividad.pk})`
  seguido de `#lista-espera`. HEAD no devuelve cuerpo.
- IDs inexistentes o relación incongruente: 404 después del guard.
- Visitante anónimo o usuario sin permiso: 403 antes de consultar objetos o
  resolver métodos no admitidos; no se convierte en redirección a login.
- Otros métodos: 405 para un usuario autorizado. No se promueven ni modifican
  participantes ni se usan parámetros del cliente para construir `Location`.
- La tarjeta existente recibe solamente `id="lista-espera"`. Se conservan texto,
  estilos, tabla, estado vacío y formularios de promoción.

La consulta de detalle conserva sus permisos actuales; no se añaden por analogía
los controles de tomar asistencia o gestionar un centro.

### HEAD diagnóstico preexistente

Las reglas anteriores describen solicitudes desde IP externa y de usuarios no
staff. Admindocs intercepta HEAD si la IP pertenece a `INTERNAL_IPS` o el usuario
está activo y es staff: conserva 200, cuerpo vacío y `X-View` antes de llegar a la
vista. No se amplió la excepción existente de las APIs de sesión ni se modificó
middleware alguno para W1.

Las pruebas separan explícitamente el cliente público sintético
(`REMOTE_ADDR=203.0.113.42`) del diagnóstico interno/staff. El valor loopback
predeterminado del cliente Django no representa este recorrido público. Se
comprobó el diagnóstico tanto en la base como en el candidato.

## Verificación local

Pruebas:
`src/backends/cdf/centrodefamilia/tests/test_lista_espera_compatibilidad.py`.
Usan URL pública, modelos sintéticos relacionados y estado persistido antes/después.

Runner: imagen local fijada
`sha256:a8e59c769a921d84cf449d17b9bd173bd72c367d376d3e604d95ff2c0abe9502`,
sin pull, red deshabilitada, fuente de solo lectura, entorno sintético limpio,
SQLite y scratch fuera del worktree. No ejecutar el comando con una base compartida
ni configuración ambiental:

```text
python /proof/run_tests.py src/backends/cdf/centrodefamilia/tests/test_lista_espera_compatibilidad.py -q --tb=short --create-db -o addopts= -o cache_dir=/scratch/cache --basetemp=/scratch/pytest
```

Resultados observados:

- RED inicial: 19 fallos y 7 casos correctos sobre la vista original. Parte de los
  fallos HEAD correspondía al diagnóstico interno, no a una petición pública.
- RED público corregido contra los bytes originales: cuatro fallos de HEAD y
  cuatro casos correctos; no se ocultó ni deshabilitó middleware.
- Candidato: 28 casos W1 correctos, incluidos diagnóstico interno y staff.
- Regresión existente CDF: 106 casos correctos, incluida asistencia.
- Black de los dos Python propios correcto. Pylint del módulo de vistas conserva
  siete avisos preexistentes; la base tiene esos siete y un import adicional sin
  uso. No se hizo limpieza ajena al comportamiento solicitado.

## Comparación visual y navegación

Se comparó la ficha completa anterior/candidata en escritorio 1440×900 y móvil
390×844, con el mismo navegador, datos y bytes de assets públicos en caché. La
fuente de referencia difiere solamente en los dos archivos W1 originales. La
barra de diagnóstico se cerró mediante su control normal en ambos lados y se
esperó a que terminara su transición; no se enmascararon regiones.

Se completó la caché de Lora mediante el helper existente de assets públicos,
restringido a `fonts.googleapis.com` y `fonts.gstatic.com`: ocho recursos con
SHA256, sin cookies, credenciales, sustitutos ni dependencias nuevas. El título
usó Lora cargada en ambos lados. Las capturas finales tienen cero píxeles
diferentes en ambos viewports, sin assets desconocidos, hashes inválidos ni
excepciones de página observadas.

La URL antigua respondió 302 y el navegador llegó al fragmento visible. Tab
alcanzó el enlace del participante en espera con foco visible; no hubo overflow
del documento en ninguno de los viewports. La respuesta GET de promoción conservó
status, destino y cuerpo respecto de la base. La identidad visual no implica
aceptación humana ni prueba de un entorno desplegado.

## Reversión y límites

La reversión se limita a la vista compatible y al atributo de ancla. No debe
revertir operaciones de participantes ni reconstruir un template ausente. No se
modificaron servicios, registro de URL, guard compartido ni middleware. La
verificación independiente y la aceptación humana son pasos separados.

## Referencias

- la ficha histórica F6/W1 del contrato aprobado (documento no incluido en este corte), ficha F6/W1.
- `docs/registro/cambios/2026-T4/2026-11-03-2811-cdf-lista-espera-compatible.md`.
