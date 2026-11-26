# Ciudadano 360: aportes JSON y disponibilidad (#2807)

Fecha: 2026-10-27. Estado: **C2 elegida; contrato ejecutable y validación pendientes**.
La excepción visual explícita «c2» está en el
[registro de decisión](../../registro/decisiones/2026-10-27-2807-ciudadano360-c2.md).
Fuente inspeccionada: `13d367f81d6da879f1fc3e43532a894e034dc557`, sin confirmar
despliegue. Continúa el [plan integral](2026-10-27-2785-migracion-integral-react.md)
y las [brechas por consumidor](2026-10-27-2786-2788-brechas-por-consumidor.md).
El [índice de evidencia](2026-10-27-2807-aportes-evidencia.json) vincula los ocho
bloques con dueño, proveedor, template y expresiones fuente. No es un schema API.

## Recorrido existente y autorización observada

`src/backends/kernel/ciudadanos/views.py`, `CiudadanosDetailView`, exige sesión
y `ciudadanos.view_ciudadano`, carga el ciudadano y solicita ocho fragmentos.
`contribucion_detalle_ciudadano` exige ese mismo permiso, rechaza nombres no
registrados localmente y consulta el ciudadano por PK. Los proveedores reciben
ciudadano y logger, no el usuario/request: no suponer que filtran por provincia,
centro o equipo del solicitante. No se demostró alcance de objeto adicional en
ese recorrido ni se ejecutaron tests de autorización.

`src/backends/kernel/ciudadanos/detail_contributions.py` resuelve proveedor local
o backend dueño. La llamada remota conserva sesión con `outbound_headers`,
timeout de cuatro segundos y sin seguir redirects. Error de red o status distinto
de 200 produce cadena vacía; un 200 se consume como texto. Eso no distingue por
sí solo ausencia de registros, denegación ni una plantilla equivocada.

G1 agrega procedencia de evaluación de requisitos web para APIs nuevas; no crea
permisos de dominio que no existen ni reemplaza el permiso de consulta Ciudadano.
No imponer automáticamente el scope de consulta de centros CDF al resumen 360:
son recorridos diferentes. Una corrección de acceso requiere evidencia y decisión
propias, sin ampliar datos ni agregar permisos por intuición en esta migración.

## Ocho bloques y cuatro runtimes dueños

| Bloque actual | Runtime / app | Datos mínimos candidatos según presentación actual |
|---|---|---|
| `comedores` | comedores / comedores | Nómina actual e histórica, nombre/tipo/provincia/municipio del espacio y fecha, destinos de navegación existentes |
| `comedores_colaboraciones` | comedores / comedores | Espacio, fechas de alta/baja, actividades y acciones del modal existente |
| `pwa` | comedores / pwa | Tres indicadores de perfil: pueblo originario, situación de calle y persona con celiaquía; conservar etiquetas actuales |
| `pwa_badges` | comedores / pwa | Presentación de badges actuales basada en los indicadores pertinentes; no inferir diagnóstico nuevo |
| `celiaquia` | celiaquia / celiaquia | Resumen de legajo actual, estados/cruce/cupo, titular/revisión e historial ya mostrado |
| `vat` | vat / VAT | Programas, vouchers, créditos, inscripciones/ofertas y resumen de asistencia ya calculado por el proveedor |
| `centrodefamilia` | cdf / centrodefamilia | Centro/actividad/fecha de participaciones según orden actual |
| `centrodefamilia_monto` | cdf / centrodefamilia | Suma de precios de participaciones inscritas, con formato monetario actual; no sumar desde cadenas formateadas en React |

El registro remoto es `src/backends/config/backends.json`; los proveedores están
en `ciudadano_detail.py` de cada app. Los templates y todas sus expresiones están
en el índice, incluyendo estructuras condicionales, no solo nombres de modelos.
La UI independiente Celiaquía permanece fuera de la migración: este bloque
incrustado en Ciudadano 360 sí debe renderizarse en React con contrato de su dueño.
PWA no se reimplementa; solo se transforma su aporte existente a esta pantalla.

## Contrato JSON propuesto para revisión

Conservar fragmentos HTML para consumidores Django mientras se agrega una
proyección JSON explícita en cada dueño. Reutilizar sus consultas/cálculos sin
serializar ORM completo ni copiar servicios al kernel. El dueño autoriza y
construye únicamente los datos necesarios para el bloque visible.

La propuesta separa resultado válido con registros, resultado válido vacío,
denegación y no disponible/payload inválido. No envolver cualquier excepción en
una lista vacía o cero. La representación de falla en pantalla sigue C2,
elegida por el responsable; esta distinción no habilita mostrar datos privados.

La URI candidata debe ser del contrato web nuevo, ligada a ciudadano y aporte
permitido en ese runtime; no permitir origen/URL arbitrario o contribución de
otro backend. No fijar ocho endpoints por reflejo: resolver una representación
por dueño cuando comparta datos, sin crear un agregador que importe verticales.
La definición final debe declarar campos/tipos/nulls, orden, formato/locale y
destinos de enlaces. No emitir un schema operativo ni generar tipos desde este
índice de expresiones de templates.

Reutilizar transporte de sesión y G1 cuando se concrete, sin llamada circular
al core, cache de identidad, reintentos de mutaciones ni nuevo servicio. Una
llamada a aporte que se implemente fuera del proxy principal también debe emitir
y comprobar su constancia con audiencia/target correctos. La autorización de
la página no convierte en confiable una URL provista por el cliente.

