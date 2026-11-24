# Cambio: INET Asistencia y contacto opcional (#2895)

## Alcance

Perfil docente limitado al centro asignado mediante las relaciones de referentes existentes, siguiendo el alcance de CFP. Permiso `auth.role_inet_asistencia` y grupo `INET Asistencia`, con lectura de centros, cursos y comisiones y operaciones específicas de asistencia y resultados. No concede gestión de inscripciones.

Se agregan teléfono y mail opcionales al formulario de carga manual de ciudadanos. Se reutilizan los campos y validaciones del modelo existente.

Implementación principal en `src/backends/vat/VAT/services/access_scope.py`, `src/backends/vat/VAT/views/curso.py`, `src/backends/vat/VAT/forms.py` y `src/backends/vat/VAT/templates/vat/oferta_institucional/comision_detail.html`. La creación del grupo se agrega a la semilla del kernel y a `src/backends/kernel/users/migrations/0062_inet_asistencia.py`.

## Comportamiento

El docente ve Información, Clases y Resultados. Las pestañas y paneles administrativos no se renderizan. Las operaciones administrativas siguen protegidas en el servidor. La asignación del centro admite el grupo nuevo y no habilita lectura del panel de credenciales. Los roles combinados conservan sus capacidades previas.

Los datos de contacto son opcionales y se guardan en el ciudadano. Un mail inválido produce error de validación.

La validación del solicitante detectó estilos bloqueados por CSP en el entorno local. Se agregó el nonce existente a los estilos internos de centro, curso, comisión y asistencia, sin desactivar CSP. Se agregó una prueba de regresión que verifica los estilos renderizados en las cuatro pantallas.

**Requiere revisión técnica:** permisos y migración de datos del grupo. No incorpora modelos ni dependencias.

## Verificación

134 pruebas automáticas aprobadas en SQLite local: nuevos casos de permisos/centro/contacto/CSP y regresión de formularios, grupos, templates, centros y API INET. Black aprobó nueve archivos Python.

La comprobación del grafo de migraciones está bloqueada por una referencia existente a la migración faltante `pwa.0018_catalogoactividadpwa_manage_permission`. La creación idempotente del grupo se probó directamente. Pylint está bloqueado por rutas duplicadas de apps en Windows. Djlint fue interrumpido sin resultado tras varios minutos.

Verificación visual final, capturas, MySQL, CI y aceptación humana pendientes. La automatización de navegador no pudo determinar la URL activa. Se comprobó por HTTP que centro y comisión responden y entregan todos los bloques de estilo con nonce. El solicitante autorizó publicar el PR; se prepara en borrador con estos pendientes. Sin merge ni despliegue.
