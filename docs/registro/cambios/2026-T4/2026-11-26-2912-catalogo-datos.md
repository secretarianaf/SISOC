# Cambio: catálogo operativo para Datos (#2912)

## Alcance

La pantalla dedicada permite editar nombre, estado y visibilidad del menú de tableros existentes. La ruta y el guardado exigen el rol explícito `Equipo de Datos` o ser superadministrador activo; no conceden administración general de usuarios. Los campos técnicos y permisos no se modifican desde el formulario.

El menú ofrece «Administración de tableros» dentro de «Tableros» al equipo de Datos y a superadministradores activos. El acceso se verifica de nuevo en el servidor; mostrar u ocultar el enlace no sustituye esa autorización ni amplía los tableros ordinarios de un usuario con restricciones.

La búsqueda por nombre de usuario permite administrar asignaciones individuales nacionales o por varias provincias. Agregar es aditivo y revocar afecta solamente la concesión individual elegida; no altera grupos ni asignaciones de audiencias. Las asignaciones guardadas no garantizan que el tablero o su proveedor apliquen la política. La pantalla muestra por separado las asignaciones por audiencia.

Cada asignación indica si su tipo de alcance tiene una política integrada activa en ese tablero. Ese estado no afirma que el usuario tenga acceso efectivo por otras condiciones, ni acredita el aislamiento de proveedores externos.

Las audiencias permiten crear y renombrar grupos de tableros, agregar o quitar miembros y mantener sus asignaciones. Las membresías no cambian roles generales y se emplean las operaciones auditadas existentes. El front incluye enlaces a creación e importación de usuarios; esas rutas conservan sus propios permisos.

Las pantallas de catálogo, usuarios, asignaciones, audiencias y selección de CDI reutilizan los componentes y estilos existentes de Comedores. La revisión visual final de esos recorridos permanece pendiente.

El selector CDI consulta al servicio dueño y ofrece solo centros activos no borrados. Antes de guardar un lote, valida todos los identificadores; si el servicio falla o la respuesta es incompleta, no se guardan concesiones. La selección es múltiple por página y permite agregar más centros después.

## Seguridad y verificación

Los enlaces **Crear usuario** e **Importar usuarios** solo se muestran con el permiso de alta existente. Las rutas mantienen sus propios controles: la pertenencia al equipo de Datos no concede ese permiso. Una prueba sintética comprueba visibilidad y respuesta de ambas rutas, con y sin permiso. Este ajuste no tiene todavía validación visual final.

Las solicitudes de escritura usan CSRF y las modificaciones pasan por la auditoría del modelo. Se probaron con datos sintéticos el acceso sin rol, el guardado, la auditoría, la conservación de campos técnicos y el caso de un slug preexistente. La suite de dashboard pasó y el usuario confirmó los casos visuales positivo y negativo. La revisión independiente no se completó por una negativa del proveedor; las correcciones posteriores no tienen verificación independiente.

Las asignaciones individuales y de audiencias cuentan con pruebas sintéticas de creación, revocación, rollback, auditoría y protección de concesiones ajenas. Una verificación independiente encontró que `HEAD` era interceptado antes de autorizar las nuevas rutas; el middleware se ajustó y el rechequeo de esas rutas pasó. La verificación independiente del flujo de audiencias no encontró bloqueantes. La validación visual y verificaciones finales de ambos flujos siguen pendientes.

## Asignaciones y membresías por lote

La administración de usuarios y el detalle de audiencias comparten un formulario de asignación por lote. Se seleccionan varios tableros y un alcance nacional, varias provincias o varios CDI activos. La acción agrega concesiones sin reemplazar las existentes y rechaza el lote completo si no puede aplicarlo. La base serializa las escrituras por sujeto y la auditoría registra cada fila. La sección Miembros permite agregar varias personas existentes mediante sugerencias; no cambia sus roles generales. Se conservan las operaciones anteriores y sus controles de autorización.

En la copia integrada pasaron 198 pruebas en Docker/SQLite sin migraciones y se omitió una. En MySQL 8.4/InnoDB sintético se observaron diez carreras provinciales entre lotes o revocaciones, con espera real del bloqueo, sin duplicados ni escrituras parciales y con auditoría por actor. Esa prueba no cubre migraciones, concurrencia CDI ni carga sostenida.

## Ajustes de la revisión visual

Cada fila del catálogo abre un modal de edición con los campos operativos ordenados y conserva los errores de la fila editada. El listado de usuarios muestra las asignaciones de la página por tablero, alcance, origen y estado según la política existente. El catálogo no habilita el acceso a tableros desde el menú ni concede el permiso de alta o importación de usuarios.

## Limitaciones

Las concesiones CDI quedan preparadas, pero aún no filtran datos: el usuario confirmó que el tablero que las utilizará todavía no existe. Cuando se implemente, deberá revalidar el alcance al consultar e integrar el filtro específico del tablero o proveedor. Ocultar el menú no bloquea una ruta directa. El aislamiento efectivo depende de la aplicación del alcance por cada tablero y proveedor. No se accedió a datos reales ni se publicó el cambio.

En Celiaquía no se excluirán los expedientes con registros de varias provincias; el equipo de Datos definirá su tratamiento definitivo. Una prueba sintética conserva el expediente al consultar cada provincia. Esto no demuestra aislamiento provincial estricto: siguen expuestos metadatos compartidos y la atribución de errores requiere validación de Datos.

El alcance para Celiaquía se obtiene de la sesión en el núcleo. El Compose versionado configura el origen interno; ante falta de conexión la consulta falla cerrada, incluso para usuarios legacy. Otros despliegues necesitan configurar ese origen antes de adoptar el cambio. La sesión viaja por HTTP interno: se requiere una red confiable y un proxy que impida acceso directo a los servicios y sanee cabeceras reenviadas. Dos procesos aislados con sesión sintética pasaron pruebas de acceso, revocación y falla; eso no demuestra la configuración ni el aislamiento de una instalación real.

Las migraciones de `dashboard` y sus dependencias se probaron en SQLite y MySQL sintéticos. Se corrigió una incompatibilidad de colaciones en el control de concesiones y se verificaron dos combinaciones de colación de base y conexión en MySQL 8. Si existen configuraciones de Celiaquía, la reversión de la configuración se rechaza antes de modificar la restricción; requiere ausencia de escrituras concurrentes. El grafo completo de MySQL pasó en una base vacía sintética con `utf8mb4_0900_ai_ci` después de esa corrección; esto no prueba una actualización sobre datos reales. El grafo completo en SQLite falló también en la base sin estos cambios, por una migración de CDI.

## Alcance de esta entrega

La asignación nacional habilita la entrada desde SISOC a los informes externos del catálogo; no controla el acceso directo en el proveedor ni aplica filtros territoriales externos. Los informes de portada de Centro de Familia y Comedores se incorporan como fichas independientes y conservan la compatibilidad anterior. Inspecciones, sus exportaciones y sus descargas quedan fuera de esta entrega.
