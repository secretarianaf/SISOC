# Listado React de Insumos

## Alcance

Se reemplazó el placeholder del piloto local por el listado de Insumos en React. La pantalla carga las opciones y la página actual desde la API web, conserva los filtros en la URL y mantiene la descarga en la ruta Django protegida. El alcance inicial no incluía los formularios. La continuación de 2026-11-02 incorpora su implementación local en validación; no equivale a cierre visual ni aceptación humana. No se activó el frontend globalmente.

## Comportamiento

- Búsqueda por título o descripción, filtro por categoría y paginación consumen el contrato del backend; la fecha se muestra como llega preformateada.
- Se conservan la tabla, los estados vacíos, los nombres de columnas y las clases de estilos locales usadas por el listado legado.
- Las acciones de gestión se muestran según las capacidades proyectadas; el servidor sigue siendo la autoridad de permisos. No se usa `can_view` para bloquear el shell.
- La descarga solo acepta una ruta interna devuelta por la API; el acceso continúa pasando por Django.
- Solicitudes canceladas u obsoletas no pueden reemplazar la vista actual. Los errores limpian el listado y ofrecen reintento explícito; no hay reintentos automáticos.
- Los valores de página de la URL se envían sin reinterpretarlos (excepto `page=1`, equivalente al valor por defecto); los errores 404 del backend permanecen visibles en vez de caer silenciosamente en la primera página.
- Las hojas CSS bajo `/v2/sisoc/static/` se reescriben a `/static/` al pasar por el proxy local al backend candidato en `127.0.0.1:18885`; el resto de las rutas del frontend queda excluido y se conserva `Host`.
- La búsqueda, las acciones y el filtro conservan el orden y las clases de `components/search_bar.html`; el estado vacío conserva el contenedor de paginación legado, sin mostrar el conteo cero.
- El shell reutiliza la estructura y clases de `includes/header.html`, `includes/sidebar/base.html`, `includes/sidebar/opciones.html`, `includes/main.html` y `includes/footer.html`. El árbol activa el ancestro de la ruta React, la cuenta queda antes de Inicio como en la captura fuente y el botón móvil usa el estado `sidebar-open` del layout legado.
- El shell conserva el logo solo desde el breakpoint `lg`, iconos locales/Bootstrap del menú y footer, avatar de una inicial y scroll horizontal de tabla en móvil. No se alteraron hojas de estilo legacy.

## Verificación

- `vitest run apps/sisoc/src/App.test.tsx apps/sisoc/src/InsumosList.test.tsx apps/sisoc/src/localProxy.test.ts --reporter=dot`: 22 pruebas aprobadas. Incluyen orden del buscador, cuenta vacía, ancestría/orden del menú, apertura móvil y proxy CSS servido como `text/css` (no fallback HTML).
- `tsc -p tsconfig.json --noEmit`: aprobado.
- `eslint` sobre los archivos React y la configuración local del proxy: aprobado.
- `vite build --config vite.config.ts`: aprobado. Los CSS servidos por Django se mantienen como URL de runtime; Vite informó que no existen en el snapshot aislado de build.
- Comparación de navegador con datos sintéticos y cache offline: seis pares `desktop/mobile × default/empty` y breakpoints 991/992, sin diferencias de filas ni fallos de checks. En `desktop/default`, encabezado, sidebar, lista y pie coincidieron en geometría (81px; sidebar `0,76,300,824`; lista `320,139,1100`; pie `y=2702.656,h=136`). En `mobile/empty`, lista y pie también coincidieron (`20,139,350,665.594`; pie `y=824.594,h=136`). Las CSS candidatas cargaron reglas locales y la fuente de glyphs del título fue Montserrat.
- El Vite de prueba se ejecutó en `127.0.0.1:5180`, mientras la configuración HMR conservó `clientPort=5176`; el runner registró errores de WebSocket de HMR, pero la página, API, CSS y mediciones se completaron. La apertura interactiva del menú móvil no se capturó en navegador.

Las pruebas usan datos sintéticos y no constituyen paridad completa INS-A ni aceptación humana. La tabla conserva el comportamiento legado de scroll horizontal; la verificación visual interactiva del menú móvil y las demás pantallas/formularios no pertenecen a este alcance.

