# Cambio: transporte backend de respuesta de encuestas (#2785, EQ-A)

## Corte backend actual

Esta unidad incorpora únicamente la cola pendiente y los adaptadores JSON de
respuesta, postergación y descarte, sus pruebas y el montaje de cuatro rutas.
Reutiliza los servicios, mensajes, validaciones y destinos seguros existentes.
No incluye administración de encuestas, React, preview, nuevas políticas de
audiencia ni cambios de modelos o permisos.

La verificación aislada pasa con 160 pruebas de respuestas, sesión, requisitos y
cuenta; Black en cuatro Python, Pylint y referencias documentales. Persisten
siete avisos previos. Se usó la imagen local fijada sin red, código de solo
lectura y SQLite sintético; sin navegador, TCP ni recuperación visual.

Las 48 regresiones HEAD observaron veinticuatro fallos internos y veinticuatro
casos externos correctos antes del ajuste puntual del adaptador admindocs. Solo
la ruta pendiente y las tres acciones numéricas reciben la excepción nueva;
se conservan las excepciones previas y los diagnósticos fuera de este alcance.
Sesión y requisitos de mayor prioridad se evalúan antes del método. Las acciones
siguen siendo POST-only: GET/HEAD autorizados devuelven 405 con Allow POST, sin
imponer un formato nuevo para ese error. La metadata inicializa CSRF; no se
supone que las acciones HEAD inicialicen esa cookie.

La comprobación independiente pasa 96 GET/HEAD y 152 comparaciones directas del
middleware contra el baseline. Metadata, presentación, respuestas, cumplimientos,
recordatorios y sesiones se conservan. Los servicios y vistas nativos siguen
idénticos a HEAD; las pruebas propias cubren validación, atomicidad y efectos.
No se repitieron POST ni la suite completa durante este cierre independiente.
Un redirect puede representar un error con mensaje y no acredita guardado.

Los controles de middleware no son una suite HTTP adicional. Los blobs corregidos
coinciden con GREEN; no se confunden bytes CRLF del archivo Git con blobs LF.
Requiere revisión técnica por requisitos de sesión y middleware compartido.
No acredita paridad visual, aceptación humana, CI ni despliegue.

Las secciones siguientes preservan el registro histórico del circuito completo.
Sus pruebas de UI, capturas, correcciones y cierre visual no son evidencia nueva
ni aceptación del corte backend actual.

## Registro histórico del circuito completo

## Alcance

Implementación local de Inicio y del circuito de respuesta de encuestas,
sin activar React globalmente ni modificar las vistas HTML de producción.
Los controles, modal y Home se construyen en React desde metadata explícita;
no se inserta HTML de formularios Django en el componente.

- `src/backends/sisoc_core/encuestas/web_answer.py` adapta las vistas originales
  de respuesta, postergación y descarte. Reutiliza sus servicios y mensajes.
- `PendingSurvey.tsx` (componente histórico no incluido) presenta los ocho tipos de
  pregunta, variantes Inicio/INET, modalidades y acciones de la fuente.
- la fábrica histórica de preview (no incluida en este corte) agrega `/inicio/`
  exclusivamente a la fábrica de preview local explícito.

No se agregan modelos, dependencias, permisos, políticas de audiencia o tokens.
El selector de grupos U07 permanece fuera de este cambio: su reparación funcional se autorizó por separado y no cambia el contrato de encuestas.

## Comportamiento y límites

GET/HEAD `/api/web/surveys/pending/` entrega únicamente la presentación ya visible
del marco, variante de Inicio, mensajes existentes y la primera ronda de la cola
nativa. Conserva el orden por cierre, incluso cuando una encuesta opcional
precede a una obligatoria. No expone segmentación, puntajes, respuestas previas
ni la identidad de cumplimiento de respuestas anónimas.

