# Ejemplo: release del 2026-10-22

Caso real que motivó la regla "parar y preguntar" de esta skill.

## Qué pasó

- El usuario quería subir a PRD solo el hotfix #2759.
- Ese mismo día se mergeó #2760 (`development -> homologacion`), así que `homologacion`
  ya tenía todo `development`, sin la semana de prueba en HML.
- La release #2771 promovió `homologacion -> main` y PRD desplegó todo eso.
- Hubo que forzar `main` a `9fb740344` (homologacion previa a #2760 + hotfix #2759),
  revertir migraciones en PRD y cerrar la promoción descendente #2773.

## Cómo lo evita la skill

1. Paso 1: el relevamiento muestra que `homologacion` trae los PRs de #2760.
2. Paso 3: esos PRs aparecen en "En HML hace menos de 7 días" del PR final.
3. Regla: como entraron sin la semana en HML y el usuario pidió solo #2759, se para y
   se pregunta qué debe entrar antes de crear el PR final.
4. Orden: el PR `development -> homologacion` se crea pero se mergea recién después
   del release, así no se mezcla con lo que va a PRD.

## Referencia de formato

El body de #2722 (release 2026-10-15) muestra los markers del orquestador y el
resumen por módulo que reproduce `plantillas.md`.
