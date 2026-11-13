# Cambio: ficha del comedor en React, cabecera, título y acordeón (#2785, CO07.01)

## Qué cambia

- **API (solo backend en esta entrega).** `GET /api/web/comedores/comedores/<pk>/`
  (`src/backends/comedores/comedores/web_api_comedor_ficha.py`) corre `ComedorDetailView` con
  su `setup()`, `get_object()` (alcance del usuario; fuera de alcance es 404) y
  `get_context_data()`, y proyecta a JSON un bloque de `comedor_detail.html` por clave. El
  acceso es el de la ruta nativa: `view_comedor`, `view_admision` o
  `view_informacionrelevante` (cualquiera de las tres). Es de solo lectura.
- **`header`**: el bloque `app-header` (Validar, convenio PNUD, Actividades, Acompañamiento
  Territorial, Historial, el menú «Acciones» y el selector de convenios con su enlace
  `?admision_id=`). Cada acción lleva la condición que mira la plantilla: lo que el usuario
  no puede usar no aparece (no hay controles inertes).
- **`titulo`**: la tarjeta de título (aviso de conformidad pendiente, nombre, validación,
  programa, etiqueta de estado, CARITAS y fechas de ejecución).
- **`acordeon`** (`web_api_comedor_ficha_datos.py`): los cuatro paneles. Ubicación (mapa por
  coordenadas o por dirección, o el aviso sin datos, y los doce datos con sus íconos),
  Responsables (foto de legajo con su versión WebP o la imagen por defecto, datos de la
  organización, firmantes y avales), Prestaciones (colaboradores, días por semana,
  prestaciones y monto mensuales, y la tabla de comidas por día, con «Merienda Reforzada»
  solo en la línea tradicional) y Actividades (PNUD: tabla con detalle y acciones según
  permiso) o Acompañamiento Territorial (donaciones, tipo de servicio, tipo de espacio y
  actividades del anexo). Cada valor se renderiza con la misma expresión de plantilla que
  la página (valores por defecto, formatos de fecha), de modo que el JSON muestra lo que
  muestra la página.
- El contrato crece agregando claves, sin renombrar. Quedan para las próximas entregas el
  la línea de tiempo, las tarjetas, las tablas de admisiones, las
  certificaciones, los colaboradores, las capacitaciones y los modales; la nómina y las
  tablas de intervenciones y observaciones siguen siendo fragmentos nativos.
- **`tablero`** (`web_api_comedor_ficha_tablero.py`): la línea de tiempo (admisión enviada,
  conector y pasos), las cuatro cajas de resumen, los datos del gráfico «Asistencia por rango
  etareo», la tarjeta «Detalles de Admisión» o «Datos del Convenio» (PNUD, con los
  territoriales asignados) y la tarjeta «Responsable de la tarjeta» (solo para quien puede
  gestionarla). Cada valor se renderiza con la expresión de la plantilla, de modo que un dupla
  inexistente queda vacío como en la página.
  `routes/comedorFichaTablero.tsx` dibuja esos bloques con el gráfico de Chart.js 4.4.4 del
  mismo CDN que el diseño nativo; la columna de nómina es un hueco que la página completa con
  su propio componente.
- **Tarjetas «Transacciones - Nación Servicios» y «Mes de ejecución»**
  (`web_api_comedor_ficha_tarjetas.py`, claves `transacciones` y `mes_ejecucion` de `tablero`).
  Cada tarjeta es `null` cuando la plantilla no la dibuja (la primera exige `view_comedor`; la
  segunda, programa 2), de modo que React no dibuja controles que la página no muestra. Los
  valores salen de las mismas expresiones de la plantilla (`default`, `monto_sin_decimales`) y los
  enlaces «Ver detalles» y «Ver más» siguen apuntando a las pantallas nativas.
  `routes/comedorFichaTarjetas.tsx` dibuja la fila (una sola tarjeta se alinea a la derecha, como
  la plantilla) y entra en el hueco `rows` del tablero.
- **Comenzar Admisión.** `POST /api/web/comedores/comedores/<pk>/admision/`
  (`web_api_comedor_admision.py`) corre `ComedorService.crear_admision_desde_comedor` para el
  comedor que resuelve el alcance del usuario (fuera de alcance es 404), con el acceso de la
  ficha nativa (sin permiso extra de alta, como pide el contrato). Responde 201 si creó la
  admisión y 200 con el motivo si el servicio la rechazó (nómina directa, sin tipo,
  renovación sin incorporación previa, incorporación activa o cuatro renovaciones activas);
  en ambos casos el mensaje nativo queda en cola para la ficha a la que redirige. Solo lee
  el tipo: `descartar_expediente` y el redirect territorial del `post` nativo no se
  alcanzan por esta ruta.
  `routes/comedorFichaAdmision.tsx` dibuja el modal «Seleccione el tipo de Admisión» que abre
  el ítem «Comenzar Admisión» del menú, y la ficha muestra los mensajes en cola.
- **Certificaciones mensuales** (`web_api_comedor_ficha_bloques.py`, clave `certificaciones`).
  Las seis últimas conformidades con las celdas de la plantilla (período `m/Y`, usuario generador
  con el nombre completo o el usuario, badge «Conforme» / «No conforme», fecha en hora local y el
  enlace «Ver PDF» solo si hay archivo) y el enlace «Ver historial completo». La tarjeta es de
  solo lectura: la plantilla nativa no tiene acciones de cambio de estado en este bloque; las
  que existen (aceptar y rechazar con observación) son las de la tabla de Capacitaciones.
  `routes/comedorFichaBloques.tsx` dibuja la tarjeta con el botón de colapsar de AdminLTE.
