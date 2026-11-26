# Cambio: transporte backend de cuenta y confirmación (#2785, ID-D)

## Corte backend actual

Esta unidad incorpora únicamente los dos transportes JSON de cuenta propia y
confirmación, sus pruebas y el helper de presentación mínimo. Conserva el Form,
el guardado atómico, los guards y las rutas HTML originales. No incluye React,
modal, nuevas políticas ni activación global.

La verificación aislada pasa con 167 pruebas de cuenta, cambio obligatorio,
login, sesión y requisitos; Black en cinco Python, Pylint y referencias
documentales. Persisten siete avisos previos. Se usó la imagen local fijada sin
red, código de solo lectura y SQLite sintético; sin navegador ni servicio TCP.

Veinte regresiones HEAD observaron diez fallos internos y diez casos externos
correctos. Se añadieron solamente `/api/web/account/` y su ruta `confirm/` a la
excepción del adaptador admindocs propio. Conserva las excepciones de login,
categorías y cambio obligatorio; no incorpora el cambio voluntario pendiente.
No se observó exposición privada ni mutación por la respuesta diagnóstica.

La comprobación independiente pasa 40 GET/HEAD por ambas rutas, IP y estado de
acceso; privacidad, CSRF, redirects, sesión y datos se conservan. Otras 112
comparaciones directas de middleware coinciden con el baseline, y cuatro estados
del contexto existente son equivalentes a HEAD. El helper de presentación no
habilita `navigation` ni capacidades para sesiones pendientes. Los controles de
middleware no son una suite HTTP adicional; no se repitieron POST en este cierre.
Los blobs corregidos coinciden con GREEN; no se confunden bytes CRLF del archivo
Git con los blobs LF. Requiere revisión técnica por afectar controles de acceso
y contexto compartido. No acredita paridad visual, aceptación humana, CI ni deploy.

Las secciones siguientes preservan el registro histórico del circuito completo.
Sus pruebas de UI, correcciones, capturas y resultados no son evidencia nueva
ni aceptación de este corte backend. Las referencias a demostraciones son
históricas, sin afirmar que estén disponibles actualmente.

## Unidad React separada (2026-11-06)

Esta unidad agrega las pantallas React de cuenta propia y confirmación sobre las
APIs ya incorporadas. No modifica backend, rutas de producción ni dependencias.

- `src/frontends/apps/sisoc/src/Account.tsx` tiene dos modos. `/mi-cuenta/`
  muestra el formulario dentro del marco heredado; al guardar vuelve a consultar
  datos y avisos de la misma página, sin duplicar la notificación. En
  `/mi-cuenta/confirmar/` el formulario vive en el modal obligatorio, sin cierre
  ni ESC, y el éxito navega a `/inicio/`. Los POST son URL-encoded; los errores
  400 reconstruyen el formulario con los datos enviados, un 403 muestra el aviso
  de acceso y un resultado incierto bloquea el reenvío.
- `InsumosToast.tsx` acepta el nivel del mensaje de Django (por defecto
  `success`) y agrega `InsumosToastList`, un único contenedor Toastr para varios
  avisos. INS-A e INS-B siguen usando el aviso individual sin cambios.
- `shell.css` excluye el botón `data-mi-cuenta-submit` del anillo de foco del
  marco para conservar el foco nativo de la página original.
- `App.tsx` monta ambos modos con el marco heredado, alimentado solo por el DTO
  de presentación.

### Verificación de esta unidad React

Sobre la unidad de cambio obligatorio, en una copia aislada: `Account.test.tsx`
falló por módulo ausente, cuatro pruebas de nivel y lista de avisos y las dos
rutas nuevas de `App.test.tsx` fallaron antes de implementar. Con el componente
y antes del ajuste de `shell.css`, las dos pruebas de foco fallaron. Después
pasan las 133 pruebas frontend, TypeScript, ESLint y el build de Vite.

Comparación visual en runtime sintético local, solo GET, dos cargas nuevas por
lado, 1440x900 y 390x844: cuenta con usuario listo y confirmación con usuario
pendiente son idénticas en píxeles y geometría. Cambio obligatorio, login,
INS-A e INS-B se repitieron con el CSS nuevo: capturas idénticas byte a byte a
las de la unidad anterior. Al llegar con Tab a «Guardar datos» el contorno
calculado es el nativo y la captura es idéntica en cuenta (ambos viewports) y en
confirmación móvil.

