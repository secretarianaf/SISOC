# Alta y edición de Relevamientos en las URLs canónicas

El listado React de Acompañamiento Territorial muestra **Cargar formulario** a quien tiene permiso de alta. El detalle muestra **Editar** a quien tiene permiso de edición. Esas acciones abren el mismo formulario React, respectivamente en `/comedores/<comedor_pk>/relevamiento/crear` y `/comedores/<comedor_pk>/relevamiento/<pk>/editar`. No reemplazan el modal operativo de asignación ni los flujos PWA, Seguimiento o PDF.

- Las entradas sirven React si se activa `comedores` y existe el build. Si se desactiva, la resolución vuelve a las vistas Django.
- Los dos endpoints web requieren G1, sesión, CSRF para la escritura y el permiso de la ruta. La edición, incluida la vista Django de reversión, comprueba que el relevamiento pertenezca al comedor de la URL. Las rutas web no reciben otro comedor desde el formulario.
- El adaptador ejecuta la construcción, validación y guardado de los formularios Django existentes. Una respuesta inválida conserva campos y errores sin renderizar HTML; un éxito vuelve al detalle canónico. El cliente no reenvía una escritura con resultado incierto.
- El formulario nativo omitía preguntas obligatorias de Punto de Entrega y su JavaScript deshabilitaba otras preguntas obligatorias del anexo. React muestra esas preguntas, sin inferir respuestas adicionales a los valores iniciales provistos por Django, y solo borra y deshabilita campos dependientes que sean opcionales. El servicio guarda al responsable en el vínculo persistente; antes escribía un atributo transitorio. Si se elige el referente del comedor, conserva el vínculo existente sin duplicar el contacto. Al editar, muestra el responsable guardado y no modifica contactos compartidos ni los datos congelados.

## Cómo verificar

1. Desde el listado del comedor, abrir **Cargar formulario**, responder las preguntas y guardar. El detalle debe aparecer en la URL canónica.
2. Desde ese detalle, abrir **Editar**, cambiar una observación y confirmar. Verificar el valor al recargar y que se mantiene el comedor.
3. Con un usuario solo lector, verificar que no aparecen los dos enlaces y que las URLs directas no permiten abrir ni guardar el formulario.
4. Repetir el recorrido en móvil y con teclado. Comprobar el desplazamiento horizontal de la tabla de prestaciones y que un POST inválido conserva datos y errores.

La comparación visual con Django tiene la diferencia intencional de las preguntas faltantes. No reemplaza la aceptación del recorrido en un navegador contra un entorno integrado.

## Evidencia de desarrollo

La suite focal de pytest sobre SQLite pasó al cubrir creación y edición reales, asociación con el comedor, permisos, CSRF, reversión, enlaces, validación y el servicio nativo. Vitest verificó las entradas React canónicas, los controles dependientes, la carga del editor y los errores ligados; el typecheck de la app pasó. Chrome con un build del workspace y una base SQLite sintética verificó el alta desde el enlace y el teclado (1440 × 960): el envío inválido conservó los datos y no creó otra fila; el válido abrió el detalle. También comprobó la edición desde ese detalle en modo móvil (390 × 844), la persistencia tras recargar, el foco y el desplazamiento horizontal limitado a la tabla. El perfil lector no vio los enlaces y recibió 403 por URL directa. Otro comedor recibió 404. El detalle admite el estado nativo nulo de un alta sin inventar un estado persistido. Quedan fuera de esta prueba la comparación visual píxel a píxel y la topología remota.
