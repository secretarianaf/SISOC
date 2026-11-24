# CO01: consulta, estados, derivación y copia de nómina

E2: primer grupo de contratos CO01, sin ejecución o familia completamente lista.
IDs CO01.01 Nómina y registro asistencia; CO01.02 Gestión; CO01.03 Carga/corrección.
Alta/Ciudadano/PNUD y escritura/documentos de asistencia requieren siguiente mapa.

## Dos modos, un modelo

Nomina por admision utiliza admision.comedor; directa comedor con admisionNULL.
Objeto autorizado por cualquiera de ambas relaciones y comedores scoped. Directa
además exige predicado no usa_admision_para_nomina; no decidir modo por comentario
«programas3/4», usar configuración ejecutable. Admisión debe pertenecer al comedor.

Rutas login: nomina_ver/asistencia_historial ViewNomina; nomina_crear Add;
nomina_borrar Delete; nomina_importar POST Add; nomina_directa_ver/crear/borrar
View/Add/Delete; nomina_editar_ajax Change; nomina_cambiar_estado POST Change;
nomina_derivar POST Change Y Add. Códigos comedores.*. AJAX de objeto es compartido,
no exclusivo de admisión por aparecer en esa lista.

## Consulta y modificaciones

Ambas consultas usan nomina_detail, GETpage/dni/tab. PNUD pestañas alimentaria/
actividades/todas, otros todas. Contexto filas/métricas M/F/X/espera/activos/menores/
rangos/estados/destinos/labels; directa admision_pkNone. Page int directo en vista,
no saneamiento uniforme supuesto. No calcular métricas globales desde páginaUI.

AJAX GET fragmentoHTML, POST NominaForm(estado,observaciones): requerido choice
Nomina.ESTADO_CHOICES. Éxito200 successTrue/message «Datos modificados con éxito.»;
inválido200 successFalse/errors, no GETJSON existente ni422 genérico impuesto.
React necesita proyección de Form y errores propia, no inyecciónHTML.

Cambioestado POST choice válido, inválido400/otro método405, guarda soloestado,
successTrue/estado. No FIFO/cupo/egreso adicional ni implementar #142 por implicación.
Baja poradmisión scoped porhijo/admisión/comedor/actor, preview y softdelete,
«Registro de nómina dado de baja correctamente.»→nomina_ver. EstadoBaja no es
softdelete. Queryset exacto de baja directa aún requiere contraste antes de cierre.

## Derivación: Baja origen, Espera destino

POST centro_destino_id entero y motivo opcionalstrip; scopedorigen, errorformato400,
service success/message200o400. Opciones destinos scoped/excluyeorigen; si usa
admisión requiere alguna activa. Service: origenActivo/concomedor, destinodistinto/
scoped, últimaadmisiónactiva por mayorID o relacióncomedor directa; sinpersona
Activa/Espera en destino.

Atomic bloquea origen/revalida, origenBaja, crea destinoEspera mismoCiudadano,
NominaDerivacion actor/motivo/relaciones. No mueve/duplica Ciudadano ni copia
observaciones/actividades/asistencias no acreditadas. Lockorigen no garantiza
exclusión de carreras en todos los destinos; no idempotencykey nueva supuesta.
Error registrado y traducido a dominio, no traceback al cliente.

## Importar no es subir archivo

POST copia convenio anterior→admisiónactual scoped. «Anterior»=mayorIDinferior con
alguna nómina, no fecha/últimaactiva. Toma ciudadanos, omite ya presentes destino,
crea filas nuevas Activo con bulk_create. No conserva estado/observaciones/
actividades/asistencias del origen. Sinorigen warning; «Se importaron N personas
a la nómina.»→nomina_ver. Repeticiónsecuencial puede importar0; no idempotencia
concurrente o normalización de duplicadosfuente demostrada por setdestino.

## Historial de asistencia: frontera de lectura

RegistroAsistenciaNominaPWA mensual, filtra admisión o comedor directo y excluye
softdeleted. Agrupa periodos, GETperiodo selecciona asistentes con nombres/sexo/
tomador; último documento de nómina porperiodo. No formulario web de escritura
acreditado por ese historial. Alta PNUD sincroniza alimentaria/actividades vía
servicio compartido: pendiente contrato, no flags inventados cliente.

## Casos futuros

Persona/admisión/directa, objeto/hijoajeno, estados inválidos, GETHTML frentePOSTJSON
200inválido, sin efecto extra de cupo; derivación origen/destino/admisiónactiva/
duplicado/estados/historial/repetición/concurrencia; copia porID, repetida0,
Baja frente softdelete. Listas/tab/métricas/modales/filtros/feedback/retornos,
referencia/candidato/diff desktop/móvil/foco/acumulado. Sintéticos, no ejecución.

## Fuente

src/backends/comedores/comedores/urls.py:346–414;
views/nomina.py:43–89,122–271,529–685;
forms/comedor_form.py:63–74;
services/comedor_service/impl.py:1779–1962.
Vistanómina contrastada con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
servicioprincipal comparado antes, Formscheckout. Padre contrastó cambioestado.
CodeGraphsync, sin DB/RENAPER/app/tests/browser/remote o aceptación.

- [FichaComedor](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Bajas y preview](2026-10-28-2787-confirmacion-baja-logica.md).
