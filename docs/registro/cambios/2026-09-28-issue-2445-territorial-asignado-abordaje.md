# #2445: Territorial Asignado Abordaje Comunitario (legajo y filtro de rendiciones)

## Legajo de Organización

`Organizacion` suma el campo `territoriales_abordaje_comunitario` (M2M a
usuarios, opcional), editable desde el alta y la edición del legajo con un
selector múltiple con búsqueda. Cada opción se muestra como
`Apellido, Nombre (username)`. Los asignados se ven en el cuadro
"Información de la Organización", debajo de "Códigos de Proyecto".

Las opciones son los usuarios **activos** cuyo `Profile.rol` es
`TERRITORIAL PNUD` o `RESPONSABLE TERRITORIAL PNUD` (sin distinguir
mayúsculas). La regla vive en `users/services_territoriales.py` y la usan el
legajo y el filtro de rendiciones.

Al editar, un territorial ya asignado que perdió el rol sigue apareciendo como
opción, para que guardar el legajo no lo quite sin que nadie lo haya pedido.

## Listado de Rendiciones

- Filtro nuevo **Territorial asignado**. Varias filas del filtro se combinan con
  OR (devuelve las rendiciones de cualquiera de los territoriales elegidos) y con
  AND respecto de los demás campos, como el resto de los filtros. Se puede
  guardar como favorito.
- Columna **Territorial asignado** disponible en la configuración de columnas y
  en la exportación CSV. No está activa por defecto: el issue pide que esté
  disponible, y activarla para todos cambiaría la grilla de quienes no la usan.

La organización de una rendición es la de su proyecto; si no tiene proyecto
(rendiciones históricas), la de su comedor. El filtro y la columna usan la misma
regla. El filtro se resuelve por ids de organización, con una subconsulta sobre
la tabla intermedia, para usar los índices de las FK y no duplicar filas.

### Opciones del filtro

Las opciones son los territoriales elegibles (misma regla que el legajo) **más**
los usuarios que siguen asignados a alguna organización activa aunque hayan
perdido el rol o estén inactivos. La columna los muestra mientras sigan
asignados; si no estuvieran entre las opciones, sus rendiciones no se podrían
filtrar. Las asignaciones a organizaciones dadas de baja no se consideran.

Las opciones se calculan en cada request, fuera de la caché de 15 minutos de la
configuración, para que un territorial nuevo aparezca enseguida.

## Dependencia con #2444

El #2444 carga el `Profile.rol` de los usuarios territoriales. Esta
funcionalidad no depende de su código, pero hasta que esos datos estén cargados
en el ambiente, el selector no ofrece opciones.

## Despliegue

Aplicar `organizaciones.0022_issue_2445_territoriales_abordaje_comunitario`
(solo crea la tabla intermedia; no modifica datos existentes).