Advertencias previas del marco compartido, que también se reproducen en el
listado de categorías de INS-B ya incorporado y no se corrigen aquí: el orden de
tabulación del sidebar difiere del nativo (posición visual idéntica), y al
enfocar con teclado el enlace de versión del pie la página nativa reduce su
altura a 906 px mientras React conserva 1036 px. Por eso la captura de foco de
confirmación en escritorio, cuyo recorrido pasa por ese enlace, no es idéntica.

Sin máscaras, errores de página, solicitudes bloqueadas ni POST; dominio
sintético sin cambios. El guardado real no se ejecutó en el navegador; lo cubren
las pruebas del componente. Las suites backend relacionadas (entrada de
identidad, login, cambio obligatorio y cuenta) pasan 136 pruebas en la imagen
fijada sin red. No constituye aceptación humana, revisión nativa, CI ni
despliegue. Riesgo técnico: guardado de datos personales, marco compartido y
respuestas asíncronas.

## Registro histórico del circuito completo

## Alcance

Implementación local del circuito de cuenta y confirmación, sin activar React
globalmente ni reemplazar rutas HTML de producción. Se conservan `/mi-cuenta/`
y `/mi-cuenta/confirmar/`, las validaciones de `MiCuentaForm`, el guardado atómico
de User/Profile y los controles de acceso originales.

- `src/backends/sisoc_core/usuarios/web_account.py`: adapta `MiCuentaView` y
  `ConfirmacionDatosView`; el usuario proviene exclusivamente de la sesión.
- `src/backends/sisoc_core/tests/test_web_account.py`: contratos por URLs públicas,
  sesión real, CSRF, rechazo sin cambios y compatibilidad del formulario nativo.
- `Account.tsx` (componente histórico no incluido): modos cuenta/confirmación; reutiliza
  cliente CSRF, presentación del frame y renderer de avisos existentes.
- `Account.test.tsx` (prueba histórica no incluida): envío, errores, estados inciertos,
  respuestas tardías, modal obligatorio y entrega única de avisos.

El coordinador es dueño de App, rutas/registro, entrada estática y helper de
presentación. No se agregan modelos, dependencias, permisos, sesiones alternativas
ni políticas de unicidad del correo electrónico.

## Comportamiento

GET/HEAD de `/api/web/account/` y `/api/web/account/confirm/` devuelve metadata
explícita, valores iniciales y errores de los seis campos permitidos: nombre,
apellido, mail, DNI, CUIL y correo institucional. Solo el último es opcional.
La presentación contiene únicamente los datos ya visibles de usuario, menú legacy
y versión. No incluye capacidades, estado ready ni otros atributos privados.

La cuenta ordinaria conserva los requisitos de acceso; la confirmación permite
resolver su propio requisito antes de la encuesta y conserva la prioridad de
acceso web y contraseña. Si ya está confirmada, conserva la redirección sin
escribir. Los rechazos no habilitan navegación de negocio ni modifican datos.

POST URL-encoded usa los hooks originales de vista/Form: 400 con errores del Form
o 200 con destino validado y mensaje original. Otros métodos y tipos de contenido
se rechazan; CSRF se mantiene. No se aceptan IDs arbitrarios, grupos, permisos,
rol, alcances ni flags privados. Se preserva la sesión Django y sus cookies.

El modo confirmación reproduce el modal sin cierre/ESC/backdrop dismiss y mantiene
los overlays después del footer, como el template original. La cuenta conserva
su destino canónico; después de guardar refresca metadata y entrega una vez los
avisos consumidos de Django, sin duplicar el eco del POST ni usar storage nuevo.
Los niveles de los avisos se proyectan mediante un conjunto cerrado de tipos
existentes, nunca como clases CSS provenientes de tags arbitrarios.

## Verificación local y limitación visual pendiente

Se observó RED público con 23 fallos de rutas ausentes y dos contratos nativos
correctos. Tras implementar y registrar las rutas, 71 pruebas focalizadas pasaron
(cuenta propia, suite original de Mi cuenta y 18 regresiones ID-C). La ejecución
usó una sola imagen local fijada, 768 MiB/1 CPU, sin pull, red saliente ni datos
reales; memoria máxima observada de 320278528 bytes, sin alcanzar timeout de 240 s.

El test React observó inicialmente módulo ausente; el ciclo de avisos observó
RED propio antes de su implementación. Once pruebas React y lint propio terminaron
correctamente. La comprobación inicial de tipos identificó estrechamiento de
estado y un import no usado; ambos se corrigieron. La comprobación final de tipos terminó correctamente. El addendum de avisos observó
RED propio y la suite final de cuenta pasó 28 pruebas, incluidos entrega única y
preservación de avisos previos, rollback y prioridad de perfil antes de encuesta.
Black con la configuración explícita del repositorio y Pylint propios finalizaron
correctamente. Se corrigieron únicamente el formato según target py311 y el nombre
convencional del mixin, sin suprimir diagnósticos.

