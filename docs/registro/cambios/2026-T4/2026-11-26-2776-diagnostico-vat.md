# Diagnóstico de bloqueos de VAT (#2776)

## Alcance

El runtime de VAT registra estado, duración, método, patrón de ruta y PID con un ID generado por el servidor. Cuando Gunicorn interrumpe un worker, registra el contexto disponible y vuelca una traza del hilo sin variables locales. Para ese aborto se omite la URI del mensaje automático de Gunicorn.

## Comportamiento

El middleware se activa solo en VAT. Reutiliza el log INFO diario y no agrega consultas a MySQL. La configuración de Gunicorn de VAT conserva workers y timeout. El [procedimiento de diagnóstico](../../../operacion/diagnostico_vat.md) acota la captura de CPU, memoria, procesos y contadores MySQL al próximo incidente.

## Verificación

Una simulación con Gunicorn 23 y un worker sync reprodujo un timeout fuera de producción. La traza mostró la función bloqueada, la ruta quedó parametrizada, el log omitió los valores de la ruta y la consulta, y Gunicorn arrancó otro worker que volvió a responder. Las pruebas cubren el registro de peticiones, el contexto de aborto y su limpieza.

Pasaron 692 pruebas de VAT y el chequeo del runtime aislado. Se validaron la sintaxis del procedimiento y las lecturas de contadores en el MySQL local.
