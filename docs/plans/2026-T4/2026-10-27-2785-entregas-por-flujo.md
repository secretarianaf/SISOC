# Catálogo de entregas propuestas por flujo (#2785)

Estado: E2, planificación. 95 familias; 215 slices propuestos, **no tickets listos para implementar**.

Fuente de rutas: `ae0b0da01c546d801f18237c3c6dab29a5496790`. Delta de registro: `59a8f797688c9e762d5a4e9eaa187698ffade8aa`.

[Catálogo estructurado](2026-10-27-2785-entregas-por-flujo.json). [Fuente de cada familia/ruta](2026-10-27-2786-matriz-flujos.md). [Orden integral](2026-10-27-2785-secuencia-por-flujos.md).

Los slices tienen un resultado por revisar y perfiles de contrato/pruebas. La partición exacta de rutas por slice sigue pendiente: no convertir un clasificador de nombres en conocimiento de negocio. Primero se cierra ese contrato con la fuente; después se deriva un issue acotado.

| Familia | Dueño | Entregas propuestas | Riesgo que debe resolver el contrato |
|---|---|---|---|
| T01 Inicio y encuesta transversal | kernel/core | T01.01 Inicio y contenido transversal [L]; T01.02 Integrar modal obligatorio con E01 [M] | Modal/context processor y orden de requisitos; no basta servir un shell. |
| T02 Novedades | kernel/core | T02.01 Listado y detalle de novedades [L] | Parseo/cache siguen backend, no duplicar en React. |
| T03 Arquitectura y grafo | kernel/core | T03.01 Vista de arquitectura [L]; T03.02 Interacción y datos del grafo [L] | Grafo describe estructura interna; nunca convertirlo en asset público. |
| T04 Preferencias y geografía | kernel/core | T04.01 Geografía y opciones dependientes [L]; T04.02 Preferencias y filtros guardados [M] | Contratos AJAX no son pantallas; validar todos los consumidores antes de cambiar. |
| T05 Programas | kernel/core | T05.01 Consulta de programas [L]; T05.02 Alta edición y baja autorizadas [M] | Separar lectura/ABM y confirmar permisos antes de implementar. |
| T06 Papelera y restauración | kernel/core | T06.01 Consulta de papelera [L]; T06.02 Restauración y sus efectos [M] | Puede restaurar relaciones; no convertir en update directo. |
| T07 API de catálogos/integraciones | kernel/core | T07.01 Contratos de catálogos e integraciones existentes [K] | HasAPIKey no equivale a sesión web; no exponer credenciales. |
| U01 Login y logout web | sisoc_core/usuarios | U01.01 Entrada y autenticación web [A]; U01.02 Logout y limpieza del contexto privado [A] | No usar login/logout token como equivalentes de sesión. |
| U02 Contraseña y recuperación | sisoc_core/usuarios | U02.01 Solicitud y confirmación de recuperación [A]; U02.02 Cambio obligatorio y enlaces vencidos [A]; U02.03 Cambio voluntario y confirmación estándar [A] | Entry público, CSRF, tokens sintéticos y controles forzados. |
| U03 Cuenta y confirmación | sisoc_core/usuarios | U03.01 Consulta y edición de cuenta [A]; U03.02 Confirmación obligatoria y retorno [A] | No abrir edición de otro usuario ni saltar bloqueo. |
| U04 Credenciales masivas | sisoc_core/usuarios | U04.01 Solicitud y seguimiento de credenciales masivas [J]; U04.02 Entrega protegida de resultados [F] | Operación sensible; no generar ni imprimir credenciales reales. |
| U05 Importación de usuarios | sisoc_core/usuarios | U05.01 Preparación y ejecución de importación [J]; U05.02 Estado errores y resultado del job [L] | Conservar ownership del job, permisos y errores de fila. |
| U06 Usuarios y exportación | sisoc_core/usuarios | U06.01 Consulta y detalle de usuarios [L]; U06.02 Gestión de usuario y estado [M]; U06.03 Exportación autorizada [F] | ABM, activación y export requieren tareas separadas; no regla admin Unfold. |
| U07 Grupos y permisos | sisoc_core/usuarios | U07.01 Consulta de grupos y permisos [L]; U07.02 Modificación de asignaciones autorizadas [M] | No ampliar asignación de privilegios; lectura y mutación separadas. |
| U08 API de identidad PWA/SIIS | sisoc_core/usuarios | U08.01 Regresión de identidad PWA y SIIS [K] | Fuera de reescritura PWA; no eliminar TokenAuthentication. |
| C01 Importación y jobs de ciudadanos | kernel/ciudadanos | C01.01 Preparación e inicio de importación [J]; C01.02 Seguimiento errores y resultado [L] | No revertir estados/columnas del worker ni tratar mocks como MySQL. |
| C02 Revisión de datos | kernel/ciudadanos | C02.01 Cola y evidencia de revisión [L]; C02.02 Resolución autorizada de revisión [M] | Confirmar roles y efecto de cada transición, no solo listado. |
| C03 Grupo familiar | kernel/ciudadanos | C03.01 Consulta de grupo familiar [L]; C03.02 Vínculos y desvinculación autorizados [M] | Relaciones y alcance del ciudadano; no borrar por simplificación. |
| C04 Contribuciones Ciudadano 360 | kernel/ciudadanos | C04.01 Proyección JSON por aporte [L]; C04.02 Renderers y disponibilidad C2 [L] | HTML remoto actual no es contrato JSON React; sin imports entre backends. |
| C05 Consulta, ficha, ABM y exportación | kernel/ciudadanos | C05.01 Consulta ficha y navegación [L]; C05.02 Alta y edición [M]; C05.03 Baja autorizada [M]; C05.04 Exportación [F] | Descomponer listado/ficha/ABM; búsqueda API no acredita resto de CRUD. |
| I01 Consulta y descarga de Insumos | sisoc_core/insumos | I01.01 Consulta filtros y paginación [L]; I01.02 Descarga Django protegida [F] | 403 anónimo frente a router v2; inactivos descargables. #2802. |
| I02 Categorías de Insumos | sisoc_core/insumos | I02.01 Consulta de categorías [L]; I02.02 Alta edición y baja de categoría [M] | Permisos distintos al combo de consulta y relación programa-categoría. |
| I03 ABM de Insumos | sisoc_core/insumos | I03.01 Alta y edición de Insumo [M]; I03.02 Baja y efectos en archivos [M] | Baja elimina archivo; fuera del piloto de lectura. |
| E01 Respuesta y modal | sisoc_core/encuestas | E01.01 Consulta de encuesta/modal [L]; E01.02 Respuesta y estado obligatorio [M] | Conservar condiciones de ronda; no habilitar posponer si no corresponde. |
| E02 Segmentación e importación | sisoc_core/encuestas | E02.01 Definición y consulta de segmentos [L]; E02.02 Importación de segmentación [J] | Datos/PII por backend; no resolver elegibilidad en React. |
| E03 Resultados y exportación | sisoc_core/encuestas | E03.01 Consulta de resultados [L]; E03.02 Exportación autorizada [F] | Confidencialidad y filtros del conjunto exportado. |
| E04 Gestión, revisión y rondas | sisoc_core/encuestas | E04.01 Listado ficha y revisión [L]; E04.02 Gestión de encuesta y rondas [M] | Una transición por tarea; notificaciones/historial siguen services. |
| D01 Dashboards y tableros | sisoc_core/dashboard | D01.01 Listado y acceso a tableros [L]; D01.02 Métricas remotas y estados actuales [L] | Fuentes remotas, permisos y disponibilidad; ceros no prueban ausencia de datos. |
| A01 Consulta de auditoría | kernel/audittrail | A01.01 Consulta y filtros de auditoría [L]; A01.02 Detalle y navegación a objeto [L] | Datos sensibles, alcance y retención actuales; no confundirse con admin. |
| CO01 Nómina y asistencia | comedores/comedores | CO01.01 Nómina y registro de asistencia [L]; CO01.02 Gestión de nómina [M]; CO01.03 Carga y corrección de asistencia [M] | Lista de espera y activos según comportamiento vigente; no aplicar #142 sin decisión. |
| CO02 Intervenciones y archivos | comedores/comedores | CO02.01 Consulta de intervenciones [L]; CO02.02 Alta edición y baja [M]; CO02.03 Adjuntos y descargas protegidas [F] | Reglas/historial y formato del archivo; no normalizar por asociación. |
| CO03 Colaboradores y actividades del espacio | comedores/comedores | CO03.01 Colaboradores y actividades [L]; CO03.02 Gestión de colaboración y vigencia [M] | Services comunes con PWA/admin; no romper contratos externos. |
| CO04 Catálogos de cursos/actividades | comedores/comedores | CO04.01 Consulta de cursos y actividades [L]; CO04.02 Gestión de catálogos autorizada [M] | No reconstruir la app móvil ni alterar reglas de capacitación. |
| CO05 Prestaciones y certificaciones | comedores/comedores | CO05.01 Prestaciones y certificaciones [L]; CO05.02 Operaciones autorizadas [M]; CO05.03 Documentos asociados [F] | Generación/calculo backend; no aplicar pendientes históricos #1103. |
| CO06 Observaciones | comedores/comedores | CO06.01 Observaciones existentes [L]; CO06.02 Alta y modificaciones autorizadas [M] | Visibilidad de información y relación al comedor. |
| CO07 Legajo, convenio y validación | comedores/comedores | CO07.01 Listado ficha y navegación de espacio [L]; CO07.02 Alta y edición [M]; CO07.03 Convenio y validación con estados actuales [W] | Descomponer ficha/ABM/validación; ramas de convenio y aportes remotos. |
| CO08 API territorial y métricas | comedores/comedores | CO08.01 Contrato territorial y métricas [K]; CO08.02 Regresión de consumidores existentes [K] | Token/alcance propio del consumidor; no ampliar listados por sesión genérica. |
| O01 Convenio de proyecto | comedores/gestion_organizaciones | O01.01 Consulta de convenio de proyecto [L]; O01.02 Operaciones y documentos del convenio [W] | Reglas de línea/Imprevistos/avisos; fuente actual, no snapshot viejo. |
| O02 Documentos e historial | comedores/gestion_organizaciones | O02.01 Historial y metadatos [L]; O02.02 Carga descarga y operaciones de documentos [F] | Archivos y mutaciones parciales; confirmar permiso y pertenencia. |
| O03 Firmantes y avales | comedores/gestion_organizaciones | O03.01 Firmantes y avales [L]; O03.02 Altas cambios y desvinculación [M] | Conservar restricción de programa y datos existentes. |
| O04 Rendiciones de organización | comedores/gestion_organizaciones | O04.01 Consulta de rendición [L]; O04.02 Acciones y evidencias por línea [W] | No perder filtro de línea incorporado en #2775. |
| O05 Organización y proyectos | comedores/gestion_organizaciones | O05.01 Organización y proyectos [L]; O05.02 Gestión de organización [M]; O05.03 Gestión de proyectos y programas [M] | Baja bloqueada con proyectos y servicios actuales; subdividir antes de implementación. |
| DU01 Equipo técnico y asignaciones | comedores/duplas | DU01.01 Equipo y asignaciones [L]; DU01.02 Asignar y modificar según permisos [M] | Alcance por equipo/usuario y permisos de asignar/desasignar. |
| AD01 Gestor de templates de informes | comedores/admisiones | AD01.01 Consulta de templates [L]; AD01.02 Editor y operaciones autorizadas [M]; AD01.03 Preview y documento generado por backend [F] | UI incluida; templates que generan documentos quedan Django, no borrar por nombre. |
| AD02 Informes y documentos de admisión | comedores/admisiones | AD02.01 Informes y metadatos [L]; AD02.02 Acciones del informe [W]; AD02.03 Adjuntos y generación backend [F] | Backend genera documentos; diferenciar previsualización de formulario y PDF. |
| AD03 Circuito técnico/legal y seguimiento | comedores/admisiones | AD03.01 Estado y seguimiento de admisión [L]; AD03.02 Transiciones técnicas [W]; AD03.03 Transiciones legales y efectos [W] | Una transición observable por tarea; no concentrar circuito en un componente. |
| AC01 Seguimiento e hitos | comedores/acompanamientos | AC01.01 Seguimiento e hitos [L]; AC01.02 Acciones autorizadas y evidencia [W] | Acciones de ficha pueden vivir en POST de detalle y no tener URL separada. |
| EX01 Expedientes de pago | comedores/expedientespagos | EX01.01 Consulta y ficha de expediente [L]; EX01.02 Operaciones sobre expediente [W] | Separar alta/edición/baja; efectos financieros no se recalculan en React. |
| EX02 Importación de expedientes | comedores/importarexpediente | EX02.01 Preparación validación e importación [J]; EX02.02 Errores y resultado del procesamiento [L] | Borrar datos importados no es limpieza de UI; acción sensible separada. |
| R01 Relevamiento y primer seguimiento | comedores/relevamientos | R01.01 Relevamiento y seguimiento [L]; R01.02 Captura y edición de datos [M]; R01.03 Documentos y descargas [F] | Servicios GESTIONAR y PDF/backend se conservan; validar estado y permisos. |
| R02 Actas complementarias | comedores/relevamientos | R02.01 Consulta de actas [L]; R02.02 Operaciones y evidencias del acta [W] | Confirmaciones y archivos; alcance del comedor. |
| R03 Seguimientos y PNUD | comedores/relevamientos | R03.01 Seguimientos y PNUD [L]; R03.02 Acciones y estados asociados [W] | No eliminar variantes PNUD ni unificar etapas sin contrato. |
| RM01 Rendición mensual y documentos | comedores/rendicioncuentasmensual | RM01.01 Consulta de rendición mensual [L]; RM01.02 Acciones del circuito [W]; RM01.03 Documentos y comprobantes [F] | Separar documentos, auditoría y transiciones; conservar reglas por organización/línea. |
| RF01 Rendición final y documentos | comedores/rendicioncuentasfinal | RF01.01 Consulta de rendición final [L]; RF01.02 Acciones del circuito [W]; RF01.03 Documentos y comprobantes [F] | No sustituir validación/subsanación por update de estado; archivos privados. |
| CM01 Mailing y jobs | comedores/comunicados | CM01.01 Audiencia y seguimiento de envío [L]; CM01.02 Solicitud y estado del mailing sin envíos reales en pruebas [J] | No enviar correos en relevamiento; ownership, reintentos y efectos externos. |
| CM02 Gestión y publicación | comedores/comunicados | CM02.01 Consulta y ficha de comunicado [L]; CM02.02 Edición y gestión [M]; CM02.03 Publicación y estados [W] | API PWA solo publicada no acredita paridad de borradores/gestión. |
| CM03 Lectura de comunicados | comedores/comunicados | CM03.01 Lectura publicada por destinatario [L] | No ampliar contenido por reutilizar API institucional de otro consumidor. |
| CDI01 Usuarios CDI/SIMEPI | cdi/centrodeinfancia | CDI01.01 Consulta de usuarios CDI SIMEPI [L]; CDI01.02 Gestión autorizada [M]; CDI01.03 Regresión de integración [K] | Identidad de integración, no login web genérico ni credenciales reales. |
| CDI02 Asistencia | cdi/centrodeinfancia | CDI02.01 Consulta de asistencia [L]; CDI02.02 Carga y corrección autorizadas [M] | Ruta legacy de trabajadores puede redirigir; no duplicar funcionalidad inexistente. |
| CDI03 Formularios CDI | cdi/centrodeinfancia | CDI03.01 Consulta de formularios [L]; CDI03.02 Captura y modificación autorizadas [M] | Reglas/formsets y campos dinámicos siguen backend. |
| CDI04 Nómina y derivación | cdi/centrodeinfancia | CDI04.01 Nómina y detalle [L]; CDI04.02 Gestión de nómina [M]; CDI04.03 Derivación y estados [W] | Permiso y pertenencia al centro; no perder acciones parciales. |
| CDI05 Trabajadores | cdi/centrodeinfancia | CDI05.01 Consulta de trabajadores [L]; CDI05.02 Gestión autorizada de trabajadores [M] | No convertir vínculo de trabajador en alta de usuario general. |
| CDI06 Intervenciones y adjuntos | cdi/centrodeinfancia | CDI06.01 Consulta de intervenciones [L]; CDI06.02 Gestión de intervención [M]; CDI06.03 Adjuntos y descarga [F] | Archivos e historial no se autorizan solo por ocultar controles. |
| CDI07 Observaciones | cdi/centrodeinfancia | CDI07.01 Consulta de observaciones [L]; CDI07.02 Operaciones autorizadas [M] | Permiso/objeto y visibilidad de información. |
| CDI08 Reportes y exportaciones | cdi/centrodeinfancia | CDI08.01 Consulta de reportes [L]; CDI08.02 Exportaciones con alcance idéntico [F] | Generadores quedan backend; no confundir archivo con pantalla migrable. |
| CDI09 Centros, ficha y catálogos | cdi/centrodeinfancia | CDI09.01 Listado ficha y catálogos [L]; CDI09.02 Gestión de centro y catálogos [M] | Alcance local/SSE y autorización; separar consulta y mutaciones. |
| CDF01 Informes CABAL | cdf/centrodefamilia | CDF01.01 Consulta de informes CABAL [L]; CDF01.02 Operaciones del informe [W]; CDF01.03 Documentos y descargas [F] | Procesamiento afecta datos; distinguir API key y permisos de backoffice. |
| CDF02 Actividades, asistencia y espera | cdf/centrodefamilia | CDF02.01 Actividades y participantes [L]; CDF02.02 Gestión de actividad [M]; CDF02.03 Asistencia y lista de espera [W] | No convertir lista de espera en estado distinto; services y alcance actual. |
| CDF03 Beneficiarios y responsables | cdf/centrodefamilia | CDF03.01 Beneficiarios y responsables [L]; CDF03.02 Gestión de datos y relaciones [M] | PII/parentesco; HasAPIKey actual no se expone al navegador. |
| CDF04 Centros y usuario | cdf/centrodefamilia | CDF04.01 Consulta de centros y ficha NoCount [L]; CDF04.02 Gestión de centro [M]; CDF04.03 Gestión de usuario vinculada al centro [A] | Rol territorial/local y API existente de integración requieren contrato web propio. |
| DS01 Mapa y ubicación | dispositivos/dispositivos | DS01.01 Mapa y consulta de ubicación [L]; DS01.02 Edición de punto y previsualización [M] | Coordinar #2792; no integrar un mapa alternativo ni cambiar georreferencias. |
| DS02 Catálogo y legajos | dispositivos/dispositivos | DS02.01 Listado y legajo [L]; DS02.02 Gestión autorizada del dispositivo [M] | Separar ficha/ABM y preservar filtros/relaciones. |
| DC01 Operativos/relevamientos DataCalle | dispositivos/datacalle | DC01.01 Consulta de operativos y relevamientos [L]; DC01.02 Captura y modificación [M]; DC01.03 Cierre y reintento con contrato vigente [W] | Token/PWA y cierre 409 tienen contratos propios; no reintento ciego. |
| DC02 Casos y catálogos DataCalle | dispositivos/datacalle | DC02.01 Casos y catálogos [L]; DC02.02 Gestión autorizada [M]; DC02.03 Regresión del consumidor de campo [K] | Alcance equipo/provincia; no confundir cola offline PWA con web. |
| IN01 Importaciones escuelas/asignaciones | inspecciones/inspecciones | IN01.01 Importación de escuelas [J]; IN01.02 Importación de asignaciones y resultado [J] | Token temporal por usuario; diez rutas dinámicas y resultado POST con UI. |
| IN02 Asignaciones | inspecciones/inspecciones | IN02.01 Consulta de asignaciones [L]; IN02.02 Gestión y cambios autorizados [M] | Permiso de gestión y objeto; mantener correspondencia de escuela/inspector. |
| IN03 Tablero y exportaciones | inspecciones/inspecciones | IN03.01 Tablero y métricas [L]; IN03.02 Exportaciones con alcance idéntico [F] | Filtros y alcance; sin datos reales para capturas. |
| IN04 Actas, imágenes y notificaciones | inspecciones/inspecciones | IN04.01 Consulta y ficha de actas [L]; IN04.02 Operaciones y notificación sin entrega real en pruebas [W]; IN04.03 Imágenes archivos y descarga [F] | API PWA token no es contrato web; conservar PDF backend y estados. |
| IN05 Escuelas y catálogos | inspecciones/inspecciones | IN05.01 Consulta de escuelas y catálogos [L]; IN05.02 Gestión autorizada [M] | Gestión por puede_gestionar; conservar layout claro propio de este módulo. |
| PAS01 DDJJ por invitación sin sesión | pas/pas | PAS01.01 Invitación y sesión P1 [A]; PAS01.02 Cinco pasos validación y presentación [M]; PAS01.03 Confirmación y estados de invitación [L] | Token inexistente 404, vencido/usado 410, formulario inválido 400; no mover al router protegido genérico. |
| PAS02 DDJJ administrativa y archivos | pas/pas | PAS02.01 Gestión administrativa de DDJJ [L]; PAS02.02 Descarga y rechazo de media directo [F] | No exponer tokens reales ni abrir media directo; PDF queda Django. |
| PAS03 Cruces SINTyS/RENAPER | pas/pas | PAS03.01 Preparación y ejecución de cruces [J]; PAS03.02 Resultados y evidencia sin llamadas reales en pruebas [L] | Integraciones y lotes siguen backend; no ejecutarlos en relevamiento. |
| PAS04 Informes y PDF | pas/pas | PAS04.01 Consulta de informes [L]; PAS04.02 Solicitud de generación [W]; PAS04.03 Preview y PDF backend [F] | Generación backend; conservar texto/estado de error. |
| PAS05 Áreas y formación | pas/pas | PAS05.01 Consulta de áreas y formación [L]; PAS05.02 Operaciones autorizadas [M] | No inventar operaciones completas si la UI actual solo expone información. |
| PAS06 Padrón y estados | pas/pas | PAS06.01 Padrón y ficha [L]; PAS06.02 Alta y edición [M]; PAS06.03 Cambios de estado autorizados [W] | Una transición por tarea; preservar vigencia/controles y confirmar permisos. |
| OCR01 Carga y seguimiento OCR | ocr/ocr | OCR01.01 Carga múltiple de archivos [F]; OCR01.02 Estado y resultado del procesamiento [J] | ocr.use_ocr y ownership; no tocar motor/worker ni modificar pipeline. |
| OCR02 Descarga OCR protegida | ocr/ocr | OCR02.01 Descarga y rechazo de job ajeno [F] | ID de documento ajeno debe rechazarse aun si se cambia URL. |
| V01 Vouchers y parametrías | vat/VAT | V01.01 Vouchers y parametrías [L]; V01.02 Gestión autorizada [M]; V01.03 Acciones de crédito según reglas backend [W] | No presumir cobertura INET ni duplicar cálculos de negocio en React. |
| V02 Asistencia y resultados de comisión | vat/VAT | V02.01 Contrastar asistencia INET integrada [K]; V02.02 Resultados y remanente de reportes [L] | Reconciliar #2794: clases realizadas, nómina completa, alcance por CFP. |
| V03 Inscripciones y alumnos | vat/VAT | V03.01 Contrastar inscripción INET integrada [K]; V03.02 Remanente de alumnos inscripción y estados [W] | Cupo/duplicados/identidad; no reconstruir lo implementado en INET. |
| V04 Comisiones y horarios | vat/VAT | V04.01 Contrastar comisiones y horarios INET [K]; V04.02 Remanente de edición regeneración y estados [W] | Regeneración de clases y datos históricos; coordinar #2794 antes de migrar. |
| V05 Cursos y ofertas | vat/VAT | V05.01 Contrastar cursos y ofertas INET [K]; V05.02 Remanente autorizado por acción [M] | Oferta y curso no son necesariamente el mismo circuito; dividir tras comparar INET. |
| V06 Centro, contacto y ubicación | vat/VAT | V06.01 Contrastar centros contacto ubicación INET [K]; V06.02 Remanente autorizado por acción [M] | Mapa y alcance por centro/provincia; #2794 ya cubre parte del recorrido. |
| V07 Planes y catálogos curriculares | vat/VAT | V07.01 Contrastar planes INET [K]; V07.02 Remanente de catálogos curriculares [M] | Revisar remanentes INET; catálogos no se migran solo por nombre de modelo. |
| V08 Evaluaciones y otros reportes | vat/VAT | V08.01 Evaluaciones y reportes restantes [L]; V08.02 Acciones de evaluación [W]; V08.03 Descargas y exportaciones [F] | Requiere descomposición; reportes repetidos/aliases deben reconciliarse, no contarse como dos pantallas. |

