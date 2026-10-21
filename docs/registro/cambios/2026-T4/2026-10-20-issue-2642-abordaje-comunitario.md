# Issue #2642: evolutivos de Abordaje Comunitario

## Comportamiento

1. Alta y edición de Organizaciones incorporan la sección colapsable «Datos
   Abordaje Comunitario» debajo de Vigencia. Región y Subzona son opcionales y
   se eligen de catálogos cerrados administrables desde Django Admin.
2. Rendiciones permite filtrar Región y Subzona de la organización del proyecto,
   con fallback a la organización del comedor para registros históricos.
3. Solo una rendición por proyecto puede estar en Territorial en curso,
   pendiente de correcciones o subsanada. Iniciar otra muestra la rendición
   que ocupa el cupo; pasar a Revisión para Carga pendiente lo libera.
4. Comedores ordena sus filtros alfabéticamente por etiqueta y Organizaciones
   reutiliza el mismo componente de filtros combinables, con sus campos propios.
5. Formulario I aparece después de Seguros II cuando corresponde y antes de
   Documentación Adicional, con la leyenda bancaria solicitada.
6. En Mobile, Organización se toma del contexto de ingreso y Línea Programática
   se deriva del proyecto; ambos se muestran como solo lectura. Proyecto sigue
   siendo seleccionable entre los activos de esa organización. El servidor
   calcula la línea tanto en el alta como en su validación previa e ignora una
   línea contradictoria del cliente cuando hay proyecto explícito.
7. En Convenio, personas SIPH queda junto a Personas conveniadas en Tradicional
   y junto a Cantidad Módulos Mensuales en Secos. Los montos se muestran como
   `100.000.000`, sin decimales, también en el detalle. Guardar otro campo sin
   cambiar el monto conserva los centavos históricos. Nuevos valores escritos
   admiten pesos enteros con o sin separador de miles; rechazan formatos ambiguos.
8. El legajo permite agregar y quitar parejas Proyecto–Territorial. Ambos datos
   son necesarios para agregar una pareja, pero la sección completa es opcional.
   Convenio muestra las asignaciones con su código de proyecto. La columna y el
   filtro Territorial de Rendiciones consideran también estas asociaciones.
9. Las decisiones documentales se guardan como borradores compartidos de la
   revisión en curso, rectificables hasta finalizar Territorial o Revisión para
   Carga. El cierre confirma estados y observaciones en una única transacción.
   Mientras tanto, la organización recibe los estados confirmados anteriores.
   Un cierre incompleto no confirma parcialmente los documentos. Los documentos
   reemplazados del historial no admiten decisiones nuevas.
10. La descarga alimentaria de Formulario V usa el XLSX adjunto al issue en ambas
    líneas. El modelo de SIPH se conserva.

## Decisiones y datos pendientes

- El 21/10 se recibió `REGIONES_Y_ZONAS.xlsx`: la migración
  `organizaciones.0026_issue_2642_regiones_zonas_excel` reemplaza las opciones
  provisorias por cinco regiones y 28 subzonas vinculadas. Las provisorias se
  desactivan, conservando cualquier FK existente, sin inferir equivalencias.
  El selector y el POST restringen las subzonas a la región elegida.
  Detalle: `docs/registro/cambios/2026-T4/2026-10-21-issue-2642-regiones-zonas-excel.md`.
- Se interpreta AMBA como coincidencia exacta de código **o nombre** de proyecto,
  ignorando mayúsculas y espacios externos. Si el área define otro identificador,
  debe ajustarse `inferir_linea_programatica`. La API entrega la línea calculada
  en `organizacion_proyectos`; Mobile la usa y mantiene fallback para su caché.
- Los registros antiguos sin proyecto conservan el contrato de línea anterior
  para no romper cargas offline ya preparadas por versiones previas de Mobile.
- Las asignaciones generales anteriores no reciben proyectos inferidos. Se
  muestran separadamente y se conservan. Al asociar explícitamente una persona
  a un proyecto se retira su asignación general; las demás siguen disponibles.
- Los estados históricos inconsistentes no se corrigen automáticamente.

## Dueños, esquema y compatibilidad

