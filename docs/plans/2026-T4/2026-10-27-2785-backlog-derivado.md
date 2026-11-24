# Backlog derivado del plan aprobado (#2785)

Fecha: 2026-10-27. El responsable aprobó el plan, alternativa A, piloto de
Insumos y recomendaciones de transición después de recibir los cuatro documentos
de relevamiento. La aprobación no acredita comprensión técnica ni aceptación
funcional/visual; siguen los controles de AGENTS.md antes de decisiones materiales,
incorporación y activación. No hubo cambios de aplicación en esta etapa.

Plan: [migración integral](2026-10-27-2785-migracion-integral-react.md).
Diagnóstico: [R0](2026-10-27-2786-inventario-estatico.md),
[R1](2026-10-27-2787-base-compartida.md),
[transición](2026-10-27-2788-transicion.md).

## Sub-issues creadas y vinculadas al padre

Todas asignadas a `juanikitro`, abiertas. Su relación formal de sub-issue con
#2785 se creó y verificó por API; las dependencias están en los cuerpos y en
esta tabla, no se afirma haber configurado relaciones formales de bloqueo.

| Issue | Resultado | Dependencias / estado inicial |
|---|---|---|
| [#2798](https://github.com/secretarianaf/SISOC/issues/2798) | Definir contrato de contexto/navegación web sin cambiar PWA | Relevamiento estático iniciable; contrasta R0/R1 y #2788. Cierra dueño/nombre/rutas/campos/status y deriva implementación solo con contrato revisado |
| [#2799](https://github.com/secretarianaf/SISOC/issues/2799) | Comparación visual Django→React por URL | Requiere referencia visual y entorno sintético acordados; reutiliza Playwright. Coordina #2794 |
| [#2800](https://github.com/secretarianaf/SISOC/issues/2800) | Reproducir shell actual para el piloto | Bloqueada para implementar por #2798, #2799 y reconciliación de paquetes de #2794 |
| [#2801](https://github.com/secretarianaf/SISOC/issues/2801) | Incorporar app del piloto a tests/contratos/CI existentes | Dueño/nombre/contrato en #2798; coordina #2799/#2800 y los mismos archivos de #2794. No crear workspace vacío para cerrar |
| [#2802](https://github.com/secretarianaf/SISOC/issues/2802) | Consulta, filtros, paginación y descarga protegida de Insumos en React idéntico | Bloqueada para implementar hasta resolver dependencias anteriores y contrato API de lectura/baseline; no activa ni retira legacy |
| [#2811](https://github.com/secretarianaf/SISOC/issues/2811) | W1: compatibilidad de URL de espera CDF hacia ficha existente | Definición acotada derivada y relación con #2785 verificada; futuro código requiere autorización, no se crea pantalla nueva |

El contexto de sesión tiene primero un contrato porque los endpoints existentes
son token/PWA o específicos de VPSL. Una tarea de implementación del contexto
se derivará después de #2798; no se presupone que escribir su especificación
entregue ya un endpoint operativo. Esa dependencia debe completarse antes de
dar por operativo el piloto con sesión real.

## Orden para continuar

Bajo E2, continuar el [catálogo de 95 familias/214 slices](2026-10-27-2785-entregas-por-flujo.md),
sus contratos y la [aceptación/riesgos/retiro](2026-10-27-2785-aceptacion-riesgos-y-retiro.md).
No derivar 214 tickets automáticamente ni volver a pedir pasar al piloto por
defecto. Las tareas futuras salen de unidades con evidencia y contrato completo.

Continuación solicitada sobre los cinco puntos: [contratos/remediaciones](2026-10-27-2798-contratos-y-remediaciones.md)
y [reutilización/referencia INET](2026-10-27-2794-reutilizacion-y-referencia-visual.md).
Al contrastar reutilización se encontró I1/I2, decisión de referencia visual
antes de cerrar esa parte: conservar Django como baseline o tomar React INET
como referencia específica. El responsable eligió I1. No se
declaran completos los cinco puntos ni se derivan tareas visuales listas sobre
una referencia sin elegir. El resto sigue con las decisiones G1/P1/C2/E2 vigentes.

Con I1 resuelta se profundizó el [registro por ruta y cobertura](2026-10-27-2786-contratos-y-cobertura-por-ruta.md):
614 declaraciones, 602 símbolos, 81 forms localizados; grafo de 509 templates HTML
y 4 de texto backend, más 148 entradas de assets y 5 paquetes frontend.
La cobertura integral contempla las 95 familias y sus obligaciones por ruta,
sin capturas/fixtures ejecutadas ni roles inventados. Quedan referencias
dinámicas y retornos/helpers identificados para revisar, no URLs omitidas.

Se distinguieron GET 405/POST redirect de importaciones de pantallas inexistentes,
OCR `.txt` de templates, emails backend y paths Unicode válidos. La referencia
HTML que sigue sin archivo localizado corresponde a espera CDF: se eligió
[W1](2026-10-27-cdf-lista-espera-decision.md), sección de ficha existente y
compatibilidad de URL, derivada a #2811. No se declara fallo de producción ni
se inventa una pantalla. La elección afecta solo ese recorrido CDF02.

Avance publicado y verificado en #2785, #2786, #2787, #2788 y #2799, estados OPEN
preservados. I1 quedó registrada; W1/W2 estaba pendiente en ese avance. Se verificaron 41
artefactos, 614 IDs de cobertura coincidentes con fuente, 95 familias y el grafo
de consumidores sin problemas estructurales/documentales. Todos los estados de
captura/runtime permanecen sin ejecutar. Archivos locales sin commit/push.

Después se eligió W1. Se creó/asignó #2811 y se verificó como sub-issue formal
de #2785, sin iniciar su implementación. Las [fichas prioritarias](2026-10-27-2785-fichas-prioritarias.md)
refinan el piloto y la compatibilidad por contrato/negativos. Retornos y bases
permitieron clasificar las 614 declaraciones en fuente; 632 símbolos/bases,
85 forms y 196 archivos Python leídos, sin importar Django. Cinco aristas
dinámicas de templates tienen ramas fuente enumeradas; diez URLs de importación
y nueve paths React INET quedaron materializados en el registro.

La decisión [M2](2026-10-27-2788-avisos-y-unidad-activacion.md) queda elegida tras
aclarar que todos los formularios del alcance deben terminar en React. Se descarta
el puente M1. Activar por circuitos completos con feedback propio y retornos
permitidos inventariados (incluidos next/referrer); los grupos pueden abarcar
varios slices. Desarrollo y comparación por partes siguen permitidos bajo futura
autorización; no se reabre E2. Excepción admin/Unfold #2789 confirmada y fuera de esta migración.

Estado posterior a las definiciones: G1, P1, C2 y E2 elegidas. Unfold #2793 e INET
#2794 están integrados; ver [delta de base](2026-10-27-2786-delta-integraciones.md).
El [paquete de ejecución del piloto](2026-10-27-2785-paquete-piloto-insumos.md)
queda como referencia futura: el responsable eligió E2 y pidió profundizar la
planificación completa. No se vuelve a solicitar el cambio de fase. No se
iniciaron cambios de aplicación ni entorno.

### Definiciones adicionales nacidas de R0

La [matriz de 95 familias](2026-10-27-2786-matriz-flujos.md),
[brechas por consumidor](2026-10-27-2786-2788-brechas-por-consumidor.md) y
[secuencia integral](2026-10-27-2785-secuencia-por-flujos.md) concretan trabajo
más allá del piloto. Se crearon y vincularon al mismo padre:

| Issue | Resultado acotado | Dependencias / límites |
|---|---|---|
| [#2805](https://github.com/secretarianaf/SISOC/issues/2805) | Contrato web de consulta de centros CDF sin exponer API keys | #2798 y controles entre runtimes; comparar alcance/NoCountPaginator con vistas HTML, sin ABM ni cambio de API integración |
| [#2806](https://github.com/secretarianaf/SISOC/issues/2806) | Transición de DDJJ pública PAS por invitación | #2788/#2799; guest, CSRF y estados 400/404/410, consumo transaccional y PDF backend; sin abrir padrón/descarga/media |
| [#2807](https://github.com/secretarianaf/SISOC/issues/2807) | JSON por aporte remoto de Ciudadano 360 | Dueños/backend, #2798 y #2808; convivencia del HTML actual, renderer React final y checklist 3 de verticales |
| [#2808](https://github.com/secretarianaf/SISOC/issues/2808) | Controles de sesión web en APIs de verticales | #2788/#2798 y contratos por dominio; comparar alternativas/costo/disponibilidad antes de crear guard/protocolo/call remoto |

Las cuatro son de definición estática y están abiertas/asignadas a juanikitro;
no autorizan implementar auth/infra, consultar datos reales ni arrancar servicios.
No se crearon tickets por cada una de las 95 familias. Las dependencias se
expresan en cuerpos/documentos; no se afirman bloqueos formales configurados.

Detalle preparado para revisión: [#2805](2026-10-27-2805-contrato-lectura-cdf.md)
conserva alcance/paginación NoCount y separa acceso de lista/ficha/panel usuarios;
[#2808](2026-10-27-2808-alternativas-control-web.md) compara gate+constancia
firmada, política HTTP separada y gate solo en core/red privada. El callback al
mismo pool introduce un ciclo de espera bajo concurrencia; es riesgo del diseño
nuevo, no incidente de producción verificado. El responsable eligió G1; el
[registro](../../registro/decisiones/2026-10-27-2808-control-web-g1.md) delimita
esa elección. El protocolo y namespaces siguen pendientes, sin implementación.
El [borrador de protocolo G1](2026-10-27-2808-protocolo-g1.md) define payload,
transporte, errores, compatibilidad y matriz de pruebas. La preparación de URLs
y firmas futuras se verificó solo con bibliotecas locales/datos sintéticos;
recepción real, presupuesto temporal y Django objetivo siguen pendientes.

### Secuencia del piloto y remanente

Detalle de #2806: [DDJJ pública PAS](2026-10-27-2806-ddjj-publica-pas.md) y
[manifiesto visual](2026-10-27-2806-pas-manifiesto-visual.json). La sesión
restringida puede bloquear el enlace que funciona para un visitante anónimo.
El responsable eligió P1 (preservar), registrada en la
[decisión PAS](../../registro/decisiones/2026-10-27-2806-ddjj-pas-p1.md).
La elección queda resuelta; contrato ejecutable y pruebas HTTP pendientes.

Detalle de #2807: [aportes de Ciudadano 360](2026-10-27-2807-aportes-ciudadano360.md)
e [índice de evidencia](2026-10-27-2807-aportes-evidencia.json). Ocho bloques,
cuatro runtimes y contraste de datos reales vacíos con indisponibilidad.
El responsable eligió C2 (excepción mínima `No disponible`), registrada en la
[decisión Ciudadano 360](../../registro/decisiones/2026-10-27-2807-ciudadano360-c2.md).
La elección queda resuelta; implementación y diff visual siguen pendientes.

1. #2798 y completar R0 por contratos/permisos; preparar el manifiesto y diseño
   de ejecución de #2799, sin levantar entornos no autorizados.
2. Cerrar contrato, nombre/rutas de app y referencia visual; derivar la
   implementación del contexto mínima y comprobar compatibilidad PWA/SIIS.
3. #2799, #2800 y #2801 dentro del alcance mínimo, secuenciando los archivos
   compartidos y coordinando #2794. No declarar «base lista» por config escrita.
4. #2802 y aceptación de su recorrido con datos sintéticos, positiva y negativa;
   medir esfuerzo real y problemas antes de extrapolar el calendario.
5. Descomponer las familias restantes del plan en tareas por flujo que conserven
   permisos, archivos, validaciones y diseño. No abrir tickets gigantes por
   módulo ni dar por migrado INET mientras #2794 no tenga evidencia propia.
6. Implementar transición de identidad, activación y retiro en tareas separadas
   cuando sus contratos estén cerrados; repetir diff acumulado final por URL.

## Pendientes de las tareas iniciales

- #2786: clasificación y productores de las doce rutas no nominales no API/admin
  resueltos; falta composición activa y auditoría de permisos/objeto/provincia,
  acciones y contratos por cada flujo. Categorizar prefijos no prueba cobertura
  funcional. Permanece abierto.
- #2787: diagnóstico y cinco tareas derivadas disponibles; debe contrastarse
  contra R0 final y completar consumidores/regresiones. Permanece abierto.
- #2788: orientación D1–D6 aprobada; faltan contratos, nombres/mapeos exactos,
  control de comprensión previsto por AGENTS.md y fichas de implementación de
  identidad/activación. Permanece abierto.

La evidencia documental sigue local y sin commit/push hasta autorización para
publicarla. Los issues son autocontenidos y enlazan el padre/antecedentes; no
incluyen enlaces a archivos de una rama remota inexistente. Cuando exista PR
documental autorizado se agregarán los enlaces de documentos/SHA publicados.

## Continuación de contratos y manifiesto

- #2798: [contrato detallado](2026-10-27-2798-contrato-contexto-web.md),
  [OpenAPI documental](2026-10-27-2798-web-session.openapi.json) y
  [referencias del sidebar](2026-10-27-2798-sidebar-referencias.json). Concreta
  propuesta de app/rutas, datos/status, estados forzados, consumidor y compatibilidad;
  no implementa ni cierra la revisión material de contrato.
- #2799/#2802: [contrato y guía de paridad](2026-10-27-2799-2802-paridad-insumos.md)
  y [manifiesto](2026-10-27-2799-insumos-manifiesto-visual.json): 18 casos,
  38 combinaciones iniciales y siete checks de contrato. Sin ejecución; acceso
  anónimo marcado bloqueado hasta resolver guard compatible.
- No se creó tarea de implementación del contexto como si el contrato estuviera
  aceptado. No hubo cambios de permisos/auth/infra, datos, app o schema runtime.

## Validación de publicación

El conector GitHub permitió lectura pero rechazó crear issues con
`403 Resource not accessible by integration`. Se usó `gh` con la sesión
disponible, cuyos permisos de repositorio se verificaron, para crear las cinco
tareas y asociarlas mediante `POST /repos/secretarianaf/SISOC/issues/2785/sub_issues`.
Se preservaron las tres sub-issues iniciales. No se enviaron comentarios,
notificaciones propias ni mensajes a personas; GitHub conserva su comportamiento
normal de notificaciones al crear/asignar issues.

Se verifica por GET la lista final, asignaciones, estado y dependencias en los
cuerpos. No se cierra ningún issue ni se modifica #2789. Sin tests/servidores/DB,
Docker, UI implementada, commit, push, merge ni deploy.

## Historial de publicación y estado actual

Los documentos de detalle #2805 y alternativas #2808 están guardados y enlazados
localmente. Dos intentos de actualizar sus avances y los de #2785/#2788 mediante
`gh` fallaron al conectar con `api.github.com`, antes del primer PATCH. No hubo
actualización parcial de ese bloque ni se afirma estado remoto actual nuevo.
Reintentar publicación después de recuperar conexión, leyendo cuerpos actuales
y preservando el trabajo ajeno; los bloques de avance preparados son idempotentes.

Después de esos intentos, el responsable eligió G1 explícitamente. La elección
y su registro están guardados localmente; no se afirma publicada esa actualización.
La revisión del contrato concreto y namespace sigue pendiente. No hay un proceso
nuevo ni implementación aprobados por omisión y no se vuelve a solicitar G1/G2.

Actualización posterior: recuperada la conexión, se publicó y verificó el bloque
`react-g1-protocolo-2026-10-27` en #2808 y #2785, conservando sus estados OPEN y
los cuerpos previos. Una primera comparación local falló por finales CRLF;
la lectura posterior confirmó contenido y se normalizaron solo los finales de
línea para verificar. No fue un fallo de publicación. Ese avance referencia
archivos locales sin commit/push, no documentos ya disponibles en GitHub.
No se afirma publicada la actualización anterior específica de #2805/#2788.

Continuación posterior: P1 PAS registrada y manifiesto actualizado; publicados
y verificados avances en #2806, #2807 y #2785, todos OPEN. Ocho aportes de
Ciudadano 360 y 146 expresiones fuente indexados localmente; C1/C2 estaba pendiente
en ese avance y fue resuelta posteriormente por elección explícita de C2.
Documentos sin commit/push. No se declara que esas referencias locales estén
disponibles como archivos en la rama remota.

Último avance: C2 registrada, manifiesto Ciudadano 360 con 31 casos/62
combinaciones sin ejecutar y delta Unfold/INET integrado preparados. Publicados
y verificados bloques en #2807, #2786, #2787, #2788 y #2785, estados OPEN
conservados. E1/E2 de fase queda pendiente; G1/P1/C2 no se vuelven a solicitar.
29 artefactos documentales/JSON verificados sin problemas. Sin aplicación,
entorno, capturas, commit/push ni desplegar; documentos continúan locales.

El responsable eligió después E2 y aclaró que el objetivo es profundizar la
planificación integral. E1/E2 queda resuelta. Se prepararon catálogo de 95
familias/214 slices, perfiles de contrato y negativos, dependencias por entrega,
orden recomendado y aceptación/riesgos/retiro. No se crean 214 issues ni se
declaran contratos cerrados por esa cuenta. Los siguientes avances siguen siendo
documentales; no se solicita otra vez iniciar implementación.

Publicado y verificado ese alcance E2 y la profundización integral en #2785,
#2786, #2787 y #2788; estados OPEN preservados y criterios sin marcar por rutina.
Validación local: 32 artefactos, 95 familias exactas, 214 IDs de slice únicos,
614 declaraciones fuente + 156 exclusiones, perfiles/dependencias existentes y
18 riesgos, sin problemas de JSON, enlaces, tablas ni whitespace. Check documental
oficial correcto. Sin app/API, entorno, DB, capturas, CI, commit/push o deploy.

Avance posterior: W1 elegida, registrada y derivada a #2811, subissue de #2785,
asignada y OPEN. Seis fichas prioritarias refinan contratos, validación y
dependencias sin declarar listas las 214 propuestas. Registro fuente normalizado:
614 rutas asignadas, 632 definiciones y 85 formularios; cobertura visual añade
avisos y cadenas de retorno, sin capturas ejecutadas. Decisión M1/M2 pendiente
sobre feedback entre formularios Django y lecturas React; recomendación del agente
M1 acotada al ingreso de página, sin elegirla por el responsable.

Publicados y verificados estos avances en #2785, #2786, #2787, #2788, #2799,
#2800, #2801 y #2802, conservando estados OPEN. Validación local de 44 artefactos:
JSON, referencias, enlaces y whitespace correctos; check oficial de documentación
sin referencias rotas. Documentos locales sin commit/push; E2 sigue vigente,
sin aplicación, DB, servidores, capturas, CI ni despliegue.

Continuación vigente: el responsable aclaró que todos los formularios deben ser
React y eligió la orientación M2. Se registró la decisión en ADR, se descartó
planificar el puente M1 y se ajustaron fichas, secuencia, retiro y política de
activación estructurada. Desarrollo/comparación por slices no equivale a activar
un circuito con formularios Django pendientes. Excepción admin/Unfold #2789 confirmada por el responsable, sin modificar su trabajo paralelo. Publicado y verificado en #2785,
#2786, #2787, #2788, #2799 y #2802, manteniendo estados OPEN. Validación de 45
artefactos y check documental oficial correctos; sin aplicación, capturas, CI,
commit/push ni deploy. E2 continúa.

Continuación de los cinco pendientes: contrato Insumos INS-A/INS-B con rutas,
campos, opciones, permisos por acción, multipart, errores, feedback, efectos y
retornos concretos; propuesta única `/api/web/insumos/`. Catálogo conserva sus
214 IDs y explicita dos grupos de activación sin declarar listas las demás
familias. Fichas F7/F8 describen formularios futuros, sin nuevos tickets masivos.
Manifiesto Insumos: 51 casos visuales, 104 combinaciones caso/viewport, doce casos
de contrato y ocho roles; todas las capturas sin ejecutar, baseline sin aceptar.
G1-E01–E07 concretan experimentos futuros, sin medir ni fijar parámetros ficticios.
INET incorpora contraste por operación y efectos para reutilizar el código real.

Se encontró decisión material R1/R2 de edición de centros INET: la API añade
Change al predicado de centro que usa la vista Django, mientras el seed CFP no
incluye Change. Impacto real no medido; no se cambiaron permisos ni se eligió por
omisión. Recomendación del agente R1, preservar contrato Django con alcance real.
El detalle y alternativas están en
[contrato de decisión](2026-10-27-2794-permisos-edicion-centro.md).

Publicados y verificados avances en #2785, #2786, #2787, #2788, #2799, #2802 y
#2808, conservando estados OPEN. Validación estructural de 49 artefactos y check
documental oficial correctos, más coherencia de grupos/casos/roles. Documentos
locales sin commit/push; sin aplicación, DB, servidores, capturas, CI o deploy.
Admin/Unfold #2789 queda aparte. E2 y decisiones anteriores siguen vigentes.

R1 fue elegida explícitamente por el responsable («r1»): conservar View y el
predicado Django de edición de centros, sin Change extra para la rama referente;
provinciales mantienen Change/scope. R2 descartada. Se registró ADR y matriz
de diez perfiles/condiciones con positivos y rechazos, sin cambiar código ni
privilegios. Plan, fichas, secuencia, reutilización y cobertura actualizados;
la decisión salió de pendientes y quedó resuelta, sin afirmar implementación.
Publicación y lectura verificada en #2785, #2786, #2787, #2788 y #2799, todos
OPEN preservados. Validación de 50 artefactos y check documental oficial correctos.
Sin app, DB, pruebas runtime, capturas, CI, commit/push o deploy. E2 continúa.

Continuación de identidad: contratos M2 ID-A–ID-E/EQ-A y manifiesto de 52 casos
visuales/104 combinaciones y quince checks de contrato, todos sin ejecutar.
Campos, efectos de sesión/reset/cuenta y cola de encuestas precisados desde
fuente; entrada estática no debe recibir tokens/uid/next/query privada.
Suplemento auth reconcilia ocho rutas estándar con registro y fuente local
Django 5.2.15 (objetivo 5.2.17 pendiente de contraste): tres paths adicionales,
cinco reemplazados por declaraciones anteriores; no afirmar resolver ni loader.
U02.03 agrega cambio voluntario al catálogo, ahora 215 propuestas en 95 familias,
conservando los 214 IDs anteriores e inventario literal 614/770 sin cambios.

R1 está resuelta. Nueva decisión S1/S2 de gestión de encuestas ante respuesta
obligatoria pendiente: el middleware actual exceptúa esas rutas con Change;
gate universal ready lo quitaría. Recomendación S1 acotada; no modificar control
ni elegir por omisión. Ver
[alternativas y aceptación](2026-10-27-2788-excepcion-gestion-encuestas.md).
Publicados y verificados avances en #2785, #2786, #2787, #2788, #2798, #2799 y
#2808, conservando estados OPEN. Validación documental de 54 artefactos y check
oficial correctos; coherencia adicional de grupos, IDs, roles/sesiones y rutas.
Documentos siguen locales sin commit/push; sin app, entorno, mail, datos reales,
capturas, CI o deploy. Admin/Unfold aparte y E2 vigente.

El responsable eligió S1 («s1»). Registrada en ADR; S2 descartada y S1 retirada
de pendientes. Mapa fuente de veinte rutas de encuestas: diecisiete gestión/
descarga, tres respuesta/remediación, con permisos y métodos propuestos separados.
No es allowlist ejecutable ni prueba de dispatch. Contexto mantiene encuesta
pendiente, sin falsear ready; Change no concede acciones ni elude otros requisitos.
El manifiesto de identidad conserva 52 casos/104 combinaciones y pasa de quince
a veinte checks de contrato, todos sin ejecutar.

La continuación de widgets encontró Select2/jQuery real en CDF/Inspecciones y
patrón React Autocomplete existente en VPSL. Se preparó
[J1/J2](2026-10-27-2787-selectores-react-j1-j2.md): encapsular plugin actual o
reproducir control/interacción en React con el mismo diseño. Recomendación J2,
sin elegir ni incorporar dependencias. No usar aparición en script global como
prueba de consumidor de otros plugins o editores.

Actualizados y verificados los bloques propios de avance en #2785, #2786, #2787,
#2788, #2798, #2799 y #2808, conservando estado OPEN y cuerpo externo al bloque.
Validación de 57 artefactos y check documental oficial correctos; comprobaciones
semánticas de la política y manifiesto. Documentos locales sin commit/push; sin
app, permisos reales, entorno, capturas, CI o deploy. E2 y admin aparte vigentes.

El responsable eligió J2 («j2»): selectores con comportamiento React y diseño
actual, sin trasladar jQuery/Select2 a esos nuevos circuitos. J1 descartada;
registrada ADR y cerrada la elección en cobertura, sin cambiar dependencias.
La continuación precisó opciones múltiples CDF, categoría/actividad y contratos
remotos de Inspecciones (mínimos, límites distintos, iniciales, padres y payload).
Actividad CDF retorna a centro_detail: dependencia M2 concreta de ficha destino,
sin extenderla a todo el módulo por intuición.

Manifiesto de selectores: 28 casos visuales/56 combinaciones y doce checks de
contrato, todos sin ejecutar; paths contrastados con nombres específicos del
registro congelado, sin resolver HTTP/IDs reales. Catálogo sigue 215 propuestas.
Se encontró rama sin catch en carga de actividades CDF; causa de código analizada
sin reproducir un incidente desplegado. Nueva
[decisión L1/L2](2026-10-27-2787-error-carga-actividades-l1-l2.md): paridad del
fallo actual o aviso/reintento acotado al selector, recomendación del agente L2.
No extender C2 ni inventar resultados de ejecución; ninguna opción implementada.

Actualizados y verificados bloques propios en #2785, #2786, #2787, #2788, #2798,
#2799 y #2808, estados OPEN preservados. Validación documental de 61 artefactos
y check oficial correctos, más coherencia de casos/rutas/decisiones. Documentos
locales sin commit/push; sin app, permisos, entorno, capturas, CI o deploy.
Skills registro-cambios y systematic-debugging para trazabilidad y límites de
evidencia. E2 y excepción admin/Unfold #2789 vigentes.

## 2026-10-28: L2 elegida para carga de actividades CDF

El responsable eligió «l2». Se registra la [decisión acotada](../../registro/decisiones/2026-10-28-2787-carga-actividades-l2.md): error visible y reintento manual solo del GET de opciones de la categoría actual, conservando otros campos, sin actividad inválida ni repetición de POST. L1 queda descartada; no se amplía C2.

Contratos, cobertura y manifiesto de selectores reflejan L2. Permanecen 28 casos visuales/56 combinaciones/12 checks de contrato sin ejecutar; E2 no autoriza implementación ni capturas. Tras autorización explícita del responsable, se actualizó el bloque propio de planificación en #2785, #2786, #2787, #2788, #2798, #2799 y #2808 usando la sesión gh previamente utilizada. Se verificaron cuerpo completo y estado OPEN de cada issue, preservando el contenido externo al bloque. No se tocó #2789 ni se publicaron los documentos locales mediante commit/push.

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

## Consolidación sin otro tracker

Se indexaron los contratos posteriores dentro del catálogo existente y de la
matriz vigente de cierre:95 familias/215 IDs conservados. La estrategia está
definida, los niveles de preparación quedan separados de runtime/visual y los
campos finales se cierran por slice. AD02 incluye regla de schema contextual,
borrador guardado ante error de publicación, revisión y borrado documental;
no queda una entrevista por cada detalle. No publicación remota en esta continuación.

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
