# Fichas prioritarias para derivar implementación (#2785)

Estado: **E2, especificación de trabajo futuro**. No autoriza código, entorno,
DB, commits ni despliegue. Las fichas distinguen definición suficientemente
acotada de dependencia aún abierta; no convierten 214 propuestas en tickets listos.
Complementan el [catálogo](2026-10-27-2785-entregas-por-flujo.md) y el
[registro por ruta](2026-10-27-2786-contratos-y-cobertura-por-ruta.md).

## F1 — Contexto y navegación web (#2798)

- **Resultado:** una sesión obtiene su identidad mínima, siguiente requisito,
  menú/capacidades actuales y footer, sin usar tokens PWA ni declarar ready por
  un error. No es endpoint de login ni entrega contraseñas.
- **Contrato:** GET/HEAD `/api/web/session/`; anónimo/inactivo 401 explícito;
  autenticado 200 incluso con remediación, menú/capacidades de negocio vacíos
  si no ready. Mismos campos de la especificación #2798; no DNI/email/permisos
  completos por volcar Profile/User. `private, no-store`, Vary Cookie.
- **Fuente/dueño:** usuarios/core para composición de requisitos; IAM y
  condiciones de sidebar existentes para menú. Conservar en Insumos `has_perm`
  para visibilidad y el predicado IAM de la ruta para autorización.
- **Validación:** cinco estados prioritarios y combinaciones; dos usuarios sin
  cache compartida; token solo no autentica; menú de referencia por rol; error
  de dependencia no devuelve ready. Seguir patrón Session/401 de INET sin
  importar VAT desde core ni cambiar autenticación global.
- **Salida de definición:** revisar condiciones del sidebar de la extracción
  y firma/tipos del OpenAPI propuesto. La implementación se deriva después de
  esa revisión; #2798 no se cierra por existir este texto.

## F2 — Comparación visual del piloto (#2799)

- **Resultado:** ejecutar un manifiesto de casos concretos del piloto y producir
  referencia/candidato/diff por URL/estado/rol/viewport con revisión humana.
- **Implementación futura mínima:** reutilizar Playwright, sus assertions y
  reporter. Empezar por el manifiesto Insumos, sin nuevo paquete, DSL, pipeline
  o motor universal para 95 familias. Extender cuando haya casos definidos.
- **Entrada necesaria:** URLs reales del entorno sintético, fixture/rol, viewport,
  estado/acción de preparación, SHA referencia/candidato y aceptación explícita
  de referencia. Un path placeholder o fixture ausente bloquea el caso; no pasa.
- **Aceptación:** caso omitido/diferencia inesperada/referencia no aceptada
  impiden aprobar; nunca aceptar por `updateSnapshots` global. Sanitizar artefactos,
  no adjuntar cookies/tokens/headers privados ni usar datos reales. Diferencia
  autorizada C2 o W1 se documenta por caso, no mediante máscara amplia.
- **Negativos del mecanismo:** entrada incompleta, baseline incorrecto, URL extra
  del conjunto de impacto y cambio compartido no cubierto. Un test de mecanismo
  no prueba la paridad de la pantalla hasta ejecutar ambos lados.
- **Dependencia futura:** entorno/fixtures autorizados, no creados bajo E2.

## F3 — Shell fiel para Insumos (#2800)

- **Resultado:** header/sidebar/footer, oscuro forzado, fuentes, iconos, espaciado,
  responsive y foco según includes/main/base actuales; no adoptar el tema claro
  ni controles de V2Layout por comodidad.
- **Alcance:** componente local de app sisoc antes de modificar un paquete común;
  reutilizar assets/CSS en orden actual. No copiar todo AdminLTE ni crear un
  sistema de diseño nuevo. Datos de menú vienen de F1; sin HTML remoto inyectado.
- **Validación:** desktop/mobile, ambos lados de breakpoint afectado, drawer,
  logout POST, usuario en sidebar y roles. Si un cambio termina en paquete/CSS
  común, ampliar a todos los consumidores identificados; no basta Insumos.
- **Dependencias:** contrato F1 y mecanismo/entorno F2. Puede prepararse en fuente,
  pero no declararse idéntico con un screenshot de otra app.

## F4 — Checks/contrato del workspace (#2801)

- **Resultado:** app sisoc participa de tests, build focal, tipos y contrato
  reales; app omitida o schema desactualizado se detectan.
- **Alcance:** conservar proyectos Vitest/Playwright y schemas integrados de
  INET/VPSL/Celiaquía. Registrar la app nueva cuando exista, sin workspace vacío
  para cerrar el issue ni regenerar tipos de una API aún inexistente.
