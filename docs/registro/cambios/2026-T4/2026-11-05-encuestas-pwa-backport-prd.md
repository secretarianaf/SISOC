# API selectiva de encuestas para Espacios

## Alcance y motivo

Backport acotado desde development dfedc04f, sobre el main real posterior a #2877,
para compatibilidad del frontend Espacios be2197c5. No promueve todo #2878.
El usuario aprobó un PR coherente de aproximadamente 700 líneas y dos refreshes
secuenciales de backends en la ventana actual. Backup confirmado por el usuario,
no probado por el agente. No hay acceso DB/SSH ni contenido o activación operativa.

## Diseño y límites

El core mantiene modelos, API y respuestas; Comedores/PWA confirma acceso por el
helper HTTP interno existente. No hay imports Python entre dueños ni dependencias
nuevas. Disponible por opt-in, conserva publicación y segmentación existentes.
El bloqueo de ronda y cumplimiento único deduplican; UUID validado no es ledger.
Cambios compartidos mínimos: metadatos de versión/serialización, límites de texto y
visibilidad recursiva de preguntas. Se excluyen editor, UI de activación y worker.
La migración 0008 conserva los bytes publicados, sin migración de datos.

## Verificación

RED observado sobre main: GET y POST anónimos devolvían 404, esperado 401.
Primer candidato: 35 pruebas API pasaron; un test nuevo tenía configuración
incompleta de creación (duración/modalidad), corregida sin alterar lógica productiva.
Suite local completa: 324 pruebas aprobadas; makemigrations sin cambios; check de core aislado sin incidencias; Black 9 archivos convergentes; registro regenerado con exactamente dos entradas nuevas y ninguna retirada. Pylint sin errores funcionales: única advertencia C0103 por el nombre numérico de la migración publicada, conservado intencionalmente. Verificación independiente: 105 pruebas API/legacy/web y cuatro probes de hash de todas las tablas encuestas ante rechazos aprobados; diferencial de 61 pruebas legacy idéntico en baseline y candidato (solo duración normalizada). Registry regenerado idéntico y migración publicada idéntica al donor. Sin blockers reproducidos. CI MySQL, HTTP real entre servicios, deploy y navegador autenticado siguen pendientes.
SQLite local no demuestra bloqueos concurrentes MySQL ni operación productiva.
No se afirma aceptación humana ni prueba autenticada del navegador de Espacios.

## Operación y rollback

El registro compartido de URLs fuerza refresh completo. Preservar aprobación
humana de Environment production. Backend desplegado antes de promover Espacios.
No reejecutar el release diario con un tag existente que identifica otro baseline.
Rollback de código separado del esquema aditivo; no borrar columnas con datos.
La composición productiva carece de encuestas_worker: no se agrega ni se activa.

Risk: items 1,2,3,4,5 (schema, token/owner access, shared response behavior, round locking, deployment).
