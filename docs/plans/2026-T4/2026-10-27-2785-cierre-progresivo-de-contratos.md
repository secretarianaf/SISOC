# Continuación de planificación: preparación por circuito

## Índice vigente consolidado — 2026-10-28

**Estrategia integral definida; contratos preparados por circuito; implementación y
aceptación futuras.** Catálogo vigente: **95 familias / 215 propuestas**, sin
renumerar IDs ni transformar todas las propuestas en tareas ejecutables.

La autoridad del estado actual es esta tabla y `planning_contract_preparation` del
[catálogo existente](2026-10-27-2785-entregas-por-flujo.json). El desarrollo cronológico
posterior conserva evidencia histórica; una alternativa antes pendiente puede estar
resuelta en su registro. No reabrirla por leer una entrada anterior.

### Tres niveles, sin confundirlos

1. **Estrategia definida:** todo formulario/pantalla de aplicación termina React;
   apariencia actual, activación M2 por circuito, backend PDF/correo, Admin/Unfold
   #2789 fuera. No nuevas dependencias ni rediseño por conveniencia.
2. **Preparación contractual:** rutas, dueños, acciones, permisos, efectos y retornos
   documentados o localizados; desarrollo fuente no equivale a tarea lista.
3. **Implementación y aceptación:** endpoints/tipos reales, pruebas, fixtures,
   referencia/candidato/diff por URL y revisión humana; aún no ejecutados bajo E2.

Resumen derivado del catálogo: `contrato_fuente_desarrollado`: 40; `descomposicion_propuesta_con_fuente_localizada`: 48; `contrato_parcial_de_contribuciones`: 1; `reutilizacion_integrada_por_contrastar`: 6. Ninguna familia se declara lista por ese conteo.

| Bloque | IDs originales | Preparación actual | Siguiente gate y alcance |
|---|---|---|---|
| Base/piloto | I01, I02, I03 | B0–B2, contexto/shell e INS-A/INS-B | Consolidar endpoints/tipos al implementar; no exigir todos los demás dominios o G1 remoto para piloto local. |
| Identidad y remediaciones | T01, E01, U01, U02, U03, U04, U05, U06, U07, U08 | Contratos web, lotes, compuesto y regresión token | Permisos/efectos por actor y job; secretos separados; contratos PWA/SIIS intactos. |
| Transversal | T02, T03, T04, T05, T06, T07, E02, E03, E04, D01, A01 | Registro de fuente y perfiles del catálogo | Precisar recorridos al preparar cada circuito; atención a restauración, encuestas y consumidores compartidos. |
| Ciudadanos | C01, C02, C03, C04, C05 | Aportes360 definidos parcialmente; inventario del resto | Importación/revisión/familia/ABM por circuito, preservar identidad global y fronteras G1/C2. |
| Comedores y equipo | CO01, CO02, CO03, CO04, CO05, CO06, CO07, CO08, DU01 | Contratos específicos CO01–CO07/DU01 | CO08 es frontera API/regresión; no reescribir PWA ni corregir otros permisos por analogía. |
| Organizaciones | O01, O02, O03, O04, O05 | Integración #2775 y catálogo de rutas | Refrescar evidencia integrada antes de implementar; agrupar convenio/documentos/firmantes/rendiciones/proyecto. |
| Admisiones | AD01, AD02, AD03 | AD02 contextual; configuración y circuito legal con dueño propio | Cerrar publicaciones/transiciones y consumidores de AD01/AD03, sin duplicarlos en React. |
| Seguimiento y pagos | AC01, EX01, EX02 | Catálogo fuente y dependencias de ficha/expedientes | Recorrido por estado, importación y resultado/archivo; sin efectos externos reales en pruebas. |
| Relevamientos | R01, R02, R03 | Rutas/Forms y dependencia desde ficha | Separar carga, actas y seguimiento; no ampliar offline ni apps de campo por asociación. |
| Rendiciones | RM01, RF01 | Catálogo y consumidores documentales | Unir captura, validación, documentos y retornos antes de activación. |
| Comunicaciones | CM01, CM02, CM03 | Catálogo de mailing/jobs, gestión y lectura | Autorización de job/archivos y entregas externas simuladas; no inferir éxito real de un registro guardado. |
| CDI | CDI01, CDI02, CDI03, CDI04, CDI05, CDI06, CDI07, CDI08, CDI09 | Contratos por circuito y cambios acotados aprobados | CDI-F2 requiere preflight de ownership antes de elegir transición; no bloquea circuitos independientes. |
| CDF | CDF01, CDF02, CDF03, CDF04 | CABAL/actividades/asistencia/centros/usuarios | CDF03 beneficiarios/responsables aún propuesto; D1/W1/CR1/J2/L2 se mantienen sin nuevas entrevistas. |
| Dispositivos/DataCalle | DS01, DS02, DC01, DC02 | Fuente localizada y coordinación #2792 | Concretar legajo/mapa/operativo/caso/equipo/cierre; no agregar infraestructura o app móvil nueva. |
| Inspecciones | IN01, IN02, IN03, IN04, IN05 | Cinco circuitos con importación, tablero y archivos | Schemas/fixtures y regresión de PWA externa antes de activación; no nueva carga de notificación backoffice. |
| PAS | PAS01, PAS02, PAS03, PAS04, PAS05, PAS06 | PAS01 público y catálogo administrativo | Separar invitación P1, gestión, cruces, PDF y padrón; integración real no autorizada por plan. |
| OCR | OCR01, OCR02 | Catálogo de carga/job/descarga | Conservar motor/worker y permisos por job/archivo; no presumir capacidad por tests estáticos. |
| VAT/INET | V01, V02, V03, V04, V05, V06, V07, V08 | I1 y reutilización integrada de V02–V07 por contrastar | V01/V08 no quedan cubiertos por INET; medir paridad y adaptar presentación, no rehacer servicios por rutina. |

