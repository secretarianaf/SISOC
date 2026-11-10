# CDI03/CDI05: formularios institucionales y trabajadores

E2: preparación por fuente, sin implementación o verificación runtime. IDs
CDI03.01/02 y CDI05.01/02 conservados. CDI-A2 solo asistencia/derivaciónPOST;
CDI-CR1 no habilita nuevos paneles de contraseñas de trabajadores.

## Trabajadores: circuito CDI05

centrodeinfancia_trabajador_ver/crear/editar/eliminar usan View/Add/Change/Delete
Trabajador respectivamente. Nested queryset centro+trabajador y alta scoped.
Mutaciones _AuditoriaSoloLecturaMixin. Lista vive en fichaCentro, no ruta nueva.
Altas/edición/baja→centrodeinfancia_detalle; mensajes «Trabajador agregado
correctamente.», «Trabajador actualizado correctamente.», «Trabajador eliminado
correctamente.». M2 requiere ficha/feedback consumidor, no Form aislado.

TrabajadorCDIForm Meta42campos: fecha_carga,subcomponente,funcion_pfpi,funcion_egp,
funcion_cdi,sala_cdi,funcion_uaf,registro_tipo,fecha_actualizacion,nombre,apellido,
fecha_nacimiento,tipo_documentacion,dni,sexo_registral,cuit,pais_nacimiento,
nacionalidad_trabajador,nivel_educativo,formacion_academica,capacitaciones_certificadas,
anos_trabajo_primera_infancia,tipo_contratacion,carga_horaria_semanal,email,telefono,
calle_contacto,unidad_funcional,tipo_barrio,provincia_contacto,departamento_contacto,
municipio_contacto,localidad_contacto,grupo_pertenencia,pueblo_originario,lenguajes,
es_interprete,tiene_discapacidad,tipo_discapacidad,recibe_apoyo_discapacidad,tiene_cud,
numero_cud. Requeridos finales parten CAMPOS_OBLIGATORIOS, no modelo blank.

PFPI requiere funcion_pfpi; EGP funcion_egp; CDI funcion_cdi+sala_cdi; UAF funcion_uaf.
Email requerido solo alta para provisión. RENAPER verificado disabled en servidor;
valores iniciales inválidos no se bloquean y corregirlos deja de verificarlos.
Token prefill15min actor+centro; país crudo no sustituye nacionalidad de catálogo.
Nacimiento nofuturo, edad0..100, DNI7/8, CUIT, teléfonos/nombres/CUD y carga≤60h.
Múltiples grupo/lenguajes/capacitaciones con exclusiones, no strings únicos.

Guardar puede crear/vincular User/enviar credenciales; edición puede sincronizar
email si cuenta temporal. Error provisión no invalida trabajador guardado: éxito
parcial y aviso fieles, no repetir POST para reenviar. No vista de credencial nueva
por analogía con CR1: servicio envía y enlace a User es efecto distinto.

## Institucional: circuito CDI03

centrodeinfancia_formulario_listado/crear/detalle/editar, View/Add/View/Change
FormularioCDI. Sin ruta borrar. Centro scoped y formulario filtrado centro+scope;
auditor rechazado antes de guardar POST. Crear toma snapshot de datos centro;
editar usa instancia, no autosync del centro fuente. Oferta preseleccionada solo
si centro tiene una. Éxito→ficha formulario «Formulario #<pk> creado/actualizado
correctamente.». FichaCentro consume tres recientes; activación coordina resumen.

FormularioCDIForm usa Meta.exclude, no fields cerrado: excluye centro,
source_form_version/auditoría/softdelete/horarioapertura-cierre legacy. Schema final
requiere modelo + SECCIONES_FORMULARIO_CDI, no serializador completo automático.
Múltiples meses/días/protocolosalud/prestaciones; booleanos trivalentes, geografía
CDI/organización y horarios por día.