## Archivos principales

- `src/frontends/apps/sisoc/src/InsumosList.tsx`
- `src/frontends/apps/sisoc/src/InsumosList.test.tsx`
- `src/frontends/apps/sisoc/src/App.tsx`
- `src/frontends/apps/sisoc/vite.config.ts`
- `src/frontends/apps/sisoc/index.html`

## Corrección acotada de navegación móvil y paridad de sidebar (2026-11-02)

- El control de grupos del menú usa el elemento `<a href="#" role="button">` del legado, con Enter/Espacio manejados sin doble activación ni cambio de hash. La cuenta recupera el separador y espaciado fuente (`border-top pt-2`); el encabezado agrupa botón y marca, y muestra la marca solo con el menú móvil abierto. El backdrop queda transparente, preservando su cierre por clic sin oscurecer la vista.
- La evidencia de origen fue el markup real de `opciones.html` y `header.html`, más Chromium en ambas aplicaciones: los grupos y las filas del menú quedaron alineados (ancho 316 px; filas Inicio/Legajos/Configuración/Insumos en y=250/310/370/430 en desktop). La cuenta se separa por 1 px de borde + 8 px de padding fuente; no se aplicó un desplazamiento mágico de 9 px ni `mt-auto`, que computaba 0 px en la referencia.
- RED/GREEN: la prueba nueva falló porque el grupo seguía siendo `BUTTON` y porque la marca permanecía visible con menú cerrado; tras la corrección, las 9 pruebas de `App.test.tsx` aprobaron. Chromium confirmó que Enter y Espacio activan exactamente una vez, mantienen URL/hash y Espacio no desplaza la página.
- Verificación final en scratch aislado: 24/24 Vitest, TypeScript, ESLint y build Vite aprobados; el build mantuvo sus avisos esperados de URL CSS Django resuelta en runtime. Playwright produjo 11 pares, 18 checks, cero fallos y cero solicitudes desconocidas. Diferencia de píxeles en capturas full-page: desktop default 0.498%, categoría 0.597%, página 2 1.231%, vacío 1.366%; móvil default 1.881%, categoría 2.427%, página 2 2.764%, vacío 2.927%; 991 px 0.352%, 992 px 0.586%. Las filas conservaron su geometría en todas las vistas.
- Límite observado: el menú abierto coincide en caja de sidebar (0,72; 300×772), visibilidad y hit-testing; la captura viewport abierta todavía difiere 26.907% de píxeles. La captura full-page abierta (12.594%) no sirve como medida del overlay porque Chromium omite el sidebar fijo de la referencia en esa modalidad. No se atribuye una causa nueva a esa diferencia sin evidencia suficiente y no se alteró el DOM/CSS del backend de referencia. El diff visual general no es cero; la aceptación humana y la paridad completa siguen pendientes.


## Estado vigente de la intervención renovada (2026-11-02)

Esta sección reemplaza las mediciones y conclusiones provisionales anteriores; conserva su historial, no las presenta como validación vigente.

- El scrim usa la clase original `sidebar-overlay`, con su fondo medido del 20%, no transparente. El logo móvil aparece con el menú abierto. La cuenta queda al final del DOM como en la plantilla y antes de Inicio visualmente mediante orden flex; el separador de Comunicados se replica desde su estilo explícito en la plantilla, no por `last-child`.
- El listado recupera en React las clases y señales de scroll de `poncho_scroll_tablas.js`, conservando el margen fuente de dos píxeles. Los eventos y ResizeObserver se desconectan al cambiar de consulta o desmontar; los callbacks tardíos quedan inactivos. No se carga jQuery ni el controlador legado en React.
- Verificación vigente: 29 pruebas Vitest, TypeScript, ESLint y build aprobados. Verificación independiente adicional: ocho pruebas de límites fraccionarios, remontaje y callbacks posteriores a limpieza, aprobadas. El build conserva los avisos de CSS Django resuelto en runtime.
- Comparación sintética: 11 pares, 24 verificaciones funcionales y ningún error de navegador/red. Diferencias sin tolerancia: escritorio normal 80 píxeles, categoría 146, página 2 1006, vacío 80; móvil normal 0, categoría 69, página 2 300, vacío 0, menú abierto 906; a 991 px 0 y a 992 px 80. Las dimensiones de todos los pares coinciden. El menú abierto se compara por viewport, no por captura full-page.
- La diferencia de 80 píxeles está localizada en el chevron de Configuración. DOM, geometría, color, transformación y fuente efectiva coinciden; la causa del pintado no está probada. Se observaron animaciones de filas todavía activas en una sonda separada. Un intento adicional de esperar el final de animaciones finitas agotó cinco segundos antes de producir pares; por eso tampoco se afirma una captura estable ni paridad completa.
- Evidencia externa al repositorio: fase `separator` del scratch `sisoc-menu-final-48cnhrry`, manifiesto fuente `e2d133951945cd53ba8436314459f2838399bd56089f782bd72fed41032de77e`. El intento `stable-paint` quedó registrado como fallido, no aprobado.
- Se abrió un navegador visible en `http://127.0.0.1:5176/v2/sisoc/insumos/` con datos sintéticos. La aceptación humana sigue pendiente. No se realizaron commit de UI, publicación, despliegue ni activación global; formularios React y matriz completa permanecen pendientes.

