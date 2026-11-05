# Cambio: transporte backend de acceso web por sesión (#2785, ID-A)

## Corte backend actual

Esta unidad incorpora únicamente el transporte JSON de login, sus pruebas y el
montaje de su ruta. Reutiliza LoginView y el formulario existentes; no incluye
componentes React, nueva entrada HTML, configuración de assets ni API de logout.
Las rutas nativas de salida y sus controles CSRF permanecen sin cambios.

Las secciones siguientes conservan el registro histórico del circuito completo.
Sus resultados de frontend, capturas, correcciones y URL de demostración no son
pruebas nuevas de este corte ni afirman disponibilidad o aceptación actuales.
La verificación aislada del backend pasa: 94 pruebas de login, sesión y requisitos,
Black en cuatro Python, Pylint y referencias documentales. Persisten siete avisos
previos. Se usó la imagen local fijada, sin red, con fuente de solo lectura y
SQLite sintético; no se ejecutó navegador, TCP ni recuperación visual.

La revisión inicial encontró formato pendiente y que admindocs interceptaba
HEAD interno antes de inicializar CSRF. Una regresión observó un fallo interno
y un caso externo correcto; se añadió únicamente `/api/web/login/` a la
excepción del adaptador propio, manteniendo las excepciones de categorías.
Tras normalizar el test, la suite pasa. No fue un bypass de autenticación ni
una exposición de datos privados. La comprobación independiente limitada
confirma cuatro GET/HEAD internos/externos con CSRF y privacidad, sin sesión
autenticada ni X-View; 96 comparaciones directas contra el baseline conservan
categorías, sesión, INS-A y diagnósticos admindocs fuera del alcance. No son una
suite HTTP adicional. Requiere revisión técnica por afectar sesión/configuración.
Los blobs corregidos coinciden con GREEN; el archivo Git conserva sus bytes
CRLF y es equivalente tras normalización, no idéntico a los blobs LF.
Estas pruebas no acreditan paridad visual, aceptación humana, CI ni despliegue.

## Registro histórico del circuito completo

## Alcance

Implementación local del circuito ID-A, sin reemplazar rutas HTML de producción,
activar React globalmente ni cambiar políticas de autenticación. La selección de
la entrada React, el registro de rutas y los assets públicos de la demostración
son integración compartida, no responsabilidad de este módulo.

- `src/backends/sisoc_core/usuarios/web_login.py`: transporte público JSON que
  hereda `UsuariosLoginView` y el mismo `BackofficeAuthenticationForm`.
- `src/backends/sisoc_core/tests/test_web_login.py`: peticiones reales a las rutas
  registradas, sesiones sintéticas, CSRF y compatibilidad de ambas salidas.
- `Login.tsx` (componente histórico, no incluido en este corte): pantalla autónoma que reproduce el
  template `src/backends/sisoc_core/usuarios/templates/user/login.html`.
- `Login.test.tsx` (prueba histórica, no incluida en este corte): envío, errores, estados asíncronos,
  navegación y ausencia de consultas al contexto de negocio.

Se siguió el formulario y template de acceso existentes, no el shell de Insumos.
No hay modelos, dependencias, permisos, tokens PWA ni mecanismos de sesión nuevos.

## Comportamiento

GET/HEAD `/api/web/login/` inicializa CSRF anónimo y entrega únicamente los dos
campos del Form, `initial.username`, errores vacíos y el rótulo público de versión.
La respuesta es privada, `no-store` y varía por Cookie. No devuelve contraseñas,
identificadores de sesión, tokens, usuarios serializados ni navegación de negocio.

POST usa `application/x-www-form-urlencoded`, valida con el Form existente y
conserva la normalización de usuario y la contraseña sin trim. Datos inválidos
devuelven 400 con los errores originales y el usuario normalizado, nunca la clave.
JSON no admitido devuelve 415 después del control CSRF. Otros métodos no admitidos
devuelven 405. La denegación de una cookie con acceso web deshabilitado conserva
403 y no cambia de cuenta ni repara permisos.

El éxito devuelve `{ok:true, redirect}` usando el destino validado por LoginView;
la navegación real aplica después contraseña, perfil y encuesta, en ese orden.
Al convertir la redirección del framework a JSON se conservan sus cookies: perder
esa copia dejaría de enviar la nueva cookie CSRF aunque la sesión ya hubiera rotado.

La UI conserva el usuario y borra la contraseña tras un rechazo; no interpreta un
403 HTML de CSRF como credenciales inválidas. Ante resultado incierto no reintenta
automáticamente y requiere recarga para comprobar el estado. Ignora resultados
asíncronos de una pantalla abandonada y bloquea doble envío. La contraseña vive
solamente en el estado local del formulario; no se persiste ni se registra.

No se creó API de logout. Se mantienen `/logout` y `/logout/`, POST nativo con CSRF
y navegación completa; GET conserva 405 sin cerrar sesión. También funciona con
requisitos pendientes o acceso web deshabilitado después de iniciar sesión.

