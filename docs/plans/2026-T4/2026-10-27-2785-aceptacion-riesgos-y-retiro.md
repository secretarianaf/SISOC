# Aceptación, riesgos y retiro de UI Django (#2785)

Estado: **E2, planificación exclusivamente**. Complementa el
[plan integral](2026-10-27-2785-migracion-integral-react.md) y el
[catálogo de entregas](2026-10-27-2785-entregas-por-flujo.md). No añade un tracker,
pipeline ni herramienta: usa issues, PRs, comandos y artefactos existentes.
Los controles siguientes son criterios para la implementación futura, no
validaciones ejecutadas ni capacidades demostradas.

## Criterio final M2: todos los formularios React

Para cada circuito registrar lectura, altas, edición, bajas, acciones, modales,
validaciones y retornos (incluidos next/referrer permitidos). No activar hasta
que sus formularios y avisos sean React y tengan pruebas funcionales y diff
visual por URL/estado/rol/viewport. Login, cuenta, remediaciones y formularios
públicos también entran. Inventario de formularios Django pendientes del alcance
debe quedar vacío antes de cerrar la migración; conservar validadores backend no
es conservar UI. No basta quitar archivos: comprobar rutas, enlaces y usos reales.
Excepción admin/Unfold #2789 confirmada: permanece fuera y no se toca su trabajo paralelo.

## Unidad verificable y evidencia de salida

Una entrega cubre un recorrido observable con sus rutas, permisos, operaciones
y estados. No se acepta «modelo migrado», «template portado» o «API disponible»
como prueba de que ese recorrido funciona. No exigir cerrar todo un vertical
si una entrega puede convivir de forma compatible con enlaces legacy.

Antes de derivar implementación, completar en la ficha existente del issue:

| Dato | Contenido que debe quedar concreto |
|---|---|
| Fuente | SHA, backend dueño, definiciones de URL/vista/service/template y consumidores actuales |
| Resultado | Un caso positivo y uno negativo en términos del usuario; acciones y estados incluidos |
| Rutas | Paths resueltos con fixtures, aliases y query relevantes, navegación y resultados POST con UI |
| Contrato | Campos visibles/editables, filtros, orden, paginación, nulls, errores, permiso y alcance; API reutilizada o nueva justificada |
| Efectos | Transacción, archivos, jobs, notificaciones/integraciones y comportamiento al fallar o repetir |
| Presentación | Layout/tema/fuentes vigentes, responsive, foco/teclado, estados y excepción aprobada si existe |
| Dependencias | Base integrada, cambios comunes, contrato de identidad y compatibilidad entre versiones |
| Prueba | Fixture sintética, comando focal, resultado esperado, límites del mock y prueba runtime necesaria |
| Comparación | Manifiesto completo, referencia/candidato, capturas/diff, decisión humana y diferencias pendientes |
| Retorno | Cómo desactivar nueva entrada, qué backend/contrato debe seguir compatible y efectos que no revierte |

No inventar estos datos por nombres de clases. Una duda de negocio se investiga
en el service/tests/caller y se eleva solo si cambia una regla material o no hay
fuente suficiente. Las recomendaciones técnicas reversibles se resuelven con
patrones existentes, sin consultar por cada archivo.

## Cobertura de cada URL y de cambios compartidos

Por entrega se construye el conjunto de impacto desde el diff real:

1. Rutas de páginas y acciones modificadas, incluidos aliases, entradas públicas,
   POST que muestran UI, pantallas de error, reload, enlaces y retorno `next`.
2. Consumidores de templates base/partials, CSS/JS/assets, fuentes y componentes
   compartidos. Usar extends/includes/imports y mapa del repo; una ruta fuera del
   menú sigue siendo consumidora. Una arista dinámica desconocida queda pendiente.
3. APIs/archivos que esas páginas consumen y consumidores externos que comparten
   el contrato. PWA/SIIS/token/API key no pasan a sesión web por coincidencia de URL.
