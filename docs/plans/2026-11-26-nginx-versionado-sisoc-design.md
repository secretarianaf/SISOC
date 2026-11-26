# Diseño: Nginx versionado y reconciliación por entorno

Estado: diseño aprobado; no habilita cambios en servidores ni despliegues.

## Objetivo y alcance

Versionar la configuración SISOC y verificarla antes de cada despliegue de QA, HML y producción, sin modificar otros sitios ni el Nginx global. La configuración de producción proporcionada es el contrato prioritario; QA es referencia y HML requiere incorporación con evidencia del entorno. Conservar TLS externo, rutas, límites, registros, PWA y protecciones existentes. Proteger los archivos privados de CDF e Inspecciones sin cerrar todo `/media/`.

## Confianza y activación

Infra instala por separado un helper root-owned de interfaz y destinos fijos. El runner no recibe capacidad para ejecutar scripts mutables como root ni para elegir destinos, includes, comandos o contenido arbitrario. Infra valida y registra fuera del control del runner un manifiesto root-owned, específico del entorno, que identifica los bytes exactos de cada archivo gestionado. Una aprobación corresponde al paquete Nginx, no a cada revisión de la aplicación. Si el paquete no cambia, se reutiliza en despliegues posteriores sin instalación ni reload.

Antes del onboarding el estado se informa como no gestionado, sin afirmar cobertura. Una vez activado, la ausencia de verificación efectiva, manifiesto inválido, paquete no aprobado o cualquier fallo detiene el despliegue antes de migraciones y cutover. La activación no es una excepción permanente. Un pipeline de firma aislado es una posible evolución, no una dependencia de esta entrega.

## Reconciliación y recuperación

El helper debe comprobar el paquete y el estado efectivo; si son iguales no escribe ni recarga. Ante diferencias autorizadas, toma backup, instala atómicamente solo archivos SISOC, valida `nginx -t`, recarga y comprueba evidencia efectiva y smoke. Un fallo restaura la configuración previa y falla el despliegue. La reversión posterior de la aplicación no debe retirar una protección Nginx ya efectiva. La restauración fallida se informa explícitamente; no se declara éxito.

## Evidencia y límites

Las pruebas usan Docker y fixtures sintéticos: igualdad, actualización, permisos y errores, rollback, alcance, preservación de producción, PWA y respuestas privadas 404 junto a públicas 200. También cubren dos revisiones de aplicación con el mismo paquete aprobado y el rechazo de contenido manipulado. No se infiere la topología de HML ni se prueba ni modifica ningún host real. La preparación y activación requieren revisión y ejecución posterior por Infra.
