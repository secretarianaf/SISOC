# Cambio: adjuntos de rendición con puntos en el nombre (#2750, punto 1)

## Alcance

En PRD, subir documentación de rendición desde mobile fallaba con
`SuspiciousFileOperation` cuando el archivo tenía puntos internos en el nombre
(por ejemplo `FORM_1234567.V.CERTIFICACION_DE_PRESTACIONES_-_PRESTACION_ALIMENTARIA.pdf`).
`Storage.get_available_name` toma como extensión todos los sufijos, deja una
raíz muy corta y no puede acortar el nombre para que entre en `max_length=100`.

Se agregó `_nombre_archivo_acotado` en
`src/backends/comedores/rendicioncuentasmensual/models.py`, usado por tres
funciones `upload_to` (`documentacion_adjunta_upload_to`,
`acta_auditoria_upload_to`, `documento_regularizacion_upload_to`), una por cada
`FileField` de rendición. La migración
`src/backends/comedores/rendicioncuentasmensual/migrations/0027_upload_to_nombre_acotado.py`
solo cambia el estado de Django: no altera columnas.

## Comportamiento

- El nombre guardado conserva solo la extensión final, cambia los puntos
  internos por `_` y se recorta para dejar lugar al sufijo que agrega Django
  cuando el nombre ya existe. Siempre entra en 100 caracteres.
- Aplica a la carga mobile y a la web, porque ambas usan el mismo campo.
- Los archivos ya guardados no se mueven ni se renombran.
- No se subió `max_length`, así que no hay `ALTER TABLE`.

## Verificación

- Test nuevo `test_adjuntar_rendicion_con_puntos_en_el_nombre_guarda_dos_veces`
  en `src/backends/comedores/tests/test_pwa_comedores_api.py`: sube dos veces
  el nombre de PRD por el endpoint mobile. Sin el fix falla con el mismo
  `SuspiciousFileOperation` de PRD; con el fix pasa.
- `test_upload_to_deja_una_extension_y_entra_en_max_length` y
  `test_upload_to_conserva_nombres_cortos` en
  `src/backends/comedores/tests/test_rendicioncuentasmensual_services_unit.py`
  cubren los tres `upload_to`.
- `pytest src/backends/comedores/tests/ -k "rendicion or documentacion or pwa"`:
  459 passed, 2 skipped (antes de sumar los tests unitarios; después,
  `test_rendicioncuentasmensual_services_unit.py` + `test_pwa_comedores_api.py`:
  87 passed).
- Prueba en la app local levantada: cuatro subidas del mismo archivo al endpoint
  mobile respondieron 201 y guardaron cuatro nombres distintos, todos `.pdf` y
  de 100 caracteres o menos.
- `makemigrations --check --dry-run`: sin cambios. black sin cambios. pylint
  solo marca el nombre de la migración, y CI ignora las migraciones.
- No validado todavía en QA/HML con la app mobile real.