4. Expandir familias dinámicas y concretar parámetros con fixtures autorizadas.
   Capturar la URL resuelta y query, no solo el nombre del template o prefijo.
5. Enumerar explícitamente cada ruta del conjunto en el manifiesto. Ninguna queda
   sin tipo, evidencia o razón de no aplicación. Si aparece un consumidor nuevo,
   ampliar cobertura antes de aprobar, no después de aceptar las capturas.

No significa capturar todas las combinaciones infinitas de IDs/query. Significa
cubrir cada ruta afectada y sus clases de comportamiento relevantes, con paths
resueltos reproducibles: permitido/denegado, válido/inválido, vacío/con datos,
página/filtro, archivo/job propio/ajeno y estados del circuito que cambien UI.

| Tipo de URL | Evidencia requerida |
|---|---|
| Página HTML/React, modal/estado asociado y resultado POST visible | Capturas referencia/candidato y diff por caso/rol/viewport, además de contrato/HTTP |
| API JSON sin pantalla propia | Resultado de contrato/HTTP y vínculo a todas las URLs visuales consumidoras. No fabricar una captura de JSON como prueba visual del producto |
| Descarga/archivo protegido | Permiso/status, tipo/nombre/contenido y pantalla que la solicita. Si cambia el contenido renderizado de un documento, verificarlo visualmente como artefacto separado |
| Alias/redirect | Status, destino y preservación de query/método segura; captura de la UI resultante y negativa del alias cuando difiera |
| Ruta de soporte sin UI | Prueba del comportamiento afectado o exclusión explícita justificada; no contarla como pantalla migrada |

No declarar cubierta una URL tocada porque otra con el mismo template se vea
bien. La lista puede agrupar evidencia reutilizable, pero debe conservar cada
entrada y sus diferencias de guard/routing.

## Baseline y comparación visual

La referencia se fija por flujo y SHA en entorno sintético, con aceptación del
responsable después de verla. Un PR mergeado no la acepta automáticamente. Si
un cambio paralelo está aceptado se integra a la referencia de ese flujo y se
conserva la evidencia anterior; no rebaselinar silenciosamente para borrar fallos.

Mantener referencia y candidato con la misma fixture, rol, query, contenido,
viewport, navegador/versión, escala, locale y zona horaria. Esperar fuentes e
imágenes; estabilizar animaciones/carga y scroll. No comparar un fallback de
fuente con la tipografía real ni datos de momentos diferentes. Controlar los
valores variables desde fixtures; cualquier máscara debe ser acotada y explicada.

Registrar por caso: ruta/estado/rol/viewport, revisiones, entorno, preparación,
capturas completas, recortes útiles, overlay/diff y resultado. Informar píxeles
distintos y diferencias funcionales; una métrica baja no sustituye revisión de
alineación, contraste, truncado, foco, errores o control ausente.

Criterio: **cero diferencias inesperadas** en condiciones comparables. No subir
una tolerancia global para aprobar; investigar antialiasing/nondeterminismo y
documentar su alcance antes de excluirlo. Un diff que no se ejecutó es pendiente,
no aprobado. Una captura no demuestra permisos, persistencia o integridad.

Excepción vigente: Ciudadano 360 C2 autoriza `No disponible` en la zona del aporte
fallido; los estados normales conservan apariencia idéntica. Referencia y candidato
mostrarán esa diferencia intencional, que se revisa y acepta por caso. No ocultar
la región completa, autoaceptar imágenes o extender la excepción a dashboards.

Reutilizar los manifiestos de [Insumos](2026-10-27-2799-insumos-manifiesto-visual.json),
[PAS](2026-10-27-2806-pas-manifiesto-visual.json) y
[Ciudadano 360](2026-10-27-2807-manifiesto-visual.json); contienen casos declarados,
no fixtures creadas ni resultados. Extender el mecanismo a todas las entregas.
Conservar escritorio/móvil y añadir lados de breakpoints afectados; dos tamaños
no prueban todos los responsive ni todas las combinaciones de roles/temas.

