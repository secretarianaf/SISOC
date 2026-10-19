# #2641 C1: disponibilidad, identidad y contratos propuestos

Estado: **contratos y traslado de auditoría aprobados; implementación local validada**.
Fecha: 2026-10-15. Conserva la propuesta aprobada como antecedente; el resultado
se registra en `docs/registro/cambios/2026-T4/2026-10-15-issue-2641-c1-identidad-y-disponibilidad.md`.
Complementa el diagnóstico de fronteras y el registro de C0, ya validado localmente.

## Criterios confirmados por el responsable

El usuario indicó:

1. Ante caída de Comedores/Espacios comunitarios, conservar inicio/cierre de
   sesión, cambio/recuperación de contraseña, consulta de datos propios y todo
   lo demás que pueda funcionar para los otros programas.
2. Mantener disponible toda administración que pueda operar; bloquear sólo
   lo que necesite el servicio caído.
3. Mostrar los últimos valores disponibles del dashboard ante una falla.

Interpretación propuesta para aceptación: una operación demostrablemente
independiente de Comedores no consulta ese backend como condición de éxito.
Si cambia accesos de Espacios, duplas o una regla que los necesita, se ejecuta
completa con ese dueño o se bloquea completa. No se guarda una parte del mismo
formulario mientras otra falla. Conservar datos anteriores no implica usarlos
para autorizar nuevas acciones.

Siguen confirmados: nombre **Espacios comunitarios**, proxy actual durante la
preparación, sesión y credenciales existentes, DB/almacenamiento/migrador compartidos,
#2725 postergado, sin commits/push/merge/deploy autorizados. El usuario delegó
la revisión y pidió omitir el ejercicio de modos de falla; no se lo vuelve a pedir.

## Evidencia adicional que condiciona C1

- `usuarios.forms` mezcla formularios de login, recupero y Mi cuenta con
  `PWAAccessMixin` y modelos de Espacios. `usuarios.views` importa todo ese módulo
  y `AccesoComedorPWA`, incluso para exponer vistas de identidad.
- `usuarios.api_views.UserLoginViewSet` admite Espacios, territoriales,
  Datacalle e Inspecciones; SIIS tiene una rama propia. El OR actual consulta
  Espacios antes de las capacidades de los demás programas.
- `/api/users/me/` mezcla identidad y contexto de Espacios. Un error puede
  conducir al fallback general y vaciar permisos que son independientes.
- `usuarios.services_password_reset_pwa.request_password_reset_for_identity`
  exige hoy `is_pwa_user`, incluso aunque el endpoint tenga nombre compartido.
  No basta con mover imports para garantizar recupero a los otros programas.
- `pwa.services.auditoria_service` persiste `AuditoriaSesionPWA` y consulta
  contexto de Espacios. Su implementación actual captura fallas y registra el
  error; no garantiza bloquear el login si falla la escritura de auditoría.
- La auditoría de sesión sólo tiene FK a User y snapshots JSON/IDs; no FK a
  Comedor. La auditoría de operaciones de negocio sí tiene relaciones de dominio.
- `UserDeleteView` desactiva `User.is_active`; no borra físicamente al usuario.
  Esa operación de identidad puede seguir siendo central, con el mismo alcance
  del actor. No habilita nuevas bajas en tablas de Espacios.
- `CAMPOS_POR_SECCION` ya identifica secciones de Espacios, territoriales,
  equipos técnicos, Datacalle, Inspecciones y administración. Se puede reutilizar
  para separar responsabilidades; también hay que revisar cambios indirectos
  de grupos/permisos, no sólo los nombres enviados por el navegador.
- `dashboard.Dashboard` ya guarda `llave/cantidad` y lo consume el dashboard y
  Django admin. Sus cinco indicadores actuales se actualizan con callbacks
  locales de Comedores/Relevamientos. Se conserva esa tabla como último resultado
  válido; no se introduce otra caché ni se retira el admin.

## División recomendada para C1

