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

## Decisión

El contador "Asistentes" del apartado Nómina sigue contando solo personas de
la nómina. Las de identidad reservada se muestran en un contador aparte y no
se suman a ese número ni a los porcentajes por edad, que se distorsionarían
con personas sin datos.