Los destinos mantienen rutas legacy hasta migrar cada flujo. No usar HTML
remoto, `dangerouslySetInnerHTML` o extracción de texto de fragmentos como contrato
final. Aislar el renderer React de cada bloque con datos tipados y fallback
acordado; no mover los cálculos de VAT/CDF al navegador por comodidad.

## Riesgo confirmado en fuente: un cero puede ser indisponibilidad

El proveedor CDF `src/backends/cdf/centrodefamilia/ciudadano_detail.py` captura
excepciones durante parte de la consulta y devuelve lista vacía/costo cero.
Su template de monto formatea cero. Además, la tarjeta de
`src/backends/kernel/ciudadanos/templates/ciudadanos/ciudadano_detail.html` usa
`default:'$0.00'` si el fragmento de monto está vacío. Por tanto, un timeout o
no-200 remoto puede acabar en `$0.00` sin haber consultado el monto.

Esto se acredita por lectura de ambas ramas, no por provocar una caída real.
No se afirma que cada fallo produzca cero: un queryset perezoso puede fallar
después del try durante renderizado, y no se recorrieron todas las excepciones.
El cero de una agregación exitosa sin participaciones inscritas sí es válido.
La UI actual mezcla casos que el nuevo contrato debe distinguir internamente.

## Decisión material C1/C2 antes de cerrar la presentación

| Alternativa | Resultado ante aporte no disponible | Ganancia | Consecuencia |
|---|---|---|---|
| C1. Conservar presentación actual | Mantener omisiones y `$0.00` donde hoy existe ese fallback; contrato/observabilidad pueden distinguir la causa internamente | Igualdad estricta de los estados actuales, sin excepción visual | El usuario puede interpretar cero como dato consultado aunque la fuente no haya respondido |
| C2. Distinguir indisponibilidad, excepción mínima | Mantener layout y resto de UI; en valores que hoy podrían fingir cero/ausencia, mostrar `No disponible` cuando la consulta falla. Un cero exitoso sigue siendo cero; no agregar badges sobre datos sensibles ausentes | Evita presentar datos desconocidos como resultados confirmados | Cambia el estado visible de degradación y requiere aprobar esta excepción a la igualdad visual, además del diff correspondiente |

**Recomendación del agente: C2**, con excepción acotada a indisponibilidad y
sin rediseño ni nuevos controles. La exigencia de diseño idéntico sigue vigente
para estados normales. El responsable eligió C2 explícitamente; C1 queda como
alternativa descartada. No se vuelve a pedir la elección. No se extiende la
decisión a otros dashboards ni módulos, ni se presenta como UI implementada.

La distinción del nuevo endpoint exige revisar los catch de sus proveedores:
no basta con que el transporte haya recibido 200 si el proveedor ya convirtió
un error en cero. Mantener compatibilidad del fragmento HTML durante transición;
no cambiar silenciosamente el manejo global de errores de servicios existentes.

## Evidencia posterior requerida

| Prueba | Resultado requerido |
|---|---|
| Ocho bloques con registros y vacíos reales | Campos, cálculos, orden, enlaces y condición de visualización idénticos al bloque actual |
| Fallo remoto, timeout, redirect, 403 y JSON inválido | No convertir en datos válidos; aplicar C2 sin caída total de la ficha ni revelar datos denegados |
| Error del proveedor antes de construir JSON | No responder éxito cero al endpoint nuevo; no confundir 200 con evaluación exitosa |
| Sesión anónima/expirada, flags y permiso Ciudadano ausente | Sin datos privados ni bypass por nombre/PK/runtime; G1 no sustituye autorización |
| Datos con badges falsos frente a aporte no disponible | No inventar `No` ni un diagnóstico a partir de un error |
| Monto cero real frente a CDF caído | Caso separado y aceptación explícita de la presentación elegida |
| Composición completa y runtimes aislados | Mismo resultado autorizado, sin imports cruzados ni callback circular |
| Navegación, modales y todos los tabs de ficha | Diff de URL/estado/rol en escritorio/móvil, incluyendo monto, badges y colaboraciones fuera del tab principal |

Solo fixtures sintéticas, sin expedientes/identidades reales. Baseline y candidato
deben estar fijados y aceptados, con fuentes/iconos/animaciones estables. No hay
capturas ni baseline aceptado de Ciudadano 360 en esta tarea.

El [manifiesto visual C2](2026-10-27-2807-manifiesto-visual.json) prepara 31 casos
y 62 combinaciones escritorio/móvil, todos sin ejecutar. La diferencia autorizada
solo cubre el estado afectado; no permite autoaceptar otros cambios de captura.

## Checklist 3 de verticales independientes

| Ítem de la guía | Evidencia y pendiente |
|---|---|
| Contrato sin importar modelos/api.py del dueño en core | HTML/registro identificados; JSON mínimo definido como propuesta, pendiente schema por dueño |
| Consulta/autorización/template en dueño y registro | Ocho proveedores/templates y cuatro runtimes en índice; pendiente implementación y pruebas de acceso |
| Helpers conservando sesión/headers | Identificados `outbound_headers`/proxy; pendiente integración G1 para cada vía nueva |
| Timeout/caída/403/vacío/payload inválido | Ramas fuente identificadas; C2 elegida, contrato y pruebas posteriores pendientes |
| Composición completa y runtimes separados | Pendiente autorización/ejecución de entorno; no se acredita por inspección estática |

Aplicación de `verticales-checklist` según
`docs/desarrollo/verticales_independientes.md`, sin checklist ni herramienta nuevos.
Validación actual: referencias documentales/fuente, consistencia de ocho bloques
y registro. Sin tests de aplicación, red, DB, servidores, UI, build, CI ni deploy;
no se alteran código, datos, permisos, #2789 ni trabajo de INET #2794.
