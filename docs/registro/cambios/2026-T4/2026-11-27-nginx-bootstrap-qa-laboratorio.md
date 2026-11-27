# Cambio: bootstrap Nginx QA en laboratorio

## Alcance

Se agrega un modo root explícito de primera instalación para QA sin marcador previo. No activa el entorno ni se ejecutó en servidores. Rechaza estados ya gestionados y archivos con atributos extendidos.

## Comportamiento

Tras validar el manifiesto aprobado, guarda los dos archivos y sus metadatos admitidos, registra la ausencia del marcador, instala el sitio y verifica Nginx. QA selecciona un paquete PWA específico con los bytes CRLF observados durante una inspección anterior; debe cotejarse y aprobarse nuevamente antes de activarlo. Si el snippet PWA compartido no coincide exactamente con el aprobado, falla sin modificarlo. Ante errores intenta restaurar el sitio desde el backup y comprobar una respuesta HTTP estable; también se ofrece restauración root explícita para una interrupción. La comprobación de una respuesta no demuestra la identidad completa de la configuración cargada; tampoco se garantiza recuperación ante un corte abrupto o fallo de restauración. La ventana operacional sin deploy y la revisión de protecciones son precondiciones pendientes, no un lock probado.

## Verificación

En contenedor descartable con Nginx real se ejercitaron la primera instalación, los fallos de validación, reload y probe, y la restauración de archivos y respuesta sintética. `systemctl` fue simulado. No se usaron datos reales ni se verificó QA; se requiere revisión independiente antes de cualquier publicación o activación. El detalle operativo y sus límites están en [reconciliación de Nginx](../../../operacion/nginx/reconciliacion.md).