Riesgo: item 4, ciclo asíncrono del observador y eventos; verificado de manera independiente. La paridad visual continúa parcial y requiere decisión antes de otra intervención correctiva.


## Investigación adicional de estabilidad de captura (2026-11-02)

Autorizada por el usuario con “autorizo”; investigación sin modificaciones del código funcional, del DOM/CSS de referencia ni del criterio de aceptación.

- Las capturas full-page consecutivas de la propia referencia difieren en los mismos 80 píxeles del chevron. Después de capturarlas aparece hold-transition en el body fuente; AdminLTE lo agrega ante resize y lo elimina a los 400 ms. Esto prueba inestabilidad del método en ese caso, no que todos los residuos sean artefactos.
- En viewport original, escritorio normal coincide con React en cero píxeles, y ambas repeticiones individuales también coinciden en cero. No aparece el cambio de clase observado con full-page.
- En viewport fijo, página 2 conserva 926 píxeles diferentes, categoría móvil desplazada a scroll 2700 conserva 88 y menú móvil abierto 906; cada lado por separado se repite sin diferencias. Estas cifras son sondas de regiones visibles, no reemplazan la matriz completa.
- En página 2, las columnas segunda/quinta miden 163.9375/328.59375 px en la referencia y 163.921875/328.609375 px en React: diferencia de 1/64 px, ancho total 1100 px. Los estilos estándar muestreados coinciden salvo las dimensiones y orígenes resultantes.
- No quedó probada una causa por espacios de la plantilla. Los primeros clones aislados no reprodujeron la geometría nativa y no sirven como prueba causal. En clones del DOM completo los anchos se igualaron antes de sustituir texto/acciones, pero cambió el shorthand de fuente respecto del runtime; tampoco se usa esto como conclusión causal. Redimensionar normalmente 1439 → 1440 mantuvo la diferencia nativa.
- OverlayScrollbars aporta wrappers presentes solo en el origen, pero no se probó su responsabilidad en el pintado. El chevron tiene capa propia, glyph, color y transformación coincidentes en ambos lados.
- La espera global de animaciones falla por transiciones del scrollbar con timeline/endTime no numéricos. La espera acotada de animaciones finitas de filas sí termina, pero no elimina las diferencias persistentes.
- Evidencia: paint-investigation, viewport-investigation, computed-investigation, full-dom-lab y resize-investigation dentro del scratch de evidencia indicado arriba. La fuente frontend mantiene el mismo manifiesto.
- No se agregaron offsets, CSS de suavizado, máscaras, tolerancias ni nuevas referencias. La paridad sigue pendiente. Recomendación: evitar más ajustes especulativos de CSS; continuar los formularios aprobados sin cerrar el gate visual requiere resolver explícitamente esa secuencia, no aceptar implícitamente los residuos.


## Formularios React INS-A en validación (2026-11-02)