## Perfiles de contrato y negativos

En V02–V07 hay código INET integrado por reutilizar y contrastar, pero la
[referencia visual I1](2026-10-27-2794-reutilizacion-y-referencia-visual.md)
está elegida: Django. No derivar una tarea como visualmente inequívoca
solo porque el endpoint o el componente ya existe.

El [registro por ruta](2026-10-27-2786-contratos-y-cobertura-por-ruta.md) agrega
símbolos/forms y cobertura. En CDF02, W1 está elegida para la URL independiente de espera;
no bloquea por sí sola toda la asistencia o gestión de actividades.

### L — Lectura y navegación

Contrato: Campos visibles y nulls sin ORM completo; Filtros orden paginación y relaciones con query/URL; Permiso y alcance en consulta y detalle.

Negativos: Sin permiso y objeto ajeno; Vacío válido versus fallo según política del flujo; Reload enlaces directos y página/filtro inválidos.

### M — Mutación de datos

Contrato: Campos editables y validaciones backend actuales; CSRF y permiso de acción/objeto; Resultado errores de campo y efectos sobre adjuntos o vínculos.

Negativos: POST/PUT directo sin permiso o CSRF; Datos inválidos y cambio concurrente; Respuesta perdida sin replay automático.

### W — Acción o transición de circuito