| Responsabilidad | Dueño | Comportamiento si Espacios está caído |
| --- | --- | --- |
| Credenciales, sesión/Token, contraseñas y datos personales | Portal + kernel users | Continúa para los otros programas; conserva sus verificaciones propias |
| Consulta y cambios independientes de usuarios | Portal, usando servicios compartidos de identidad | Continúan; no vacían ni modifican campos/permisos de Espacios por omisión |
| Alta/edición compuesta con accesos de Espacios o duplas | Comedores | Se bloquea la operación completa si ese dueño no responde |
| Elegibilidad y contexto de Espacios | Comedores | Se informa indisponibilidad; no se interpreta como ausencia o autorización |
| Registro común de autenticación | Kernel, propuesta de traslado de estado abajo | No depende de importar ni consultar código de Espacios |
| Auditoría de operaciones/accesos de negocio | Espacios comunitarios, dentro de Comedores | Permanece junto a la operación de negocio |
| Presentación y último agregado válido de indicadores | Portal/dashboard | Conserva valores previos; avisa que no se pudieron actualizar |
| Cálculo de indicadores de Comedores | Comedores/Relevamientos | No se calcula en el portal importando modelos del dominio |

Alternativa principal: ejecutar también el ABM genérico o toda autenticación en
Comedores. Conserva más código junto, pero una caída de Comedores impediría
operaciones ajenas. No satisface la disponibilidad solicitada y no se recomienda.
Otra alternativa, separar los pasos de una misma mutación entre procesos,
introduciría resultados parciales; se mantiene descartada por la atomicidad requerida.

## Contratos HTTP propuestos

Se conservan las URLs públicas y el formato exitoso actual de login. Las rutas
internas propuestas no se agregan a los prefijos públicos del proxy. Los nombres
de esas rutas son propuesta del agente, no implementación existente.

### Login y contexto

- Portal valida las credenciales con los servicios actuales. SIIS conserva su
  API key, habilitación y flujo propios. Datacalle/Inspecciones se comprueban
  con sus servicios compartidos actuales, sin pedir permiso a Comedores.
- Si necesita comprobar exclusivamente elegibilidad de Espacios, reenvía la
  solicitud de login a `/interno/espacios/login/` en el backend Comedores.
  El dueño vuelve a validar las credenciales y su acceso antes de emitir o
  reutilizar el Token existente. No se crea un Token provisional, una firma
  nueva ni se acepta un user_id de header como prueba de identidad.
- Costo explícito: ese camino puede validar la contraseña dos veces. No se
  introduce una credencial entre servicios para evitar esa validación.
- Credenciales inválidas mantienen el rechazo actual. Credenciales válidas cuya
  habilitación depende de un backend caído reciben indisponibilidad, sin emitir
  acceso ni afirmar que el usuario carece de habilitación.
- `/api/users/me/` obtiene primero identidad, permisos y scopes que pertenecen
  al kernel. Consulta `/interno/espacios/contexto/` con el Token del solicitante
  para el contexto de negocio. El backend autentica al actor por sí mismo.
- Propuesta de compatibilidad del contexto: mantener los campos actuales y añadir
  `espacios_comunitarios_disponible: true|false` en el nivel superior de `/me/`.
  Con false, conservar identidad, permisos y scopes del kernel; mantener la forma
  de los campos de Espacios con listas vacías/defaults conservadores y declarar
  explícitamente que no representan una comprobación de ausencia de accesos.
  No usar esos defaults para autorizar mutaciones. Contrastar consumidores y
  schemas estrictos en la validación antes de incorporar. No reutilizar el
  fallback actual que vacía también los permisos generales.
- Logout y cambio/confirmación de contraseña se resuelven contra la identidad
  compartida y mantienen la revocación de Token actual sin consultar Espacios.
- Recupero debe admitir también las identidades habilitadas de los otros
  programas: conservar usuario+email, respuesta antienumeración y rate limit.
  Para esos usuarios se reutiliza el flujo web SISOC de recupero, sin inventar
  URLs de fronts externos. El enlace actual de Espacios debe preservarse en su
  propio camino. Propuesta para usuarios con accesos combinados reconocidos por
  los servicios de identidad: usar el flujo web central para no consultar Comedores
  como condición del recupero. Eso puede cambiar el destino del enlace para un
  usuario mixto; se incluye en la aprobación del contrato y en las pruebas.

### Administración y transacción compuesta

