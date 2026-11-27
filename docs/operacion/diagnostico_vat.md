# Diagnóstico de bloqueos de VAT

## Registros del backend

- `vat_request` registra el método HTTP, el patrón de URL declarado en Django, el estado de respuesta, duración hasta que Django construye la respuesta y PID. Cada registro tiene un ID generado por VAT. Si Django no llega a resolver la URL, se registra `sin_resolver`. Las descargas con streaming pueden seguir enviando datos después del registro.
- Si Gunicorn envía SIGABRT, `vat_worker_abort` registra el PID, el ID y el patrón de la petición activa si estaba en Django. Debajo aparece la traza del hilo sin valores de variables. Si el worker está bloqueado en código nativo o ya recibió SIGKILL, la traza puede faltar.
- Cruzá los eventos del proxy y de VAT por hora, método y patrón de ruta. Dentro de VAT, usá el PID y el ID local para distinguir peticiones. La duración del proxy puede terminar antes de que Gunicorn interrumpa el worker. Un 504 del proxy puede corresponder a una petición que sigue en ejecución en VAT.
- Los eventos normales usan el log INFO diario existente. Los abortos y las trazas van al canal de Gunicorn visible con `docker logs`. La rotación de archivos diarios y la retención del driver de Docker siguen la operación existente del entorno. El costo añadido es un registro INFO por petición y una traza solamente en el aborto. El registro normal no consulta MySQL.

## Captura acotada durante el próximo episodio

Desde el host de aplicación, con el acceso de operación habitual, seleccioná el contenedor de VAT del Compose del entorno. Ejecutá el bloque una vez durante la demora y otra después de recuperarse para comparar los contadores acumulados. Estados por host y contenedor se consultan por separado. Ante falta de permisos o timeout, guardá la indicación y seguí con el resto de la captura.

```sh
# Ejecutar en el directorio del Compose del entorno y cargar su configuración habitual.
VAT_CONTENEDOR="$(docker compose -f docker/compose/docker-compose.deploy.yml ps -q backend_vat)"
if [ -z "$VAT_CONTENEDOR" ]; then
    printf '%s\n' 'VAT no encontrado en este Compose'
else
    date -Is
    uptime
    free -m
    timeout 6s docker stats --no-stream \
        --format '{{.Name}} CPU={{.CPUPerc}} Mem={{.MemUsage}} PIDs={{.PIDs}}' \
        "$VAT_CONTENEDOR" || printf '%s\n' 'Estadísticas del contenedor no disponibles'
    timeout 6s docker top "$VAT_CONTENEDOR" -eo pid,ppid,pcpu,pmem,stat,comm \
        | head -n 26
    timeout 6s docker logs --since 5m --tail 200 "$VAT_CONTENEDOR" 2>&1 \
        | grep -E 'WORKER TIMEOUT|vat_worker_abort' | tail -n 30
    timeout -k 1s 12s docker exec -i "$VAT_CONTENEDOR" \
        timeout -k 1s 8s python manage.py shell <<'PY'
from django.db import Error, connection

consultas = (
    ("estado", """
        SHOW GLOBAL STATUS WHERE Variable_name IN (
            'Threads_connected', 'Threads_running', 'Max_used_connections',
            'Innodb_row_lock_current_waits', 'Innodb_row_lock_waits'
        )
    """),
    ("esperas", """
        SELECT EVENT_NAME, COUNT_STAR, SUM_TIMER_WAIT
        FROM performance_schema.events_waits_summary_global_by_event_name
        WHERE EVENT_NAME LIKE 'wait/%' AND SUM_TIMER_WAIT > 0
        ORDER BY SUM_TIMER_WAIT DESC
        LIMIT 10
    """),
)
for etiqueta, consulta in consultas:
    try:
        with connection.cursor() as cursor:
            cursor.execute(consulta)
            print(etiqueta, cursor.fetchall())
    except Error as exc:
        print(etiqueta, "no disponible", type(exc).__name__)
PY
fi
```

El bloque usa la conexión MySQL configurada para VAT y solo pide contadores y nombres de instrumentos. Si Performance Schema está desactivado o el usuario carece de acceso, puede faltar esa parte de la captura. El límite de tiempo evita dejar esperando indefinidamente al operador. Las estadísticas de espera son globales y acumuladas, por lo que no identifican por sí solas la consulta que bloqueó el worker. Compartí solo estas salidas y los eventos del diagnóstico, sin copiar otros registros de solicitudes ni la configuración del entorno.

## Lectura de la captura

- Compará el horario del 504 con `WORKER TIMEOUT`, el PID y el patrón de ruta de `vat_worker_abort`. Revisá la traza que sigue a ese evento en el log de Gunicorn.
- Si suben los workers ocupados y `Threads_running` o los contadores de bloqueo de filas, usá el incremento de las esperas para orientar la investigación. Una traza en la llamada al driver indica dónde esperaba el worker, no qué consulta originó la contención.
- `WORKER TIMEOUT` y SIGKILL de Gunicorn no demuestran un OOM. Para confirmarlo, hace falta un evento del kernel del host correspondiente, con hora y PID.