Contrato: Estado de origen acción y rol habilitados; Reglas y efectos en service existente; Conflictos y resultado observable sin update arbitrario de estado.

Negativos: Transición inválida o repetida; Estado cambió entre lectura y envío; Efectos externos simulados y resultado incierto.

### F — Archivo documento o exportación

Contrato: Solicitud y autorización backend; Mismo filtro alcance formato nombre y descarga protegida; Documento generado por backend y ciclo de vida actual.

Negativos: ID/job/archivo ajeno o faltante; Upload inválido límite y cancelación; Fallo de storage o descarga sin abrir media privado.

### J — Job importación o envío

Contrato: Preparación validación ejecución estado y resultado; Identificador autorizado alcance y errores por fila cuando existen; Reglas de reintento y efectos externos actuales.

Negativos: Job ajeno doble envío o expiración de sesión; Fallo parcial o respuesta perdida sin duplicar efectos; No usar datos reales ni enviar mensajes o consultar integraciones reales.

### A — Identidad invitación o credencial

Contrato: Sesión o invitación y estado prioritario; CSRF expiración y retorno interno seguro; Separación de token PWA/SIIS y web.

Negativos: Sin sesión/token inválido o consumido; Requisitos combinados sin bucles ni bypass; No exponer secretos y no reintentar mutación tras login.