`organizaciones` (kernel) conserva los datos maestros: los dos catálogos,
las FK opcionales de Organización y la M2M Proyecto–Territorial. No importa
código de Comedores. La validación de usuarios elegibles y las pantallas viven
en `gestion_organizaciones` (Comedores). Los borradores documentales pertenecen
a `rendicioncuentasmensual` (Comedores). No hay dependencias nuevas entre servicios.

El bloqueo del inicio Territorial usa la organización como ancla común entre
proyectos explícitos e históricos; sin ella usa el comedor y, en registros
huérfanos, la propia rendición. Se serializan brevemente los inicios de la
organización, pero proyectos distintos pueden permanecer activos a la vez.
Las bajas lógicas no ocupan cupo. Guardar decisiones y finalizar una revisión
bloquean la rendición para evitar que un borrador se escriba después de su cierre.

Los estados y claves documentales de la API no cambian. Los borradores no se
incluyen en las respuestas documentales de Mobile ni habilitan la descarga PDF.
No se agregan dependencias frontend: se reutilizan estilos y componentes locales.

## Despliegue y reversa

- Ejecutar en el migrador `organizaciones.0024_issue_2642_abordaje_comunitario`,
  `organizaciones.0025_issue_2642_catalogos_provisorios`,
  `organizaciones.0026_issue_2642_regiones_zonas_excel` y `rendicioncuentasmensual.0027_issue_2642_abordaje_comunitario`.
- Publicar backend Comedores y generar sus estáticos por el circuito habitual.
- Coordinar la PWA del repositorio `SISOC-EspaciosComunitarios`, rama
  `Fixes-Issue-2642`: contexto y tipo de proyectos, selectores de solo lectura y tests.
- El catálogo definitivo se carga con la migración 0026. Las organizaciones
  que todavía tengan opciones provisorias pueden conservarlas al editar otro
  dato; deben reasignarse manualmente cuando se conozca su correspondencia.
- Para revertir, preservar previamente catálogos, asociaciones y borradores;
  coordinar la vuelta del backend y Mobile antes de deshacer las migraciones.
  Revertirlas borra datos de campos/tablas nuevos y pierde decisiones sin confirmar.

## Validación

- 347 tests aprobados y uno omitido en SQLite (el test de concurrencia requiere MySQL).
- Después de endurecer el POST de nuevas asignaciones, 66 regresiones focalizadas
  adicionales aprobaron, incluida la exigencia de proyecto ante cargas manuales.
- 60 tests aprobados sobre MySQL 8.4 temporal, incluida la aplicación del grafo de
  migraciones y dos inicios simultáneos con un solo cupo disponible.
- Mobile: seis tests aprobados, TypeScript, build Vite y ESLint de archivos modificados.
- Chrome con datos ficticios: revisión de escritorio y ancho móvil, colapso por
  teclado, agregar/quitar asignaciones, montos y selección documental editable.
- Black y control de migraciones aprobados. Pylint conserva exclusivamente los
  avisos preexistentes de `src/backends/comedores/comedores/views/comedor.py`,
  contrastados contra HEAD. Las rutas documentales no tienen referencias obsoletas.
- Djlint aprueba cinco templates. El chequeo de `comedor_detail.html` supera
  35 segundos tanto en HEAD como con este cambio; no se reformateó masivamente.
- El MySQL temporal no tiene volúmenes ni puertos publicados y se elimina al cerrar.
- No se aplicaron migraciones a la base local ni se hizo deploy.

## Correcciones durante CI del PR #2751

- Regenerado el registro de URLs para las pantallas de administración de regiones
  y subzonas. Los tests de permisos de mensajes verifican primero que la
  notificación exista para el usuario autorizado al finalizar la revisión.
- El test histórico de la migración 0019 restaura ahora todas las migraciones
  vigentes al terminar, para no dejar un esquema incompleto a los tests siguientes.
  La suite completa de compatibilidad MySQL aprueba sus 15 tests.
- Suite completa SQLite: 7.204 tests aprobados y 26 omitidos; cobertura total
  89,92 % y cobertura de líneas modificadas 92,46 %.
- Actualizado únicamente Vitest de 4.1.11 a 4.1.12 y sus paquetes asociados para
  resolver los avisos GHSA-qxg6-89mg-rqv8 y GHSA-xp26-3454-mjgp, que comenzaron
  a bloquear la auditoría npm durante el seguimiento del PR. Es una dependencia
  de pruebas; se mantiene la misma versión mayor y menor.
