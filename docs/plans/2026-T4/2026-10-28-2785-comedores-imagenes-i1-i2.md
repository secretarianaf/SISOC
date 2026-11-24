# CO07.02: aislamiento del borrado de imágenes y selectores

E2: planificación. CO-I2 elegida explícitamente («CO-I2»); no aplicación, DB, storage o explotación
reproducida. CDI-F2 y auditorCDI no se extienden a Comedores por analogía.

## Hallazgo de pertenencia: cadena fuente completa

Vistaeditar exige ChangeComedor y resuelve comedor por scope. Form y Referente
válidos→atomic→save→delete_images(request.POST) sin filtrado previo de claves.
Servicio extrae regex imagen_ciudadano-borrar-(id) y elimina ImagenComedor.objects
por id__in global, sin comedor del objeto autorizado. Queryset visual de GET no
limita POSTforjado. Con edición válida de A y claveimagenB la cadena inspeccionada
seleccionaría registroB. No se verificó middlewareglobal, escriturareal o efecto
físicofichero; no describir incidenteproducción ni borrado de bytes demostrado.

## Decisión resuelta: CO-I2 elegida, CO-I1 descartada

| Alternativa | Alcance | Costo/riesgo |
|---|---|---|
| CO-I1 — Paridad literal de selección global por ID | Conservar comportamientolegacy y representarlo como tal al migrar | Menor alcancecorrectivo, pero puede reproducir borrado de registroajeno en contrato nuevo; no es autorización segura por scopepantalla |
| CO-I2 — Planificar corrección coordinada por comedor autorizado (recomendación) | Filtro obligatorio de pertenencia en legacy y futura API, usando comedor autorizado del servidor; no confiar en comedor_id del cliente | Cambia efecto de POSTforjado y amplía corrección de dominio; exige negativos A/B, filaspropias y rollbacksegúncontrato. No cambia permisos/grupos ni serving de todos los medios |

CO-I2 fue aceptada el 2026-10-28 solo para planificación. No incluye corregir
erroresuploadignorados,
introducir validación nueva a foto_legajo o resolver todos los archivos públicos.
Política exacta frente a lista mixta propia/ajena debe definirse antes de implementar
para no ocultar parcialidad; el requisito mínimo es no alterar imagen fuera del
comedor autorizado. No añadir grants o tratarIDglobal como dueño.

## Upload/serving: conservar contratos reales

create_imagenes valida ImagenComedorForm con comedor/origen e imagen:≤3MB e imagen
real por ImageField. Retorna objeto o dict errores; callersweb de alta/edición
ignoran resultado, así que imageninválida no acredita rechazo del guardadoentero.
No corregirlo por usar serializerdistinto sin decisión/evidencia. API PWA y territorial
consumen esehelper: preservar sus contratos/errores. client_uuid para offlinePWA no
se presume idempotencykeyweb. Foto_legajo otroImageField sin clean3MB acreditado.

ImagenComedor upload_to comedor/; permite relaciónrelevamiento/seguimiento y origen
web/mobile. Borrarregistro no prueba borrararchivo. Foto_legajo_borrar usa instancia
actual, intenta storage.delete, logexcepción y limpia campo de todas formas. DBatomic
no reviertebytes. .url directo en previews, producción no inspeccionada; CDI-F2 no
se extiende a estos archivos por decisión de otrodominio.

## Selectores y mapa del formulario

Municipios GET provincia_id, login/require_GET, mapa territorialactor, array id/nombre
ordennombre. Localidades GET municipio_id (prioridad) o provincia_id, ninguno→[],
array id/nombre; no repite mapaterritorial en método, no describir ambosigualscoped.
Organizaciones GETq/page, login, nombreicontains/ordennombre30página, results id/text
+pagination.more global. Proyecto organización requiere ANY permisos inclAdd/Change
Comedor más objeto scoped: superusuario/ViewOrganizacion todo, resto organizaciones
de comedores dondetécnico/abogado, activos→{proyectos:[id,codigo,nombre]}.

address_preview POSTautenticado provincia+domicilio o calle+número/altura,
municipio/localidad opcionales; invalid400/errors, unavailable503, located/not_found/
ambiguous200 con posible suggestion; private/no-store, no persiste/autorizaComedor.
Geocodificaciónexterna timeout8s fuente: pruebasfuturas simuladas, no callrealE2.

## Ficha: consumidores inventariados, todavía no completitud