- Se implementaron alta, edición y confirmación de eliminación en InsumosForm.tsx, montadas desde las rutas React del shell. El backend sigue autorizando cada operación por separado; las capacidades del listado no sustituyen esos permisos.
- Se consumen los metadatos existentes del Form. Programa/categoría conservan opciones del servidor y filtrado por programa; no se duplica la validación de negocio. El envío es multipart mediante el cliente existente de sesión/CSRF. Editar sin archivo nuevo conserva el archivo actual; checkbox desmarcado omite activo, como el formulario HTML.
- Los errores 400 se muestran por campo, con valores conservados. Un POST de resultado incierto no se reintenta ni anuncia éxito: bloquea la repetición y remite a revisar el listado. Respuestas de otra ruta o de componentes desmontados no pueden navegar ni reemplazar la vista actual; existe bloqueo sincrónico de doble envío.
- Los mensajes de una operación se conservan únicamente en memoria. InsumosToast.tsx reutiliza el CSS Toastr ya existente y su posición inferior derecha; React controla su markup, temporizadores y limpieza, sin cargar jQuery ni una biblioteca nueva. La verificación de navegador de esta última presentación todavía está pendiente.
- La prueba real encontró un defecto del proxy local: Vite interpreta una ruta proxy string como changeOrigin=true. El cliente sí enviaba cookie/token y Origin correctos, pero Django rechazaba el Host reescrito. Se cambió solo /api/web a target explícito con changeOrigin=false. No se amplió CSRF_TRUSTED_ORIGINS ni se desactivó protección alguna.
- La CSS listModerno.css pertenece al listado, no al layout global: se retiró de index.html y se monta/desmonta con InsumosList, en la ubicación del template legado. Esto recuperó geometría/colores del formulario sin offsets ni modificaciones del origen.
- RED/GREEN observado: módulo de formulario ausente; luego aislamiento de respuestas anteriores y confirmación de borrado; integración de ruta/ancestría/retorno; proxy real 403 → 200; CSS específica del listado; temporización de mensajes. Comprobación actual: 43 Vitest, TypeScript, ESLint y build aprobados. No se instalaron dependencias.
- Navegador real contra el candidato sintético 18886: validación vacía 400 sin guardado, alta con PDF sintético, persistencia, edición sin reemplazo y activo falso, cancelación de borrado sin POST, eliminación y ausencia posterior: siete verificaciones aprobadas. Solo se registró el 400 deliberado y su aviso de consola. No se probaron cuentas ni datos reales.
- Se capturaron seis pares de formularios normales: crear/editar/eliminar en escritorio y móvil. Alta y eliminación coinciden en dimensiones del contenedor; edición sigue pendiente porque la plantilla Crispy contiene una fila adicional Actualmente. Estas capturas no son aceptación visual.
- El runtime inicial 18886 incluía CHANGELOG.md, a diferencia del origen backend-only, y mostraba otra etiqueta de pie. Se preparó 18887 con los mismos archivos backend de ebf, helper y copia sintética, sin ese metadato raíz: footer Versiones vuelve a coincidir. Un curl directo posterior confirmó 401 de la API sin sesión. La comparación de navegador sobre ese candidato y la revisión independiente final están pendientes.
- Decisión abierta: el widget Crispy muestra también la clave relativa de storage y enlaza directamente a media. El contrato aprobado solo entrega current_file.name (nombre) y download_url protegida. No se copiará el enlace público ni se ampliará el descriptor sin decidir esa diferencia. Se recomienda mantener nombre y descarga protegida, reproduciendo el widget sin la ruta interna.
- En esta continuación el usuario indicó exactamente: “pagina 2 y menu movil no interesa, ignoralo, continua”. Solo esos bloqueos visuales quedan excluidos; no se retiran sus pruebas funcionales ni las verificaciones móviles de los formularios.
- No hay commit de UI, publicación, merge, despliegue, aceptación humana ni modificación de admin/Unfold. La revisión independiente de seguridad/ciclos asíncronos y el cierre visual quedan pendientes, no omitidos como si hubieran aprobado.

### Presentación de denegaciones 403 en React