- **Aceptar / Rechazar capacitaciones.**
  `POST /api/web/comedores/comedores/<pk>/capacitaciones/<certificado_id>/estado/`
  (`web_api_comedor_ficha_capacitaciones.py`) corre `review_certificate` para un certificado
  del comedor que resuelve el alcance del usuario (otro comedor o inexistente es 404), con el
  acceso de la ruta nativa (`change_comedor`: ver la ficha no alcanza). Responde con el mismo
  JSON nativo (`success` + `item`, o `success: false` + `error` con 400) y un rechazo (estado
  inválido, certificado ya revisado, rechazo sin observación) deja el certificado sin cambios.
- **Colaboradores del espacio, historial de interacciones y capacitaciones**
  (`web_api_comedor_ficha_bloques.py`, claves `colaboradores`, `interacciones` y
  `capacitaciones`). Colaboradores: las filas con las celdas de la plantilla (valores por defecto,
  fechas, actividades), el recuento «Se encontraron N resultado(s).» y cada acción solo si el
  usuario puede usarla (`Agregar` con permiso de alta y programa que lo permite, `Editar` con
  permiso de cambio y sin baja, `Eliminar` con permiso de baja; con baja el botón se dibuja
  deshabilitado, como la plantilla). «Eliminar» pide la confirmación nativa y llama a la API de
  colaboradores (CO03.01, `colaboradores_web_eliminar`) que corre la baja nativa; la ficha a la que
  redirige muestra el mensaje en cola. Interacciones: etiquetas y valores del gráfico de líneas
  (Chart.js 4.4.4, mismo script que la plantilla). Capacitaciones: la tabla, que la página nativa
  convierte en una tabla DataTables 1.11.5 (textos en inglés, primera columna ascendente, diez
  filas por página); `routes/comedorFichaCapacitaciones.tsx` reproduce ese comportamiento
  (orden, búsqueda, tamaño de página, paginación) y las acciones Aceptar / Rechazar (con la fila
  de observación) llaman a la API de revisión y actualizan la fila en el lugar, con los `alert`
  de la página nativa.
- **Fuente, sin cambios.** La plantilla nativa actual no dibuja la tabla de admisiones ni el
  modal «Descartar Expediente» (solo existe el armado del contexto y el `post` de
  descartar): no se construyen controles sin origen. Si se vuelven a dibujar, la ruta de
  descarte (solo superusuario) debe sumarse con sus pruebas de efecto persistido.
- **React (parte superior de la ficha).** `src/frontends/apps/sisoc/src/routes/comedorFicha.tsx`
  dibuja la cabecera (acciones, menú «Acciones» y selector de convenios, con los menús como
  los de Bootstrap), la tarjeta de título y el acordeón horizontal de cuatro paneles con el
  ancho y el alto que calcula `newcomedor.js` (un panel abierto en escritorio, cada panel
  alterna en el celular). Los controles cuya acción es de una entrega posterior (el modal
  de validación y «Comenzar Admisión») se dibujan solo cuando la página les pasa su
  acción, de modo que no hay controles inertes. La pantalla **no está registrada** en
  `routes/index.ts` ni tiene ruta de vista previa: sale cuando toda la ficha sea real (la
  nómina, las intervenciones y las observaciones reutilizarán los componentes React de sus
  entregas).

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red), 14 pruebas: los cuatro paneles del acordeón
  (valores, ramas del mapa, con y sin organización, sin informe técnico, opciones
  territoriales) y bloques de cabecera y título contra
  los valores nativos, selector de convenios (seleccionado y enlaces), acciones según
  permisos, 404 fuera de alcance, que leer no escribe, métodos, cada permiso de acceso,
  401, 403 y requisito web pendiente con cabecera falsificada. Las pruebas reemplazan el
  doble automático de la carpeta para correr los servicios reales.

- Pytest aislado, 10 pruebas de Comenzar Admisión: creación de incorporación y renovación,
  cada rechazo con su mensaje y sin cambios, tipo ausente o vacío, nómina directa, que la
  acción de descartar no se alcanza, 404, métodos, permisos, CSRF, 401 y 403 con cabecera
  falsificada. Pytest de la ficha: 18 (4 del tablero). Vitest (10 del encabezado y el
  acordeón, 8 del modal y 9 del tablero), tsc, eslint y compilación
  sin avisos. G1 con la ficha (200 y 403). Visual S13 de la parte superior (se recortan
  ambos lados después del acordeón, que son entregas siguientes) con una ruta de vista
  previa temporal que no se entrega: escritorio y móvil, también con el menú «Acciones»
  abierto, con el modal de admisión abierto y tras un rechazo (renovación sin incorporación
  previa) y el tablero (con y sin admisión), sin diferencias de estructura ni de píxeles. La biblioteca toastr nativa no
  carga sin red en el banco, por lo que los avisos se verifican con las pruebas unitarias.

## Limitaciones y diferencias conocidas

- Los botones de estado de la tarjeta de título (validación, programa, estado) son
  `button` sin acción, igual que en la página nativa.

- Como la página nativa, leer la foto de legajo puede crear su versión WebP en disco.
- La rama PNUD de Actividades se proyecta con las mismas expresiones pero no tiene prueba
  propia todavía.
- La proyección corre todo el contexto nativo de la ficha (como la página), por lo que su
  costo es el de la página actual.
