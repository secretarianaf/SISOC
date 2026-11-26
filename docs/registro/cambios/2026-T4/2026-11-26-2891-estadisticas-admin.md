# Estadísticas bajo demanda en el admin (#2891)

## Alcance

El índice del admin abre la navegación y ofrece el botón **Ver estadísticas**. La pantalla independiente muestra las métricas del proceso y reutiliza los gráficos, los errores por sección y la caché existentes. Cada índice de aplicación conserva sus métricas.

## Comportamiento

El índice omite el cálculo y la carga automática de estadísticas. El acceso directo a la pantalla nueva usa el mismo control de acceso del admin. Con caché fría, abrir las estadísticas todavía puede demorar, ya que el cálculo se ejecuta en esa solicitud.

## Verificación

Pasaron 77 pruebas del dashboard, Unfold y los runtimes, incluidos el índice con caché fría sin cálculos, el acceso directo sin autorización, el aislamiento de errores y la reutilización de caché.

Medianas de cinco ejecuciones por escenario en SQLite aislada con 30 usuarios sintéticos, conexiones salientes bloqueadas y autenticación fuera de la medición. La comparación anterior usa la plantilla original y el callback que calculaba todas las métricas.

| Escenario | Total (ms) | SQL (consultas) | SQL (ms) | Lecturas de métricas por aplicación |
| --- | ---: | ---: | ---: | ---: |
| Índice anterior, caché fría | 95,19 | 76 | 0,91 | 58 |
| Índice anterior, caché caliente | 73,70 | 2 | 0,09 | 58 |
| Índice anterior, caché fría con métricas desactivadas durante la prueba | 47,59 | 2 | 0,13 | 0 |
| Índice nuevo, caché fría | 41,07 | 2 | 0,07 | 0 |
| Índice nuevo, caché caliente | 40,31 | 2 | 0,07 | 0 |
| Estadísticas, caché fría | 73,79 | 75 | 0,68 | 58 |
| Estadísticas, caché caliente | 65,28 | 1 | 0,06 | 58 |

Las lecturas con caché caliente fueron búsquedas en caché. En frío, los mayores tiempos de métricas por aplicación se registraron en Usuarios (1,15 ms), Celiaquía (0,80 ms), Audittrail (0,77 ms), Ciudadanos (0,73 ms) y VAT (0,71 ms) en el índice anterior. Los resultados son locales y no establecen la latencia ni la causa del incidente en producción.

En Chrome se verificó la navegación por teclado en ambas direcciones y el diseño en escritorio (1440 px) y móvil (390 px), usando las respuestas de Django con datos sintéticos. La revisión manual confirmó que los gráficos se ven en modo oscuro y que el botón Volver regresa al índice.
