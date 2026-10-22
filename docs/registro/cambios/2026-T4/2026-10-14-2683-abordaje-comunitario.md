# Issue #2683: rendiciones, prestaciones y actividades de Abordaje Comunitario

## Alcance

- SISOC: rama `Fix-Issue-2683`. Mobile: repositorio `SISOC-EspaciosComunitarios`, rama `main`, según instrucción del responsable.
- Se conservan los componentes, estilos, catálogo, permisos, archivos históricos y funcionamiento offline existentes.

## Comportamiento

1. Mobile quita Rendiciones del hub de cada espacio y conserva el acceso desde el hub de organizaciones. Las rutas de consulta exigen `manage_mobile_rendicion`, con la excepción existente del coordinador PWA de sólo lectura. Los formularios siguen exigiendo permiso de escritura. La API ya verifica permiso y alcance del comedor.
2. Reenviar una subsanación territorial deja `revision_documentacion:subsanado`; Revisión para Carga mantiene `revision_auditoria:subsanado`.
3. Mobile muestra «Rendición Cargada» para `finalizada`, incluso para registros cacheados con la etiqueta anterior. El estado interno y las etiquetas de SISOC se conservan.
4. Abrir un documento marca una actualización pendiente del detalle. Al regresar a la pestaña o ventana de SISOC se recarga una sola vez para consultar la confirmación persistida. Volver sin abrir documentos no recarga. Si hay una revisión sin guardar (estado elegido u observación escrita), la recarga se posterga para no perderla.
5. La subsanación copia la observación al archivo nuevo. Web y mobile la muestran durante la revisión; una observación nueva la reemplaza y validar el archivo la limpia. Mobile conserva la observación al cargar offline. No reconstruye observaciones de archivos corregidos antes de este cambio si ya no están disponibles.
6. El botón de Revisión para Carga se denomina «Iniciar revisión para carga».
7. El cuadro del legajo muestra Merienda Reforzada sólo para Línea Tradicional, con los campos existentes del convenio.
8. Los encabezados del cuadro dicen Prestaciones.
9. Planilla de Seguros II admite varios archivos y usa el mismo historial de subsanaciones que Documentación Adicional, tanto en SISOC como en mobile. El código `planilla_seguros` y el nombre del modelo descargable se conservan.
10. Actividades separa Categoría y Actividad con filtrado dependiente y opciones alfabéticas. Se conserva la FK al catálogo, por lo que los registros previos ya tienen el nuevo formato sin migrar datos. La edición conserva la opción actual aunque el catálogo haya sido deshabilitado; no permite asignar una actividad de otra categoría. Los POST anteriores sin categoría mantienen compatibilidad.

## Migración y publicación

- `rendicioncuentasmensual.0026_issue_2683_planilla_seguros_ii` actualiza únicamente choices de dos campos; no cambia códigos ni archivos.
- Publicar backend y mobile coordinadamente para alinear la multiplicidad e historial de seguros: al subsanar `planilla_seguros`, mobile debe enviar `documento_subsanado_id`; sin él, el archivo se suma y el observado sigue bloqueando la presentación. Ejecutar migraciones con el migrador habitual.
- La migración no se aplicó sobre una base de negocio durante el desarrollo. La publicación de código se realiza por PR de SISOC a `development` y push autorizado de mobile a `main`.

## Validación

- Regresiones de estados, observaciones en categorías con y sin historial, seguros múltiples, permisos API, categoría/actividad y cuadro de prestaciones.
- Pruebas JS del retorno al visor y de permisos de rutas mobile, sin dependencias nuevas.
- Compilación de mobile y ESLint de archivos modificados.
- El lint global de mobile ya falla en archivos ajenos al issue: `SpaceActivitiesPage.tsx`, `ThemeContext.tsx` y `buttons.tsx`.
- La comprobación de migraciones con `DJANGO_SETTINGS_MODULE=config.settings_all` desde el inicio informa `No changes detected`. El error previo del grafo fue causado por inicializar el core antes de procesar `--settings`; no es una dependencia faltante del repositorio. El contenedor sin MySQL advierte que no puede comprobar el historial de la base; CI valida sobre MySQL.

### Resultado de cierre

- 184 pruebas Python aprobadas; compilación mobile y ESLint de archivos modificados aprobados.
- 4 pruebas JS de SISOC y 3 pruebas de permisos mobile.
- Black aplicado a Python. Pylint conserva únicamente dos errores de inferencia `E1101` sobre `forms.TimeField.clean`; se reprodujeron en el archivo original de la rama antes del cambio.
- djlint 1.43.2, la versión fijada para CI, completó el formateo de los tres templates. La versión anterior del contenedor (1.34.2) se detenía en el template grande. El modo lint conserva dos avisos `H037` en tags Django ya existentes; el workflow usa `--check` para verificar formato.
- `check_docs_paths.py` señala una referencia previa obsoleta en el mapa (`kernel/tests/test_usuarios_simepi_scope.py`).
