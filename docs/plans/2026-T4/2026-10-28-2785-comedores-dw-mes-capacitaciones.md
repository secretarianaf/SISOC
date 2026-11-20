# CO07/CO04: contribuciones DW, mes de ejecución y revisión de certificados

E2: contrato fuente sin conexiones DW/app/DB/worker/proveedor/tests. Son lecturas
con efectos especificados y una acción inline existente, no nuevos controles de
edición. C2 se mantiene solo360; no cambia política de fallosDW por analogía.

## DW: resumen y histórico CO07.01

Ficha consulta solo ViewComedor, aunque otros permisos permitan entrar. Histórico
comedor_transacciones_detalle GET comedores/<pk>/transacciones, login+ViewComedor,
objeto scopedporservicio. DWTransaccionesService cursorDjango SQLparametrizado en
DW_sisoc.vw_EC_resumen_transacciones, no endpointHTTP nuevo. Campos comedor_id_sisoc,
periodo,cantidad_debitos,credito_total,debito_total,cereo. Resumen periodoDESC/LIMIT1;
histórico COUNT/LIMIT/OFFSET. No credencial o configuraciónDW se lee/guarda en plan.

PeriodoYYYYMM→YYYY-MM. **Transferido=debito_total, Gastado=credito_total**, no
invertir por nombre intuitivo; Saldo=cereo. $/milespunto/sindecimales, null→«Sin
información». Excepción registrada→None o [],0 igual ausencia, no fallo tipadoReact:
conservar UI sin indicador nuevocaído/éxito falso. Pruebas caracterizan causa por
separado aunque displayigual, sin inferir interoperabilidad de mocks.

Page entero inválido→1;1000/página. Servicio recibepage antes Paginator.get_page,
negativos/fuera pueden dar datos/pager no equivalentes; no normalizar sin baseline.
Contexto transacciones/page_obj/total_count/es_ultima_pagina. Sin filtroperiodo,
POST o export identificado: no inventarlos. Enlace desde tarjeta/histórico/retorno
completosReact, proyecciónweb nueva del dueño, no API ya existente declarada.

## Mes de ejecución: tarjeta de lectura, no input

Programa_id2 solo; otros mostrar_mes_ejecucionFalse/resumennull. Resumen último
expediente porperiodo y mespersistido; prestaciones suma desayuno/almuerzo/merienda/
cena; montototal expediente.total si no null, sino sumamontos. Tarjeta expediente
convenio/pago/mes/año/monto/prestaciones/mes_ejecucion enlaza expedientespagos_list.
ComedorForm excluye mes_ejecucion, no editorReact por existir columna en listado.

Escribe ImportarExpediente: presente→mesconvenio; ausente puede quedar -ausencias;
inactividad/≥3ausencias→null y transiciónestado. Actualiza si cambia. Valoresnegativos
no se reinterpretan mesinválido ni null→0; APIterritorial readonlynullable mantiene
contrato. No recalcular importación en cliente/ficha ni nueva familia «mes».

## Certificados de capacitación CO04

CO04.01 consulta/CO04.02 gestión de catálogos existentes incluyen definición de
capacitacion_certificado_estado_ajax, acción embebidaficha; aclarar dependencia
sin cambiarIDs. POST comedores/<pk>/capacitaciones/<certificado_id>/estado,
ChangeComedor+scopecomedor+certificadodelcomedor. Otros métodos405successFalse/error.
Body form-urlencoded estado/observacion, CSRF. Error400 successFalse/error dict-list-
string;200successTrue/item. No djangoForm independiente, editorinline debe serReact.

Destinos rechazado/aceptado/sin presentar. Final aceptado/rechazado no cambia a otro;
repetir mismo actualizafecha/actor. Rechazar observaciónstrip requerida; aceptar
limpiaobservación. Sinpresentar limpia referenciarchivo/presentador/fechapresentación,
conserva registro y revisor/fecha; no storage.delete acreditado. No verificación
archivoexistente en review_certificate, no agregar correo/upload a estePOST.

Serializer identidad/etiqueta + estado/estado_label/archivo_url/archivo_nombre/origen/
intervencion_id/fecha_origen/observacion/fecha_presentacion/fecha_revision/
presentado_por/revisado_por. Archivo propio o intervenciónlegacy, no solo carganueva.
Listar llama ensure que crea registros faltantes sinpresentar y enlaza legacy:
GETficha puede materializar, no lectura pura declarada. EstadoReact no replica
calendarios/actualización servidor ni efectosglobales de otrodominio.

Tabla y editorrechazo filahija actualizan porrespuesta sin abandonar ficha; conservar
visual/foco/error/CSRF y condicionesbotón calculadas servidor, no inyectar HTML.

## Casos y límites

DW sinpermiso no consulta, objetoajeno, periodo/montos/null, vacío/fallo con UIigual,
pageinválida-negativa-fuera, ida/vuelta; no conectividadDW acreditada. Mes programa2/
otro/sinexpediente/totalnull/negativonull, sininput accidental. Certificadoajeno,
sinpermiso/GET405/estadodesconocido/rechazovacío/finalinmutable/repetido/reset,
legacyfile/errorheterogéneo/creaciónlectura. Desktop/móvil/teclado/foco, tabla/fila
hija/tarjetas/mensajes/retornos con paresreferencia-candidato-diff y acumulado,
fixtures sintéticas, todo pendiente. Intervenciones/observaciones/colaboradores/
nómina/certificadouploadmóvil siguen familias propias, ficha completa no cerrada.

## Fuente

src/backends/comedores/comedores/views/comedor.py:1003–1044,1617–1624,1786–1824;
urls.py:145–152,471–476;
services/dw_transacciones_service/impl.py:12–160;
templates/comedor/comedor_mes_ejecucion_card.html:10–35;
api_views_territorial.py:90;
src/backends/comedores/importarexpediente/services.py:619–623,658–725;
src/backends/comedores/comedores/views/capacitaciones.py:13–46;
services/capacitaciones_certificados_service.py:81–115,154–201,233–292;
templates/comedor/comedor_detail.html:2255–2320. ServicesDW/certificados e import
contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa; principalvista comparada
antes, auxiliares/templatescheckout. Padre contrastó formato Transferido/Gastado.
CodeGraphsync, sin llamadasexternas/config/DB/ejecución o CI/publicación.

- [Legajo y dependencias](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Validación/convenio](2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md).
