# 2026-11-12 - Eliminar y deshacer lotes de expedientes de pago (#2632)

## Contexto

- En el detalle de un lote de "Importar Expedientes", el botón "Eliminar Archivo" no eliminaba el lote: solo deshacía la importación. En un lote que nunca se importó no hacía nada, y por eso parecía que no respondía.
- Deshacer una importación no volvía atrás los cambios que la importación hace sobre los comedores de Alimentar Comunidad (estado y `mes_ejecucion`).
- Las rutas de borrado solo pedían estar logueado.

## Cambios aplicados

- Lote **no importado**: "Eliminar Archivo" (nueva ruta `eliminar_archivo_importado`) borra el lote, sus filas validadas (éxitos y errores) y el archivo del storage.
- Lote **importado**: el botón pasa a ser "Deshacer importación" (ruta existente `borrar_datos_importados`). Borra los expedientes del lote y devuelve los comedores al estado y `mes_ejecucion` previos. Luego el lote queda listo para reimportar.
- Nuevo modelo `CambioEstadoImportacion` y campo `ArchivosImportados.fecha_importacion` (migración `importarexpediente.0016`). `aplicar_estados_por_lote` guarda, por comedor modificado, el estado y el mes de ejecución de antes y de después.
- Reglas de "Deshacer importación", decididas con quien pidió el cambio:
  - Solo se puede deshacer el último lote importado (por `fecha_importacion`), porque cada importación calcula ausencias mirando las anteriores.
  - Los lotes importados antes de este cambio (`fecha_importacion` vacía) no se pueden deshacer. No hay registro de cómo estaban los comedores, y la pantalla lo explica.
  - Si un comedor cambió de estado o de mes después de la importación, no se toca y se avisa cuántos quedaron así.
  - Los `EstadoHistorial` creados por la importación revertida se borran, para que la próxima importación calcule las ausencias igual que si el lote nunca se hubiera importado.
- Las rutas de deshacer y eliminar exigen `importarexpediente.change_archivosimportados` o `expedientespagos.change_expedientepago`. Son los mismos permisos que ya mostraban los botones de gestión del lote.

## Impacto esperado

- Quien tiene solo permiso de lectura ya no ve ni puede usar los botones de deshacer o eliminar (responde 403).
- `importar_datos` sigue pidiendo solo login. Agregarle permiso queda como mejora aparte.

## Validación

- Tests en `src/backends/comedores/importarexpediente/tests/test_import_flow.py`: eliminar un lote no importado y uno importado, revertir estados, respetar cambios manuales, deshacer solo el último lote, bloquear lotes viejos, mostrar el botón según el estado del lote y negar acceso sin permiso.
- `black`, `pylint`, `djlint`, `makemigrations --check` y `test_registro_de_urls_al_dia`.

## Riesgos y rollback

- Riesgo: una importación ahora guarda una fila por comedor modificado (todos los de Alimentar Comunidad). Es un volumen acotado.
- Rollback: revertir el PR y la migración `importarexpediente.0016`. Se pierden los registros de estados previos, y los lotes importados mientras tanto vuelven a no poder deshacerse.
