# Auditoría conjunta de rendiciones — issue #2673

Registro consolidado del cambio, actualizado el 16/10/2026. Reemplaza los
registros de las iteraciones de cierre, búsqueda, navegación, validación,
regularización, origen del acta y alineación visual. La especificación vigente
está en [Rendiciones mensuales](../../../flujos/rendiciones_mensuales_proyectos.md).

## Comportamiento final

Nueva pantalla de Auditoría dentro de `sisoc_core/rendicioncuentasmensual`,
accesible desde el detalle y desde «Nueva Auditoría», ubicado sobre la tabla
del listado. Se gestionan rendiciones existentes, sin crear auditorías sueltas
ni duplicar información general. No se solicitan montos en esta pantalla.

- Si todavía no está validada, es obligatorio confirmar el checkbox. Se puede
  guardar solo la validación: queda Auditoría en curso, sin decisión de acta
  ni fecha de cierre, y se vuelve al detalle base.
- Al reingresar, «Validada: Sí» es inmutable y la decisión Sí/No sobre el acta
  es obligatoria. También se puede confirmar la validación y decidir el acta
  en el primer ingreso. El botón alterna entre «Guardar» y «Guardar y cerrar
  Auditoría» según esa decisión y el estado persistido.
- Guardar una decisión Sí/No cierra la gestión individual. No se puede
  reabrir desde detalle, buscador, GET/POST directo o el servicio histórico.
  No permite incluirse en otra acta hasta estar validada y cerrada con No.
  En ese caso se muestra «Auditoría validada sin acta» como etiqueta visible,
  conservando el subestado interno existente.
  La etiqueta exige validación afirmativa, decisión No, cierre y subestado
  `en_curso`; los históricos finalizados conservan su resultado visible.
- Con Sí se exige resultado y, si hay observaciones, su texto. El archivo de
  acta y el Acta Complementaria conservan su carácter opcional.
- Las incorporadas deben estar activas, en Auditoría pendiente/en curso,
  validadas, con gestión cerrada sin acta y sin archivo de acta; comparten
  código de proyecto y organización. Hay fallback legado por comedor.
  No se impone un máximo de períodos ni una restricción por línea.
- La base se incluye automáticamente. El grupo comparte resultado,
  observaciones, documentos, fechas y vínculos. El guardado bloquea filas
  en orden de PK y revalida las selecciones dentro de la transacción.
- Una auditoría finalizada con observaciones permite regularización solo
  desde la rendición que originó el acta, con el permiso existente. Las
  incorporadas reciben las transiciones y Acta Complementaria, pero no
  pueden ejecutarlas ni mediante POST directo. La propagación también
  contempla grupos históricos cuyo campo de validación es NULL.
- «Acciones del proceso» se muestra cuando existe alguna acción autorizada
  para el estado y la rendición actuales; no depende solo de tener acta.

## Búsqueda, navegación y presentación

El filtro predeterminado es Proyecto. No hay resultados antes de buscar ni
con texto vacío. La coincidencia es parcial, sin distinguir mayúsculas ni
tildes españolas, y consulta solo el filtro elegido: código/nombre de proyecto,
nombre de organización o períodos superpuestos. Período admite fecha, mes,
año y variantes ISO. Se normalizan entrada y columnas SQL, sin depender de
una collation concreta. Los resultados se presentan en tabla paginada de 20.

La tabla permite comparar proyecto, organización, convenio, rendición y
período antes de elegir «Gestionar»; reemplaza un select con etiquetas largas.
Como alternativa futura para móviles se pueden usar tarjetas con esos mismos
datos; no se agrega un segundo componente en este cambio.

El selector de rendiciones incluidas es compacto, sin buscador interno.
La base aparece marcada, grisada y bloqueada. Se conserva su inclusión fija
al cambiar la decisión de acta. La documentación se muestra por rendición;
en el detalle se oculta si validación y acta todavía están sin definir.
Los paneles muestran validación NULL/False como «No».

Las etiquetas y los controles de validación/acta comparten una grilla responsive;
el checkbox se presenta como «Confirmar validación», con borde contrastado,
sin imitar un campo de texto. La información general utiliza una grilla
uniforme. Se reutilizan layout, colores, variables CSS, tarjetas y botones
del módulo; se respeta CSP con archivos estáticos, sin scripts inline.

