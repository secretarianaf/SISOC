# CO07.01/02: listado, ficha y formularios Comedores

E2: fuente parcial todavía no schema final o implementación. CO07.01 Listado ficha
y navegación, CO07.02 Alta/edición; CO07.03 Convenio/validación se profundiza aparte.
Owner comedores/comedores. La ficha incluye mutaciones, no solo lectura.

## Rutas y alcance

comedores/listar (comedores) y comedores/<pk> (comedor_detalle) login + ANY
ViewComedor/ViewAdmision/ViewInformacionRelevante. CrearAddComedor, editarChange,
bajaDeleteComedor. Responsabletarjeta/editar acciónaparte role_tecnico_comedor.
Listado get_filtered_comedores(request,user), NoCount10/página, no totalconvencional
inventado. Detalle servicio con actor, edición/baja scopedqueryset.

Scope objeto: global sinfiltro; coordinador por equipos, técnico/abogado por dupla;
territorial UNION con asignados fuera de territorio, no intersección. Sin rol
restringido/territorial preserva base. Global exacto: sinuser uso interno, superusuario o tiene_grupo(role_coordinador_general).
En requests pasar actor siempre, no is_staff/role_admin ni actoromitido como default.
Listado tiene helper especializado distinto, no unificar mecánicamente con objeto.

## Alta/edición y efectos

ComedorForm + ReferenteForm prefijo referente, imágenes múltiples imagenes.
Alta transaccional crea referente/comedor/estados/imágenes; errornofield «Error al
guardar el comedor: …». Edición conserva dupla_original, actualiza referente/comedor,
borra imágenes/foto segúnPOST y agrega nuevas; «Error al actualizar el comedor: …».
Éxitoalta-edición→comedor_detalle. Baja→comedores «Comedor dado de baja correctamente.».
DBatomic no prueba rollback de bytes, no prometerlo por configuración Django.

ComedorForm Meta __all__ con exclusiones ultimo_estado/fecha_validado/mes_ejecucion:
schemaReact necesita whitelist efectiva de modelo+controlesUI, no serializer__all__.
Estado_general/subestado requeridos; motivo opcional, hijos pertenecen padre.
Comienzo opcional1900–2026 en fuente actual; postal1000..999999, coordenadas±90/180.
es_caritas requerido vacío/Sí/No con coerciónbooleana. Organizaciónremota queryset
selectedID y proyectosactivos propios. Programa sincódigo limpia proyecto/código;
compatible requiere proyectoactivo y deriva código. Categoríanootra limpia detalle.
En PACprograma2 existente, estados disabled salvo permisos/predicado correspondientes;
no confiar en bloqueoUI. Historialestado solo sicambio, preserva ultimo_estado.
Enumeración completa, Referente/geografía/filtros/columnas y adjuntos aún pendientes.

## Mutaciones de ficha y dependencias

POSTadmision→crear_admision_desde_comedor. POSTaction=descartar_expediente solo
superusuario, admision_id/motivo_descarte; buscaID, marcaarchivo/motivo/fecha y estados
Descartado, retornofeedback. Esa rama no comprueba pertenencia a comedor en búsqueda:
registrar como fuente, no endurecer en silencio o afirmar incidenteproducción.
Legacyterritorial/territorial_editar avisa/redirige a Relevamientos; resto retornaficha.
No placeholders para sustituir esos recorridos ni sumisión mutación a rutaGETnueva.

DetailViewSet Token/PWA no es contrato de autorización sesión web equivalente.
Admisión/validación/convenio, relevamientos, historial, imágenes/mapa y asignacióndupla
son consumidores/dependencias M2 a concretar: hero no completa CO07.01.

## Evidencias futuras

Actoresporacción/ANYfrenteCRUD/scopeunión, NoCount/filtros, Forms+referente y
multipart/imágenes/reemplazo/errores, estados y proyectos dependientes, cancelación,
retornosfeedback, previewbaja y accesoindirectodupla. Mutacionesficha y contratos
dueños necesitan efectos comprobados, no solo HTTPredirect. Desktop/móvil/foco/
modales/errores y diffacumulado, sintéticos, ninguna ejecución.

## Fuente

src/backends/comedores/comedores/urls.py:70–143; views/comedor.py:1049–1064,
1172–1226,1370–1434,1715–1783; forms/comedor_form.py:380–489,657–764;
services/comedor_service/impl.py:496–571;
api_views.py:132–152,282. Vistascomedor/Form contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; otroscheckout. ExploraciónCodeGraphsync.

- [DU01 y acceso indirecto](2026-10-28-2785-duplas-equipo-asignaciones-m2.md).
- [Preview compartido](2026-10-28-2787-confirmacion-baja-logica.md).

## Suplemento CO07.01: filtros/export y admisión desde ficha

