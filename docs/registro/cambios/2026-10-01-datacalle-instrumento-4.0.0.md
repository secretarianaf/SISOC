# Cambio: instrumento DataCalle 4.0.0 (formulario FINAL en papel)

## Alcance

El área sustantiva entregó el formulario definitivo en papel y DATACALLE
reemplazó **el instrumento entero**: 19 claves nuevas, 27 que dejan de
preguntarse, cero renombres, y la matriz etaria de 5 a 7 franjas con códigos
nuevos. SISOC toma la 4.0.0 y adapta lo poco que dependía del instrumento.

La copia local de SISOC estaba en **2.2.0**, no en 3.1.0: las versiones 2.3.0,
3.0.0 y 3.1.0 se publicaron pero nunca se sincronizaron. Así que este cambio es
un salto 2.2.0 → 4.0.0 y, de paso, destapa que
`GET /api/datacalle/catalogos/` venía sirviendo un instrumento de hace cuatro
versiones.

## Comportamiento

- **`GET /api/datacalle/catalogos/` devuelve `"version": "4.0.0"`** con los
  catálogos nuevos (`programaSocialPropio`, `programaSocialHijos`) y las 7
  franjas etarias del papel. El shape acordado (`{version, catalogos,
  cuestionario}`) no cambia.
- **Un caso 4.0.0 se guarda y se lee completo.** Las 19 claves que nacen
  (`tieneDocumento`, `cantidadHijos`, `conQuienesVive`, `desdeCuandoCalle`,
  `motivosCalle`, …) resuelven etiqueta de pregunta y de catálogo.
- **Un caso ya guardado con el instrumento anterior se lee igual**, con sus
  franjas retiradas (`r19a59`, `r0a14`) y sus preguntas retiradas
  (`tiempoEnCalle`, `motivoPrincipalCalle`, el set del Grupo de Washington).
  La ficha ahora las marca **"pregunta retirada"**, para que la ausencia del
  dato en un caso nuevo no se lea como dato faltante.
- **La matriz etaria deja de verse en crudo.** El listado de casos mostraba
  `r19a59_varon#1`; ahora muestra "Entre 19 y 59 años · Varón (persona 1)", y el
  conteo del grupo observado deja de volcarse como JSON.
- **La observación del asentamiento del cierre en campo** se muestra con la
  etiqueta del catálogo en lugar del código.
- **El contador "Menores" pasa a "Sin entrevista por edad"** y el chip del
  listado, de "Menor de edad" a "Sin entrevista (edad)".

## Decisiones

### Quién no se entrevista ya no lo decide `esMenorDeEdad`

Hasta la 3.1.0, SISOC contaba a quien no correspondía entrevistar como
`esMenorDeEdad = si` sin `realizaEntrevista`. Desde la 4.0.0 eso está mal: no
hay más formulario abreviado, así que **una persona de 16 años sí se entrevista
y una de 13 no**. El contrato lo dice en el propio campo (*"Desde 4.0.0 NO
decide nada"*) y publica la regla correcta en `estados.rechazada`:
`personaEntrevistada` con prefijo en `r0a5` / `r6a13` / `r0a13` / `r0a14`.

Además es un dato más confiable: a quien no se entrevista no se le pregunta la
fecha de nacimiento, que es de donde salía el cálculo de `esMenorDeEdad`.

**La lista de prefijos se lee del cuestionario, no se hardcodea.** Así la
próxima sincronización la actualiza sola, y además DATACALLE ya dejó en ella los
prefijos de las versiones anteriores a propósito: la misma regla cuenta bien las
dos generaciones de casos que conviven en la base. Se conserva la condición
vieja en OR para los casos 3.1.0 cargados bajo la regla F1 que no dejan la
franja en un prefijo de la lista.

### No se mapea nada entre versiones

El contrato lo prohíbe explícitamente y SISOC lo respeta:

- `r19a59` **no** es `r18a29 + r30a45 + r46a64`: los cortes no coinciden y nadie
  puede repartir ese conteo sin inventarlo.
- `tiempoEnCalle` y `desdeCuandoCalle` son dos escalas sin equivalencia; lo
  mismo `motivoPrincipalCalle` (única) y `motivosCalle` (múltiple).
- `asisteComedor.todosLosDias` y `todosLosDiasExactos` son preguntas distintas.

Por eso son claves distintas y se guardan separadas. Cuando se construyan los
tableros (N13), ahí hay una decisión de negocio pendiente: ver §Pendientes.

### Las preguntas retiradas se muestran, no se ocultan

Las 27 `soloHistorico` se siguen leyendo y mostrando con su etiqueta. Ocultarlas
sería perder la lectura del histórico, que es justo lo que el contrato pide
conservar al no borrar ninguna clave.

### El diccionario de respuestas entra como segunda fuente de etiquetas

`_campos_por_id()` ahora combina `cuestionario.json` con
`diccionario-respuestas.json`. Si una clave guardada no aparece en las páginas
del cuestionario local, igual se resuelve su etiqueta, su catálogo y su marca
`soloHistorico`. Es el seguro contra la próxima desincronización.

## Compatibilidad

- **No hay migraciones.** El instrumento vive en un `JSONField` sin schema y las
  9 columnas indexadas copian claves que no cambiaron de nombre.
- **La app 3.1.0 contra este backend sigue funcionando**: `validate_respuestas`
  sólo exige que `respuestas` sea un objeto, y la variante `"adolescente"` se
  acepta igual (`variante` es texto libre).
- **La app 4.0.0 contra el backend viejo también funciona**, por lo mismo: lo
  único que ve distinto es la versión del endpoint de catálogos, y la app usa su
  copia embebida como respaldo.

## Pendientes de decisión del área

- **Permanencia en calle y motivo principal**: las series se cortan. Hoy no hay
  tablero que las use; cuando lo haya, hay que decidir con el área si se
  muestran dos series separadas o se define un mapeo a mano.
- **País emisor del documento extranjero**: se pierde la serie de migración que
  había pedido QA-0043 (8.4 del aviso).
- **`cualDiscapacidad` es texto libre con dato de salud.** Queda en `respuestas`
  —ya excluido del log de auditoría— pero se muestra en la ficha del caso a
  cualquiera con `datacalle.view_encuesta`.
- **Los 13 años** (8.2b del aviso): el papel dice "menores de 13" pero su franja
  observacional es "6 a 13". Con la implementación actual, una persona de 13 no
  se entrevista. Si el área cambia de criterio, cambia la app, no el backoffice.

## Hallazgo incidental corregido

`relevamiento_detail.html` tenía, dentro de `{% block title %}`, una copia
entera de la tabla "Casos relevados" que ya estaba en `{% block content %}`:
todo ese HTML se renderizaba dentro de `<title>`. Pre-existente y sin relación
con la 4.0.0, pero la tabla cambia en este PR y dejar dos copias divergentes
habría sido peor.
