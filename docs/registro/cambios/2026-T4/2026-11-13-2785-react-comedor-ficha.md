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

- Vitest (10 pruebas del encabezado, la tarjeta y el acordeón), tsc, eslint y compilación
  sin avisos. G1 con la ficha (200 y 403). Visual S13 de la parte superior (se recortan
  ambos lados después del acordeón, que son entregas siguientes) con una ruta de vista
  previa temporal que no se entrega: escritorio y móvil, también con el menú «Acciones»
  abierto, sin diferencias de estructura ni de píxeles.

## Limitaciones y diferencias conocidas

- Los botones de estado de la tarjeta de título (validación, programa, estado) son
  `button` sin acción, igual que en la página nativa.

- Como la página nativa, leer la foto de legajo puede crear su versión WebP en disco.
- La rama PNUD de Actividades se proyecta con las mismas expresiones pero no tiene prueba
  propia todavía.
- La proyección corre todo el contexto nativo de la ficha (como la página), por lo que su
  costo es el de la página actual.