Listado GETfilters JSON avanzado y motor compartido con scope. Campos permitidos
nombre,estado,estado_general,estado_proceso,estado_detalle,estado_validacion,
codigo_de_proyecto,es_judicializado,categoria_espacio_comunitario,organizacion,
programa,tipocomedor,dupla,provincia,municipio,localidad,referente,referente_apellido,
calle,piso,departamento,manzana,lote,entre_calle_1,entre_calle_2,partido,barrio,
id,id_externo,comienzo,numero,codigo_postal,latitud,longitud,mes_ejecucion.
Textops contains/ncontains/eq/ne/empty; number eq/ne/gt/lt/empty; catálogoschoice,
no reducir todos a textlibre. NoCount y columnas se mantienen separados de totales.

ExportCSV listado_comedores.csv tiene barrerainterna además URL: superusuario o
ANY role_admin/role_administrador/role_superadmin admitidos; otros necesitan
ANYpermisolectura Y rolCSV. Comparte filters/scope, sort/direction y preferencias
comedores_list, nombreobligatoria. Columnas id,nombre,tipo,organizacion,programa,
dupla,estado_general,estado_actividad,estado_proceso,estado_detalle,provincia,
municipio,localidad,barrio,partido,calle,numero,ubicacion,direccion,referente,
referente_celular,validacion,fecha_validado. No trasladar solo decorador ni permiso
export-only como acceso genérico de cualquier actor.

POSTadmision resuelve comedorscoped y mantiene ANYlectura de ficha: servicio no
agrega AddAdmision o vetoactor. Reglas: nóminadirecta rechaza, tipovacío rechaza,
renovación necesita incorporaciónprevia de cualquierestado; incorporación rechaza
otra incorporaciónactiva; otras ramas máximocuatro renovacionesactivas. UI solo
incorporacion/renovacion, helper no whitelistotrosstrings acreditada. Preservar
contrato y caracterizar, no agregar permiso/tipo por intuición de «crear».

Éxito crea Admision(comedor,tipo,tipo_entidad_origen deorganización), mensaje y
retornoficha. Método conteo+creación sintransaction/lock acreditados: no exclusión
concurrente prometida. post_save crea historialinicial on_commit con actor/estado;
receptores completos requieren contratoAdmisiones. No incidenteruntime afirmado.
CapacidadDTO de iniciar distingue mutación de lectura, sin conceder permisos nuevos.

## Suplemento CO07.02: controles visibles y archivos

ControlesComedor renderizados: nombre,id_externo,tipocomedor,
categoria_espacio_comunitario,categoria_espacio_comunitario_otra,organizacion,
programa,proyecto,es_judicializado,es_caritas,estado_general,subestado,motivo,comienzo,
provincia,municipio,localidad,partido,barrio,codigo_postal,calle,numero,piso,
departamento,manzana,lote,entre_calle_1,entre_calle_2,latitud,longitud,foto_legajo.
Referente prefijoreferente: nombre,apellido,mail,celular,documento,funcion; opcionales
modelo, mail strip/Unicode/validación. No inferir requeridos de otroFormreferente.

Formbackend __all__ acepta más que visual: responsabletarjeta/referente/dupla/
estado_validacion entre otros. No exponerlos por serializarmodelo; DTO poracción
visible y preservaciónserver de relaciones noeditables. Edición repone duplaoriginal.
Whitelistweb no cambia por sí misma contratoslegacy/token; no retirar campos de
contrato externo existente sin análisis. Estado/proyectos se validan backend.

Provincia opciones por scopeterritorial, municipios provinciaseleccionada,
localidades municipio, querysets vacíos sinpadre. Reusar auxiliares existentes
ajax_load_municipios/localidades/organizaciones, organizacion_proyectos_ajax,
address_preview/map_pin_editor; concretar payloads/guards antes de UI.

Foto_legajo con preview/modal; imagenes múltiples; checkbox individual
imagen_ciudadano-borrar-<id>. Método borrarimagenes usaIDpost sin filtrocomedor
en rama inspeccionada: no inferir scope del querysetUI; comprobar callers antes de
concluir corrección/decisión. foto_legajo_borrar borra storage y limpia campo.
No suponer rollbackDB reviertebytes. URLs directas imágenes existentes: CDI-F2 no
se extiende a estas por analogía. Confirmar validación/serving en mapa siguiente.

Casosextra: ANYlectorcrear admisión dentro/fuera scope, nóminadirecta/renovaciones/
repetición/concurrencia; exportadmin/lector sinCSV/CSVsinlectura; PAC/bloqueoestados,
organizaciónproyectoajeno, referenteUnicode, fotografía/reemplazo/borrar/cancelar.
Efectos y capturas sintéticas pendientes, sin nuevos controles implementados.

Fuenteadicional checkout: services/filter_config/impl.py:13–114;
views/export.py:13–98,140–168; templates/comedor/comedor_detail.html:75–84,2065–2096;
templates/comedor/comedor_form.html:69–250,279–434,510–512;
forms/comedor_form.py:30–60,492–541; models.py:50–64;
services/comedor_service/impl.py:481–571,681–725,830–874,1965–1997;
src/backends/comedores/admisiones/signals.py:84–98. Serviceimpl contrastado con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; templates/export/filtros checkout solamente.
Padre contrastó reglasdominio admisión; CodeGraphsync, sin ejecución.
