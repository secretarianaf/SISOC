# INET: frontend React e integración con SISOC

## Cambios funcionales

- Buscador y legajo de CFP con ubicaciones, contactos, oferta educativa y comisiones.
- Administración de planes curriculares y cursos con los catálogos existentes.
- Creación y edición de comisiones con horarios, cupos, período y resumen previo.
- Inscripciones con o sin DNI, control de duplicados, bajas y conservación del historial.
- Registro de asistencia con nómina completa, observaciones e indicadores.
- API interna con sesión, CSRF, permisos VAT y alcance por centro/provincia.
- Operaciones compartidas con las vistas anteriores para mantener validaciones
  y proteger el historial de clases y asistencias.

## Cambios visuales

- Navegación lateral, encabezado y pie institucional, con modos claro y oscuro.
- Filtros como chips, contador de resultados y exportación de búsqueda.
- Paneles agrupados, mapa del CFP y contexto de la comisión.
- Tablas compactas, fechas legibles y columnas numéricas alineadas a la derecha.
- Formularios con ayudas y errores junto al campo; confirmaciones y avisos de
  éxito con acciones de continuidad.
- Corrección del mapa, conservación de valores en selectores territoriales y
  recuperación ante errores de pantalla o fechas inválidas.

Se conserva la distribución vigente. La adaptación a la estructura actual de
SISOC actualiza configuración, rutas y builds sin reorganizar las pantallas.
Las dependencias compartidas existentes se actualizaron a versiones compatibles
corregidas para superar el control de seguridad.

## Datos y verificación

Se reutilizan los modelos existentes, sin tablas ni migraciones nuevas propias
de INET. Las diez tablas locales revisadas conservaron sus 37 registros y sus
huellas de contenido tras actualizar el entorno. No se detectaron inconsistencias
en relaciones de centros, comisiones, horarios y asistencias. Las migraciones
existentes de SISOC se aplicaron con respaldo previo.

- 39 pruebas de INET y permisos de ubicaciones y 64 de rutas, proxy, aislamiento
  de servicios y vistas/formularios anteriores: aprobadas en bases de prueba.
- 100 pruebas del frontend aprobadas con dos procesos.
- Un flujo Chromium aprobado: navegación, validación, CSRF, temas, móvil y mapa,
  con APIs y proveedor del mapa simulados.
- TypeScript, contratos API y builds de las tres apps y de la imagen INET:
  correctos. Auditoría de dependencias sin vulnerabilidades.
- Formato Python correcto. Persisten avisos preexistentes de lint en una vista
  anterior y advertencias de desarrollo de React, sin impedir la compilación.

La verificación es local; no acredita el pipeline remoto completo ni la
disponibilidad del proveedor externo del mapa.

Pantallas y reglas: `docs/implementaciones/inet_react.md`.
Configuración y comandos: `docs/operacion/inet_react.md`.
