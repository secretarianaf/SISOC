# VPSL React: Cambios visuales/ux VPSL v2

Se aplicó una capa visual acotada a `/v2/vpsl/`: cabeceras de marca de alto contraste, resumen modular con datos reales de las páginas de itinerarios y sedes, indicadores de carga para ese resumen, filtros en barra, tarjetas con profundidad suave, contadores tipo píldora, botones y pestañas de aspecto más actual, y respuesta visual en filas, controles y paneles. Las acciones de eliminación se distinguen por el color de error del tema.

La capa usa los tokens de color existentes y funciona en claro y oscuro. Las cabeceras y los paneles entran con desplazamientos breves al cambiar de ruta; los resúmenes tienen una entrada escalonada y responden al hover, mientras las tarjetas elevan suavemente su sombra. El contenido se remonta por ruta React para que la transición se perciba también entre detalles. Las animaciones se desactivan con `prefers-reduced-motion`. No se modificaron permisos, API ni formularios.

La confirmación de eliminación usa ahora un diálogo React con el desglose de elementos afectados que ya proveía la API. Cancelar cierra el diálogo sin ejecutar la acción. MUI anima la entrada del diálogo.

## Ajuste según export de Figma SISOC

El export CSS de UX se interpretó como especificación de componentes, no como hoja para pegar directamente: contiene posiciones absolutas de frames, repeticiones por estado y notas de implementación. `Sisoc/Header` y `Sisoc/Footer` se aplicaron al layout compartido Front v2. UX entregó luego el logo blanco de SISOC y la textura horizontal del header, que se incorporaron como `src/backends/kernel/static/custom/img/sisoc_logo_header.png` y `src/backends/kernel/static/custom/img/sisoc_header_texture.png` (servidos en `/static/custom/img/`). La cabecera usa estos PNG, avatar con menú, botón de modo claro/oscuro visible a su derecha y franja ámbar inferior, siguiendo la captura adicional de referencia. El pie usa la superficie de navegación y la franja ámbar superior.

El theme compartido alinea MUI Button e IconButton a los radios, paddings, tamaños y jerarquía de Figma. En modo oscuro, el hover de los botones contained primarios y de error usa el tono claro, como propone el propio export para resolver el contraste pendiente. VPSL usa iconos MUI para agregar, buscar, ver, editar, borrar, exportar y navegar; las acciones de tabla conservan etiquetas accesibles. Itinerarios y Sedes pasaron de pestañas superiores a enlaces del sidebar, visibles según permisos y activos según la ruta, con navegación React. StateChip usa la superficie neutral llena del DS como punto de partida. Se mantienen las animaciones cortas previas en cards, rutas y hover, con reducción de movimiento cuando el sistema la pide.

## Revisión directa de Figma

Se inspeccionó el archivo Figma en sesión y se documentaron sus tokens, dimensiones, variantes y activos en `docs/implementaciones/sisoc_figma_ds.md`. Con los estados reales de `EstadoItinerario` y `EstadoJornada` se estableció la matriz semántica antes de colorear `StateChip`: neutral para etapas descriptivas, info para gestión, warning para revisión pendiente, success para habilitación/conclusión y error para rechazo/cancelación. Los chips pasan al alto y la tipografía del DS. Se alinearon bordes de Button outlined, color de IconButton secondary, tabs y paginación. Los buscadores de los dos listados ahora usan TextField de MUI con icono Search y el filtro de Estado usa Select de MUI. El banner principal y las microanimaciones siguen siendo la composición propia de VPSL.

En los detalles de itinerario y jornada, las acciones generales (editar/subsanar, presentar, checklist, cierre diario y exportar, según estado y permiso) se ubican en la misma barra que el botón para volver, alineadas a la derecha. Se retiró la tarjeta vacía que las contenía. La barra permite ajuste de línea en anchos reducidos; las decisiones de evaluación y de cierre definitivo permanecen junto a sus datos y formularios.

En el formulario React de registro nominal, la verificación RENAPER se representa además con el campo oculto `renaper_estado` dentro del formulario. El guardado de registros se envía como `FormData` multipart, incluso sin adjunto, para que la vista Django reciba el indicador por `request.POST` igual que el formulario clásico. Se conserva la comprobación de verificación en React y la validación definitiva del servidor.

Las tablas de itinerarios, jornadas del itinerario y registros nominales ahora conservan la celda de acciones como celda de tabla, con ancho ajustado al contenido y botones alineados al borde derecho. Se mantiene el padding izquierdo y se reduce el espacio entre iconos solo en estas columnas.

Las altas «Nueva jornada» y «Nuevo registro» usan exactamente la misma configuración de MUI Button que «Crear itinerario»: variante Contained Primary, tamaño medio por defecto e icono Add antes del texto. El ancho se ajusta al icono y al label, sin medidas fijas. La regla visual del contador de cabecera se limitó al `span` hijo directo: antes decoraba también los `span` internos de MUI Button y dibujaba un círculo y bordes sobre el botón. Se conservan hover y foco del theme, y las cabeceras de tarjeta permiten que el botón pase de línea en pantallas angostas.

## Unificación de controles visibles con MUI

Las cuatro tablas de VPSL usan `Table`, `TableHead`, `TableBody`, `TableRow` y `TableCell`; la paginación usa `TablePagination` con el tamaño fijo de cada endpoint (10 itinerarios, 15 sedes, 25 registros o casos de laboratorio). Los enlaces de fila usan `Button` de texto; los enlaces de archivos y navegación usan `Link`. Los historiales expandibles usan `Accordion`. Se conserva el ancho compacto y la alineación derecha de la columna de acciones.