### K — Compatibilidad o contraste de implementación existente

Contrato: Consumidor y contrato operativo actual; Matriz por campo acción rol y estado antes de reutilizar; Delta real y remanente sin duplicar producto integrado.

Negativos: Mismo modelo no prueba misma autorización; Merge o test mockeado no prueba runtime ni aceptación visual; No romper consumidor externo ni adoptar baseline sin aceptación.

## Cómo convertir un slice en implementación

1. Identificar URLs concretas y métodos en la fuente, incluyendo aliases/dinámicas y resultados POST con UI.
2. Fijar campos, acciones, estados, permisos/objeto y consumidor; comparar API existente sin inventar equivalencia.
3. Seleccionar los negativos del perfil y agregar los propios de las reglas fuente; fijar fixtures sintéticas.
4. Resolver presentación y baseline, registrar todos los consumidores indirectos y definir el diff visual.
5. Revisar dependencia/cambio compartido, compatibilidad y reversión; entonces crear o refinar el issue de implementación.

No crear 214 issues automáticamente ni usar esta cuenta como estimación de esfuerzo. No ejecutar implementación, DB, tests de aplicación ni entorno bajo E2.

## Grupos M2 concretados en esta continuación

[INS-A/INS-B](2026-10-27-2785-insumos-circuitos-m2.md) agrupan I01+I03 e I02
respectivamente. Los seis IDs de slice se conservan; agrupar activación no fusiona
tickets ni autoriza código. El JSON del catálogo incorpora esos dos grupos como
propuesta fundada en fuente. Las demás familias siguen con partición pendiente,
sin inventar grupos mediante clasificación de nombres. Ver
[orden de preparación restante](2026-10-27-2785-cierre-progresivo-de-contratos.md).


## Reconciliación de identidad y rutas del framework

El catálogo pasa de 214 a 215 propuestas: U02.03 cubre cambio voluntario y su
confirmación estándar, distintos del cambio obligatorio. Los 214 IDs previos se
conservan; no se crean tickets por esta cuenta. Las cifras anteriores son historia.
El inventario literal original de 614 rutas asignadas/770 declaraciones no cambia:
la ampliación se registra como [suplemento auth](2026-10-27-2786-auth-framework-suplemento.json).
Se proponen ID-A–ID-E/EQ-A como grupos M2 desde
[contrato de identidad](2026-10-27-2788-identidad-remediaciones-m2.md), sin activar.
