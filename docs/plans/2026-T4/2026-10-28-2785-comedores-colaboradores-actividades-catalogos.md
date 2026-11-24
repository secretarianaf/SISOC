# CO03/CO04: colaboradores, horarios y catálogos

E2: cuatro circuitos de preparación, sin runtime, usuario real, RENAPER o capturas.
CO03.01 Colaboradores/actividades, CO03.02 Gestión/vigencia; CO04.01 consulta,
CO04.02 catálogosautorizados. Revisióncertificado ya está en contratoembebido.

## Colaborador no es usuario de acceso

Crear/editar/baja comedores/<pk>/colaboradores, Add/Change/DeleteColaboradorEspacio
propios, login/scopedcomedor, edición hijoactual y sinbaja. Baja soloPOST comprueba
pertenencia y admiteyaBaja; alta excluyesecos, no extrapolar ese veto a editar/baja.
Alta búsqueda query/dni o ciudadano_id→preview→guardar. LocalporDNI, si no RENAPER;
numérico≥7, duplicadocolaboración detectado. POSTrequiere ciudadano_id o DNI,
servicio creaCiudadano si procede y colaboración, messages→ficha. No Formmanual
libre/API JSON existente ni User/PWAaccess generado por asociar persona.

Form genero,codigo_telefono,numero_telefono,fecha_alta,fecha_baja,actividades.
Altafecha requerida/bajafecha opcional YYYY-MM-DD; actividades checkboxmúltiple
requerido catálogoactivo ordenorden,id; teléfonos opcionales strip/dígitos.
Bajaantesalta errorcampo. GuardadoCiudadano-relación/M2M, actormodificador y auditoría
snapshot. Baja fechaactual o altafutura para no invertir, repetidabaja éxito sin
nuevamutaciónprincipal. Ediciónrechazabaja, no borraCiudadano ni crea/grantusuario.

## Actividades de espacio: múltiples horarios son múltiples registros

actividad_espacio_pwa_crear/editar GET/POST, ANYrole_admin/pwa.manage_colaboradores_pwa
más mixin, comedor scoped+is_pnud_comedor, objeto hijo delcomedor al editar.
Form catalogo_actividad,responsable_actividad,vigencia_actividad_meses y categoria
auxiliar (backendoptional porcompatibilidad, widgetrequired). Arraysrepetidos
schedule_dia_actividad/schedule_hora_inicio/schedule_hora_fin. Catálogoactivo o
selecciónhistórica, categoríasderivadas y Dia porID. Vigenciapresente≥1,≥1horario,
díaválido, HH:MM/finposterior, dedupidénticos, rechaza crucesinternos y con misma
actividadexistentecomedor.

Alta atómica crea1registro/horario; editar actualizaprimero y creaextra. No cambiar
entidadpersistida a array por conveniencia UI. ServicioPWA compartido creaactor/
actualizador/auditoría y mensajes distinguencantidad/actualizaciónadicionales.
Retorno comedor_detalle#legajo-actividades-pnud. Sinbajaweb en esasrutas, no añadir
por existir helperPWA. Sinfiles/email, no separar persistencia en Nsubmits de cliente.

## Cursos catálogo global

cursos_app_mobile_list/crear/editar/eliminar, login+role_admin,20/página global.
Form nombre,link,imagen,descripcion,programa_objetivo,es_recomendado,orden,activo.
Nombre requerido255, linkURLrequerido500, programa pnud/alimentar_comunidad/ambos;
descripciónopcional300/imagenopcional, PositiveIntegerorden default0/recomendadoFalse/
activoTrue. Uploadcomedores/cursos_app_mobile/. Alta/editar transacciónactor,
messages→lista. Baja confirmaciónpreview/softdelete, no activoFalse equivalente.
Imagen/linkconsumidosApp, no conexión externa probada. ConstanteIMAGE_SIZE96x96 no
prueba transformación física sin leer save; mantener pendiente ese productor.

## Catálogo PNUD global

Lista admin o View/Managecatálogo, mutaciones admin o pwa.manage_catalogoactividadpwa.
50/página ordencategoria,actividad,id; estadoactivaDefault/inactivaFalse/otro sinfiltro;
q categoríayactividad. Form categoria,actividad,activo + categoria_modo existente/nueva
hiddenrequired initialexistente, categoria_existente/nueva. Opcionesdistinct,
strip/noempty categoría y actividad. Alta/editar mensajes→lista. BajaGETconfirmación,
POSTactivoFalse+fecha, yainactiva aviso; no softdelete/borrarrelacioneshistóricas.
Actividadselector conserva actualinactiva, no perderhorarios por desactivacióncatálogo.

## Casos sintéticos pendientes

Comedor/hijoajeno, altaSecosfrenteedit, local/RENAPER/fallo/duplicado, teléfono/fechas,
altafutura/bajarepetida/M2Mautoría. Horariosuno-varios/duplicados/cruces/vigencia/
selecciónhistórica, ediciónextraatomic. Viewcatálogo-sinManage, filtroestado/orden/
columnas, imágenesinválidas/link/programa, desactivaciónconhistóricos/softdeletecurso.
Pantallaslista/ficha/Form/modalpreview/error/filashorario conservadas/confirmación,
retornosmessages/hash/foco/teclado desktop-móvil y diffreferencia/candidato/acumulado.
No evidencia runtime, email/API/PWAexterna o capturas ejecutadas.

## Fuente y brechas

src/backends/comedores/comedores/urls.py:162–194,253–309;
views/colaborador.py:22–234; forms/comedor_form.py:227–288;
services/colaborador_espacio_service/impl.py:152–287;
views/actividad_espacio_pwa.py:19–119; forms/actividad_espacio_pwa_form.py:19–208;
src/backends/comedores/pwa/services/actividades_service.py:38–93;
src/backends/comedores/comedores/views/cursos_app_mobile.py:13–73;
forms/cursos_app_mobile_form.py:6–39; models.py:1082–1106;
views/actividades_pnud.py:13–132; forms/actividades_pnud_form.py:6–78.
Vistascolaborador/actividad/cursos/PNUD y Formactividad contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; otroscheckout. Padre contrastó altahorarios.
ResultadoRENAPER/duplicados, saveimagencurso y rutasconsumidorasPWA siguen por
profundizar antes de cerrarcompatibilidad. CodeGraphsync, sin ejecuciones.

- [Contribuciones/revisióncertificado](2026-10-28-2785-comedores-dw-mes-capacitaciones.md).
- [Ficha](2026-10-28-2785-comedores-legajo-base-m2.md).
