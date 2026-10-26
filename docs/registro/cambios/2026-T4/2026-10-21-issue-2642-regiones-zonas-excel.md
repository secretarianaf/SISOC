# #2642: regiones y subzonas del Excel recibido

## Fuente y catálogo

Fuente: `REGIONES_Y_ZONAS.xlsx`, hoja `Hoja2`, columnas `REGION` y
`AGLOMERADO/SUBZONA`, recibido del usuario el 21/10/2026.
SHA-256: `2f2e1dcf1104ed7f23889b916608a183a9da77539bbc017698683562ffc54bbc`.
Se conservan los nombres y su escritura original. SAN JUAN está duplicado
dentro de la misma región en el Excel y se carga una sola vez.

| Región | Subzonas |
| --- | --- |
| AGBA | CABA NORTE y OTROS, NOROESTE, SUR ESTE, OESTE (LM) |
| CENTRO | CONCORDIA, CORDOBA, PARANA, ROSARIO, SANTA FE |
| CUYO PATAGONIA BAI | BARILOCHE, LA PLATA, MAR DEL PLATA, MENDOZA, SAN JUAN, NEUQUEN, RIO NEGRO, LA PAMPA, SAN LUIS |
| NEA | CORRIENTES, FORMOSA, MISIONES, CHACO |
| NOA | CATAMARCA, JUJUY, SALTA, SANTIAGO DEL ESTERO, TUCUMAN, LA RIOJA |

## Implementación y compatibilidad

- La migración `organizaciones.0026_issue_2642_regiones_zonas_excel` agrega la
  FK opcional Subzona–Región y carga cinco regiones y 28 subzonas activas.
  Usa modelos históricos y el alias de base del migrador. No depende del
  archivo en Downloads durante el despliegue.
- Las opciones provisorias Región 1/2 y Zona 1/2 de la primera iteración no
  llegaron a desplegarse; se retiró su migración y la 0026 depende de la 0024.
- En alta/edición de Organización, Subzona depende de Región tanto en el
  selector JavaScript como en la validación de Django. Cambiar Región descarta
  una subzona incompatible. Ambos campos siguen siendo opcionales; seleccionar
  una subzona del catálogo definitivo requiere su región.
- La selección vigente inactiva se mantiene solo para su organización. No se
  ofrece para nuevas asignaciones. Los filtros mantienen los valores históricos
  para poder encontrar organizaciones/rendiciones pendientes de reasignación.
- Se actualiza la clave de caché de filtros de Organizaciones para que el
  despliegue no conserve temporalmente el catálogo anterior.

## Despliegue y reversa

Aplicar la migración 0026 en el migrador y publicar el backend Comedores con
sus estáticos habituales. No requiere cambios en Mobile. Los catálogos y su
relación pertenecen a `organizaciones` (kernel), sin imports a Comedores.

La reversa de datos es intencionalmente no destructiva: no elimina opciones
ya utilizadas. Revertir el esquema retira la FK Subzona–Región, por lo que debe
coordinarse con la vuelta del formulario anterior y respaldar esa relación.
No se aplicaron migraciones a la base local ni se hizo deploy.

## Validación

- 61 tests aprobados: catálogo, idempotencia, preservación de asignaciones
  con opciones inactivas, validación de combinaciones Región/Subzona y
  regresiones cercanas.
  El test de concurrencia MySQL se omite en esta ejecución SQLite.
- 60 tests aprobados en MySQL temporal, incluidas las migraciones del catálogo
  y concurrencia. Los tests de carga admiten una base vacía o ya inicializada
  por las migraciones y conservan las verificaciones de idempotencia y asignaciones.
- Chrome: cinco regiones, filtrado de subzonas, limpieza de una selección
  incompatible al cambiar región y presentación móvil verificados con datos
  ficticios y los mismos valores del Excel.
- Black, Pylint (10/10), djlint, control de migraciones pendientes y rutas
  documentales aprobados.
