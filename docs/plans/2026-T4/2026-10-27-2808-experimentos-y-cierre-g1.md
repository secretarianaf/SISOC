# G1: definición de experimentos y condiciones de habilitación

Estado **E2**. Complementa el [protocolo propuesto](2026-10-27-2808-protocolo-g1.md)
y la elección G1, que no se reabre. No autoriza entorno, claves, red, DB ni tests.
Especificar un experimento no significa que se ejecutó ni que su resultado pasó.

## Qué se puede cerrar en planificación

Core evalúa requisitos, firma request interno concreto; runtime autentica sesión,
verifica constancia y mantiene permisos/objeto/CSRF. Rechazo implica cero llamadas
al negocio. Constancia nunca sale al navegador ni a logs. No callback al core,
anti-replay/exactly-once, cache de autorización ni servicio de claves nuevos.
Namespace/header/campos son propuesta revisable del protocolo, no API publicada.

## Lo que necesita evidencia del entorno objetivo

| Experimento futuro | Preparación/medición concreta | Criterio de salida y acción ante fallo |
|---|---|---|
| G1-E01 target real | Core y runtime aislados con versiones objetivo. Registrar solo comparación sintética prepared path_url frente a target recibido por servidor, sin cookies/payload personal. Probar `%2F`, `%25`, `%7e`, `+`, `%20`, Unicode, duplicados, vacíos, prefijos y rewrite | Una fuente cruda confiable documentada, sin header del cliente. Si no hay correspondencia inequívoca, no habilitar; reconsiderar representación antes de código de negocio |
| G1-E02 reloj/cola | Medir desvío de relojes, espera antes de verificación y duración de transporte con concurrencia representativa acordada; distinguir cola de tiempo de ejecución | Proponer antigüedad máxima y tolerancia futura a partir de medidas y margen explicado. No elegir un número por intuición ni ampliar indefinidamente para pasar carga |
| G1-E03 límites | Medir tamaño de header firmado y target máximo para casos legítimos sintéticos; cotejar límites de cada salto HTTP y servidor | Límite explícito previo a parseo/firma, exceso rechazado sin negocio; si la URL legítima no cabe, redefinir contrato antes de activar |
| G1-E04 sesión/CSRF | Sesión inicial, rotada y persistida en core; cookie efectivamente reenviada, autenticación destino, HEAD/multipart y CSRF válido/inválido | Sub/binding corresponden a sesión autenticada; cookie vieja no sirve a firma nueva; CSRF inválido nunca muta. Nada de secretos en evidencia |
| G1-E05 rotación | Probar emisor/verificador versión vieja/nueva, despliegue parcial, rollback y retiro de fallback dentro de la política revisada | Envolvente y binding usan la misma política. No habilitar si acepta firma antigua pero binding falla, ni aceptar request sin firma para compatibilidad |
| G1-E06 fallos | Alterar por separado versión/audiencia/usuario/sesión/método/target/tiempo/firma; caída upstream antes/después de envío; request directo y header del cliente | Rechazo previo a negocio; core sustituye header. Mutación con respuesta perdida conserva incertidumbre y no replay automático. Acceso directo no salta gate |
| G1-E07 regresiones | APIs PWA/SIIS/token/API key actuales, PAS P1 anónimo/con sesión restringida, monolito, admin excluido | Sin cambio de autenticación de consumidores previos; no usar passing mocks nuevos como prueba de compatibilidad real |

Todos: estado **no ejecutado**, resultados/entorno/SHA pendientes. La versión local
de librerías observada en el protocolo no reemplaza versiones objetivo del repo.
Usar mecanismos existentes de tests y despliegue; no crear harness/servicio nuevo
por esta tabla. Capturas de bloqueos/remediaciones se vinculan al manifiesto UI.

## Orden y aprobación concreta

1. Revisión técnica de estructura/canonicalización/firma y amenazas con fuentes.
2. En fase futura autorizada, ejecutar E01–E04 y definir parámetros medidos.
3. Presentar política de clave/fallback/retirada y efectos de despliegue parcial;
   elección de G1 no la aprueba por omisión. No acceder ni rotar claves ahora.
4. Ejecutar E05–E07, contrastar compatibilidad y preparar evidencia por ruta.
5. Solo después de revisión y aceptación, habilitar circuito remoto autorizado.

Insumos local no depende de activar G1 remoto. Otros circuitos pueden avanzar en
contratos/React mientras se define, pero sus nuevas APIs web remotas no se abren
sin verificador y emisor compatibles. Desactivar entrada vuelve a una versión
autorizada; no desactivar firma ni protección para hacer funcionar un fallback.

## Pendientes honestos

No cerrar #2808 ni afirmar que el protocolo está listo para producción: faltan
revisión técnica y resultados. La planificación sí deja especificado qué medir,
qué resultado bloquea y qué decisión futura corresponde. No solicitar ahora
elegir valores operativos sin la evidencia que debe justificarlos.
