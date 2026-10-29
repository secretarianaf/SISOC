# Cambio: variantes AMBA para homologación (#2642)

## Alcance

Adaptación acotada desde origin/homologacion del arreglo AMBA preparado en el
PR #2816 para development. Homologación todavía no tenía la inferencia por
proyecto de aquel desarrollo: se incluye la parte mínima en el servicio y API.
No se integra development completo ni cambios de auditoría, permisos o esquemas.

## Comportamiento

El código o nombre que comienza con AMBA usa Secos, ignorando mayúsculas y
espacios externos. AMBA111, AMBA123, AMBA 1111, AMBA-123 y AMBA_123 califican;
XAMBA111 usa Tradicional. La regla por prefijo incluye cualquier sufijo,
alcance aceptado por el usuario. Sin proyecto se conserva la regla anterior.
La API informa la línea en el catálogo y la deriva del proyecto al validar y
crear; una línea contradictoria del cliente no reemplaza esa decisión.
Las rendiciones históricas no se recalculan. Se coordina con el PR de la app
sobre homologacion; los PR de development se mantienen para la otra rama.

## Verificación

Regresiones de alta y API en test_issue_2642_amba.py, incluidas validación sin
persistir y catálogo de proyectos. Suite de dominio y API PWA ejecutadas en
SQLite aislado; Black, Pylint y build/tests de la app. CI debe validar la rama
de homologación independientemente de los checks previos de development.
No se mergeó ni desplegó a ningún servidor.
