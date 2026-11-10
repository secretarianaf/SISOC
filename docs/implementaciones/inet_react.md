# INET React: pantallas y comportamiento

## Alcance y pantallas

INET gestiona centros de formación profesional (CFP), ubicaciones, contactos,
planes curriculares, cursos, comisiones, inscripciones y asistencia. Reutiliza
los datos y reglas de VAT mediante la API interna de SISOC.

| Pantalla | Ruta | Contenido |
| --- | --- | --- |
| Buscador de CFP | `/v2/inet/` o `/v2/inet/centros/` | Filtros, resultados y exportación. |
| Legajo de CFP | `/v2/inet/centros/:id/` | Información, mapa, ubicaciones, contactos, cursos y comisiones. |
| Nueva comisión | `/v2/inet/comisiones/nueva/?curso=:id` | Ubicación, cupo, período, horarios y confirmación. |
| Edición de comisión | `/v2/inet/comisiones/:id/editar/` | Datos y horarios con advertencia sobre regeneración de clases. |
| Legajo de comisión | `/v2/inet/comisiones/:id/` | Información, indicadores, inscriptos y clases. |
| Asistencia | `/v2/inet/sesiones/:id/asistencia/` | Nómina, presentes, ausentes y observaciones. |
| Planes curriculares | `/v2/inet/planes/` y `/v2/inet/planes/:id/` | Búsqueda, detalle y administración según permisos. |

Los formularios de CFP, curso, ubicación, contacto e inscripción se abren desde
su contexto. Las bajas y eliminaciones requieren confirmación.

## Presentación y navegación

- Se conserva la distribución vigente de campos, botones, paneles y columnas.
- Temas claro y oscuro, Roboto local y componentes compartidos SISOC, con
  encabezado institucional, navegación lateral desplegable y pie institucional.
- Buscador con selección de campo, valor y Agregar filtro. Los filtros aplicados
  aparecen como chips editables y pueden quitarse individualmente.
- Contador de resultados y Exportar búsqueda para el conjunto filtrado.
- Legajo de CFP con mapa y grupos Establecimiento, Domicilio y Referente del centro.
- Legajo de comisión con contexto del CFP, ubicación, horarios e indicadores de
  inscriptos, clases dictadas y asistencia general.
- Fechas en formato día/mes/año, columnas numéricas a la derecha y tablas con
  desplazamiento interno en pantallas pequeñas.
- Formularios con ayudas, errores junto al campo y avisos de resultado. Al crear
  un curso se ofrece continuar con Crear comisión.
- Divisores, placeholders, alertas, estados y controles usan el tema compartido;
  los bordes de controles conservan contraste AA en ambos modos.
- Ante errores de pantalla se ofrece Volver o Reintentar. Las fechas vacías o
  inválidas se muestran como `—` sin interrumpir los formularios.

## Mapa del centro

El mapa consulta Google Maps con calle y número, o domicilio de actividades como
alternativa, junto con localidad, provincia y Argentina. Sin domicilio o territorio
suficiente se muestra un mensaje en el mismo espacio. Requiere conexión y depende
de la resolución del domicilio por el proveedor; no son coordenadas certificadas.

## Reglas de datos y permisos

- Los accesos se delimitan por permisos VAT y alcance territorial o CFP.
- La búsqueda de personas usa un documento exacto en SISOC. La identidad y los
  contactos se administran en Ciudadanos; INET gestiona la inscripción.
- La inscripción sin DNI exige un motivo y queda Sin validar.
- Cupos y duplicados se validan en el backend. Las altas compuestas se guardan
  en una transacción para evitar personas nuevas sin su inscripción ante un fallo.
- Los cursos admiten inscripción libre o gestionada; esta última no equivale
  necesariamente a una condición exclusiva de voucher.
- Al editar horarios se conservan clases realizadas o canceladas y asistencias;
  se regeneran las programadas sin repetir fechas históricas.
- La asistencia exige la nómina activa completa. Los no marcados se guardan como
  ausentes; las observaciones permanecen disponibles bajo la tabla.
- Las clases completadas permiten Ver asistencia. Las pendientes y las
  programadas de hoy o anteriores permiten Cargar asistencia.
- La baja libera cupo y conserva historial. La asistencia general se calcula
  sobre inscripciones activas y clases realizadas, por lo que puede variar al
  dar de baja o restaurar una inscripción.
- Con historial relacionado se ofrece un cambio de estado cuando corresponde;
  antes de eliminar se muestran los efectos sobre los registros relacionados.

Configuración, API y comandos: `docs/operacion/inet_react.md`.