Volver usa la navegación unificada y destinos explícitos al detalle o a
resultados según el origen; el formulario es transitorio y conserva filtros.
El detalle vuelve al listado. El legajo de organización omite Monto Auditado
y Observaciones en listado y detalle.

## Permisos, arquitectura y compatibilidad

Se reutilizan `manage_auditoria_stage` y `manage_regularizacion_stage`;
no se agregan permisos, dependencias ni contratos entre verticales.
La lógica se concentra en servicios del core; URLs registradas dentro del
prefijo existente y `url_registry.json` regenerado. No cambia la API PWA.

Los campos de validación, decisión, inclusión y origen del acta no se ofrecen
para editar desde el formulario general. La gestión revalida datos y estado
en el servidor, independientemente de los controles de la interfaz.
Los formularios/servicios históricos se conservan; los POST antiguos de
Auditoría en el detalle redirigen a la pantalla específica sin escribir.

## Migraciones, deploy y rollback

Aplicar con settings completos mediante el migrador, antes de publicar el core:

1. `0023_issue_2673_validada`: booleano nullable, sin inferir validaciones
   históricas desde fechas de revisión.
2. `0024_cierre_gestion_auditoria`: marca gestiones existentes con validación
   y decisión explícitas, usando fecha auditada, de carga o última modificación.
3. `0025_origen_acta_auditoria`: persiste la base en todos los integrantes.
   Recupera actas individuales y grupos históricos coherentes por el orden
   de inserción de vínculos: los guardados anteriores insertaban primero los
   de la base. No infiere por número de rendición ni estado actual. Los grupos
   inconsistentes quedan sin origen y requieren conciliación antes de ofrecer
   acciones. Esta recuperación depende de conservar el orden de esos vínculos.

Las tres migraciones están aplicadas en la base local verificada `sisoc-local`.
No hace falta publicar otras verticales. El rollback de imagen puede conservar
las columnas nullable; revertir esquema elimina validación, cierre y origen,
y requiere backup si deben recuperarse. Las reversas de datos son noop.

## Validación y límites

Revisión de `AGENTS.md` y sus guías vigentes. `CODEX.md` fue fusionado en
`AGENTS.md` durante la reorganización de octubre; no existe un segundo archivo
vigente que aplicar. Se ejecutan tests de formularios, servicios, vistas,
permisos, búsqueda, cierre, inclusión, regularización y recuperación de origen,
además de regresiones cercanas de rendiciones, organizaciones y PWA.

La base de tests está aislada mediante `USE_SQLITE_FOR_TESTS=1`; no se borran
ni reinician datos dummy locales. La selección obsoleta tiene regresión de
revalidación/rollback; no equivale a una prueba de carreras concurrentes en
MySQL real. La recuperación de datos se verifica con las funciones de migración;
la coherencia del esquema se comprueba con `makemigrations --check --dry-run`.

Revisión visual manual en navegador local a 390, 1440 y 1800 px, sin guardar
la auditoría. El atajo de zoom del navegador integrado no produjo cambios;
se revisó también la distribución con mayor superficie disponible.
Los datos dummy se crearon solo en desarrollo y no forman parte de migraciones
ni de fixtures productivas.

Resultados de cierre (16/10/2026):

- 269 tests aprobados: auditoría, vistas/servicios/reglas de rendiciones,
  visualizaciones, seed de etapas, organizaciones, edición PWA, filtros,
  historial y registro de URLs.
- Black: 13 archivos sin cambios de formato. Pylint: 10/10 para los seis
  archivos de lógica modificados. djlint: seis templates sin diferencias.
- `makemigrations rendicioncuentasmensual --check --dry-run`: sin cambios.
- Sintaxis JavaScript correcta; `git diff --check` sin errores.
- Control documental: 83 documentos vigentes, cero referencias obsoletas.
- Se conservan seis advertencias de deprecación de Django 6 sobre el esquema
  predeterminado de URLField, ajenas al comportamiento de esta funcionalidad.

La revisión corrigió la exposición de datos del acta en el formulario general
por `fields="__all__"` y la propagación de regularización en grupos históricos
con validación NULL; ambas tienen regresiones. Se actualizaron los tests que
esperaban las reglas de iteraciones anteriores. Siete casos adicionales verifican
que la etiqueta sin acta exige validación y cierre, y no sustituye resultados
finalizados históricos.