- Las peticiones de Insumos aceptan localmente solo respuestas 2xx o 403 para inspección; el adaptador convierte el 403 en error y conserva el comportamiento compartido de 401/login, CSRF y otros errores HTTP.
- Ante 403, listado y formularios muestran el contenido estático del template `src/backends/kernel/templates/403.html`. No se renderizan cuerpos HTML ni detalles arbitrarios del servidor. El POST denegado no se presenta como éxito ni se reintenta; los errores de validación 400 conservan su flujo.
- En `web/session/`, un 403 con un contexto completo y un estado de prerequisito conserva `access.state` y `required_action_url` para `AccessMessage`; cualquier otro 403 queda en la página de permisos, nunca en la pantalla de sesión vencida ni habilita el shell.
- Los endpoints React de Insumos usan otro payload 403 deliberadamente mínimo: `detail`, `state` y `required_action_url`. El adaptador acepta solo estados no preparados conocidos, ignora `detail` para el texto de UI y conserva el destino solo si es una ruta interna segura; así puede reusar la misma presentación de `AccessMessage`. Un 403 de permiso (solo `detail`), un estado `ready`, una URL externa/inválida, HTML o cuerpo no estructurado termina en la página estática fuente.
- El backend calcula los prerrequisitos con precedencia de acceso web, cambio de contraseña, confirmación de perfil y encuesta obligatoria. La API de sesión autenticada devuelve el contexto completo con 200 para esos estados; una sesión ausente devuelve 401. La adaptación no concede permisos de acción ni consulta `can_view` para habilitar el shell.
- La ruta de regreso usa `/inicio/`, equivalente al `dashboard` del template. La respuesta backend sigue siendo quien decide el estado HTTP y el permiso.
- Verificación focal RED/GREEN local en Vitest: los 403 de lista y POST con payload real `{detail,state,required_action_url}` debían preservar el requisito y bloquear controles/éxito; el 403 de permiso o HTML debía mostrar la página fuente. El endpoint de sesión conserva sus prerrequisitos sin convertir 403 no estructurado en login. Suite completa, TypeScript, lint y build aprobados localmente; navegador de extremo a extremo y aceptación visual permanecen pendientes del cierre integrado.

Riesgo: items 2, 3 y 4; sesión/CSRF, navegación/estilos compartidos y respuestas/temporizadores asíncronos.

### Actualización de verificación y decisión S10

- La decisión de descriptor antes abierta quedó resuelta por el usuario con “apruebo”: mostrar el nombre del archivo con descarga protegida, sin clave de storage, enlace público ni ampliación de API. El widget Actualmente conserva su estructura; con permiso de descarga presenta dos enlaces protegidos y sin View muestra dos nombres sin enlace. No es aceptación general de diferencias.
- Capturas posteriores: crear coincide sin píxeles distintos en escritorio y móvil; la cabecera de confirmación de eliminación requirió el peso 600 ya usado por el origen y su captura de escritorio quedó sin diferencias. Edición conserva la diferencia de nombre aprobada. Estos resultados no sustituyen la matriz completa ni la inspección humana.
- Los mensajes de operación se observaron visibles y se descartaron según los temporizadores; la verificación independiente anterior comprobó conservación de archivos, permisos sin View y ciclos asíncronos. La integración actual añade 53 pruebas frontend y 14 probes independientes de límites 403, todos satisfactorios; respuestas tardías no reemplazan la ruta vigente y no se modifica el cliente compartido.
- La prueba posterior por Django alcanzó las tres pantallas con usuarios de acción sin View y metadata API del mismo origen. La matriz visual completa sigue pendiente; no hay commit de UI, publicación, despliegue ni aceptación humana. Las notas previas de pendientes son historia de cada etapa, no pruebas omitidas ni aprobación implícita.

### Corrección de cascada del listado

