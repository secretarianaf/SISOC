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

## Protección frente a operaciones simultáneas

- La migración `0017` agrega una tabla de coordinación. Al importar o deshacer,
  ambas operaciones bloquean la misma fila hasta finalizar la transacción y
  comprueban el lote después de obtener el bloqueo. Esto conserva el orden entre
  operaciones de este flujo, a costa de ejecutarlas de a una.
- La reversión actualiza cada comedor solo si su estado y mes todavía coinciden
  con lo que dejó la importación. La comparación y actualización son una sola
  operación SQL; un cambio concurrente se respeta y se informa como omitido.
- Las pruebas de concurrencia ejecutan dos transacciones reales sobre MySQL
  aislado. No cubren cambios en otros campos ni escrituras externas que no
  respeten las transacciones del sistema.
- Durante un despliegue selectivo, las instancias anteriores pueden seguir
  activas mientras se ejecuta la migración y no toman el bloqueo nuevo. Antes
  del despliegue o rollback se debe detener la importación y reversión de lotes
  hasta que todas las instancias estén actualizadas; la migración sola no
  protege una convivencia de versiones. No se verificó ese procedimiento en un
  entorno real y requiere coordinación operativa antes de desplegar.
- El bloqueo solo coordina este flujo. El `UPDATE` condicionado evita pisar un
  valor diferente de estado o mes, pero no detecta un cambio externo que vuelva
  a dejar exactamente esos mismos valores, ni serializa otras escrituras.
- Para revertir el cambio, revertir `0017` antes de `0016` y el código asociado;
  no hacerlo mientras haya operaciones de importación o reversión en curso.
