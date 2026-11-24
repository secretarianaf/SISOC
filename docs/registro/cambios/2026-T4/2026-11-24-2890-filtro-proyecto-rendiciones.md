# Cambio: código de Proyecto en el listado global de rendiciones (#2890)

## Alcance

El listado global usaba el código del comedor incluso cuando la rendición tenía otro proyecto asignado. El cambio afecta el filtro avanzado Proyecto, la columna Proyecto y su exportación CSV. No modifica datos, permisos, paginación, operadores ni encabezados.

## Comportamiento

La vista calcula el código una vez en el queryset, con la misma prioridad que Auditoría: si la rendición tiene proyecto, usa el código de ese proyecto. Si no tiene proyecto, usa el código del comedor. El filtro, la grilla y el CSV leen ese resultado.

## Verificación

La prueba de regresión del listado autenticado reprodujo el problema antes del cambio: una rendición con un proyecto distinto entraba en el resultado del código del comedor. Después del cambio pasaron la regresión y las suites de vistas de rendiciones y del filtro Territorial (#2445), con SQLite en memoria dentro de Docker y datos sintéticos. La prueba comprueba los códigos de grilla y CSV para proyectos explícitos y para el caso legado.

No se verificó en un navegador interactivo ni en producción. La prueba HTTP de Django no sustituye esa validación.