### Cierre proporcionado y secuencia

- Completar el primer circuito revisable según B0–B2 y contratos INS-A/INS-B;
  no exigir definir los 215 schemas antes del piloto ni cerrar G1 remoto para
  lecturas locales independientes. Esto no autoriza iniciar implementación.
- Para cada siguiente circuito, usar su owner/rutas/Forms/servicios del registro,
  cerrar la whitelist de campos efectivos y comparar efectos antes de escribir.
  Extraer opciones, mensajes y DTO exacto es descubrimiento por slice, no nueva
  decisión humana si conserva las reglas y límites aprobados.
- Resolver por el agente formatos, validación de presencia/omisión y render React
  con patrones existentes; no trasladar lógica de negocio o permisos al cliente.
  Defectos previos quedan en registro de riesgos, salvo cambios acotados aprobados.
- Escalar solo decisiones humanas importantes: cambio de negocio/alcance, límites
  de seguridad, costos/obligaciones externas o acciones irreversibles. Agruparlas,
  sin preguntar por cada campo, error, parámetro o microdecisión técnica.
- CDI-F2 mantiene estrategia operativa pendiente de preflight autorizado; G1 de
  mediciones E01–E07. Incertidumbre visible con camino de prueba no se convierte
  en supuesto resuelto ni bloquea trabajo local independiente.

### Evidencia que no se puede cerrar mediante más documentación

Baseline visual y versión candidata aceptados; capturas y diff por cada URL/estado/
rol/viewport afectado y consumidores indirectos; aceptación humana; persistencia,
concurrencia, fallos, contratos efectivos de sesión/CSRF/alcance; capacidad G1; salud
por entorno; compatibilidad de archivos y serving; CI, merge o despliegue.
Todo permanece futuro y requiere su autorización correspondiente. Un test mock,
una lectura de fuente o una selección de alternativa no es ninguna de esas pruebas.

