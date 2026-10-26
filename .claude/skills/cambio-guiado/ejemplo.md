# Ejemplo: "quiero filtrar el listado de comedores por un dato más"

Caso ilustrativo sobre un patrón real del repo: los filtros avanzados
(`docs/implementaciones/filtros_avanzados.md`). Al momento de escribirlo, el
campo `categoria_espacio_comunitario_otra` existe en el modelo `Comedor` pero no
en los filtros; antes de usar el ejemplo, confirmarlo en el código.

## 1. Entender el pedido

Pedido original: "Agregá un filtro al listado de comedores".

Preguntas en simple antes de tocar código:

- ¿Por qué dato querés filtrar? → "por lo que cargan en 'Otra categorización'".
- ¿Dónde lo usás? → "en el listado de comedores, el buscador con filtros".
- ¿Cómo sabés que anda? → "escribo 'merendero' y solo veo los que tienen eso cargado".

Primero revisar si el filtro ya existe: `provincia`, por ejemplo, ya está. Si
existe, la respuesta es mostrar cómo usarlo, no escribir código.

## 2. Ubicar dónde va

Comedores es un vertical: `src/backends/comedores/comedores/`. La guía de filtros
indica que la configuración vive en `services/filter_config/` de la app.

## 3. Patrón existente

- Configuración: `src/backends/comedores/comedores/services/filter_config/impl.py`
  (`FIELD_MAP`, `FIELD_TYPES`, `FILTER_FIELDS`, `get_filters_ui_config()`).
  El campo hermano `categoria_espacio_comunitario` ya está: copiar su forma.
- Motor compartido: `AdvancedFilterEngine` en `src/backends/kernel/core/services/advanced_filters/`
  (se usa, no se modifica).
- Tests del mismo estilo: `src/backends/comedores/tests/test_comedores_filter_config_unit.py`.

En el PR: "Se hizo como el filtro `categoria_espacio_comunitario` de Comedores".

## 4. Implementar en chico

- Agregar `categoria_espacio_comunitario_otra` a `FIELD_MAP` (lookup igual al
  campo), a los campos de texto de `FIELD_TYPES` y a `FILTER_FIELDS` con un label
  legible ("Otra categorización").
- No tocar el motor del kernel ni crear otro sistema de filtros.
- Si el dato pedido no existe en el modelo, **parar**: sería un campo y una
  migración nuevos (zona delicada). Explicarlo en simple y marcar el PR como
  "Requiere revisión técnica".

## 5. Tests

En `src/backends/comedores/tests/test_comedores_filter_config_unit.py`, igual que
los existentes:

```python
def test_config_expone_filtro_por_otra_categoria():
    config = get_filters_ui_config()
    fields = {field["name"]: field for field in config["fields"]}

    assert fields["categoria_espacio_comunitario_otra"]["type"] == "text"
    assert FIELD_MAP["categoria_espacio_comunitario_otra"] == (
        "categoria_espacio_comunitario_otra"
    )
```

Y un test del listado que afirme que, con el filtro aplicado, solo vuelven los
comedores que tienen ese texto (nombres de vista y fixtures, del código real).

## 6. Autorrevisión

- Patrón: el mismo `filter_config`; sin motor nuevo. ✔
- Nombres: los del modelo. ✔
- Permisos: el listado ya filtra por alcance del usuario; el filtro no lo cambia. ✔
- Diff: solo `filter_config` y sus tests. ✔

## 7. PR en lenguaje simple

> **Qué cambia, en simple:** en el listado de comedores aparece el filtro
> "Otra categorización". **Cómo probarlo:** abrir Comedores → Filtros → elegir
> "Otra categorización" → escribir un texto → solo se ven los comedores que lo
> tienen. **Qué podría romperse:** nada fuera de este filtro; no cambia permisos
> ni datos.