- **Validación:** prueba de detección de app/contrato divergente, tests focales de
  la app y regresiones justificadas de archivo común. Sin upgrades ni full-build
  por rutina. Schemas se generan desde backend implementado, no este catálogo.
- **Dependencias:** nombres/contrato de F1 y app real de F3/F5; configuración
  repo existente, no reemplazar archivos con versiones previas a INET.

## F5 — Lectura y descarga Insumos (#2802, I01)

- **Resultado:** buscar, filtrar, paginar y descargar con misma UI y reglas.
- **Rutas de lectura propuestas unificadas:** `/api/web/insumos/` y `options/`;
  las referencias iniciales `/api/insumos/` quedan reemplazadas documentalmente.
  Mantener descarga `/insumos/<pk>/descargar` como backend. Alta/edición/baja/categorías Django solo son situación temporal durante desarrollo: deben tener UI React antes de activar su circuito público M2.
- **Contrato:** queryset/orden actuales, página 20, filtros busqueda/categoria/sin,
  inválidos e inactivos según fuente. Campos mínimos del documento Insumos, no
  descripción/usuario/storage completos. Fecha con misma zona y formato visible.
- **Autorización:** requisitos web locales y `view_insumo` por request; no basta
  F1. Entry anónimo conserva 403 HTML, mientras API nueva tiene 401 JSON; no
  quitar guard global de otras apps ni exigir view_insumo a toda app sisoc.
- **Validación:** matriz sintética de 25 insumos, roles y categorías declarada;
  Add sin Change/Delete; páginas/filtros inválidos; archivo ajeno/faltante y
  descarga inactiva; mismo diff por URL/estado y aceptación humana.
- **Dependencias:** F1–F4 y revisión del contrato de lectura. No necesita desplegar
  G1 remoto, migrar login o ABM completo antes del piloto local.

## F6 — Compatibilidad de URL de espera CDF (W1, #2811)

