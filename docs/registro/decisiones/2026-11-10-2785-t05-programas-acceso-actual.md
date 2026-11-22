# 2026-11-10 - Programas (T05): acceso actual se conserva en la migración a React (#2785)

## Estado

- aceptada (responsable, 2026-11-10):

> "sobre los t05, dejalo como esta, se arreglara en otro momento, documentalo"

## Contexto

Las vistas de Programas del kernel (`Programa*View` en
`src/backends/kernel/core/views.py`, rutas en `src/backends/kernel/core/urls.py`)
solo exigen `LoginRequiredMixin`. Cualquier usuario autenticado puede listar,
crear, editar y eliminar programas. No hay permiso específico ni restricción por
rol.

La migración a React (#2785) necesita una API web para este flujo (familia T05
del catálogo de entregas). Copiar el acceso actual mantiene una brecha conocida;
agregar permisos cambiaría quién puede operar sobre programas.

## Decisión

La migración de T05 conserva el acceso actual tal como está: la API web y las
pantallas React aplican la misma regla que las vistas Django (solo sesión
autenticada). No se agregan permisos ni restricciones en esta migración.

## Consecuencias

- La brecha de permisos de Programas sigue abierta y se corrige en otro trabajo,
  aparte de la migración. Ese trabajo debe cubrir a la vez las vistas Django y la
  API web, para no dejar dos reglas distintas.
- Los tests de la API web de T05 fijan el comportamiento actual (cualquier usuario
  autenticado opera) para que el arreglo posterior tenga que cambiarlos de forma
  explícita.
- Pendiente sin verificar: el mensaje de éxito al eliminar se define en un
  `DeleteView.delete()` sobrescrito, que las versiones recientes de Django pueden
  no invocar. Se revisa al migrar T05 sin cambiar el comportamiento visible.

## Referencias

- Épica de migración a React #2785.
- `src/backends/kernel/core/views.py` (`ProgramaListView` a `ProgramaDeleteView`).