## Historial de profundización (conservar como evidencia fechada)

Estado **E2**, sin implementación. Profundiza cinco pendientes encontrados en la
revisión: circuitos M2, contratos API, G1, casos visuales y coherencia/reutilización.
No convierte el catálogo de 214 propuestas en 214 fichas ejecutables.

## Resultado verificable de esta continuación

| Frente | Definición concreta añadida | Qué falta, sin confundir fases |
|---|---|---|
| M2 | [INS-A e INS-B](2026-10-27-2785-insumos-circuitos-m2.md): nueve URLs públicas, retornos/efectos y dependencias; descarga backend diferenciada | Revisión de contrato, implementación y evidencia; los otros dominios aún requieren partición fuente propia |
| API | Una propuesta vigente `/api/web/insumos/`, operaciones GET/HEAD/POST explícitas, campos/options/errores y permisos por acción; formularios React con validación Form/backend | OpenAPI de operaciones implementadas/tipos se generan en implementación, no desde un catálogo; no declarar endpoint creado |
| G1 | [Experimentos E01–E07](2026-10-27-2808-experimentos-y-cierre-g1.md), métricas, criterios de rechazo y orden | Revisión técnica y parámetros basados en mediciones futuras; no bloquear Insumos local por G1 remoto |
| Visual | Manifiesto Insumos extendido a formularios, confirmaciones, errores, éxito, permisos y efectos; reglas de fixtures independientes | Resolver IDs reales/entorno, capturar pares, diff y aceptación humana después; no aceptar baseline en esta etapa |
| Coherencia | Referencias API y alcance del piloto reconciliados con M2; [reutilización INET](2026-10-27-2794-reutilizacion-y-referencia-visual.md) precisa diferencias por acción | Actualizar snapshot al comenzar una implementación autorizada; diff previo para no sobrescribir integración ajena |

## Orden de contratos restantes

1. Contexto #2798 y shell: revisar OpenAPI mínimo/menú/estados contra fuente; no
   cambiar contrato token PWA ni importar VAT desde core.
2. Insumos: revisar INS-A/INS-B y derivar fichas de formularios; #2802 sigue lectura.
3. Identidad U01–U03 e inicio/encuestas T01/E01: concretar remediaciones y retornos
   como circuito transversal propio; no condicionar una encuesta a estar ready.
4. CDF: W1 #2811 conserva acceso a sección existente; revisar permisos/objeto y
   formularios de su grupo antes de activarlo. PAS P1 y aportes C2 mantienen sus
   contratos específicos, sin extender excepciones a otras pantallas.
5. INET: contrastar acciones ya integradas antes de definir código nuevo; luego
   dominios padres y operaciones según dependencias del catálogo existente.

Este es orden técnico propuesto, no prioridad de negocio ni compromiso de fechas.
No reabrir G1/P1/C2/E2/I1/W1/M2 ni sumar trackers o estados de board.

## Regla de preparación para cada una de las 95 familias

Conservar IDs del catálogo y de rutas. Para cada circuito nombrar rutas de
lectura/formulario/acción/retorno, Forms/services y consumidores existentes.
Separar desarrollo por slice de activación por circuito; justificar enlaces a
otro circuito y efectos compartidos. No agrupar toda la app por sidebar global,
ni separar artificialmente formulario y destino de su POST.

Una ficha queda definida cuando tiene campos/options/errores/permiso/objeto,
efectos y negativos propios; API existente reutilizada o nueva justificada;
casos visuales por ruta/estado/rol y fixture declarada; compatibilidad y reversión.
Si falta información de negocio se investiga fuente antes de pedir decisión;
si cambia reglas/seguridad/alcance se presentan alternativas y se espera elección.
Los registros estáticos no prueban dispatch efectivo, permiso ni persistencia.