- Mantener una entrada de administración. Extraer formulario/servicio de identidad
  de las dependencias de Espacios; las capacidades de dominio se obtienen del dueño.
- Clasificar en servidor el conjunto completo de cambios, usando secciones,
  permisos del actor y efectos de grupos/permisos. Un campo oculto del cliente
  no decide qué validaciones se omiten.
- Cambios personales/genéricos independientes se guardan en el portal. Los
  campos de Espacios no presentes se conservan: ausencia no significa revocación.
- Si el guardado incluye accesos de Espacios/duplas, reenviar la operación
  completa a `/interno/usuarios/operacion/` del dueño, con los campos actuales
  del formulario, sesión/Token originales y CSRF aplicable. Allí se
  ejecutan servicios compartidos de identidad más las reglas de dominio en una
  sola `transaction.atomic()`, validando actor, objeto y alcance nuevamente.
- La capacidad de guardar grupos o permisos sin Comedores se habilita sólo
  para cambios cuya independencia esté demostrada. Si hay efectos de dominio
  que no puedan comprobarse, bloquear ese guardado, no toda la administración.
- No reintentar automáticamente mutaciones después de un timeout. Si puede haber
  ocurrido el commit, consultar el estado; si tampoco se puede confirmar, informar
  resultado incierto. No anunciar rollback por una mera pérdida de respuesta.

### Dashboard y último valor válido

Nuevo GET propuesto: `/api/comedores/metricas-dashboard/`, con Session/Token
existentes y comprobación en el dueño de `dashboard.view_dashboard`, que controla
la visualización actual. Nunca autenticar por un ID declarado por el cliente.

Respuesta completa con las cinco claves que ya persiste el portal:

```json
{
  "cantidad_comedores_activos": 10,
  "cantidad_relevamientos_activos": 7,
  "presupuesto_desayuno": 100,
  "presupuesto_merienda": 100,
  "presupuesto_comida": 200
}
```

Los ejemplos no son datos reales. Reutilizar los cálculos existentes y la
normalización actual a los enteros de `Dashboard.cantidad`; no cambiar unidades
ni precisión del almacenamiento como parte de este corte.

- Al abrir el dashboard, usar el helper JSON existente y su timeout acotado.
  Sólo una respuesta completa, válida y autorizada actualiza las cinco claves
  dentro de una transacción. No borrar ni poner ceros ante timeout/503/403,
  payload parcial o inválido. No reemplazar otras claves del dashboard.
- El dueño de la tabla persistida y del admin sigue siendo el portal. Retirar
  los callbacks locales cuando su reemplazo esté conectado y probado; no dejar
  al dominio escribiendo en `dashboard` de otro servicio.
- Si hay datos guardados, mostrarlos con aviso de actualización fallida. Si nunca
  se guardó un resultado válido, mostrar ausencia de información, no un cero
  inventado. No prometer una fecha de actualización que el modelo no almacena.
- No persistir un resultado de alcance reducido como si fuera un agregado global.
  Conservar la semántica y permisos actuales de estos indicadores.
- CDF mantiene su contrato y fallback existentes en este corte; extenderle el
  último valor persistido sería un cambio secundario separado.

## Auditoría común: decisión material propuesta por separado

Recomendación: que la auditoría común de autenticación pertenezca a `audittrail`
del kernel; la auditoría de operaciones de Espacios se conserva en su dominio.
No se propone una nueva infraestructura, DB, copia de registros ni store paralelo.

Traslado propuesto de `pwa.AuditoriaSesionPWA` a
`audittrail.AuditoriaSesionPWA`, conservando la tabla
`pwa_auditoriasesionpwa`, sus filas, PKs, índices y relaciones a User:

1. Crear el estado destino y retirar el estado origen con
   `SeparateDatabaseAndState`, sin crear/borrar la tabla física.
2. Reasignar el ContentType conservando su PK y los IDs de Permission y sus
   asignaciones a usuarios/grupos. Si existen ambos ContentTypes, detenerse;
   no fusionarlos ni borrar automáticamente uno de ellos.
