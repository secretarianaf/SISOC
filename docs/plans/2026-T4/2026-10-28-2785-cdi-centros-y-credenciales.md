# CDI09 y dependencia CDI01: centros, provisión y credenciales

E2: planificación estática, sin implementación o evidencia runtime. CDI09.01
Listado ficha y catálogos / CDI09.02 Gestión de centro y catálogos conservan IDs.
Generación/estado de usuarios depende CDI01; no ampliar D1/CR1 CDF implícitamente.

## Rutas y política existente

centrodeinfancia listado/view; _crear/add; _detalle/view; _editar/change;
_eliminar/delete. _ajax, _ajax_load_departamentos_ipi y _renaper_bloque tienen
reglas propias, no permisos derivados de menú. Ficha/edición/baja queryset con scope
CDI: objeto fuera404. Mutaciones además Auditoría solo lectura, permite GET/HEAD/
OPTIONS pero no escritura. No trasladar D1 CDF como relajación de controles CDI.

Listado10/página, busqueda nombre/organización, orden nombre; filtros avanzados y
columnas personalizables, nombre obligatoria/default nombre-organización-nómina-
geografía. Alta/edición retornan ficha; baja lógica listado y «Centro de Desarrollo
Infantil dado de baja correctamente.». Activación M2 incluye operaciones y feedback.

## Formulario, validación y efectos

CentroDeInfanciaForm campos nombre,organizacion,cuit_organizacion_gestiona,ambito,
provincia,departamento,municipio,localidad,codigo_postal,calle,numero,latitud,longitud,
telefono,mail,meses_funcionamiento,dias_funcionamiento,tipo_jornada,tipo_jornada_otra,
oferta_servicios,modalidad_gestion,modalidad_gestion_otra,nombre_referente,
apellido_referente,email_referente,telefono_referente,dni_referente,cuil_referente,
fecha_inicio; horarios por día y decil_ipi derivado/deshabilitado.

Requeridos se toman de CAMPOS_OBLIGATORIOS, no blank del modelo: CUIL referente
obligatorio solo alta; coordenadas/horarios/DNI y «otra» con reglas específicas.
Fecha_inicio en UI es añoAAAA,1900–actual, compatible enero1 al guardar; no datepicker.
Meses/días/oferta múltiples. Provincia actor puede estar bloqueada si no nacional.
Coordenadas opcionales lat -55..-21/lon -74..-53, no validación CDF±90/180.
Jornada/gestión no otra limpian campo otra; horario día seleccionado, ambos extremos
o ninguno, cierre posterior. Guardado elimina horarios de días deseleccionados y
upsert restantes. Duplicado combina organismo/referente, no solo nombre.
CUIT/CUIL/teléfono/mail/número requieren completar traslado fiel de validadores
forms.py:500–663: no declarar schema DTO final por enumerar campos.

Guardar centro también actualiza referente: sin usuarios crea responsable; cambio
de persona crea/vincula nueva cuenta y anterior conserva cuenta/acceso, pierde
responsabilidad. Identidad por DNI, no email institucional compartido. Misma persona
email solo sincroniza cuenta temporal; cuenta ya modificada recibe warning sin
reemplazo. Fallo de provisión no deshace guardado CDI: conservar éxito parcial y
warning, no reintentar centro entero para reenviar credenciales. Email simulado futuro.

## RENAPER y ficha

Bloque/DNI valida auditor, rate-limit por usuario y log DNI enmascarado;400/429;
éxito success/message/valores/token. Token firmado usuario+valores,1hora; Form usa
token no POST alterado. Expiración vuelve carga manual según fuente. Identidad
verificada bloquea nombre/apellido/DNI/CUIL, no teléfono/email. No almacenar token
en persistencia/contexto global ni confiar en boolean cliente. Integración simulada.

Ficha: flags nómina/asistencia/formularios/intervenciones; nómina10 nomina_page,
intervenciones10 intervenciones_page, observaciones5 observaciones_page; métricas
sexoM/F/X/espera/menores globales. Horarios/info, Form observación y condicional de
intervención, trabajadores, tres formularios recientes y permisos, usuarios.
Bloques y acciones enlazan CDI02–07/CDI01: hero no completa CDI09.01; coordinar
activación sin convertir todo CDI en una sola tarea. No app CDI React/APIcentros web
identificada; public_api/ticketera no prueban equivalencia ABM/ficha.

## Decisión resuelta: CDI-CR1 elegida, CDI-CR2 descartada

La ficha muestra usuarios bajo predicados CDI y aplica autorización de credencial
por fila: superusuario o cuenta propia, aun si responsable administra otras.
GenerarUsuarioCDIView retorna página POST con username/email/temporal/estadoemail/
generarotro. Responsable genera solo en su CDI sin delegación global; DNI/CUIL,
RENAPER, bloqueo al vincular/responsabilidad y username porDNI si email compartido
son diferencias que no se sustituyen por reglas CDF.

| Alternativa | Beneficio | Costo/riesgo |
|---|---|---|
| CDI-CR1 — Extender patrón privado mínimo a CDI (recomendación) | Conservar pantallas actuales mediante resultado de generación separado y lectura restringida por actor/fila CDI; mismas protecciones CR1 contra fuga, no-store, sin User/Profile completos, logs, URLs, contexto global o storage/caché persistente cliente | Nuevo transporte sensible exige pruebas propias CDI y no elimina exposición backend/pantalla. No reutilizar matriz CDF ni ampliar permiso por administrar usuarios |
| CDI-CR2 — No exhibir temporal en React | Reduce transporte/exhibición de secreto en nueva UI | Cambia diseño/operación, requiere definir entrega alternativa y caso de fallo email antes de activar |

CR1 fue aceptada para CDF, no como aprobación general de contratos de secretos.
El responsable eligió «cdi-cr1» el 2026-10-28: se extiende el patrón, no las reglas
de autorización, datos ni persistencia compartida. Solo planificación; implementación sigue fuera de E2.

## Casos futuros y límites

Scope nacional/provincial/referente/auditor; columnas/filtros/paginaciones separadas;
año/múltiples/horarios eliminados/coordenadas/duplicado; flags/vacíos; RENAPER fallo/
429/tokenajeno-expirado-manipulado; centro guardado con provisión/email fallidos;
cambio responsable conserva acceso anterior; credenciales por actor/fila. Cada
URL/estado desktop/móvil, foco/teclado, mensajes/retornos y diff acumulado. Sintéticos,
ninguno ejecutado; no probar RENAPER/email con datos reales.

## Fuente

Prefijo src/backends/cdi/centrodeinfancia/: urls.py:66–161;
views.py:302–374,377–498,501–932,1364–1418;
forms.py:192–318,500–749; access.py; views_usuario_cdi.py:110–168;
services_user_provisioning.py:171–202,266–281,333–369;
services_renaper_bloques.py:1–21;
templates/centrodeinfancia/centrodeinfancia_detail.html:402–406.
URLs/views/Forms/access/views_usuario/provisioning contrastados por explorador con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; templates/RENAPER son checkout inspeccionado.
Padre contrastó filtrado panel y respuesta POST de credenciales. CodeGraph sync,
sin app, DB, navegador, capturas, tests, commit/push o deploy. Sin cambio GitHub.

- [Catálogo](2026-10-27-2785-entregas-por-flujo.json).
- [CR1 CDF, alcance original](../../registro/decisiones/2026-10-28-2785-cdf-credenciales-cr1.md).

Registro: [CDI-CR1 aceptada](../../registro/decisiones/2026-10-28-2785-cdi-credenciales-cr1.md).
