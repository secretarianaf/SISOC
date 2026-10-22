---
name: migracion-app-label
description: >
  Mueve un modelo Django entre apps (cambio de app label) en SISOC conservando la tabla, los IDs y
  el content type con migraciones de estado (SeparateDatabaseAndState). Usar al trasladar un modelo
  entre kernel, sisoc_core y verticales, o al revisar una migración que cambia el label de un modelo.
---

# Mover un modelo de app conservando tabla y content type

Fuente: checklist 4 de `docs/desarrollo/verticales_independientes.md`. Esta
skill detalla cómo escribir las migraciones; si algo difiere de la guía, vale la guía.

## 0. ¿Hace falta migración?

- **Mover la carpeta conservando el app label** (por ejemplo, de `sisoc_core/` a
  `comedores/`): no hay traslado de modelo en el estado. No crear migraciones de
  traslado; verificar con `makemigrations --check --dry-run`.
- **Cambiar el app label del modelo**: sí hace falta. Seguir los pasos de abajo.

## 1. Relevar antes de escribir

- Tabla real (`db_table`), FKs entrantes y salientes, content type, permisos,
  referencias genéricas, admin, fixtures, imports y consumidores.
- Registrar conteos e IDs en una DB **aislada**, nunca en un entorno compartido.

## 2. Migración en la app destino

- `SeparateDatabaseAndState` con `state_operations=[CreateModel(...)]` y
  `database_operations=[]`.
- `options={"db_table": "<tabla_original>"}`: la tabla no se crea ni se renombra.
- `RunPython` que reasigna el content type **conservando su PK** (`update(app_label=destino)`),
  con función reversa.
- Si ya existen content types de origen y destino, **fallar** con un mensaje
  claro; no borrar duplicados ni usar `remove_stale_contenttypes`.
- Dependencias: última migración del origen, `contenttypes` y las apps de las FKs.

## 3. Migración en la app origen

- `SeparateDatabaseAndState` con `state_operations=[DeleteModel(...)]` y
  `database_operations=[]`.
- Depende de la migración destino, para que el estado nunca quede sin el modelo.

## 4. Código

- Mover el modelo y su `Meta.db_table`; actualizar imports, admin, fixtures y FKs por string (`"<app>.<Modelo>"`).
- Respetar los boundaries: el kernel no puede importar el modelo si queda en un vertical.

## 5. Validar (DB aislada)

- Instalación vacía y actualización desde el estado previo, en MySQL aislado.
- Mismos IDs, filas, relaciones, permisos y auditoría antes y después.
- `python manage.py makemigrations --check --dry-run` sin cambios pendientes.
- Reversa probada, y compatibilidad con imágenes previas durante el deploy:
  el rollback de imagen **no** revierte la migración.

## 6. Registrar

Registrar el traslado con tablas, content type, compatibilidad y reversa
(skill `registro-cambios`). Si no se probó en MySQL, decirlo.

Ejemplo completo: `ejemplo.md` en esta carpeta.