- La primera captura de página completa por Django mostró 3475 píxeles distintos, frente a 31 en la repetición del origen. El análisis aisló colores incorrectos de paginación: React cargaba listModerno después de poncho_listados, contrario al orden documentado en search_bar.html. No era un cambio de geometría.
- El listado monta ahora poncho_listados inmediatamente después de listModerno, igual que el componente legado; ambos enlaces propios desaparecen al salir del listado. La hoja global permanece para no alterar las rutas de formulario. No se agregaron colores, offsets ni dependencias.
- RED real: la prueba de ciclo/orden esperaba el enlace posterior y recibió null. GREEN focal y suite de 53 pruebas, tipos y lint aprobaron. El primer comando de build usó un directorio incorrecto y no encontró index.html; ejecutado desde apps/sisoc, el build aprobó. Una primera sonda de test usó un matcher no instalado y fue corregida antes de registrar RED funcional.
- Verificación independiente por navegador con bundle congelado y fixtures equivalentes: ocho estilos del listado y seis del formulario coincidieron. La captura candidato coincidió byte por byte con la segunda captura del origen: cero píxeles entre ambas. La diferencia respecto de la primera captura fue 79 píxeles, exactamente la misma diferencia y bbox de la repetición del propio origen; no se afirma cero contra aquella primera captura ni se cambió el presupuesto visual.
- La navegación real listado→editar retiró listModerno y el enlace Poncho propio de la ruta, conservó el global y no produjo errores de consola ni API. La matriz visual restante continúa pendiente; no es aceptación humana. Evidencia local externa al repositorio: sisoc-list-cascade-check-20261102-a01, verification.json.

### Matriz parcial y pendientes no aceptados

- Ejecutados 19/36 casos y 40/74 combinaciones, no aprobados globalmente; restan 17/34. Filtro por categoría: 8582 píxeles frente a repetición del origen, mismos datos/estilos/fuentes, límites de columna difieren 0,016–0,031 px; causa no demostrada tras prueba de whitespace. Sin tolerancia ni offsets.
- Overlay móvil de grupo expandido corresponde al menú ya excluido; no se exime el contenido móvil ni funcionamiento. Seis pares de operación no tienen repetición del origen. Errores requeridos móviles: origen scrollY=0, candidato 227; pendiente. Título de alta: origen SISOC - Nuevo insumo, candidato SISOC - Insumos; pendiente.
- Comparación visible del filtro en 18893 y 18894, retenida por Node PID 53560; CUA no pudo asociarse a los IDs de ventana. No se afirma aceptación humana. Evidencia en sisoc-list-cascade-check-20261102-a01/scratch. Datos sintéticos, sin publicación ni cambios a runtimes originales.

### Criterio visual aprobado el 2026-11-03

El usuario indicó: “acepto, lo mismo de aca en adelante, siempre que la diferencia sea <1 pixel esta aprobado”. Se acepta el residual del filtro por categoría y, en adelante, desplazamientos geométricos medidos estrictamente menores a un píxel CSS con contenido, estilos y comportamiento equivalentes. No es un umbral de cantidad total de píxeles coloreados en un diff ni aprobación de cambios de contenido/color, controles ausentes, scroll, títulos o fallos funcionales. Se conservan métricas e imágenes sin máscaras. Scroll móvil, título de formulario y matriz restante siguen pendientes; no hay aceptación general ni permiso para publicar.

### Títulos de documento y bloqueo del entorno (2026-11-03)

- Se alinearon los títulos de listado, alta, edición y eliminación con los templates fuente; al volver al listado o desmontar la aplicación se restaura el título correspondiente. RED real: tres rutas de formulario conservaron el título estático incorrecto; listado pasó. Se agregaron pruebas de las cuatro rutas y regreso tras alta.
- La verificación independiente detectó un conflicto de limpieza: el padre restauraba el título externo y luego el error 403 hijo reponía un título capturado ya obsoleto. Una corrección acotada limita esa restauración al caso en que el hijo todavía conserva Error 403; se agregaron regresiones de sesión, listado y formulario al desmontar. Suite de 60, tipos, lint y build aprobaron; recheck independiente focal de cinco casos y repetición del padre aprobaron. No hubo commit ni publicación.
- Falta corroboración en navegador real del nuevo bundle. Los puertos anteriores y PID 53560 ya no existen; Docker no logra conectarse a su motor Linux. No se reinició Docker ni se usó otro runtime compartido.
- No se aplicó corrección especulativa al scroll: el formulario React no ejecuta focus/scroll y usa noValidate; falta medir antes del clic y el orden de eventos. Que Playwright haya desplazado el botón y la SPA conserve la posición es una hipótesis, no una causa demostrada.

### Retorno al inicio después de validación (2026-11-03)