Al integrar varias entregas, repetir el diff acumulado de la versión combinada
para todas las URLs del conjunto de impacto. Diffs individuales anteriores no
demuestran que la cascada CSS o paquetes integrados sigan iguales.

## Registro de riesgos y barreras de salida

Los dueños son responsabilidades de revisión, no personas/equipos nuevos.
Todos los riesgos están identificados; ninguno se declara mitigado por este texto.

| Riesgo | Evidencia o mecanismo | Barrera de salida / negativo | Dueño |
|---|---|---|---|
| R01. API salta requisitos web | `/api/` está exento de middleware HTML; ocultar UI no autoriza | Misma prioridad de requisitos por request; directo al endpoint/runtime sin gate rechaza | Core/usuarios + runtime |
| R02. Ampliar datos o reducir permisos | Mismo modelo no equivale a contrato por campo/objeto/provincia | Comparación por acción/campo/alcance; IDs ajenos y roles mixtos; sin serializers completos por comodidad | Dominio |
| R03. Política pública cambia con cookie | PAS sin sesión frente a sesión restringida | P1 coherente en entry/datos/POST; CSRF e invitación independientes del login | Core + PAS |
| R04. Constancia G1 no prueba lo prometido | Firma temporal no da uso único, cifrado ni aislamiento entre claves compartidas | Protocolo explícito, target/audiencia/sesión y reloj; no activar con representación ambigua ni prometer anti-replay absoluto | Core/kernel + runtime |
| R05. Bloqueo circular o capacidad supuesta | Proxy síncrono esperando backend y callback al mismo pool | Sin callback circular; medir capacidad en entorno aislado, sin inferirla de mocks | Core/runtime |
| R06. Cero o vacío enmascara falla | Transporte/proveedor puede convertir errores antes del 200 | Resultado tipado y C2 en 360; en otros módulos registrar conducta actual sin extender cambio no aprobado | Dominio + frontend |
| R07. Transición o mutación duplicada | Estado cambia entre pantalla y POST; red pierde respuesta | Service mantiene reglas/transacción; conflictos y repetición; sin retry automático de mutaciones | Dominio |
| R08. Job/import parcialmente aplicado | Preview no prueba aplicación; autorización puede perderse durante job | Cubrir inicio, estado, errores, resultado, job ajeno y reintento permitido; no inventar idempotencia | Dominio/worker |
| R09. Efectos reales durante prueba | Mailing, notificaciones, RENAPER/SINTyS u otros conectores | Datos sintéticos y adaptadores simulados; integración real solo como prueba explícitamente autorizada | Dominio/operación |
| R10. Archivo privado se vuelve público | Enlace a media evita permiso; upload consume memoria/cambia nombre | Descarga por dueño, objeto ajeno/faltante, CSRF, límites y formatos; no reemplazar storage por URLs públicas | Dominio/storage |
| R11. Contrato numérico distinto | NoCount CDF, filtros legacy, orden por página, fechas/decimales | Igual queryset/orden/null/locale; páginas límite, categoría inactiva e inválida; no agregar COUNT o total ficticio | Dominio/API |
| R12. CSS/theme altera otras URLs | Globals, fuentes, CssBaseline o paquete compartido | Cierre de consumidores y diff acumulado; modos reales por módulo; sin adoptar shell INET como baseline universal | Frontend + dueños |
| R13. Herramientas omiten una app | Configs enumeran workspaces y schemas específicos | App incluida en checks reales; contrato generado desde API implementada y verificado contra consumidor | Frontend/CI |
| R14. Base móvil o trabajo paralelo sobrescrito | PRs/HEAD cambian durante migración | Snapshot por evidencia, delta de integraciones y checkout propio; revisar diff antes de tocar común | Implementador/revisor |
| R15. Retiro borra recursos aún usados | Templates/assets pueden servir PDFs, correo, admin o alias | Grafo inverso de consumidores y pruebas antes de borrar; mantener backend/documentos excluidos | Dominio/core |
| R16. Retorno o rutas rompen acceso | next/query/hash, reload y links antiguos; redirects de POST | Mapeo explícito, destino interno seguro, status y método; no catch-all global ni redirect de mutación | Core/frontend |
| R17. Falla de bundle deja UI muda | Router puede devolver 503 sin app | Emergencia mínima definida en #2788, independiente del bundle, status correcto y sin contenido privado | Core/router |
| R18. CI verde se interpreta como aceptación | Checks no prueban despliegue, datos reales o apariencia | Registrar evidencia por separado y aceptación humana positiva/negativa | Implementador/revisor/responsable |

