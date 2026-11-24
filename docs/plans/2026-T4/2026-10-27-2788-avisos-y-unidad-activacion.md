# Avisos tras operaciones y unidad de activación (#2788)

Estado: **E2, M2 elegida por el responsable: todos los formularios del alcance serán React**. No modifica mensajes,
router, endpoints ni la política de activación actual. La decisión afecta
convivencia/orden de publicación, no el aspecto final ni reglas de negocio.

## Caso concreto encontrado al refinar tareas

`InsumoUpdateView.form_valid` guarda por service, registra
`messages.success(..., "Insumo actualizado correctamente.")` y redirige a
`insumos_listar`. Alta y baja siguen el mismo patrón de aviso y retorno.

Hoy el listado Django hereda includes/base y renderiza
`includes/scripts/toastr_messages.html`: mensajes con su severidad y posición
inferior derecha. Si `/insumos/` pasa a React mientras edición sigue Django,
la edición puede guardar correctamente y redirigir a una página que ya no
renderiza ese partial. El router estático devuelve el index recibido, sin
composición de mensajes; el contrato propuesto `/api/web/session/` tampoco los
incluye. Por tanto, falta un mecanismo o una condición de activación para
preservar el aviso. No se reprodujo el flujo en navegador ni se afirma un fallo
de una versión desplegada.

Fuentes: `src/backends/sisoc_core/insumos/views.py`,
`src/backends/kernel/templates/includes/base.html`,
`src/backends/kernel/templates/includes/scripts/toastr_messages.html`,
`src/backends/kernel/core/v2_frontend.py` y
[contrato de contexto](2026-10-27-2798-contrato-contexto-web.md).

## Práctica existente revisada antes de proponer otro mecanismo

`src/backends/vpsl/ver_para_ser_libre/api_workflow.py` tiene adaptadores de
form/acción que leen mensajes en el contexto de esa operación y responden JSON
con error o éxito/mensaje/redirect. Es antecedente para dar feedback desde una
API de operación. No es un puente general para un POST legacy que ya redirigió
a otra página, ni prueba de entrega exactamente una vez o aislamiento de avisos
anteriores. Revisar semántica de almacenamiento al reutilizar el patrón;
no importar VPSL desde otro backend ni copiarlo sin pruebas.

No se localizó en la fuente inspeccionada un puente general para ese redirect
legacy→entry React. Tampoco se presume que el contexto VAT de INET lo sea.
La configuración/ejecución efectiva se verifica después, en entorno autorizado.

## Decisión vigente y alcance

El responsable aclaró: «todo debe ser react, no debe quedar formulario django,
por ende se parece mas a M2». Se adopta M2: activar por circuito completo React,
con formularios, validaciones visibles, errores, éxito y retornos compatibles.
La presentación Django de esos circuitos se retira tras aceptación y reversión
previstas. Django conserva APIs, servicios, validadores, autenticación, CSRF y
dominio; reutilizar clases Form para validar en servidor no mantiene una UI Django.

Desarrollo y comparación pueden seguir por slices, pero una lectura React con
formularios Django pendientes no constituye un circuito activado ni migrado.
No se planifica el puente M1. El login/remediaciones pueden migrarse como
circuito independiente, sin exigir reemplazar todo el sistema simultáneamente.
Retornos permitidos entre circuitos (incluidos next/referrer) se inventarían antes
de activar; no se descartan ni amplían por omisión. Formularios no migrados en
otros circuitos son deuda temporal explícita y bloquean el cierre integral.

El responsable confirmó: «React para toda la aplicación; admin/Unfold queda aparte».
La excepción admin/Unfold #2789 sigue vigente; no modificar ese trabajo paralelo. PDF y correos
generados en backend no son formularios de interfaz.

## Alternativas evaluadas (historial, no tareas vigentes)

| Opción | Cómo se publica un flujo | Ganancia | Costo / consecuencia |
|---|---|---|---|
| M1. Convivencia con puente acotado al ingreso | Se puede activar el listado React y conservar formularios Django. El core compone datos de avisos para ese ingreso autenticado y React los presenta con apariencia actual; no un endpoint de lectura general ni mensajes en contexto consultado en background | Permite publicar por partes más pequeñas manteniendo feedback de formularios legacy | Agrega contrato de bootstrap/privacidad del entry y ciclo de consumo; revisar avisos sensibles, cache/CSP, pestañas y reintentos. Evaluar retiro de la compatibilidad al terminar los callers legacy, sin copiar scripts inseguros |
| M2. Activación por circuito compatible | Validar lectura React en `/v2/`, pero activar la URL pública solo cuando las operaciones que retornan a ella ya tengan flujo compatible y feedback propio para React. Si falta, la entrada pública permanece Django | Evita un puente genérico/transitorio y mantiene avisos vinculados a cada operación; aprovecha el patrón de adaptación local existente | Publicación de lectura espera a esas operaciones, por lo que el conjunto de activación puede abarcar varios slices. El piloto sigue útil para validar paridad/esfuerzo sin publicación temprana |

