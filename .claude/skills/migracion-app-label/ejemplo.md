# Ejemplo: Firmante de `organizaciones` a `gestion_organizaciones`

Caso real del repo. `Firmante` estaba en el kernel (`organizaciones`), pero se
relaciona con `comedores.Programas`, así que no podía quedar ahí: pasó a
`gestion_organizaciones`, del cluster de Comedores. La tabla sigue siendo
`organizaciones_firmante`.

Migraciones:

- destino: `src/backends/comedores/gestion_organizaciones/migrations/0001_firmante_desde_organizaciones.py`
- origen: `src/backends/kernel/organizaciones/migrations/0023_firmante_a_gestion.py`

## Destino: crear en el estado y mover el content type

```python
def _mover_content_type(apps, origen, destino):
    content_type = apps.get_model("contenttypes", "ContentType")
    if content_type.objects.filter(app_label=destino, model="firmante").exists():
        if content_type.objects.filter(app_label=origen, model="firmante").exists():
            raise RuntimeError(
                f"Existen content types {origen}.firmante y {destino}.firmante: "
                "resolver a mano antes de migrar para no perder permisos."
            )
        return
    content_type.objects.filter(app_label=origen, model="firmante").update(
        app_label=destino
    )

operations = [
    migrations.SeparateDatabaseAndState(
        state_operations=[
            migrations.CreateModel(
                name="Firmante",
                fields=[...],  # mismos campos que en el origen
                options={"db_table": "organizaciones_firmante"},
            ),
        ],
        database_operations=[],
    ),
    migrations.RunPython(content_type_a_gestion, content_type_a_organizaciones),
]
```

Puntos clave:

- `database_operations=[]`: no se toca la tabla.
- `update(app_label=...)` conserva la PK del content type, y con ella los
  permisos y las referencias de auditoría.
- Si existen los dos content types, falla en lugar de borrar.
- Dependencias: `comedores` (FK a `Programas`), `contenttypes` y la última
  migración de `organizaciones`.

## Origen: retirar del estado

```python
dependencies = [
    ("organizaciones", "0022_issue_2445_territoriales_abordaje_comunitario"),
    ("gestion_organizaciones", "0001_firmante_desde_organizaciones"),
]
operations = [
    migrations.SeparateDatabaseAndState(
        state_operations=[migrations.DeleteModel(name="Firmante")],
        database_operations=[],
    ),
]
```

## Qué queda por demostrar

El recorrido de la guía es documental. Para un traslado nuevo hay que repetir
las pruebas de la sección 5 de la skill en MySQL aislado y registrar el
resultado. Los catálogos usan el mismo patrón en
`src/backends/kernel/catalogo_intervenciones/migrations/0001_catalogos_desde_intervenciones.py`.
