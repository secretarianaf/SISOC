# C2: importación local compuesta y pantallas de Montos en Comedores

Estado: aprobado por el responsable el 2026-10-15 para #2641. A las dos
decisiones pendientes respondió «1. apruebo» y «2. comedores». No autoriza C3,
commit, push, merge, cierre del issue, deploy ni acciones en entornos.

## Contexto y elección

El importador de Usuarios mezclaba lectura/cola/reportes transversales con
imports directos de PWA para expandir espacios, validar permisos y sincronizar
accesos. El worker confirma usuario, accesos y checkpoint del lote en una misma
transacción. Además, las pantallas kernel de Montos de Prestación escribían
Historial de Comedores durante su transacción.

Se aprobó el adaptador **local** de Espacios compartido por kernel, conservando
lectura, cola, filas, credenciales y reportes en Usuarios. La implementación del
dominio permanece en Comedores/PWA; no hay HTTP dentro de la mutación de fila.
Si falta el adaptador, las filas independientes siguen funcionando y las
dependientes se rechazan antes de escribir. Las reglas de Inspecciones siguen
en el importador transversal y no se trasladan por llamarse importación PWA.

El responsable eligió Comedores para las pantallas de Montos. Vistas, rutas,
templates y pruebas de operación pasan a ese dueño, conservando URLs, nombres y
permisos. El modelo `core.MontoPrestacionPrograma`, su tabla, ContentType, IDs,
formulario y recurso de exportación compartidos permanecen en kernel. El registro
Django admin de Montos se carga desde Comedores, con su ruta histórica
`/admin/core/montoprestacionprograma/` y permisos `core.*` sin cambios.
No hay migración ni separación de DB/storage/migrador. Historial no se promueve
al kernel para eludir el límite.

## Razones, alternativas y consecuencias

Las razones técnicas siguientes son la recomendación del agente aceptada por
el responsable; no se atribuye una explicación retrospectiva al responsable.
Separar usuario, acceso y checkpoint por HTTP introduciría commits parciales y
un resultado incierto en un timeout. El adaptador local conserva la transacción
actual, su lease y los rechazos del dueño sin otro protocolo de autenticación.
Mover todo el importador a Comedores acoplaría importaciones de otros programas
a su disponibilidad. Se mantiene la responsabilidad transversal de Usuarios.

El costo es que el proceso que ejecuta una fila de Espacios necesita el
adaptador y código del dueño instalados. C3 debe resolver la imagen del worker
sin hacer importar Usuarios al runtime web de Comedores ni instalar sus modelos
en el portal por accidente. No se crean en C2 imágenes, runtimes o workers nuevos.

La ausencia del proveedor no se convierte en autorización ni en una omisión
silenciosa de revocaciones. Se reutiliza el clasificador C1 de grupos/permisos;
los reemplazos con efectos de dominio se rechazan si no pueden validarse.
Los casos ambiguos se bloquean conservadoramente.

Montos pierde disponibilidad cuando su dueño Comedores cae, como consecuencia
de la propiedad elegida. Su escritura y la de Historial permanecen locales en
la misma transacción. Se conserva la política existente del escritor de Historial;
este corte no promete detección de errores que ese servicio ya suprima.

## Verificación, reversa y revisión de la decisión

Probar filas independientes sin adaptador, Inspecciones, rechazos de grupos y
permisos, expansión/asociación de organizaciones, errores de sincronización,
rollback del checkpoint, y rutas/permisos/operaciones de Montos con Historial.
El probe sin módulos de Comedores/PWA debe incluir los callers del importador;
pasarlo no demuestra una imagen aislada.

Rollback de C2 coordinando código/rutas/templates y adaptador anterior, sin
borrar tablas, filas o ContentTypes. Las migraciones y reversa C1 mantienen sus
requisitos propios. Revisar la decisión si se requiere ejecutar filas de
Espacios sin instalar su dueño, si Montos debe quedar independiente de Comedores
o si se activa la separación de datos #2725. #2725 sigue postergado.

Evidencia en
`docs/registro/cambios/2026-T4/2026-10-15-issue-2641-c2-consumidores-y-recursos.md`.
La aprobación define la elección; no acredita comprensión humana ni aceptación
funcional manual, cuyos ejercicios fueron delegados/declinados anteriormente.

Continuación C3 aprobada el 2026-10-16: se reutiliza la imagen completa del
migrador para el worker con rol propio, sin migrar ni servir HTTP. Ver
`docs/registro/decisiones/2026-10-16-c3-worker-importacion-imagen-migrador.md`.