**Recomendación inicial del agente, descartada tras la aclaración: M1**, con datos de avisos ligados al ingreso de página,
porque preserva la estrategia incremental ya elegida y evita perder feedback
cuando un formulario legacy vuelve a una lectura React. La fuente tiene retornos
flexibles (`next`/referrer) además de destinos fijos; con M2 hay que inventariarlos
para saber cuánto crece cada grupo de activación. No se garantiza por intuición
que baste migrar un solo formulario ni se inventa una estimación de demora.

La alternativa M1 descartada habría debido ser acotada al entry/flujo, con datos
emitidos solo por el core al usuario autorizado; el servidor estático nunca
recibe cookie, mensajes o credenciales. Usar primitivas y recursos existentes,
sin introducir un servicio nuevo por omisión. El diseño concreto y retiro del
puente se cierran antes de programarlo, no se amplía ahora `/api/web/session/`.

Propuesta concreta para poder revisar M1: el core obtiene el index estático sin
credenciales y compone la respuesta privada de ingreso con datos serializados
mediante primitivas seguras del framework; React representa esos datos. Assets
siguen públicos/versionados; el HTML que incluye avisos de usuario es private,
no-store y Vary Cookie. No ejecutar HTML/JS contenido en mensajes, no relajar CSP
ni compartir ese HTML entre usuarios. Las APIs de operación nuevas entregan su
propio resultado; no dependen de este puente para errores o éxito.

Orden propuesto: comprobar acceso, obtener index, componer respuesta privada y
entonces consumir avisos para esa entrega. Si el index/entry falla, no vaciar
la cola para devolver un 503. Probar el camino completo de una operación en
runtime que emite Set-Cookie/avisos y una navegación posterior al core: no basta
un test de serialización local ni asumir que el proxy conserva todo correctamente.
Las consultas de contexto en background no consumen avisos. Si la respuesta se
pierde después del envío, conservar los límites de entrega del framework y no
añadir una promesa de confirmación de lectura que todavía no existe.

M2 evita ese contrato de ingreso, pero necesita confirmar todos los retornos
legacy hacia la entrada que se activa, incluidos next/referrer permitidos. No
se puede cortar ese retorno ni perder un aviso para hacer que el grupo parezca
más pequeño. Según esos callers, la publicación puede quedar más acoplada.

## Garantías comunes a ambas opciones

- No perder ni duplicar feedback por asumir que un redirect es un éxito. Una
  operación que redirige tras error también requiere interpretación correcta.
- Conservar texto, severidad, posición y apariencia de los avisos actuales;
  no reemplazarlos por un Snackbar distinto sin justificación/aceptación.
- Datos de una operación pertenecen al usuario autorizado. Algunos mensajes
  de creación de usuarios contienen una contraseña inicial generada según
  `src/backends/sisoc_core/usuarios/views.py`; no volcar todos los mensajes en
  contexto compartido, logs, analytics, localStorage o artefactos. Este hallazgo
  es de código, no se leyó ni generó una contraseña real.
- No convertir HTML de mensajes en `dangerouslySetInnerHTML`. Representar de
  forma segura los contenidos que el flujo realmente necesita y revisar casos
  de enlaces/credenciales expresamente, sin declarar todo texto inocuo.
- No prometer uso único/exactly-once por usar almacenamiento Django. Probar
  navegación, mensajes anteriores, reload y pestañas concurrentes según alcance;
  no añadir cache/nonce/ack persistente para taparlo sin otra decisión.
- Nuevas APIs de operación preservan autorización/CSRF, validaciones, efectos,
  transacciones y resultado incierto ante pérdida de red. No crear un API que
  solo llame form.save y omita efectos de form_valid/service.
- Un redirect o aviso de éxito no acredita persistencia; pruebas funcionales
  y visuales se complementan, incluidas las de fallo parcial.

## Dependencias vigentes tras elegir M2

No se deriva una tarea de puente M1. Con M2 se añade
una dependencia de activación por circuito: I01 puede implementarse/probarse
separadamente, pero su URL pública espera la compatibilidad de I03 y demás
acciones que retornen a ella; categorías puede constituir otro circuito si sus
retornos son independientes. Enumerar callers/retornos, no bloquear un vertical
entero por una mutación no relacionada.

W1 de espera CDF sigue elegida y la tarea de alias puede definirse sin crear
pantalla nueva. Cuando su destino cambie a React, se aplica también la política
de feedback de las operaciones que regresan a esa ficha. G1/P1/C2/E2/I1 no se
reabren. M2 queda elegida; resta concretar por circuito sus formularios, acciones,
retornos y evidencia. La elección no acredita implementación ni aceptación visual.

Validación actual: lectura de productores/renderers/adaptadores y contratos
existentes, con referencias documentales. Sin app, DB, browser, mensajes reales,
capturas, CI, commit/push ni deploy.
