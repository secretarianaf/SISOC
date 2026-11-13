# Cambio: API de la ficha del comedor para React, cabecera y tarjeta de título (#2785, CO07.01)

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
- El contrato crece agregando claves, sin renombrar. Quedan para las próximas entregas el
  acordeón de datos, la línea de tiempo, las tarjetas, las tablas de admisiones, las
  certificaciones, los colaboradores, las capacitaciones y los modales; la nómina y las
  tablas de intervenciones y observaciones siguen siendo fragmentos nativos.
- No hay pantalla React ni ruta de vista previa todavía: se registran cuando la pantalla
  esté completa.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red), 10 pruebas: bloques de cabecera y título contra
  los valores nativos, selector de convenios (seleccionado y enlaces), acciones según
  permisos, 404 fuera de alcance, que leer no escribe, métodos, cada permiso de acceso,
  401, 403 y requisito web pendiente con cabecera falsificada. Las pruebas reemplazan el
  doble automático de la carpeta para correr los servicios reales.

## Limitaciones y diferencias conocidas

- La proyección corre todo el contexto nativo de la ficha (como la página), por lo que su
  costo es el de la página actual.
