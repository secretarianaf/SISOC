# Cambio: documentos de intervenciones CDI en una carpeta privada propia (CDI-F2, #2785)

## Decisión

Del responsable, 2026-11-16: "dale a cdi su propia carpeta". Se cierra el alias público
`/media/documentacion/` solo para CDI. Comedores comparte esa carpeta
(`comedores/intervenciones/models/intervenciones.py`, `upload_to="documentacion/"`, y su plantilla y
ruta React enlazan `/media/documentacion/...`), así que ese prefijo **no se cierra** y Comedores sigue
igual.

## Qué cambió

- `IntervencionCentroInfancia.documentacion` sube a `cdi/documentacion/` (migración
  `0055_documentacion_intervencion_prefijo_cdi`, solo `AlterField` de `upload_to`; no modifica datos).
- Comando `mover_documentacion_cdi` para los archivos existentes: copia, verifica el tamaño, actualiza
  la fila y recién entonces borra el archivo viejo. Solo selecciona filas de CDI. Dry-run por defecto,
  `--aplicar` ejecuta. El destino es `cdi/documentacion/<pk>_<nombre>`, determinístico, por lo que una
  corrida interrumpida se reanuda sin copias duplicadas. Los faltantes se informan sin fallar; si otra
  fila CDI apunta al mismo archivo viejo, no se borra.
- La descarga autenticada (`/api/web/cdi/intervenciones/<id>/documentacion/`) no cambia: lee el nombre
  guardado, así que sirve el archivo en la ruta nueva.
- El detalle nativo de la intervención enlazaba `documentacion.url` (`/media/...`); ahora enlaza la
  descarga autenticada, porque `/media/cdi/` queda cerrado.
- Nginx: `location ^~ /media/cdi/ { return 404; }` en `docs/operacion/nginx/sisoc-produccion.conf` y en
  los bloques equivalentes de `deploy_entornos_docker_nginx_mysql.md` y `qa_trixie_deploy.md`.

## Riesgos y límites

- Alto: toca nombres guardados y la ubicación de archivos. El movimiento debe correr antes de cerrar
  Nginx, o en la misma ventana. Pasos exactos y reversa en `docs/operacion/comandos_administracion.md`
  (sección "Centro de infancia (CDI)").
- Mientras los archivos viejos no se muevan, siguen accesibles por `/media/documentacion/` (el alias
  que se mantiene abierto por Comedores): cerrar CDI-F2 de verdad requiere correr el comando.
- El nombre nuevo se acorta (conservando la extensión) para entrar en el `max_length` del campo; un `DataError` al actualizar se informa como CONFLICTO y se borra la copia. Antes de borrar el archivo viejo también se verifica que ninguna intervención de Comedores lo use.
- Los archivos movidos se descargan con el nombre `<pk>_<nombre original>`.
- Nada se ejecutó contra datos reales.

## Verificación

Tests en `src/backends/cdi/centrodeinfancia/tests/test_mover_documentacion_cdi.py`: subida nueva en el
prefijo CDI, dry-run sin cambios, `--aplicar` mueve solo archivos CDI (un archivo de Comedores queda
intacto) y la segunda corrida no hace nada, reanudación tras copia interrumpida, faltante informado,
descarga autenticada del archivo movido (anónimo 401, sin permiso 403) y enlace del detalle nativo.

## Endurecimiento del comando (revisión independiente)

- Antes de actualizar la fila y de borrar el archivo viejo se compara el SHA-256 (en streaming) de origen y destino; un destino con otro contenido, aunque tenga el mismo tamaño, es CONFLICTO y se conservan ambos archivos.
- Si no se puede comprobar el uso por Comedores (app no instalada en el runtime, p. ej. `backend_cdi`), el archivo viejo no se borra y se informa `PENDIENTE`; hay que repetir el comando en el migrador / `settings_all`.
- Una pasada de reconciliación borra el archivo viejo de las filas ya movidas cuyo borrado se interrumpió (nombre legado recuperado de `cdi/documentacion/<pk>_<nombre>`), con la misma comprobación de hash y de uso. Si el nombre se acortó al mover, el original no es recuperable por esta vía y queda a revisión manual.
- Tests nuevos: consumidores no comprobables, destino de igual tamaño y distinto contenido, reanudación tras interrupción entre actualizar y borrar, y reconciliación en dry-run, con contenido distinto y sin poder comprobar Comedores.
