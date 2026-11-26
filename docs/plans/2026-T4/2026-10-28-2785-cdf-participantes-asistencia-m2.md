# CDF-C/CDF-D: participantes, espera y asistencia en React

Estado E2: contrato de planificación basado en fuente, sin API implementada ni
verificación runtime. D1 mantiene autorización existente; no corrige reglas de
negocio, concurrencia o seguridad en silencio. W1/M2/J2/L2 permanecen vigentes.

## Unidad de activación

CDF-C reúne alta/baja/promoción y presentación de inscritos/espera en
`actividadcentro_detail`; CDF-D reúne planilla, guardado y retorno con fecha.
No activar operaciones React cuyo resultado o mensaje termine en formulario Django.
La ficha de actividad es dependencia común; alta/edición de actividad también
requieren `centro_detail` React según CDF-B. No convertir todas las familias CDF
en una única entrega por compartir menú. Desarrollo por slices, activación por circuito.

## CDF-C: rutas e inputs

| Ruta nombrada | Recorrido fuente | Datos |
|---|---|---|
| participanteactividad_create | GET búsqueda/formulario; POST inscripción o espera | centro_id/actividad_id de ruta, query de búsqueda; ciudadano_id o Form, allow_waitlist=1 |
| participanteactividad_delete | GET confirmación; POST baja | centro_id/actividad_id/pk de ruta |
| actividadcentro_lista_espera | GET histórico | W1: acceso compatible al bloque de espera en ficha, no pantalla nueva |
| participanteactividad_promover | POST solicita primer participante en espera; GET redirige sin mutar | centro_id/actividad_id/pk; GET retorna actividad con promo_error=1 |

Son recorridos fuente, no una declaración de exclusividad HTTP: HEAD/OPTIONS
heredados requieren contraste. Login y permiso URL `view_centro` se conservan;
D1 no agrega restricciones de pertenencia ausentes ni elimina comprobaciones
existentes. No deducir permisos por visibilidad de botones.

`ParticipanteActividadForm` declara nombre/apellido CharField(max_length=255),
fecha_nacimiento DateField, tipo_documento choices de Ciudadano, dni IntegerField
y genero ModelChoice Sexo; todos requeridos. `Meta.fields` vacío. La actividad
proviene de ruta, no de un nuevo campo editable.

### Búsqueda y ramas de inscripción

Búsqueda delegada a Ciudadano.buscar_por_documento: strip, numérico, mínimo siete
dígitos, prefijo y orden por documento, hasta diez resultados. La UI actual dice
«mín 4 dígitos»: divergencia fuente conservada y documentada, no corrección aprobada.

- Con ciudadano_id, vista omite validación de Form y llama servicio con ID.
- Sin ID, valida Form; error vuelve al formulario sin redirección. Duplicado en
  clean: «El ciudadano ya está inscrito o en lista de espera.»
- Inscrito: «Participante agregado correctamente.»; espera: «Participante agregado
  a la lista de espera.»; ambos retornan a ficha actividad con feedback.
- CupoExcedido provoca segunda llamada de dominio con allow_waitlist=True y
  «Cupo completo: participante agregado a lista de espera.». Es regla existente,
  no autorización para retry de red o POST automático.
- AlreadyRegistered/SexoNoPermitido: warning de excepción y retorno a ficha;
  LookupError/ValueError: error de excepción y retorno a ficha.

No trasladar ramas de Form.save que este recorrido POST no ejecuta. El modal
condicional show_waitlist_modal existe en template pero esta vista no lo establece:
no declararlo estado alcanzable sin evidencia adicional.

### Efectos y repetición

Alta transaccional crea/reutiliza ciudadano, participante e historial según reglas
existentes. El validador de edad está vacío: no inventar rechazo por edad. Duplicado
inscrito/en espera se rechaza; no prometer idempotencia general o protección
completa ante altas concurrentes/reinserción.

Baja bloquea participante, registra historial e intenta promoción automáticamente,
incluso si el estado anterior no era inscrito. Si ya dado_baja, retorna sin nuevo
historial/promoción. Mensaje: «Participante dado de baja correctamente.» o excepción.

Promoción selecciona primero por fecha_registro, no necesariamente la fila cuyo
pk figura en URL; no agregar desempate ID ni bloqueo ausente. Repetir POST puede
promover otro si hay cupo: nunca reintentar automáticamente. Mensajes:
«Participante promovido a inscrito correctamente.» / «No hay participantes en lista
de espera.» (verificar bytes exactos de fuente antes de fijar snapshots).
GET no muta y retorna con promo_error=1; incluir ese modal/feedback en ficha React.

