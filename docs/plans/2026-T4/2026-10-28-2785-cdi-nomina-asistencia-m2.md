# CDI04/CDI02: nómina, derivación y asistencia

E2: contrato fuente de preparación, sin implementación/fixtures/capturas. IDs
CDI04.01 Nómina/detalle, CDI04.02 Gestión nómina, CDI04.03 Derivación/estados;
CDI02.01 Consulta asistencia, CDI02.02 Carga/corrección. No copiar reglas CDF.

## Nómina: rutas, acceso y retorno

centrodeinfancia_nomina_ver:100/página/view_nominacentroinfancia;
_nomina_formulario_ver mismo permiso; _nomina_destinatario_ver por nomina_id usa
view_centrodeinfancia. Crear add_nomina; editar/editar_ajax change_nomina;
derivar change_nomina Y add_nomina; borrar delete_nomina. Scope y nested centro_id
se verifican, no solo PK. Altas/edición/baja regresan a centrodeinfancia_nomina_ver;
ficha centro es consumidor indirecto. M2 exige lista/feedback y operaciones React.

Form completo NominaCentroInfanciaDestinatariosForm incluye identificación niño,
documentación, trabajador/registro, salud/nutrición/desarrollo/discapacidad/CUD/
cobertura, geografía, responsables1/2/identidades/vínculos/consentimientos/beneficios,
adulto responsable, convivencia/lenguajes/ANSES/sala/estado/observaciones.
Meta modifica campos heredados: extracción exacta sigue pendiente para DTO final.
No usar Form pequeño NominaCentroInfanciaForm de AJAX como schema del completo.

Alta conserva búsqueda/selección Ciudadano, precarga local/RENAPER y Formbound.
Formulario visible con seleccionado/noresultados/formenviado. Token prefill15min
usuario+centro; tokens por bloque mantienen semántica propia; token niño incompatible
con seleccionado se descarta. Inválido «Hay errores en la ficha de la nómina.»
misma pantalla. Ciudadano inexistente/DNI diferente rechaza, no crea otra persona.
POST alta nueva puede consultar RENAPER antes de transacción, reconsulta local y
crea/vincula atomic. Tests futuros simulan integración, no llamadas con datos reales.

Crear bajo bloqueo preserva única vigencia/ciudadano; vigente otro centro error;
mismo centro duplicado warning/retorno; éxito «Ficha creada y agregada a la nómina.».
Excepción amplia «No se pudo guardar la ficha en la nómina.», conserva Form. No
reintentar automáticamente para recuperar resultado incierto de mutación.

Edición completa no cambia DNI del niño vinculado por RENAPER, revalida reactivación
atomic. Baja softdelete, «Registro de nómina dado de baja correctamente.».
AJAXlegacy GET HTML, POST otro Form, éxito/error ambos200 JSON success/errors o
success/message «Datos modificados con éxito.». React requiere DTO sin inyectar
HTML ni asumir422 obligatorio por ser Form inválido.

## Derivación: operación de dominio

SoloPOST, destino entero/motivo trim, JSON éxito200/error400. Origen Activo;
destino distinto y en scope; sin vigente destino/tercercentro. Atomic bloquea
Ciudadano/nómina y revalida; origen Baja, crea destino Pendiente, copia campos
permitidos e historial actor/motivo/origen/destino. No mover FK ni activar destino
por conveniencia. Repetición origen Baja rechaza, no idempotencykey inventada.
Mensaje «Derivación realizada correctamente.» y conflictos propios del servicio.

## Asistencia CDI: conservar diferencias de dominio

centrodeinfancia_nomina_asistencia/_calendario y alias _trabajadores_asistencia
requieren change_centrodeinfancia. Alias conserva query hacia nómina, no pantalla
nueva de asistencia trabajadores. FechaAAAA-MM-DD, defaulthoy; parser no rechaza
futuro. Calendario mesAAAA-MM, GET {dias:[ISO...]}, inválido400detail.