No completar los 214 contratos mediante inferencia de nombres ni exigir definir
todo el sistema antes de cualquier implementación futura. Preparar primero un
circuito completo revisable; expandir en orden, dejando explícito qué sigue siendo
propuesta. La migración completa no se cierra con formularios Django residuales.
Admin/Unfold queda fuera; PDF/correos siguen backend.

Validación de esta continuación: lectura estática, consistencia documental/JSON y
rutas; sin aplicación, DB, servidores, navegador, capturas, CI, commits o deploy.

## Avance posterior: identidad y remediaciones

El [contrato de identidad](2026-10-27-2788-identidad-remediaciones-m2.md) concreta
ID-A–ID-E/EQ-A; el manifiesto propio agrega 52 casos/104 combinaciones y quince
comprobaciones de contrato, sin ejecución. La inclusión auth de Django se
reconcilia con registro y fuente local: tres paths estándar adicionales y cinco
shadowed. Se añade U02.03 al catálogo, ahora 215 propuestas, sin cambiar los 214
IDs previos ni el inventario literal congelado.

R1 de centros está resuelta. S1 fue elegida para
[gestión de encuestas](2026-10-27-2788-excepcion-gestion-encuestas.md),
que conserva la excepción origen en el gate sin bypass general; falta implementación y evidencia, no una nueva elección S1/S2.

Después de S1, identidad conserva 52 casos/104 combinaciones y amplía checks de
contrato de quince a veinte, todos sin ejecutar. Selectores complejos tienen
[J2 elegida](2026-10-27-2787-selectores-react-j1-j2.md), una elección de
dependencia/mantenimiento; reutilizar React no implica adoptar apariencia MUI.


La continuación J2 añade [contratos de CDF/Inspecciones](2026-10-27-2787-selectores-contratos-j2.md)
y manifiesto de controles específicos, sin trasladar Select2/jQuery a formularios
React. [L2 fue elegida](2026-10-27-2787-error-carga-actividades-l1-l2.md) el 2026-10-28:
mensaje/reintento manual acotado para categoría→actividad CDF. Solo repite GET de
opciones de la categoría actual, conserva otros campos y no repite guardado.
La rama sin catch se identificó en fuente; no se reprodujo incidente desplegado.


## Continuación 2026-10-28: alcance de autorización CDF

Se identificaron cinco particiones propuestas CDF-A–CDF-E y una asimetría de
autorización en fuente. [D1 elegida](2026-10-28-2785-cdf-circuitos-y-alcance-autorizacion.md):
paridad estricta o planificar endurecimiento coordinado legacy/API. El responsable eligió «d1»: conservar autorización actual, sin endurecimiento
ni bypass nuevos. Riesgo separado; no se afirma explotación en producción. E2 y decisiones previas vigentes.

CDF-C/CDF-D tienen [contrato fuente de participantes, espera y asistencia](2026-10-28-2785-cdf-participantes-asistencia-m2.md),
con efectos de baja/promoción, ramas de Form/servicio, fecha, marcas, mensajes y
casos visuales/negativos propuestos. Sin ejecución ni otra decisión de producto
en esos recorridos; usuarios/CABAL aún requieren profundización.

CDF-E tiene [mapa de usuarios/CABAL y decisión CR1/CR2](2026-10-28-2785-cdf-usuarios-cabal-y-credenciales.md).
La UI actual exhibe temporal en resultado de alta y panel con condiciones diferentes.
D1 no autoriza un nuevo contrato de secretos: el responsable eligió «cr1»: proyecciones
privadas mínimas y separadas, conservando controles existentes, sin exposición
global ni almacenamiento persistente cliente. CR2 descartada.
No se implementó ni publicó contrato sensible.

[Centros y actividades CDF-A/B](2026-10-28-2785-cdf-centros-actividades-m2.md)
concretan campos, opciones, permisos distintos por acción, métricas, paginación
y consumidores compartidos. Dos bloques de ficha carecen de productor identificado y se conservan vacíos
según template; center_map_query se resuelve por tag. Mapa reutiliza motor existente
y hora admite adaptador local flatpickr; ver contrato ampliado, sin inventar datos.

