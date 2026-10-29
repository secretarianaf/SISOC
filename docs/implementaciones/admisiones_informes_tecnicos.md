# Informes Técnicos de Admisiones

## Alcance

El Informe Técnico concentra los datos de admisión usados por las plantillas
DOCX. Los formularios validan las condiciones del dominio antes de renderizar y
conservan errores de unicidad como errores de formulario, sin responder 500.

## Renovaciones y prestaciones

Las renovaciones pueden requerir un Informe Técnico Complementario cuando se
modifican prestaciones. Esa condición se persiste en Admisiones y se expone
como variable documental para la plantilla; no debe resolverse solo en el
template ni inferirse después de guardar.

Los formularios base y jurídico, tanto de creación como de edición, ya no
solicitan ni validan los campos `monto_total_conveniado_informe` y
`monto_total_conveniado`. Se retiró la sección "Monto total conveniado".
Los valores históricos y las variables documentales se conservan; este cambio
no modifica las plantillas publicadas ni requiere una migración.
Ver `docs/registro/cambios/2026-T3/2026-09-11-informes-tecnicos-sin-monto-conveniado.md`.

## Templates dinámicos

Las combinaciones de condiciones se resuelven mediante versiones publicadas de
templates dinámicos. Solo personal autorizado publica una versión y únicamente
las variables documentales activas quedan disponibles. Antes de habilitar una
combinación nueva en un ambiente, debe existir su template publicado: no se
crea ni publica automáticamente durante el alta de una admisión.

## Despliegue y compatibilidad

### Descarga para GDE

El Word editable y el archivo subido para validación se conservan como DOCX.
"Descargar para GDE" entrega una copia transitoria en DOC binario Word 97-2003
(`application/msword`) del último DOCX editado o, si no existe, del borrador.
La descarga exige informe validado y los permisos existentes del técnico.
No reemplaza archivos guardados, estados ni versiones publicadas.

Antes de convertir se normalizan los anchos de las tablas. LibreOffice Writer,
incluido en la imagen Django, realiza la conversión con directorio y perfil
temporales propios por solicitud y un timeout de 120 segundos. Si no está
disponible, falla, no genera salida o devuelve un formato incorrecto, se informa
el error y no se entrega un DOCX renombrado como DOC.

La generación desde HTML conserva `colspan` y `rowspan`. El cuadro de prestaciones
de nueve columnas, identificado por sus encabezados, reserva mayor ancho para
el tipo de prestación y el total que para cada día. Si falla una plantilla
publicada, no se aplica el fallback de texto plano que perdía sus cuadros; la
finalización existente informa el error y mantiene el informe editable.

El adjunto funcional del issue #2580 es una referencia visual de otra variante;
no reemplaza el contenido de las plantillas publicadas. Los documentos históricos
ya degradados a párrafos no recuperan sus tablas al convertirlos: requieren
revisión de su plantilla y del circuito de edición. La aceptación visual final
debe verificarse importando en GDE un documento de la variante correspondiente.

Aplicar las migraciones `admisiones.0076`, `0077` y `0078` antes de operar los
nuevos campos. Luego verificar una renovación sin modificación de prestaciones
y otra que requiera informe complementario, incluyendo la resolución de la
plantilla publicada. El rollback de aplicación conserva los datos agregados;
no borrar templates ni valores ya persistidos.

## Referencias

- `src/backends/comedores/admisiones/forms/admisiones_forms.py`
- `src/backends/comedores/admisiones/services/docx_service/impl.py`
- `src/backends/comedores/admisiones/services/templates_informe_tecnico_service/impl.py`
- `docs/registro/cambios/2026-T3/2026-08-10-fixes-admisiones-pwa-rendiciones.md`
- `docs/registro/cambios/2026-T3/2026-08-12-correcciones-issues-reabiertos.md`
