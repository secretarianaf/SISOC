# CO01.02: alta de nómina, Ciudadano y perfil PNUD

E2: definición fuente, sin altas, consultas RENAPER o pruebas. Mismos recorridos
por admisión y directa, con sus guards; no es una escritura aislada de fila.
Asistencia mensual y documentos se concretan por separado de flags PNUD.

## Entrada y búsqueda

nomina_crear/nomina_directa_crear GET/POST AddNomina: comedor scoped, admisión
perteneciente o predicado de directa. Template nomina_form; éxito retorna listado
de nómina correspondiente, no siempre fichaCentro. Conservar ambas cadenas M2.

GETquery busca documento local. Sin identidad local validada, query numérico≥7
puede consultar RENAPER; registros pendientes no lo impiden. Contexto ciudadanos,
sinresultados, Form conDNI/sinDNI/complementario, modo, flags y actividadesPNUD.
Precarga no incorpora sola; mensajes del productor se conservan. No prueba
externa ni DNI real permitido en fixtures; integración futura simulada.

## Ciudadano seleccionado: omisión no significa false

POSTciudadano_id selecciona rama existente, no valida Form completo de identidad
nueva. Inexistente→mensaje/redirect; requiere_revision_manual→rechazo. Valida
NominaExtraForm y complementario(instance=ciudadano,prefix=modal); inválido conserva
Form y «Datos inválidos para agregar ciudadano a la nómina.».

Claves modal-pertenece_comunidad_indigena,modal-en_situacion_de_calle,
modal-persona_con_celiaquia. Ausente conserva valor existente y no fuerza validación
pertinente: no enviar defaultsFalse/null indiscriminados. Service revalida revisión/
duplicado, bloquea Ciudadano en transacción y crea Nómina. **Datos sociales cambian
Ciudadano global**, no snapshot del comedor. Error integridad mensaje dominio;
otras excepciones pueden incluir texto técnico actual, no afirmar sanitización.
No exigir todos los campos de alta nueva a esta rama de selección.

## Persona nueva con/sin DNI

Sin ciudadano_id: modo_creacion=sin_dni usa Form específico, resto estándar;
identidad+extra válidos, origen_dato=renaper se propaga como origen, no consulta
RENAPER nueva acreditada en ese guardado. Servicio crea Ciudadano, agrega Nómina;
si incorporación falla elimina al recién creado. No atomicidad mayor a la fuente
supuesto. Inválido conserva modo/campos y vuelve a pantalla; no POSTretry automático.

FormconDNI apellido,nombre,fecha_nacimiento,tipo_documento,documento,sexo y tres
flags sociales. Requeridos y choices de identidad heredados del modelo Ciudadano
requieren esquema dirigido, no inferir un formulario universal por esta lista.
FormsinDNI apellido,nombre,fecha_nacimiento,sexo,motivo_sin_dni,
motivo_sin_dni_descripcion y flags; exige motivo y fija registroSIN_DNI,
tipo_documentoDNI,documentoNone. Revisiónmanual se omite solo para verdadero SIN_DNI,
no bypass general. Duplicado de nómina rechaza; duplicado documental estándar
puede devolver «Ya existe un ciudadano estandar con este tipo y numero de documento.».
No dedup universal para personas sin DNI ni idempotencia del formulario.

## Configuración PNUD y efectos sucesivos

NominaForm estado/observaciones. Extra asistencia_alimentaria opcional initialTrue,
asistencia_actividades opcional, actividad_ids múltiple de actividadesactivas del
comedor. NoPNUD elimina esos tres campos. PNUD: seleccionar actividades fuerza
flagactividades;≥1flag entre alimentaria/actividades; flagactividades requiere≥1ID.

Tras incorporación, vista localiza nómina creada y sincroniza NominaEspacioPWA:
get_or_create, flags/activoTrue/fecha_bajaNone/actor; inscripciones y auditoría
nomina_perfil/origenweb_nomina. No registra asistencia de un mes. Pasos sucesivos
sin transacción exterior acreditada, no prometer rollback completo ante fallo de
sync ni ejecutarlo como segunda escritura cliente. No heredar topes PWA de otro
entrypoint create_nomina_persona automáticamente.

## Baja directa y asistencia: fronteras

NominaDirectaDeleteView filtra comedor directo scoped, hijo de ese comedor y
admisionNULL, no helperuniónAJAX. Preview/softdelete y «Registro de nómina dado de
baja correctamente.»→nomina_directa_ver. No borra nómina por admisión por coincidenciaID.

Escrituras de asistencia ubicadas en PWA: registrar_asistencia y
registrar_asistencia_alimentaria; lecturas historial/periodos/asistencia_periodo.
Documento mensual por generar_nomina_destinatarios_pdf y último porperiodo. Rutas,
DTO/predicados/versionado requieren mapa siguiente. No crear escritura web o upload
porque historial tenga un enlace; distinguir productor externo existente.

## Casos futuros

Local validado/pendiente+RENAPER/sinresultados/fallo, seleccionado inexistente/
pendiente, Form distinto, omisión social frente a cambio global, duplicado local/
concurrente, sinDNI/motivo; PNUDflags/actividadesajenas-inactivas, syncfallida tras
alta; comedor/admisiónajenos y baja directa con admisión noNULL. Formularios,
precarga/modal/errores/mensajes/retornos desktop-móvil/foco, paresreferencia-candidato-
diff y acumulado, sintéticos. Ningún efecto o captura ejecutado.

## Fuente

src/backends/comedores/comedores/views/nomina.py:113–147,298–526,688–907;
forms/comedor_form.py:63–224;
services/comedor_service/impl.py:1666–1776;
src/backends/comedores/pwa/services/nomina_service.py:550–610;
pwa/api_views.py:1064–1165; services/nomina_destinatarios_pdf_service.py:351–378.
Vistanómina/serviceprincipal ya contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa;
PWA/Formauxiliarcheckout, no comparación individual nueva. Padre contrastó flags
omitidos. CodeGraphsync; sin ejecución o conectores.

- [Estados, derivación y copia](2026-10-28-2785-comedores-nomina-estados-derivacion.md).
- [Ficha](2026-10-28-2785-comedores-legajo-base-m2.md).