Los campos visibles del alta de itinerario, los formularios dinámicos, la evaluación y la actualización masiva de laboratorio usan `TextField`, `MenuItem` y `Checkbox` de MUI. Las tarjetas de formularios usan `Card`. Los inputs ocultos siguen siendo HTML por su función de transporte; el selector de archivo usa `TextField` de MUI con input de archivo interno. El banner, los resúmenes y las microanimaciones siguen siendo composiciones del módulo. No se cambiaron endpoints ni reglas de permisos.

## Contraste con la entrega UX REACT SISOC

Se compararon las especificaciones de componentes, theme, handoff y hoja de ruta, el `theme.ts` entregado y las láminas Color Dark, Layout y Tipografía. Color Light no se pudo visualizar con el visor local; sus valores se comprobaron en los documentos de texto. La entrega se hizo para MUI 5; el Front v2 usa MUI 9. Se trasladaron los tokens y overrides al theme existente sin reemplazar la versión de la librería. El archivo `theme.ts` entregado no incluye dos overrides que la hoja de ruta versión 2 sí enumera (`MuiFormLabel` y `MuiMenuItem`); se implementaron a partir de la especificación versión 2.

El theme compartido incorpora `chart`, `backdrop`, el borde de `OutlinedInput` al 23 %, Link, CardContent, TableCell sin franja de color, Checkbox, Radio, FormHelperText, FormLabel, MenuItem, Select y Backdrop. Alert Standard y Outlined usa el mismo color semántico para texto e ícono; Filled usa fondo `main` y `contrastText`. El ítem seleccionado del sidebar deja el ícono blanco y acentúa solo el label, con la clase `sisoc-section`. Las tablas VPSL toman el encabezado `overline` del theme. Los enlaces de fila usan `MUI/Link`, las acciones de ícono muestran Tooltip, los campos vuelven al alto de 56 px, los checkboxes llevan `FormControlLabel` y los errores/ayudas de TextField usan `helperText`. El guardado exitoso del registro nominal muestra un Snackbar Filled de 6 segundos. Se conservan las animaciones y el banner propios de VPSL.

La entrega UX no incluye pantallas específicas de administración VPSL. Sus tablas de HSD e INET no definen los anchos de columnas de itinerarios, jornadas o registros; se mantienen los anchos y la paginación del módulo. El contrato de sesión VPSL tampoco ofrece rol ni ruta de cierre de sesión para completar esas opciones del menú de perfil sin inventar un flujo.

## Resumen de itinerario y revisión autenticada — 2026-10-05

Las tarjetas Cartas, Planificación y la explicación de Jornadas se reemplazan por una única Card MUI «Resumen del itinerario», con Período, Referente, Teléfono, Correo y Carta. Se conservan enlace, referencia y estados de la carta; la tabla de jornadas permanece independiente. Datos y carta se distribuyen en dos columnas en escritorio y una en anchos menores de 850 px. Localidades y Observaciones dejan de aparecer en este resumen por el alcance solicitado. Banner y animaciones se conservan como excepciones del módulo.

Se realizó una revisión autenticada local en navegador con viewport de 1440×1000 y 390×844, modos claro y oscuro: listado de itinerarios, detalle del itinerario 16, jornada 30, listado de sedes y alta nominal de esa jornada. Se inspeccionaron header, navegación, tarjetas, acciones, campos, tablas y footer. No se guardaron ni eliminaron datos. Las tablas desplazan horizontalmente dentro de su contenedor en móvil; el documento no presenta desborde horizontal en las vistas comprobadas.

La revisión encontró overrides antiguos que reducían los campos nominales a 33–37 px. Se retiraron; la comprobación DOM posterior confirmó 56 px en los primeros cinco campos de texto/Select. La compilación final TypeScript + Vite pasó y se reconstruyó solo front_vpsl con --no-deps. No se ejecutaron nuevos tests automatizados en esta revisión visual.

Alcance y pendientes: este cotejo cubre las pantallas y tamaños enumerados, no todos los estados de permisos, validación, diálogos o respuestas RENAPER, ni una comparación píxel a píxel con Figma. Algunas sedes muestran «2024-04-09 00:00:00» como localidad; requiere revisar datos/importación. El banner, los indicadores y las animaciones propias siguen siendo excepciones aceptadas. Evidencia de escritorio: [resumen claro](vpsl-resumen-itinerario-claro.jpg).

### Ajustes posteriores de etiquetas y listado

El detalle de jornada deja de mostrar los acordeones de historial de cada ítem del checklist. Conserva estado actual, observación y evidencia. El guardado y los datos de auditoría siguen disponibles en el backend; solo se elimina su representación visual en React.

Datos de la jornada y Ubicación comparten una fila de dos columnas iguales cuando existe mapa. Se reutiliza la grilla del módulo: debajo de 850 px las tarjetas se apilan; sin mapa, Datos mantiene el ancho disponible completo.

Localidad en alta/edición de jornada usa una etiqueta superior del mismo tamaño y peso que los campos vecinos (14 px, 500), conservando Autocomplete MUI. Sexo en Identificación RENAPER usa etiqueta superior con asociación accesible al Select; se alinean DNI y Sexo sin etiquetas flotantes mezcladas. Se retiraron los tres overview-tile del listado de itinerarios y sus placeholders; los indicadores del listado de sedes se conservan.

Compilación TypeScript + Vite correcta, reconstrucción únicamente de front_vpsl y comprobación autenticada en escritorio: Localidad y Ubicación comparten coordenada superior; DNI y Sexo también, ambos de 56 px de alto; el listado de itinerarios contiene cero overview-tile. Evidencia: [RENAPER alineado](vpsl-renaper-alineado.jpg). Sin nuevos tests automatizados ni cambios Git de rama/commit.