Cincomódales declarados: intervención/observación/admisión/validación/motivosno.
DU01equipo; CO01nómina-admisión/directa/import; CO02intervencionesarchivos/next;
CO03colaboradoresactividades; CO05certificacioneshistoriadescarga; CO06observaciones;
CO07tarjeta/convenioPNUD/validación/admisión. Relevamientos/audittrail/capacitaciónAJAX/
DWtransacciones/mes_ejecucion aportan otras vistas/acciones. No afirmar totalacciones
cerrado ni ficha preparada por tener CRUDbase. No IDs nuevos para cada modal.

## Casos futuros

ActorChangeComedorA con idimagenB y mezclaA/B, inexistente, cancelar, propios y
repetición, alcance objeto, DB frente storage; upload inválido/noimagen/>3MB/mezcla/
fallostorage/legajo. Selectores padres/scopes distintos/errores/stale y preservar
iniciales. Ficha modales/next/contribuciones por rol. Sintéticos, desktop/móvil/foco,
referencia/candidato/diff y acumulado. Ninguno ejecutado; no archivos reales.

## Fuente

src/backends/comedores/comedores/views/comedor.py:1207–1208,1720–1765;
services/comedor_service/impl.py:830–855,933–941;
forms/comedor_form.py:775–788; models.py:1348–1394;
api_views.py:711; api_views_territorial_adjuntos.py:177;
src/backends/kernel/core/urls.py:42–50; views.py:65–101;
location_views.py:11–53; services/geolocation.py:23–69;
src/backends/comedores/gestion_organizaciones/views.py:121–157,1540–1550;
urls.py:37–41,201–206;
comedores/templates/comedor/comedor_detail.html:1247–2136.
Vistas/servicioprincipal ya contrastados al snapshot59a8f797688c9e762d5a4e9eaa187698ffade8aa;
auxiliarescheckout, no comparaciónindividual. Padre contrastó caller y selección
IDglobal. CodeGraphsync, sin app/tests/DB/navegador/remote o cambiosinfra.

- [Contrato base CO07](2026-10-28-2785-comedores-legajo-base-m2.md).

Registro: [CO-I2 aceptada](../../registro/decisiones/2026-10-28-2785-comedores-imagenes-i2.md).

## Resultado resuelto: CO-I3, rechazo completo antes de efectos

CO-I2 ya está aceptada y ambas alternativas impiden borrar imágenes ajenas. El responsable eligió «CO-I3»: rechazo completo antes de guardar ante una
selección inválida. Se conserva la evaluación previa de una edición que mezcla imágenes autorizadas y
no autorizadas/no resolubles, junto con otros cambios del formulario. Vista actual
savecomedor/referente antes de delete_images dentro de transacción; la nueva
validación debe diseñarse antes de cualquier efecto que se pretenda rechazar.

| Alternativa | Resultado | Costo/riesgo |
|---|---|---|
| CO-I3 — Rechazar toda la edición (recomendación) | Validar selección contra comedor autorizado antes de guardar; ante ID no autorizado/no resoluble, error genérico y ningún cambio de formulario, imágenes o referente | Evita guardado parcial y ambigüedad. Una selección desactualizada puede obligar a refrescar/revisar antes de guardar otra vez |
| CO-I4 — Guardar lo permitido y avisar | Guardar campos válidos y borrar solo imágenes autorizadas; omitir las demás con aviso explícito de resultado parcial, sin detalles del dueño | Permite completar cambios válidos, pero usuario debe entender que no se aplicó toda la solicitud. Exige contrato claro de éxito parcial, no success genérico |

Ambas mantienen CO-I2, permisos y diseño normal. Mensaje excepcional no revela
existencia/dueño/nombre de archivo ajeno, no logs con datos personales. Ninguna
permite retry automático, imagen externa modificada, reintento que duplique upload
o cambios de serving. No corregir por esto erroresuploadprevios ignorados.

Casos adicionales: selección totalmente propia, mixta, inexistente/desactualizada,
sincheckboxes, error sin datos ajenos y reenvío manual. Comprobar camposComedor,
Referente e imágenes de ambos objetos además de mensaje. Contraste de rechazo o
parcialidad explícita se hará conforme CO-I3 en futura ejecución sintética; no queda una nueva elección.

Fuente de orden de efectos: views/comedor.py:1744–1765, serviceimpl:830–839 ya
contrastadas. No estado de referencia nuevo ejecutado ni implementación.

Registro: [CO-I3 aceptada](../../registro/decisiones/2026-10-28-2785-comedores-imagenes-i3.md).
