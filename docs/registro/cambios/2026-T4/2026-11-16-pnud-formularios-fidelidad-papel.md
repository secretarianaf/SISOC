# Cambio: formularios PNUD II A y II B fieles al papel oficial

## Alcance

Se actualiza la copia vendorizada `src/backends/comedores/relevamientos/data/pnud_formularios.json`, con la que el backoffice muestra las respuestas de los seguimientos PNUD que carga la app Gestionar. La definición de los formularios vive en Gestionar (`pwa/src/features/pnud/pnudForm.ts`) y allí se hizo la corrección. No cambia código de SISOC, modelos ni migraciones: las respuestas siguen en `SeguimientoPnud.datos` (JSON).

## Qué cambia en el backoffice

- II A y II B: nueva pregunta 7.1.6 «Recipiente para la basura» (Sí/No, clave `basura_recipiente`).
- II A y II B: 4.1 «¿Quién realiza las compras?» admite las dos opciones (`enumlist`). Un registro viejo con una sola respuesta en texto se sigue mostrando: `pnud_formularios.py` ya trata un valor suelto como lista.
- Rótulos con el texto del papel oficial: 4.2 «Otro ¿Cuál?», 5.1, 5.3, 5.5 y 5.6, 7.1.1 a 7.1.5, 7.1.2 «Heladera», 7.2.1 «Otros: ¿cuál?» y 8.1.1 a 8.1.3.
- Motivo de funcionamiento, 5.3 y «¿Por qué?» pasan a texto largo; «Destinatarios» por módulo (II B / II B.1, 5.7 / 3.7) pasa a texto, porque el papel usa rangos («2-3»).

No se renombra ni se quita ninguna clave: los datos ya guardados se leen igual.

## Alcance acotado de la copia

La copia de `homologacion` está atrasada respecto de Gestionar en otros puntos (sección de cierre, «la entrevista se realizó de forma», rótulos de combustible). Para no mezclar cambios, se aplicó solo el diff de este cambio, no una regeneración completa. La sincronización completa queda para un PR aparte.

## Verificación

- Tests PNUD de SISOC (`test_pnud_formularios_estructura.py`, `test_seguimiento_siph_2651.py`, `test_issue_2641_c2_recursos.py`): 34 pasan. Se actualizó la etiqueta esperada «Heladeras» → «Heladera».
- `pytest -k "pnud or siph or 2641 or seguimiento"`: 352 pasan y 2 fallan; las 2 fallas (`test_listados_sin_n_mas_1[...primerseguimiento...]` y `test_issue_2641_c2_http.py`) ya fallaban con la imagen local en la rama base.
- Gestionar: 431 tests unitarios y `tsc --noEmit` limpios.