El seam final autorizado de cinco módulos de identidad pasó 103 pruebas, sin
repetir las suites amplias previas. Los cinco Python compartidos pasaron Black
check-only y Pylint 10.00/exit 0. Memoria máxima observada de 332328960 bytes dentro
del límite de 768 MiB/1 CPU; ningún timeout. La comparación del registro mantuvo
las 2750 entradas anteriores y agregó solo las tres APIs autorizadas.

El build integrado fue compartido por ambos escritores. La matriz real inicial
cubrió ocho casos en desktop/mobile: 16 pares y 32 lados funcionales correctos,
sin errores JS ni requests externos desconocidos. Cada ejecución partió de un
clon SQLite nuevo y cerró su contexto y conexión antes de la siguiente. Los hashes
pre/post de las 32 ejecuciones están conservados; los nombres de DB iniciales eran
por lado/caso, no viewport, por lo que se retienen 16 DB finales y el esquema
(desktop fue reemplazado en esos paths al ejecutar mobile). No se reconstruyeron
ni repitieron esas ejecuciones para modificar la evidencia.

Los rectángulos ocultos de un modal genérico legacy y selectores de ayuda con IDs
distintos generaron diferencias iniciales del harness, no elementos visuales
faltantes. Un probe DOM de solo lectura confirmó texto, clases y rects idénticos
de `.form-text`, y asociaciones aria-describedby válidas en ambos lados. Esos
IDs se conservaron, sin cambios cosméticos ni nuevas excepciones.

Se corroboraron dos defectos reales mobile: la vuelta a cuenta conservaba 237 px
de scroll de ventana, y la confirmación inválida conservaba 95 px del modal-body.
Se observaron dos regresiones RED y se corrigió únicamente la restauración de
scroll después del commit de markup, como una recarga nativa. Los doce tests React,
tipos y lint propios pasaron. Un rebundle compartido incluyó ese lote y el ajuste
independiente de ID-E; no se repitió la suite amplia. El recheck quedó limitado a
los dos pares mobile fallidos y dos pares de entrada sin guardar: geometría cero
en los cuatro; los dos pares de scroll son además pixel-idénticos. Cada recheck
usa DB/media con lado, caso y viewport distintos y conserva las capturas iniciales.

**Resultado parcial de pintura:** diez de los dieciséis pares iniciales eran
pixel-idénticos. Los dos defectos de scroll ya están resueltos. Permanece una
diferencia de 2776 píxeles en el contorno de foco de Guardar datos: blanco/negro
en el documento nativo y dorado en React, con el mismo botón enfocado y rectángulo
idéntico. Aparece en las entradas de cuenta y confirmación y se conserva en el
smoke final de cuenta. No se declara paridad completa ni se extiende S2 como una
excepción de pintura. La clasificación de este contorno fue posterior al lote
propio; no se abrió otro lote de corrección. La verificación independiente recibe
el hallazgo y las capturas originales para corroborarlo.

Los runtimes propios se detuvieron tras guardar recibos, respetando el lease de
768 MiB/1 CPU. Picos observados: 297250816 bytes en matriz inicial y 289812480 en
recheck. El endpoint local de la última prueba fue
`http://127.0.0.1:55432/mi-cuenta/`; no queda servidor propio en ejecución. La
prueba humana/entorno visible final se mantiene como gate del coordinador después
de la verificación independiente; no se presenta una captura como aceptación.

Los artefactos son sintéticos y no registran contraseñas, tokens, identificadores
de sesión ni cuerpos sensibles. Los resultados locales no acreditan CI, despliegue
ni aceptación humana.

## Riesgo y límites

Riesgo: ítems 2/3/4 por autenticación y requisitos, contrato de transporte y
respuestas asíncronas. La habilitación global, Git, publicación, revisión nativa y
prueba humana pertenecen al coordinador y no están acreditados por esta nota.


## Corrección independiente del foco

La verificación independiente corroboró que la regla global de foco de React sustituía el contorno nativo del botón de cuenta y confirmación. Se excluye únicamente el selector existente `data-mi-cuenta-submit` de esa regla, sin eliminar el foco nativo ni cambiar los botones de otros circuitos. Las regresiones comprueban la exclusión en ambos modos y la conservación del selector para otros botones. La revalidación independiente limitada pasó: cuenta y confirmación en escritorio y móvil conservan el foco nativo, la geometría y cuatro pares de capturas completas sin diferencias de píxeles. No se repitió la matriz completa.