[Inspecciones IN01–IN05](2026-10-28-2785-inspecciones-circuitos-m2.md)
precisa once entregas existentes por circuito: importación/revisión/aplicación,
asignaciones, tablero/exportación, actas/archivos y escuelas/modal-página.
Suplemento precisa payload tablero, clasificación y notificación como constancia
física PWA, no email/push. Consumidor PWA externo sin tecnología verificada,
contratos preservados; sin nueva elección ni ejecución.

[CDI09/CDI01](2026-10-28-2785-cdi-centros-y-credenciales.md)
precisa centros, Forms, año/horarios, scope/auditoría, provisión parcial, RENAPER
y dependencia de bloques de ficha. CDI-CR1 elegida explícitamente para transporte
privado mínimo de credenciales, conservando predicados CDI por actor/fila.
CDI-CR2 descartada; no se importa autorización CDF ni se implementa bajo E2.

[CDI04 nómina/derivación y CDI02 asistencia](2026-10-28-2785-cdi-nomina-asistencia-m2.md)
precisan circuitos y diferencias frente CDF: derivar crea destino Pendiente; quitar
marca asistencia elimina registro. Form completo y política auditor en dos acciones
requieren contraste adicional; no se inventa esquema o nueva restricción.

CDI-CR1 quedó aceptada; nómina y asistencia avanzan con contratos fuente.
[CDI-A1/CDI-A2](2026-10-28-2785-cdi-auditoria-a1-a2.md) quedó resuelta con CDI-A2: plan de corrección coordinada de POST asistencia/
derivación con predicado auditor actual y sus excepciones. Hallazgo estático,
sin reproducción o mitigación demostrada.
No se cambian permisos ni se extiende D1 CDF automáticamente.

[CDI03 institucional/CDI05 trabajadores](2026-10-28-2785-cdi-formularios-trabajadores-m2.md)
concreta retornos, Forms/formsets, provisión parcial y riesgos preexistentes de
filas creadas en GET/horarios fuera de rama persistente. Sin corrección silenciosa
ni otra decisión todavía; CDI06/CDI07 quedan como siguiente grupo acotado.

[CDI06/CDI07](2026-10-28-2785-cdi-intervenciones-observaciones-m2.md)
concreta intervenciones/archivos/observaciones, Forms, permisos y retornos. Ocho
mutaciones adicionales se incorporan por elección explícita «cdi-a3», con mismo
predicado/excepciones y sin cambiar permisos de grupos. Total diez operaciones
nombradas; no implementación ni ampliación implícita a otros hallazgos.
Descarga FileField.url no demuestra serving privado; verificación futura pendiente.

[CDI01 usuarios/CDI08 reportes y documentación](2026-10-28-2785-cdi-usuarios-reportes-documentacion.md)
precisa estados, redirectEGP, CSV/XLSX/PDF con reglas distintas. Receta local Nginx
no protege documentacion frente al aliasgeneral; serving producción no verificado.
CDI-F2 elegida: plan de descarga autenticada y cierre de bypass tras inventario
de consumidores, sin bloqueo global ni movimiento de archivos por inferencia.
Es independiente de las diez mutaciones A2/A3 y no autoriza implementación.

[Inventario F2](2026-10-28-2785-cdi-documentacion-inventario-f2.md)
identifica prefijo compartido CDI/Comedores y APIComedores con URL/path. Descarga
CDIporPK puede preservar bytes, pero capa de cierre y ownership histórico requieren
preflight futuro; no bloquear globalmente ni afirmar F2 implementada.

F2 distingue descarga porobjeto y cierre de aliasNginx/fallbackdev. Proxy/transporte
existentes no clasifican ownership; preflight histórico/compartidos pendiente en
entorno autorizado antes de elegir transición sin moverbytes o segregación.
No se fuerza elección arquitectónica sin esa evidencia; siguen otras familias.