Filas activas más Baja con registro de asistencia de esa fecha, sin softdeleted;
orden apellido/nombre/pk. Métricas True/False/None, observación por fila y datos
identidad con fallbackCiudadano. No filtrar solo activos ni reutilizar regla CDF.
POST fecha, presente_<pk> 0/1/ausente, obs_<pk> strip/None. Marca inválida rechaza
antes de escribir. Atomic crea/actualiza con actor/observación; sin marca elimina
registro existente, no se convierte a Ausente como CDF.

GETfecha inválida mensaje/planilla hoy; POSTerror redirige sinfecha; éxito
«Asistencia registrada correctamente.» y misma ruta ?fecha=ISO. Calendario/planilla/
feedback/retorno completos React, no confundir catálogo global con datos del mes.

## Auditoría: evidencia pendiente, no cambio aprobado

Alta/edición/baja tienen _AuditoriaSoloLecturaMixin y AJAX control explícito;
asistencia/derivación no muestran ese guard en ramas inspeccionadas. Conservan
permisoURL/scope. Verificar IAM y combinaciones de permisos antes de concluir que
existe acceso indebido; D1 CDF no se extiende. No agregar guard ni afirmar bypass
explotable o pedir excepción sin ese contraste mínimo.

## Casos futuros

Búsqueda/selección/sinresultados/Formerror, identidad/tokenajeno-expirado-manipulado,
duplicado mismo/otrocentro, fallo RENAPER, permisos poracción/nestedIDajeno,
lista100/totalesglobales, editar ambas interfaces, softdelete y mensajes/retornos.
Derivar estados/destinoigual-ajeno-vigentetercero/repetición/concurrencia: verificar
origenBaja+destinoPendiente+historial, no solo HTTP200.
Asistencia activos/Baja histórica/espera/softdeleted, Noneborra/0ausente/1presente,
inválido sin escritura, futura/fechamesmalformados, observaciones, aliasquery.
Por URL/estado/rol: sintéticos, desktop/móvil/foco/teclado, referencia/candidato/diff
y acumulado. Sin ejecución ni evidencia de persistencia/runtime/aceptación.

## Fuente

Prefijo src/backends/cdi/centrodeinfancia/: urls.py:164–269;
forms.py:881–1315,1385–1999; views.py:1578–1634,1637–2198,2399–2521;
services.py:185–301,342–420. Estos cuatro archivos contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa por explorador; padre contrastó borrado
asistencia sinmarca. CodeGraph sincronizado. No app/tests/DB/navegador/remote.

- [Centros, provisión y credenciales CDI](2026-10-28-2785-cdi-centros-y-credenciales.md).
- [Catálogo de entregas](2026-10-27-2785-entregas-por-flujo.json).

## Contraste posterior: auditor y Form completo

La combinación Auditoría+EGP conserva es_auditor_simepi=True y suma permisos
suficientes por seed; IAM revisado no aplica veto superior. [CDI-A1/CDI-A2](2026-10-28-2785-cdi-auditoria-a1-a2.md)
quedó resuelta: CDI-A2 elegida, corrección coordinada de los dos POST según
predicado actual, sin quitar permisos de grupos ni cambiar excepciones. No se
afirma explotación runtime o mitigación; E2 no autoriza implementar. No extender D1.

Extracción AST estática Form: Meta efectiva87campos, pero no87controles: init
elimina campos y agrega vacunas dinámicas vacuna_<code>_dosis/_fecha desde
vacunacion_nomivac. Trabajador limitado al centro, sincentro queryset none.
Declarados extra/heredados y eliminaciones impiden llamar listo el DTO; pendientes
concretos campos eliminados/requeridos finales/catálogos. No importar Django para
inferirlos bajo E2 ni completar por nombres/modelo.
Reglas adicionales: exclusiones en grupos/lenguajes/discapacidad/alergias, documentos/
CUIT/teléfonos, antropometría, fechas/registro, condiciones discapacidad/CUD, vacunas
JSON y valores verificados RENAPER. Fuente forms.py:1488–1556,1737–1999.

[Extracción posterior de campos eliminados y requerimientos](2026-10-28-2785-cdi-formularios-trabajadores-m2.md)
resuelve nombres CAMPOS_OCULTOS; Meta87 no equivale a controles finales. Catálogos,
vacunas y esquema final siguen explícitamente pendientes, no hipótesis completas.
