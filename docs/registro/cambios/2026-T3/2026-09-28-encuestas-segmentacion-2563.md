# Segmentación por IDs de usuarios — issue 2563, punto 6

Se agrega «Listado de IDs de usuarios» junto a todos los usuarios y documentos.
Permite agregar/quitar individualmente y reemplazar por Excel o CSV UTF-8 de
hasta 5 MB. La plantilla XLSX se descarga según el tipo seleccionado: documentos
conserva su formato y usuarios contiene una columna `usuario_id`, sin IDs de
ejemplo que puedan incorporar accidentalmente a una persona real.

Los IDs deben ser enteros positivos de usuarios existentes. Se eliminan
duplicados; un archivo vacío, mal formado o con IDs inexistentes se rechaza
completo sin alterar el tipo ni los destinatarios previos. Cambiar de tipo
elimina los destinatarios del tipo anterior. El listado muestra ID, cuenta y
nombre, también durante la revisión del aprobador.

La migración `0006_segmentacion_usuarios` agrega una relación muchos a muchos
con usuarios. No convierte ni modifica las segmentaciones existentes. Se
conservan permisos de gestión y bloqueo de cambios durante aprobación; los
cambios con ronda abierta siguen aplicándose inmediatamente. La cola de
pendientes precarga solo el usuario consultante y la respuesta comprueba su
pertenencia al listado incluso si no tiene documento en el perfil.

Las nuevas versiones conservan los destinatarios. Exportar con segmentación por
IDs usa JSON versión 4; los demás casos conservan versión 3 y el importador sigue
aceptando versiones 1–3. Al importar se valida que los IDs existan. La interfaz
advierte que un ID puede identificar a otra persona en otro ambiente; para
traslados entre ambientes se recomienda documentos o configurar destinatarios
en destino. No se agregaron condiciones adicionales sin un caso de uso concreto.

## Validación

- Migración aplicada al MySQL local; `makemigrations --check --dry-run` sin cambios.
- 276 tests del módulo pasaron en Docker (17 nuevos), incluidos reemplazo atómico,
  CSV/XLSX, permisos, respuesta fuera del segmento, aprobación y portabilidad.
- Black, djlint y `git diff --check` sin diferencias. Pylint: 9,99/10;
  única advertencia por longitud de `services.py` (1064 líneas frente a 1000).
  Se conserva la organización actual para evitar un refactor ajeno al pedido.
- Chrome contra MySQL local: descarga de plantilla, alta manual, reemplazo CSV,
  rechazo de ID inexistente sin pérdida del listado y baja individual. Vista de
  390 px sin desborde y sin errores JavaScript con los recursos externos cargados.
  Se dejó la encuesta QA 10 en borrador con un usuario de prueba seleccionado.