**Definición acotada para una futura implementación**, con W1 elegida. Requiere
revisión técnica/ejecución autorizada, no otra pantalla o decisión de W1/W2.
Derivada a [#2811](https://github.com/secretarianaf/SISOC/issues/2811), asignada y
vinculada formalmente a #2785. No se inició su ejecución ni se cambió la app.

- **Entrada:** GET/HEAD
  `/centrodefamilia/centros/<centro_id>/actividades/<actividad_id>/lista-espera/`.
- **Salida propuesta:** redirect temporal 302 al destino generado por reverse de
  `actividadcentro_detail`, kwargs pk=actividad_id, con fragmento `#lista-espera`.
  No 301 cacheado ni redirección determinada por parámetros `next`/URL del cliente.
- **Validación:** centro/actividad existen y corresponden; mismo permiso de URL
  y acceso de consulta del destino. No añadir roles ni cambiar scope por inferencia.
  Inexistente/incongruente 404 después del guard; sin permiso/anon conserva
  precedencia 403 del decorador actual, no convertirlo en login por quitarlo.
- **Otros métodos:** POST/PUT/PATCH/DELETE 405, sin consultas de negocio/mutaciones
  más allá de lo necesario para el guard. No llamar al service de promoción.
- **Query:** la vista actual no define filtros de consulta; no usar parámetros
  desconocidos para construir Location. Si se localiza un consumidor con una
  query reconocida, documentar su compatibilidad antes de ampliar la allowlist.
- **Foco:** ancla no visual `lista-espera` en la sección existente y su futura
  versión React; no cambiar tabla, datos, cupos, orden, botones ni estilo.
- **Recursos futuros mínimos:** vista/URL CDF, ancla de template si falta y tests
  junto al dueño. Class-based view y patrones de redirect existentes. Sin modelo,
  migración, permiso, dependencia ni settings nuevos.
- **Pruebas:** GET/HEAD validan status/destino/ausencia de cuerpo en HEAD; permisos,
  IDs inexistentes e incongruentes, método no admitido y Location fijo ante query
  manipulada; screenshot de sección actual/candidata y navegación/foco móvil.
  No considerar un mock de objeto prueba de alcance real.
- **Baseline:** tabla de la ficha existente. Reproducir el render antiguo solo
  como diagnóstico; no aceptar un supuesto error de template como diseño vigente.
- **Retorno:** desactivar cambio de entrada compatible de forma controlada;
  no borrar datos ni restaurar como objetivo un template ausente. La reversión
  se revisa con el estado real previo antes de activar.

## Fichas restantes y criterio de preparación

Dependencia de activación elegida:
[M2 de avisos](2026-10-27-2788-avisos-y-unidad-activacion.md). F5 sigue siendo
piloto de lectura validable por separado; no implica que publicar `/insumos/`
antes de migrar sus formularios/operaciones a React cumpla M2. Definir ABM, errores y retornos como grupo de activación; sin puente M1. No cerrar el piloto de lectura como migración completa de Insumos.

El [registro fuente](2026-10-27-2786-contratos-fuente.json) aporta bases/forms,
inputs GET/POST/getlist, respuestas/helpers y evidencia por ruta para las demás
familias. Su revisión no se sustituye por generar títulos. Para cada nuevo issue:
cerrar partición del slice y proyección de campos, seleccionar negativos del
perfil y vincular todos los consumidores/estados. Si falta una regla, dejar
una tarea de definición concreta; no llamarla implementación lista.

La definición de un trabajo puede estar lista y su ejecución no autorizada.
Baseline, pruebas runtime y aceptación son entradas/resultados de fase futura,
no un permiso implícito por crear el issue. No se crean 214 issues masivos.

Validación de estas fichas: coherencia con fuentes/decisiones y referencias.
No se escribieron app/API/tests de aplicación ni se iniciaron entornos.

## F7/F8 — Formularios para completar Insumos M2 (definición, sin ticket nuevo)

- F7 corresponde a I03: alta/edición/baja Insumo y validaciones/archivo/feedback;
  activa con F5 en INS-A. No ampliar #2802 silenciosamente.
- F8 corresponde a I02: listado y alta/edición/baja Categoría, incluyendo SET_NULL
  en insumos; activa como INS-B. No usar opciones del filtro como ABM de categorías.
- [Contrato, nueve rutas, permisos, campos, respuestas y efectos](2026-10-27-2785-insumos-circuitos-m2.md).
- Estado F7: definición estática coherente; API/ejecución/baseline pendientes.
  #2802 sigue lectura; I03/F7 agrega formularios para activar INS-A completo.
- F7 incluye GET/HEAD/POST de crear, <pk>/editar y <pk>/eliminar bajo
  /api/web/insumos/, dueño insumos con Add/Change/Delete propios; lectura/options
  pertenecen I01/F5 con View. GET/HEAD no mutan, otros métodos405.
- Backend conserva Forms/services, multipart/checkbox, errores campo/__all__,
  respuesta de éxito por operación y redirect fijo /insumos/. Nunca HTML Form remoto.
- Cada request conserva precedencia #2798: acceso_web→contraseña→perfil→encuesta→ready,
  y permiso/CSRF de acción; no ready por defecto. CSRF puede devolver HTML403 y
  cliente debe tratarlo como rechazo sin mutación, no asumir JSON.
- current_file muestra solo nombre y URL existente: descargar requiere View aunque
  editar esté permitido por Change. Add/Change/Delete sin View pueden guardar y
  retornar a listado denegado; caso explícito, sin permiso añadido ni retry.
- B2:52 visuales/106 combinaciones/13 contratos/9 roles; INS-A38/78, INS-B14/28.
  Fixtures por ref y partición por caso explícitas; cero datos/capturas ejecutados.
- Decisión de permisos INET [R1 elegida](2026-10-27-2794-permisos-edicion-centro.md)
  conserva regla Django de edición de centros; implementar y verificar en fase futura. No afecta INS-A/INS-B.


## Próximas fichas de identidad y respuesta

[ID-A–ID-E/EQ-A](2026-10-27-2788-identidad-remediaciones-m2.md) aporta fuente,
paths, campos/efectos, grupos M2 y manifiesto propio. U02.03 añade el cambio
voluntario del framework que no estaba separado en el catálogo anterior (215
propuestas actuales). Son contratos para revisión, sin tickets masivos ni código.
La autorización excepcional de gestión de encuestas queda definida por S1;
no altera respuesta ordinaria, R1 de centros o excepción admin/Unfold.


## Selectores con J2 y condiciones concretas

[J2 registrada](../../registro/decisiones/2026-10-27-2787-selectores-react-j2.md)
y [contratos de consumidores](2026-10-27-2787-selectores-contratos-j2.md):
CDF sexoact/dias y categoría/actividad, Inspecciones inspector/escuela/localidad.
No es un formulario universal ni una dependencia aprobada nueva. Actividad CDF
retorna a centro_detail: incluir ficha React destino en su grupo M2. Formularios
de modal Inspecciones necesitan DTO, no inyectar fragmento HTML.
L2 elegida para fallo de carga del selector CDF: mensaje y reintento manual del
GET actual, sin repetir POST ni perder otros campos. No confundirlo con lista
vacía válida ni trasladar esa excepción automáticamente a todos los selectores.
