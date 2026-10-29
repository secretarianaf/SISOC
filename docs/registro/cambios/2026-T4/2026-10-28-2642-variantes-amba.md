# Cambio: variantes AMBA en la línea programática (#2642)

## Alcance

`inferir_linea_programatica` en
`src/backends/comedores/rendicioncuentasmensual/services.py` reconoce el prefijo
AMBA en código o nombre del proyecto, en lugar de exigir coincidencia exacta.
Responde al comentario 6474668538 del issue 2642. Sigue el patrón de inferencia
centralizada existente; no agrega dependencias, permisos ni migraciones.

## Comportamiento

AMBA, AMBA111, AMBA 1111, AMBA123 y sufijos con guiones o guiones bajos usan
Secos. Se ignoran mayúsculas y espacios externos. XAMBA111 usa Tradicional.
La regla por prefijo también comprende nombres como AMBATO; se conversó ese
alcance con el usuario y se aceptó. La creación continúa ignorando la línea
contradictoria enviada por el cliente cuando se especifica proyecto.
No se modifican rendiciones históricas ni la inferencia sin proyecto.
Debe coordinarse con la corrección del contexto y fallbacks en la app móvil.

## Verificación

Regresiones del alta real parametrizadas en
`src/backends/comedores/tests/test_issue_2642.py`: verifican código, nombre,
normalización, sufijos y caso negativo. Pruebas en SQLite aislado, Black y
Pylint del servicio. El caso concurrente del módulo requiere MySQL y se omite
en SQLite. Validación local de la app con backend real y proyectos ficticios.
No se ejecutó despliegue ni modificación en HML o producción.