- Con Docker nuevamente disponible se prepararon pares sintéticos nuevos. En móvil ambas páginas empezaron en scrollY=0 y el botón estaba debajo del viewport. El primer evento de interacción ya registró 227 en React; tras su API 400 conservó esa posición, mientras el POST legado navegó y terminó arriba. El mecanismo inicial del desplazamiento no quedó demostrado; sí la diferencia de navegación y posición final.
- Se restituye instantáneamente el inicio después de renderizar errores de validación del endpoint actual de alta o edición. Se usa useLayoutEffect, no un temporizador ni un cambio de foco; se mantienen valores, archivo seleccionado y protecciones de respuesta tardía/duplicación. Bajas, errores inciertos, permisos y respuestas ajenas no disparan ese retorno.
- RED real en alta/edición; suite de 62, tipos, lint y build aprobados. Verificación independiente de 25 casos y repetición del padre aprobaron; la base mantuvo nueve comportamientos previos y falló solo las dos nuevas reglas de retorno.
- Navegador real por Django: alta con errores y edición inválida en escritorio/móvil terminaron ambas en scrollY=0, con errores/alertas/títulos equivalentes y sin assets desconocidos ni hashes erróneos. Se verificaron también los títulos de listado/alta/edición/baja y acceso de alta sin View. Los hashes de datos de negocio y archivos no cambiaron dentro de cada lado; no se afirma identidad de hashes entre bases con datos de autenticación preparados independientemente.
- Las diferencias naturales del nombre de archivo ya aprobadas en S10 se registran aparte del criterio geométrico menor a un píxel. La matriz restante sigue en ejecución: no se declara aceptación general, commit, publicación o despliegue.

### Recuperación de evidencias y paridad de avisos/archivos

- Tras el reinicio se reconciliaron JSON y capturas antes de ejecutar casos nuevos. Un inventario truncado y un log vacío habían ocultado resultados de edición existente, confirmación y cancelación de edición; esos recorridos funcionales no se repitieron. La captura antigua de cancelación de edición sigue sin aprobarse visualmente: mostró tabla atenuada/hover y cabecera distinta, sin prueba de asentamiento completo. Una cancelación de borrado posterior sí coincidió una vez cargados CSS y fuentes, pero no sustituye automáticamente aquel caso.
- El aviso de éxito difería en dos estilos medidos sin animación activa: origen con opacidad 0,8 y fondo computado rgb(5,27,17), candidato con opacidad 1 y rgb(81,163,81). No era una diferencia subpíxel ni del texto del nuevo registro. Se mueve la hoja Toastr existente al head antes de AdminLTE, como en el origen, y se retira su inserción tardía del componente. Se elimina el override de opacidad; las animaciones usan el valor subyacente nativo, sin paleta nueva ni dependencias.
- En los rechazos de archivo, el formulario legado limpia la selección local y React la conservaba. El contrato aprobado exige las semánticas reales de ClearableFileInput/Form. Ahora un 400 estructurado del endpoint vigente limpia solo el archivo nuevo en estado y DOM; conserva los otros valores y el archivo ya persistido en edición. No añade envíos automáticos ni modifica el almacenamiento.
- RED real en orden/opacidad y en reenvío de archivo seleccionado tras validación; GREEN focal y suite de 66, tipos, lint y build aprobaron. Los primeros errores de carga de fixtures CSS de test eran del entorno de pruebas: el URL de asset transformado no era un file URL y el import CSS raw devolvía vacío; se corrigieron antes del RED válido, leyendo la hoja real. Verificación independiente de propiedad de respuesta/archivo: siete casos aprobaron. La comprobación real del nuevo bundle y el resto de la matriz siguen pendientes; no se afirma aceptación general, commit ni publicación.
- El manifiesto canónico leído en binario tiene 78.530 bytes; la copia retenida tiene 78.529. Solo difieren en el LF final y sus objetos JSON son idénticos; no se confunden los hashes de ambas representaciones. Los nuevos actores guardan resultados por caso antes y después de acciones para recuperar el progreso sin repetirlo.


### Cierre incremental de capturas y correcciones (2026-11-03)