3. El cambio de app label cambia el prefijo de los cuatro códigos técnicos de
   auditoría `pwa.add_auditoriasesionpwa`, `pwa.change_auditoriasesionpwa`,
   `pwa.delete_auditoriasesionpwa` y `pwa.view_auditoriasesionpwa` a `audittrail`
   con los mismos codenames. **Esto requiere autorización expresa**:
   preservar asignaciones no equivale a conservar esas cadenas de permiso.
   Los permisos operativos `pwa.manage_*` no se trasladan.
4. Cambiar admin, persistidor y consumidores con compatibilidad de import donde
   corresponda. Resolver el grafo completo sin ciclos y probar instalación vacía,
   actualización con datos y reversa antes de incorporar.
5. La auditoría genérica no debe consultar contexto de Comedores como condición
   para registrar un evento. Los snapshots de contexto que no estén disponibles
   se distinguen en la observabilidad y no se inventan; acordar esa degradación
   antes de modificar el persistidor. No cambiar silenciosamente la política
   actual ante fallas de escritura de auditoría.

Si deben conservarse exactamente los cuatro códigos anteriores, no ejecutar
este traslado sin diseñar primero una compatibilidad que también cubra
`get_all_permissions()` y el admin. No usar dos modelos/escritores contra la misma
tabla ni SQL oculto para simular independencia.

## Orden y alcance de ejecución

1. Separar formularios/vistas de autenticación y Mi cuenta de los módulos que
   importan Espacios. Cuerpos, validaciones y URLs conservados; contratos de
   imports y probe de arranque del componente sin apps de negocio.
2. Implementar cálculo remoto de indicadores y conservación del último resultado
   completo en portal, con tests de éxito y fallas. Preservar composición local
   durante la transición; no afirmar independencia de proceso hasta C3.
3. Implementar contrato de elegibilidad/contexto y administración compuesta una
   vez aprobados los detalles materiales y auditado cada consumidor.
4. Traslado de auditoría sólo con autorización específica de estado/permisos.
5. Volver a C2/C3 para consumidores, runtime, imágenes, Compose y deploy selectivo.

Archivos principales: `usuarios/forms.py`, `views.py`, `urls.py`, `api_views.py`,
`api_serializers.py`, servicios de recupero/importación y sus tests; componentes
de identidad separados en esa app; `pwa` para las capacidades de Espacios;
`dashboard/{apps,signals,utils,views,models,admin}.py` y template;
`comedores/api.py`, `relevamientos/api.py` y URLconfs; `.importlinter`.
Sólo el corte de auditoría afectaría sus modelos/migraciones/admin compartidos.

## Validación, rollback y límites

- Tests de fallo de Comedores con login/logout/contraseña/Mi cuenta de los otros
  programas disponibles, y rechazo acotado para operaciones dependientes.
- Identidad, permisos y territorio se validan en cada dueño; cubrir requests
  manipulados, campos omitidos, grupos con efectos de dominio y usuarios mixtos.
- Una falla antes del commit no guarda usuario sin accesos; una respuesta
  perdida después del commit no provoca reintento ciego ni una falsa reversión.
- Dashboard conserva exactamente su último conjunto válido ante las distintas
  fallas; una respuesta parcial nunca mezcla indicadores de dos muestras.
- Migraciones de auditoría, si se autorizan: filas/IDs, CT/Permission PKs,
  asignaciones, códigos, instalación/upgrade/reversa y versiones cruzadas.
- Usar nuevamente pruebas focalizadas y Docker/MySQL aislados ya autorizados;
  no reutilizar datos ni entornos compartidos. Los tests de C0 no validan C1.
- Rollback de componentes sin esquema: código y contratos compatibles; del
  traslado de estado: revertir su estado/ContentType con prueba antes de volver
  a una imagen anterior. El rollback de imagen no revierte migraciones.
- La propuesta fue aprobada y su implementación local pasó 392 tests con
  Docker/MySQL sintéticos autorizados. Se preserva C0. #2641 continúa abierto.

Las razones de recomendación son del agente; los criterios y la aprobación del
responsable se registran arriba. La decisión aceptada está en
`docs/registro/decisiones/2026-10-15-identidad-y-espacios-comunitarios.md`.
Este documento conserva la propuesta que se aprobó; no es evidencia de deploy.