## Verificación local y limitación pendiente

El preflight previo comprobó 33 comportamientos públicos. La nueva API observó
RED con doce fallos 404 y terminó con 45 casos correctos. También se reprodujo y
corrigió el desvío de métodos/formato de contenido con sesión autenticada. Las
pruebas React observaron módulo ausente; después de la corrección visual final,
los trece casos propios, TypeScript y lint de los archivos propios terminaron bien.

La verificación integrada inicial del frontend terminó con 196 pruebas correctas,
TypeScript, lint y build correctos. Tras la corrección acotada se repitieron solo
las pruebas afectadas, tipos, lint y build; no se repitió toda la suite. Los dos
Python propios se normalizaron antes de verificar; Pylint propio terminó con
10.00/exit 0. La verificación integrada de backend y la revisión independiente son
responsabilidad del coordinador, no se sustituyen por estas pruebas propias.

La matriz vigente tiene quince casos ID-A y treinta combinaciones de viewport en
el manifiesto visual histórico de identidad (no incluido en este corte). Se ejecutaron
sesenta lados reales referencia/candidato: rutas, errores, acceso restringido,
rotaciones, destinos y ambas salidas de sesión cumplieron sus afirmaciones de
estado. La comparación inicial encontró veinte diferencias de geometría. Se
corrigió el aislamiento de estilos del acceso autónomo: mientras está montado,
se deshabilitan los links de estilos de negocio ajenos al allowlist exacto del
login original y se restauran sus valores al desmontar; también se conserva la
estructura flex del body mediante `display: contents` temporal en el root.

La regresión del ciclo de vida observó RED antes de la corrección y prueba la
restauración exacta del shell. El recheck acotado final de doce pares afectados
presentó geometría coincidente bajo S2 (ninguna diferencia de un CSS px o mayor),
fuentes originales cargadas, sin requests externos desconocidos ni errores JS.
No se repitieron los comandos de autenticación ya acreditados para comprobar el
layout posterior al logout. Se verificó además Enter por teclado, salida mediante
el botón nativo y Volver en referencia desktop y candidato desktop/mobile:
sesión de uno a cero registros y API de sesión anónima 401 después de volver.

**Resultado parcial de paridad visual:** siete de esos doce pares tienen PNG
idéntico. Cinco entradas en blanco conservan 26 píxeles distintos: 25 dentro del
SVG de Presidencia y uno en el borde de la contraseña, sin diferencia de geometría.
El caso desktop de campos obligatorios conserva 4488 píxeles distintos en la
región del foco del usuario: el POST nativo vuelve a enfocar el campo mediante
autofocus; la respuesta React muestra los mismos errores y geometría, pero no
restaura ese foco. No se enmascararon imágenes ni se solicitó una excepción nueva.
La coincidencia geométrica no se presenta como igualdad de pintura ni paridad
completa: esta diferencia de foco queda pendiente de resolución del coordinador.

El recheck también detectó una recodificación incorrecta durante la corrección;
se restauró UTF-8 y se compararon ocho textos originales, incluidos acentos y
elipsis, contra el bundle previo a la corrección. Los bytes finales no contienen
esa corrupción. Los fallos iniciales del harness —intercepción local de assets
por StaticFilesHandler, arranque aún no listo y expectativa 403 en lugar del 401
anónimo documentado— se corrigieron solo en artefactos temporales, no en producción.

Entorno autorizado: imagen local fijada `a8e59c769a92`, sin pull, fuente de solo
lectura, entorno limpio, SQLite sintético y red saliente de aplicación bloqueada;
Node y dependencias prescritas existentes. Assets originales cacheados con hash
idéntico en ambos lados. Sin datos reales ni valores de contraseña, token o sesión
en evidencias. La entrada headed local quedó disponible en
`http://127.0.0.1:55332/login/`; mostrarla no acredita aceptación humana.

## Riesgo y límites

### Corrección acotada del foco (2026-11-04)

La verificación independiente reprodujo el defecto mediante POST público vacío:
la referencia enfocó `id_username` y React dejó el foco en `BODY`, con los mismos
errores y sin cambios persistidos. El componente ahora restaura el foco del
usuario después de renderizar errores y habilitar nuevamente los controles.
La regresión observó RED antes del cambio y los 13 tests de Login pasaron después;
tipos, lint y build afectados también pasaron. No cambian autenticación, CSRF,
destinos, logout ni reintentos. El recheck independiente limitado sigue pendiente;
las capturas históricas no se presentan como prueba del nuevo bundle.

Riesgo: ítems 2/3/4/5 por autenticación/CSRF, contrato de transporte, respuestas
asíncronas e integración de la entrada. No hay commit, publicación, CI, merge,
deploy ni aceptación humana acreditados por esta nota. La paridad completa permanece pendiente por el foco descrito.
