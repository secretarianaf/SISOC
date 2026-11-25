# Cambio: compatibilidad de lista de espera CDF (#2811)

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

## Alcance

La URL histórica `actividadcentro_lista_espera` reutiliza la sección de espera de
`actividadcentro_detail` mediante 302 y `#lista-espera`. No se crea una pantalla ni
se completa un circuito React CDF. Contrato: ficha F6/W1 en
la ficha histórica F6/W1 del contrato aprobado (documento no incluido en este corte).

Archivos:

- `src/backends/cdf/centrodefamilia/views/participante.py`: CBV GET/HEAD con
  comprobación real de centro y actividad relacionada y destino fijo generado por
  reverse; otros métodos no admitidos.
- `src/backends/cdf/centrodefamilia/templates/centros/actividadcentro_detail.html`:
  solamente el atributo de ancla de la tarjeta existente.
- `src/backends/cdf/centrodefamilia/tests/test_lista_espera_compatibilidad.py`:
  regresión por URL pública y modelos sintéticos relacionados.
- `docs/operacion/cdf_lista_espera.md`: guía canónica, alcance y límites.

Se siguieron los redirects existentes de participantes a la ficha de actividad y
los patrones de fixtures de `test_asistencia_actividad.py`. No se cambian URL,
modelos, permisos, middleware, servicios, settings ni dependencias.

## Comportamiento

GET/HEAD públicos ordinarios autorizados responden 302 al detalle con fragmento;
objetos inexistentes o centro/actividad incongruentes responden 404. Se conserva
403 prioritario para visitante anónimo o usuario sin permiso, sin redirect a login.
No se usan `next` ni otros parámetros del cliente para decidir `Location`. Métodos
no admitidos responden 405 y no mutan participantes.

Se conserva expresamente el HEAD diagnóstico de admindocs: IP interna o usuario
activo staff recibe 200 con `X-View` antes de la vista. No se extiende la excepción
preexistente de APIs de sesión. Las pruebas públicas usan una IP sintética externa
y verifican el diagnóstico interno/staff por separado.

## Verificación

Primera preparación: el motor Docker estaba cerrado y no se implementó antes de
observar RED. Al recuperarse el runner autorizado se continuó con la misma unidad,
sin instalaciones ni arranque del motor por el agente.

Entorno: imagen local fijada `a8e59c769a92`, `--pull never`, fuente de solo lectura,
red deshabilitada en tests, entorno limpio, SQLite sintético y tmpfs. El launcher
`run_tests.py` configura `config.settings_all` con estado descartable; no usa una
base real ni valores ambientales. Comando focal:

```text
python /proof/run_tests.py src/backends/cdf/centrodefamilia/tests/test_lista_espera_compatibilidad.py -q --tb=short --create-db -o addopts= -o cache_dir=/scratch/cache --basetemp=/scratch/pytest
```

- RED original: 19 fallos/7 correctos; reprodujo template ausente y falta de ancla.
- Primer candidato con cliente loopback: 20 correctos/6 fallos HEAD. La causa era
  la interceptación diagnóstica preexistente, comprobada en el middleware instalado,
  no un fallo público ni motivo para modificar seguridad compartida.
- Comparación con IP externa sobre la base original, filtro `-k head`: cuatro
  fallos y cuatro correctos. Después, candidato completo: 28 correctos.
- Suite CDF existente: 106 correctos con los destinos
  `src/backends/cdf/tests` y `src/backends/cdf/centrodefamilia/tests`, excluyendo el
  nuevo archivo focal, una vez. Siete advertencias de Django/WeasyPrint en ambos
  tipos de ejecución; no se instalaron paquetes para silenciarlas.
- Black de vistas/pruebas correcto. Pylint del módulo de vistas termina con siete
  avisos preexistentes; comparación real con la base: ocho avisos, incluidos esos
  siete. El caché de Pylint de la imagen no era escribible; no se cambió el entorno
  global. No se presenta este lint como aprobado.
- Paths de documentación y sintaxis se verificaron localmente; no sustituyen HTTP,
  persistencia, navegador ni aceptación humana.

## Evidencia visual y funcional

Baseline/candidato usan los mismos datos sintéticos, assets cacheados y navegador.
Se completó únicamente la fuente Lora real del template con el helper existente,
restringido a Googleapis/gstatic: ocho recursos, cero errores, SHA256 de la hoja
`5bf048daa8488d4a5b3bea066e45cbc6d2b45a7bc7809c011375fd1cc53e07a6`.
No cookies, credenciales, assets sustitutos ni cambios de aplicación.

La comparación final de la ficha completa produjo cero píxeles diferentes en
1440×900 y 390×844, con Lora cargada. La barra de diagnóstico se cerró mediante su
control normal y se esperó un segundo para estabilizar la transición, sin máscaras.
Las primeras capturas sin fuente y durante la transición se conservaron como
preliminares; no se usaron como prueba final.

El recorrido de URL antigua llegó al fragmento visible en ambos viewports; Tab
alcanzó el enlace del participante con foco visible, sin overflow del documento.
No hubo assets desconocidos, hashes de caché inválidos ni excepciones de página.
La promoción GET mantuvo status/destino/cuerpo idénticos. El HTML completo contiene
nonces CSP y telemetría de desarrollo variables: no se afirma identidad byte a byte
entre respuestas crudas de detalle.

Artefactos y launchers conservados fuera del repo bajo
`TEMP/sisoc-cdf-w1-44bfd273728749bba9b65d4c4f60a618`: logs RED/GREEN, comparación
HEAD pública, suite CDF, Pylint base/candidato, caché Lora, resultados de navegador
y capturas `w1-final-detail-*`/`w1-final-redirect-*`. La referencia monta solamente
los dos archivos originales de comportamiento sobre el mismo target de solo lectura.

## Riesgos y límites

Riesgo: ítem 2, por precedencia del guard y correspondencia centro/actividad.
Verificación independiente y aceptación humana pendientes al cerrar esta unidad
local. Sin commits, publicación, CI, merge, deploy ni activación global.
