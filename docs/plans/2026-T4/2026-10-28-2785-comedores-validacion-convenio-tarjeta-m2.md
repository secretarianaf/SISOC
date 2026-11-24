# CO07.03: validación, convenio y responsable de tarjeta

E2: preparación fuente, sin implementación, esquema API generado o capturas.
Tres operaciones con guardas propias, no capacidad genérica ChangeComedor.
CO-I2 solo ownershipimágenes; otras decisiones no se amplían implícitamente.

## Validación/no validación

validar_comedor POST comedores/<pk>/validar, login+ANYlecturaficha+scopeobjeto.
Servicio requiere superusuario, role_validador_comedores o miembro técnicos de dupla
asignada. Abogado/coordinador no bastan. GET405; frontend recibe capacidad calculada
servidor, no replica conjunto de roles como autorización.

Inputs accion validar/no_validar, opciones multivalor para no, comentario defvacío,
nextPOSToGET safe_redirect/fallbackficha. Sin Form específico ni JSONfuente;
messages+redirect. Validar estadoValidado/opcionesnull «Comedor validado correctamente.».
NoValidar estadoNoValidado y≥1opción; «Debe seleccionar al menos una opción.»;
otro requiere comentariostrip. Accióninválida «Acción no válida.»; nocapacidad
«No tiene permisos para validar este comedor.». UIchoices limitadas, servicio no
whitelisttodoscódigos acreditada: documentar, no añadir por inferencia migración.

Opciones pac_inexistente_o_no_coincide,sin_movimiento,no_se_reconoce_el_comedor,
no_corresponde_a_la_dupla,otro. Atomic actualiza fecha_validado now y crea historial
actor/opciones/comentario. Repetir añade fecha/historial, no no-op/idempotencykey.
Historialdescfecha, display ignora desconocidos. Dosmodales condiciónpuede_validar:
primeroValidar/No, segundoopciones/comentario. Cancelar no muta, retornofichaM2.

## Convenio PNUD/Abordaje

comedor_convenio_pnud GET/POST, login+ChangeComedor; servicio detalle conactor y
aplicabilidad usa_datos_convenio_pnud. Noaplicable→«Esta opcion solo aplica para
comedores PNUD o Abordaje Comunitario.»/ficha. get_object get_or_create OneToOne:
GETpuede crear vacío, no lectura pura acreditada. POSTválido→ficha sin successcustom.
Precarga readonly organización/códigoproyecto/estados/nombre/idexterno/domicilio y
territorialesporproyecto/flagslinea, no campos editables ampliados por DTO.

CamposForm: monto_total_conveniado,monto_convenio_prestaciones_alimentarias,
monto_convenio_siph,nro_convenio,prestaciones_financiadas_mensuales,
prestaciones_financiadas_diarias_{desayuno,almuerzo,merienda,merienda_reforzada,cena},
personas_conveniadas,personas_declaradas_siph,cantidad_modulos,
aprobadas_{comida}_{lunes..domingo}35campos. Montos opcionalesDecimal14,2;
nro≤120opcional, cantidadesPositiveIntegeropcionales, matriz default0/min0 requerida.
No sumaobligatoria inventada entre montos o prestaciones.

Variantes: secos elimina mensuales+35aprobadas+5diarias; tradicional elimina
mensuales/cantidadmodulos; resto elimina5diarias+7meriendareforzada. Campos retirados
no se mandan/limpian en React: preservar valoreshistóricos, no convertir omitidoen0.
UI monto admite enteros/milespunto, rechaza decimal segúnmensajeexistente; si monto
visible redondeado no cambió, clean restaura inicial y conserva centavoshistóricos.
No parsear/renderizar ida-vuelta como entero persistido ni usar float para reconstruir
la validaciónDecimalbackend. Guardado modifica datos que leen API PWAprestaciones,
no equivalencia de esos contratosToken con nueva ediciónweb. Sin upload/email.

## Responsable tarjeta

comedor_responsable_tarjeta_editar GET/POST. Guardrole_tecnico_comedor, objeto scoped,
programaAlimentar y membresía exactagrupo «Tecnico Comedor»; falta grupo404 aunque
permisoruta pase. No superuserbypass nuevo en dispatch. No cambiar grupo porpermiso.

Campos responsable_tarjeta_nombre, responsable_tarjeta_mail, responsable_tarjeta_dni,
responsable_tarjeta_cuit,responsable_tarjeta_domicilio,responsable_tarjeta_provincia,
responsable_tarjeta_municipio,responsable_tarjeta_localidad,responsable_tarjeta_telefono.
Opcionalesmodelo, nombre≤255,DNI/CUIT≤20,emailvalidación y límites restantesmodelo.
Provincia catálogoordenado completo, municipio porprovincia, localidad municipio o
fallbackprovincia. Inicialantigua localidad sinmunicipio deriva de localidad.
Valida relacionesgeográficas en campos, guarda soloestos, sin archivo/email;
éxito→ficha sin mensajeadicionalcustom. No acoplar Formprincipal__all__ a esta acción.

## Pruebas y visuales futuros

Validación lector/técnicoasignado-ajeno/abogado/validadorfuerascope, GET405, acción,
noopciones/otro-vacío, next externo, repeticiónhistorial. Modales completos/error/
fichaestado. Convenio variantes/nopertenece/objetoajeno, GETcrea1vez, montoentero-
miles-decimal, otrocampoeditado conserva centavos, cantidadesnegativas, matriz/
omitidos conservados. Tarjeta permiso-sin-grupo/grupo-sin-permiso/programa/scope,
legado-localidad/cadenas incompatibles y cancelar. CadaURL/estado/rol desktop/móvil/
foco/formularios/avisos/retorno con referencia/candidato/diff y acumulado. Sintéticos,
ningún caso ejecutado o aceptación afirmada; archivos/backend no reimplementados.

## Evidencia

Prefijo src/backends/comedores/comedores/: urls.py:131–136,453–469;
views/validacion.py:11–37; services/validacion_service/impl.py:15–66;
models.py:421–449,657–725,1562–1606;
views/comedor.py:1630–1711; forms/convenio_pnud_form.py:13–163;
forms/comedor_form.py:291–377;
templates/comedor/comedor_detail.html:2101–2183;
api_serializers.py:1157–1266; api_views.py:474–512,1988.
Formconvenio/servicevalidación/viewvalidación contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; principalviews/Form comparados antes,
modelos/templatesauxiliarescheckout. Padre contrastó preservacióncentavos.
CodeGraphsync, sin app/tests/DB/navegador/remote, CI o publicación.

- [Legajo base y dependenciaficha](2026-10-28-2785-comedores-legajo-base-m2.md).
- [Imágenes y CO-I2](2026-10-28-2785-comedores-imagenes-i1-i2.md).