POST URL-encoded `/api/web/surveys/<id>/answer/`, `postpone/` y `dismiss/` usa
sesión y CSRF originales. Admite resolver el requisito propio de encuesta sin
otorgar acceso de negocio; acceso web, contraseña y perfil mantienen precedencia.
Los servicios originales validan elegibilidad, vigencia, modalidad, tipos,
condiciones y atomicidad. La respuesta contiene el destino validado de la vista,
no un indicador incondicional de guardado: los errores nativos también redirigen.

El frontend navega a ese destino completo y reconstruye el formulario, sin
conservar borradores tras un error ni repetir solicitudes inciertas. Los avisos
se consumen una sola vez. Las respuestas múltiples conservan valores repetidos;
los campos condicionales ocultos quedan deshabilitados y no se envían. El JS
condicional y Bootstrap originales se reutilizan sobre nodos propiedad de React,
sin reemplazar sus recursos por otra biblioteca o versión.

La entrada local conserva autenticación, middleware y comportamiento no-GET de
Inicio. Los assets siguen congelados por la fábrica existente, sin proxy hacia
proveedores externos ni activación en el URLconf de producción.

## Verificación en curso

Se observó RED de 17 contratos públicos por rutas ausentes y GREEN de los 17
tras implementar. Tres fallos intermedios se debían a solicitudes vacías del
fixture sin Content-Type; se corrigió el fixture, no la política de medios.
Diez pruebas React pasaron después del RED contra el componente vacío. La nueva
ruta App observó RED y luego las 44 pruebas focalizadas de App/encuestas pasaron.
La entrada Home tuvo RED por servir todavía HTML nativo, preservando el POST
nativo correcto. El seam integrado pasó 96 pruebas backend y 147 frontend;
Black, Pylint, tipos, lint y build terminaron correctamente. El registro conserva
sus 2753 entradas anteriores y agrega únicamente las cuatro rutas nuevas.

La ejecución canónica fuente/candidato completó 18 escenarios por lado y sus
efectos finales coinciden. La prueba de paridad visual permanece parcial: una
reescritura del harness temporal con codificación Windows contaminó textos
sintéticos en 17 fixtures del candidato. Sus diferencias no son defectos de
producto demostrados ni excepciones aceptadas. Se conservan los resultados y
no se repiten acciones exitosas; el cierre requiere capturas GET sobre estados
sintéticos equivalentes y revisión independiente fresca.

La revisión propia detectó además que el modelo admite orden de pregunta cero.
Se agregó una regresión React, observó RED y se corrigió únicamente la validación
de orden de pregunta/referencia, sin relajar los IDs ni cambiar reglas de dominio.
Las once pruebas focalizadas, tipos, lint y nuevo build pasaron.

La verificación independiente confirmó los límites públicos, lifecycle React,
assets y cinco observaciones HTML iguales al baseline. Reconstruyó las capturas
faltantes con fixtures equivalentes y sin repetir POST de negocio. El reintento
expresamente autorizado cerró los siete residuos pendientes: los 93 caracteres
no vacíos de cada caso coinciden en secuencia, estilos efectivos y fuentes, con
máximo 0,015625 CSSpx de diferencia. No se afirma igualdad de rectángulos de cada
espacio en blanco ni de variables CSS no utilizadas. El gradiente fresco fue
idéntico; el residuo histórico apareció al volver a rasterizar solamente la
fuente. Es evidencia de variabilidad del baseline, no una tolerancia de color.
El toast asentado es idéntico; sus propiedades de animación distintas permanecen
registradas. El coordinador repitió las siete aserciones offline y pasaron.
El cierre técnico EQ-A está observado; demostración final y aceptación humana
siguen pendientes y no se infieren de estas pruebas.

La evidencia se conserva en el task existente `odd/tasks/react-global-2785.md`.
No se afirma CI, aceptación humana, commit, publicación ni despliegue de EQ-A.

Risk: items 2, 3, 4 y 5 (acceso/CSRF, transporte y marco compartidos,
respuestas asíncronas, entrada local y recursos congelados).
