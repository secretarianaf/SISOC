# Identidad disponible y operaciones de Espacios comunitarios

Estado: decisión aprobada por el responsable el 2026-10-15; implementación local
C1 validada con 392 pruebas focalizadas. No es aprobación de merge ni deploy. Issue #2641; #2725 queda
postergado.

## Contexto y aprobación

El responsable pidió conservar login/logout, cambio/recupero de contraseña,
datos propios y toda operación independiente posible si Comedores falla. Pidió
bloquear las operaciones que no puedan completarse y conservar los últimos
indicadores disponibles. Aprobó los contratos propuestos y el traslado de
la auditoría: «apruebo y prefiero no dejar pendiente».

Las razones técnicas y alternativas siguientes son la recomendación del agente
aceptada por el responsable; no se atribuye al responsable una explicación
retrospectiva que no dio. La hipótesis inicial fue ofrecida y declinada. La
revisión se delegó al agente y se pidió omitir el ejercicio de modos de falla;
la comprensión humana y la aceptación funcional todavía no están verificadas.

## Decisión

- Identidad, contraseñas, sesión/Token y alcances compartidos siguen en kernel;
  el portal conserva sus pantallas y URLs públicas. No consulta Comedores como
  condición de éxito para autenticar otros programas habilitados.
- Comedores es dueño de elegibilidad/contexto de Espacios y de las operaciones
  compuestas que alteran sus accesos, duplas o invariantes. La operación completa
  usa una única transacción con los servicios comunes de identidad.
- Se reutilizan sesión/Token, CSRF y permisos existentes. El dueño autentica y
  comprueba permisos y alcance. Ningún header con un ID es prueba de identidad.
- El portal clasifica los campos y efectos reales de grupos/permisos. No confía
  en un flag oculto del navegador. Campos omitidos conservan asignaciones.
  Un cambio cuya independencia no se puede probar requiere al dueño; no bloquea
  el resto del administrador. Las escrituras genéricas conservan cambios ajenos
  hechos después de validar y vuelven a comprobar los efectos antes de guardar.
- Login exclusivo de Espacios revalida credenciales en el dueño antes de emitir
  el Token existente. Puede verificar la contraseña dos veces. Indisponibilidad
  de elegibilidad devuelve 503; no emite Token ni afirma ausencia de habilitación.
- `/api/users/me/` mantiene identidad, permisos y territorio del kernel; agrega
  `espacios_comunitarios_disponible`. Un contexto no disponible usa defaults
  conservadores, nunca como autorización. Se conserva el destino de recupero
  para Espacios exclusivo; cuentas mixtas u otros programas usan el enlace web
  central, con usuario+email, rate limit y respuesta antienumeración existentes.
  La confirmación central revoca el Token anterior en la misma transacción que
  la contraseña y los flags del perfil.
- Los contratos internos usan la red del dueño y timeout acotado. Para desarrollo
  compuesto se registran adaptadores locales del mismo dueño, como los registros
  de contribuciones existentes; no se instala código de otro servicio en la
  imagen del consumidor. No se añade infraestructura ni autenticación nueva.
- Dashboard sigue siendo dueño de su tabla y admin. Comedores calcula y autoriza
  el agregado global. Sólo cinco enteros completos y válidos reemplazan una
  muestra en una transacción. Fallas conservan la muestra anterior y muestran
  un aviso. Sin muestra se informa ausencia; no se inventan ceros ni fecha.
  Se retiran callbacks que escribían en el portal desde el dominio. CDF conserva
  su contrato actual.
- `AuditoriaSesionPWA` pertenece a `audittrail`. Conserva tabla física
  `pwa_auditoriasesionpwa`, filas, PKs, índices, FKs y PK del ContentType;
  conserva IDs de Permission y asignaciones. Cambian sólo los cuatro prefijos
  técnicos de permisos de ese modelo de `pwa` a `audittrail`, expresamente
  aprobados. `pwa.manage_*` sigue perteneciendo a Espacios.
- El traslado usa estado de migraciones y reasignación del ContentType, sin
  DDL de esa tabla ni duplicación de datos. Dos ContentTypes existentes provocan
  un error explícito; no se fusionan ni borran automáticamente. La escritura de
  auditoría conserva su política previa: registra errores sin interrumpir la
  autenticación; un snapshot de negocio no condiciona el evento común.
  El admin usa el nuevo app label: GETs legacy redirigen y POSTs viejos se
  rechazan con 405, sin repetir acciones contra otra URL.
- DB, almacenamiento y migrador siguen compartidos. Se preserva el proxy actual.
  La independencia de imagen/proceso y selección de deploy se verifica en C3;
  pasar C1 no demuestra un despliegue independiente.

## Alternativas y consecuencias

Poner toda autenticación y administración en Comedores mantiene más código
junto, pero una caída bloquearía programas ajenos. Separar los pasos de una
misma mutación entre procesos exigiría aceptar resultados parciales; se
conserva la transacción única. No se recomienda un gateway nuevo para resolver
estas dependencias de negocio.

El costo es un contrato interno explícito, una consulta adicional de contexto y
la doble validación del camino exclusivo de Espacios. Una falla de la DB
compartida sigue afectando a todos. Algunas mutaciones ambiguas de grupos,
roles o programas se bloquean si el dueño no está disponible. Ante timeout de
POST no hay reintento automático: se informa resultado incierto, porque el
commit puede haber ocurrido.

## Validación y rollback

La evidencia ejecutada se incorpora al registro del corte, sin confundir
regresión, CI, merge, deploy ni aceptación humana. La instalación vacía,
upgrade con filas/permisos/asignaciones y reversa se prueban sólo en MySQL
sintético aislado autorizado. No se ejecutan migraciones en entornos compartidos.
Registro: `docs/registro/cambios/2026-T4/2026-10-15-issue-2641-c1-identidad-y-disponibilidad.md`.

El rollback del código no revierte el ContentType ni los códigos de permiso.
Antes de volver a una imagen anterior debe coordinarse la reversa de estado y
ContentType con el migrador completo, evitando versiones que exijan prefijos de
permiso distintos al mismo tiempo. La tabla y registros permanecen intactos.
Un conflicto de ContentTypes requiere revisión explícita antes de continuar.

Revisar la decisión si cambia la disponibilidad requerida, se propone una DB
independiente (#2725), se requiere otra política de auditoría o se necesitan
contratos de autenticación/infraestructura distintos. Ninguno queda autorizado
por esta decisión.
