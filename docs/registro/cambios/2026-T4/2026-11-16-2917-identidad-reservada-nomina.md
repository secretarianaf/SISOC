# Personas con identidad reservada en Datos del Convenio (#2917)

## Alcance

Aplica a comedores de `Abordaje Comunitario - Línea Secos` y
`Abordaje Comunitario - Línea Tradicional`.

En Datos del Convenio (`/comedores/<pk>/convenio-pnud/`), sección
"Prestaciones y Personas", se agrega el campo numérico
**Cantidad de personas con identidad reservada**. Sin completar vale 0.

## Comportamiento

- Las personas con identidad reservada asisten al espacio pero no figuran en
  la nómina. Ocupan lugar dentro de las personas conveniadas: el máximo de
  personas con prestación alimentaria en la nómina pasa a ser
  `Personas Conveniadas - Cantidad de personas con identidad reservada`
  (nunca menor que 0). Vale para el alta desde SISOC web y desde la PWA, que
  ya compartían el tope (#2844).
- El valor no puede superar a Personas Conveniadas; el formulario lo rechaza.
- Sin Personas Conveniadas cargadas sigue sin haber tope.
- El dato se muestra en el legajo del comedor: en el cuadro "Datos del
  Convenio" y en el apartado "Nómina", junto a los demás contadores.
- En el resto de los programas el campo no se carga ni se muestra, y el tope
  no cambia.

## Implementación

- Modelo `ComedorDatosConvenioPnud.personas_identidad_reservada`
  (`src/backends/comedores/comedores/models.py`) y migración
  `0064_comedordatosconveniopnud_personas_identidad_reservada`: agrega una
  columna con default 0, sin tocar datos existentes.
- `0065_merge_alcance_programa_identidad_reservada` une las dos migraciones
  `0064` de Comedores sin operaciones. En MySQL aislado, la ida y la reversa
  al estado previo conservaron filas existentes y la tabla de alcance por
  programa; la nueva columna queda en 0 al aplicar el cambio.
- Formulario y validación: `src/backends/comedores/comedores/forms/convenio_pnud_form.py`.
- Tope de nómina: `_get_tope_nomina_alimentaria` en
  `src/backends/comedores/pwa/services/nomina_service.py`.
- Tests: `src/backends/comedores/tests/test_issue_2917_identidad_reservada.py`.

## Pantallas React (2026-11-27)

El cambio original solo tocó los templates Django. Las pantallas equivalentes
de React (frontend v2) no mostraban el dato, por eso en el entorno de prueba
el campo no aparecía ni en Datos del Convenio ni en la ficha. Se completó:

- Formulario de Datos del Convenio
  (`src/frontends/apps/sisoc/src/routes/comedorConvenio.tsx`): muestra el
  campo y su aclaración debajo de Personas Conveniadas. La API ya lo enviaba.
- Ficha, cuadro "Datos del Convenio"
  (`src/backends/comedores/comedores/web_api_comedor_ficha_tablero.py`): fila
  nueva después de Personas conveniadas.
- Ficha, tarjeta "Nómina"
  (`src/backends/comedores/comedores/web_api_comedor_ficha_relaciones.py` y
  `src/frontends/apps/sisoc/src/routes/comedorFichaRelaciones.tsx`): clave
  `identidad_reservada` (`null` fuera de Abordaje Comunitario) y contador
  después de "Asistentes".

## Decisión

Decisión original (2026-11-16), reemplazada: "Asistentes" contaba solo
personas de la nómina y las de identidad reservada iban en un contador aparte.

Decisión vigente (2026-11-27): el issue pide que el número se contabilice en
la totalidad de personas que asisten al espacio. En Abordaje Comunitario
(Línea Secos y Línea Tradicional) "Asistentes" es ahora
`activos de la nómina + personas con identidad reservada`
(`_build_nomina_metrics` en `src/backends/comedores/comedores/views/comedor.py`,
que alimenta el legajo Django y la ficha React).

- El contador "Personas con identidad reservada" se mantiene, como detalle
  de cuántas de esas personas asistentes no figuran en la nómina.
- En el gráfico por edad las personas con identidad reservada cuentan como
  "Sin dato": no tienen fecha de nacimiento y así los porcentajes siguen
  sumando 100.
- Hombres, Mujeres y Menores de edad siguen contando solo la nómina, por lo
  que ya no suman el total de Asistentes cuando hay identidades reservadas.
- El tope de nómina no cambia.