## Compatibilidad, activación y retorno

Mantener contrato anterior mientras haya clientes que lo consumen. Agregar nueva
API y consumidor compatibles como entrega, con pruebas de ambos cuando corresponda.
No retirar un endpoint token/PWA porque el navegador ya use otro. Versionar la
representación nueva si cambia un contrato externo; no introducir versiones nuevas
por rutina cuando una extensión compatible y explícita alcanza.

Para cada flujo, antes de proponer activación:

1. Nuevas APIs, assets y routing disponibles en la misma versión compatible;
   startup/error no abre acceso por fallback. Cerrar G1 si cruza runtime.
2. Mapeo de URL histórica a React revisado, con aliases y acciones backend aún
   válidos. La validación `/v2/` no significa que la entrada histórica esté migrada.
3. Pruebas de contrato/permiso/estado y diff acumulado aceptados; confirmar que
   la versión de baseline no oculta cambios paralelos.
4. Plan concreto de desactivar la entrada nueva sin eliminar datos y volver a
   una UI legacy compatible. No confundir esto con rollback de mutaciones ya hechas.
5. Propuesta de despliegue por servicios afectados y evidencias por entorno.
   No incluye autorización de merge/deploy: se solicita cuando sea trabajo futuro.

El retorno debe probar reload, navegación y lectura contra backend compatible.
Si una operación nueva crea estados que legacy no sabe mostrar, resolver esa
compatibilidad antes de activar; no descubrirlo al revertir. Una BD compartida
no garantiza que dos versiones de UI/contrato sean compatibles.

## Retiro de presentación legacy

Separar retiro de activación inicial. Antes de eliminar template/CSS/JS/ruta:

- Enumerar quién lo usa en cada servicio, export/documento/correo/admin y alias.
  Un grep sin resultado no demuestra ausencia de consumidores dinámicos.
- Conservar Django para autorización/dominio, generación de PDF/correo, jobs y
  descargas. Si se extrae un template compartido, verificar esos consumidores.
- Confirmar que las rutas históricas aprobadas llevan al flujo React con mismo
  resultado y que no hay estados UI o roles que aún dependan de la vista anterior.
- Resolver observación/aceptación por entorno y posibilidad de volver a una
  versión compatible antes de perder ese recurso. Duración de observación depende
  de criticidad y uso medidos; no inventar una ventana garantizada en este plan.
- Actualizar inventario/resolver/contratos y documentación. Repetir contraste
  integral: templates que desaparecen no equivalen automáticamente a UI migrada.

## Aceptación y evidencia por etapa

Usar campos/enlaces en issues y PRs existentes; no crear estados de board nuevos.
Separar: definición revisada, implementación local, tests/checks, comparación
visual, aceptación humana local, PR/CI, integración, despliegue/health y aceptación
en entorno. El responsable verifica localmente un caso positivo y uno negativo
antes del commit/PR cuando haya UI, según AGENTS.md. La aceptación de una opción
de diseño no sustituye esa prueba ni demuestra comprensión técnica.

Cerrar la planificación exige cobertura, alternativas resueltas o incertidumbres
materiales visibles y un camino de investigación que permita derivar cada entrega.
Cerrar la migración exige además ejecución y evidencia completas contra un
inventario actualizado y el retiro autorizado de la UI que corresponda. No se
declara ninguno de esos resultados por generar este documento.

Validación actual: revisión estructural/documental únicamente. No se ejecutaron
tests de aplicación, contenedores, DB, navegador, capturas, CI, commits ni deploy.