[U06/U07 usuarios/grupos de aplicación](2026-10-28-2785-usuarios-grupos-y-credenciales.md)
precisa permisos/scope, operacióncompuesta core/Comedores, omisiónvsrevocación,
estado y grupos. U-CR1 elegida explícitamente: alerta/campo sensibles separados
de avisos genéricosM2 con permisos y scope ABM, sin conceder acceso de edición
a actor soloAdd. No afecta admin/Unfold #2789.

[U04/U05 lotes e importación](2026-10-28-2785-usuarios-lotes-importacion-m2.md)
concreta carga/job/seguimiento/reanudación/checkpoints, SMTP y CSV sensible existente
con guard propio. Actualización manualGET no es pollingJSON; sin idempotencia
global supuesta. No nueva elección o exposiciónmasiva de secretos autorizada.

[U08/regresión y U06 compuesto](2026-10-28-2785-usuarios-u08-formulario-compuesto.md)
conserva contratosToken/SIIS externos y caídaComedores tipada, sin copiar Profile
a nueva web; concreta permisos/campossección y configuraciónMobile suspendida.
Siguiente dependencia DU01 equipos/asignaciones; no otra elección en este tramo.

[DU01 equipo/asignación](2026-10-28-2785-duplas-equipo-asignaciones-m2.md)
precisa permisosANY export, Formsincoordinador, señalesUsuarios y asignación
scoped que cambia estadocomedor/accesoPWA. Previewbaja y fichaComedores son
dependencias siguientes, sin nueva regla o decisión obligatoria en este mapa.

[Previewbaja](2026-10-28-2787-confirmacion-baja-logica.md) conserva soft/hard técnico
y planrecalculadoPOST; [CO07.01/02 Comedores](2026-10-28-2785-comedores-legajo-base-m2.md)
fija Formcompuesto, scopesunión y mutacionesficha. Falta detalle de campos/UI y
admisión/convenio, no falsa lectura preparada ni nuevo permiso por API PWA similar.

[CO-I1/CO-I2 y contratos de imágenes/selectores](2026-10-28-2785-comedores-imagenes-i1-i2.md)
quedó resuelta con CO-I2: corrección coordinada de pertenencia al comedor
autorizado para legacy/API, sin permiso nuevo o arreglosfile ajenos. Evidencia
estática, no incidente ni mitigación implementada. Cinco modales y contribuciones de ficha
quedan inventariados, no contrato completo ni nueva exposición de medios.

[CO07.03 validación/convenio/tarjeta](2026-10-28-2785-comedores-validacion-convenio-tarjeta-m2.md)
precisa guardasdistintas, historialrepetido, variantesForm y centavoshistóricos
preservados. GETconvenio puedecrearregistro, no lectura pura; sin nuevadecisión.
ContribucionesDW/mes/capacitación siguen como dependencias de ficha a concretar.

[DW/mes/capacitaciones](2026-10-28-2785-comedores-dw-mes-capacitaciones.md)
precisa tres contribuciones: DWfallo/ausencia UIigual sin extenderC2, meslectura
con valoresnegativos, y revisióncertificadoPOST existente/lectura materializadora.
Sin otra elección, sin proveedor consultado ni ficha integral cerrada.

[CO02/CO06](2026-10-28-2785-comedores-intervenciones-observaciones-m2.md)
concreta intervención/documentos/observación y sus alcances distintos. Permisos
y objetosglobalesCO02 permanecen residuales documentados, no corrección por
analogía CO-I2/CDI-F2 ni descargasprotegidas acreditadas por título de catálogo.