Tres formsets fijos sin can_delete:
- distribucion_salas: grupo_etario,cantidad_salas,superficie_exclusiva_m2,
  cantidad_ninos,cantidad_personal_sala.
- demanda_insatisfecha_por_grupo_etario: grupo_etario,cantidad_demanda_insatisfecha.
- frecuencia_articulacion: tipo_institucion,frecuencia.

Claves de fila desde catálogo, no filas arbitrarias. DTO de errores incluye
ManagementForm, porfila y globales; no esconderlos en aviso genérico. Clean limpia
«otra» fuera de rama, dependientes cocina/exterior/electricidad/prestaciones;
código edición desde instancia no POST. Horarios día/par/orden mantienen validación.

## Riesgos fuente que no se corrigen incidentalmente

GET edición construye formsets y ensure_fixed_rows puede crear faltantes de tres
catálogos. Veto auditor soloPOST no demuestra GET sin efectos. Registrar y contrastar
baseline en fase autorizada antes de diseñar nueva lectura JSON con esa semántica;
no introducir una nueva mutación automática cliente o declarar lectura pura por nombre.

Vista POST usa form.save(commit=False), formulario.save(), formsets.save() y
ensure_fixed_rows. No vuelve a Form.save(commit=True), cuya rama persiste/elimina
horarios y actualiza columnas legacy. No afirmar persistencia de horarios de ese
POST sin prueba: reutilizar save(True) podría corregir comportamiento no solicitado.
Hipótesis estática, no bug reproducido; guardar limpio en UI no acredita resultado.
No ampliar CDI-A2 a esta discrepancia. Si verificación demuestra cambio necesario
se presenta antes de implementarlo; otros contratos pueden seguir definiéndose.

## Nómina: cierre de incertidumbres de campos

Destinatarios CAMPOS_OCULTOS elimina (pop) posee_obra_social,diagnostico_peso,
diagnostico_talla,orientacion_msal,recibe_apoyo_discapacidad. No recrearlos editables
por aparecer en modelo/base. Meta87 no es número final de controles: declarados y
vacunas dinámicas vacuna_<code>_dosis/_fecha suman otros; trabajador queryset centro.
Requeridos se redefinen desde lista1404 sobre campos presentes: responsable1 sí,
responsable2 no obligatorio por existir; extracción de lista exacta/catálogos sigue
necesaria antes de afirmar DTO final aceptado. No importar Form bajo E2.

## Casos futuros, ninguno ejecutado

Trabajador actores/objetoajeno/auditor; búsqueda/RENAPER/manual/token, subcomponentes,
emailalta, identidadbloqueada/inválida, múltiples/CUD/≤60h, éxito+provisiónfallida,
edición/baja/cancelar/mensajes/retornos. Email/RENAPER simulados, sin datos reales.
Institucional inicialuna/múltiplesofertas, condicionales/trivalentes, formsets/
ManagementForm/filas/totales, código inmutable, auditor/snapshot, GETfilasfaltantes,
POSThorarios versus baseline, repetición/éxito/resumen reciente. Fixtures sintéticas,
referencia/candidato/diff porURL/estado/rol desktop/móvil/foco/teclado y acumulado.

## Evidencia

Prefijo src/backends/cdi/centrodeinfancia/: urls.py:185–238,342–367;
views.py:935–1274; forms.py:1404,1547–1553,1727–1745,2020–2444;
views_formulario_cdi.py:49–82,161–205,267–370,477–569;
forms_formulario_cdi.py:61–383.
Vistas/Forms institucional y views.py/forms.py contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa. Padre contrastó guard y save(commit=False).
Exploración CodeGraph sync; sin app/tests/DB/navegador/remote o capturas.

- [Nómina/asistencia](2026-10-28-2785-cdi-nomina-asistencia-m2.md).
- [Centros y provisión](2026-10-28-2785-cdi-centros-y-credenciales.md).
- [CDI-A2](../../registro/decisiones/2026-10-28-2785-cdi-auditoria-a2.md).
