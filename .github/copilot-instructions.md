# Instrucciones para GitHub Copilot (SISOC)

Fuente de verdad:
- `AGENTS.md`

Arranque minimo:
1. `AGENTS.md`
2. `docs/indice.md`
3. archivo objetivo + tests
4. una guia relevante de `docs/ia/`

Principios:
- minimo contexto suficiente,
- diffs chicos,
- sin inventar contratos ni permisos,
- validacion puntual antes de checks amplios,
- documentacion en `docs/` para cambios importantes.

Responsabilidades (resumen de `AGENTS.md`; Copilot no carga skills):
- quien pide puede no saber programar: entender el problema y el resultado esperado antes de escribir codigo; preguntar si es ambiguo,
- seguir un caso parecido que ya exista en el repo y nombrarlo en el PR,
- logica en `services/`, views nuevas class-based, sin dependencias, modelos, settings ni permisos nuevos sin explicarlo,
- siempre tests que afirmen el comportamiento (CI exige tocar tests y 80% de cobertura de las lineas cambiadas),
- migraciones, permisos, settings, `src/backends/config/`, `src/backends/kernel/`, workflows, `docker/` o dependencias: marcar el PR como "Requiere revision tecnica",
- si el cambio se ve en pantalla, guiar a quien pidio a verificarlo en el entorno local (con un caso que no deberia funcionar) y esperar su confirmacion antes del commit y del PR,
- completar la seccion "En lenguaje simple" de la plantilla de PR; no mergear ni usar el label `excepcion-calidad`.

Si falta `AGENTS.md`, usar este archivo como fallback corto y evitar cambios grandes hasta tener contexto.