[CO03/CO04 colaboradores/horarios/catálogos](2026-10-28-2785-comedores-colaboradores-actividades-catalogos.md)
conserva persona≠usuarioacceso, unregistro/horario y bajasdistintas de catálogos.
Sin nueva elección; PWAconsumidores/RENAPER/schemaimagen siguen evidencia pendiente.

[CO05 certificaciones y montos](2026-10-28-2785-comedores-certificaciones-montos-m2.md)
separa historial/descarga web, productor PWA de PDF backend y ABM de montos con
eliminación convencional. Modelo de montos requiere cierre; no se implementa
generación web inexistente ni se extiende protección documental CDI.

[CO01 estados/derivación/copia](2026-10-28-2785-comedores-nomina-estados-derivacion.md)
precisa modos con unmodelo, destinoEspera y copiaanteriorporID sinestadofuente.
Alta/asistencia siguenpendientes. Modelo de montosCO05 se precisó Decimal10,2,
≥1nonull/ceroválido y sinunicidadprograma; sin ejecución.

[CO01 alta/Ciudadano/PNUD](2026-10-28-2785-comedores-nomina-alta-ciudadano-pnud.md)
precisa ramas seleccionado/nuevo/sinDNI, omisión de flags sociales y efecto global
en Ciudadano, configuración de inscripciones y baja directa. Sin nuevo Formweb
de asistencia inferido ni nueva elección de producto en esta unidad.

[CO01 asistencia/documento](2026-10-28-2785-comedores-asistencia-documento-mensual.md)
separa historialweb React del productorPWA; bulk cierra con PDF y poblaciónactiva
distinta de selección. No nueva cargaweb o regeneraciónv2 inventada; constraints/
plantillafija/DTOresumen siguen evidencia pendiente.

[AD02 informes/documentos](2026-10-28-2785-admisiones-informes-documentos-m2.md)
fija fronteras borrador/submit/publicación/Word/revisión/fila documental React,
sin schema completo ni transiciones inventadas. AD01/AD03 mantienen dueños propios.

CO-I2 queda aceptada. Su [contrato de resultado mixto CO-I3/CO-I4](2026-10-28-2785-comedores-imagenes-i1-i2.md)
quedó resuelto con CO-I3: rechazar edición completa antes de cualquier efecto
por selección no autorizada/no resoluble; sin guardar parcialmente ni revelar datos ajenos.

## Continuación ágil autorizada

El responsable pidió: «Necesito apurar este proceso, asi que me gustaria que no me
pidas mas decisiones salvo que sea muy importante la decision humana, el resto
decidelo vos en base a lo ya decidido».

Resolver detalles técnicos conservadores con patrones y decisiones vigentes;
agrupar brechas por circuito, no crear una pregunta por DTO, campo o error. Preservar
comportamiento no cambiado y dejar defectos previos como riesgos separados, salvo
correcciones acotadas ya aprobadas. Escalar solo cambios importantes de negocio,
alcance, límites de seguridad, costos o autorización externa/irreversible. No
inferir implementación, acceso remoto, publicación o deploy de esta autonomía.

## Cierre estático del paquete INS-A B0–B2

El responsable aprobó continuar con preservación local en Git y preparación del
primer circuito, sin iniciar implementación. [Paquete existente](2026-10-27-2785-paquete-piloto-insumos.md)
reconciliado: no piloto de lectura como activación pública, fuentes históricas vs
ref local59a8f separadas de baseline, permisos independientes por acción/descarga,
F7 explícita y datasets/fixtures por ref. Manifiesto52casos/106combinaciones/13contratos,
9roles; INS-A38/78 e INS-B14/28, cero ejecuciones. Delete sin View cubierto sin
conceder View; retorno con query no cambia retornos fijos de mutaciones.

B0–B2 quedan coherentes documentalmente; entorno, API/UI, schemas reales, baseline,
contratos/persistencia y aceptación visual permanecen gates futuros. Sin fetch,
push/PR/deploy ni interferencia con #2789. El ref local no acredita desarrollo remoto actualizado.
