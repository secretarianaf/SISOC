# Cambio: copia de pnud_formularios.json alineada con el generador de Gestionar

## Alcance

Se regenera `src/backends/comedores/relevamientos/data/pnud_formularios.json` con `pwa/scripts/pnud/formularios-json.mjs` de Gestionar (`development`, más el ajuste del generador en su PR asociado). No cambia código de SISOC, modelos ni migraciones.

## Qué cambia

- 7.2.1 de II A: los ítems del ranking de combustible toman la pregunta del papel oficial, «¿Cuál es el tipo de combustible que utilizan para cocinar? — <ítem> (n° de orden)».

Todo lo demás queda igual. Se verificó que la regeneración reproduce la copia actual: bloques finales numerados en su propia sección, firma en «Cierre», «La entrevista se realizó de forma» y `opcionExclusiva` del SIPH. Para lograrlo se corrigió el generador de Gestionar, que había quedado atrás de esta copia. No se renombra ni se quita ninguna clave.

## Verificación

- Tests PNUD de SISOC (`test_pnud_formularios_estructura.py`, `test_seguimiento_siph_2651.py`, `test_issue_2641_c2_recursos.py`): 34 pasan. Se actualizó la pregunta esperada de 7.2.1.
- Gestionar: 433 tests unitarios y `tsc --noEmit` limpios.
