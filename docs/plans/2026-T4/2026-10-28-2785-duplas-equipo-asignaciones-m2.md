# DU01: equipo técnico, coordinación y asignación a comedor

E2: planificación fuente. DU01.01 Equipo y asignaciones [L], DU01.02 Asignar y
modificar según permisos [M], dueño comedores/duplas, sin APIregistrada identificada.
No nuevo ID por la asignación enlazada que pertenece circuitoComedores.

## Rutas y autorizaciones no intercambiables

Equipo-tecnico: dupla_list/crear/detalle/editar/eliminar, login + role_admin;
GETlectura/Form/confirmación, POSTguardar/bajalógica. Querysetsglobal Dupla.objects,
no scopeactor adicional identificado. dupla_exportar usa ANY role_admin/rolCSV,
no ANDcomoUsuarios. No copiar permisos de export a CRUD.

comedores/dupla/asignar/<pk> dupla_asignar: GET/POST login+duplas.change_dupla y
scopecomedor, no role_admin. Éxito/error→comedor_detalle. La dependencia M2 exige
fichaComedores/avisos, no formulario solo que vuelve a UIlegacy.

## Listado, detalle y CSV DU01.01

10/página, -fecha,nombre, filtrosM2M distinct, preferenciasduplas_list y favoritos
DUPLAS. Filtros nombre/tecnico/tecnico_apellido/abogado/abogado_apellido/coordinador/
coordinador_apellido/estado text; contains,ncontains,eq,ne,empty. Columnas nombre
obligatoria/enlace, coordinador,técnicos,abogado,estado; opcionales fecha/id. Técnicos
coma y coordinador vacío «Sin asignar». Detalle muestra equipo/estado/miembros y
acciones. CSV listado_duplas.csv mismas columnas/filtros, sort/direction whitelist,
fallback -fecha,nombre y distinct. No nuevo JSON existente por renombrar HTML/CSV.

## Form y efectos DU01.02

Nombre requerido255; tecnico múltiple requerido grupo «Tecnico Comedor»; abogado
simple requerido grupo «Abogado Dupla»; estado requerido Activo/Inactivo. Etiqueta
Apellido Nombre - username/fallbackusername; grupos faltantes→querysetvacío. No
filtro is_active en esas opciones ni límitemáximo técnico por número de duplas.
ModelChoices siguen validación servidor, no aceptar IDforjado por esconder opciones.

Coordinador excluido Form; se asigna desde Usuarios aunque docstringmodelo sugiera
bidireccionalidad. No añadir selector por descripción. Guardado ModelForm/CBV, no
servicio create_dupla no usado en vista. Alta→listado «Equipo técnico creado
correctamente.», inválido aviso general y errores; edición→listado sin success
explícito equivalente. Cancelar→listado; no email/archivos/integraciones en CRUD.

Baja confirmación usa delete_confirm/previewcascada; POST delete(user,cascade=True),
listado «Equipo técnico dado de baja correctamente.». No harddelete/limpieza manual.
Comedor.dupla nullable/PROTECT no demuestra solo resultado de softdeletecascada:
reusar mecanismo y contrastar efecto completo. M2M Dupla.coordinadores usa tabla
histórica users_profile_duplas_asignadas, señales sincronizan FKcoordinador y relación
inversa; no dividir en dos escrituras cliente ni reimplementar señalesfrontend.

## Asignación enlazada y acceso indirecto

GETresuelve comedor scoped, opcionesduplasactivas. POSTrepitescope, lee dupla_id;
vacío «No se seleccionó ninguna dupla.». Servicio cambia dupla_id y estado del
comedor a «Asignado a Dupla Técnica». No revalida Activo en ese método: conservar
asimetría fuente y contrastar POSTforjado, no endurecer incidentalmente. No acción
desasignar identificada. CoordinadorPWA consulta comedores según duplasscope:
reasignar puede cambiar acceso indirecto, no solo texto de ficha.

## Casos visuales/contrato futuros

Listado/filtros/columnas/paginación/detalle sincoordinador/múltiplestécnicos; Forms
alta-edición errores/cancelar, previewbaja, asignación/retornofeedback. Export-only
frenteCRUD, ChangeDupla+comedorajeno, miembrofueraopciones/faltagrupo, coordinador
preservado, inactivaPOSTfuente, señales/relaciones/bajarepetida. Verificar estado
comedor y conjuntosacceso tras asignación, no solo HTTPredirect. Sintéticos,
referencia/candidato/diffdesktop-móvil/foco y acumulado; sin ejecución.

## Fuente

src/backends/comedores/duplas/urls.py:14–44; views.py:48–191;
views_export.py:15–57; forms.py:7–73; models.py:33–105; signals.py:16–86;
dupla_filter_config.py:7–45; dupla_column_config.py:7–80;
templates/dupla_detail.html:33–97; dupla_form.html:52–65;
src/backends/comedores/comedores/urls.py:246–250; views/dupla.py:16–42;
services/comedor_service/impl.py:822–827; models.py:347–352;
src/backends/comedores/pwa/services/accesos.py:133–150;
src/backends/kernel/core/soft_delete/view_helpers.py:90–117.
Seis archivosduplas urls/views/export/forms/models/signals contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa normalizandoCRLF, otroscheckout. Padre
contrastó cambioequipo/estadocomedor. CodeGraphsync; sin app/tests/DB/browser/remote.

- [U06 campos compuestos](2026-10-28-2785-usuarios-u08-formulario-compuesto.md).
- [Catálogo existente](2026-10-27-2785-entregas-por-flujo.json).