- La matriz cuenta ahora con los 36 casos y 74 combinaciones de viewport capturados, tras las exclusiones visuales aprobadas. Capturado no significa identidad absoluta, aceptación humana ni cierre global: se mantienen las excepciones S2/S10 y los resultados originales sin máscaras.
- El error de campo conserva ahora el elemento strong del formulario Crispy fuente (peso visible 700); los errores generales no cambian. La página de permiso usa el título exacto SISOC - Error 403 y el espacio JSX entre icono y texto. RED real y suite final de 67 pruebas, tipos, lint y build satisfactorios. El padre repitió cinco probes independientes de propiedad del título.
- La verificación independiente final completó rechazo de categoría y extensión en ambas pantallas: selección nueva vacía tras 400, otros valores preservados, peso 700, geometría de campo idéntica y hashes de negocio/media sin cambios. Móvil: diff cero; escritorio: 76 píxeles restringidos al glifo de sidebar ya medido con rectángulo/estilos/transformación iguales; todas las repeticiones fueron estables. No se aplica un umbral sobre cantidad de píxeles cambiados.
- La cancelación sin View llegó realmente al listado API 403, sin GET de documento ni escritura: título, icono y presentación iguales; diff cero en ambos viewports. El espacio medido difiere 0,015625 píxeles CSS, dentro de S2.
- Los avisos nuevos conservaron fondo y opacidad nativos; capturas de conservación y reemplazo móvil dieron diff cero. La cancelación de edición se recapturó sin POST, con CSS/fuentes cargadas y estabilidad: diff cero móvil y 79 píxeles del glifo en escritorio. La captura antigua cuya repetición cambiaba 74.801 píxeles es inválida, no un defecto estable acreditado.
- Evidencia externa: sisoc-fileclear-final-ohoyqf0z/verification-report.md y sisoc-insa-t7-resume-20261103-b5078432. El bundle vigente es index-fcNhx9jf.js. La prueba humana visible queda preparada en http://127.0.0.1:53489/v2/sisoc/insumos/ con datos sintéticos; no equivale a aceptación. Continúan separados contratos pendientes, revisión nativa, commit de UI, CI y publicación.


### Contratos restantes y respuesta perdida

- La evidencia incremental completa los doce contratos INS-A del manifiesto, sin repetir los ya acreditados. La fase final comprobó por HTTP la descarga exacta, el registro existente sin archivo y el ID inexistente como dos 404 distintos, la denegación de edición/baja heredadas al rol solo alta/consulta, y la descarga 403 sin bytes del PDF ni attachment. Cada grupo de lectura conservó hashes de negocio y media.
- Se envió una única alta sintética real: el proxy de prueba reenvió el POST una vez, recibió 200 y comprobó registro y archivo persistidos antes de abortar la respuesta al navegador. La UI quedó incierta, sin aviso de éxito y con reenvío bloqueado. La API de lectura y Cancelar hacia el listado reconciliaron exactamente un registro/archivo; no hubo repetición manual. No se modifica el backend para simularlo.
- La prueba anterior de CSRF, métodos 405, descarga inactiva, fallo de storage después de eliminar y baja sin View se conserva como evidencia histórica, no como ejecución fresca. INS-B queda fuera. Un timeout del harness ocurrió antes de la mutación; el checkpoint permitió continuar solo la rama aún no iniciada. El padre verificó las aserciones del recibo y los hashes de fuentes vigentes, sin repetir escrituras. Una URL de asset inferida no acreditó el bundle; el acceso anónimo al preview devuelve el 403 esperado, sin invalidar la prueba autenticada conservada.
- Evidencia: sisoc-insa-contract-last-g7poz1e1/contract-verification-report.md y contract-delta-summary.json. Su contenedor ya está detenido; la demostración sintética 53489 permanece. Falta confirmación humana del recorrido local y tratamiento del candidato nativo antes del commit de UI; no hay publicación, CI ni despliegue acreditados.

## Corrección acotada del alias durante la separación local

La entrada existente `/v2/sisoc/insumos` sin barra final no activaba el enlace
ni expandía su grupo: ambos predicados de navegación reconocían solamente la
variante con barra y sus descendientes. Se reconoce ese alias exacto sin
redireccionar, reescribir la URL ni aceptar prefijos ajenos. La regresión
comprueba visibilidad, `aria-current`, expansión del padre y pathname intacto,
junto con la ruta canónica y dos prefijos no pertenecientes al circuito.

Esta corrección no declara aceptadas las diferencias de pintura pendientes
en la flecha del sidebar y la tabla filtrada, ni cambia la excepción S10.