Botones de alta existentes muestran spinner y se deshabilitan: reproducir ese
estado no demuestra protección backend de exactamente una vez. No extrapolar
ese atributo a promoción/asistencia si no existe.

## CDF-D: planilla y guardado

`actividadcentro_asistencia`: GET fecha; POST fecha y presente_<pk>.
Login + view_centro + puede_tomar_asistencia_cdf(user, actividad.centro).
D1 conserva este control adicional; actividad inexistente404 y actor no habilitado403.

Fecha por defecto timezone.localdate; formato %Y-%m-%d. Errores fuente:
«La fecha indicada no es válida.» / «No se puede tomar asistencia para una fecha
futura.». GET inválido muestra hoy y aviso con «Se muestra la planilla de hoy.»;
POST inválido no guarda y redirige a ruta sin fecha con message.error.

Solo inscritos actuales, orden apellido/nombre, aunque espera/baja tengan
asistencias históricas. Cada fila comienza None/True/False según registro;
métricas presentes/ausentes/sin marcar. **Guardar convierte no marcado en ausente**,
no conserva None como tercer estado persistido por ese POST.

Guardado transaccional update_or_create(participante,fecha), constraint único.
Repetir actualiza marca y registrado_por, no duplica esa clave; no promete bloqueo
de edición concurrente. Éxito «Asistencia del DD/MM/AAAA registrada para N
participante(s).» y retorno misma ruta ?fecha=YYYY-MM-DD. Volver/breadcrumb a ficha.

Radios individuales, Presente (todos)/Ausente (todos): desmarcar checkbox masivo
no limpia radios previos; cambio manual actualiza métricas. Conservar interacción,
no sincronizar por inferencia ni rediseñar estados.

## Casos de contrato y visuales por concretar en entorno autorizado

Todos propuestos, sin ejecutar. Para cada caso visual: referencia/candidato/diff,
URL instanciada con IDs sintéticos, rol, estado y desktop/móvil, teclado/foco y
retorno. No aceptar capturas de controles cerrados como prueba de todo el formulario.

| Grupo | Casos requeridos por la fuente |
|---|---|
| CDF-C búsqueda | Vacía, seis/siete dígitos, no numérico, sin resultados y hasta diez; diferencia texto/umbral |
| CDF-C alta | Existente/nuevo, Form inválido, duplicado, sexo no admitido, ID inexistente; cupo libre/lleno, feedback y spinner |
| CDF-C ficha y espera | Inscritos/espera/vacíos, alias W1 y GET promoción sin mutación, promo_error |
| CDF-C efectos | Cancelar/confirmar baja, baja repetida, promoción automática, cupo lleno, sin espera, primer registro y empate sin orden inventado |
| CDF-D fecha y filas | Hoy/pasada/futura/inválida, GET frente a POST, ningún inscrito, None/True/False, excluir espera/baja |
| CDF-D interacción | Individual/masivos/desmarcado, métricas, no marcado→ausente, guardar/corregir/repetir, mensaje contador/fecha y retorno |
| Autorización y efectos | Actor permitido/no permitido según política existente, CSRF, IDs inconsistentes y acceso directo; denegación existente sin mutación ni efecto secundario |

Relaciones inconsistentes y concurrencia requieren contraste diferencial; un
resultado legacy inseguro no se convierte en aprobación de seguridad. D1 registra
el riesgo aparte. No inventar un 403 nuevo como condición de aceptación de paridad.

## Fuente y validación

Prefijo `src/backends/cdf/centrodefamilia/`:
urls.py:145–184; forms.py:215–279; views/participante.py:20–190;
services/participante/impl.py:118–212; views/asistencia.py:19–93;
services/asistencia/impl.py:17–95; models.py:284–287;
templates/centros/participanteactividad_form.html:41,69–140;
templates/centros/actividadcentro_asistencia.html:163–224.
Búsqueda: src/backends/kernel/ciudadanos/models.py:483–499.
Spinner: src/backends/kernel/static/custom/js/base.js:410–423.

Exploración CodeGraph sincronizada y fuente contrastada con snapshot 59a8f797688c9e762d5a4e9eaa187698ffade8aa
para archivos previamente indicados; contraste puntual del padre en POST asistencia.
Solo validación documental, no tests de aplicación, fixtures, persistencia o paridad.

- [Particiones y D1](2026-10-28-2785-cdf-circuitos-y-alcance-autorizacion.md).
- [Decisión D1](../../registro/decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).
